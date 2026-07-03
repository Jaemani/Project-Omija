"""P5 GenerateNotificationDraft tests.

Covers the decision-list guarantees:
  (a) a draft with empty cites is REFUSED (no draft without provenance),
  (b) no raw secret survives into a draft body (masking guardrail),
  (c) an active-compromise supplier's draft carries the traverses path AND the
      isolation ("격리") recommendation,
  plus persistence of the draft + its cites links.
"""

import re

import pytest

from actions.notify_draft import (
    CitationRequired,
    generate_drafts,
    generate_notification_draft,
)
from adapter.mock import DEMO_NOW, MockExposureSource
from scripts.p5_drafts import build_pipeline
from store.sqlite import SqliteOntologyStore


def test_draft_refused_without_cites():
    """(a) A supplier with no correlated exposures cannot be cited → refused."""
    store = SqliteOntologyStore(":memory:")
    store.upsert_supplier(id="sup-x", name="Nihil Corp", tier=1, criticality="high")
    with pytest.raises(CitationRequired):
        generate_notification_draft(store, "sup-x", now=DEMO_NOW)
    assert store.draft_for_supplier("sup-x") is None      # nothing persisted
    store.close()


def test_draft_has_no_raw_secret():
    """(b) Masking: no synthetic raw secret string reaches any draft body."""
    store, assessments = build_pipeline(DEMO_NOW)
    drafts = generate_drafts(store, assessments, top=3, now=DEMO_NOW)
    assert drafts
    raw = MockExposureSource().raw_secrets()
    for d in drafts:
        assert not any(s in d.body for s in raw), f"raw secret in {d.supplier_ref}"
        assert not re.findall(r"Synthetic-[A-Za-z]+-\d+!", d.body)
        assert not re.findall(r"SID[0-9a-f]{20,}", d.body)
        assert d.status == "draft"       # never sent
        assert d.evidence_refs           # cites non-empty
    store.close()


def test_active_draft_has_path_and_isolation():
    """(c) Active supplier draft summarizes the compromise path and recommends
    account isolation + session revocation + MFA."""
    store, _assessments = build_pipeline(DEMO_NOW)
    assert store.incidents_for_supplier("sup-a")          # precondition: active
    d = generate_notification_draft(store, "sup-a", now=DEMO_NOW)

    assert "격리" in d.body                                # isolation recommendation
    assert "경로" in d.body                                # path summary section
    assert "InfectedDevice" in d.body and "Program" in d.body  # full traverses chain
    assert "세션" in d.body and "MFA" in d.body            # revocation + MFA playbook
    store.close()


def test_draft_persisted_with_cites():
    """The action persists a NotificationDraft with non-empty cites links."""
    store, _assessments = build_pipeline(DEMO_NOW)
    generate_notification_draft(store, "sup-a", now=DEMO_NOW)
    stored = store.draft_for_supplier("sup-a")
    assert stored and stored["status"] == "draft"
    assert store.draft_cites(stored["id"])                # provenance links present
    store.close()


def test_p5_drafts_pipeline_runs_green():
    """P5 CLI smoke: full pipe + draft generation returns RESULT: OK."""
    from scripts.p5_drafts import run
    assert run() == 0
