"""Foundry/OSDK-backed read store.

Writes still belong to Foundry Action Types and are intentionally not wired
here. This class implements the read side needed to prove the SQLite validation
store can be swapped for the Foundry ontology through the same boundary.
"""

from __future__ import annotations

from typing import Any

from adapter.base import Exposure
from store.osdk_compat import (
    build_client_from_env,
    field_value,
    get_object,
    list_objects,
    object_key,
    parse_jsonish,
    related,
)


_TODO = "FoundryOntologyStore write/action method is not wired; use Foundry Action Types."


LINKS = {
    "subcontracts_to": ("subcontractsTo", "subcontracts_to"),
    "supplies": ("supplies", "primes"),
    "runs": ("runs", "programs"),
    "owns": ("domains", "owns"),
    "belongs_to": ("domain", "belongsTo", "belongs_to"),
    "of": ("identity", "of"),
    "targets": ("domain", "targets"),
    "sourced_from": ("threat_source", "threatSources", "sourcedFrom"),
    "leaked": ("credential_exposures", "leaked"),
    "traverses_supplier": ("traversesSupplier", "traverses_supplier", "suppliers"),
    "traverses_program": ("traversesProgram", "traverses_program", "programs"),
    "cites_incident": ("citesIncident", "cites_incident", "compromise_incidents"),
}


OBJECT_ENV = {
    "Supplier": "FOUNDRY_OSDK_OBJECT_SUPPLIER",
    "Prime": "FOUNDRY_OSDK_OBJECT_PRIME",
    "Program": "FOUNDRY_OSDK_OBJECT_PROGRAM",
    "Domain": "FOUNDRY_OSDK_OBJECT_DOMAIN",
    "Identity": "FOUNDRY_OSDK_OBJECT_IDENTITY",
    "CredentialExposure": "FOUNDRY_OSDK_OBJECT_CREDENTIAL_EXPOSURE",
    "InfectedDevice": "FOUNDRY_OSDK_OBJECT_INFECTED_DEVICE",
    "ThreatSource": "FOUNDRY_OSDK_OBJECT_THREAT_SOURCE",
    "MergeProposal": "FOUNDRY_OSDK_OBJECT_MERGE_PROPOSAL",
    "RiskAssessment": "FOUNDRY_OSDK_OBJECT_RISK_ASSESSMENT",
    "CompromiseIncident": "FOUNDRY_OSDK_OBJECT_COMPROMISE_INCIDENT",
    "ProgramExposure": "FOUNDRY_OSDK_OBJECT_PROGRAM_EXPOSURE",
    "NotificationDraft": "FOUNDRY_OSDK_OBJECT_NOTIFICATION_DRAFT",
}


def _get(client: Any, object_type: str, primary_key: str) -> Any:
    return get_object(client, object_type, primary_key, OBJECT_ENV.get(object_type))


def _list(client: Any, object_type: str) -> list[Any]:
    return list_objects(client, object_type, OBJECT_ENV.get(object_type))


def _maybe_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _iso(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def _related(obj: Any, names: tuple[str, ...]) -> list[Any]:
    try:
        return related(obj, names)
    except Exception:
        return []


def _first_related(obj: Any | None, names: tuple[str, ...]) -> Any | None:
    if obj is None:
        return None
    items = _related(obj, names)
    return items[0] if items else None


def _supplier_row(obj: Any) -> dict:
    return {
        "id": object_key(obj),
        "name": field_value(obj, "name"),
        "tier": field_value(obj, "tier"),
        "criticality": field_value(obj, "criticality"),
        "status": field_value(obj, "status"),
        "is_prime_candidate": field_value(obj, "is_prime_candidate"),
    }


def _prime_row(obj: Any) -> dict:
    return {"id": object_key(obj), "name": field_value(obj, "name"), "status": field_value(obj, "status")}


def _program_row(obj: Any) -> dict:
    return {
        "id": object_key(obj),
        "name": field_value(obj, "name"),
        "sensitivity": field_value(obj, "sensitivity"),
        "status": field_value(obj, "status"),
    }


def _domain_row(obj: Any) -> dict:
    return {
        "fqdn": object_key(obj),
        "host": field_value(obj, "host"),
        "url": field_value(obj, "url"),
        "asset_type": field_value(obj, "asset_type") or field_value(obj, "supplier_id"),
        "criticality": field_value(obj, "criticality"),
        "access_surface": field_value(obj, "access_surface"),
        "verified_at": _iso(field_value(obj, "verified_at")),
    }


class FoundryOntologyStore:
    """Read-only OSDK implementation of the `OntologyStore` protocol."""

    def __init__(self, client: Any | None = None, *, env_file: str = ".env") -> None:
        self._client = client
        self._env_file = env_file

    @property
    def client(self) -> Any:
        if self._client is None:
            self._client = build_client_from_env(self._env_file)
        return self._client

    # -- schema / writes -----------------------------------------------------

    def init_schema(self) -> None:
        return None

    def upsert_supplier(self, *, id: str, name: str, tier: int, criticality: str) -> None:
        raise NotImplementedError(_TODO)

    def upsert_domain(self, *, fqdn: str, supplier_id: str) -> None:
        raise NotImplementedError(_TODO)

    def upsert_prime(self, *, id: str, name: str) -> None:
        raise NotImplementedError(_TODO)

    def upsert_program(self, *, id: str, name: str, sensitivity: str | None = None) -> None:
        raise NotImplementedError(_TODO)

    def link_supplies(self, *, supplier_id: str, prime_id: str) -> None:
        raise NotImplementedError(_TODO)

    def link_runs(self, *, prime_id: str, program_id: str) -> None:
        raise NotImplementedError(_TODO)

    def link_subcontract(self, *, sub_supplier_id: str, parent_supplier_id: str) -> None:
        raise NotImplementedError(_TODO)

    def write_exposure(self, exp: Exposure, *, domain: str | None = None) -> str:
        raise NotImplementedError(_TODO)

    def attach_identity_domain(self, identity_id: str, domain_ref: str) -> None:
        raise NotImplementedError(_TODO)

    def record_correlation(
        self,
        *,
        exposure_ref: str,
        identity_ref: str,
        domain_ref: str,
        supplier_id: str,
        match_basis: str,
        matched_at: int,
    ) -> None:
        raise NotImplementedError(_TODO)

    def record_merge_proposal(
        self,
        *,
        id: str,
        identity_a: str,
        identity_b: str,
        basis: str,
        status: str,
        created_at: int,
    ) -> None:
        raise NotImplementedError(_TODO)

    def set_merge_proposal_status(self, proposal_id: str, status: str) -> None:
        raise NotImplementedError(_TODO)

    def merge_identities(self, *, keep_id: str, drop_id: str) -> None:
        raise NotImplementedError(_TODO)

    def record_risk_assessment(
        self,
        *,
        id: str,
        supplier_ref: str,
        score: float,
        grade: str,
        active_flag: bool,
        computed_at: int,
        components: dict,
        evidence: list,
    ) -> None:
        raise NotImplementedError(_TODO)

    def record_incident(
        self,
        *,
        id: str,
        supplier_ref: str,
        opened_at: int,
        status: str,
        path: list,
        blast_radius: dict | None = None,
    ) -> None:
        raise NotImplementedError(_TODO)

    def record_program_exposure(
        self,
        *,
        id: str,
        program_ref: str,
        score: float,
        grade: str,
        active_flag: bool,
        computed_at: int,
        components: dict,
        contributing_paths: list,
        evidence: list,
    ) -> None:
        raise NotImplementedError(_TODO)

    def record_notification_draft(
        self,
        *,
        id: str,
        supplier_ref: str,
        body: str,
        status: str,
        created_at: int,
        cites: list,
    ) -> None:
        raise NotImplementedError(_TODO)

    # -- read-back -----------------------------------------------------------

    def suppliers(self) -> list[dict]:
        return [_supplier_row(obj) for obj in _list(self.client, "Supplier")]

    def primes(self) -> list[dict]:
        return [_prime_row(obj) for obj in _list(self.client, "Prime")]

    def programs(self) -> list[dict]:
        return [_program_row(obj) for obj in _list(self.client, "Program")]

    def registered_domains(self) -> dict[str, str]:
        result: dict[str, str] = {}
        for supplier in _list(self.client, "Supplier"):
            for domain in _related(supplier, LINKS["owns"]):
                result[object_key(domain)] = object_key(supplier)
        return result

    def propagation_for_supplier(self, supplier_id: str) -> list[dict]:
        rows: list[dict] = []
        supplier = _get(self.client, "Supplier", supplier_id)
        for prime in _related(supplier, LINKS["supplies"]):
            for program in _related(prime, LINKS["runs"]):
                rows.append(
                    {
                        "prime_id": object_key(prime),
                        "prime_name": field_value(prime, "name"),
                        "program_id": object_key(program),
                        "program_name": field_value(program, "name"),
                        "sensitivity": field_value(program, "sensitivity"),
                    }
                )
        return rows

    def propagation_paths(self, supplier_id: str, *, depth_cap: int = 6) -> list[list[dict]]:
        paths: list[list[dict]] = []
        queue: list[tuple[Any, list[Any]]] = [(_get(self.client, "Supplier", supplier_id), [])]
        while queue:
            supplier, chain = queue.pop(0)
            sid = object_key(supplier)
            if sid in {object_key(s) for s in chain}:
                continue
            next_chain = [*chain, supplier]
            for prime in _related(supplier, LINKS["supplies"]):
                for program in _related(prime, LINKS["runs"]):
                    nodes = [
                        {"type": "Supplier", "ref": object_key(s), "name": field_value(s, "name")}
                        for s in next_chain
                    ]
                    nodes.append({"type": "Prime", "ref": object_key(prime), "name": field_value(prime, "name")})
                    nodes.append(
                        {
                            "type": "Program",
                            "ref": object_key(program),
                            "name": field_value(program, "name"),
                            "sensitivity": field_value(program, "sensitivity"),
                        }
                    )
                    paths.append(nodes)
            if len(next_chain) <= depth_cap:
                for parent in _related(supplier, LINKS["subcontracts_to"]):
                    queue.append((parent, next_chain))
        return paths

    def _exposure_row(self, exposure: Any, owner_map: dict[str, str] | None = None) -> dict:
        owner_map = owner_map or {}
        identity = _first_related(exposure, LINKS["of"])
        identity_domain = _first_related(identity, LINKS["belongs_to"])
        target_domain = _first_related(exposure, LINKS["targets"])
        threat_source = _first_related(exposure, LINKS["sourced_from"])
        infected = _first_related(exposure, ("infected_device", "infected_devices"))
        supplier = _first_related(identity_domain, ("supplier", "suppliers"))
        domain_ref = object_key(identity_domain) if identity_domain else None
        supplier_id = object_key(supplier) if supplier else owner_map.get(domain_ref or "")
        return {
            "id": object_key(exposure),
            "module": field_value(exposure, "module"),
            "secret_type": field_value(exposure, "secret_type"),
            "masked_value": field_value(exposure, "masked_value"),
            "secret_present": field_value(exposure, "secret_present"),
            "secret_fingerprint": field_value(exposure, "secret_fingerprint"),
            "host": field_value(target_domain, "host") or object_key(target_domain),
            "observed_at": _iso(field_value(exposure, "first_seen")),
            "fetched_at": _iso(field_value(exposure, "last_seen")),
            "source": field_value(threat_source, "name"),
            "source_ref": field_value(exposure, "source_ref") or object_key(threat_source),
            "confidence": field_value(exposure, "confidence"),
            "identity_ref": object_key(identity) if identity else None,
            "email": field_value(identity, "email"),
            "username": field_value(identity, "username"),
            "domain_ref": domain_ref,
            "target_domain_ref": object_key(target_domain) if target_domain else None,
            "supplier_id": supplier_id,
            "malware": field_value(infected, "malware"),
            "infected_at": _iso(field_value(infected, "infected_at")),
            "has_session_cookie": field_value(infected, "has_session_cookie"),
            "account_type": field_value(identity, "account_type"),
            "threat_kind": field_value(threat_source, "kind"),
            "threat_name": field_value(threat_source, "name"),
        }

    def exposures_for_supplier(self, supplier_id: str) -> list[dict]:
        return [row for row in self.all_exposures() if row.get("supplier_id") == supplier_id]

    def all_exposures(self) -> list[dict]:
        owner_map = self.registered_domains()
        return [
            self._exposure_row(obj, owner_map)
            for obj in _list(self.client, "CredentialExposure")
        ]

    def exposures_for_correlation(self) -> list[dict]:
        return [
            {
                "id": row["id"],
                "source_ref": row.get("source_ref"),
                "identity_ref": row.get("identity_ref"),
                "email": row.get("email"),
            }
            for row in self.all_exposures()
        ]

    def unmatched_exposures(self) -> list[dict]:
        return [row for row in self.all_exposures() if not row.get("domain_ref")]

    def infected_devices(self) -> list[dict]:
        rows: list[dict] = []
        for obj in _list(self.client, "InfectedDevice"):
            exposure = _first_related(obj, LINKS["leaked"])
            identity = _first_related(obj, ("identities", "identity"))
            rows.append(
                {
                    "id": object_key(obj),
                    "exposure_ref": object_key(exposure) if exposure else None,
                    "identity_ref": object_key(identity) if identity else None,
                    "malware": field_value(obj, "malware"),
                    "infected_at": _iso(field_value(obj, "infected_at")),
                    "has_session_cookie": field_value(obj, "has_session_cookie"),
                    "os": field_value(obj, "os"),
                    "status": field_value(obj, "status"),
                }
            )
        return rows

    def identities(self) -> list[dict]:
        rows: list[dict] = []
        for obj in _list(self.client, "Identity"):
            domain = _first_related(obj, LINKS["belongs_to"])
            rows.append(
                {
                    "id": object_key(obj),
                    "email": field_value(obj, "email"),
                    "username": field_value(obj, "username"),
                    "domain_ref": object_key(domain) if domain else None,
                }
            )
        return rows

    def merge_proposals(self, status: str | None = None) -> list[dict]:
        rows = [
            {
                "id": object_key(obj),
                "identity_a": field_value(obj, "identity_a"),
                "identity_b": field_value(obj, "identity_b"),
                "basis": field_value(obj, "basis"),
                "status": field_value(obj, "status"),
                "created_at": _iso(field_value(obj, "created_at")),
            }
            for obj in _list(self.client, "MergeProposal")
        ]
        return [row for row in rows if status is None or row["status"] == status]

    def risk_assessments(self) -> list[dict]:
        return [
            {
                "id": object_key(obj),
                "supplier_ref": field_value(obj, "supplier_ref"),
                "risk_band": field_value(obj, "risk_band"),
                "score": field_value(obj, "score"),
                "grade": field_value(obj, "grade"),
                "active_flag": field_value(obj, "active_flag"),
                "computed_at": _iso(field_value(obj, "computed_at")),
                "components": parse_jsonish(field_value(obj, "components"), {}),
                "status": field_value(obj, "status"),
            }
            for obj in _list(self.client, "RiskAssessment")
        ]

    def risk_evidence(self, assessment_ref: str) -> list[dict]:
        assessment = _get(self.client, "RiskAssessment", assessment_ref)
        result: list[dict] = []
        for attr, kind in (
            ("credential_exposures", "exposure"),
            ("infected_devices", "device"),
            ("compromise_incidents", "incident"),
        ):
            if hasattr(assessment, attr):
                for obj in _related(assessment, (attr,)):
                    result.append({"evidence_ref": object_key(obj), "evidence_kind": kind})
        return result

    def incidents(self) -> list[dict]:
        rows: list[dict] = []
        for obj in _list(self.client, "CompromiseIncident"):
            rows.append(
                {
                    "id": object_key(obj),
                    "supplier_ref": field_value(obj, "supplier_ref"),
                    "risk_band": field_value(obj, "risk_band"),
                    "opened_at": _iso(field_value(obj, "opened_at")),
                    "status": field_value(obj, "status"),
                    "path": parse_jsonish(field_value(obj, "path_snapshot"), []),
                    "path_snapshot": field_value(obj, "path_snapshot"),
                    "path_hash": field_value(obj, "path_hash"),
                    "blast_radius": parse_jsonish(field_value(obj, "blast_radius"), {}),
                    "path_confidence": field_value(obj, "path_confidence"),
                    "traverses_suppliers": [object_key(x) for x in _related(obj, LINKS["traverses_supplier"])],
                    "traverses_programs": [object_key(x) for x in _related(obj, LINKS["traverses_program"])],
                }
            )
        return rows

    def incidents_for_supplier(self, supplier_id: str) -> list[dict]:
        return [row for row in self.incidents() if row.get("supplier_ref") == supplier_id]

    def infected_device_paths(self) -> list[dict]:
        rows: list[dict] = []
        for device in self.infected_devices():
            exposure_ref = device.get("exposure_ref")
            if not exposure_ref:
                continue
            exposure = next((row for row in self.all_exposures() if row["id"] == exposure_ref), None)
            if exposure:
                rows.append({**device, **exposure})
        return rows

    def device_compromised_suppliers(self, device_id: str) -> list[str]:
        device = _get(self.client, "InfectedDevice", device_id)
        suppliers = {
            row.get("supplier_id")
            for exposure in _related(device, LINKS["leaked"])
            for row in [self._exposure_row(exposure, self.registered_domains())]
            if row.get("supplier_id")
        }
        return sorted(suppliers)

    def program_exposures(self) -> list[dict]:
        return [
            {
                "id": object_key(obj),
                "program_ref": field_value(obj, "program_ref"),
                "risk_band": field_value(obj, "risk_band"),
                "score": field_value(obj, "score"),
                "grade": field_value(obj, "grade"),
                "active_flag": field_value(obj, "active_flag"),
                "computed_at": _iso(field_value(obj, "computed_at")),
                "components": parse_jsonish(field_value(obj, "components"), {}),
                "contributing_paths": parse_jsonish(field_value(obj, "contributing_paths"), []),
                "status": field_value(obj, "status"),
            }
            for obj in _list(self.client, "ProgramExposure")
        ]

    def program_exposure_evidence(self, exposure_ref: str) -> list[dict]:
        exposure = _get(self.client, "ProgramExposure", exposure_ref)
        result: list[dict] = []
        for attr, kind in (("risk_assessments", "assessment"), ("compromise_incidents", "incident")):
            if hasattr(exposure, attr):
                for obj in _related(exposure, (attr,)):
                    result.append({"evidence_ref": object_key(obj), "evidence_kind": kind})
        return result

    def notification_drafts(self) -> list[dict]:
        return [
            {
                "id": object_key(obj),
                "supplier_ref": field_value(obj, "recipient_ref"),
                "recipient_ref": field_value(obj, "recipient_ref"),
                "body": field_value(obj, "body"),
                "status": field_value(obj, "status"),
                "created_at": _iso(field_value(obj, "created_at")),
                "created_by": field_value(obj, "created_by"),
                "reviewer": field_value(obj, "reviewer"),
            }
            for obj in _list(self.client, "NotificationDraft")
        ]

    def draft_for_supplier(self, supplier_id: str) -> dict | None:
        return next((row for row in self.notification_drafts() if row.get("supplier_ref") == supplier_id), None)

    def draft_cites(self, draft_ref: str) -> list[dict]:
        draft = _get(self.client, "NotificationDraft", draft_ref)
        result: list[dict] = []
        for attr, kind in (
            ("credential_exposures", "exposure"),
            ("infected_devices", "device"),
            ("compromise_incidents", "incident"),
            ("risk_assessments", "assessment"),
        ):
            if hasattr(draft, attr):
                for obj in _related(draft, (attr,)):
                    result.append({"evidence_ref": object_key(obj), "evidence_kind": kind})
        return result
