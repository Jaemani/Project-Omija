"""CorrelateExposure action (ontology.md §3).

Attributes each Exposure to a Supplier by matching the Identity's email domain
against the registered supplier domains, then confirms the ontology links
`Identity belongs_to Domain` (+ `Domain owned_by Supplier`, already set by the
registry). Every match records a human-readable `match_basis` string —
provenance, so a downstream RiskAssessment can always trace *why* an exposure
was attributed to a supplier (CLAUDE.md §5). Subdomains are resolved to their
registered parent (e.g. `mail.supplier-a.example` → `supplier-a.example`).

Unmatched exposures are left unattributed and counted (not silently dropped).
This is a pure attribution step: no scoring, no send (defensive-only).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CorrelationResult:
    matched_exposures: int = 0
    unmatched_exposures: int = 0
    per_supplier: dict[str, int] = field(default_factory=dict)   # supplier_id -> count
    matches: list[dict] = field(default_factory=list)            # provenance samples
    unmatched: list[dict] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"matched {self.matched_exposures} exposures across "
            f"{len(self.per_supplier)} suppliers; "
            f"unmatched {self.unmatched_exposures}"
        )


def match_domain(
    email_domain: str, registered: set[str]
) -> tuple[str | None, str]:
    """Resolve an email domain to a registered supplier domain.

    Exact match wins; otherwise the longest registered domain that is a parent
    of the email domain (subdomain case). Returns (matched_domain|None, basis).
    """
    ed = (email_domain or "").strip().strip(".").lower()
    if not ed:
        return None, "empty email domain"
    if ed in registered:
        return ed, f"email domain '{ed}' == registered supplier domain"
    parents = [d for d in registered if ed.endswith("." + d)]
    if parents:
        best = max(parents, key=len)  # most specific registered parent
        return best, f"email domain '{ed}' is a subdomain of registered '{best}'"
    return None, f"email domain '{ed}' matched no registered supplier domain"


def correlate_exposures(store: Any, *, now: int | None = None) -> CorrelationResult:
    """Run CorrelateExposure over every stored Exposure. Mutates the store:
    sets Identity→Domain links and writes `exposure_match` provenance rows."""
    now = int(time.time()) if now is None else now
    registered = store.registered_domains()          # {fqdn: supplier_id}
    reg_set = set(registered)
    result = CorrelationResult()

    for row in store.exposures_for_correlation():
        exp_id = row["exposure_id"]
        ident_id = row["identity_id"]
        src_ref = row.get("source_ref")
        email = row.get("email")

        if not email or "@" not in email:
            result.unmatched_exposures += 1
            result.unmatched.append(
                {"exposure_id": exp_id, "reason": "no email identity", "source_ref": src_ref}
            )
            continue

        email_domain = email.rsplit("@", 1)[1]
        matched, basis = match_domain(email_domain, reg_set)
        if matched is None:
            result.unmatched_exposures += 1
            result.unmatched.append(
                {"exposure_id": exp_id, "email_domain": email_domain,
                 "reason": basis, "source_ref": src_ref}
            )
            continue

        supplier_id = registered[matched]
        store.attach_identity_domain(ident_id, matched)   # Identity belongs_to Domain
        store.record_correlation(
            exposure_ref=exp_id, identity_ref=ident_id, domain_ref=matched,
            supplier_id=supplier_id, match_basis=basis, matched_at=now,
        )
        result.matched_exposures += 1
        result.per_supplier[supplier_id] = result.per_supplier.get(supplier_id, 0) + 1
        result.matches.append(
            {"exposure_id": exp_id, "supplier_id": supplier_id, "domain": matched,
             "source_ref": src_ref, "match_basis": basis}
        )

    return result
