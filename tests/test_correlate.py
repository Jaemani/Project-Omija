"""(f) CorrelateExposure: email-domain → Supplier attribution, subdomain
handling, match_basis provenance, and unmatched counting."""

from actions.correlate import correlate_exposures, match_domain
from adapter.base import normalize
from adapter.mock import DEMO_NOW, MODULES, MockExposureSource
from registry.loader import load_into_store
from store.sqlite import SqliteOntologyStore


def _pipe(store) -> None:
    load_into_store(store)
    src = MockExposureSource()
    for fqdn in src.domains():
        for module in MODULES:
            for raw in src.search(module, "domain", fqdn):
                store.write_exposure(normalize(module, raw))  # unattributed


# -- pure matcher --------------------------------------------------------------

def test_match_domain_exact():
    reg = {"supplier-a.example", "parts-d.example"}
    matched, basis = match_domain("supplier-a.example", reg)
    assert matched == "supplier-a.example"
    assert "==" in basis


def test_match_domain_subdomain():
    reg = {"supplier-a.example"}
    matched, basis = match_domain("mail.supplier-a.example", reg)
    assert matched == "supplier-a.example"
    assert "subdomain" in basis


def test_match_domain_unmatched():
    reg = {"supplier-a.example"}
    matched, basis = match_domain("evil.other.example", reg)
    assert matched is None
    assert "no registered" in basis


def test_match_domain_longest_parent_wins():
    reg = {"example", "supplier-a.example"}
    matched, _ = match_domain("mail.supplier-a.example", reg)
    assert matched == "supplier-a.example"  # most specific parent


# -- action over the store -----------------------------------------------------

def test_correlate_attributes_exposures_to_supplier():
    with SqliteOntologyStore(":memory:") as store:
        _pipe(store)
        result = correlate_exposures(store, now=DEMO_NOW)
        assert result.matched_exposures > 0
        rows = store.exposures_for_supplier("sup-a")  # supplier-a.example
        assert rows, "supplier-a should have correlated exposures"
        assert all(r["supplier_id"] == "sup-a" for r in rows)


def test_correlate_records_match_basis_provenance():
    with SqliteOntologyStore(":memory:") as store:
        _pipe(store)
        correlate_exposures(store, now=DEMO_NOW)
        corr = store.correlations()
        assert corr, "no correlation provenance recorded"
        assert all(c["match_basis"] for c in corr), "match_basis must be recorded"
        assert all(c["supplier_id"] for c in corr)


def test_correlate_subdomain_email_is_attributed():
    """An email at a subdomain of a registered domain must still correlate."""
    with SqliteOntologyStore(":memory:") as store:
        load_into_store(store)
        raw = {
            "id": "ub-sub-0",
            "user": "ops@mail.supplier-a.example",  # subdomain email
            "password": "Synthetic-sub-1!",
            "host": "https://mail.supplier-a.example/login",
            "leak_date": DEMO_NOW - 5 * 86400,
            "_mock": True,
        }
        store.write_exposure(normalize("ub", raw))
        result = correlate_exposures(store, now=DEMO_NOW)
        assert result.matched_exposures == 1
        rows = store.exposures_for_supplier("sup-a")
        assert any(r["id"] == "exp:ub-sub-0" for r in rows)


def test_correlate_counts_unmatched():
    """An exposure whose email domain is not registered stays unmatched."""
    with SqliteOntologyStore(":memory:") as store:
        load_into_store(store)
        foreign = {
            "id": "cb-foreign-0",
            "user": "admin@not-a-supplier.example",  # unregistered
            "password": "Synthetic-x-1!",
            "host": "not-a-supplier.example",
            "leak_date": DEMO_NOW - 10 * 86400,
            "_mock": True,
        }
        store.write_exposure(normalize("cb", foreign))
        result = correlate_exposures(store, now=DEMO_NOW)
        assert result.unmatched_exposures == 1
        unmatched = store.unmatched_exposures()
        assert any(u["source_ref"] == "cb-foreign-0" for u in unmatched)
        # and it is NOT attributed to any supplier
        assert all(
            not store.exposures_for_supplier(s["id"])
            or all(r["source_ref"] != "cb-foreign-0"
                   for r in store.exposures_for_supplier(s["id"]))
            for s in store.suppliers()
        )


def test_clean_supplier_has_no_exposures_after_correlate():
    with SqliteOntologyStore(":memory:") as store:
        _pipe(store)
        correlate_exposures(store, now=DEMO_NOW)
        # sup-e (logistics-e.example) is clean in the mock
        assert store.exposures_for_supplier("sup-e") == []
