# ADR-0009: Approved Provider Rows as Foundry Lineage Input

Date: 2026-07-05
Status: Approved

## Context

Track judging feedback was direct: Omija's ontology reasoning was interesting, but the demo did not show enough real data lineage. The StealthMole hackathon API data is approved and already filtered for the event, so keeping the provider rail as an empty or live-only slot weakens the system claim.

Public artifacts still must not expose API keys, JWTs, raw provider envelopes, passwords, cookies, tokens, or raw account identifiers.

## Decision

Use approved filtered StealthMole hackathon rows as real provider input for finals lineage, but export only sanitized Foundry-ready rows:

- `CredentialExposure`
- `InfectedDevice`
- `ThreatSource`
- hashed `Identity`
- observed `Domain`
- `of`, `targets`, `sourced_from`, `leaked`, `compromises` links

Raw email/account values are replaced with stable `source_ref_hash` identities. Short passwords/cookies/tokens are not prefix-masked; import boundary forces `redacted:<hash>` masks independent of raw value.

## Implementation Record

- Provider records collected: 150
- Normalized exposures: 150
- Foundry-ready object/link CSVs generated: 14 files
- Existing ontology backing dataset upload: 14/14 OK
- Existing ontology backing dataset schema PUT: 14/14 OK
- Separate schema-aware live measurement datasets: 14/14 OK
- Foundry SQL counts: 14/14 match expected row counts
- Ontology OSDK live PK readback: index refresh pending

## Rationale

This keeps the technical proof aligned with the product claim:

- Provider data really enters Omija.
- Omija redacts at adapter/import boundary.
- Foundry can store and measure sanitized object/link rows.
- Derived decision objects are not created unless enough provenance and a defense supplier path exist.

## Consequences

Positive:

- Finals can show 150 approved provider rows measured in Foundry.
- Secret handling remains enforceable by tests and safety scans.
- The boundary between real provider evidence and synthetic incident reasoning is explicit.

Tradeoff:

- Full ontology E2E readback is not claimed until Foundry datasource/index refresh makes `scripts/foundry_live_readback.py` pass.
