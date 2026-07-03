"""Ontology Actions (human-on-the-loop pipeline steps, ontology.md §3).

- `CorrelateExposure` (P1): attribute each Exposure to a Supplier by email-domain
  match, recording the match basis as provenance.
- `EntityResolver` (P2): propose Identity merges (rule-based, confirm-only).
- `ComputeRisk` (P3): active-weighted RiskAssessment (evidence enforced).
- `FlagActiveCompromise` (P3): open a CompromiseIncident when a full Device→…→
  Program path exists.

`GenerateNotificationDraft` lands in P5.
"""

from .compute_risk import EvidenceRequired, RiskAssessment, compute_all, compute_risk
from .correlate import CorrelationResult, correlate_exposures, match_domain
from .entity_resolver import (
    MergeProposal,
    ResolutionResult,
    confirm_merge,
    normalize_local_part,
    propose_merges,
)
from .flag_active import FlagResult, flag_active_compromises, path_chain
from .scoring import SCORING, dedup_exposures, grade_for, score_supplier

__all__ = [
    "CorrelationResult", "correlate_exposures", "match_domain",
    "MergeProposal", "ResolutionResult", "propose_merges", "confirm_merge",
    "normalize_local_part",
    "SCORING", "score_supplier", "grade_for", "dedup_exposures",
    "EvidenceRequired", "RiskAssessment", "compute_risk", "compute_all",
    "FlagResult", "flag_active_compromises", "path_chain",
]
