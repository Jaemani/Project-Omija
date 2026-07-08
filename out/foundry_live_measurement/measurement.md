# Foundry Live Measurement Bundle

Generated: `2026-07-05T06:50:05.357717+00:00`

This bundle converts approved filtered StealthMole hackathon rows into Foundry-ready
ontology CSVs. It intentionally excludes raw provider envelopes, API secrets, JWTs,
raw emails, passwords, cookies, and tokens.

## Summary

- Input records: `150`
- Active candidates: `0`
- Unique observed domains: `17`
- Derived decision objects: `0`
- Decision reason: approved provider probe has no confirmed defense supplier path; do not create Incident/Draft without provenance

## Modules

- `cb`: `50` records
- `cds`: `50` records
- `cl`: `50` records

## Generated Files

- `01_supplier.csv`: `1` rows
- `03_program.csv`: `1` rows
- `04_domain.csv`: `17` rows
- `05_identity.csv`: `150` rows
- `06_credential_exposure.csv`: `150` rows
- `07_infected_device.csv`: `150` rows
- `08_threat_source.csv`: `150` rows
- `23_link_owns.csv`: `17` rows
- `25_link_belongs_to.csv`: `150` rows
- `26_link_of.csv`: `150` rows
- `27_link_targets.csv`: `150` rows
- `28_link_sourced_from.csv`: `150` rows
- `29_link_leaked.csv`: `150` rows
- `30_link_compromises.csv`: `150` rows

## Foundry Load Order

1. Object CSVs: `01`, `03`, `04`, `05`, `06`, `07`, `08`.
2. Link CSVs: `23`, `25`, `26`, `27`, `28`, `29`, `30`.
3. Re-index ontology object/link types.
4. Measure object counts and path readback against `measurement.json`.
