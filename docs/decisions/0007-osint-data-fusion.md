# ADR-0007: OSINT Data Fusion Overlay

Date: 2026-07-04
Status: Approved

## Context

The project target is Track 2/3: OSINT, knowledge graph, LLM-assisted analysis,
data fusion, and defense intelligence. StealthMole credential exposure remains a
strong early-warning signal, but the demo cannot depend on a single commercial
feed being available at judging time.

The current Foundry ontology already proves the core graph:

```text
CredentialExposure -> Identity -> Domain -> Supplier
Supplier -> Supplier -> Prime -> Program
CredentialExposure -> target Domain -> Prime asset
CompromiseIncident -> traverses_* provenance
NotificationDraft -> cites evidence
```

The missing piece was public intelligence context explaining why the target
asset and exposure path matter now.

## Decision

Use public OSINT feeds as an overlay for the hackathon demo. Do not add CVE,
TTP, IOC, or advisory object types before the deadline.

Implemented public feeds:

- NVD CVE API for critical VPN CVEs.
- CISA KEV for known exploited vulnerabilities.
- MITRE ATT&CK Enterprise for credential-access and initial-access techniques.
- abuse.ch URLhaus for recent malicious URL tags and stealer/loader context.

Mapping:

- `Domain.asset_type` selects the relevant OSINT filter.
- `CredentialExposure.targets -> Domain` identifies the target asset.
- `RiskAssessment.components` stores the derived context.
- `CompromiseIncident.path_snapshot` remains the active path record.
- `NotificationDraft.cites` can cite incident and evidence summaries.

## Rationale

This preserves the ontology that was already built and validated in Foundry. It
also keeps the demo honest:

- public OSINT is real and refreshable;
- Foundry path traversal is live OSDK readback;
- credential-exposure records remain synthetic unless the authorized live
  StealthMole pipeline succeeds.

## Consequences

Positive:

- The demo no longer blocks on StealthMole availability.
- The Track 2/3 story becomes data fusion instead of API integration only.
- Reviewers can inspect generated JSON/HTML artifacts without secrets.
- Ontology churn is minimized before the hackathon deadline.

Tradeoffs:

- CVE/TTP/IOC search is not first-class in Foundry yet.
- OSINT evidence is summarized into risk components rather than modeled as full
  ontology objects.
- Future ACL/audit requirements may require first-class `Vulnerability`,
  `Technique`, `Indicator`, or `Advisory` objects.

## Rejected Options

| Option | Reason rejected |
|---|---|
| Add `CVE`, `Technique`, `IOC`, and `Advisory` object types immediately | Too much ontology churn before demo; link and action surface would expand without enough testing time. |
| Treat synthetic `CredentialExposure` seed as real leaked data | Incorrect and unsafe claim. |
| Block the demo on StealthMole auth | The project must still prove data fusion when one feed is unavailable. |
| Hide StealthMole status | Reviewers should see that the integration boundary exists and that 401 evidence is captured without secrets. |

## Follow-Up

After the demo, consider a v0.4 ontology ADR for first-class OSINT objects:

- `Vulnerability`
- `Technique`
- `Indicator`
- `Advisory`
- `Observation`

Only add them when search, ACL, audit, or workflow requirements justify the
additional ontology surface.
