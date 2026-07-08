# Finals Data Lineage Upgrade

Status: implemented finals upgrade after track judging feedback.

## Why this changes

Judging feedback showed two gaps:

1. The demo did not make data lineage explicit enough.
2. The demo was too defensive about StealthMole data, even though the hackathon API provides already-filtered demonstration records that can be used in the demo.

The finals version should use the approved hackathon API records in the lineage demo, while still excluding API keys, JWTs, raw provider envelopes, and reusable secret material from tracked/static artifacts.

## Target narrative

Omija does not just say "approved feeds could be connected later." It shows an approved StealthMole API run entering a redaction boundary, becoming ontology objects, feeding the reasoning engine, and producing auditable decisions.

Safe one-line claim:

> Approved StealthMole hackathon records are ingested live, normalized into Omija ontology objects, and traced through every decision object by lineage.

Implemented claim as of 2026-07-05:

> Approved StealthMole hackathon records are ingested, redacted, converted into Foundry-ready object/link rows, and measured in Foundry schema-aware datasets. Ontology object readback remains index-refresh pending.

Do not claim:

- Raw leaked passwords, cookies, or tokens are stored in the repo or static pages.
- `targets` proves successful login.
- Band A proves confirmed breach.
- Foundry object readback is fully solved before datasource/index refresh is verified.

## Data boundary for finals

Keep three layers, but make the private layer visible as lineage metadata:

| Layer | What can be shown | What cannot be shown |
|---|---|---|
| Public OSINT | KEV/NVD/EPSS/ATT&CK/HIBP counts, CVE IDs, technique names | none beyond source licenses |
| StealthMole approved hackathon API | module, run id, source_ref hash, approved query seed, normalized target/domain fields, account class, timestamps, confidence, has_session_cookie boolean, normalized object IDs, row-level lineage | API keys, JWTs, full raw provider payloads, reusable secret values if any |
| Synthetic scenario | fictional suppliers/devices used to make path examples deterministic | label clearly as synthetic |

## Required finals artifact

Add a new page:

```text
out/data_lineage_live.html
```

Recommended navigation label:

```text
데이터 계보
```

The page should answer:

1. Which StealthMole module was queried?
2. Which approved seed/query was used?
3. How many rows returned?
4. How many were normalized?
5. Which ontology objects were created or updated?
6. Which links were created?
7. Which engine decisions consumed those objects?
8. Which fields were removed or masked?

## Page layout

### 1. Run Summary

Show one run card:

```text
run_id
generated_at
modules: CL / CDS / CB / DT / TT
seed_id
query_type
query_value redacted or domain-level only
returned
normalized
rejected
raw_secret_removed: true
```

### 2. Lineage Swimlane

Use a left-to-right flow:

```text
StealthMole API
  -> Raw envelope (private, ignored)
  -> Redaction boundary
  -> Normalized candidates
  -> Ontology objects
  -> Ontology links
  -> Engine decisions
  -> Human review actions
```

Each node should show counts and provenance labels:

- `LIVE_PROVIDER`
- `PRIVATE_RAW`
- `NORMALIZED`
- `ONTOLOGY`
- `ENGINE`
- `LIVE_FOUNDRY` if uploaded/read back

### 3. Record-Level Lineage Examples

Show 2-3 redacted examples. Each row should be safe:

```text
source_ref_hash
module
normalized_object
object_id
links_created
consumed_by
decision_output
fields_removed
```

Example:

```text
CDS #a19f...
-> InfectedDevice dev:a19f
-> CredentialExposure exp:a19f
-> of Identity id:...
-> targets Domain vpn.prime-x.example
-> FlagActiveCompromise skipped: no live session cookie
```

or, if active:

```text
CDS #b72c...
-> InfectedDevice dev:b72c
-> Identity -> Supplier -> Prime -> Program
-> CompromiseIncident incident:...
-> RiskAssessment risk:...
-> NotificationDraft draft:...
```

### 4. Redaction Proof

Show a compact checklist:

```text
password: removed
cookie: removed
token: removed
provider raw payload: not exported
source_ref: hashed
masked_value: boundary-generated
```

### 5. Foundry Lineage Evidence

If Foundry MCP / UI is used, capture:

- Dataset lineage from sanitized CSV/dataset to object type.
- Object type backing dataset view.
- Link type backing dataset view.
- Action run/readback audit stream.

If backing dataset schema is still blocked, say:

> Foundry ontology and action workflow are configured; provider-to-decision lineage is verified in the local reasoning engine and prepared as sanitized Foundry upload artifacts.

## Implementation steps for Codex

1. Add a lineage export script:

```text
scripts/data_lineage_live.py
```

Inputs:

```text
data/private_candidates/collection_meta.json
out/private_candidate_import.json
out/early_warning_readiness.json or local engine output
out/foundry_action_chain.json
```

Outputs:

```text
out/data_lineage_live.html
out/data_lineage_live.json
```

2. Extend `scripts/import_candidate_signals.py` output with `lineage` entries:

```json
{
  "source_ref_hash": "...",
  "module": "cds",
  "raw_envelope": "private",
  "normalized_objects": ["CredentialExposure", "InfectedDevice", "ThreatSource"],
  "links": ["sourced_from", "leaked", "of", "targets"],
  "removed_fields": ["password", "cookie", "token"],
  "policy": "raw_secret_removed"
}
```

3. Run an approved StealthMole query locally only:

```bash
uv run python scripts/private/stealthmole_private_connector.py \
  --plan out/collection_plan.json \
  --seed-id <approved_seed_id> \
  --modules cl,cds,cb \
  --limit-records 10

uv run python scripts/import_candidate_signals.py \
  --input data/private_candidates/candidates.jsonl
```

4. Generate the lineage page:

```bash
uv run python scripts/data_lineage_live.py
```

5. Optional Foundry upload:

Only upload sanitized CSV/JSON artifacts, never raw provider payloads.

## Finals demo flow update

Insert `data_lineage_live.html` after `data_evidence_brief.html`:

```text
steady console
-> data evidence
-> live data lineage
-> incident report
-> Foundry captures / actions
```

Suggested 15-second script:

> In the first demo we kept the sensitive rail too locked. For finals, this page shows the approved StealthMole hackathon API run as lineage. The demo uses the filtered provider rows, while API secrets and raw provider envelopes stay out of the public artifact. What you see is the full transformation path: provider module, normalization boundary, ontology objects, links created, engine decisions, and human review outputs.
