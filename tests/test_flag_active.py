"""(c)/(d) FlagActiveCompromise: path detection accuracy + no-path refusal.

Active compromise is a graph path, not a heuristic. Exactly the three seeded
active suppliers get a CompromiseIncident (each with a complete VARIABLE-LENGTH
path — sup-a/sup-g have the classic 6-node shape, sup-h the multi-tier terminal
has a longer path with an intermediate Supplier hop); a qualifying device whose
supplier has no Prime→Program connection yields NO incident (the derived object
is refused without its traverses path)."""

from actions.correlate import correlate_exposures
from actions.flag_active import flag_active_compromises
from adapter.base import normalize
from adapter.mock import DEMO_NOW, DAY, MODULES, MockExposureSource
from registry.loader import load_into_store
from store.sqlite import SqliteOntologyStore

_ACTIVE_SUPPLIERS = {"sup-a", "sup-g", "sup-h"}


def _full_pipe(store) -> None:
    load_into_store(store)
    src = MockExposureSource()
    for fqdn in src.domains():
        for module in MODULES:
            for raw in src.search(module, "domain", fqdn):
                store.write_exposure(normalize(module, raw))
    correlate_exposures(store, now=DEMO_NOW)


def _assert_path_shape(path) -> None:
    """A valid traverses path: Device → Identity → Domain, then ≥1 Supplier hop,
    ending Prime → Program, every node populated."""
    types = [n["type"] for n in path]
    assert types[:3] == ["InfectedDevice", "Identity", "Domain"]
    assert types[-2:] == ["Prime", "Program"]
    supplier_hops = types[3:-2]
    assert supplier_hops and set(supplier_hops) == {"Supplier"}
    assert all(n["ref"] for n in path)


# -- (d) exactly three active suppliers, each with a complete path ------------

def test_flag_opens_incident_for_each_active_supplier():
    with SqliteOntologyStore(":memory:") as store:
        _full_pipe(store)
        res = flag_active_compromises(store, now=DEMO_NOW)
        assert len(res.incidents) == 3
        assert {i["supplier_ref"] for i in res.incidents} == _ACTIVE_SUPPLIERS
        # persisted incidents each carry a complete (variable-length) path
        for inc in store.incidents():
            assert inc["status"] == "open"
            _assert_path_shape(inc["path"])


def test_flag_skips_stale_and_non_privileged_devices():
    with SqliteOntologyStore(":memory:") as store:
        _full_pipe(store)
        res = flag_active_compromises(store, now=DEMO_NOW)
        # the stale (40d, no cookie, user account) stealer hits are skipped
        assert res.skipped
        assert all(inc["supplier_ref"] in _ACTIVE_SUPPLIERS for inc in res.incidents)


# -- (c) no Supplier→Prime→Program path ⇒ incident refused --------------------

def test_flag_refuses_incident_without_prime_program_path():
    with SqliteOntologyStore(":memory:") as store:
        # a supplier with a domain but NO supplies/runs link
        store.upsert_supplier(id="lone", name="Lone Supplier", tier=2, criticality=2)
        store.upsert_domain(fqdn="lone.example", supplier_id="lone")
        raw = {
            "id": "cds-lone-active",
            "user": "ops@lone.example",
            "password": "Synthetic-lone-1!",
            "session_cookie": "SIDdeadbeefdeadbeefdeadbeef01",
            "has_cookie": True,
            "malware": "RedLine",
            "infected_at": DEMO_NOW - 2 * DAY,
            "account_type": "admin",
            "host": "vpn.lone.example",
            "os": "Windows 10",
            "_mock": True,
        }
        store.write_exposure(normalize("cds", raw))
        correlate_exposures(store, now=DEMO_NOW)

        res = flag_active_compromises(store, now=DEMO_NOW)
        assert res.incidents == []
        assert store.incidents() == []
        # device met conditions 1-4 but was refused on condition 5 (no path)
        reasons = " ".join(r for s in res.skipped for r in s["reasons"])
        assert "Prime" in reasons and "Program" in reasons
