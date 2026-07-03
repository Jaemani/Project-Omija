"""P5: defensive notification DRAFTS for the top-ranked suppliers.

Runs the full mock pipe (registry → ingest → normalize → correlate → resolve →
FlagActiveCompromise → ComputeRisk), then GenerateNotificationDraft for the top
suppliers (active-compromise suppliers sit on top, so they are always covered).
Each draft is written to `out/drafts/<supplier_id>.md` and summarized on the CLI.

Guardrails (CLAUDE.md): drafts are GENERATED ONLY — there is no send path. Every
draft cites its backing records (empty cites ⇒ the action refuses). Secrets are
masked. Data is synthetic (`*.example`).

Run: `uv run python scripts/p5_drafts.py`
"""

from __future__ import annotations

import os
import sys

# Repo root on path (script may be run directly).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from actions.compute_risk import compute_all                       # noqa: E402
from actions.entity_resolver import propose_merges                 # noqa: E402
from actions.flag_active import flag_active_compromises            # noqa: E402
from actions.notify_draft import generate_drafts                   # noqa: E402
from adapter.mock import DEMO_NOW                                   # noqa: E402
from scripts.p1_report import build_store                          # noqa: E402

TOP_N = 3

OUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out"
)
DRAFTS_DIR = os.path.join(OUT_DIR, "drafts")


def build_pipeline(now: int = DEMO_NOW):
    """registry → mock → normalize → correlate → resolve → flag → score.
    Returns (store, assessments) with all derived objects persisted."""
    store, _corr, _written = build_store()
    propose_merges(store, now=now)
    flag_active_compromises(store, now=now)
    assessments = compute_all(store, now=now)
    return store, assessments


def run() -> int:
    now = DEMO_NOW
    store, assessments = build_pipeline(now)
    drafts = generate_drafts(store, assessments, top=TOP_N, now=now)

    os.makedirs(DRAFTS_DIR, exist_ok=True)
    sup_by_id = {s["id"]: s for s in store.suppliers()}

    print("=" * 74)
    print("P5 GenerateNotificationDraft — defensive early-warning drafts")
    print("draft only · no send capability · masked · synthetic domains")
    print("=" * 74)

    written_paths: list[str] = []
    for d in drafts:
        path = os.path.join(DRAFTS_DIR, f"{d.supplier_ref}.md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(d.body)
        written_paths.append(path)
        sup = sup_by_id.get(d.supplier_ref, {})
        active = bool(store.incidents_for_supplier(d.supplier_ref))
        print(
            f"  {sup.get('name', d.supplier_ref):<20} status={d.status:<6} "
            f"active={'YES' if active else '-':<4} cites={len(d.evidence_refs):<3} "
            f"→ {os.path.relpath(path, OUT_DIR)}"
        )

    # RESULT invariants: drafts generated, every draft cites evidence, status is
    # 'draft' (never sent), and no draft leaks a raw secret.
    from adapter.mock import MockExposureSource
    raw_secrets = MockExposureSource().raw_secrets()
    all_draft = all(d.status == "draft" for d in drafts)
    all_cited = all(d.evidence_refs for d in drafts)
    no_secret = all(
        not any(s in d.body for s in raw_secrets) for d in drafts
    )

    print("\n" + "=" * 74)
    print(f"drafts generated          : {len(drafts)}")
    print(f"every draft cites evidence : {all_cited}")
    print(f"all status == 'draft'      : {all_draft}")
    print(f"no raw secret in any draft  : {no_secret}")
    print("=" * 74)

    ok = bool(drafts) and all_cited and all_draft and no_secret
    print("RESULT:", "OK" if ok else "FAIL")
    store.close()
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(run())
