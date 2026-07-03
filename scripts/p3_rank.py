"""P3 ranking pipeline — the project's core differentiator, end to end.

Runs the full pipe on the mock corpus (no network, no secrets):

    registry → mock ingest → normalize → CorrelateExposure
             → EntityResolver (propose merges — pending human review)
             → FlagActiveCompromise (Device→…→Program path ⇒ CompromiseIncident)
             → ComputeRisk (active-weighted, evidence-enforced)

then prints a supplier RISK RANKING (score · grade · active flag · freshest
signal · evidence count) and the traversed path of every CompromiseIncident as a
`Device → … → Program` chain.

The RESULT check asserts the core property: every supplier with an active
compromise ranks strictly above every non-active supplier.

Run: `uv run python scripts/p3_rank.py`
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

# Repo root on path (script may be run directly).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from actions.compute_risk import compute_all                       # noqa: E402
from actions.entity_resolver import propose_merges                 # noqa: E402
from actions.flag_active import flag_active_compromises, path_chain  # noqa: E402
from adapter.mock import DEMO_NOW                                   # noqa: E402
from scripts.p1_report import build_store                          # noqa: E402

_CRIT_LABEL = {3: "high", 2: "medium", 1: "low"}


def _fmt_ts(ts) -> str:
    if not ts:
        return "—"
    return datetime.fromtimestamp(int(ts), timezone.utc).strftime("%Y-%m-%d")


def run() -> int:
    # 1-3) registry → mock → normalize → correlate (reused P1 slice)
    store, corr, written = build_store()
    now = DEMO_NOW

    # 4) EntityResolver — propose Identity merges (human-on-the-loop, no auto-merge)
    resolution = propose_merges(store, now=now)

    # 5) FlagActiveCompromise — open incidents where a full path exists
    flags = flag_active_compromises(store, now=now)

    # 6) ComputeRisk — active-weighted, evidence-enforced, for exposed suppliers
    assessments = compute_all(store, now=now)

    sup_by_id = {s["id"]: s for s in store.suppliers()}

    print("=" * 78)
    print("P3 RISK RANKING — active-compromise-weighted supply-chain triage")
    print(f"anchor DEMO_NOW = {_fmt_ts(now)} UTC · "
          f"records={written} · {corr.summary()}")
    print("=" * 78)

    # -- merge proposals (pending human review) -------------------------------
    print(f"\nEntityResolver: {resolution.summary()}")
    for p in resolution.proposals:
        print(f"  [pending] {p.identity_b}  →merge into→  {p.identity_a}")
        print(f"            basis: {p.basis}")

    # -- ranking table --------------------------------------------------------
    print(f"\n{'#':<3}{'supplier':<20}{'tier':<6}{'crit':<8}"
          f"{'score':>7}  {'grade':<6}{'active':<8}{'fresh':<12}{'ev':>4}")
    print("-" * 78)
    for i, a in enumerate(assessments, 1):
        sup = sup_by_id.get(a.supplier_ref, {})
        crit = _CRIT_LABEL.get(sup.get("criticality"), str(sup.get("criticality")))
        fresh = a.components.get("recency", {}).get("age_days")
        fresh_txt = "—" if fresh is None else f"{fresh:.0f}d ago"
        active = "ACTIVE" if a.active_flag else "-"
        print(f"{i:<3}{sup.get('name', a.supplier_ref):<20}"
              f"T{sup.get('tier', '?'):<5}{crit:<8}"
              f"{a.score:>7.2f}  {a.grade:<6}{active:<8}{fresh_txt:<12}"
              f"{len(a.evidenced_by):>4}")

    # -- incident paths (Device → … → Program) --------------------------------
    incidents = store.incidents()
    print(f"\nActive-compromise incidents: {flags.summary()}")
    for inc in incidents:
        sup = sup_by_id.get(inc["supplier_ref"], {})
        print(f"\n  Incident {inc['id']}  ({sup.get('name', inc['supplier_ref'])}, "
              f"status={inc['status']}, opened={_fmt_ts(inc['opened_at'])})")
        print(f"    {path_chain(inc['path'])}")

    # -- top-component breakdown for the #1 supplier --------------------------
    if assessments:
        top = assessments[0]
        print(f"\nTop supplier score breakdown ({top.supplier_ref}):")
        for k in ("exposure_scale", "recency", "secret_type", "module_confidence"):
            c = top.components.get(k, {})
            print(f"    {k:<18} {c}")
        print(f"    base_score={top.components.get('base_score')} · "
              f"active={top.components.get('active_flag')} · "
              f"quality={top.components.get('active_quality')} · "
              f"score={top.score} ({top.grade})")

    # -- RESULT: active suppliers must rank above every non-active one ---------
    active_scores = [a.score for a in assessments if a.active_flag]
    nonactive_scores = [a.score for a in assessments if not a.active_flag]
    active_on_top = (
        bool(active_scores)
        and (not nonactive_scores or min(active_scores) > max(nonactive_scores))
    )
    every_assessment_has_evidence = all(a.evidenced_by for a in assessments)
    incidents_ok = len(incidents) == len(flags.incidents)

    print("\n" + "=" * 78)
    print(f"active suppliers          : {len(active_scores)}  "
          f"(min active score {min(active_scores):.2f})" if active_scores else
          "active suppliers          : 0")
    print(f"non-active suppliers      : {len(nonactive_scores)}"
          + (f"  (max non-active score {max(nonactive_scores):.2f})"
             if nonactive_scores else ""))
    print(f"active-on-top             : {active_on_top}")
    print(f"every score has evidence  : {every_assessment_has_evidence}")
    print(f"incidents opened          : {len(incidents)}")
    print("=" * 78)

    ok = (written > 0 and assessments and active_on_top
          and every_assessment_has_evidence and incidents_ok
          and len(incidents) > 0)
    print("RESULT:", "OK" if ok else "FAIL")
    store.close()
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(run())
