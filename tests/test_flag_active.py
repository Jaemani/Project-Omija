"""(c)/(d) FlagActiveCompromise: path detection accuracy + no-path refusal.

Active compromise is a graph path, not a heuristic. Exactly the two seeded
active suppliers get a CompromiseIncident (each with a full 6-hop path); a
qualifying device whose supplier has no Prime→Program connection yields NO
incident (the derived object is refused without its traverses path)."""

from actions.correlate import correlate_exposures
from actions.flag_active import flag_active_compromises
from adapter.base import normalize
from adapter.mock import DEMO_NOW, DAY, MODULES, MockExposureSource
from registry.loader import load_into_store
from store.sqlite import SqliteOntologyStore

_FULL_PATH = ["InfectedDevice", "Identity", "Domain", "Supplier", "Prime", "Program"]


def _full_pipe(store) -> None:
    load_into_store(store)
    src = MockExposureSource()
    for fqdn in src.domains():
        for module in MODULES:
            for raw in src.search(module, "domain", fqdn):
                store.write_exposure(normalize(module, raw))
    correlate_exposures(store, now=DEMO_NOW)


# -- (d) exactly two active suppliers, each with a complete path ---------------

def test_flag_opens_incident_for_each_active_supplier():
    with SqliteOntologyStore(":memory:") as store:
        _full_pipe(store)
        res = flag_active_compromises(store, now=DEMO_NOW)
        assert len(res.incidents) == 2
        assert {i["supplier_ref"] for i in res.incidents} == {"sup-a", "sup-g"}
        # persisted incidents each carry the full traverses path
        for inc in store.incidents():
            assert inc["status"] == "open"
            assert [n["type"] for n in inc["path"]] == _FULL_PATH
            assert all(n["ref"] for n in inc["path"])


def test_flag_skips_stale_and_non_privileged_devices():
    with SqliteOntologyStore(":memory:") as store:
        _full_pipe(store)
        res = flag_active_compromises(store, now=DEMO_NOW)
        # the stale (40d, no cookie, user account) stealer hits are skipped
        assert res.skipped
        assert all(inc["supplier_ref"] in {"sup-a", "sup-g"} for inc in res.incidents)


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
