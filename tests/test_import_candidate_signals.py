"""Private candidate import validates normalized, redacted handoff files."""

import json

from scripts.import_candidate_signals import import_records


def test_import_candidate_signals_redacts_sensitive_values():
    records = [
        {
            "module": "cds",
            "scope": {
                "supplier_id": "sup-a",
                "query_type": "domain_exact",
                "query_value": "supplier-a.example",
            },
            "raw": {
                "id": "rec-1",
                "user": "ops@supplier-a.example",
                "host": "vpn.prime-x.example",
                "password": "Synthetic-Do-Not-Leak-1!",
                "session_cookie": "SESSION-Do-Not-Leak-2",
                "has_cookie": True,
                "infected_at": "2026-07-01T00:00:00Z",
                "malware": "ExampleStealer",
                "account_type": "vpn",
            },
        }
    ]

    result = import_records(records)
    text = json.dumps(result, ensure_ascii=False)

    assert result["summary"]["normalized_exposures"] == 1
    assert result["summary"]["lineage_entries"] == 1
    assert "Synthetic-Do-Not-Leak-1!" not in text
    assert "SESSION-Do-Not-Leak-2" not in text

    exposure = result["normalized_exposures"][0]
    assert exposure["secret"]["masked_value"].startswith("redacted:")
    assert exposure["source_ref_hash"]
    assert exposure["device"]["has_session_cookie"] is True
    assert exposure["is_active_signal"] is True

    lineage = result["lineage"][0]
    assert lineage["source_ref_hash"]
    assert lineage["raw_payload_exported"] is False
    assert lineage["policy"] == "raw_secret_removed"
    assert lineage["normalized_objects"] == [
        "CredentialExposure",
        "InfectedDevice",
        "Identity",
        "ThreatSource",
    ]
    assert "password" in lineage["removed_fields"]
    assert "session_cookie" in lineage["removed_fields"]
    assert "of" in lineage["links"]
    assert "targets" in lineage["links"]
    assert "FlagActiveCompromise" in lineage["engine_consumers"]
    assert "CompromiseIncident" in lineage["decision_outputs"]


def test_import_candidate_signals_context_modules_land_as_threat_sources():
    records = [
        {
            "module": "dt",
            "scope": {
                "supplier_id": "sup-a",
                "query_type": "company_alias",
                "query_value": "Alpha Precision",
            },
            "raw": {"id": "mention-1", "title": "synthetic mention"},
        },
        {
            "module": "tt",
            "scope": {
                "program_ref": "prog-sentinel",
                "query_type": "program_keyword",
                "query_value": "Sentinel ISR",
            },
            "raw": {"id": "mention-2", "title": "synthetic channel"},
        },
    ]

    result = import_records(records)

    assert result["summary"]["normalized_exposures"] == 0
    assert result["summary"]["threat_sources"] == 2
    assert result["summary"]["lineage_entries"] == 2
    assert result["threat_sources"][0]["ontology_targets"] == ["ThreatSource"]
    assert result["threat_sources"][0]["source_ref_hash"]
    assert result["lineage"][0]["normalized_objects"] == ["ThreatSource"]
    assert "ContextComponents" in result["lineage"][0]["engine_consumers"]


def test_import_candidate_signals_rejects_unknown_modules():
    result = import_records([{"module": "unknown", "raw": {"id": "x"}}])

    assert result["summary"]["rejected"] == 1
    assert result["summary"]["lineage_entries"] == 0
    assert result["rejected"][0]["reason"] == "unsupported module"
