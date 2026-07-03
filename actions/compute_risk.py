"""ComputeRisk action (ontology.md §3, architecture.md §3).

Builds a RiskAssessment for a supplier from its correlated exposures, using the
transparent weights in `actions.scoring`. Two ontology rules are enforced here:

  * provenance is MANDATORY — `evidenced_by` must be non-empty or the action is
    REFUSED (`EvidenceRequired` raised). No score may exist without the original
    records backing it (ontology.md §3, CLAUDE.md §5). A supplier with no
    correlated exposures therefore gets no RiskAssessment at all.
  * active-compromise state is NOT guessed — it is read from whether
    FlagActiveCompromise has opened a CompromiseIncident for the supplier (path
    existence). ComputeRisk only *weights* that flag.

The full component breakdown (from `score_supplier`) is stored for
explainability, and every evidenced_by ref traces back to an Exposure/Device.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from actions.scoring import SCORING, score_supplier


class EvidenceRequired(Exception):
    """ComputeRisk refused: evidenced_by would be empty (provenance mandatory)."""


@dataclass
class RiskAssessment:
    id: str
    supplier_ref: str
    score: float
    grade: str
    active_flag: bool
    computed_at: int
    components: dict
    evidenced_by: list = field(default_factory=list)   # list[(ref, kind)]


def _supplier(store: Any, supplier_id: str) -> dict:
    for s in store.suppliers():
        if s["id"] == supplier_id:
            return s
    raise ValueError(f"unknown supplier: {supplier_id}")


def _evidence(exposures: list[dict]) -> list[tuple[str, str]]:
    """evidenced_by = every backing Exposure, plus the InfectedDevice for any
    exposure that carries a stealer signal. Ordered + de-duplicated."""
    ev: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def add(ref: str, kind: str) -> None:
        key = (ref, kind)
        if ref and key not in seen:
            seen.add(key)
            ev.append(key)

    for r in exposures:
        add(r["id"], "exposure")
    for r in exposures:
        if r.get("infected_at") is not None:
            add(f"dev:{r['source_ref']}", "device")
    return ev


def compute_risk(
    store: Any, supplier_id: str, *, now: int | None = None, config: dict = SCORING,
) -> RiskAssessment:
    """Compute + persist a RiskAssessment for one supplier. Raises
    `EvidenceRequired` if the supplier has no exposures to cite."""
    now = int(time.time()) if now is None else now
    supplier = _supplier(store, supplier_id)
    exposures = store.exposures_for_supplier(supplier_id)

    evidence = _evidence(exposures)
    if not evidence:
        raise EvidenceRequired(
            f"ComputeRisk refused for {supplier_id!r}: evidenced_by is empty — "
            "no score without provenance (ontology.md §3)."
        )

    # active-compromise flag comes from FlagActiveCompromise (a path/incident)
    active_flag = bool(store.incidents_for_supplier(supplier_id))
    active_age_days = None
    if active_flag:
        active_ts = [
            int(r["infected_at"]) for r in exposures
            if r.get("infected_at") and r.get("has_session_cookie")
            and r.get("account_type") in {"vpn", "admin"}
        ]
        if active_ts:
            active_age_days = max(0.0, (now - max(active_ts)) / config["day_seconds"])

    score, grade, components = score_supplier(
        exposures, supplier=supplier, active_flag=active_flag,
        active_age_days=active_age_days, now=now, config=config,
    )

    rid = f"risk:{supplier_id}"
    store.record_risk_assessment(
        id=rid, supplier_ref=supplier_id, score=score, grade=grade,
        active_flag=active_flag, computed_at=now, components=components,
        evidence=evidence,
    )
    return RiskAssessment(
        id=rid, supplier_ref=supplier_id, score=score, grade=grade,
        active_flag=active_flag, computed_at=now, components=components,
        evidenced_by=evidence,
    )


def compute_all(
    store: Any, *, now: int | None = None, config: dict = SCORING,
) -> list[RiskAssessment]:
    """ComputeRisk for every supplier that has evidence (exposed suppliers).
    Clean suppliers are skipped (they would be refused for lack of provenance)."""
    now = int(time.time()) if now is None else now
    out: list[RiskAssessment] = []
    for sup in store.suppliers():
        try:
            out.append(compute_risk(store, sup["id"], now=now, config=config))
        except EvidenceRequired:
            continue     # no exposures → no assessment (provenance rule)
    out.sort(key=lambda a: a.score, reverse=True)
    return out
