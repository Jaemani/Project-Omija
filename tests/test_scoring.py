"""(a)/(e)/(g) Scoring guarantees: active dominance, dedup counting, grades.

These pin the *guarantees* (active always outranks non-active; recirculation is
counted once; grade thresholds), not the exact magic numbers in `SCORING`."""

from actions.correlate import correlate_exposures
from actions.scoring import dedup_exposures, grade_for, score_supplier
from adapter.base import normalize
from adapter.mock import DEMO_NOW, MODULES, MockExposureSource
from registry.loader import load_into_store
from store.sqlite import SqliteOntologyStore

DAY = 86400


# -- (a) active-compromise dominance ------------------------------------------

def test_active_outranks_heavy_nonactive():
    """A lightly-exposed, tier-2/medium ACTIVE supplier must outrank a
    heavily-exposed, tier-1/high NON-active supplier — the core differentiator."""
    now = DEMO_NOW
    heavy = [
        {"identity_ref": f"id{i}", "host": f"h{i}", "secret_type": "plaintext",
         "module": "ub", "observed_at": now - DAY}
        for i in range(12)
    ]
    s_heavy, g_heavy, _ = score_supplier(
        heavy, supplier={"id": "heavy", "tier": 1, "criticality": 3},
        active_flag=False, now=now,
    )
    light_active = [
        {"identity_ref": "x", "host": "vpn", "secret_type": "cookie",
         "module": "cds", "infected_at": now - 2 * DAY},
    ]
    s_active, g_active, _ = score_supplier(
        light_active, supplier={"id": "light", "tier": 2, "criticality": 2},
        active_flag=True, active_age_days=2, now=now,
    )
    assert s_active > s_heavy
    assert g_active == "즉시"
    assert s_heavy < 70.0     # any non-active stays out of the active band


def test_active_band_floor_holds_for_weak_active():
    """Even a supplier with almost no base exposure, once active, clears the
    active floor (path existence guarantees top-tier triage)."""
    now = DEMO_NOW
    weak = [{"identity_ref": "x", "host": "h", "secret_type": "hash",
             "module": "cb", "observed_at": now - 300 * DAY}]
    score, grade, comp = score_supplier(
        weak, supplier={"id": "w", "tier": 2, "criticality": 1},
        active_flag=True, now=now,
    )
    assert score >= 70.0
    assert grade == "즉시"
    assert comp["active_flag"] is True


# -- (e) dedup counting --------------------------------------------------------

def test_dedup_collapses_recirculated_credential():
    rows = [
        {"identity_ref": "id:ops", "host": "mail", "secret_type": "plaintext", "module": "ub"},
        {"identity_ref": "id:ops", "host": "mail", "secret_type": "plaintext", "module": "cb"},  # recirc dup
        {"identity_ref": "id:admin", "host": "hr", "secret_type": "hash", "module": "cl"},
    ]
    dd = dedup_exposures(rows)
    assert dd["raw_count"] == 3
    assert dd["dedup_count"] == 2                      # recirc pair collapses to one
    assert set(dd["modules"]) == {"ub", "cb", "cl"}   # provenance/diversity preserved


def test_dedup_count_on_mock_delta_parts():
    """Delta Parts carries a ub→cb recirculation: 5 raw exposures, 4 deduped."""
    with SqliteOntologyStore(":memory:") as store:
        load_into_store(store)
        src = MockExposureSource()
        for fqdn in src.domains():
            for module in MODULES:
                for raw in src.search(module, "domain", fqdn):
                    store.write_exposure(normalize(module, raw))
        correlate_exposures(store, now=DEMO_NOW)
        rows = store.exposures_for_supplier("sup-d")
        dd = dedup_exposures(rows)
        assert dd["raw_count"] == 5
        assert dd["dedup_count"] == 4
        assert {"ub", "cb"} <= set(dd["modules"])


# -- (g) grade thresholds ------------------------------------------------------

def test_grade_thresholds():
    assert grade_for(100.0) == "즉시"
    assert grade_for(70.0) == "즉시"
    assert grade_for(69.99) == "주의"
    assert grade_for(40.0) == "주의"
    assert grade_for(39.99) == "관찰"
    assert grade_for(0.0) == "관찰"
