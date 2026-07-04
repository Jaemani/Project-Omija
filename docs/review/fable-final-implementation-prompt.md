# Fable Prompt — Final Implementation Review

Use this with `claude -p --model fable` when Fable quota is available.

```text
Project Omija hackathon implementation review.

Context:
- Foundry ontology and seed data are visible in Object Explorer.
- Python OSDK smoke verifies core links:
  - Supplier subcontractsTo Supplier
  - Supplier supplies Prime
  - Prime runs Program
  - Supplier owns Domain
  - Prime prime_owns Domain
  - Identity belongs_to Domain
  - CredentialExposure of Identity
  - CredentialExposure targets Domain
  - CredentialExposure sourced_from ThreatSource
  - InfectedDevice leaked CredentialExposure
  - CompromiseIncident traverses Supplier/Program
  - NotificationDraft cites CompromiseIncident
- Implemented:
  - read-only FoundryOntologyStore
  - generated OSDK bootstrap/smoke
  - SQLite vs Foundry demo_e2e comparison
  - Foundry-backed static demo report
  - final_demo_check.py one-command pre-demo verification
- Under two-day hackathon constraints.
- Do not depend on or discuss any external threat-intelligence provider. Treat seed evidence as already present in Foundry.

Ask:
Give a concrete priority plan for what Codex should implement next, ordered by demo impact. Include tests, stop conditions, and what should explicitly not be implemented before the deadline.
```
