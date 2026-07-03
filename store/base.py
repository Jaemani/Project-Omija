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

    def write_exposure(
        self, exp: Exposure, *, domain: str | None = None
    ) -> str:
        """Decompose an `Exposure` into ontology objects (Identity,
        CredentialExposure, InfectedDevice, ThreatSource) with links, resolving
        the Identity by email/username (entity resolution). Returns exposure id.
        Masking is already enforced upstream in `normalize()`; the store must
        never receive or persist a raw secret."""
        ...

    # -- read-back ---------------------------------------------------------

    def suppliers(self) -> list[dict]:
        ...

    def exposures_for_supplier(self, supplier_id: str) -> list[dict]:
        """Exposures attributed to a supplier (via Identity→Domain→Supplier),
        joined with any InfectedDevice active-signal fields."""
        ...

    def all_exposures(self) -> list[dict]:
        ...

    def infected_devices(self) -> list[dict]:
        ...
