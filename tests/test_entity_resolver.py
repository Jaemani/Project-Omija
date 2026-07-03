"""(f) EntityResolver: rule-based merge proposals + human-confirm merge.

Nothing merges automatically (human-on-the-loop). A proposal is created for the
`j.kim@` / `jkim@` variant pair; `confirm_merge` collapses the two Identities
while preserving every Exposure (provenance)."""

import pytest

from actions.entity_resolver import (
    confirm_merge,
    normalize_local_part,
    propose_merges,
)
from actions.correlate import correlate_exposures
from adapter.base import normalize
from adapter.mock import DEMO_NOW, MODULES, RESOLUTION_DOMAIN, MockExposureSource
from registry.loader import load_into_store
from store.sqlite import SqliteOntologyStore


def _pipe(store) -> None:
    load_into_store(store)
    src = MockExposureSource()
    for fqdn in src.domains():
        for module in MODULES:
            for raw in src.search(module, "domain", fqdn):
                store.write_exposure(normalize(module, raw))
    correlate_exposures(store, now=DEMO_NOW)


# -- pure normalizer -----------------------------------------------------------

def test_normalize_local_part_dot_and_tag_insensitive():
    assert normalize_local_part("J.Kim+ci@acme.example") == "jkim"
    assert normalize_local_part("jkim@acme.example") == "jkim"
    assert normalize_local_part("j.kim@acme.example") == "jkim"


def test_normalize_local_part_rejects_non_email():
    assert normalize_local_part("localadmin") is None
    assert normalize_local_part(None) is None
    assert normalize_local_part("") is None


# -- proposal generation -------------------------------------------------------

def test_propose_merges_flags_the_variant_pair_only():
    with SqliteOntologyStore(":memory:") as store:
        _pipe(store)
        res = propose_merges(store, now=DEMO_NOW)
        assert len(res.proposals) == 1, "exactly one variant pair is seeded"
        p = res.proposals[0]
        assert {p.identity_a, p.identity_b} == {
            f"id:j.kim@{RESOLUTION_DOMAIN}", f"id:jkim@{RESOLUTION_DOMAIN}",
        }
        assert p.status == "pending"
        assert "normalized handle 'jkim'" in p.basis   # provenance recorded
        # persisted as pending — nothing merged yet
        assert len(store.merge_proposals(status="pending")) == 1


def test_propose_merges_is_deterministic():
    with SqliteOntologyStore(":memory:") as a, SqliteOntologyStore(":memory:") as b:
        _pipe(a)
        _pipe(b)
        pa = [p.id for p in propose_merges(a, now=DEMO_NOW).proposals]
        pb = [p.id for p in propose_merges(b, now=DEMO_NOW).proposals]
        assert pa == pb


# -- human-confirm merge -------------------------------------------------------

def test_confirm_merge_collapses_identity_preserving_exposures():
    with SqliteOntologyStore(":memory:") as store:
        _pipe(store)
        before_exposures = len(store.all_exposures())
        before_identities = len(store.identities())

        propose_merges(store, now=DEMO_NOW)
        pid = store.merge_proposals(status="pending")[0]["id"]
        confirm_merge(store, pid)

        # one Identity removed, exposures fully preserved (provenance intact)
        assert len(store.identities()) == before_identities - 1
        assert len(store.all_exposures()) == before_exposures
        # both of the variant's exposures now hang off the surviving identity
        keep = f"id:j.kim@{RESOLUTION_DOMAIN}"
        idents = {i["id"] for i in store.identities()}
        assert keep in idents
        assert f"id:jkim@{RESOLUTION_DOMAIN}" not in idents
        # proposal transitioned to confirmed
        assert len(store.merge_proposals(status="confirmed")) == 1


def test_confirm_merge_is_idempotent_and_guards_status():
    with SqliteOntologyStore(":memory:") as store:
        _pipe(store)
        propose_merges(store, now=DEMO_NOW)
        pid = store.merge_proposals(status="pending")[0]["id"]
        confirm_merge(store, pid)
        # re-confirming an already-merged proposal is refused
        with pytest.raises(ValueError):
            confirm_merge(store, pid)
        # unknown proposal refused
        with pytest.raises(ValueError):
            confirm_merge(store, "merge:nope|nope")
