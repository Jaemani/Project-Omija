# Demo Script

D4D Track 2/3: ontology-based defense-intelligence reasoning for supply-chain
exposure early warning.

Current data boundary:
- no live credential feed;
- no public-feed fetching in the main demo;
- no raw credential, cookie, JWT, bearer token, or reusable secret;
- notification output is draft-only and human-reviewed;
- candidate evidence slots are intentionally empty.

## Preparation

```bash
uv sync
uv run pytest -q
uv run python scripts/intelligence_demo.py
open out/intelligence_demo.html
```

Optional page variants:

```bash
uv run python scripts/palantir_pages.py
open out/palantir_v1.html
open out/palantir_v2.html
open out/palantir_v3.html
```

## Three-Minute Flow

### Problem

Defense supply chains span primes, first-tier suppliers, and deeper suppliers.
A flat list of leaked-looking records does not answer the operational question:
does a supplier identity create a path to a protected target asset and program?

### Solution

Project Omija models the decision path as ontology objects and links. The
important split is `CredentialExposure.of -> Identity` versus
`CredentialExposure.targets -> Domain`: whose account is involved can differ
from the asset being targeted.

### Demo

1. Open `out/intelligence_demo.html`.
2. Point to the policy gates: live data disabled, sensitive handling blocked,
   draft-only response.
3. Open `out/omija_console_graph.html`.
4. Explain why `of`, `targets`, `subcontractsTo`, `traverses_*`, and `cites`
   are ontology links, not extra columns.
5. Open `out/omija_console_response.html`.
6. Show that `RiskAssessment`, `CompromiseIncident`, `ProgramExposure`, and
   `NotificationDraft` are derived decision objects with blank evidence slots.

### Close

Omija does not rank by volume alone. It prioritizes active paths where an
identity, target asset, supplier chain, prime, and program can be connected by
the ontology. No sensitive data is needed to demonstrate that reasoning core.

## Do Not Claim

- Do not claim live credential ingestion.
- Do not claim public feeds were fetched for the current demo.
- Do not show real leaked records.
- Do not claim notification was sent.
