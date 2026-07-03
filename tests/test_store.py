"""(d) OntologyStore round-trip: write Exposure objects, read them back."""

from adapter.base import normalize
from adapter.mock import MODULES, SEED_SUPPLIERS, MockExposureSource
from store.sqlite import SqliteOntologyStore


def _seed_and_load(store: SqliteOntologyStore) -> int:
    src = MockExposureSource()
    for fqdn, meta in SEED_SUPPLIERS.items():
        store.upsert_supplier(
            id=meta["id"], name=meta["name"], tier=meta["tier"],
            criticality=meta["criticality"],
        )
        store.upsert_domain(fqdn=fqdn, supplier_id=meta["id"])
    written = 0
    for fqdn in src.domains():
        for module in MODULES:
            for raw in src.search(module, "domain", fqdn):
                store.write_exposure(normalize(module, raw), domain=fqdn)
                written += 1
    return written


def test_write_readback_counts():
    with SqliteOntologyStore(":memory:") as store:
        written = _seed_and_load(store)
        read = store.all_exposures()
        assert written > 0
        assert len(read) == written


def test_exposures_attributed_to_supplier():
    with SqliteOntologyStore(":memory:") as store:
        _seed_and_load(store)
        rows = store.exposures_for_supplier("sup-a")  # supplier-a.example
        assert rows, "supplier-a should have exposures"
        assert all(r["supplier_id"] == "sup-a" for r in rows)


def test_active_signal_survives_roundtrip():
    with SqliteOntologyStore(":memory:") as store:
        _seed_and_load(store)
        rows = store.all_exposures()
        active = [
            r for r in rows
            if r.get("has_session_cookie")
            and r.get("account_type") in {"vpn", "admin"}
            and r.get("infected_at")
        ]
        assert active, "active-compromise signal lost in store round-trip"
        assert any(r["account_type"] == "vpn" for r in active)


def test_no_raw_secret_persisted():
    src = MockExposureSource()
    with SqliteOntologyStore(":memory:") as store:
        _seed_and_load(store)
        rows = store.all_exposures()
        import json
        blob = json.dumps(rows)
        leaked = [s for s in src.raw_secrets() if s in blob]
        assert leaked == [], f"raw secret persisted: {leaked}"
        # masked values are present for present secrets
        present = [r for r in rows if r["secret_present"]]
        assert present and all(r["masked_value"].endswith("***") for r in present)


def test_entity_resolution_merges_identity():
    """Same email across modules → one Identity row (not one per exposure)."""
    with SqliteOntologyStore(":memory:") as store:
        _seed_and_load(store)
        n_identities = store.conn.execute(
            "SELECT COUNT(*) FROM identity"
        ).fetchone()[0]
        n_exposures = len(store.all_exposures())
        assert n_identities < n_exposures, "identities not merged (entity resolution)"
