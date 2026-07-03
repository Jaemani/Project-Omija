"""(e) Registry loads and seeds the ontology store (Supplier·Domain·Prime·
Program + supplies/runs), and mirrors the mock corpus (active + clean)."""

from adapter.mock import ACTIVE_DOMAINS, SEED_SUPPLIERS
from registry.loader import load_into_store, load_registry
from store.sqlite import SqliteOntologyStore


def test_registry_parses_all_sections():
    reg = load_registry()
    assert reg["suppliers"], "no suppliers in registry"
    assert reg["primes"], "no primes in registry"
    assert reg["programs"], "no programs in registry"


def test_registry_domains_match_mock():
    """Every mock seed domain must be a registered supplier domain (so the mock
    corpus correlates cleanly)."""
    reg = load_registry()
    reg_domains = {d for s in reg["suppliers"] for d in s.get("domains", [])}
    assert set(SEED_SUPPLIERS.keys()) == reg_domains


def test_registry_covers_active_and_clean():
    reg = load_registry()
    reg_domains = {d for s in reg["suppliers"] for d in s.get("domains", [])}
    # active-compromise domains present
    assert ACTIVE_DOMAINS <= reg_domains
    # at least one clean domain present
    clean = {d for d, m in SEED_SUPPLIERS.items() if m["clean"]}
    assert clean & reg_domains


def test_load_into_store_populates_objects_and_links():
    with SqliteOntologyStore(":memory:") as store:
        counts = load_into_store(store)
        assert counts["suppliers"] == len(SEED_SUPPLIERS)
        assert counts["domains"] == len(SEED_SUPPLIERS)
        assert counts["primes"] >= 1
        assert counts["programs"] >= 1
        assert counts["supplies"] >= 1
        assert counts["runs"] >= 1

        # objects readable back
        assert len(store.suppliers()) == len(SEED_SUPPLIERS)
        assert store.primes()
        assert store.programs()

        # owns-link: every domain resolves to a supplier
        registered = store.registered_domains()
        assert set(registered) == set(SEED_SUPPLIERS.keys())
        assert all(v for v in registered.values())


def test_propagation_path_supplier_to_program():
    """Supplier → Prime → Program path exists for a supplier (upward propagation)."""
    with SqliteOntologyStore(":memory:") as store:
        load_into_store(store)
        rows = store.propagation_for_supplier("sup-a")
        assert rows, "sup-a has no propagation path"
        assert any(r.get("prime_id") for r in rows)
        assert any(r.get("program_id") for r in rows), "no Prime→Program reached"
