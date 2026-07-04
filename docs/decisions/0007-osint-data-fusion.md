# ADR-0007: Public Context Slots, Not Live OSINT Fetching

Date: 2026-07-04  
Status: Superseded by 2026-07-05 no-live-data directive

## Context

Project Omija targets Track 2/3: OSINT, knowledge graph, LLM-assisted analysis,
data fusion, and defense intelligence. The core claim is not feed collection.
The core claim is that the ontology can turn an approved candidate signal into
identity, target asset, supplier path, program impact, risk object, incident
object, and human-reviewed response.

The Foundry ontology already proves the reasoning spine:

```text
CredentialExposure.of -> Identity
CredentialExposure.targets -> Domain
Identity.belongs_to -> Domain
Supplier.owns -> Domain
Supplier.subcontractsTo -> Supplier
Supplier.supplies -> Prime
Prime.runs -> Program
CompromiseIncident.traverses_* -> path nodes
NotificationDraft.cites -> reviewed evidence slots
```

## Current Decision

Do not fetch public feeds in the main demo. Keep public intelligence as empty
candidate context slots only. This preserves the Track 2/3 data-fusion story
without handling live records during the demo.

Current implementation:
- `scripts/intelligence_demo.py` writes no-live-data ontology pages.
- `scripts/osint_collect.py` writes disabled placeholder context if run.
- Existing summarizer helpers remain for tests and future approved offline
  fixtures.

## Rationale

This keeps the project focused on the ontology engine:
- `of` and `targets` separation explains cross-organization access.
- variable-depth `subcontractsTo` explains supplier-path propagation.
- `traverses_*` links preserve path drill-down.
- `cites` and draft-only action state preserve review provenance.
- risk banding is a structural ontology outcome, not a feed-volume score.

## Consequences

Positive:
- demo cannot accidentally fetch or display live public-feed records;
- reviewers see the problem-solving model without data-handling risk;
- future approved evidence packages can occupy the same slots without ontology
  redesign.

Tradeoffs:
- no current claim of real public-feed collection;
- CVE/TTP/IOC/advisory objects remain future work;
- presentation must explain candidate slots clearly.

## Rejected Current Option

Using live public feeds as the demo surface is rejected for the current handoff.
The project should show where such context would attach, not collect it.
