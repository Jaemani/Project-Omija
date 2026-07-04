# Open Data Catalog for Omija

Purpose: explain what public, non-sensitive data can strengthen the demo without putting real leaked credentials on screen.

## Decision

Use synthetic organizations, identities, credentials, and devices for the demo. Use public data only as context around asset classes, attacker techniques, vulnerability urgency, and breach/infostealer reality. Do not mix real account or credential records into hosted demo pages.

## Candidate Sources

| Source | Use | Store raw? | Ontology fit | Demo label |
|---|---|---:|---|---|
| CISA KEV | Known exploited vulnerability context for VPN, SSO, firewall, mail, remote access assets | Yes, safe snapshot | `RiskAssessment.components.public_context.kev` | `PUBLIC_CONTEXT` |
| NVD CVE API | Broader CVE context by asset keyword (`vpn`, `citrix`, `fortinet`, `ivanti`) | Summary + sampled CVE metadata | `Domain.asset_type` -> `RiskAssessment.components.cve_context` | `PUBLIC_CONTEXT` |
| FIRST EPSS | Exploit-likelihood signal for CVE prioritization | Summary + sampled CVE probability metadata | `RiskAssessment.components.epss_context` | `PUBLIC_CONTEXT` |
| CISA advisory RSS | Recent public advisory context, including access and campaign language | Title/link/date only | `ThreatSource.kind`, `ProgramExposure.components.public_advisory_context` | `PUBLIC_CONTEXT` |
| CISA ICS advisory RSS | Industrial-system advisory context relevant to manufacturing and defense suppliers | Title/link/date only | `ProgramExposure.components.ics_context` | `PUBLIC_CONTEXT` |
| MITRE ATT&CK STIX | Tactics and techniques explaining credential access and initial access | Yes, safe snapshot | `ThreatSource.kind`, `RiskAssessment.components.techniques` | `PUBLIC_CONTEXT` |
| URLhaus | Malware distribution context tag counts | Aggregate only; do not store raw URLs in demo | `ProgramExposure.components.threat_context` | `PUBLIC_CONTEXT` |
| HIBP breach metadata | Explain breach data-class scale without querying accounts | Metadata only | Presentation layer, not core object yet | `PUBLIC_CONTEXT` |
| StealthMole public pages | Show what kind of credential-protection fields exist publicly | No private data | Data contract cards only | `VENDOR_PUBLIC` |

## What Not To Store

- real usernames, emails, passwords, cookies, sessions, or tokens;
- raw private vendor responses;
- raw malicious URL tables in hosted pages;
- real supplier domains unless explicitly cleared;
- any automatic notification-send action.

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

The ontology is what turns signal into decision path. Public data explains why asset classes matter; synthetic data proves the reasoning engine safely.

## Snapshot Script

Command:

```bash
uv run python scripts/public_context_snapshot.py
```

Outputs:

```text
out/public_context/summary.json
out/public_context/summary.md
```

Public context matrix:

```bash
uv run python scripts/public_context_matrix.py
```

Output:

```text
out/public_context_matrix.html
```

## Presentation Placement

Best visual placement:

- `out/public_context_matrix.html`: source-by-source proof that safe public data is available without touching credential records.
- `out/data_coverage_map.html`: show how public context sits beside synthetic seed and locked sensitive slots.
- `out/omija_console_home.html`: show public context as an operating rail, not the main product.
- `out/omija_demo.html`: use small `PUBLIC_CONTEXT` cards under target assets.

Avoid:

- putting public CVE/IOC counts above ontology path;
- making the product look like a feed collector;
- raw IOC tables in the first viewport.
