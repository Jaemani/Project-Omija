# 2026-07-04 Intelligence Demo Integration

Superseded on 2026-07-05 by the no-live-data directive. Do not use this entry as
the current demo runbook. The active runbook is `docs/demo-runbook.md`; the
active demo script is `scripts/intelligence_demo.py`.

## Current Status

- `scripts/intelligence_demo.py` generates no-live-data ontology pages.
- Candidate evidence slots are empty.
- Public-feed fetching is disabled for the main demo.
- Live credential-feed scripts are neutralized.
- Notification output remains draft-only.

## Active Outputs

```text
out/intelligence_demo.json
out/intelligence_demo.html
out/omija_console_core.html
out/omija_console_graph.html
out/omija_console_response.html
```

## Verification

```bash
uv run pytest -q
uv run python scripts/intelligence_demo.py
```

Expected:
- tests pass;
- demo command prints `RESULT: READY`;
- generated pages contain no live records, tokens, credentials, or source API
  instructions.
