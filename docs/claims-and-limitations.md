# Claims and Limitations

This document prevents overclaiming during demo, judging, or handoff.

## Safe Claims

These are technically supported by the current repository.

1. Omija models defense supply-chain exposure as an ontology, not a flat leak table.
2. The current ontology separates account owner (`of`) from target asset (`targets`).
3. The system can represent a tier-2 supplier path to tier-1 supplier, prime, and program.
4. The mock engine correlates synthetic credential exposure and infostealer-device records into supplier risk ranking.
5. The synthetic fixture proves active-on-top behavior: active compromise candidates rank above high-volume passive leaks.
6. The current readiness check verifies collection-plan coverage and ranking invariants.
7. Public context sources are used as background/asset-risk context, not as credential evidence.
8. Notification output is a human-reviewed `NotificationDraft`; there is no automatic send action.

## Conditional Claims

These are valid only if an approved private feed and handling policy are connected later.

1. Omija can ingest approved exposure candidates through a normalization boundary.
2. CL-like inputs can become `CredentialExposure` records after normalization.
3. CDS-like inputs can become `InfectedDevice` records after normalization.
4. DT/TT/country/keyword results can enrich `ThreatSource` and review queues.
5. Supplier ranking can be computed on real candidate evidence if raw secrets are discarded and normalized fields are retained.

## Do Not Claim

Do not say these.

1. "Omija proves a supplier is currently breached."
2. "Omija has ingested live credential records in this public demo."
3. "Session cookies are valid right now."
4. "APT attribution is confirmed from darkweb/Telegram mentions."
5. "The reported precision/recall is field performance."
6. "The system automatically notifies suppliers."
7. "Public CVE/IOC context is credential evidence."

## Correct Technical Framing

Use this phrasing:

> Omija produces active-compromise candidates and response priorities. Confirmation requires VPN, SSO, IAM, EDR, mail, or supplier-response evidence.

Use this for metrics:

> The synthetic evaluation proves the pipeline is wired correctly and enforces the active-on-top invariant. It is not a claim of real-world detection precision.

Use this for private feeds:

> Approved private exposure feeds would enter through a normalization boundary that stores only masked, deduplicated, provenance-linked fields.

## Evidence Labels

| Label | Meaning | Safe use |
|---|---|---|
| `SYNTHETIC` | Made-up suppliers, identities, devices, exposures | Demo corpus and engine proof |
| `PUBLIC_CONTEXT` | Public CVE/advisory/technique/breach metadata | Asset-risk background |
| `ENGINE` | Computed by local scoring/path logic | Ranking, incidents, program rollups |
| `LIVE_FOUNDRY` | Foundry object/action/readback evidence | Ontology/workflow proof |
| `LOCKED_PRIVATE` | Approved feed contract slot, not displayed | Future integration boundary |

## Judge Q&A

### Is this just a dashboard?

No. The important part is the object/link model: `of`, `targets`, `subcontractsTo`, `traverses_*`, and `cites`. The pages are views over that model.

### Why not show real leaked credentials?

Real leaked credentials are victim data. Showing them in a hosted demo or recording would create a new exposure surface. The demo uses synthetic entities to prove the reasoning pipeline and public context to explain why the monitored assets matter.

### What would make this production-ready?

Approved supplier registry, approved private-feed handling policy, RBAC for sensitive evidence, raw-secret destruction audit, and confirmation integrations with VPN/SSO/IAM/EDR/mail logs.

### What is the core differentiator?

Omija ranks by structural risk, not raw volume. A small active path involving recent infostealer evidence, session/account hints, high-risk target asset, and program reachability outranks a large passive leak list.
