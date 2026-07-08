# Reviewer Guide

2026-07-08 status note: `README.md` is the primary project index and should be
read first. Earlier no-live-data demo documents remain for history, but the
latest finals state includes approved filtered StealthMole hackathon row
lineage, sanitized Foundry measurement, and an explicit limitation that Ontology
OSDK live PK readback remains index-refresh pending.

## Review Order

1. Read [README.md](../README.md) primary status and project index.
2. Read [ADR-0009](decisions/0009-approved-provider-foundry-lineage.md) latest data-lineage decision.
3. Read [Foundry Live Measurement Update](review/foundry-live-measurement-update.md).
4. Read [Final Demo Alignment](final-demo-alignment.md).
5. Read [HANDOFF.md](../HANDOFF.md) for broader historical context.
6. Read [ontology.md](../ontology.md) Foundry ontology structure.

## Verification Commands

```bash
uv run pytest -q
make build
uv run python scripts/foundry_live_measurement.py
```

Expected today:

- tests pass;
- static pages regenerate into `out/`;
- approved provider lineage is shown only as sanitized rows and counts;
- no API keys, JWTs, raw passwords, cookies, tokens, or raw provider envelopes appear in public artifacts;
- Foundry SQL measurement remains valid;
- `scripts/foundry_live_readback.py` may still return `NOT_INDEXED` until Foundry ontology datasource/index refresh completes.

## Main Artifacts

| Artifact | Meaning |
|---|---|
| `out/omija_console_home.html` | Steady-state operating console. |
| `out/data_coverage_map.html` | Data/source/engine/Foundry coverage map. |
| `out/data_evidence_brief.html` | Public OSINT and provider boundary brief. |
| `out/data_lineage_live.html` | Approved provider run lineage. |
| `out/foundry_live_measurement.html` | Foundry sanitized dataset measurement report. |
| `out/omija_demo.html` | Synthetic incident reasoning report. |
| `out/program_threat_view.html` | Optional program reverse-query backup view. |

## What To Confirm

- `of` and `targets` are explained as separate links.
- `subcontractsTo*` explains variable-depth supplier propagation.
- Active candidates are presented as verification priority, not confirmed compromise.
- `NotificationDraft` remains draft-only and human-reviewed.
- Approved provider rows are redacted before public/static outputs.
- Synthetic incident scenario and approved provider measurement are clearly labeled as different layers.

## Claim Boundary

Allowed:

- "Omija demonstrates an ontology-centered reasoning engine."
- "Approved filtered StealthMole hackathon rows are used after redaction for lineage and Foundry measurement."
- "The synthetic incident scenario shows where active candidate evidence becomes supplier/program/draft decisions."
- "Notifications are draft-only and require human review."

Not allowed:

- "Raw leaked credentials, cookies, tokens, or provider envelopes are stored or displayed."
- "The approved provider run proves a confirmed breach."
- "Foundry Ontology OSDK live object readback is fully solved."
- "The seed evidence is real leaked defense data."
- "A notification was sent automatically."
