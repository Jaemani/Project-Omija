# Foundry seed data

Import/replace object CSVs `01_*.csv` through `08_*.csv`. This folder is FK-link mode: there are no separate link CSVs.

This assumes `Domain` primary key is `fqdn`.
If other Foundry API names differ, map columns during import. Keep the values unchanged.

Configure links as foreign-key links using these columns:

- `subcontracts_to`: Supplier.parent_supplier_id -> Supplier.id
- `supplies`: Supplier.prime_id -> Prime.id
- `runs`: Program.prime_id -> Prime.id
- `owns`: Domain.supplier_id -> Supplier.id
- `prime_owns`: Domain.prime_id -> Prime.id
- `belongs_to`: Identity.domain_fqdn -> Domain.fqdn
- `of`: CredentialExposure.identity_id -> Identity.id
- `targets`: CredentialExposure.target_domain_fqdn -> Domain.fqdn
- `sourced_from`: CredentialExposure.threat_source_id -> ThreatSource.id
- `leaked`: CredentialExposure.infected_device_id -> InfectedDevice.id
- `compromises`: InfectedDevice.identity_id -> Identity.id

Primary Object Explorer paths to verify:

1. `sup-h -> subcontractsTo -> sup-f -> supplies -> prime-x -> runs -> prog-sentinel`
2. `exp:micro-h:active -> of -> id:ops@micro-h.example -> belongsTo -> micro-h.example -> owns(reverse) -> sup-h`
3. `exp:micro-h:active -> targets -> vpn.prime-x.example -> primeOwns(reverse) -> prime-x -> runs -> prog-sentinel`

This seed is synthetic. It contains no real secrets; `masked_value` is already redacted.
