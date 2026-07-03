"""Foundry/OSDK store skeleton — hot-swap contract without OSDK.

The Foundry store is the migration TARGET for the local SQLite store (ADR-0003).
Today it is a skeleton, and these tests pin the properties day-1 depends on:
  * importing/constructing it must NOT require the (unpublished) OSDK package;
  * it satisfies the same `OntologyStore` Protocol as SQLite (so the swap is a
    genuine one-liner, not wishful typing);
  * every method raises NotImplementedError until OSDK is wired.
"""

from __future__ import annotations

import pytest

from store.base import OntologyStore
from store.foundry import FoundryOntologyStore


def test_imports_and_constructs_without_osdk():
    # No OSDK client, no import error — module load + construction are safe.
    assert FoundryOntologyStore() is not None


def test_satisfies_ontology_store_protocol():
    # Structural hot-swap contract: same surface as SqliteOntologyStore.
    assert isinstance(FoundryOntologyStore(), OntologyStore)


def test_read_method_raises_not_implemented():
    with pytest.raises(NotImplementedError):
        FoundryOntologyStore().suppliers()


def test_write_method_raises_not_implemented():
    with pytest.raises(NotImplementedError):
        FoundryOntologyStore().upsert_supplier(
            id="sup-a", name="Alpha", tier=1, criticality="high"
        )


def test_action_method_raises_not_implemented():
    with pytest.raises(NotImplementedError):
        FoundryOntologyStore().record_risk_assessment(
            id="risk:sup-a", supplier_ref="sup-a", score=1.0, grade="관찰",
            active_flag=False, computed_at=0, components={},
            evidence=[("exp:1", "exposure")],
        )
