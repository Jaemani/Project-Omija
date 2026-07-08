# Claude Prompt — Palantir MCP Live Load Completion

Use this prompt for an agent that has Palantir MCP / Foundry UI access.

```text
Project: /Users/jaeman/Codes/D4D/Project-Omija

Goal:
Finish Foundry ontology datasource/index refresh for approved filtered StealthMole hackathon rows.

Current completed state:
- Codex collected/imported 150 approved provider rows.
- Sanitized Foundry-ready CSV bundle exists at:
  out/foundry_live_measurement/
- Existing ontology backing dataset CSV upload succeeded:
  upload_result.json => 14/14 OK
- Explicit schema PUT succeeded:
  schema_put_result.json => 14/14 OK
- Separate schema-aware live measurement datasets were created:
  schema_dataset_create_result.json => 14/14 OK
- Foundry SQL count measurement succeeded:
  sql_measurement_result.json => 14/14 OK
- Current remaining blocker:
  readback_result.json => live PKs not visible through OSDK object reads yet.

Hard rules:
- Do not read or display raw files under data/private_candidates/.
- Do not expose API keys, JWTs, raw provider envelopes, raw emails, passwords, cookies, or tokens.
- Use only sanitized files under out/foundry_live_measurement/.
- Do not claim complete ontology E2E until readback_result.json ok=true.

Tasks:
1. In Foundry UI/MCP, inspect datasource/index status for:
   Supplier, Program, Domain, Identity, CredentialExposure, InfectedDevice, ThreatSource.
2. Confirm the object/link datasource mappings still point to the known backing dataset RIDs already listed in upload_result.json.
3. Trigger or wait for datasource/index refresh if Foundry exposes that control.
4. Re-run:
   uv run python scripts/foundry_live_readback.py
5. If readback succeeds, update:
   out/foundry_live_measurement/readback_result.json
   docs/review/foundry-live-measurement-update.md
   docs/changelog/finals-live-foundry-lineage-2026-07-05.md
6. If readback still fails, document exact Foundry UI/MCP blocker in:
   docs/review/foundry-live-measurement-update.md

Expected final claim only after success:
Live approved provider rows are visible as Foundry ontology objects and links through OSDK readback.
```
