# 2026-07-05 — Finals Live Foundry Lineage

## What Changed

- Collected approved filtered StealthMole hackathon API rows for `probe:domain:naver.com`.
- Imported 150 provider rows through `scripts/import_candidate_signals.py`.
- Forced raw-independent `redacted:<hash>` masking at import boundary.
- Generated sanitized Foundry-ready CSVs under `out/foundry_live_measurement/`.
- Uploaded all 14 object/link CSVs to known ontology backing dataset RIDs.
- Attached explicit tabular schemas to all 14 backing dataset RIDs with `datasets/{rid}/putSchema`.
- Created separate schema-aware `live_measurement_*` Foundry datasets for direct SQL measurement.
- Added SQL measurement artifact proving 14/14 Foundry counts match expected local CSV counts.
- Updated `out/data_lineage_live.html` to show live provider rows, Foundry schema status, SQL counts, and ontology readback boundary.

## Measurement

- Provider rows: 150
- Modules: CL 50, CDS 50, CB 50
- Foundry-ready object rows:
  - Supplier 1
  - Program 1
  - Domain 17
  - Identity 150
  - CredentialExposure 150
  - InfectedDevice 150
  - ThreatSource 150
- Foundry-ready link rows:
  - owns 17
  - belongs_to 150
  - of 150
  - targets 150
  - sourced_from 150
  - leaked 150
  - compromises 150

## Foundry Status

- Backing dataset uploads: 14/14 OK
- Backing dataset schema PUT: 14/14 OK
- Schema-aware live measurement datasets: 14/14 OK
- Foundry SQL counts: 14/14 OK
- OSDK object readback for live PKs: not indexed yet

## Current Limit

Do not claim full ontology E2E readback yet. The accurate claim is:

> Live approved provider data is loaded and measured in Foundry datasets; ontology object index readback still requires Foundry datasource/index refresh.
