"""(a) Mock yields records across all four modules + an active case exists."""

from adapter.mock import ACTIVE_DOMAINS, MODULES, MockExposureSource


def test_all_four_modules_present():
    src = MockExposureSource()
    seen = {m for (_d, m, _r) in src.all_records()}
    assert set(MODULES) <= seen, f"missing modules: {set(MODULES) - seen}"


def test_active_compromise_case_exists():
    src = MockExposureSource()
    active = [
        r for (_d, m, r) in src.all_records()
        if m == "cds"
        and r.get("has_cookie") is True
        and r.get("account_type") in {"vpn", "admin"}
        and r.get("malware")
        and r.get("infected_at")
    ]
    assert active, "no active-compromise cds record produced"
    # RedLine active case as specified in the decision.
    assert any(r.get("malware") == "RedLine" for r in active)


def test_records_flagged_mock():
    src = MockExposureSource()
    assert all(r.get("_mock") is True for (_d, _m, r) in src.all_records())


def test_deterministic_across_instances():
    a = MockExposureSource().all_records()
    b = MockExposureSource().all_records()
    assert a == b, "mock corpus is not deterministic"


def test_clean_domains_have_no_records():
    src = MockExposureSource()
    domains_with_records = {d for (d, _m, _r) in src.all_records()}
    # At least one seeded domain is clean (no exposures) — demo realism.
    assert domains_with_records < set(src.domains())


def test_active_domains_are_not_clean():
    src = MockExposureSource()
    domains_with_records = {d for (d, _m, _r) in src.all_records()}
    assert ACTIVE_DOMAINS <= domains_with_records
