# Data Collection Playbook

Purpose: define how Omija should collect, normalize, and use data to satisfy the mission without overclaiming or mishandling sensitive records.

Mission:

> 방산 1·2차 협력사 도메인을 대상으로 유출 자격증명·스틸러 감염기기를 자동 상관하여 업체별 위험 순위를 산출하고, 활성 침해 정황에는 가중치를 높여 즉시 조치를 권고하는 조기경보 체계를 개발한다.

## 1. Collection Principle

Omija should collect enough data to answer a decision question:

```text
Which supplier needs attention first, why, and what should a human reviewer do next?
```

It should not become a raw darkweb data lake. The system stores normalized signals, provenance, aggregate public context, and decision objects. It does not store reusable secrets.

## 2. Data Classes

| Class | Examples | Store? | Ontology target | Notes |
|---|---|---:|---|---|
| Supplier registry | supplier name, tier, prime, program, domains, reviewer | Yes | `Supplier`, `Prime`, `Program`, `Domain` | Highest priority. Without this, exposure feeds cannot become supply-chain intelligence. |
| Asset surface | vpn, sso, mail, groupware, dev, admin hosts | Yes | `Domain.asset_type`, `Domain.access_surface` | Needed for active compromise prioritization. |
| Credential exposure candidate | identity hint, target host, secret type, first/last seen, source ref | Yes, normalized only | `CredentialExposure` | No raw password/cookie/token. |
| Infostealer device candidate | device fingerprint, malware, infected time, session-cookie flag, linked host | Yes, normalized only | `InfectedDevice` | `has_session_cookie` is allowed; raw cookie is not. |
| Darkweb/Telegram mention | keyword, matched supplier/program, collected time, source reliability | Yes, metadata only | `ThreatSource` | Context/provenance, not automatic active evidence. |
| Public vulnerability context | KEV, NVD, EPSS, CISA advisory, ATT&CK | Yes | `RiskAssessment.components`, `ProgramExposure.components` | Not credential evidence. |
| Confirmation logs | VPN/SSO/IAM/EDR/mail review outcome | Yes, with access control | Incident lifecycle / review notes | Needed to confirm or close active candidates. |

## 3. Collection Tracks

### Track A. Supplier Registry

This is the first data track. If registry quality is weak, the rest of the system will look impressive but produce weak decisions.

Required fields:

```text
supplier_id
name_ko
name_en
tier
criticality
status
prime_id or parent_supplier_id
program_refs
domains
asset_hosts
reviewer
notification_contact
source_of_truth
verified_at
```

Collection method:

1. Start from approved internal supplier lists if available.
2. Add public company homepages, procurement/public program references, and official partner pages only as secondary enrichment.
3. Record `source_of_truth` and `verified_at`.
4. Do not treat a domain as owned until there is a clear source.

Output:

```text
Supplier
Domain
Supplier.owns Domain
Supplier.subcontractsTo Supplier
Supplier.supplies Prime
Prime.runs Program
```

### Track B. Asset Surface Discovery

Goal: know which domains are normal websites and which are access surfaces.

Patterns to classify:

```text
vpn.*
sso.*
mail.*
owa.*
groupware.*
citrix.*
fortinet.*
ivanti.*
dev.*
admin.*
portal.*
```

Output:

```text
Domain.asset_type
Domain.access_surface
Domain.verified_at
```

Use this in scoring:

- `vpn`, `sso`, `mail`, `admin`, `dev` are higher risk targets.
- `web` is usually lower unless paired with privileged account or active device evidence.

### Track C. Public Context

Public context explains why an access surface matters. It does not prove a supplier is compromised.

Current safe sources:

| Source | Script use | Where it lands |
|---|---|---|
| CISA KEV | known exploited vulnerabilities | `RiskAssessment.components.public_context.kev` |
| NVD CVE API | asset keyword vulnerability context | `RiskAssessment.components.cve_context` |
| FIRST EPSS | exploit probability for CVEs | `RiskAssessment.components.epss_context` |
| CISA advisory RSS | recent public advisory context | `ProgramExposure.components.public_advisory_context` |
| CISA ICS advisory RSS | manufacturing/industrial context | `ProgramExposure.components.ics_context` |
| MITRE ATT&CK | initial/credential access technique vocabulary | `RiskAssessment.components.techniques` |
| URLhaus | aggregate malware tag context | `ProgramExposure.components.threat_context` |
| HIBP breaches API | breach metadata/data class scale | presentation context only |

Run:

```bash
uv run python scripts/public_context_snapshot.py
uv run python scripts/public_context_matrix.py
```

Do not store raw malicious URLs in hosted demo pages. Use aggregate tags/counts.

### Track D. Approved Private Exposure Feeds

This track is only enabled after explicit approval and handling policy. It is represented in the current demo as a locked slot.

StealthMole capability mapping:

| Capability | Query seed | Initial object | Notes |
|---|---|---|---|
| CL | supplier domain, email domain | `CredentialExposure` | Passive exposure candidate. |
| CDS | domain, target host, identity hint | `InfectedDevice` + linked `CredentialExposure` | Main active-candidate input. |
| DT | domain, company alias, program keyword | `ThreatSource` | Context/provenance. |
| TT | domain, alias, campaign keyword | `ThreatSource` | Context/provenance. |
| Country/region search | region + defense/manufacturing/security terms | `ThreatSource` aggregate / review queue | Coverage gap and trend discovery. |
| Keyword search | company alias, product, program, domain, access host | `ThreatSource` / review queue | Alias and target asset discovery. |

Private feed normalization must discard raw secrets immediately.

Allowed fields:

```text
secret_type
secret_present
secret_fingerprint
masked_value
first_seen
last_seen
source_ref
confidence
has_session_cookie
infected_at
malware
account_type
target_host
```

Forbidden fields:

```text
raw_password
raw_cookie
raw_token
session_value
full credential dump
```

### Track E. Confirmation Logs

Active candidates should trigger confirmation, not automatic conclusions.

Useful confirmation sources:

- SSO sign-in logs.
- VPN login logs.
- IAM role and MFA state.
- EDR infection/host owner data.
- Mail/groupware access logs.
- Supplier security contact response.

Confirmation outcome should update:

```text
CompromiseIncident.status
RiskAssessment.status
NotificationDraft.status
review_notes
confirmed_at / closed_at if configured
```

## 4. Query Plan

The repository now has a non-executing plan generator:

```bash
uv run python scripts/collection_plan.py
```

Outputs:

```text
out/collection_plan.json
out/collection_plan.md
```

This generator reads `registry/suppliers.yaml`, expands supplier domains, email-domain seeds, access-host patterns, company aliases, program keywords, and regional keywords, then maps each item to ontology landing targets. Every private/context query seed is emitted with `execute=false`.

After generating the plan, run the readiness check:

```bash
uv run python scripts/early_warning_readiness.py
```

Outputs:

```text
out/early_warning_readiness.json
out/early_warning_readiness.md
```

This verifies collection coverage and the current synthetic active-on-top ranking invariant.

When an approved private connector exists, it should emit local JSONL candidate records and hand them to Omija through:

```bash
uv run python scripts/import_candidate_signals.py --input data/private_candidates/candidates.jsonl
```

The command does not call a provider API. It validates and normalizes local candidate records, then writes ignored local outputs:

```text
out/private_candidate_import.json
out/private_candidate_import.md
```

See `docs/stealthmole-api-integration.md` for the candidate signal envelope and field mapping.

### Daily Scheduled Queries

For each supplier:

```text
domain exact match
email domain match
vpn/sso/mail/admin/dev host match
company alias exact match
```

For each program:

```text
program name
prime name + program name
supplier alias + program keyword
```

For country/region monitoring:

```text
<country/region> + defense
<country/region> + aerospace
<country/region> + shipbuilding
<country/region> + electronics
<country/region> + missile / radar / avionics / mro
```

Country/keyword results should enter `ThreatSource` or a review queue first. They should not automatically create `CredentialExposure`.

### Event-Driven Queries

Run focused queries when:

- CISA KEV/EPSS flags a relevant access product.
- a supplier is added to registry.
- a program becomes high priority.
- DT/TT mentions a supplier or program repeatedly.
- a new VPN/SSO/mail asset is discovered.

## 5. Normalization Rules

### Identity

Normalize:

```text
lowercase email
strip display names
canonicalize obvious local-part variants only as MergeProposal
```

Do not auto-merge identities if confidence is low. Create `MergeProposal(status=proposed)`.

### Domain / Asset

Normalize:

```text
fqdn lowercase
strip URL path/query for host matching
classify asset_type by host pattern and confirmed inventory
```

### Exposure

Dedup key:

```text
(canonical_identity, target_asset, secret_fingerprint)
```

Do not let re-circulated combo lists refresh `first_seen` freshness. For cookie/session evidence, use `InfectedDevice.infected_at`.

### Threat Mentions

Threat mentions are weaker than exposure/device evidence. They can increase context confidence but should not create Band A alone.

## 6. Risk Use

Band before score:

| Band | Condition |
|---|---|
| A | recent infostealer/device evidence + session/account/access target + supplier-to-program path |
| B | correlated high-value exposure or repeated evidence, active condition incomplete |
| C | passive/stale credential exposure |
| D | weak mention or unlinked context |

Score sorts within the band. It must not allow Band C volume to outrank Band A active candidates.

## 7. Review Workflow

1. `ComputeSupplierRisk` produces or updates `RiskAssessment`.
2. `FlagActiveCompromise` opens `CompromiseIncident` only when evidence and path exist.
3. `PropagateProgramRisk` updates `ProgramExposure`.
4. `GenerateNotificationDraft` creates a draft with `cites` links.
5. Human reviewer marks draft `reviewed`, `approved`, or `exported`.
6. Confirmation logs decide whether incident becomes `acknowledged`, `assigned`, `closed`, or remains open.

## 8. Implementation Backlog

### Short Term

- Expand synthetic corpus to 12-20 suppliers and 25-50 domains.
- Add query-plan examples to demo pages as locked/private slots.
- Add public context cards to `RiskAssessment.components`.
- Make `out/omija_console_home.html` show collection coverage by data class.

### Medium Term

- Build a `CandidateSignal` staging table or dataset for approved private-feed normalized outputs.
- Add review queue for country/keyword `ThreatSource` hits.
- Add asset discovery workflow for new target hosts.
- Add confirmation-log result slots without importing raw logs into public demo.

### Later / Production

- Role-based access control for sensitive evidence.
- Secret destruction audit.
- Supplier notification workflow approval.
- Internal SIEM/IAM/EDR integrations for confirmation.
- False-positive/false-negative evaluation on approved historical incidents.

## 9. Source References

Public context sources used by current scripts:

- CISA KEV catalog: `https://www.cisa.gov/known-exploited-vulnerabilities-catalog`
- NVD CVE API: `https://nvd.nist.gov/developers/vulnerabilities`
- FIRST EPSS API: `https://www.first.org/epss/api`
- CISA cybersecurity advisories RSS: `https://www.cisa.gov/cybersecurity-advisories/all.xml`
- CISA ICS advisories RSS: `https://www.cisa.gov/cybersecurity-advisories/ics-advisories.xml`
- MITRE ATT&CK STIX data: `https://github.com/mitre-attack/attack-stix-data`
- URLhaus: `https://urlhaus.abuse.ch/`
- HIBP breaches API: `https://haveibeenpwned.com/API/v3#BreachesForAccount`
