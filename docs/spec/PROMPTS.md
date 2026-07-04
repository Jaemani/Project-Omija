# PROMPTS.md — current safe prompts

Status: updated 2026-07-05.

Use these prompts for ontology reasoning only. Do not ask a model to design or
debug live credential-feed access.

## Fable Structure Review

```text
Review Project Omija as a no-live-data ontology engine.

Goal:
Explain whether the ontology can turn an approved candidate exposure slot into
Identity, target Domain, Supplier path, Prime, Program, RiskAssessment,
CompromiseIncident, ProgramExposure, and NotificationDraft.

Constraints:
- Do not propose live credential-feed access.
- Do not propose public-feed fetching.
- Do not include endpoint, key, token, or authentication details.
- Treat data values as empty candidate slots.
- Focus on why ontology links are necessary and why a flat table is insufficient.

Key links:
- CredentialExposure.of -> Identity
- CredentialExposure.targets -> Domain
- Supplier.subcontractsTo -> Supplier
- CompromiseIncident.traverses_* -> path nodes
- NotificationDraft.cites -> reviewed evidence
```

## Design Review

```text
Design a Palantir-style operating surface for a no-live-data ontology demo.

The page must show:
- policy gates: no live data, sensitive handling blocked, draft only;
- of vs targets separation;
- variable-depth supplier traversal;
- decision objects and required provenance links;
- empty candidate slots and candidate shape placeholders.

Do not design a landing page. Do not show real data. Do not include data-source
integration instructions.
```
