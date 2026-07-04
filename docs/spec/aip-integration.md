# aip-integration.md — Foundry/AIP ontology boundary

Status: updated 2026-07-05.

AIP/OSDK work should focus on the ontology model and decision objects, not live
data ingestion.

## Current Scope

- Build Object Types and Link Types from `ontology.md`.
- Load neutral seed CSVs when a Foundry demo needs structure.
- Use placeholder source IDs only.
- Keep Action Types as review/state transitions.
- Do not add actions that send messages outside Foundry.

## Important Links

```text
CredentialExposure.of -> Identity
CredentialExposure.targets -> Domain
Identity.belongs_to -> Domain
Supplier.owns -> Domain
Supplier.subcontractsTo -> Supplier
Supplier.supplies -> Prime
Prime.runs -> Program
RiskAssessment.evidenced_by -> evidence objects
CompromiseIncident.traverses_* -> path nodes
ProgramExposure.program_evidenced_by -> decision objects
NotificationDraft.cites -> reviewed evidence objects
```

## AIP Logic Boundary

Allowed:
- explain why an incident path is incomplete;
- propose review states;
- summarize blank candidate slots;
- generate draft text only when approved non-sensitive evidence exists.

Not allowed:
- live credential lookup;
- raw secret handling;
- automatic notification sending;
- endpoint/auth/key troubleshooting.
