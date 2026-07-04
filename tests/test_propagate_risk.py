"""PropagateRisk → ProgramExposure roll-up rules (ontology.md §1, §2, §4).

Pins:
  * evidence is MANDATORY — a Program reached only by clean suppliers gets NO
    ProgramExposure (ProgramEvidenceRequired), same rule as ComputeRisk,
  * active_flag = path existence — a Program on a reaching path from a supplier
    with an open CompromiseIncident is active,
  * active Programs sit strictly ABOVE non-active ones (band separation),
  * the MULTI-TIER money-shot: a 2차 terminal infection (sup-h) propagates up and
    lights a Program burning, and that path is recorded as multi-tier evidence,
  * blast-radius: an incident reaching several Primes/Programs records ALL of
    them (no `prop[0]`-only regression).
"""

import pytest

from actions.propagate_risk import (
    PROGRAM_SCORING,
    ProgramEvidenceRequired,
    _build_program_exposure,
    propagate_program_risk,
)
from scripts.p5_drafts import build_pipeline
from adapter.mock import DEMO_NOW
from store.sqlite import SqliteOntologyStore


# --------------------------------------------------------------------------- #
# crafted store: one active program, one quiet program, one evidence-less one
# --------------------------------------------------------------------------- #

def _crafted() -> SqliteOntologyStore:
    store = SqliteOntologyStore(":memory:")
    for sid, crit in (("act", 3), ("quiet", 2), ("clean", 1)):
        store.upsert_supplier(id=sid, name=sid, tier=1, criticality=crit)
    for pr, pg, sens in (("prA", "pgA", "high"), ("prB", "pgB", "medium"),
                         ("prC", "pgC", "low")):
        store.upsert_prime(id=pr, name=pr)
        store.upsert_program(id=pg, name=pg, sensitivity=sens)
        store.link_runs(prime_id=pr, program_id=pg)
    store.link_supplies(supplier_id="act", prime_id="prA")
    store.link_supplies(supplier_id="quiet", prime_id="prB")
    store.link_supplies(supplier_id="clean", prime_id="prC")

    # act: active (incident) + high score; quiet: exposed non-active; clean: none.
    store.record_risk_assessment(
        id="risk:act", supplier_ref="act", score=88.0, grade="즉시",
        active_flag=True, computed_at=DEMO_NOW, components={},
        evidence=[("exp:a", "exposure"), ("dev:a", "device")],
    )
    store.record_incident(
        id="incident:act", supplier_ref="act", opened_at=DEMO_NOW, status="open",
        path=[{"type": "Program", "ref": "pgA"}],
        blast_radius={"primes": [{"ref": "prA"}], "programs": [{"ref": "pgA"}]},
    )
    store.record_risk_assessment(
        id="risk:quiet", supplier_ref="quiet", score=42.0, grade="주의",
        active_flag=False, computed_at=DEMO_NOW, components={},
        evidence=[("exp:q", "exposure")],
    )
    return store


def test_active_program_outranks_quiet_and_evidence_less_is_refused():
    with _crafted() as store:
        pes = propagate_program_risk(store, now=DEMO_NOW)
        by_prog = {pe.program_ref: pe for pe in pes}

        # pgC is reached only by a clean supplier → NO ProgramExposure
        assert "pgC" not in by_prog

        a, q = by_prog["pgA"], by_prog["pgB"]
        assert a.active_flag is True and q.active_flag is False
        assert a.score >= 70.0 and q.score < 70.0        # band separation
        assert a.score > q.score
        assert a.grade == "즉시"
        # evidence carries the incident (active) + the assessment (provenance)
        kinds = {k for _ref, k in a.evidenced_by}
        assert "incident" in kinds and "assessment" in kinds


def test_evidence_less_program_raises_program_evidence_required():
    with _crafted() as store:
        # build directly for pgC's reaching entries (only the clean supplier) →
        # no contributing incident/assessment → refused.
        entries = [{"start": "clean", "path": store.propagation_paths("clean")[0],
                    "prime": "prC"}]
        with pytest.raises(ProgramEvidenceRequired):
            _build_program_exposure(
                store, program={"id": "pgC", "sensitivity": "low"}, entries=entries,
                assessments={}, incidents={}, now=DEMO_NOW, config=PROGRAM_SCORING,
            )


# --------------------------------------------------------------------------- #
# full mock pipeline: multi-tier burning + blast radius
# --------------------------------------------------------------------------- #

def test_multitier_terminal_infection_burns_program():
    """sup-h (2차 terminal) is compromised and reaches its Program only through
    sup-f (tier-1). The Program must roll up ACTIVE, with the multi-tier path
    from sup-h recorded as contributing evidence."""
    store, _assessments = build_pipeline(DEMO_NOW)
    pes = propagate_program_risk(store, now=DEMO_NOW)

    # every Program reached from sup-h must be burning (active)
    sup_h_programs = {p[-1]["ref"] for p in store.propagation_paths("sup-h")}
    assert sup_h_programs
    burning = {pe.program_ref for pe in pes if pe.active_flag}
    assert sup_h_programs <= burning

    # at least one burning Program cites a MULTI-TIER active path starting at sup-h
    multi = [
        cp for pe in pes for cp in pe.contributing_paths
        if cp["active"] and cp["multi_tier"] and cp["start"] == "sup-h"
    ]
    assert multi, "no multi-tier active contributing path from the 2차 terminal"
    assert any("Hotel Microelectronics" in cp["chain"]
               and "Foxtrot Metals" in cp["chain"] for cp in multi)
    store.close()


def test_every_program_exposure_has_evidence_and_grade():
    store, _assessments = build_pipeline(DEMO_NOW)
    pes = propagate_program_risk(store, now=DEMO_NOW)
    assert pes
    for pe in pes:
        assert pe.evidenced_by, f"{pe.program_ref} has no evidence"
        assert store.program_exposure_evidence(pe.id)          # persisted links
        assert pe.grade in {"즉시", "주의", "관찰"}
    store.close()


def test_diamond_chain_dedups_breadth_and_evidence_by_supplier():
    """A diamond (X subcontracts to BOTH Y and Z, both supplying the same Prime→
    Program) sends two paths to one Program. Breadth + evidence must count the
    distinct SUPPLIER once, not per path (pin: no shared-Prime double-count)."""
    with SqliteOntologyStore(":memory:") as store:
        store.upsert_supplier(id="X", name="X", tier=2, criticality=3)
        for yz in ("Y", "Z"):
            store.upsert_supplier(id=yz, name=yz, tier=1, criticality=2)
        store.upsert_prime(id="P", name="P")
        store.upsert_program(id="G", name="G", sensitivity="high")
        store.link_runs(prime_id="P", program_id="G")
        store.link_supplies(supplier_id="Y", prime_id="P")
        store.link_supplies(supplier_id="Z", prime_id="P")
        store.link_subcontract(sub_supplier_id="X", parent_supplier_id="Y")
        store.link_subcontract(sub_supplier_id="X", parent_supplier_id="Z")
        store.record_risk_assessment(
            id="risk:X", supplier_ref="X", score=85.0, grade="즉시",
            active_flag=True, computed_at=DEMO_NOW, components={},
            evidence=[("exp:x", "exposure")],
        )
        store.record_incident(
            id="incident:X", supplier_ref="X", opened_at=DEMO_NOW, status="open",
            path=[{"type": "Program", "ref": "G"}],
            blast_radius={"primes": [{"ref": "P"}], "programs": [{"ref": "G"}]},
        )

        # two DISTINCT paths reach G
        assert len(store.propagation_paths("X")) == 2
        pe = propagate_program_risk(store, now=DEMO_NOW)[0]
        assert pe.program_ref == "G"
        # breadth counts X ONCE, not twice
        assert pe.components["breadth_active"] == 1
        # evidence deduped by ref (incident:X + risk:X = 2, no duplicates)
        refs = [ref for ref, _ in pe.evidenced_by]
        assert len(refs) == len(set(refs)) == 2
        # both distinct chains kept for explainability
        assert len(pe.contributing_paths) == 2


def test_device_compromised_suppliers_derived_from_leaked_of():
    """compromises = leaked∘of: the device's supplier set is the supplier of the
    identity on the exposure it leaked (pin 7 derivation, not a hand-kept fact)."""
    store, _assessments = build_pipeline(DEMO_NOW)
    dev = store.incidents_for_supplier("sup-h")[0]["path"][0]["ref"]   # device id
    assert store.device_compromised_suppliers(dev) == ["sup-h"]
    # blast radius = union of propagation over that DEVICE-level supplier set
    inc = store.incidents_for_supplier("sup-h")[0]
    reached = {n["ref"] for s in store.device_compromised_suppliers(dev)
               for p in store.propagation_paths(s) for n in p if n["type"] == "Program"}
    assert {pr["ref"] for pr in inc["blast_radius"]["programs"]} == reached
    store.close()


def test_blast_radius_records_all_reached_programs_not_just_first():
    """An incident whose supplier reaches multiple Programs must record them ALL
    in blast_radius (regression guard against the old prop[0]-only path)."""
    store, _assessments = build_pipeline(DEMO_NOW)
    inc = store.incidents_for_supplier("sup-h")[0]
    programs = {p["ref"] for p in inc["blast_radius"]["programs"]}
    # sup-h → sup-f → prime-x → {prog-sentinel, prog-harbor}: both are reachable
    assert {"prog-sentinel", "prog-harbor"} <= programs
    # and the representative path only names ONE of them — proving blast != path
    path_programs = {n["ref"] for n in inc["path"] if n["type"] == "Program"}
    assert len(path_programs) == 1 and path_programs < programs
    store.close()
