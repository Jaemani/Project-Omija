# Foundry seed data

Import object CSVs `01_*.csv` through `08_*.csv` first, then link CSVs `20_*.csv` through `30_*.csv`.

This assumes `Domain` primary key is `fqdn`. If your Link Type UI names the endpoint differently, map `domain_fqdn` to the Domain primary key.
If other Foundry API names differ, map columns during import. Keep the values unchanged.

Primary Object Explorer paths to verify:

1. `sup-h -> subcontractsTo -> sup-f -> supplies -> prime-x -> runs -> prog-sentinel`
2. `exp:micro-h:active -> of -> id:ops@micro-h.example -> belongsTo -> micro-h.example -> owns(reverse) -> sup-h`
3. `exp:micro-h:active -> targets -> vpn.prime-x.example -> primeOwns(reverse) -> prime-x -> runs -> prog-sentinel`

This seed is synthetic. It contains no real secrets; `masked_value` is already redacted.
