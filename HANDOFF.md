# Project Omija Handoff

Last updated: 2026-07-05 KST

This is the source of truth for resuming the project without prior conversation
context.

## Current Direction

Project Omija is now a **no live data ontology-engine demo**.

The project should not connect to external credential feeds, fetch public feeds,
store secrets, or display live records. The page should show how the ontology
core solves the supply-chain exposure problem with empty candidate slots.

The central question:

> If approved non-sensitive candidate evidence existed, how would the ontology
> resolve it into identity, target asset, supplier path, program impact, risk
> decision objects, and a human-reviewed response?

## Hard Rules

- Do not handle StealthMole data.
- Do not add credential-feed API keys.
- Do not fetch public data for the main demo.
- Do not store or show passwords, cookies, JWTs, bearer tokens, or raw secrets.
- Do not claim live credential ingestion.
- Keep evidence, recipient, and notification body fields blank until an
  approved non-sensitive evidence package exists.

## Current Demo

```bash
uv run python scripts/intelligence_demo.py
open out/intelligence_demo.html
```

Generated files:

- `out/intelligence_demo.json`
- `out/intelligence_demo.html`
- `out/omija_console_core.html`
- `out/omija_console_graph.html`
- `out/omija_console_response.html`

The command makes no network calls.

## What The Demo Shows

The demo is a Palantir-style operating surface with three views:

1. `Core Console`
   - policy gates;
   - decision steps;
   - no-live-data state.
2. `Graph Workbench`
   - empty candidate path;
   - `of` and `targets` separation;
   - supplier-to-program graph spine.
3. `Response Review`
   - decision object registry;
   - `NotificationDraft` as draft only;
   - blank candidate slots for future approved evidence.

## Ontology Core

Object types kept as the core model:

- `Supplier`
- `Prime`
- `Program`
- `Domain`
- `Identity`
- `CredentialExposure`
- `InfectedDevice`
- `ThreatSource`
- `RiskAssessment`
- `CompromiseIncident`
- `ProgramExposure`
- `NotificationDraft`

Important links:

```text
CredentialExposure.of -> Identity
CredentialExposure.targets -> Domain
Identity.belongs_to -> Domain
Supplier.owns -> Domain
Supplier.subcontractsTo -> Supplier
Supplier.supplies -> Prime
Prime.runs -> Program
CompromiseIncident.traverses_* -> path nodes
NotificationDraft.cites -> reviewed evidence slots
```

The key idea is still `of` vs `targets`:

- `of`: whose account would be involved;
- `targets`: what access surface would be involved.

This is what lets the system reason about cross-organization access without a
flat table.

## Neutralized Boundary

These files are intentionally empty stubs and must stay that way unless the
owner explicitly reverses the directive:

- `adapter/stealthmole.py`
- `scripts/p0b_recon.py`
- `scripts/p0c_live_pipeline.py`
- `scripts/stealthmole_auth_evidence.py`

The previous generated auth artifact was removed:

- `out/p0b/stealthmole_auth_evidence.json`

`.env.example` no longer asks for credential-feed keys.

## Current Claims

Allowed:

- Omija demonstrates an ontology-centered decision engine.
- The page shows how candidate evidence would flow through identity, target,
  supplier path, program impact, risk objects, incident objects, and draft
  response.
- Sensitive data handling is disabled.

Not allowed:

- Do not say live StealthMole data was ingested.
- Do not say public feeds were fetched for the current demo.
- Do not show real credential, leak, cookie, or token data.

## Key Files

- `README.md`
- `HANDOFF.md`
- `ontology.md`
- `docs/data-strategy.md`
- `docs/demo-runbook.md`
- `docs/changelog/stealthmole-neutralized-2026-07-05.md`
- `scripts/intelligence_demo.py`

## Verification

```bash
uv run pytest -q
uv run python scripts/intelligence_demo.py
rg -n "StealthMole|STEALTHMOLE|Authorization: Bearer|eyJ" out/intelligence_demo.html out/intelligence_demo.json out/omija_console_*.html
```

Expected:

- tests pass;
- demo command prints `RESULT: READY`;
- grep returns no matches for the generated demo pages.

## Remaining Work

1. Polish the no-live-data Palantir-style surfaces.
2. If the visual direction is ambiguous, create multiple static variants and let
   the user choose.
3. Keep all sensitive-data and live-feed surfaces blank.
4. Keep the ontology model and problem-solving flow explicit.
5. Do not reintroduce feed ingestion without a new explicit owner directive.
