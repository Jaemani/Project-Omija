# 2026-07-04 — Foundry OSDK Smoke

Generated Python OSDK package `omija_sdk` was installed and imported locally.
The bootstrap path is now:

```bash
uv run python scripts/foundry_osdk_bootstrap.py
```

## Confirmed

- Object reads work through OSDK.
- Join-table links work through OSDK:
  `sup-h -> subcontracts_to -> sup-f -> primes -> prime-x -> programs`.
- Derived/provenance join-table links work:
  `CompromiseIncident -> traverses_*` and `NotificationDraft -> compromise_incidents`.
- Actual generated link API names differ from the original build guide in places:
  `subcontracts_to`, `primes`, `programs`, `identity`, `domain`,
  `compromise_incidents`.

## Current Failure

After converting several FK links to join-table backing and force-reinstalling
the generated OSDK, the current state is:

- OK: `Supplier sup-h -> subcontracts_to -> Supplier sup-f`
- OK: `Supplier sup-f -> primes -> Prime prime-x`
- OK: `Prime prime-x -> programs`
- OK: `Identity -> domain`
- OK: `CredentialExposure -> identity`
- OK: `CredentialExposure -> domain`
- OK: `CredentialExposure -> threat_source`
- OK: `CompromiseIncident -> traverses_*`
- OK: `NotificationDraft -> compromise_incidents`

Final smoke after MCP enablement and Foundry link backing updates:

- OK: `Supplier sup-h -> domains -> Domain micro-h.example`
- OK: `Prime prime-x -> domains -> Domain vpn.prime-x.example`
- OK: `InfectedDevice dev:micro-h:laptop1 -> credential_exposures -> exp:micro-h:active`

`edit_credential_exposure` does not expose `identity` or `domain` parameters,
so this cannot be fixed by generated CRUD actions.

## Fast Fix

For the hackathon path, keep the working join-table pattern. The remaining
foundation/evidence links were fixed by using join-table datasource links and
the existing seed CSVs:

- `23_link_owns.csv`
- `24_link_prime_owns.csv`
- `29_link_leaked.csv`

For these links, the expected datasource column mapping is:

- `owns`: `left-Supplier-primary-key -> Supplier.id`,
  `right-Domain-primary-key -> Domain.domain_fqdn`
- `prime_owns`: `left-Prime-primary-key -> Prime.id`,
  `right-Domain-primary-key -> Domain.domain_fqdn`
- `leaked`: `left-InfectedDevice-primary-key -> InfectedDevice.id`,
  `right-CredentialExposure-primary-key -> CredentialExposure.id`

After any future ontology link backing change, rerun:

```bash
uv run python scripts/foundry_osdk_bootstrap.py --force-reinstall
uv run python scripts/foundry_osdk_smoke.py --diagnose
```

If any ontology API names change, regenerate and reinstall the Python OSDK.

## Final Read-Only Demo

Implemented and verified the read side needed for the hackathon demo:

- `store/osdk_compat.py`: generated OSDK compatibility helpers.
- `store/foundry.py`: read-only `FoundryOntologyStore`.
- `scripts/foundry_osdk_bootstrap.py`: install/probe/smoke from `.env`.
- `scripts/foundry_osdk_smoke.py --diagnose`: live ontology link diagnostic.
- `scripts/demo_e2e.py --compare --supplier sup-h`: SQLite vs Foundry decision-path comparison.
- `scripts/foundry_demo_report.py`: Foundry-backed static HTML report at `out/foundry_demo.html`.

Verified:

```bash
uv run pytest -q
uv run python scripts/foundry_osdk_smoke.py --diagnose
uv run python scripts/demo_e2e.py --compare --supplier sup-h
uv run python scripts/foundry_demo_report.py
```

Latest result: `112 passed`; smoke links all `OK`; E2E compare `RESULT: OK`.
