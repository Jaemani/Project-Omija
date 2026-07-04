# Project Omija

**D4D Hackathon Track 2/3: Supply-chain Credential Exposure Early Warning**

Project Omija connects public OSINT, credential-exposure signals, and a Foundry
ontology to answer one operational question:

> Which supplier appears to create an active path into a protected defense
> program, and what action should be prepared first?

## Current Demo

Run the integrated demo:

```bash
uv run python scripts/intelligence_demo.py
open out/intelligence_demo.html
```

The command:

1. collects real public OSINT summaries from NVD, CISA KEV, MITRE ATT&CK, and
   abuse.ch URLhaus;
2. verifies the Foundry ontology through OSDK readback;
3. runs the blast-radius check for `exp:micro-h:active`;
4. records StealthMole auth status without exposing secrets;
5. writes `out/intelligence_demo.json` and the dashboard-first
   `out/intelligence_demo.html`.

Foundry-only fallback:

```bash
uv run python scripts/final_demo_check.py --full
open out/foundry_demo.html
```

## What It Proves

- `CredentialExposure.of -> Identity` identifies whose account was exposed.
- `CredentialExposure.targets -> Domain` identifies the asset that appears
  reachable.
- Supplier and prime links propagate the blast radius to programs.
- Public OSINT adds vulnerability and threat context to the target asset class.
- Notification output remains a human-reviewed draft.
- The main dashboard shows operational value first, then path, evidence,
  ranked response, draft advisory, and collection status.

## Data Boundary

| Layer | Current status |
|---|---|
| Public OSINT | Real public data collected at demo time. |
| Foundry ontology path | Live OSDK readback from the current ontology seed. |
| Foundry credential exposure seed | Synthetic and safe for repeatable demo. |
| StealthMole live credential feed | Integration exists, but `/user/quotas` currently returns `401`. |

Do not claim synthetic seed credentials are real leaked data. Real credential
ingestion is only claimed after `scripts/p0c_live_pipeline.py` succeeds with an
authorized registry and working StealthMole authentication.

## Review Docs

- [HANDOFF.md](HANDOFF.md): start here when resuming the project without prior
  conversation context.
- [docs/data-strategy.md](docs/data-strategy.md): data sources, ontology
  mapping, and claim boundaries.
- [docs/demo-runbook.md](docs/demo-runbook.md): exact demo sequence and
  fallback flow.
- [docs/decisions/0007-osint-data-fusion.md](docs/decisions/0007-osint-data-fusion.md):
  decision record for the OSINT overlay.
- [docs/decisions/0008-dashboard-first-demo-surface.md](docs/decisions/0008-dashboard-first-demo-surface.md):
  decision record for the dashboard-first demo surface.
- [docs/changelog/intelligence-demo-2026-07-04.md](docs/changelog/intelligence-demo-2026-07-04.md):
  change inventory and latest verification.
- [docs/reviewer-guide.md](docs/reviewer-guide.md): checklist for independent
  verification.
- [ontology.md](ontology.md): Foundry Ontology Manager build guide.

## Live Credential Pipeline

Use only for authorized domains:

```bash
uv run python scripts/p0c_live_pipeline.py \
  --authorized \
  --registry registry/suppliers.live.yaml \
  --domains REPLACE_WITH_AUTHORIZED_DOMAIN \
  --modules cds
```

Guardrails:

- `--authorized` is mandatory.
- Domains must be in the private registry.
- Synthetic domains are refused by the live runner.
- Raw reusable secrets are not stored.
- `.env` stays local and is not committed.

## Repository Map

- `adapter/`: `ExposureSource` protocol and StealthMole adapter.
- `store/`: `OntologyStore` protocol, SQLite store, Foundry OSDK store.
- `actions/`: correlation, scoring, propagation, and notification draft logic.
- `scripts/`: demo, reports, evaluation, OSINT collection, live pipeline.
- `registry/`: synthetic seed and private live registry template.
- `docs/`: strategy, runbook, ADRs, specs, and review notes.
- `out/`: generated demo artifacts that are safe to review when explicitly
  allowlisted in `.gitignore`.

## Verification

```bash
uv run pytest -q
uv run python scripts/intelligence_demo.py
```

Expected terminal result: `RESULT: READY`.
