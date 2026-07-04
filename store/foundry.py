"""Foundry/OSDK implementation of `OntologyStore` — the hot-swap TARGET (skeleton).

AIP (Foundry Ontology + OSDK) is the **spine**; the local SQLite store
(`store/sqlite.py`) is **validation / insurance** only (ADR-0003,
docs/decisions/0003-local-validation-store.md). THIS class is what the pipe is
migrated onto once the Foundry ontology + Action Types are published and an OSDK
package exists (see docs/runbooks/foundry-day1.md, aip-integration.md §2-(3)).

Because it implements the SAME `OntologyStore` Protocol as `SqliteOntologyStore`,
swapping the backend is a one-line change at the call site — the pipe code
(correlate / resolve / flag / score / draft) is untouched.

STATUS: skeleton. Every method raises `NotImplementedError` and carries a
comment sketching the intended OSDK call. post-publish fills these in.

Design constraints:
  * NO OSDK import at module top level — the published package name is not known
    until the Developer Console publishes it (foundry-day1.md §4). Importing this
    module must NEVER raise ImportError. The client is injected/loaded lazily in
    the constructor only.
  * Masking is already enforced upstream in `adapter.base.normalize()`; this
    store, like SQLite, must never receive or persist a raw secret.
  * Provenance/path rules (evidenced_by / cites / traverses non-empty) are
    enforced in the Action layer (`actions/`) and, on Foundry, additionally by
    Action Type submission criteria — not re-checked here.
"""

from __future__ import annotations

from typing import Any

from adapter.base import Exposure

_TODO = "FoundryOntologyStore is an OSDK wiring placeholder — wire the OSDK call, then remove this raise."


class FoundryOntologyStore:
    """OSDK-backed `OntologyStore` (skeleton). Same interface as SQLite → hot-swap.

    Construct with a published OSDK `FoundryClient` (or let it read env at
    post-publish). No network/import happens at module load.

        # from <published_osdk> import FoundryClient  # name TBD (foundry-day1.md §4)
        # client = FoundryClient(auth=UserTokenAuth(token=...), hostname=...)
        store = FoundryOntologyStore(client)
    """

    def __init__(self, client: Any | None = None) -> None:
        # `client` is a published-OSDK FoundryClient. Kept as-is; no OSDK type is
        # imported here so this module loads without the (unknown) package.
        self._client = client

    def _c(self) -> Any:
        """Return the OSDK client or fail loudly. post-publish may instead lazily build
        it from env (FOUNDRY_HOSTNAME / FOUNDRY_TOKEN, foundry-day1.md §5)."""
        if self._client is None:
            raise NotImplementedError(
                "No OSDK client bound. Inject a published FoundryClient "
                "or lazily construct it here from env. " + _TODO
            )
        return self._client

    # -- schema / seed writes ---------------------------------------------------

    def init_schema(self) -> None:
        # No-op on Foundry: the ontology schema is defined in Ontology Manager
        # (Object/Link/Action Types), not created at runtime. post-publish: assert the
        # expected object types exist via the OSDK metadata, else raise.
        raise NotImplementedError(_TODO)

    def upsert_supplier(self, *, id: str, name: str, tier: int, criticality: str) -> None:
        # client.ontology.actions.upsert_supplier(id=id, name=name, tier=tier,
        #     criticality=criticality)  # Action API name per console
        raise NotImplementedError(_TODO)

    def upsert_domain(self, *, fqdn: str, supplier_id: str) -> None:
        # client.ontology.actions.upsert_domain(fqdn=fqdn, supplier=supplier_id)
        #   → creates Domain + Supplier owns Domain link
        raise NotImplementedError(_TODO)

    def upsert_prime(self, *, id: str, name: str) -> None:
        # client.ontology.actions.upsert_prime(id=id, name=name)
        raise NotImplementedError(_TODO)

    def upsert_program(self, *, id: str, name: str, sensitivity: str | None = None) -> None:
        # client.ontology.actions.upsert_program(id=id, name=name, sensitivity=sensitivity)
        raise NotImplementedError(_TODO)

    def link_supplies(self, *, supplier_id: str, prime_id: str) -> None:
        # client.ontology.actions.link_supplies(supplier=supplier_id, prime=prime_id)
        #   → Supplier supplies Prime (N:M)
        raise NotImplementedError(_TODO)

    def link_runs(self, *, prime_id: str, program_id: str) -> None:
        # client.ontology.actions.link_runs(prime=prime_id, program=program_id)
        raise NotImplementedError(_TODO)

    def link_subcontract(
        self, *, sub_supplier_id: str, parent_supplier_id: str
    ) -> None:
        # client.ontology.actions.link_subcontract(sub=sub_supplier_id,
        #     parent=parent_supplier_id)  → Supplier subcontracts_to Supplier (N:M)
        raise NotImplementedError(_TODO)

    def write_exposure(self, exp: Exposure, *, domain: str | None = None) -> str:
        # Decompose Exposure → Identity / CredentialExposure / InfectedDevice /
        # ThreatSource objects + links via Action(s). Masking already enforced in
        # normalize(); pass exp.to_dict() fields, NEVER a raw secret.
        # client.ontology.actions.ingest_exposure(**exp.to_dict(), domain=domain)
        raise NotImplementedError(_TODO)

    # -- CorrelateExposure support ---------------------------------------------

    def registered_domains(self) -> dict[str, str]:
        # {fqdn: supplier_id} — read every Domain object:
        # {d.fqdn: d.supplier_ref for d in client.ontology.objects.Domain.iterate()}
        raise NotImplementedError(_TODO)

    def exposures_for_correlation(self) -> list[dict]:
        # client.ontology.objects.CredentialExposure.iterate() joined to Identity
        raise NotImplementedError(_TODO)

    def attach_identity_domain(self, identity_id: str, domain_ref: str) -> None:
        # client.ontology.actions.correlate_exposure(identity=identity_id,
        #     domain=domain_ref)  → Identity belongs_to Domain
        raise NotImplementedError(_TODO)

    def record_correlation(
        self, *, exposure_ref: str, identity_ref: str, domain_ref: str,
        supplier_id: str, match_basis: str, matched_at: int,
    ) -> None:
        # Persist match provenance (part of CorrelateExposure Action edits).
        raise NotImplementedError(_TODO)

    def unmatched_exposures(self) -> list[dict]:
        # CredentialExposure objects whose Identity has no belongs_to Domain.
        raise NotImplementedError(_TODO)

    # -- read-back --------------------------------------------------------------

    def suppliers(self) -> list[dict]:
        # [s.__dict__ for s in client.ontology.objects.Supplier.iterate()]
        raise NotImplementedError(_TODO)

    def primes(self) -> list[dict]:
        # client.ontology.objects.Prime.iterate()
        raise NotImplementedError(_TODO)

    def programs(self) -> list[dict]:
        # client.ontology.objects.Program.iterate()
        raise NotImplementedError(_TODO)

    def propagation_for_supplier(self, supplier_id: str) -> list[dict]:
        # Supplier → supplies → Prime → runs → Program link traversal via OSDK:
        # sup = client.ontology.objects.Supplier.get(supplier_id)
        # for p in sup.supplies.iterate(): for prog in p.runs.iterate(): ...
        raise NotImplementedError(_TODO)

    def propagation_paths(
        self, supplier_id: str, *, depth_cap: int = 6
    ) -> list[list[dict]]:
        # Variable-depth traverse of subcontracts_to (2차→1차→…) then supplies/
        # runs. On Foundry this is an OSDK graph traversal / an AIP Logic
        # function walking Supplier.subcontracts_to recursively (depth_cap +
        # visited-set), emitting Supplier…→Prime→Program node paths.
        raise NotImplementedError(_TODO)

    def exposures_for_supplier(self, supplier_id: str) -> list[dict]:
        # Traverse Supplier ← owns ← Domain ← belongs_to ← Identity ← of ←
        # CredentialExposure (+ InfectedDevice active-signal fields).
        raise NotImplementedError(_TODO)

    def all_exposures(self) -> list[dict]:
        # client.ontology.objects.CredentialExposure.iterate()
        raise NotImplementedError(_TODO)

    def infected_devices(self) -> list[dict]:
        # client.ontology.objects.InfectedDevice.iterate()
        raise NotImplementedError(_TODO)

    # -- entity resolution (P2) -------------------------------------------------

    def identities(self) -> list[dict]:
        # client.ontology.objects.Identity.iterate()
        raise NotImplementedError(_TODO)

    def record_merge_proposal(
        self, *, id: str, identity_a: str, identity_b: str, basis: str,
        status: str, created_at: int,
    ) -> None:
        # client.ontology.actions.propose_merge(identity_a=..., identity_b=...,
        #     basis=basis)  → MergeProposal (status=pending, human-on-the-loop)
        raise NotImplementedError(_TODO)

    def merge_proposals(self, status: str | None = None) -> list[dict]:
        # client.ontology.objects.MergeProposal.where(status == ...).iterate()
        raise NotImplementedError(_TODO)

    def set_merge_proposal_status(self, proposal_id: str, status: str) -> None:
        # client.ontology.actions.set_merge_status(proposal=proposal_id, status=status)
        raise NotImplementedError(_TODO)

    def merge_identities(self, *, keep_id: str, drop_id: str) -> None:
        # client.ontology.actions.merge_identities(keep=keep_id, drop=drop_id)
        #   → repoint Exposure/Device/match links, drop the variant (confirm-only)
        raise NotImplementedError(_TODO)

    # -- active-compromise path (P3) -------------------------------------------

    def infected_device_paths(self) -> list[dict]:
        # Device → compromises → Identity → belongs_to → Domain → Supplier
        # (left half; FlagActiveCompromise appends Supplier→Prime→Program).
        raise NotImplementedError(_TODO)

    def device_compromised_suppliers(self, device_id: str) -> list[str]:
        # compromises = leaked∘of: dev = InfectedDevice.get(device_id);
        # {e.of.belongs_to.owned_by for e in dev.leaked.iterate()} — the distinct
        # Suppliers this device reaches, for device-level blast aggregation.
        raise NotImplementedError(_TODO)

    # -- ComputeRisk output (P3) -----------------------------------------------

    def record_risk_assessment(
        self, *, id: str, supplier_ref: str, score: float, grade: str,
        active_flag: bool, computed_at: int, components: dict, evidence: list,
    ) -> None:
        # client.ontology.actions.compute_risk(supplier=supplier_ref,
        #     evidence=[ref for ref, _ in evidence], ...)  → RiskAssessment +
        #     evidenced_by links. Non-empty evidence enforced by the Action Type
        #     submission criteria (foundry-day1.md §3-G) AND actions/compute_risk.py.
        raise NotImplementedError(_TODO)

    def risk_assessments(self) -> list[dict]:
        # client.ontology.objects.RiskAssessment.iterate()
        raise NotImplementedError(_TODO)

    def risk_evidence(self, assessment_ref: str) -> list[dict]:
        # ra = client.ontology.objects.RiskAssessment.get(assessment_ref)
        # [ {evidence_ref, evidence_kind} for e in ra.evidenced_by.iterate() ]
        raise NotImplementedError(_TODO)

    # -- FlagActiveCompromise output (P3) --------------------------------------

    def record_incident(
        self, *, id: str, supplier_ref: str, opened_at: int, status: str, path: list,
        blast_radius: dict | None = None,
    ) -> None:
        # client.ontology.actions.flag_active_compromise(supplier=supplier_ref,
        #     path=path, blast_radius=blast_radius, ...)  → CompromiseIncident with
        #     traverses path + blast radius (no incident without a complete path —
        #     enforced in flag_active.py).
        raise NotImplementedError(_TODO)

    def incidents(self) -> list[dict]:
        # client.ontology.objects.CompromiseIncident.iterate()
        raise NotImplementedError(_TODO)

    def incidents_for_supplier(self, supplier_id: str) -> list[dict]:
        # client.ontology.objects.CompromiseIncident.where(supplier_ref == supplier_id)
        raise NotImplementedError(_TODO)

    # -- PropagateRisk / ProgramExposure output --------------------------------

    def record_program_exposure(
        self, *, id: str, program_ref: str, score: float, grade: str,
        active_flag: bool, computed_at: int, components: dict,
        contributing_paths: list, evidence: list,
    ) -> None:
        # client.ontology.actions.propagate_risk(program=program_ref, score=score,
        #     evidence=[ref for ref, _ in evidence], ...)  → ProgramExposure +
        #     evidenced_by links. Non-empty evidence enforced by the Action Type
        #     submission criteria AND actions/propagate_risk.py.
        raise NotImplementedError(_TODO)

    def program_exposures(self) -> list[dict]:
        # client.ontology.objects.ProgramExposure.iterate()
        raise NotImplementedError(_TODO)

    def program_exposure_evidence(self, exposure_ref: str) -> list[dict]:
        # pe = client.ontology.objects.ProgramExposure.get(exposure_ref)
        # [ {evidence_ref, evidence_kind} for e in pe.evidenced_by.iterate() ]
        raise NotImplementedError(_TODO)

    # -- GenerateNotificationDraft output (P5) ---------------------------------

    def record_notification_draft(
        self, *, id: str, supplier_ref: str, body: str, status: str,
        created_at: int, cites: list,
    ) -> None:
        # client.ontology.actions.generate_notification_draft(supplier=supplier_ref,
        #     cites=[ref for ref, _ in cites], body=body)  → NotificationDraft
        #     (status always 'draft' — NO send path exists; CLAUDE.md guardrail).
        raise NotImplementedError(_TODO)

    def notification_drafts(self) -> list[dict]:
        # client.ontology.objects.NotificationDraft.iterate()
        raise NotImplementedError(_TODO)

    def draft_for_supplier(self, supplier_id: str) -> dict | None:
        # client.ontology.objects.NotificationDraft.where(supplier_ref == supplier_id)
        raise NotImplementedError(_TODO)

    def draft_cites(self, draft_ref: str) -> list[dict]:
        # nd = client.ontology.objects.NotificationDraft.get(draft_ref)
        # [ {evidence_ref, evidence_kind} for c in nd.cites.iterate() ]
        raise NotImplementedError(_TODO)
