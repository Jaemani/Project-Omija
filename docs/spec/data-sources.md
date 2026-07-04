# data-sources.md — redacted data-source boundary

Status: superseded by the 2026-07-05 no-live-data directive.

This project no longer documents or implements live credential-feed access.
Historical endpoint, authentication, key, and response-contract details have
been removed from the active repository documentation.

## Current Rule

- Do not add API keys, bearer tokens, JWTs, cookies, raw secrets, or reusable
  credentials.
- Do not implement live credential-feed clients.
- Do not fetch public feeds for the main demo.
- Keep candidate evidence slots empty unless an approved non-sensitive evidence
  package is explicitly provided.
- Use `HANDOFF.md`, `README.md`, `docs/data-strategy.md`, and `ontology.md` as
  the source of truth.

## Accepted Demo Input Shape

The ontology engine can explain where approved candidate data would attach
without storing values:

```text
CredentialExposure:
  id, module, secret_type, masked, first_seen, last_seen,
  source_ref, confidence, status

Identity:
  id, email or username, domain_ref, status

Domain:
  fqdn, asset_type, criticality, status

InfectedDevice:
  id, infected_at, has_session_cookie, account_type, malware, status

ThreatSource:
  id, kind="placeholder", name="Candidate placeholder",
  collected_at, confidence, status
```

The demo should use neutral placeholder IDs such as `src:candidate:empty`, not
vendor names.

## Ontology Mapping

```text
CredentialExposure.of -> Identity
CredentialExposure.targets -> Domain
Identity.belongs_to -> Domain
Supplier.owns -> Domain
Supplier.subcontractsTo -> Supplier
Supplier.supplies -> Prime
Prime.runs -> Program
CredentialExposure.sourced_from -> ThreatSource
CompromiseIncident.traverses_* -> path nodes
NotificationDraft.cites -> reviewed evidence slots
```

This mapping is the product core. Data collection is outside the current demo.
