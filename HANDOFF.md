# Project Omija Handoff

Last updated: 2026-07-05 KST

This file is the handoff source of truth for a new engineer, another model, or a
new project workspace. Do not rely on prior chat history. Start here, then open
the linked docs.

## 1. Project Intent

Project Omija is a D4D Hackathon Track 2/3 project:

- Track 2: OSINT and defense intelligence.
- Track 3 adjacency: supply-chain security and incident response workflow.

The operational question is:

> Which supplier appears to create an active path into a protected defense
> program, why does it matter now, and what action should be prepared first?

The product is not a credential dump viewer and not a single API demo. It is a
data-fusion early-warning system that connects:

- credential exposure and infostealer signals;
- public OSINT context;
- supplier, prime, and program relationships;
- risk scoring and blast-radius reasoning;
- human-reviewed notification drafts.

## 2. Current Repository State

Important commits:

- `86f9a2b Redesign intelligence demo dashboard`
  - current `main` / `origin/main`;
  - converts `out/intelligence_demo.html` into a dashboard-first surface.
- `ec65433 Add integrated OSINT intelligence demo`
  - adds public OSINT collection, integrated demo, auth evidence, and handoff
    docs.
- `2f2f19a stealthmole-api-match`
  - pushed as branch `origin/stealthmole-api-match`;
  - records StealthMole hackathon API contract alignment work.

Branches:

- `main`: current demo and documentation.
- `stealthmole-api-match`: branch requested for StealthMole API match history.

Current verification from latest local run:

```bash
uv run pytest -q
# 121 passed

uv run python scripts/intelligence_demo.py
# RESULT: READY
```

## 3. What Exists Now

### Integrated Dashboard

Primary command:

```bash
uv run python scripts/intelligence_demo.py
open out/intelligence_demo.html
```

What it does:

1. collects real public OSINT summaries;
2. verifies Foundry OSDK ontology links;
3. runs the `exp:micro-h:active` blast-radius proof;
4. records StealthMole auth status without secrets;
5. writes `out/intelligence_demo.json` and dashboard-first
   `out/intelligence_demo.html`.

The dashboard intentionally shows value first:

- `Current Threat Picture`
- `Operational Value`
- `Ontology Path — Credential To Program`
- `Public Source Corroboration`
- `Recommended Response — Analyst Review Required`
- `Unsent Advisory — Draft`
- `Collection Status`

### Foundry Ontology Readback

Foundry OSDK smoke test is already wired:

```bash
uv run python scripts/final_demo_check.py --full
open out/foundry_demo.html
```

Fast path:

```bash
uv run python scripts/final_demo_check.py
uv run python scripts/foundry_blast_radius.py exp:micro-h:active
open out/foundry_demo.html
```

Core path currently proven by OSDK:

```text
CredentialExposure exp:micro-h:active
-> of Identity id:ops@micro-h.example
-> belongs_to Domain micro-h.example
-> Supplier sup-h
-> subcontractsTo Supplier sup-f
-> supplies Prime prime-x
-> runs Program prog-sentinel / prog-harbor
```

Key modeling rule:

- `CredentialExposure.of` means whose credential was exposed.
- `CredentialExposure.targets` means what asset the credential appears to
  access.

That separation is the reason the ontology is valuable. It shows a supplier
identity reaching a prime/defense-program access surface.

### Public OSINT

Implemented in `scripts/osint_collect.py`.

Sources:

- NVD CVE API;
- CISA KEV;
- MITRE ATT&CK Enterprise;
- abuse.ch URLhaus.

Artifacts:

- `out/osint/osint_summary.json`
- `out/osint/osint_report.html`

This layer is real public data and safe to describe as real OSINT.

### Credential Exposure Feed

Implemented boundary:

- `adapter/stealthmole.py`
- `scripts/p0b_recon.py`
- `scripts/p0c_live_pipeline.py`
- `scripts/stealthmole_auth_evidence.py`

Current latest integrated demo status:

- endpoint: `https://hackathon.stealthmole.com/user/quotas`
- latest `out/p0b/stealthmole_auth_evidence.json` shows `401`;
- JWT `iat` is aligned in the latest evidence package;
- likely unresolved causes are external: issued key pair, account activation,
  product enablement, or IP allowlist.

Important: historical branch/output may show earlier API alignment or success
evidence. Re-run the current command before making a claim:

```bash
uv run python scripts/stealthmole_auth_evidence.py
```

Do not claim live StealthMole credential ingestion unless the authorized live
pipeline succeeds in the current environment.

## 4. Data Boundary And Claims

Allowed claims:

- Public OSINT layer uses real public data.
- Foundry ontology path is live OSDK readback.
- The dashboard connects OSINT, graph path, blast radius, and response drafting.
- StealthMole integration boundary exists and records auth evidence without
  secrets.

Not allowed unless live pipeline succeeds:

- Foundry seed credential exposure is real leaked credential data.
- StealthMole live credential records were ingested.
- A notification was sent.

Current seed data:

- Foundry credential exposure seed is synthetic.
- Notification is draft only.
- No raw reusable passwords, cookies, JWTs, or bearer tokens should be stored.

## 5. Environment And Secrets

Use `.env.example` as a template only. Real values go in `.env`, which is
gitignored.

Important placeholders:

```bash
STEALTHMOLE_ACCESS_KEY=
STEALTHMOLE_SECRET_KEY=
STEALTHMOLE_IAT_OFFSET_SECONDS=

FOUNDRY_HOSTNAME=
FOUNDRY_TOKEN=
FOUNDRY_OSDK_PACKAGE=
FOUNDRY_OSDK_MODULE=
```

`STEALTHMOLE_ACCESS_KEY=` and `STEALTHMOLE_SECRET_KEY=` with empty values are
correct for `.env.example`. They are not sufficient for real API calls.

Never commit:

- `.env`
- access keys;
- secret keys;
- JWTs;
- bearer headers;
- raw passwords;
- reusable cookies or tokens.

## 6. Foundry Ontology State

The current hackathon ontology uses v0.2-compatible separate object types:

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

Important Foundry notes:

- Seed-filled properties must be datasource-backed, not edit-only.
- Lifecycle-only fields may be edit-only.
- Foundry conceptual union links must be split into concrete Link Types.
- `PathEvidence` was intentionally not added.
- `path_snapshot`, `path_hash`, and `traverses_*` links are enough for the demo.
- Current model keeps `Prime` separate. Long-term v0.3 may merge Prime into
  `Supplier(is_prime=true, tier=0)`, but do not change this before judging.

Detailed build guide:

- `ontology.md`
- `docs/runbooks/foundry-osdk-handoff.md`
- `docs/changelog/foundry-ontology-2026-07-04.md`
- `docs/changelog/foundry-osdk-2026-07-04.md`

## 7. Key Files

Entrypoints:

- `README.md`
- `HANDOFF.md`
- `docs/reviewer-guide.md`
- `docs/demo-runbook.md`
- `docs/data-strategy.md`

Architecture and decisions:

- `docs/spec/architecture.md`
- `docs/spec/ontology.md`
- `ontology.md`
- `docs/decisions/0006-multitier-propagation.md`
- `docs/decisions/0007-osint-data-fusion.md`
- `docs/decisions/0008-dashboard-first-demo-surface.md`

Core scripts:

- `scripts/intelligence_demo.py`
- `scripts/osint_collect.py`
- `scripts/final_demo_check.py`
- `scripts/foundry_osdk_smoke.py`
- `scripts/foundry_blast_radius.py`
- `scripts/stealthmole_auth_evidence.py`
- `scripts/p0c_live_pipeline.py`

Generated demo artifacts:

- `out/intelligence_demo.html`
- `out/intelligence_demo.json`
- `out/foundry_demo.html`
- `out/osint/osint_report.html`
- `out/osint/osint_summary.json`
- `out/p0b/stealthmole_auth_evidence.json`
- `out/blast_radius_exp_micro-h_active.json`

## 8. Resume Procedure

Fresh clone:

```bash
git clone git@github.com:Jaemani/Project-Omija.git
cd Project-Omija
uv sync
cp .env.example .env
```

Fill `.env` with local-only Foundry and StealthMole values.

Validate:

```bash
uv run pytest -q
uv run python scripts/intelligence_demo.py
open out/intelligence_demo.html
```

If Foundry credentials or OSDK package are missing, use local fallback:

```bash
uv run python scripts/p4_dashboard.py
open out/dashboard.html
```

If only Foundry readback should be checked:

```bash
uv run python scripts/final_demo_check.py --full
uv run python scripts/foundry_blast_radius.py exp:micro-h:active
```

## 9. Remaining Work

### P0: Keep Demo Stable

- Do not rename ontology link API names.
- Do not add new object types before judging.
- Do not change scoring semantics without updating docs and outputs.
- Keep `out/intelligence_demo.html` generated and committed when the demo
  surface changes.

### P1: StealthMole Live Data

- Resolve current `/user/quotas` 401 in the current environment.
- Confirm key pair, account activation, API product enablement, and IP allowlist.
- Run only with authorized domains and a private registry:

```bash
uv run python scripts/p0c_live_pipeline.py \
  --authorized \
  --registry registry/suppliers.live.yaml \
  --domains AUTHORIZED_DOMAIN \
  --modules cds
```

- Capture only masked schema/evidence.
- Do not store raw credentials.
- Once live ingestion succeeds, update `docs/data-strategy.md`,
  `docs/changelog/`, and dashboard claim language.

### P2: Foundry Actions

Current demo is read-first. Action Type write integration is not required for
the current dashboard.

Lowest-risk actions to add later:

- `AcknowledgeIncident`
- `AssignIncident`
- `CloseIncident`
- `ReviewNotificationDraft`
- `ApproveNotificationDraft`
- `ExportNotificationDraft`

Defer these until actual Action API names, parameters, and submission criteria
are confirmed.

### P3: Workshop / App Surface

The current dashboard is static HTML generated from JSON. A Foundry Workshop app
or full frontend can be added later, but the current static artifact is the
stable demo surface.

If building a Workshop or web app, preserve these panels:

- current threat picture;
- ontology path;
- public source corroboration;
- recommended response;
- unsent draft;
- collection status.

### P4: First-Class OSINT Ontology

Do not add these before judging unless there is enough time to test them:

- `Vulnerability`
- `Technique`
- `Indicator`
- `Advisory`
- `Observation`

ADR-0007 intentionally kept OSINT as a risk-component overlay for the
hackathon.

### P5: Ontology v0.3 Cleanup

Consider, but do not rush:

- merging `Prime` into `Supplier(is_prime=true, tier=0)`;
- adding stronger controlled vocabularies for status fields;
- turning more derived provenance into first-class audit objects only if ACL,
  search, or audit requirements justify it.

## 10. Model Delegation Context

The working preference used in this project was:

- Fable for strategy/planning and ontology judgment when available.
- Codex for code changes, shell execution, tests, commits, and repo hygiene.
- Opus for visual/dashboard design direction.

If a Fable request falls back to Opus, treat that answer as lower-priority
design/planning input and have Codex or another reviewer re-check the decision.
The dashboard-first surface was designed with Opus guidance and implemented in
repo code.

## 11. Troubleshooting

### Tests pass but dashboard looks stale

Re-run:

```bash
uv run python scripts/intelligence_demo.py
open out/intelligence_demo.html
```

### Foundry links fail

Run:

```bash
uv run python scripts/foundry_osdk_smoke.py --diagnose
```

Then compare link API names against `.env.example` and
`docs/runbooks/foundry-osdk-handoff.md`.

### StealthMole returns 401

Run:

```bash
uv run python scripts/stealthmole_auth_evidence.py
```

Check:

- endpoint is `https://hackathon.stealthmole.com/user/quotas`;
- JWT `iat` skew is near zero;
- access/secret key are present in `.env`;
- account/API product/IP allowlist are active.

### Secret scan before committing

```bash
rg -n "Authorization: Bearer|eyJ|STEALTHMOLE_ACCESS_KEY=[^\\n]+|STEALTHMOLE_SECRET_KEY=[^\\n]+" \
  README.md HANDOFF.md docs scripts tests out .env.example
```

This may find placeholder documentation. It must not find real key values,
JWTs, or bearer tokens.

## 12. Final Reminder

The strongest demo sentence is:

> Omija does not rank leaks by volume. It ranks active paths where a supplier
> identity can reach a sensitive target asset and an impacted defense program,
> then attaches public OSINT context and a human-reviewed response draft.

Keep the claim boundary honest:

- real public OSINT;
- live Foundry OSDK readback;
- synthetic credential seed unless live StealthMole ingestion succeeds.
