# architecture.md — no-live-data ontology engine

Status: updated 2026-07-05.

The active architecture is a static, no-live-data ontology reasoning engine.
Historical live-feed assumptions are superseded and intentionally redacted from
the active design.

## Components

```text
scripts/intelligence_demo.py
  -> out/intelligence_demo.json
  -> out/intelligence_demo.html
  -> out/omija_console_core.html
  -> out/omija_console_graph.html
  -> out/omija_console_response.html

scripts/palantir_pages.py
  -> out/palantir_v1.html
  -> out/palantir_v2.html
  -> out/palantir_v3.html

scripts/foundry_seed.py
  -> out/foundry_seed/*.csv with neutral placeholder source IDs
```

## Engine Flow

```text
candidate slot
  -> resolve Identity via of
  -> resolve target Domain via targets
  -> traverse Supplier.subcontractsTo*
  -> reach Prime.runs Program
  -> create RiskAssessment / CompromiseIncident / ProgramExposure
  -> prepare NotificationDraft with cites links
```

## Invariants

- `of` and `targets` stay separate.
- Active path beats passive volume.
- Decision objects require provenance links.
- Draft response has no send action.
- Placeholder source IDs use `src:candidate:empty`.

## Verification

```bash
uv run pytest -q
uv run python scripts/intelligence_demo.py
uv run python scripts/palantir_pages.py
```
