"""Ontology Actions (human-on-the-loop pipeline steps, ontology.md §3).

P1 implements `CorrelateExposure`: attribute each Exposure to a Supplier by
matching the identity's email domain against registered supplier domains,
recording the match basis as provenance. Later actions (ComputeRisk,
FlagActiveCompromise, GenerateNotificationDraft) land in P3/P5.
"""

from .correlate import CorrelationResult, correlate_exposures, match_domain

__all__ = ["CorrelationResult", "correlate_exposures", "match_domain"]
