# direction.md — no-live-data project backbone

Status: updated 2026-07-05.

Project Omija is an ontology-centered early-warning system for supply-chain
credential exposure. The current demo does not ingest live credential data or
public feeds. It shows how approved candidate evidence would move through the
ontology and become reviewable decisions.

## Problem

Defense supply chains include primes, tier-1 suppliers, and deeper suppliers.
Flat exposure lists cannot answer the operational question:

```text
Does a supplier identity create a path to a protected target asset and program?
```

## Core Bet

The ontology is the product core:

- `of` identifies whose account is involved.
- `targets` identifies what access surface is involved.
- `subcontractsTo` preserves variable-depth supplier paths.
- `traverses_*` preserves incident drill-down.
- `cites` preserves draft-response provenance.

## Current Demo Boundary

- Candidate data slots are empty.
- No live credential-feed code is active.
- No public feed is fetched.
- Raw secrets are blocked.
- Notification output is draft-only.

## What To Show

1. Candidate signal slot.
2. Identity and target asset resolution.
3. Supplier-to-prime-to-program traversal.
4. Derived decision objects:
   `RiskAssessment`, `CompromiseIncident`, `ProgramExposure`.
5. Human-reviewed `NotificationDraft`.

## What Not To Do

- Do not resume historical live-feed implementation.
- Do not add endpoint/auth/key details to active docs.
- Do not claim real credential ingestion.
- Do not show real leaked records.
