# Open Data Catalog for Omija

Purpose: explain what public, non-sensitive data can strengthen the demo without
putting real leaked credentials on screen.

## Decision

Use synthetic organizations, identities, credentials, and devices for the demo.
Use public data only as context around asset classes, attacker techniques,
vulnerability urgency, and breach/stealer-log reality. Do not mix real account
or credential records into hosted demo pages.

## Candidate Sources

| Source | Use | Store raw? | Ontology fit | Demo label |
|---|---|---:|---|---|
| CISA KEV | Known exploited vulnerability context for VPN, SSO, firewall, mail, dev assets | Yes, safe snapshot | `RiskAssessment.components.public_context.kev` | `PUBLIC_CONTEXT` |
| NVD CVE API | Broader CVE context by asset keyword (`vpn`, `citrix`, `fortinet`, `ivanti`) | Summary only | `Domain.asset_type` -> `RiskAssessment.components.cve_context` | `PUBLIC_CONTEXT` |
| MITRE ATT&CK STIX | Tactics/techniques that explain credential access and initial access | Yes, safe snapshot | `ThreatSource.kind`, `RiskAssessment.components.techniques` | `PUBLIC_CONTEXT` |
| URLhaus | Malware distribution context and tag counts | Aggregate only; do not store raw URLs in demo | `ProgramExposure.components.threat_context` | `PUBLIC_CONTEXT` |
| HIBP breach metadata | Explain breach data classes and scale without querying accounts | Metadata only | Presentation layer, not a core object yet | `PUBLIC_CONTEXT` |
| StealthMole public pages | Show what kind of credential-protection fields exist publicly | No API, no private data | Data contract cards only | `VENDOR_PUBLIC` |
| StealthMole official integration docs | Shows domain-based UB/user lookup and no-action risk-exchange pattern | No secrets, no endpoint implementation | Explain future adapter boundary | `VENDOR_PUBLIC` |

## StealthMole Usage Without Sensitive Data

Allowed now:
- cite public product pages for field categories and concept explanation;
- show a data contract card: domain, username/account handle, leak month,
  source/bad actor, module/category, confidence;
- show the blank slot where approved private feed results would enter;
- state that real records are not suitable for hosted/recorded demos.

Not allowed now:
- querying private credential data;
- displaying real leaked username/password/cookie/session material;
- storing private vendor API responses;
- rebuilding API auth/client code in this repo.

## Why This Is Still Useful

The judging point is not "we found a password." It is:

```text
public context + approved candidate signal
  -> Identity
  -> target Domain
  -> Supplier path
  -> Prime / Program impact
  -> risk band
  -> human-reviewed draft
```

The ontology is what turns a signal into a decision path. Public data explains
why asset classes matter; synthetic data proves the reasoning engine safely.

## Snapshot Script

Optional command:

```bash
uv run python scripts/public_context_snapshot.py
```

Outputs:

```text
out/public_context/summary.json
out/public_context/summary.md
```

These files are intentionally not part of the main demo path unless explicitly
wired into a page with `PUBLIC_CONTEXT` provenance labels.

## Presentation Placement

Best visual placement:
- Steady-state console: "Public threat context" rail beside coverage map.
- Incident page: small `PUBLIC_CONTEXT` cards under the target asset.
- Program view: aggregate "why this program's access surfaces are watched" card.

Avoid:
- putting public CVE/IOC counts above the ontology path;
- making the product look like a feed collector;
- raw IOC tables in the first viewport.
