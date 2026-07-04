# Public Context Snapshot

Generated: `2026-07-04T20:40:42.317702+00:00`

This file summarizes non-sensitive public context only. It is not wired into
the main demo automatically.

## Counts

- CISA KEV total: `1631`
- CISA KEV access-relevant: `863`
- MITRE ATT&CK selected techniques: `234`
- URLhaus sampled rows: `1000`
- URLhaus stealer/loader-tagged sample count: `42`
- HIBP public breach metadata count: `1015`

## NVD Queries

- `vpn`: 73 total, 8 sampled
- `sso`: 25 total, 8 sampled
- `citrix`: 309 total, 8 sampled
- `fortinet`: 672 total, 8 sampled
- `ivanti`: 379 total, 8 sampled

## Where This Fits

- KEV/NVD -> `Domain.asset_type`, `RiskAssessment.components.public_context`
- MITRE ATT&CK -> `ThreatSource.kind`, `RiskAssessment.components.techniques`
- URLhaus aggregate tags -> `ProgramExposure.components.threat_context`
- HIBP breach metadata -> presentation-only explanation of breach classes
