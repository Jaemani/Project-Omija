# Omija Collection Plan

Generated: `2026-07-04T21:18:17.030394+00:00`

Mode: `non_executing_collection_plan`

This file is a non-executing plan. It contains query seeds and ontology landing
targets only. It does not call private feeds or store credential material.

## Summary

- Suppliers: `9`
- Primes: `2`
- Programs: `2`
- Private/context query seeds: `118`
- Public context jobs: `2`

## Query Seeds By Track

- `alias_and_keyword_discovery`: 9
- `asset_surface_discovery`: 81
- `private_exposure_candidate`: 18
- `program_keyword_context`: 3
- `regional_context`: 7

## Sample Query Seeds

- `domain:sup-a:supplier-a.example` | `domain_exact` | `supplier-a.example` -> CredentialExposure, InfectedDevice, Identity, Domain
- `email-domain:sup-a:supplier-a.example` | `email_domain` | `*@supplier-a.example` -> CredentialExposure, Identity
- `asset-host:sup-a:vpn.supplier-a.example` | `target_host_pattern` | `vpn.supplier-a.example` -> Domain, ThreatSource, InfectedDevice
- `asset-host:sup-a:sso.supplier-a.example` | `target_host_pattern` | `sso.supplier-a.example` -> Domain, ThreatSource, InfectedDevice
- `asset-host:sup-a:mail.supplier-a.example` | `target_host_pattern` | `mail.supplier-a.example` -> Domain, ThreatSource, InfectedDevice
- `asset-host:sup-a:owa.supplier-a.example` | `target_host_pattern` | `owa.supplier-a.example` -> Domain, ThreatSource, InfectedDevice
- `asset-host:sup-a:groupware.supplier-a.example` | `target_host_pattern` | `groupware.supplier-a.example` -> Domain, ThreatSource, InfectedDevice
- `asset-host:sup-a:citrix.supplier-a.example` | `target_host_pattern` | `citrix.supplier-a.example` -> Domain, ThreatSource, InfectedDevice
- `asset-host:sup-a:dev.supplier-a.example` | `target_host_pattern` | `dev.supplier-a.example` -> Domain, ThreatSource, InfectedDevice
- `asset-host:sup-a:admin.supplier-a.example` | `target_host_pattern` | `admin.supplier-a.example` -> Domain, ThreatSource, InfectedDevice
- `asset-host:sup-a:portal.supplier-a.example` | `target_host_pattern` | `portal.supplier-a.example` -> Domain, ThreatSource, InfectedDevice
- `alias:sup-a` | `company_alias` | `Alpha Precision` -> ThreatSource, MergeProposal
- `domain:sup-b:supplier-b.example` | `domain_exact` | `supplier-b.example` -> CredentialExposure, InfectedDevice, Identity, Domain
- `email-domain:sup-b:supplier-b.example` | `email_domain` | `*@supplier-b.example` -> CredentialExposure, Identity
- `asset-host:sup-b:vpn.supplier-b.example` | `target_host_pattern` | `vpn.supplier-b.example` -> Domain, ThreatSource, InfectedDevice
- `asset-host:sup-b:sso.supplier-b.example` | `target_host_pattern` | `sso.supplier-b.example` -> Domain, ThreatSource, InfectedDevice
- `asset-host:sup-b:mail.supplier-b.example` | `target_host_pattern` | `mail.supplier-b.example` -> Domain, ThreatSource, InfectedDevice
- `asset-host:sup-b:owa.supplier-b.example` | `target_host_pattern` | `owa.supplier-b.example` -> Domain, ThreatSource, InfectedDevice
- `asset-host:sup-b:groupware.supplier-b.example` | `target_host_pattern` | `groupware.supplier-b.example` -> Domain, ThreatSource, InfectedDevice
- `asset-host:sup-b:citrix.supplier-b.example` | `target_host_pattern` | `citrix.supplier-b.example` -> Domain, ThreatSource, InfectedDevice

## Public Jobs

```text
uv run python scripts/public_context_snapshot.py
uv run python scripts/public_context_matrix.py
```

## Guardrails

- `execute=false` for every private/context query seed.
- Raw password, cookie, token, session value storage is forbidden.
- Country/keyword hits land as `ThreatSource` or review candidates first.
- `CredentialExposure` and `InfectedDevice` require normalized identity/host evidence.
- `NotificationDraft` is human-reviewed; no automatic send action.
