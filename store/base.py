"""OntologyStore Protocol — hot-swap seam for Foundry/OSDK.

The SPINE is Palantir AIP: Foundry Ontology holds the objects, OSDK reads them,
AIP Logic Actions (ComputeRisk / FlagActiveCompromise / GenerateNotificationDraft)
create derived objects. Foundry ontology creation + OSDK publishing are manual
console steps (see docs/runbooks/foundry-day1.md), so today's pipe is validated
against a local store implementing THIS interface. A future OSDK-backed
`FoundryOntologyStore` implements the same Protocol → one-line swap. See ADR-0003.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from adapter.base import Exposure


@runtime_checkable
class OntologyStore(Protocol):
    """Write/read ontology objects. Implementations: SQLite (today), OSDK (later)."""

    def init_schema(self) -> None:
        """Create the object/link schema if absent."""
        ...

    def upsert_supplier(
        self, *, id: str, name: str, tier: int, criticality: str
    ) -> None:
        """Supplier object (registry seed)."""
        ...

    def upsert_domain(self, *, fqdn: str, supplier_id: str) -> None:
        """Domain object + owns-link to its Supplier."""
        ...

    def upsert_prime(self, *, id: str, name: str) -> None:
        """Prime object (원청/주계약)."""
        ...

    def upsert_program(self, *, id: str, name: str, sensitivity: str | None = None) -> None:
        """Program object (방산 프로그램, 전파 최상단)."""
        ...

    def link_supplies(self, *, supplier_id: str, prime_id: str) -> None:
        """Supplier supplies Prime (N:M) — upward propagation edge."""
        ...

    def link_runs(self, *, prime_id: str, program_id: str) -> None:
        """Prime runs Program (N:M) — top of the propagation path."""
        ...

    def write_exposure(
        self, exp: Exposure, *, domain: str | None = None
    ) -> str:
        """Decompose an `Exposure` into ontology objects (Identity,
        CredentialExposure, InfectedDevice, ThreatSource) with links, resolving
        the Identity by email/username (entity resolution). Returns exposure id.
        Masking is already enforced upstream in `normalize()`; the store must
        never receive or persist a raw secret."""
        ...

    # -- CorrelateExposure support -----------------------------------------

    def registered_domains(self) -> dict[str, str]:
        """{fqdn: supplier_id} — the correlation key set."""
        ...

    def exposures_for_correlation(self) -> list[dict]:
        """(exposure_id, source_ref, identity_id, email) rows to correlate."""
        ...

    def attach_identity_domain(self, identity_id: str, domain_ref: str) -> None:
        """Set Identity belongs_to Domain (correlation result)."""
        ...

    def record_correlation(
        self, *, exposure_ref: str, identity_ref: str, domain_ref: str,
        supplier_id: str, match_basis: str, matched_at: int,
    ) -> None:
        """Persist the match basis (provenance) for a correlated Exposure."""
        ...

    def unmatched_exposures(self) -> list[dict]:
        """Exposures never attributed to a Supplier."""
        ...

    # -- read-back ---------------------------------------------------------

    def suppliers(self) -> list[dict]:
        ...

    def primes(self) -> list[dict]:
        ...

    def programs(self) -> list[dict]:
        ...

    def propagation_for_supplier(self, supplier_id: str) -> list[dict]:
        """Supplier → Prime → Program propagation rows."""
        ...

    def exposures_for_supplier(self, supplier_id: str) -> list[dict]:
        """Exposures attributed to a supplier (via Identity→Domain→Supplier),
        joined with any InfectedDevice active-signal fields."""
        ...

    def all_exposures(self) -> list[dict]:
        ...

    def infected_devices(self) -> list[dict]:
        ...

    # -- entity resolution (P2) --------------------------------------------

    def identities(self) -> list[dict]:
        """(id, email, username, domain_ref) for every Identity — input to
        EntityResolver."""
        ...

    def record_merge_proposal(
        self, *, id: str, identity_a: str, identity_b: str, basis: str,
        status: str, created_at: int,
    ) -> None:
        """Persist a MergeProposal (candidate pair + basis + status=pending).
        Nothing is merged here — human-on-the-loop."""
        ...

    def merge_proposals(self, status: str | None = None) -> list[dict]:
        """MergeProposals, optionally filtered by status."""
        ...

    def set_merge_proposal_status(self, proposal_id: str, status: str) -> None:
        """Transition a MergeProposal (pending → confirmed | rejected)."""
        ...

    def merge_identities(self, *, keep_id: str, drop_id: str) -> None:
        """Merge two Identities: repoint all Exposure/Device/match links from
        `drop_id` onto `keep_id`, then drop the variant. Confirm-only."""
        ...

    # -- active-compromise path (P3) ---------------------------------------

    def infected_device_paths(self) -> list[dict]:
        """Device → Identity → Domain → Supplier rows (left half of the active-
        compromise path); FlagActiveCompromise appends Supplier → Prime →
        Program."""
        ...

    # -- ComputeRisk output (P3) -------------------------------------------

    def record_risk_assessment(
        self, *, id: str, supplier_ref: str, score: float, grade: str,
        active_flag: bool, computed_at: int, components: dict, evidence: list,
    ) -> None:
        """Persist a RiskAssessment + evidenced_by links (non-empty evidence
        enforced upstream by ComputeRisk)."""
        ...

    def risk_assessments(self) -> list[dict]:
        ...

    def risk_evidence(self, assessment_ref: str) -> list[dict]:
        """evidenced_by links (evidence_ref, evidence_kind) of an assessment."""
        ...

    # -- FlagActiveCompromise output (P3) ----------------------------------

    def record_incident(
        self, *, id: str, supplier_ref: str, opened_at: int, status: str,
        path: list,
    ) -> None:
        """Persist a CompromiseIncident with its traverses `path` (Device→…→
        Program). No incident without a complete path (enforced upstream)."""
        ...

    def incidents(self) -> list[dict]:
        ...

    def incidents_for_supplier(self, supplier_id: str) -> list[dict]:
        ...
