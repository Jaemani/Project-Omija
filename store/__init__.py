"""Local validation ontology store.

AIP (Foundry Ontology + OSDK) is the SPINE; this package is a validation /
insurance store only. It mirrors the ontology schema (Supplier, Domain,
Identity, CredentialExposure, InfectedDevice, ThreatSource) behind an
`OntologyStore` Protocol so a Foundry/OSDK implementation can hot-swap in —
same pattern as the adapters. See ADR-0003.
"""

from .base import OntologyStore
from .sqlite import SqliteOntologyStore

__all__ = ["OntologyStore", "SqliteOntologyStore"]
