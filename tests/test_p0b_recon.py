"""P0-B recon: no-network safety + masking (CLAUDE.md guardrails).

Two invariants are enforced without ever touching the network:
  1. Missing credentials → the script is a clean no-op: it exits 0 and NEVER
     constructs a live source (so no JWT is signed and no HTTP call is made).
  2. Raw secrets never survive into the recon output — the masking helpers
     redact them.
"""

from __future__ import annotations

import json

import scripts.p0b_recon as recon


def test_hackathon_quotas_exclude_unavailable_modules_and_use_remaining():
    modules = dict(recon._open_modules({
        "CDS": {"allowed": 10000, "used": 916},
        "DT": {"allowed": 10000, "used": 24},
        "UB": {"allowed": 10000, "used": 0},
    }))
    assert modules == {"cds": 9084}


def test_missing_keys_exits_zero_with_zero_network(monkeypatch):
    # A local .env must not be able to inject keys during the test.
    monkeypatch.setattr(recon, "_load_dotenv", lambda *_a, **_k: None)
    monkeypatch.delenv("STEALTHMOLE_ACCESS_KEY", raising=False)
    monkeypatch.delenv("STEALTHMOLE_SECRET_KEY", raising=False)

    # Constructing a live source (which would sign a JWT / open httpx) is the
    # only path to the network. Make it explode so any attempt fails the test.
    def _boom(*_a, **_k):
        raise AssertionError(
            "network path reached: StealthMoleSource constructed without keys"
        )

    monkeypatch.setattr(recon, "StealthMoleSource", _boom)

    # Missing keys is NOT an error — exit 0, no source constructed, 0 network.
    assert recon.main([]) == 0


def test_require_keys_false_prints_guidance(monkeypatch, capsys):
    monkeypatch.delenv("STEALTHMOLE_ACCESS_KEY", raising=False)
    monkeypatch.delenv("STEALTHMOLE_SECRET_KEY", raising=False)

    assert recon._require_keys() is False
    err = capsys.readouterr().err
    assert "STEALTHMOLE_ACCESS_KEY" in err  # actionable, points at the env var


def test_mask_value_never_returns_raw_secret():
    raw = "SuperSecretHunter2Password"
    masked = recon._mask_value("password", raw, set())
    assert masked != raw
    assert raw not in str(masked)


def test_collect_fields_emits_schema_without_raw_secrets():
    raw_pw = "PlaintextRedLineLoot99"
    raw_cookie = "SID" + "a" * 40
    records = [
        {
            "user": "ops@supplier-a.example",
            "password": raw_pw,
            "session_cookie": raw_cookie,
            "malware": "RedLine",
            "infected_at": 1751500000,
            "has_cookie": True,
            "account_type": "vpn",
        }
    ]
    schema = recon._collect_fields(records, set())

    # schema captures field NAMES (the shape we want to confirm on day-1)
    for name in ("password", "session_cookie", "malware", "infected_at"):
        assert name in schema

    # ...but no raw secret value survives anywhere in the serialized summary
    blob = json.dumps(schema, default=str)
    assert raw_pw not in blob
    assert raw_cookie not in blob
