from adapter.stealthmole import StealthMoleSource
from scripts.p0c_live_pipeline import run_live_pipeline, validate_live_scope
from store.sqlite import SqliteOntologyStore


REGISTRY = {
    "suppliers": [{
        "id": "sup-live", "name": "Live Supplier", "tier": 1,
        "criticality": 3, "domains": ["owned-company.com"],
        "supplies": "prime-live",
    }],
    "primes": [{
        "id": "prime-live", "name": "Live Prime", "runs": ["prog-live"],
    }],
    "programs": [{
        "id": "prog-live", "name": "Live Program", "sensitivity": "high",
    }],
}


class FakeLiveSource:
    last_response_meta = {}

    def quotas(self):
        return {"CDS": {"allowed": 100, "used": 0}}

    def search(self, module, obs_type, value, start=None):
        assert (module, obs_type, value, start) == (
            "cds", "domain", "owned-company.com", None
        )
        self.last_response_meta = {
            "totalCount": 1, "cursor": None, "limit": 50, "queryCost": 1,
        }
        return [{
            "id": "live-cds-1",
            "email": "admin@owned-company.com",
            "password": "DoNotPersistThisPassword",
            "host": "vpn.owned-company.com",
            "infected_at": 1783160000,
            "malware": "RedLine",
            "session_cookie": "DoNotPersistThisCookie",
            "has_session_cookie": True,
            "account_type": "admin",
        }]


def test_scope_rejects_synthetic_and_unregistered_domains():
    try:
        validate_live_scope(
            domains=["supplier-a.example"], modules=["cds"], registry=REGISTRY
        )
    except ValueError as exc:
        assert "reserved/synthetic" in str(exc)
    else:
        raise AssertionError("synthetic live query should be refused")

    try:
        validate_live_scope(
            domains=["unknown-company.com"], modules=["cds"], registry=REGISTRY
        )
    except ValueError as exc:
        assert "not present" in str(exc)
    else:
        raise AssertionError("unregistered live query should be refused")


def test_live_pipeline_reaches_risk_program_and_draft_without_raw_secrets():
    store = SqliteOntologyStore(":memory:")
    try:
        summary = run_live_pipeline(
            source=FakeLiveSource(), store=store, registry=REGISTRY,
            domains=["owned-company.com"], modules=["cds"], now=1783162903,
        )
        assert summary["records_received"] == 1
        assert summary["correlation"] == {"matched": 1, "unmatched": 0}
        assert summary["incidents_opened"] == 1
        assert summary["risk_assessments"] == 1
        assert summary["program_exposures"] == 1
        assert summary["notification_drafts"] == 1

        exposure_blob = str(store.all_exposures())
        draft_blob = str(store.notification_drafts())
        for raw in ("DoNotPersistThisPassword", "DoNotPersistThisCookie"):
            assert raw not in exposure_blob
            assert raw not in draft_blob
        assert "인가된 외부 위협 인텔리전스 연동" in draft_blob
        assert "모의 데이터" not in draft_blob
    finally:
        store.close()
