"""StealthMole recon boundary must stay neutralized."""

import scripts.p0b_recon as recon


def test_p0b_recon_exposes_no_runner_or_network_helpers():
    assert not hasattr(recon, "main")
    assert not hasattr(recon, "run")
    assert not hasattr(recon, "StealthMoleSource")
    assert "intentionally emptied" in (recon.__doc__ or "")
