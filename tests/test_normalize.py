"""(b) normalize() preserves active fields AND drops raw secrets (masking)."""

import json

from adapter.base import mask_secret, normalize
from adapter.mock import MODULES, MockExposureSource


def test_active_fields_preserved():
    raw = {
        "id": "cds-x-active",
        "user": "ops@supplier-a.example",
        "password": "Synthetic-cds-active-1234!",
        "session_cookie": "SIDdeadbeefdeadbeefdeadbeef00",
        "has_cookie": True,
        "malware": "RedLine",
        "infected_at": 1783000000,
        "account_type": "vpn",
        "host": "vpn.supplier-a.example",
        "_mock": True,
    }
    exp = normalize("cds", raw)
    assert exp.device.infected_at == 1783000000
    assert exp.device.has_session_cookie is True
    assert exp.device.account_type == "vpn"
    assert exp.device.malware == "RedLine"
    assert exp.is_active_signal is True


def test_raw_secret_absent_from_serialization():
    """No synthetic raw secret (password/cookie) may appear in the serialized
    Exposure — only the masked value (first 2 chars + ***)."""
    src = MockExposureSource()
    raw_secrets = src.raw_secrets()
    assert raw_secrets  # sanity

    blob_parts = []
    for _domain, module, raw in src.all_records():
        exp = normalize(module, raw)
        blob_parts.append(json.dumps(exp.to_dict()))
    blob = "\n".join(blob_parts)

    leaked = [s for s in raw_secrets if s in blob]
    assert leaked == [], f"raw secret leaked into normalized output: {leaked}"


def test_secret_present_is_masked():
    src = MockExposureSource()
    for _domain, module, raw in src.all_records():
        exp = normalize(module, raw)
        if exp.secret.present:
            assert exp.secret.masked_value is not None
            assert exp.secret.masked_value.endswith("***")


def test_confidence_by_module():
    src = MockExposureSource()
    expected = {"cds": 0.9, "ub": 0.9, "cl": 0.6, "cb": 0.3}
    for _domain, module, raw in src.all_records():
        exp = normalize(module, raw)
        assert exp.confidence == expected[module]
    # all four modules exercised
    assert set(MODULES) == set(expected)


def test_mask_short_secret_fully_redacted():
    assert mask_secret("ab") == "***"
    assert mask_secret("abcdef") == "ab***"
    assert mask_secret(None) is None


def test_email_vs_username_identity():
    e = normalize("cb", {"user": "sales@x.example", "password": "Synthetic-1!"})
    assert e.identity.email == "sales@x.example"
    assert e.identity.username is None
    u = normalize("cb", {"user": "localadmin", "password": "Synthetic-2!"})
    assert u.identity.username == "localadmin"
    assert u.identity.email is None


def test_is_mock_flag_propagates():
    exp = normalize("cb", {"user": "a@x.example", "password": "Synthetic-9!", "_mock": True})
    assert exp.is_mock is True
    assert exp.source == "stealthmole"
