"""StealthMole live pipeline boundary must stay neutralized."""

import scripts.p0c_live_pipeline as live_pipeline


def test_live_pipeline_exposes_no_runner_or_scope_validator():
    assert not hasattr(live_pipeline, "run_live_pipeline")
    assert not hasattr(live_pipeline, "validate_live_scope")
    assert "intentionally emptied" in (live_pipeline.__doc__ or "")
