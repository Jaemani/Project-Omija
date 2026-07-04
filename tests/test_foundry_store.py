"""Foundry/OSDK store read contract without requiring a live OSDK in CI."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from store.base import OntologyStore
from store.foundry import FoundryOntologyStore


class ObjectApi:
    def __init__(self, objects):
        self._objects = objects

    def get(self, primary_key):
        return self._objects[primary_key]

    def iterate(self):
        return iter(self._objects.values())


class Relation:
    def __init__(self, *items):
        self._items = items

    def iterate(self):
        return iter(self._items)


def _fake_client():
    program = SimpleNamespace(
        id="prog-sentinel",
        name="Sentinel ISR Program",
        sensitivity="high",
        status="active",
    )
    prime = SimpleNamespace(
        id="prime-x",
        name="Xenon Aerospace",
        status="active",
        programs=Relation(program),
    )
    supplier_f = SimpleNamespace(
        id="sup-f",
        name="Foxtrot Metals",
        tier=1,
        criticality="medium",
        status="active",
        is_prime_candidate=False,
        primes=Relation(prime),
    )
    supplier_h = SimpleNamespace(
        id="sup-h",
        name="Hotel Microelectronics",
        tier=2,
        criticality="high",
        status="active",
        is_prime_candidate=False,
        subcontractsTo=Relation(supplier_f),
    )
    domain_micro = SimpleNamespace(
        domain_fqdn="micro-h.example",
        host="micro-h.example",
        asset_type="domain",
        supplier=Relation(supplier_h),
    )
    domain_vpn = SimpleNamespace(
        domain_fqdn="vpn.prime-x.example",
        host="vpn.prime-x.example",
        asset_type="vpn",
    )
    supplier_h.domains = Relation(domain_micro)
    prime.domains = Relation(domain_vpn)

    identity = SimpleNamespace(
        id="id:ops@micro-h.example",
        email="ops@micro-h.example",
        username="ops",
        account_type="admin",
        domain=Relation(domain_micro),
    )
    source = SimpleNamespace(
        id="src:candidate:empty",
        kind="osint_api",
        name="Candidate placeholder",
    )
    exposure = SimpleNamespace(
        id="exp:micro-h:active",
        module="cds",
        secret_type="cookie",
        secret_present=True,
        masked_value="SI***",
        secret_fingerprint="fp:micro-h:active",
        source_ref="src:candidate:empty",
        confidence=0.9,
        first_seen="2026-07-01T00:00:00Z",
        last_seen="2026-07-03T00:00:00Z",
        identity=Relation(identity),
        domain=Relation(domain_vpn),
        threat_source=Relation(source),
    )
    device = SimpleNamespace(
        id="dev:micro-h:laptop1",
        malware="RedLine",
        infected_at="2026-07-01T00:00:00Z",
        has_session_cookie=True,
        os="Windows 10",
        status="active",
        credential_exposures=Relation(exposure),
        identities=Relation(identity),
    )
    exposure.infected_device = Relation(device)

    incident = SimpleNamespace(
        id="incident:micro-h:active",
        supplier_ref="sup-h",
        risk_band="A",
        opened_at="2026-07-03T00:00:00Z",
        status="open",
        path_snapshot='["dev:micro-h:laptop1","exp:micro-h:active","sup-h","sup-f","prime-x","prog-sentinel"]',
        blast_radius='{"programs":["prog-sentinel"]}',
        traversesSupplier=Relation(supplier_h, supplier_f),
        traversesProgram=Relation(program),
    )
    draft = SimpleNamespace(
        id="draft:sup-h:2026-07-03",
        recipient_ref="sup-h",
        body="Synthetic demo draft",
        status="draft",
        compromise_incidents=Relation(incident),
    )
    risk = SimpleNamespace(
        id="risk:sup-h:2026-07-03",
        supplier_ref="sup-h",
        risk_band="A",
        score=95.0,
        grade="critical",
        active_flag=True,
        components='{"active_path":true}',
        status="active",
    )
    progexp = SimpleNamespace(
        id="progexp:prog-sentinel:2026-07-03",
        program_ref="prog-sentinel",
        risk_band="A",
        score=90.0,
        grade="critical",
        active_flag=True,
        components='{"active_incidents":1}',
        contributing_paths='["pathhash:micro-h-active"]',
        status="active",
    )
    merge = SimpleNamespace(
        id="merge:micro-h:ops",
        identity_a="id:ops@micro-h.example",
        identity_b="id:ops@micro-h.example",
        basis="self-link smoke test",
        status="proposed",
    )

    objects = SimpleNamespace(
        Supplier=ObjectApi({"sup-h": supplier_h, "sup-f": supplier_f}),
        Prime=ObjectApi({"prime-x": prime}),
        Program=ObjectApi({"prog-sentinel": program}),
        Domain=ObjectApi(
            {"micro-h.example": domain_micro, "vpn.prime-x.example": domain_vpn}
        ),
        Identity=ObjectApi({"id:ops@micro-h.example": identity}),
        CredentialExposure=ObjectApi({"exp:micro-h:active": exposure}),
        InfectedDevice=ObjectApi({"dev:micro-h:laptop1": device}),
        ThreatSource=ObjectApi({"src:candidate:empty": source}),
        MergeProposal=ObjectApi({"merge:micro-h:ops": merge}),
        RiskAssessment=ObjectApi({"risk:sup-h:2026-07-03": risk}),
        CompromiseIncident=ObjectApi({"incident:micro-h:active": incident}),
        ProgramExposure=ObjectApi({"progexp:prog-sentinel:2026-07-03": progexp}),
        NotificationDraft=ObjectApi({"draft:sup-h:2026-07-03": draft}),
    )
    return SimpleNamespace(ontology=SimpleNamespace(objects=objects))


def test_imports_and_constructs_without_osdk():
    assert FoundryOntologyStore() is not None


def test_satisfies_ontology_store_protocol():
    assert isinstance(FoundryOntologyStore(_fake_client()), OntologyStore)


def test_read_methods_use_injected_osdk_client():
    store = FoundryOntologyStore(_fake_client())

    assert {row["id"] for row in store.suppliers()} == {"sup-h", "sup-f"}
    assert store.propagation_paths("sup-h")[0][-1]["ref"] == "prog-sentinel"

    exposures = store.exposures_for_supplier("sup-h")
    assert exposures[0]["id"] == "exp:micro-h:active"
    assert exposures[0]["target_domain_ref"] == "vpn.prime-x.example"
    assert exposures[0]["supplier_id"] == "sup-h"

    assert store.incidents_for_supplier("sup-h")[0]["id"] == "incident:micro-h:active"
    assert store.draft_for_supplier("sup-h")["id"] == "draft:sup-h:2026-07-03"


def test_write_method_still_raises_not_implemented():
    with pytest.raises(NotImplementedError):
        FoundryOntologyStore(_fake_client()).upsert_supplier(
            id="sup-a", name="Alpha", tier=1, criticality="high"
        )


def test_action_method_still_raises_not_implemented():
    with pytest.raises(NotImplementedError):
        FoundryOntologyStore(_fake_client()).record_risk_assessment(
            id="risk:sup-a",
            supplier_ref="sup-a",
            score=1.0,
            grade="관찰",
            active_flag=False,
            computed_at=0,
            components={},
            evidence=[("exp:1", "exposure")],
        )
