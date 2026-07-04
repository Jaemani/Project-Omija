# ADR-0008: Ontology-First Demo Surface

Date: 2026-07-04  
Status: Updated 2026-07-05

## Context

The demo must show product value immediately, but current direction forbids
live credential handling and public-feed fetching. Therefore the surface should
not look like a feed-ingestion report. It should look like an operating surface
for reasoning over approved candidate evidence slots.

The operational question remains:

> If a candidate exposure is approved for review, how does the ontology turn it
> into supplier impact, program blast radius, risk objects, and a human-reviewed
> response?

## Decision

Generate no-live-data Palantir-style pages:
- `out/intelligence_demo.html` as the main report;
- `out/omija_console_core.html` for gates and workflow;
- `out/omija_console_graph.html` for the ontology path;
- `out/omija_console_response.html` for decision objects and draft review;
- `out/palantir_v1.html`, `out/palantir_v2.html`, `out/palantir_v3.html` as
  visual/structure alternatives.

The page must foreground:
- why `of` and `targets` are separate links;
- why supplier propagation uses `subcontractsTo`;
- why incidents need `traverses_*` drill-down links;
- why `NotificationDraft.cites` is provenance, not messaging automation;
- why risk bands follow active ontology paths instead of raw volume.

## Rationale

The value is not "we fetched data." The value is a decision model:
- supplier identity and target asset can belong to different organizations;
- a deeper supplier can still propagate risk to a prime program;
- derived objects preserve reviewable decisions;
- response remains draft-only and human-approved.

## Consequences

Positive:
- demo cannot accidentally reveal or imply live records;
- judges can inspect the ontology reasoning without data-handling risk;
- multiple page variants make design choice explicit.

Tradeoffs:
- current surface proves reasoning structure, not feed coverage;
- future data integration needs a separate approved evidence package;
- full Foundry Workshop implementation remains future work.

## Guardrails

- Do not claim live data ingestion.
- Do not claim public feeds were fetched.
- Keep evidence and notification fields blank until an approved non-sensitive
  package exists.
- Keep all output draft-only.
