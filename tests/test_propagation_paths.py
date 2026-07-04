"""Multi-tier propagation: variable-depth recursive traverse + cycle safety +
subcontract-only active-compromise detection (pin #1/#2).

`store.propagation_paths` follows `subcontracts` upward (2차→1차→…) with a
WITH RECURSIVE CTE and resolves the reachable Prime→Program. These pin:
  * a genuine multi-tier chain assembles a variable-length path,
  * a subcontract cycle terminates (does not hang) — depth cap + visited guard,
  * a tier-2 terminal supplier with ONLY a subcontracts edge (no direct supplies)
    still opens a CompromiseIncident, and its path carries the intermediate
    tier-1 Supplier hop.
"""

from actions.correlate import correlate_exposures
from actions.flag_active import flag_active_compromises
from adapter.base import normalize
from adapter.mock import DEMO_NOW, DAY, MODULES, MockExposureSource
from registry.loader import load_into_store
from store.sqlite import SqliteOntologyStore


def _chain(store) -> SqliteOntologyStore:
    """tier-3 → tier-2 → tier-1 → prime → program, all subcontract edges except
    the tier-1 → prime supplies edge."""
    for sid, tier in (("s3", 3), ("s2", 2), ("s1", 1)):
        store.upsert_supplier(id=sid, name=sid.upper(), tier=tier, criticality=2)
    store.upsert_prime(id="pr", name="PrimeCo")
    store.upsert_program(id="pg", name="ProgramX", sensitivity="high")
    store.link_runs(prime_id="pr", program_id="pg")
    store.link_supplies(supplier_id="s1", prime_id="pr")     # only tier-1 supplies
    store.link_subcontract(sub_supplier_id="s3", parent_supplier_id="s2")
    store.link_subcontract(sub_supplier_id="s2", parent_supplier_id="s1")
    return store


# -- variable-depth traverse ---------------------------------------------------

def test_variable_depth_path_assembles_full_chain():
    with SqliteOntologyStore(":memory:") as store:
        _chain(store)
        paths = store.propagation_paths("s3")
        assert len(paths) == 1
        p = paths[0]
        assert [n["type"] for n in p] == [
            "Supplier", "Supplier", "Supplier", "Prime", "Program",
        ]
        assert [n["ref"] for n in p] == ["s3", "s2", "s1", "pr", "pg"]
        # start at the deeper tier-1 supplier → one supplier hop only
        assert [n["ref"] for n in store.propagation_paths("s1")[0]] == ["s1", "pr", "pg"]


def test_intermediate_supplier_with_no_supplies_is_transited_not_endpoint():
    """s2 supplies nothing directly — it must NOT emit its own (dead-end) path,
    only be transited on s3's path."""
    with SqliteOntologyStore(":memory:") as store:
        _chain(store)
        assert store.propagation_paths("s2")  # s2 reaches the prime via s1
        assert all(p[-1]["ref"] == "pg" for p in store.propagation_paths("s2"))


# -- cycle safety --------------------------------------------------------------

def test_subcontract_cycle_terminates():
    """A ↔ B mutual subcontract must not loop forever (visited guard + cap)."""
    with SqliteOntologyStore(":memory:") as store:
        store.upsert_supplier(id="A", name="A", tier=2, criticality=2)
        store.upsert_supplier(id="B", name="B", tier=1, criticality=2)
        store.upsert_prime(id="pr", name="P")
        store.upsert_program(id="pg", name="G", sensitivity="low")
        store.link_runs(prime_id="pr", program_id="pg")
        store.link_supplies(supplier_id="B", prime_id="pr")
        store.link_subcontract(sub_supplier_id="A", parent_supplier_id="B")
        store.link_subcontract(sub_supplier_id="B", parent_supplier_id="A")  # cycle
        paths = store.propagation_paths("A")   # must return, not hang
        # A → B → prime → program; the cycle back to A is pruned by the visited guard
        assert any([n["ref"] for n in p] == ["A", "B", "pr", "pg"] for p in paths)
        assert all(len([n for n in p if n["type"] == "Supplier"]) <= 2 for p in paths)


def test_self_loop_terminates():
    with SqliteOntologyStore(":memory:") as store:
        store.upsert_supplier(id="X", name="X", tier=1, criticality=2)
        store.upsert_prime(id="pr", name="P")
        store.link_supplies(supplier_id="X", prime_id="pr")
        store.link_subcontract(sub_supplier_id="X", parent_supplier_id="X")  # self
        paths = store.propagation_paths("X")   # must return
        assert paths and all(p[0]["ref"] == "X" for p in paths)


# -- subcontract-only tier-2 active case (pin #2) -----------------------------

def _mock_pipe(store) -> None:
    load_into_store(store)
    src = MockExposureSource()
    for fqdn in src.domains():
        for module in MODULES:
            for raw in src.search(module, "domain", fqdn):
                store.write_exposure(normalize(module, raw))
    correlate_exposures(store, now=DEMO_NOW)


def test_subcontract_only_tier2_opens_incident_with_intermediate_hop():
    with SqliteOntologyStore(":memory:") as store:
        _mock_pipe(store)
        # sup-h has NO direct supplies edge (subcontracts-only) …
        assert store.propagation_for_supplier("sup-h") == []
        # … yet the recursive traverse reaches a Program through sup-f (tier-1).
        assert store.propagation_paths("sup-h")

        res = flag_active_compromises(store, now=DEMO_NOW)
        h = [i for i in res.incidents if i["supplier_ref"] == "sup-h"]
        assert h, "subcontract-only tier-2 active supplier got no incident"
        path = h[0]["path"]
        supplier_refs = [n["ref"] for n in path if n["type"] == "Supplier"]
        # both the terminal (sup-h) AND the intermediate tier-1 (sup-f) are on it
        assert supplier_refs == ["sup-h", "sup-f"]
        assert path[-1]["type"] == "Program" and path[-1]["ref"]
