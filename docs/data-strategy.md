# Data Strategy

> 2026-07-08 status note: this document records the earlier conservative
> no-live-data strategy. The current finals strategy is documented in
> `README.md`, `docs/decisions/0009-approved-provider-foundry-lineage.md`, and
> `docs/review/foundry-live-measurement-update.md`: approved filtered
> StealthMole hackathon rows may be used for sanitized lineage and Foundry
> measurement, while raw provider envelopes, passwords, cookies, tokens, API
> keys, JWTs, and reusable secret material remain blocked.

Project Omija currently uses **no live data mode**.

The strategic decision is to show the ontology engine and problem-solving
workflow without handling sensitive records or fetching external data. Feed
integrations are not the product core. The product core is the ontology path and
decision object model.

## Current Data Policy

| Surface | Policy | Reason |
|---|---|---|
| External credential feed | Disabled | May contain sensitive information. |
| Public feed fetching | Disabled in the main demo | The demo should show ontology reasoning, not bulk data collection. |
| Raw secrets | Blocked | No passwords, cookies, JWTs, bearer tokens, or reusable credentials. |
| Notification output | Draft only | Human review remains mandatory. |
| Demo records | Empty candidate slots | Show how data would be reasoned over without displaying data. |

## Ontology Mapping

The ontology remains the decision spine:

```text
CredentialExposure.of -> Identity
CredentialExposure.targets -> Domain
Identity.belongs_to -> Domain
Domain -> Supplier / Prime ownership
Supplier.subcontractsTo -> Supplier
Supplier.supplies -> Prime
Prime.runs -> Program
CompromiseIncident.traverses_* -> path drill-down
RiskAssessment.components <- approved non-sensitive evidence slots
NotificationDraft.cites -> reviewed evidence slots
```

The key modeling decision remains:

- `of` answers whose account would be involved.
- `targets` answers what asset would be involved.

This separation is what makes cross-organization access paths visible without
flattening everything into a table.

## Current Demo Flow

```bash
uv run python scripts/intelligence_demo.py
open out/intelligence_demo.html
```

The command:

1. builds an ontology-engine payload with empty candidate slots;
2. writes a core console page;
3. writes a graph workbench page;
4. writes a response review page;
5. writes `out/intelligence_demo.json`.

No external API is called.

## Claim Boundary

Allowed:

- The demo shows the ontology-centered reasoning engine.
- The page shows how candidate evidence would become supplier, program, risk,
  incident, and draft-review objects.
- Sensitive data handling is disabled.

Not allowed:

- Do not claim live credential ingestion.
- Do not claim public feeds were fetched for the current demo.
- Do not show or store real leaked credentials, cookies, JWTs, bearer tokens, or
  raw secrets.
