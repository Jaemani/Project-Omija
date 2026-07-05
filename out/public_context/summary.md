# Public Context Snapshot

Generated: `2026-07-05T00:21:08.430674+00:00`

This file summarizes non-sensitive public context only. It is not wired into
the main demo automatically.

## Counts

- CISA KEV total: `1631`
- CISA KEV access-relevant: `957`
- MITRE ATT&CK selected techniques: `89`
- URLhaus sampled rows: `1000`
- URLhaus stealer/loader-tagged sample count: `45`
- HIBP public breach metadata count: `1015`
- FIRST EPSS probability > 0.95 total: `513`
- CISA advisory RSS sampled: `30`
- CISA advisory RSS access-relevant: `25`
- CISA ICS advisory RSS sampled: `30`

## NVD Queries

- `vpn`: 73 total, 8 sampled
- `sso`: 25 total, 8 sampled
- `citrix`: 309 total, 8 sampled
- `fortinet`: 672 total, 8 sampled
- `ivanti`: 379 total, 8 sampled

## Where Fits

- KEV/NVD/EPSS -> `Domain.asset_type`, `RiskAssessment.components.public_context`
- CISA advisories -> `ThreatSource.kind`, `ProgramExposure.components.public_advisory_context`
- MITRE ATT&CK -> `ThreatSource.kind`, `RiskAssessment.components.techniques`
- URLhaus aggregate tags -> `ProgramExposure.components.threat_context`
- HIBP breach metadata -> presentation-only explanation of breach data classes
