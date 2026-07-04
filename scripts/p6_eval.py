"""P6 evaluation — performance numbers for the supply-chain triage pipe.

Runs the full mock pipeline (registry -> ingest -> normalize -> correlate ->
resolve -> FlagActiveCompromise -> ComputeRisk) and grades it against a
HAND-AUTHORED ground truth (`eval/ground_truth.yaml`, derived from the mock
constants — never from pipeline output, so the pipe cannot grade itself).

Metrics (all deterministic):
  1. correlation precision/recall  — exposure -> supplier attribution accuracy.
  2. active-compromise precision/recall — FlagActiveCompromise vs truth, with the
     false-positive / false-negative counts named explicitly.
  3. ranking validity — are all active suppliers ranked strictly above every
     non-active one (top-k integrity)?
  4. golden-time (response speed) — bare record enumeration vs graph triage:
     how many items an analyst must review, converted to minutes.

Output: a CLI table + `out/eval.json`. Numbers are printed exactly as computed
(no rounding-up, no massaging). The synthetic/small/clean mock limitation is
printed alongside so the ceiling P/R values are read honestly.

Run: `uv run python scripts/p6_eval.py`
"""

from __future__ import annotations

import json
import os
import sys

# Repo root on path (script may be run directly).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yaml  # noqa: E402

from adapter.mock import DEMO_NOW  # noqa: E402
from scripts.p5_drafts import build_pipeline  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GROUND_TRUTH_PATH = os.path.join(REPO_ROOT, "eval", "ground_truth.yaml")
OUT_DIR = os.path.join(REPO_ROOT, "out")
OUT_JSON = os.path.join(OUT_DIR, "eval.json")

MOCK_LIMITATION = (
    "Mock corpus is SYNTHETIC (*.example), SMALL (8 suppliers / 30 records) and "
    "CLEAN (domains map 1:1, no adversarial records) — P/R here is a correctness "
    "ceiling proving the pipe is wired right, not a field-performance claim."
)


# ---------------------------------------------------------------------------
# ground truth
# ---------------------------------------------------------------------------


def load_ground_truth(path: str = GROUND_TRUTH_PATH) -> dict:
    """Load the hand-authored ground truth. Raises FileNotFoundError if the file
    is absent — the eval must never silently pass without a ground truth to
    grade against."""
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"ground truth not found: {path!r} — P6 eval requires a hand-authored "
            "eval/ground_truth.yaml (it cannot grade the pipe against itself)."
        )
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict) or "exposure_attribution" not in data:
        raise ValueError(f"ground truth {path!r} is malformed (missing keys)")
    return data


# ---------------------------------------------------------------------------
# pure metric functions (unit-tested on small synthetic inputs)
# ---------------------------------------------------------------------------


def prf_from_sets(predicted: set, truth: set) -> dict:
    """Precision / recall / F1 + TP/FP/FN for a set-membership prediction
    (used for active-compromise supplier detection).

    Empty-denominator convention: precision is 1.0 when nothing was predicted,
    recall is 1.0 when there was nothing to find — so a correct "no positives"
    call scores 1.0 rather than 0/0."""
    predicted, truth = set(predicted), set(truth)
    tp = len(predicted & truth)
    fp = len(predicted - truth)
    fn = len(truth - predicted)
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = (2 * precision * recall / (precision + recall)
          if (precision + recall) else 0.0)
    return {
        "tp": tp, "fp": fp, "fn": fn,
        "precision": round(precision, 4), "recall": round(recall, 4),
        "f1": round(f1, 4),
        "false_positives": sorted(predicted - truth),
        "false_negatives": sorted(truth - predicted),
    }


def attribution_metrics(pred_map: dict, truth_map: dict) -> dict:
    """Correlation precision/recall for per-exposure attribution.

    `pred_map`  : {exposure_ref -> predicted supplier_id | None (unmatched)}
    `truth_map` : {exposure_ref -> true supplier_id}

    precision = correctly-attributed / attributed-to-any-supplier
    recall    = correctly-attributed / all-truth-exposures

    Also surfaces coverage gaps (exposures in one map but not the other) so a
    silent drop cannot be hidden behind a clean P/R."""
    attributed = [k for k, v in pred_map.items() if v is not None]
    correct = [k for k in attributed if pred_map[k] == truth_map.get(k)]
    misattributed = [k for k in attributed if pred_map[k] != truth_map.get(k)]
    total_truth = len(truth_map)
    unmatched = [k for k, v in pred_map.items() if v is None]

    precision = len(correct) / len(attributed) if attributed else 1.0
    recall = len(correct) / total_truth if total_truth else 1.0
    f1 = (2 * precision * recall / (precision + recall)
          if (precision + recall) else 0.0)

    missing_from_pred = sorted(set(truth_map) - set(pred_map))
    extra_in_pred = sorted(set(pred_map) - set(truth_map))
    return {
        "total_truth": total_truth,
        "attributed": len(attributed),
        "correct": len(correct),
        "misattributed": len(misattributed),
        "unmatched": len(unmatched),
        "precision": round(precision, 4), "recall": round(recall, 4),
        "f1": round(f1, 4),
        "misattributed_refs": sorted(misattributed),
        "coverage_missing_from_pipeline": missing_from_pred,
        "coverage_extra_in_pipeline": extra_in_pred,
    }


def ranking_validity(ranked_ids: list, active_ids: set) -> dict:
    """Top-k integrity: with k = |active|, the top-k ranked suppliers must be
    EXACTLY the active set (active-on-top invariant). `ranked_ids` is the
    supplier ordering, best first."""
    active_ids = set(active_ids)
    k = len(active_ids)
    top_k = ranked_ids[:k]
    active_positions = {sid: (ranked_ids.index(sid) + 1)
                        for sid in active_ids if sid in ranked_ids}
    active_all_present = all(sid in ranked_ids for sid in active_ids)
    top_k_is_active = set(top_k) == active_ids
    # rank at which BOTH (all) active suppliers have been reached, 1-indexed.
    reach_all_active_rank = max(active_positions.values()) if active_positions else 0
    return {
        "k": k,
        "top_k_ids": top_k,
        "top_k_is_exactly_active": top_k_is_active and active_all_present,
        "active_positions": active_positions,
        "reach_all_active_rank": reach_all_active_rank,
    }


def golden_time(
    *, baseline_units: int, our_units_full: int, our_units_to_active: int,
    minutes_per_item: float,
) -> dict:
    """Convert review-item counts to analyst wall-clock and the reductions.

    baseline_units      : records an analyst reviews in the bare enumeration.
    our_units_full      : ranked supplier cards for a full supply-chain triage.
    our_units_to_active : ranked entries to reach every active supplier (they
                          are provably on top, so this is small).
    """
    m = minutes_per_item
    base_min = baseline_units * m
    full_min = our_units_full * m
    active_min = our_units_to_active * m

    def pct(before: float, after: float) -> float:
        return round((before - after) / before, 4) if before else 0.0

    return {
        "minutes_per_item": m,
        "baseline_units": baseline_units,
        "our_units_full_triage": our_units_full,
        "our_units_to_reach_active": our_units_to_active,
        "baseline_minutes": round(base_min, 2),
        "our_full_triage_minutes": round(full_min, 2),
        "our_reach_active_minutes": round(active_min, 2),
        "review_unit_reduction": pct(baseline_units, our_units_full),
        "full_triage_time_reduction": pct(base_min, full_min),
        "reach_active_time_reduction": pct(base_min, active_min),
    }


# ---------------------------------------------------------------------------
# evaluation (pipeline -> metrics)
# ---------------------------------------------------------------------------


def _recency_first_contact_position(exposures: list, active_ids: set) -> int:
    """Transparency figure: if a BARE list were sorted observed_at-desc, at what
    position would an analyst have contacted the active-signal record (cds with a
    live cookie on a vpn/admin account) for EVERY active supplier? Reported so we
    never overstate a recency advantage (in this fixture the active infections
    are also the freshest records)."""
    ordered = sorted(
        exposures,
        key=lambda r: (r.get("observed_at") or 0, r.get("source_ref") or ""),
        reverse=True,
    )
    still_needed = set(active_ids)
    for i, r in enumerate(ordered, 1):
        is_active_signal = (
            bool(r.get("has_session_cookie"))
            and r.get("account_type") in {"vpn", "admin"}
            and r.get("infected_at") is not None
        )
        if is_active_signal and r.get("supplier_id") in still_needed:
            still_needed.discard(r.get("supplier_id"))
        if not still_needed:
            return i
    return len(ordered)  # never fully reached


def evaluate(now: int = DEMO_NOW, gt_path: str = GROUND_TRUTH_PATH) -> dict:
    """Run the pipe and grade it. Returns the full metrics dict (also the body
    of out/eval.json)."""
    gt = load_ground_truth(gt_path)
    truth_active = set(gt["active_suppliers"])
    truth_clean = set(gt["clean_suppliers"])
    minutes_per_item = float(gt.get("minutes_per_review_item", 3))

    # flatten hand-authored attribution: source_ref -> true supplier
    truth_attr: dict[str, str] = {}
    for supplier_id, refs in gt["exposure_attribution"].items():
        for ref in refs:
            truth_attr[ref] = supplier_id

    store, assessments = build_pipeline(now)
    try:
        exposures = store.all_exposures()

        # --- 1) correlation attribution -------------------------------------
        # Exposure `id` is "exp:<source_ref>"; ground truth keys are source_refs.
        pred_attr = {r["source_ref"]: r.get("supplier_id") for r in exposures}
        correlation = attribution_metrics(pred_attr, truth_attr)

        # --- 2) active-compromise detection ---------------------------------
        predicted_active = {inc["supplier_ref"] for inc in store.incidents()}
        active = prf_from_sets(predicted_active, truth_active)

        # --- 3) ranking validity --------------------------------------------
        ranked_ids = [a.supplier_ref for a in assessments]  # already score-desc
        ranking = ranking_validity(ranked_ids, truth_active)
        # strict numeric check: min active score > max non-active score
        active_scores = [a.score for a in assessments if a.active_flag]
        nonactive_scores = [a.score for a in assessments if not a.active_flag]
        strictly_on_top = bool(active_scores) and (
            not nonactive_scores or min(active_scores) > max(nonactive_scores)
        )
        ranking["strictly_on_top"] = strictly_on_top
        ranking["min_active_score"] = min(active_scores) if active_scores else None
        ranking["max_nonactive_score"] = (
            max(nonactive_scores) if nonactive_scores else None
        )

        # --- 4) golden time --------------------------------------------------
        # baseline: bare record enumeration -> analyst reviews every record.
        baseline_units = len(exposures)
        # ours: one card per exposed (assessed) supplier; active provably on top.
        our_units_full = len(assessments)
        our_units_to_active = ranking["reach_all_active_rank"]
        gt_time = golden_time(
            baseline_units=baseline_units,
            our_units_full=our_units_full,
            our_units_to_active=our_units_to_active,
            minutes_per_item=minutes_per_item,
        )
        gt_time["recency_first_contact_position"] = _recency_first_contact_position(
            exposures, truth_active
        )
        # dedup advantage (recirculated combos counted once for scale)
        gt_time["records_ingested"] = len(exposures)
        gt_time["exposed_suppliers"] = len(assessments)

        result = {
            "anchor_now": now,
            "corpus": {
                "records": len(exposures),
                "suppliers_total": len(store.suppliers()),
                "suppliers_exposed": len(assessments),
                "suppliers_clean_expected": sorted(truth_clean),
            },
            "correlation": correlation,
            "active_compromise": active,
            "ranking": ranking,
            "golden_time": gt_time,
            "limitation": MOCK_LIMITATION,
            "pass": (
                correlation["precision"] == 1.0
                and correlation["recall"] == 1.0
                and correlation["coverage_missing_from_pipeline"] == []
                and active["fp"] == 0 and active["fn"] == 0
                and ranking["top_k_is_exactly_active"]
                and ranking["strictly_on_top"]
            ),
        }
        return result
    finally:
        store.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _fmt_pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def run() -> int:
    res = evaluate()

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2, ensure_ascii=False)

    c = res["correlation"]
    a = res["active_compromise"]
    r = res["ranking"]
    g = res["golden_time"]

    print("=" * 78)
    print("P6 EVALUATION — supply-chain credential-exposure triage")
    print(f"anchor now={res['anchor_now']} · records={res['corpus']['records']} · "
          f"suppliers={res['corpus']['suppliers_total']} "
          f"(exposed {res['corpus']['suppliers_exposed']})")
    print("=" * 78)

    print("\n[1] Correlation  (exposure -> supplier attribution)")
    print(f"    precision {_fmt_pct(c['precision'])}  recall {_fmt_pct(c['recall'])}"
          f"  f1 {_fmt_pct(c['f1'])}")
    print(f"    attributed {c['attributed']}/{c['total_truth']}  correct {c['correct']}"
          f"  misattributed {c['misattributed']}  unmatched {c['unmatched']}")
    if c["coverage_missing_from_pipeline"] or c["coverage_extra_in_pipeline"]:
        print(f"    !! coverage gap: missing {c['coverage_missing_from_pipeline']} "
              f"extra {c['coverage_extra_in_pipeline']}")

    print("\n[2] Active-compromise detection  (FlagActiveCompromise vs truth)")
    print(f"    precision {_fmt_pct(a['precision'])}  recall {_fmt_pct(a['recall'])}"
          f"  f1 {_fmt_pct(a['f1'])}")
    print(f"    TP {a['tp']}  FP {a['fp']}  FN {a['fn']}"
          f"   FP={a['false_positives'] or '-'}  FN={a['false_negatives'] or '-'}")

    print("\n[3] Ranking validity  (active-on-top / top-k integrity)")
    print(f"    k={r['k']}  top-{r['k']} = {r['top_k_ids']}")
    print(f"    top-k is exactly the active set : {r['top_k_is_exactly_active']}")
    print(f"    strictly on top (min active {r['min_active_score']} > "
          f"max non-active {r['max_nonactive_score']}) : {r['strictly_on_top']}")
    print(f"    active supplier ranks           : {r['active_positions']}")

    print("\n[4] Golden-time  (bare record enumeration vs graph triage)")
    print(f"    assumption: {g['minutes_per_item']} min analyst review per item")
    print(f"    baseline (bare records)  : {g['baseline_units']} records "
          f"= {g['baseline_minutes']:.0f} min  (no active-flag / no dedup / no ranking)")
    print(f"    ours (full triage)       : {g['our_units_full_triage']} suppliers "
          f"= {g['our_full_triage_minutes']:.0f} min  "
          f"(review units -{_fmt_pct(g['review_unit_reduction'])}, "
          f"time -{_fmt_pct(g['full_triage_time_reduction'])})")
    print(f"    ours (reach both active) : {g['our_units_to_reach_active']} entries "
          f"= {g['our_reach_active_minutes']:.0f} min  "
          f"(active provably ranked 1..{g['our_units_to_reach_active']}, "
          f"time -{_fmt_pct(g['reach_active_time_reduction'])})")
    print(f"    transparency: recency-sorted bare list would first-contact both "
          f"active signals at position {g['recency_first_contact_position']} —")
    print("      but a bare list has NO computed active-flag, so an analyst can't "
          "know to stop there; the")
    print("      win is pre-computed, evidence-backed, provably-top-ranked triage "
          "+ dedup/aggregation, not recency.")

    print("\n" + "-" * 78)
    print(f"LIMITATION: {res['limitation']}")
    print("-" * 78)
    print(f"eval.json written        : {OUT_JSON}")
    print("=" * 78)
    print("RESULT:", "OK" if res["pass"] else "FAIL")
    return 0 if res["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(run())
