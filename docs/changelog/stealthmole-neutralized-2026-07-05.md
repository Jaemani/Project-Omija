# 2026-07-05 StealthMole Boundary Neutralized

## Why

Owner directive: the StealthMole source may contain sensitive information.
Project Omija must not handle that data in this repo. The demo direction is now
an ontology-engine operating surface with empty candidate slots.

## What Changed

The live credential-feed boundary was emptied:

- `adapter/stealthmole.py`
- `scripts/p0b_recon.py`
- `scripts/p0c_live_pipeline.py`
- `scripts/stealthmole_auth_evidence.py`

The related generated artifact was removed:

- `out/p0b/stealthmole_auth_evidence.json`

The demo generator was changed:

- `scripts/intelligence_demo.py` no longer calls public feed collection.
- `scripts/intelligence_demo.py` no longer calls credential-feed auth evidence.
- It now writes no-live-data ontology pages:
  - `out/intelligence_demo.html`
  - `out/omija_console_core.html`
  - `out/omija_console_graph.html`
  - `out/omija_console_response.html`

Tests were changed to enforce the neutralized boundary instead of exercising JWT
or live-source behavior.

## Current Claim Boundary

Allowed:

- The demo shows the ontology engine and problem-solving workflow.
- Candidate evidence slots are empty.
- Sensitive-data handling is disabled.

Not allowed:

- No live credential-feed ingestion claim.
- No public-feed-fetch claim for the current demo.
- No real leaked credential, cookie, JWT, bearer token, or raw secret.

## Verification

```bash
uv run pytest -q
uv run python scripts/intelligence_demo.py
rg -n "StealthMole|STEALTHMOLE|Authorization: Bearer|eyJ" \
  out/intelligence_demo.html out/intelligence_demo.json out/omija_console_*.html
```

Expected:

- tests pass;
- demo prints `RESULT: READY`;
- grep returns no matches for generated demo pages.
