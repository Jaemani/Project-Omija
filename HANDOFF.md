# Project Omija Handoff

> 2026-07-08 status note: `README.md` is now the primary current-state index.
> This handoff preserves earlier project context. The latest finals strategy is
> no longer "empty live slot only": approved filtered StealthMole hackathon rows
> are used after redaction for lineage and Foundry measurement, while raw
> provider envelopes and reusable secret material remain blocked.

Last updated: 2026-07-05 KST

This is the source of truth for resuming the project without prior conversation context.

## Current Direction

Project Omija is an ontology-centered defense supply-chain credential-exposure early-warning demo.

The core claim:

> Private exposure feeds provide signals. Omija turns those signals into ontology-backed decisions: identity owner, target asset, supplier path, prime/program impact, risk assessment, compromise incident, program exposure, and human-reviewed notification draft.

Concrete mission:

> 방산 1·2차 협력사 도메인을 대상으로 유출 자격증명·스틸러 감염기기를 자동 상관하여 업체별 위험 순위를 산출하고, 활성 침해 정황에는 가중치를 높여 즉시 조치를 권고하는 조기경보 체계를 만든다.

Technical boundary: Omija can produce active-compromise candidates and recommended response drafts. It must not claim external feed data alone proves a live compromise; confirmation needs VPN/SSO/IAM/EDR logs and human review.

The demo must keep a clear boundary:

- real credential/leak/session data is not displayed or stored;
- synthetic entities prove the reasoning engine;
- public, non-sensitive context can be fetched and shown as aggregate/background evidence;
- private input providers are shown as locked contracts and role maps, not as live data screens.

## Hard Rules

- Do not store or show passwords, cookies, JWTs, bearer tokens, raw secrets, session values, or real leaked accounts.
- Do not implement or expose private credential-feed auth/client code in tracked files.
- Do not claim live credential ingestion.
- Do not put real supplier domains or real people into hosted demo pages unless explicitly cleared.
- Keep notification as `NotificationDraft`; do not add automatic email/SMS/webhook sending.
- Public data is allowed only when it is non-sensitive context: CVE metadata, advisory metadata, ATT&CK technique metadata, aggregate malware tags, breach metadata without account queries.

## Current Demo Pages

Primary hosted/static pages:

```text
out/stealthmole_role_map.html
out/data_coverage_map.html
out/public_context_matrix.html
out/omija_console_home.html
out/omija_demo.html
out/program_threat_view.html
```

Raw.githack URLs after push:

```text
https://raw.githack.com/Jaemani/Project-Omija/main/out/stealthmole_role_map.html
https://raw.githack.com/Jaemani/Project-Omija/main/out/data_coverage_map.html
https://raw.githack.com/Jaemani/Project-Omija/main/out/public_context_matrix.html
https://raw.githack.com/Jaemani/Project-Omija/main/out/omija_console_home.html
https://raw.githack.com/Jaemani/Project-Omija/main/out/omija_demo.html
https://raw.githack.com/Jaemani/Project-Omija/main/out/program_threat_view.html
```

Legacy/no-live-data console variants still exist:

```text
out/intelligence_demo.html
out/omija_console_core.html
out/omija_console_graph.html
out/omija_console_response.html
```

## Presentation Order

1. Problem: flat leak lists cannot answer blast radius.
2. Foundry Ontology Manager screenshots.
3. `out/stealthmole_role_map.html`: CL/CDS/DT/TT input roles.
4. `out/data_coverage_map.html`: what is synthetic, public, engine-computed, live readback, locked.
5. `out/public_context_matrix.html`: safe public data sources and ontology fit.
6. `out/omija_console_home.html`: steady-state operating console.
7. `out/omija_demo.html`: incident/case page.
8. `out/program_threat_view.html`: optional reverse query for program owners.

## StealthMole Role

StealthMole should be described as an input provider, not as Omija's reasoning layer.

```text
Credential Lookout (CL)      -> CredentialExposure
Compromised Data Set (CDS)   -> InfectedDevice
Darkweb Tracker (DT)         -> ThreatSource
Telegram Tracker (TT)        -> ThreatSource
```

Omija's value starts after this normalization:

```text
CredentialExposure.of -> Identity
CredentialExposure.targets -> Domain
Identity.belongs_to -> Domain / Supplier
Supplier.subcontractsTo -> Supplier
Supplier.supplies -> Prime
Prime.runs -> Program
CompromiseIncident.traverses_* -> path nodes
NotificationDraft.cites -> reviewed evidence slots
```

Key phrase:

> StealthMole provides signals. Omija decides what those signals mean for defense supply-chain risk.

## Public Context Snapshot

Command:

```bash
uv run python scripts/public_context_snapshot.py
```

Outputs:

```text
out/public_context/summary.json
out/public_context/summary.md
```

Current included public sources:

- CISA KEV
- NVD CVE API
- FIRST EPSS
- CISA advisory RSS
- CISA ICS advisory RSS
- MITRE ATT&CK STIX
- URLhaus aggregate metadata
- HIBP breach metadata

Current snapshot highlights:

```text
CISA KEV total: 1631
CISA KEV access-relevant: 957
MITRE ATT&CK selected techniques: 89
URLhaus sampled rows: 1000
URLhaus stealer/loader-tagged sample count: 44
HIBP public breach metadata count: 1015
FIRST EPSS probability > 0.95 total: 513
CISA advisory RSS sampled: 30
CISA advisory RSS access-relevant: 25
CISA ICS advisory RSS sampled: 30
NVD vpn/sso/citrix/fortinet/ivanti query totals: 73 / 25 / 309 / 672 / 379
```

Generate the visual matrix:

```bash
uv run python scripts/public_context_matrix.py
```

## Ontology Core

Core object types:

- `Supplier`
- `Prime`
- `Program`
- `Domain`
- `Identity`
- `CredentialExposure`
- `InfectedDevice`
- `ThreatSource`
- `MergeProposal`
- `RiskAssessment`
- `CompromiseIncident`
- `ProgramExposure`
- `NotificationDraft`

Important links:

```text
CredentialExposure.of -> Identity
CredentialExposure.targets -> Domain
InfectedDevice.leaked -> CredentialExposure
Identity.belongs_to -> Domain / Supplier
Supplier.owns -> Domain
Supplier.subcontractsTo -> Supplier
Supplier.supplies -> Prime
Prime.runs -> Program
CompromiseIncident.traverses_* -> path nodes
NotificationDraft.cites -> reviewed evidence slots
```

Key idea:

- `of`: account owner.
- `targets`: access surface involved.

This lets Omija reason about cross-organization access without collapsing everything into a flat table.

## Key Files

```text
README.md
HANDOFF.md
ontology.md
presentation_guide.md
docs/open-data-catalog.md
docs/data-insertion-guide.md
docs/practical-early-warning-plan.md
docs/data-collection-playbook.md
docs/claims-and-limitations.md
docs/presentation-flow.md
docs/stealthmole-role-map.md
docs/stealthmole-api-integration.md
scripts/collection_plan.py
scripts/early_warning_readiness.py
scripts/import_candidate_signals.py
scripts/public_context_snapshot.py
scripts/public_context_matrix.py
scripts/stealthmole_role_map.py
scripts/data_coverage_map.py
scripts/omija_console_home.py
scripts/omija_demo.py
scripts/program_threat_view.py
```

## Verification

Run:

```bash
uv run pytest -q
uv run python scripts/collection_plan.py
uv run python scripts/early_warning_readiness.py
uv run python scripts/public_context_snapshot.py
uv run python scripts/public_context_matrix.py
uv run python scripts/stealthmole_role_map.py
uv run python scripts/data_coverage_map.py
```

Expected:

- tests pass;
- public context scripts only store non-sensitive aggregate/metadata;
- generated pages contain no private credential/feed implementation details.

## Remaining Work

1. Capture Foundry Ontology Manager and Object Explorer screens for the slide deck.
2. Keep public context visually secondary to ontology reasoning.
3. If time allows, polish `out/omija_console_home.html` so the steady-state view feels more operational.
4. Do not reintroduce private live feed ingestion without explicit owner directive and a separate sensitive-data handling plan.
