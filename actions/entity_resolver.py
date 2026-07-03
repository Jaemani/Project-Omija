"""EntityResolver (P2) — rule-based identity de-duplication *proposals*.

A single person often appears under several email spellings — `j.kim@acme` vs
`jkim@acme`, `a.b+ci@acme` vs `ab@acme`. Because ingest keys Identity by the
literal email, these land as distinct Identity rows. This resolver normalizes
the email local-part (lowercase, drop a `+tag`, remove dots) and, WITHIN THE SAME
DOMAIN, groups identities whose normalized handle collides. Each collision is
recorded as a **MergeProposal** (candidate pair + human-readable basis +
status=pending) in the store.

Human-on-the-loop (CLAUDE.md §4): nothing is merged automatically. A merge only
happens when `confirm_merge()` is called for a specific proposal — which repoints
every Exposure/Device/match link from the dropped Identity onto the kept one and
deletes the variant row (provenance of the proposal is preserved as an audit
record).

No LLM (decision 1): the demo needs determinism, and semantic/LLM-assisted
merging is deferred to the AIP Logic layer. Rules only; every match records why.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MergeProposal:
    id: str
    identity_a: str          # canonical (keep) identity id
    identity_b: str          # variant (drop-on-confirm) identity id
    basis: str               # rule provenance
    status: str = "pending"  # pending | confirmed | rejected
    created_at: int = 0


@dataclass
class ResolutionResult:
    proposals: list[MergeProposal] = field(default_factory=list)

    def summary(self) -> str:
        return f"{len(self.proposals)} merge proposal(s) (pending human review)"


def normalize_local_part(email: str | None) -> str | None:
    """Canonical handle for an email local-part: lowercase, drop a `+tag`
    suffix, remove dots. `J.Kim+ci@acme` → `jkim`. Returns None if not an
    email or the handle is empty."""
    if not email or "@" not in email:
        return None
    local = email.partition("@")[0].strip().lower()
    local = local.split("+", 1)[0]      # drop +tag
    local = local.replace(".", "")      # dot-insensitive
    return local or None


def _email_domain(email: str) -> str:
    return email.rsplit("@", 1)[1].strip().lower()


def propose_merges(store: Any, *, now: int | None = None) -> ResolutionResult:
    """Scan Identity rows, group by (normalized-handle, email-domain), and
    persist a MergeProposal for each colliding pair (canonical = lowest id).
    Deterministic and idempotent: proposal ids are keyed by the identity pair."""
    now = int(time.time()) if now is None else now
    result = ResolutionResult()

    groups: dict[tuple[str, str], list[dict]] = {}
    for ident in store.identities():
        email = ident.get("email")
        norm = normalize_local_part(email)
        if not norm:
            continue                      # username-only identities are not merged here
        groups.setdefault((norm, _email_domain(email)), []).append(ident)

    for (norm, domain), members in sorted(groups.items()):
        if len(members) < 2:
            continue
        members = sorted(members, key=lambda r: r["id"])
        canonical = members[0]
        for variant in members[1:]:
            pid = f"merge:{canonical['id']}|{variant['id']}"
            basis = (
                f"same normalized handle '{norm}' at domain '{domain}': "
                f"{variant.get('email')} ≈ {canonical.get('email')} "
                f"(dot/tag-insensitive local-part)"
            )
            store.record_merge_proposal(
                id=pid, identity_a=canonical["id"], identity_b=variant["id"],
                basis=basis, status="pending", created_at=now,
            )
            result.proposals.append(
                MergeProposal(
                    id=pid, identity_a=canonical["id"], identity_b=variant["id"],
                    basis=basis, status="pending", created_at=now,
                )
            )

    return result


def confirm_merge(store: Any, proposal_id: str) -> None:
    """Human approval step: merge the two identities named by `proposal_id` —
    repoint all Exposure/Device/match links from identity_b onto identity_a,
    drop the variant row, and mark the proposal confirmed. Raises ValueError if
    the proposal is unknown or not pending (idempotency + audit safety)."""
    proposals = {p["id"]: p for p in store.merge_proposals()}
    proposal = proposals.get(proposal_id)
    if proposal is None:
        raise ValueError(f"unknown merge proposal: {proposal_id}")
    if proposal["status"] != "pending":
        raise ValueError(
            f"merge proposal {proposal_id} is '{proposal['status']}', not pending"
        )
    store.merge_identities(keep_id=proposal["identity_a"], drop_id=proposal["identity_b"])
    store.set_merge_proposal_status(proposal_id, "confirmed")
