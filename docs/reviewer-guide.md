# Reviewer Guide

Use this page when handing the project to another teammate or judge.

## Review Order

1. Read [HANDOFF.md](../HANDOFF.md) for current project direction.
2. Read [README.md](../README.md) for the entrypoint.
3. Read [docs/data-strategy.md](data-strategy.md) for data boundaries.
4. Read [docs/demo-runbook.md](demo-runbook.md) for the demo flow.
5. Read [ontology.md](../ontology.md) for the Foundry ontology structure.
6. Read [docs/decisions/0007-osint-data-fusion.md](decisions/0007-osint-data-fusion.md)
   and [docs/decisions/0008-dashboard-first-demo-surface.md](decisions/0008-dashboard-first-demo-surface.md).

## Verification Commands

```bash
uv run pytest -q
uv run python scripts/intelligence_demo.py
uv run python scripts/palantir_pages.py
open out/intelligence_demo.html
```

## Expected Artifacts

| Artifact | Meaning |
|---|---|
| `out/intelligence_demo.json` | Machine-readable no-live-data ontology summary. |
| `out/intelligence_demo.html` | Main operating-surface report. |
| `out/omija_console_core.html` | Policy gates and decision workflow. |
| `out/omija_console_graph.html` | Ontology graph path explanation. |
| `out/omija_console_response.html` | Decision objects and draft-only response. |
| `out/palantir_v1.html` | Variant 1 page for comparison. |
| `out/palantir_v2.html` | Variant 2 page for comparison. |
| `out/palantir_v3.html` | Variant 3 page for comparison. |

## What To Confirm

- No external data fetch is part of the main demo.
- Evidence, recipient, notification body, and cited-record slots are blank.
- `of` and `targets` are explained as separate links.
- `subcontractsTo` explains variable-depth supplier propagation.
- `traverses_*` links explain incident path drill-down.
- `NotificationDraft.cites` and draft-only state explain review provenance.
- Risk bands are presented as ontology-path outcomes, not volume sorting.
- Generated artifacts contain no API keys, JWTs, bearer tokens, raw passwords,
  cookies, or reusable secrets.

## Claim Boundary

Allowed:
- "Omija demonstrates an ontology-centered reasoning engine."
- "The demo shows where approved candidate evidence would attach."
- "Sensitive data handling and live data fetching are disabled."
- "Notifications are draft-only and require human review."

Not allowed:
- "Live credential data was ingested."
- "Public feeds were fetched for the current demo."
- "The seed evidence is real leaked data."
- "A notification was sent."
