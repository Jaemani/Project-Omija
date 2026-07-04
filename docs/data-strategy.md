# Data Strategy

Project Omija is a defense-intelligence data-fusion system. It is not a
single-feed StealthMole demo. The demo should be described as:

1. real public OSINT feeds for vulnerability and threat context;
2. a Foundry ontology path that connects credential exposure to supplier,
   prime, and program impact;
3. a credential-exposure feed integration boundary that is ready for authorized
   live use, but currently blocked by StealthMole authentication.

## Feed Classes

| Feed class | Current source | Real or synthetic | Used for | Current status |
|---|---|---|---|---|
| Public OSINT | NVD, CISA KEV, MITRE ATT&CK, abuse.ch URLhaus | Real public data | Asset and threat context for scoring and explanation | Implemented in `scripts/osint_collect.py` |
| Credential exposure | StealthMole CDS/CL/CB via `adapter/stealthmole.py` | Real only when authorized live pipeline succeeds | Leaked credential and infostealer early-warning signal | Auth currently returns `401` |
| Foundry demo seed | Seed objects loaded into the current Foundry ontology | Synthetic | Reproducible graph path, scoring, incident, blast radius, and notification draft | Read back through OSDK |

## Public OSINT Layer

`scripts/osint_collect.py` collects and summarizes public, non-secret feeds:

- NVD CVE API: critical VPN CVEs.
- CISA KEV: known exploited vulnerabilities relevant to access surfaces.
- MITRE ATT&CK Enterprise: credential-access and initial-access techniques.
- abuse.ch URLhaus: recent malicious URL tags and stealer/loader indicators.

The output is written to:

- `out/osint/osint_summary.json`
- `out/osint/osint_report.html`

These outputs are safe to commit because they contain public summary data only.

## Credential Exposure Layer

The live credential feed entrypoint remains:

```bash
uv run python scripts/p0c_live_pipeline.py \
  --authorized \
  --registry registry/suppliers.live.yaml \
  --domains REPLACE_WITH_AUTHORIZED_DOMAIN \
  --modules cds
```

Guardrails:

- `--authorized` is required.
- Domains must be present in the private live registry.
- Synthetic domains are refused by the live runner.
- Secrets are masked and raw reusable credentials are not stored.
- `.env` is local only and must not be committed.

Current StealthMole status:

- Expected endpoint contract: `https://hackathon.stealthmole.com/user/quotas`.
- A previous `401` was fixed by switching away from the production `/v2`
  endpoint to the hackathon endpoint.
- The current `401` persists even after endpoint and JWT `iat` alignment.
- `out/p0b/stealthmole_auth_evidence.json` records a secret-free evidence
  package: endpoint, server date, local date, JWT `iat` skew, key lengths, and
  HTTP status only.
- Remaining likely causes are issued key pair, account activation, product
  enablement, or IP allowlist.

## Foundry Ontology Mapping

The ontology remains the decision spine:

```text
CredentialExposure.of -> Identity
CredentialExposure.targets -> Domain
Identity.belongs_to -> Domain
Domain -> Supplier / Prime ownership
Supplier.subcontractsTo -> Supplier
Supplier.supplies -> Prime
Prime.runs -> Program
CompromiseIncident.traverses_* -> path drill-down
RiskAssessment.components <- credential signal + OSINT overlay
NotificationDraft.cites -> incident and evidence
```

The important modeling decision is that `of` and `targets` stay separate:

- `of` answers whose credential was exposed.
- `targets` answers what asset the credential appears to access.

That separation is what lets the demo show a supplier identity reaching a prime
asset such as a VPN or SSO domain.

## Integrated Demo Flow

The primary command is:

```bash
uv run python scripts/intelligence_demo.py
open out/intelligence_demo.html
```

It performs five checks:

1. collects public OSINT feeds;
2. verifies Foundry OSDK ontology links;
3. runs the blast-radius proof for `exp:micro-h:active`;
4. records StealthMole auth status without exposing secrets;
5. writes `out/intelligence_demo.json` and `out/intelligence_demo.html`.

## Claim Boundary

Say this precisely during review or judging:

- The public OSINT layer uses real live public data.
- The Foundry ontology path is live OSDK readback from the current ontology.
- The Foundry credential-exposure seed is synthetic.
- Real leaked credential data should only be claimed after
  `scripts/p0c_live_pipeline.py` succeeds with an authorized registry and
  working StealthMole authentication.

Do not claim the synthetic Foundry credential record is real leaked data.
