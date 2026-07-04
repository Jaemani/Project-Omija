"""StealthMole live boundary must stay neutralized."""

import adapter.stealthmole as stealthmole


def test_stealthmole_adapter_exposes_no_live_client():
    assert not hasattr(stealthmole, "StealthMoleSource")
    assert not hasattr(stealthmole, "sm_headers")
    assert not hasattr(stealthmole, "BASE_URL")
    assert "intentionally emptied" in (stealthmole.__doc__ or "")
