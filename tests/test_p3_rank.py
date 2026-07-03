"""P3 ranking pipeline smoke test — the full mock→…→score pipe runs and its
RESULT check (active suppliers strictly on top, evidence present, incidents
opened) passes."""

from scripts.p3_rank import run


def test_p3_rank_pipeline_runs_green():
    assert run() == 0
