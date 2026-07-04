"""Collection plan stays non-executing and ontology-targeted."""

from scripts.collection_plan import ACCESS_HOST_PREFIXES, build_plan, load_registry


def test_collection_plan_builds_non_executing_query_seeds():
    plan = build_plan(load_registry())

    assert plan["mode"] == "non_executing_collection_plan"
    assert plan["summary"]["suppliers"] == 9
    assert plan["summary"]["query_items"] > 0
    assert plan["public_jobs"]

    for item in plan["items"]:
        assert item["execute"] is False
        assert item["ontology_targets"], item["id"]
        assert item["handling"]["raw_secret_storage"] == "forbidden"
        assert item["handling"]["raw_cookie_storage"] == "forbidden"
        assert item["handling"]["raw_token_storage"] == "forbidden"


def test_collection_plan_covers_domains_email_and_access_hosts():
    plan = build_plan(load_registry())
    items = plan["items"]
    query_types = {item["query_type"] for item in items}

    assert "domain_exact" in query_types
    assert "email_domain" in query_types
    assert "target_host_pattern" in query_types
    assert "company_alias" in query_types
    assert "program_keyword" in query_types
    assert "country_keyword" in query_types

    sup_a_hosts = {
        item["query_value"]
        for item in items
        if item["id"].startswith("asset-host:sup-a:")
    }
    assert {f"{prefix}.supplier-a.example" for prefix in ACCESS_HOST_PREFIXES} <= sup_a_hosts


def test_collection_plan_lands_country_keywords_as_context_only():
    plan = build_plan(load_registry())
    regional = [item for item in plan["items"] if item["track"] == "regional_context"]

    assert regional
    for item in regional:
        assert item["sensitivity"] == "context_only"
        assert item["ontology_targets"] == ["ThreatSource"]
        assert "CredentialExposure" not in item["ontology_targets"]
        assert "InfectedDevice" not in item["ontology_targets"]


def test_collection_plan_has_private_feed_capability_mapping_without_execution():
    plan = build_plan(load_registry())
    domain_items = [item for item in plan["items"] if item["query_type"] == "domain_exact"]
    asset_items = [item for item in plan["items"] if item["query_type"] == "target_host_pattern"]

    assert domain_items
    assert asset_items
    assert all({"CL", "CDS"} <= set(item["provider_capabilities"]) for item in domain_items)
    assert any({"CDS", "DT", "TT"} <= set(item["provider_capabilities"]) for item in asset_items)
    assert all(item["execute"] is False for item in domain_items + asset_items)
