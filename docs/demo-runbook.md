# Demo Runbook

Use this sequence for the hackathon demo. The goal is to prove data fusion:
public OSINT context, Foundry ontology traversal, credential-feed readiness, and
approval-gated response.

## 0. Primary Preflight

Run the integrated demo first:

```bash
uv run python scripts/intelligence_demo.py
open out/intelligence_demo.html
```

Pass condition:

- terminal ends with `RESULT: READY`;
- `out/intelligence_demo.json` exists;
- `out/intelligence_demo.html` opens.

This is the preferred judging screen because it connects all three surfaces:
public OSINT, Foundry OSDK readback, and credential-feed auth status.

## 0-B. Foundry-Only Preflight

Use this when public feed collection is slow or network availability is poor:

```bash
uv run python scripts/final_demo_check.py --full
open out/foundry_demo.html
```

Fast rerun when tests were already executed:

```bash
uv run python scripts/final_demo_check.py
open out/foundry_demo.html
```

Pass condition: terminal ends with `RESULT: READY`.

## 1. Opening Claim

Use this message:

> We are not just collecting OSINT. We connect public intelligence, credential
> exposure signals, and the defense supply-chain ontology to decide which
> supplier and program need action first.

Point to these values on the report:

- `Operational Value`: why the system exists;
- `Ontology Path — Credential To Program`: how the active path is proven;
- `Public Source Corroboration`: why the target asset class matters now;
- `Recommended Response — Analyst Review Required`: what the analyst should do;
- `Unsent Advisory — Draft`: response output is generated but not sent;
- public OSINT counts: NVD, CISA KEV, MITRE ATT&CK, URLhaus;
- risk band and path confidence;
- impacted programs;
- active ontology path;
- provenance and generated artifacts;
- notification draft marked as unsent / approval required.

## 2. Object Explorer Walk

Start at `CredentialExposure exp:micro-h:active` and traverse:

1. `CredentialExposure exp:micro-h:active`
2. `of` -> `Identity id:ops@micro-h.example`
3. `belongs_to` -> `Domain micro-h.example`
4. owner supplier -> `Supplier sup-h`
5. `subcontractsTo` -> `Supplier sup-f`
6. `supplies` -> `Prime prime-x`
7. `runs` -> `Program prog-sentinel`
8. back to `CompromiseIncident incident:micro-h:active`
9. inspect `traverses_supplier` and `traverses_program`
10. inspect `NotificationDraft draft:sup-h:2026-07-03`

Key explanation:

- `of` is the exposed account owner.
- `targets` is the asset the credential appears to access.
- The cross-organization case matters: a supplier account can target a prime
  VPN, SSO, mail, or admin asset.

## 3. CLI Proof

Show the blast radius for the seed exposure:

```bash
uv run python scripts/foundry_blast_radius.py exp:micro-h:active
```

Pass condition:

- supplier is `sup-h`;
- programs include `prog-sentinel` and `prog-harbor`;
- incident is `incident:micro-h:active`;
- terminal ends with `RESULT: OK`;
- `out/blast_radius_exp_micro-h_active.json` is written.

## 4. Static Report Closer

Open the integrated report:

```bash
open out/intelligence_demo.html
```

Narrate:

- origin endpoint: compromised supplier credential signal;
- target endpoint: protected program access surface;
- relationship labels: `subcontractsTo`, `supplies`, `runs`;
- OSINT overlay: why this target asset class matters now;
- notification draft: generated but not sent.

## 5. Failure Modes

If Foundry is unavailable:

```bash
uv run python scripts/p4_dashboard.py
open out/dashboard.html
```

Then say: the same store boundary runs locally through SQLite, and Foundry OSDK
readback is already captured in committed demo artifacts.

If StealthMole is unavailable:

```bash
cat out/p0b/stealthmole_auth_evidence.json
```

Then say: credential-feed auth is blocked, but endpoint and JWT timing evidence
are captured without secrets. The public OSINT layer and Foundry ontology path
still demonstrate the fusion workflow.

If live credential data is unavailable, do not run arbitrary queries and do not
claim synthetic seed data is real. Use the committed synthetic seed only.

## Feature Freeze

Before judging, do not:

- add new ontology types;
- rename link types;
- wire broad write support;
- change scoring semantics.

Only runbook, fallback, and documentation fixes are allowed.
