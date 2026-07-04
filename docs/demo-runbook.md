# Demo Runbook

Use this sequence for the current no-live-data demo. The goal is to prove the
ontology engine and decision workflow, not to show feed collection.

## 0. Preflight

```bash
uv run python scripts/intelligence_demo.py
open out/intelligence_demo.html
```

Pass condition:

- terminal ends with `RESULT: READY`;
- `out/intelligence_demo.json` exists;
- `out/intelligence_demo.html` opens;
- no external feed command is run.

## 1. Opening Claim

Use this message:

> Omija is an ontology-centered operating surface. It shows how a candidate
> supply-chain exposure would be resolved into identity, target asset, supplier
> path, program impact, decision objects, and a human-reviewed response, without
> handling sensitive data.

Point to:

- `Live Data: Disabled`
- `Sensitive Handling: Blocked`
- `Ontology Core: Ready`
- `Action Output: Draft Only`

## 2. Core Console

Open:

```bash
open out/omija_console_core.html
```

Explain:

- evidence slots are empty by design;
- the system is proving the reasoning structure;
- policy gates prevent live feed access and raw secret handling.

## 3. Graph Workbench

Open:

```bash
open out/omija_console_graph.html
```

Explain the path:

```text
Candidate Signal
-> Identity resolved by of
-> Target Asset resolved by targets
-> Supplier Path
-> ProgramExposure
```

The important point is that `of` and `targets` are separate. This allows the
system to represent a supplier identity and a target asset owned by another
organization.

## 4. Response Review

Open:

```bash
open out/omija_console_response.html
```

Explain:

- derived decisions are ontology objects;
- `NotificationDraft` remains draft-only;
- recipient, body, and evidence citations remain blank until an approved
  non-sensitive evidence package exists.

## 5. Do Not Do

- Do not run live credential feed scripts.
- Do not paste API keys.
- Do not fetch public feeds for the main demo.
- Do not claim live data ingestion.
- Do not show real leaked records.
