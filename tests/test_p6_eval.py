"""P6 evaluation tests.

Covers:
  - the pure metric formulas (precision/recall/F1, attribution, ranking,
    golden-time) on SMALL hand-checked synthetic inputs — independent of the
    pipeline, so they pin the maths, not the mock,
  - the eval REFUSES to run without a ground-truth file (no silent pass),
  - the full eval runs green on the mock and hits the expected ceilings,
  - a masking spot-check: out/eval.json carries no raw secret.
"""

import json

import pytest

from scripts.p6_eval import (
    attribution_metrics,
    evaluate,
    golden_time,
    load_ground_truth,
    prf_from_sets,
    ranking_validity,
    run,
)


# --- prf_from_sets (active-compromise detection maths) -----------------------


def test_prf_perfect():
    m = prf_from_sets({"a", "b"}, {"a", "b"})
    assert (m["tp"], m["fp"], m["fn"]) == (2, 0, 0)
    assert m["precision"] == 1.0 and m["recall"] == 1.0 and m["f1"] == 1.0


def test_prf_false_positive_and_negative():
    # predicted {a, x}; truth {a, b} -> tp=1 (a), fp=1 (x), fn=1 (b)
    m = prf_from_sets({"a", "x"}, {"a", "b"})
    assert (m["tp"], m["fp"], m["fn"]) == (1, 1, 1)
    assert m["precision"] == 0.5 and m["recall"] == 0.5
    assert m["false_positives"] == ["x"]
    assert m["false_negatives"] == ["b"]


def test_prf_empty_predictions_convention():
    # nothing predicted, nothing true -> both 1.0 (correct "no positives" call)
    m = prf_from_sets(set(), set())
    assert m["precision"] == 1.0 and m["recall"] == 1.0


def test_prf_missed_everything():
    m = prf_from_sets(set(), {"a", "b"})
    assert (m["tp"], m["fp"], m["fn"]) == (0, 0, 2)
    assert m["recall"] == 0.0


# --- attribution_metrics (correlation maths) ---------------------------------


def test_attribution_perfect():
    pred = {"e1": "s1", "e2": "s1", "e3": "s2"}
    truth = {"e1": "s1", "e2": "s1", "e3": "s2"}
    m = attribution_metrics(pred, truth)
    assert m["precision"] == 1.0 and m["recall"] == 1.0
    assert m["correct"] == 3 and m["attributed"] == 3


def test_attribution_misattribution_and_unmatched():
    # e2 misattributed (s2 vs s1), e3 unmatched (None). 4 truth exposures.
    pred = {"e1": "s1", "e2": "s2", "e3": None, "e4": "s3"}
    truth = {"e1": "s1", "e2": "s1", "e3": "s2", "e4": "s3"}
    m = attribution_metrics(pred, truth)
    # attributed = e1,e2,e4 (3); correct = e1,e4 (2) -> precision 2/3
    assert m["attributed"] == 3 and m["correct"] == 2
    assert round(m["precision"], 4) == round(2 / 3, 4)
    # recall = correct / all truth = 2/4
    assert m["recall"] == 0.5
    assert m["misattributed"] == 1 and m["unmatched"] == 1
    assert m["misattributed_refs"] == ["e2"]


def test_attribution_coverage_gap_surfaced():
    # pipeline dropped e2 entirely -> it must show as missing, not vanish.
    pred = {"e1": "s1"}
    truth = {"e1": "s1", "e2": "s2"}
    m = attribution_metrics(pred, truth)
    assert m["coverage_missing_from_pipeline"] == ["e2"]
    assert m["recall"] == 0.5   # correct 1 / truth 2


# --- ranking_validity --------------------------------------------------------


def test_ranking_active_on_top():
    m = ranking_validity(["a", "g", "b", "c"], {"a", "g"})
    assert m["top_k_is_exactly_active"] is True
    assert m["reach_all_active_rank"] == 2
    assert m["active_positions"] == {"a": 1, "g": 2}


def test_ranking_active_not_on_top():
    m = ranking_validity(["a", "b", "g", "c"], {"a", "g"})
    assert m["top_k_is_exactly_active"] is False
    assert m["reach_all_active_rank"] == 3   # g sits at position 3


# --- golden_time -------------------------------------------------------------


def test_golden_time_reductions():
    g = golden_time(baseline_units=25, our_units_full=5,
                    our_units_to_active=2, minutes_per_item=3)
    assert g["baseline_minutes"] == 75
    assert g["our_full_triage_minutes"] == 15
    assert g["our_reach_active_minutes"] == 6
    assert g["review_unit_reduction"] == round((25 - 5) / 25, 4)   # 0.8
    assert g["reach_active_time_reduction"] == round((75 - 6) / 75, 4)  # 0.92


# --- ground-truth requirement ------------------------------------------------


def test_eval_requires_ground_truth(tmp_path):
    missing = tmp_path / "nope.yaml"
    with pytest.raises(FileNotFoundError):
        load_ground_truth(str(missing))
    with pytest.raises(FileNotFoundError):
        evaluate(gt_path=str(missing))


# --- full eval on the mock ---------------------------------------------------


def test_full_eval_hits_expected_ceilings():
    res = evaluate()
    assert res["pass"] is True
    assert res["correlation"]["precision"] == 1.0
    assert res["correlation"]["recall"] == 1.0
    assert res["active_compromise"]["fp"] == 0
    assert res["active_compromise"]["fn"] == 0
    # three active suppliers now (sup-h is the multi-tier terminal); order within
    # the active band is not pinned, but the top-k must be EXACTLY the active set.
    assert set(res["ranking"]["top_k_ids"]) == {"sup-a", "sup-g", "sup-h"}
    assert res["ranking"]["top_k_is_exactly_active"] is True
    assert res["ranking"]["strictly_on_top"] is True
    # golden time is a real reduction, computed (not asserted-as-magic)
    assert res["golden_time"]["full_triage_time_reduction"] > 0


def test_eval_run_green_and_json_masked():
    from adapter.mock import MockExposureSource

    assert run() == 0
    from scripts.p6_eval import OUT_JSON

    with open(OUT_JSON, encoding="utf-8") as fh:
        blob = fh.read()
    json.loads(blob)   # valid JSON
    leaked = [s for s in MockExposureSource().raw_secrets() if s in blob]
    assert leaked == [], f"raw secret in eval.json: {leaked}"
