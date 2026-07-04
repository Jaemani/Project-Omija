from __future__ import annotations

from types import SimpleNamespace

import pytest

from scripts.foundry_osdk_smoke import SmokeFailure, run_smoke


class ObjectApi:
    def __init__(self, objects):
        self._objects = objects

    def get(self, primary_key):
        return self._objects[primary_key]


class Relation:
    def __init__(self, *items):
        self._items = items

    def iterate(self):
        return iter(self._items)


def _client():
    program = SimpleNamespace(id="prog-sentinel", name="Sentinel ISR Program")
    prime = SimpleNamespace(
        id="prime-x",
        name="Xenon Aerospace",
        runs=Relation(program),
    )
    supplier_f = SimpleNamespace(
        id="sup-f",
        name="Foxtrot Metals",
        supplies=Relation(prime),
    )
    supplier_h = SimpleNamespace(
        id="sup-h",
        name="Hotel Microelectronics",
        subcontractsTo=Relation(supplier_f),
    )
    exposure = SimpleNamespace(
        id="exp:micro-h:active",
        of=Relation(SimpleNamespace(id="id:ops@micro-h.example")),
        targets=Relation(SimpleNamespace(fqdn="vpn.prime-x.example")),
    )
    incident = SimpleNamespace(
        id="incident:micro-h:active",
        traversesSupplier=Relation(supplier_h, supplier_f),
        traversesProgram=Relation(program),
    )
    draft = SimpleNamespace(
        id="draft:sup-h:2026-07-03",
        citesIncident=Relation(incident),
    )
    objects = SimpleNamespace(
        Supplier=ObjectApi({"sup-h": supplier_h, "sup-f": supplier_f}),
        Prime=ObjectApi({"prime-x": prime}),
        Program=ObjectApi({"prog-sentinel": program}),
        CredentialExposure=ObjectApi({"exp:micro-h:active": exposure}),
        CompromiseIncident=ObjectApi({"incident:micro-h:active": incident}),
        NotificationDraft=ObjectApi({"draft:sup-h:2026-07-03": draft}),
    )
    return SimpleNamespace(ontology=SimpleNamespace(objects=objects))


def test_run_smoke_accepts_foundry_like_object_and_link_apis():
    checks = run_smoke(_client())

    assert "verified supplier path sup-h -> sup-f -> prime-x -> prog-sentinel" in checks
    assert "verified exposure of/targets split" in checks
    assert "verified draft cites incident provenance" in checks


def test_run_smoke_reports_missing_expected_link():
    client = _client()
    client.ontology.objects.Supplier._objects["sup-h"].subcontractsTo = Relation()

    with pytest.raises(SmokeFailure, match="sup-h -> subcontractsTo"):
        run_smoke(client)
