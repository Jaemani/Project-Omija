"""(b) ComputeRisk provenance rule + (a) end-to-end active-on-top ranking.

ComputeRisk refuses to score a supplier with no evidence (evidenced_by empty).
Over the full pipeline, the two active-compromise suppliers rank strictly above
every non-active supplier, and every assessment cites its backing records."""

import pytest

from actions.compute_risk import EvidenceRequired, compute_all, compute_risk
from actions.correlate import correlate_exposures
from actions.flag_active import flag_active_compromises
from adapter.base import normalize
from adapter.mock import DEMO_NOW, MODULES, MockExposureSource
from registry.loader import load_into_store
from store.sqlite import SqliteOntologyStore


def _full_pipe(store) -> None:
    load_into_store(store)
    src = MockExposureSource()
    for fqdn in src.domains():
        for module in MODULES:
            for raw in src.search(module, "domain", fqdn):
                store.write_exposure(normalize(module, raw))
    correlate_exposures(store, now=DEMO_NOW)


# -- (b) provenance is mandatory ----------------------------------------------

def test_compute_risk_refuses_supplier_without_evidence():
    with SqliteOntologyStore(":memory:") as store:
        _full_pipe(store)
        # sup-e (logistics-e.example) is clean in the mock → no evidence
        assert store.exposures_for_supplier("sup-e") == []
        with pytest.raises(EvidenceRequired):
            compute_risk(store, "sup-e", now=DEMO_NOW)
        # nothing persisted for the refused assessment
        assert all(a["supplier_ref"] != "sup-e" for a in store.risk_assessments())


def test_compute_risk_persists_components_and_evidence():
    with SqliteOntologyStore(":memory:") as store:
        _full_pipe(store)
        flag_active_compromises(store, now=DEMO_NOW)
        a = compute_risk(store, "sup-a", now=DEMO_NOW)
        assert a.evidenced_by, "evidenced_by must be populated"
        assert a.components["exposure_scale"]["dedup_count"] >= 1
        assert a.active_flag is True                 # incident exists for sup-a
        # evidence persisted with both exposure + device kinds
        ev = store.risk_evidence(a.id)
        kinds = {e["evidence_kind"] for e in ev}
        assert "exposure" in kinds and "device" in kinds


# -- (a) active-on-top over the whole pipeline --------------------------------

def test_active_suppliers_rank_strictly_on_top():
    with SqliteOntologyStore(":memory:") as store:
        _full_pipe(store)
        flag_active_compromises(store, now=DEMO_NOW)
        assessments = compute_all(store, now=DEMO_NOW)

        active = [a for a in assessments if a.active_flag]
        nonactive = [a for a in assessments if not a.active_flag]
        assert active and nonactive
        assert min(a.score for a in active) > max(a.score for a in nonactive)
        # active suppliers are exactly the three seeded active domains
        # (sup-h is the multi-tier terminal, active via its subcontract chain).
        assert {a.supplier_ref for a in active} == {"sup-a", "sup-g", "sup-h"}
        # every assessment cites evidence (provenance) and is graded 즉시/주의/관찰
        assert all(a.evidenced_by for a in assessments)
        assert all(a.grade in {"즉시", "주의", "관찰"} for a in assessments)
        # active ⇒ immediate grade
        assert all(a.grade == "즉시" for a in active)


def test_compute_all_skips_clean_suppliers():
    with SqliteOntologyStore(":memory:") as store:
        _full_pipe(store)
        assessments = compute_all(store, now=DEMO_NOW)
        scored = {a.supplier_ref for a in assessments}
        # clean suppliers (sup-e, sup-f) produce no assessment (no provenance)
        assert "sup-e" not in scored and "sup-f" not in scored
