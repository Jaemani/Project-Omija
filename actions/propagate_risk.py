"""PropagateRisk action → ProgramExposure (ontology.md §1, §2, §4).

Supplier-level RiskAssessments are only ATTRIBUTION. This action is where risk
PROPAGATES up the multi-tier supply chain and rolls up onto a defense
**Program**, answering the question a flat table cannot: *which program is
burning right now, and through which supplier chain?*

For every Program, gather EVERY supplier path that reaches it (via the
variable-depth recursive traverse `store.propagation_paths`, which follows
subcontracts 2차→1차→… then supplies→runs), then aggregate the contributing
suppliers' RiskAssessments into a ProgramExposure:

  * active_flag = a reaching path exists from a supplier with an open
    CompromiseIncident (PATH EXISTENCE — never guessed). One 2차 terminal
    infection two tiers down is enough to light the Program.
  * score = dominant contributing supplier score + breadth (distinct active
    reaching suppliers) × program sensitivity, normalized 0..100. Active
    programs occupy a band strictly above non-active ones (same active-on-top
    philosophy as `actions.scoring`).
  * evidenced_by is MANDATORY — the contributing CompromiseIncident +
    RiskAssessment refs. Empty ⇒ the ProgramExposure is REFUSED
    (`ProgramEvidenceRequired`), exactly like ComputeRisk's EvidenceRequired
    (ontology.md §3 provenance rule). A Program reached by zero exposed
    suppliers gets no ProgramExposure at all.
  * components carry the contribution breakdown (which supplier, which path is
    active, per-Prime subtotals) for explainability. No separate Prime derived
    object exists (scope discipline, ontology.md §5): a transited Prime/Supplier
    shows up only inside components + the incident path.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from actions.scoring import grade_for

# --- transparent configuration (the ONE place program-rollup weights live) ----
PROGRAM_SCORING: dict[str, Any] = {
    # sensitivity amplifies the margin above the active floor / the base score
    "sensitivity_multiplier": {"high": 1.2, "medium": 1.1, "low": 1.0, None: 1.0},
    # each ADDITIONAL distinct active reaching supplier adds breadth points
    "breadth_bonus_per_extra_active": 6.0,
    "breadth_cap": 18.0,
    # active programs sit in [active_floor .. active_ceiling], strictly above the
    # non-active band [0 .. base_cap] — guarantees burning programs on top.
    "active_floor": 70.0,
    "active_ceiling": 100.0,
    "base_cap": 60.0,
    # grade reuse (ontology.md §4: 즉시 / 주의 / 관찰)
    "grade_thresholds": {"즉시": 70.0, "주의": 40.0},
}


class ProgramEvidenceRequired(Exception):
    """PropagateRisk refused a ProgramExposure: evidenced_by would be empty
    (no contributing incident/assessment) — provenance is mandatory."""


@dataclass
class ProgramExposure:
    id: str
    program_ref: str
    score: float
    grade: str
    active_flag: bool
    computed_at: int
    components: dict
    contributing_paths: list = field(default_factory=list)
    evidenced_by: list = field(default_factory=list)   # list[(ref, kind)]


def _norm_sens(sensitivity: Any) -> str | None:
    if sensitivity is None:
        return None
    return str(sensitivity).strip().lower() or None


def _score_program(
    *, dominant: float, breadth_active: int, sensitivity: Any, active_flag: bool,
    cfg: dict,
) -> tuple[float, float, float]:
    """Return (score 0..100, breadth_points, sensitivity_multiplier).

    Active band: start from the dominant active supplier's score (already ≥ the
    supplier active floor), add breadth points, and let sensitivity amplify the
    margin above the floor; clamp into [active_floor, active_ceiling]. Non-active
    program: stay within [0, base_cap] (< active_floor) so no non-active program
    can ever outrank an active one."""
    sens_mult = cfg["sensitivity_multiplier"].get(_norm_sens(sensitivity), 1.0)
    if active_flag:
        floor, ceil = cfg["active_floor"], cfg["active_ceiling"]
        breadth_pts = min(
            cfg["breadth_cap"],
            max(0, breadth_active - 1) * cfg["breadth_bonus_per_extra_active"],
        )
        above_floor = max(0.0, dominant - floor) + breadth_pts
        score = floor + above_floor * sens_mult
        score = max(floor, min(ceil, score))
    else:
        breadth_pts = 0.0
        score = min(cfg["base_cap"], max(0.0, dominant) * sens_mult)
        score = max(0.0, min(cfg["base_cap"], score))
    return round(score, 2), round(breadth_pts, 2), sens_mult


def _chain_text(path: list[dict]) -> str:
    return " → ".join(f"{n['type']}({n.get('name') or n.get('ref')})" for n in path)


def _reach_map(store: Any) -> dict[str, list[dict]]:
    """program_id -> [{start, path, prime}] for every supplier path that reaches
    a Program (variable-depth recursive traverse over the whole registry)."""
    reach: dict[str, list[dict]] = {}
    for s in store.suppliers():
        sid = s["id"]
        for path in store.propagation_paths(sid):
            prog = path[-1]
            if prog.get("type") != "Program" or not prog.get("ref"):
                continue
            reach.setdefault(prog["ref"], []).append(
                {"start": sid, "path": path, "prime": path[-2].get("ref")}
            )
    return reach


def _build_program_exposure(
    store: Any, *, program: dict, entries: list[dict], assessments: dict,
    incidents: dict, now: int, config: dict,
) -> ProgramExposure:
    """Roll one Program's reaching paths into a ProgramExposure. Raises
    `ProgramEvidenceRequired` if no contributing incident/assessment exists."""
    pid = program["id"]
    # DEDUP by distinct Supplier — a diamond chain (X→Y and X→Z both reaching this
    # Program through a shared Prime) sends MULTIPLE paths here; breadth and
    # evidence must count the distinct SUPPLIER, never the path count (pin: no
    # shared-Prime / shared-Identity double-counting).
    starts = sorted({e["start"] for e in entries})
    contrib = {sid: assessments[sid] for sid in starts if sid in assessments}
    active_starts = sorted(sid for sid in starts if sid in incidents)
    active_flag = bool(active_starts)

    # evidenced_by: contributing incidents (active) + assessments (provenance),
    # deduped by underlying ref (one incident / one assessment per supplier — a
    # shared Prime does not multiply them).
    evidence: list[tuple[str, str]] = [
        (incidents[sid]["id"], "incident") for sid in active_starts
    ]
    evidence += [(contrib[sid]["id"], "assessment") for sid in sorted(contrib)]
    _seen_ev: set[str] = set()
    evidence = [(ref, kind) for ref, kind in evidence
                if not (ref in _seen_ev or _seen_ev.add(ref))]
    if not evidence:
        raise ProgramEvidenceRequired(
            f"PropagateRisk refused for program {pid!r}: no contributing "
            "incident/assessment — no ProgramExposure without provenance "
            "(ontology.md §3)."
        )

    # dominant = highest contributing supplier score; breadth = distinct active.
    dominant_sid, dominant_score = None, 0.0
    for sid in sorted(contrib):
        if contrib[sid]["score"] >= dominant_score:
            dominant_sid, dominant_score = sid, contrib[sid]["score"]
    breadth_active = len([sid for sid in active_starts if sid in contrib])

    score, breadth_pts, sens_mult = _score_program(
        dominant=dominant_score, breadth_active=breadth_active,
        sensitivity=program.get("sensitivity"), active_flag=active_flag, cfg=config,
    )
    grade = grade_for(score, config)

    # per-Prime subtotal (Prime contribution shown here, not as its own object).
    prime_sub: dict[str, dict] = {}
    for e in entries:
        pr = e["prime"]
        d = prime_sub.setdefault(pr, {"reached_by": set(), "max_score": 0.0, "active": False})
        d["reached_by"].add(e["start"])
        if e["start"] in incidents:
            d["active"] = True
        a = contrib.get(e["start"])
        if a:
            d["max_score"] = max(d["max_score"], a["score"])
    prime_subtotals = {
        pr: {"reached_by": sorted(v["reached_by"]),
             "max_score": round(v["max_score"], 2), "active": v["active"]}
        for pr, v in sorted(prime_sub.items())
    }

    # one entry per DISTINCT chain from a CONTRIBUTING (assessed) supplier — a
    # clean pure-conduit's direct path carries no risk and is not a contribution;
    # a diamond can also produce identical chains, listed once (explainability,
    # not a scoring input).
    contributing_paths = []
    _seen_chain: set[str] = set()
    for e in entries:
        if e["start"] not in contrib:
            continue
        chain = _chain_text(e["path"])
        if chain in _seen_chain:
            continue
        _seen_chain.add(chain)
        contributing_paths.append({
            "start": e["start"],
            "active": e["start"] in incidents,
            "multi_tier": len([n for n in e["path"] if n["type"] == "Supplier"]) > 1,
            "prime": e["prime"],
            "chain": chain,
        })

    components = {
        "program_ref": pid,
        "sensitivity": program.get("sensitivity"),
        "sensitivity_multiplier": sens_mult,
        "dominant_supplier": {"id": dominant_sid, "score": round(dominant_score, 2)},
        "contributing_suppliers": [
            {"id": sid, "score": round(contrib[sid]["score"], 2),
             "grade": contrib[sid]["grade"], "active": sid in incidents}
            for sid in sorted(contrib)
        ],
        "breadth_active": breadth_active,
        "breadth_points": breadth_pts,
        "prime_subtotals": prime_subtotals,
        "active_flag": active_flag,
        "score": score,
        "grade": grade,
    }

    peid = f"progexp:{pid}"
    store.record_program_exposure(
        id=peid, program_ref=pid, score=score, grade=grade, active_flag=active_flag,
        computed_at=now, components=components,
        contributing_paths=contributing_paths, evidence=evidence,
    )
    return ProgramExposure(
        id=peid, program_ref=pid, score=score, grade=grade, active_flag=active_flag,
        computed_at=now, components=components,
        contributing_paths=contributing_paths, evidenced_by=evidence,
    )


def propagate_program_risk(
    store: Any, *, now: int | None = None, config: dict = PROGRAM_SCORING,
) -> list[ProgramExposure]:
    """Roll supplier RiskAssessments UP onto every reachable Program. Programs
    with zero contributing exposed suppliers are refused (no ProgramExposure) —
    provenance is mandatory. Returns exposures sorted by score (burning on top)."""
    now = int(time.time()) if now is None else now
    reach = _reach_map(store)
    assessments = {a["supplier_ref"]: a for a in store.risk_assessments()}
    incidents = {inc["supplier_ref"]: inc for inc in store.incidents()}
    programs = {p["id"]: p for p in store.programs()}

    out: list[ProgramExposure] = []
    for pid, entries in reach.items():
        program = programs.get(pid, {"id": pid})
        try:
            out.append(_build_program_exposure(
                store, program=program, entries=entries, assessments=assessments,
                incidents=incidents, now=now, config=config,
            ))
        except ProgramEvidenceRequired:
            continue     # reached only by clean suppliers → no ProgramExposure
    out.sort(key=lambda pe: pe.score, reverse=True)
    return out
