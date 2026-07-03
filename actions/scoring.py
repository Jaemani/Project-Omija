"""Risk scoring — single source of truth for weights, thresholds, and formula.

architecture.md §3 / ontology.md §4. The score is intentionally EXPLAINABLE and
ACTIVE-COMPROMISE DOMINANT:

    base = Σ( exposure_scale[dedup], recency_decay, secret_type_weight,
              module_confidence + source_diversity )
    base_score = clamp( base × criticality_mult × tier_mult , 0 .. BASE_CAP )

    if active-compromise path exists (FlagActiveCompromise opened an incident):
        score lands in the ACTIVE BAND [active_floor .. 100], strictly above any
        non-active supplier — this is what guarantees active triage sits on top
        (the project's core differentiator). Within the band, suppliers are
        ordered by base quality + device recency.
    else:
        score = base_score  (0 .. BASE_CAP)

Every contribution is returned as a `components` breakdown for provenance/UX.

Weights live ONLY here (decision 5). Tests pin the guarantees (active > any
non-active; grade thresholds; dedup counting), not the exact magic numbers.
"""

from __future__ import annotations

from typing import Any

from adapter.base import CONFIDENCE

# --- transparent configuration (the ONE place weights are defined) -----------
SCORING: dict[str, Any] = {
    # base components — each capped so `base_subtotal` stays bounded
    "exposure_scale": {"points_per_unit": 3.0, "cap": 15.0},        # dedup'd count
    "recency": {"max_points": 15.0, "half_life_days": 30.0},        # freshest signal
    "secret_type": {
        # plaintext / live cookie / token are the operative (usable) secrets → high
        "weights": {"cookie": 1.0, "token": 1.0, "plaintext": 0.9,
                    "hash": 0.4, None: 0.2},
        "max_points": 12.0,
    },
    "module_confidence": {
        "confidence": dict(CONFIDENCE),                             # cds/ub .9 > cl .6 > cb .3
        "max_points": 8.0,
        "diversity_bonus_per_extra_module": 1.5,                   # source diversity ⇒ trust
        "cap": 12.0,
    },
    # non-active suppliers are clamped into [0, base_cap]; active ones sit above
    "base_cap": 60.0,
    "criticality_multiplier": {3: 1.15, 2: 1.05, 1: 1.00},         # high / med / low
    "tier_multiplier": {1: 1.08, 2: 1.00},                         # tier-1 amplifies
    # active-compromise band [active_floor .. active_ceiling]
    "active_floor": 70.0,
    "active_ceiling": 100.0,
    "active_base_ref": 80.0,      # normalizer for base quality inside the active band
    # grades (ontology.md §4: 즉시 / 주의 / 관찰)
    "grade_thresholds": {"즉시": 70.0, "주의": 40.0},               # else 관찰
    "day_seconds": 86400,
}

_CRIT_MAP = {"high": 3, "medium": 2, "low": 1, "3": 3, "2": 2, "1": 1}


def _crit_level(crit: Any) -> int:
    if isinstance(crit, bool):        # guard: bool is an int subclass
        return 1
    if isinstance(crit, int):
        return crit
    if crit is None:
        return 1
    return _CRIT_MAP.get(str(crit).strip().lower(), 2)


def grade_for(score: float, config: dict = SCORING) -> str:
    th = config["grade_thresholds"]
    if score >= th["즉시"]:
        return "즉시"
    if score >= th["주의"]:
        return "주의"
    return "관찰"


# --- dedup (decision 3) ------------------------------------------------------

def dedup_key(row: dict) -> tuple:
    """Recirculation key: same (identity, host, secret_type) across modules is
    the *same* leaked credential re-traded — counted once for exposure scale."""
    ident = row.get("identity_ref") or row.get("email") or row.get("username")
    return (ident, row.get("host"), row.get("secret_type"))


def dedup_exposures(rows: list[dict]) -> dict:
    """Collapse recirculated duplicates for exposure-scale counting. Provenance
    (all raw rows) is preserved by the caller; only the *count* is deduped.
    Source diversity (distinct modules) is kept as a confidence signal."""
    groups: dict[tuple, list[dict]] = {}
    for r in rows:
        groups.setdefault(dedup_key(r), []).append(r)
    modules = sorted({r.get("module") for r in rows if r.get("module")})
    return {
        "dedup_count": len(groups),
        "raw_count": len(rows),
        "modules": modules,
        "groups": groups,
    }


def _recency_points(age_days: float, rc_cfg: dict) -> float:
    decay = 0.5 ** (max(0.0, age_days) / rc_cfg["half_life_days"])
    return rc_cfg["max_points"] * decay


def score_supplier(
    exposures: list[dict], *, supplier: dict, active_flag: bool, now: int,
    active_age_days: float | None = None, config: dict = SCORING,
) -> tuple[float, str, dict]:
    """Return (score 0..100, grade, components-breakdown) for one supplier.

    `active_flag` MUST come from FlagActiveCompromise (a path/incident exists),
    not from a heuristic here — this function only weights it."""
    cfg = config
    dd = dedup_exposures(exposures)

    # 1) exposure scale (deduped)
    es = cfg["exposure_scale"]
    scale_pts = min(es["cap"], dd["dedup_count"] * es["points_per_unit"])

    # 2) recency of the freshest signal
    rc = cfg["recency"]
    freshest = None
    for r in exposures:
        ts = r.get("infected_at") or r.get("observed_at")
        if ts:
            freshest = int(ts) if freshest is None else max(freshest, int(ts))
    if freshest is None:
        age_days, recency_pts = 9999.0, 0.0
    else:
        age_days = max(0.0, (now - freshest) / cfg["day_seconds"])
        recency_pts = _recency_points(age_days, rc)

    # 3) strongest secret type present
    st = cfg["secret_type"]
    weights = st["weights"]
    best_w, best_type = 0.0, None
    for r in exposures:
        w = weights.get(r.get("secret_type"), weights.get(None, 0.2))
        if w > best_w:
            best_w, best_type = w, r.get("secret_type")
    secret_pts = st["max_points"] * best_w

    # 4) module confidence + source diversity
    mc = cfg["module_confidence"]
    conf = mc["confidence"]
    max_conf = max((conf.get(m, 0.3) for m in dd["modules"]), default=0.0)
    diversity_extra = max(0, len(dd["modules"]) - 1) * mc["diversity_bonus_per_extra_module"]
    module_pts = min(mc["cap"], mc["max_points"] * max_conf + diversity_extra)

    base_subtotal = scale_pts + recency_pts + secret_pts + module_pts

    crit_mult = cfg["criticality_multiplier"].get(_crit_level(supplier.get("criticality")), 1.0)
    tier_mult = cfg["tier_multiplier"].get(supplier.get("tier"), 1.0)
    multiplier = crit_mult * tier_mult
    raw_base = base_subtotal * multiplier
    base_score = min(cfg["base_cap"], raw_base)

    if active_flag:
        floor, ceil = cfg["active_floor"], cfg["active_ceiling"]
        base_q = min(1.0, raw_base / cfg["active_base_ref"])
        rec_age = age_days if active_age_days is None else active_age_days
        rec_q = _recency_points(rec_age, rc) / rc["max_points"]
        quality = 0.5 * base_q + 0.5 * rec_q
        score = floor + (ceil - floor) * quality
    else:
        quality = None
        score = base_score

    score = round(max(0.0, min(cfg["active_ceiling"], score)), 2)
    grade = grade_for(score, cfg)

    components = {
        "exposure_scale": {"dedup_count": dd["dedup_count"], "raw_count": dd["raw_count"],
                           "points": round(scale_pts, 2)},
        "recency": {"age_days": round(age_days, 1), "points": round(recency_pts, 2)},
        "secret_type": {"strongest": best_type, "weight": best_w,
                        "points": round(secret_pts, 2)},
        "module_confidence": {"modules": dd["modules"], "max_conf": max_conf,
                              "diversity": len(dd["modules"]), "points": round(module_pts, 2)},
        "base_subtotal": round(base_subtotal, 2),
        "criticality_multiplier": round(crit_mult, 3),
        "tier_multiplier": round(tier_mult, 3),
        "base_score": round(base_score, 2),
        "active_flag": bool(active_flag),
        "active_quality": None if quality is None else round(quality, 3),
        "score": score,
        "grade": grade,
    }
    return score, grade, components
