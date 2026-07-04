# Project Omija

**D4D Hackathon Track 2/3: Ontology-Based Supply-Chain Exposure Reasoning**

Project Omija now runs in **no live data mode**. The core artifact is an
ontology-centered decision engine and Palantir-style operating surface. It does
not connect to external credential feeds, fetch public feeds, store secrets, or
show live records.

The operational question remains:

> If a candidate exposure were approved for review, how would the ontology turn
> it into supplier impact, program blast radius, risk objects, and a human
> reviewed response?

## Current Demo

Run:

```bash
uv run python scripts/intelligence_demo.py
open out/intelligence_demo.html
```

The command writes:

- `out/intelligence_demo.json`
- `out/intelligence_demo.html`
- `out/omija_console_core.html`
- `out/omija_console_graph.html`
- `out/omija_console_response.html`

No network call is made. All evidence areas are empty candidate slots.

## What It Proves

- The ontology is the core system, not the feed.
- `CredentialExposure.of -> Identity` and `CredentialExposure.targets -> Domain`
  stay separate.
- The graph path remains `Supplier -> Supplier -> Prime -> Program`.
- Decision outputs are objects: `RiskAssessment`, `CompromiseIncident`,
  `ProgramExposure`, and `NotificationDraft`.
- Notification output is draft-only and human-reviewed.
- Live credential feed and public-feed fetching are disabled by policy.

## Data Boundary

| Surface | Current status |
|---|---|
| Live credential feed | Disabled and code boundary emptied. |
| Public feed fetching | Disabled in the main demo. |
| Sensitive data handling | Blocked. |
| Demo content | Empty candidate slots and ontology structure only. |
| Foundry ontology guide | Kept as the core build reference. |

Do not add API keys, raw credentials, cookies, JWTs, bearer tokens, or live feed
records to this repository.

## Review Docs

- [HANDOFF.md](HANDOFF.md): start here when resuming the project without prior
  conversation context.
- [ontology.md](ontology.md): Foundry Ontology Manager build guide.
- [docs/data-strategy.md](docs/data-strategy.md): current no-live-data data
  boundary.
- [docs/demo-runbook.md](docs/demo-runbook.md): demo flow for the ontology
  engine pages.
- [docs/decisions/0008-dashboard-first-demo-surface.md](docs/decisions/0008-dashboard-first-demo-surface.md):
  decision record for the dashboard-first surface.
- [docs/changelog/stealthmole-neutralized-2026-07-05.md](docs/changelog/stealthmole-neutralized-2026-07-05.md):
  live-feed boundary neutralization record.

## Repository Map

- `adapter/`: ontology exposure protocol and mock/synthetic helpers. Live
  external adapter is intentionally empty.
- `store/`: `OntologyStore` protocol, SQLite store, Foundry OSDK read side.
- `actions/`: correlation, scoring, propagation, and notification draft logic.
- `scripts/`: ontology demo pages, reports, evaluation, Foundry helpers.
- `docs/`: strategy, runbook, ADRs, specs, and review notes.
- `out/`: generated demo artifacts that are safe to review when allowlisted.

## Verification

```bash
uv run pytest -q
uv run python scripts/intelligence_demo.py
```

Expected terminal result: `RESULT: READY`.
