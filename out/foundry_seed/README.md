# Foundry seed data

This seed follows `ontology.md`: object properties stay on object CSVs, links use separate join-table CSVs.

Import/replace object CSVs `01_*.csv` through `13_*.csv` first.
Then use link CSVs `20_*.csv` through `45_*.csv` as join-table datasources for the matching Link Types.

Important:
- If a Link Type was recreated as foreign-key based, it will not use these link CSVs. Recreate it as join-table based or add the FK property to the Object Type.
- If Foundry generated different join-table column names, keep the row values but rename the two CSV headers to exactly match the Link Type's expected columns.
- Foundry Link Types are concrete pairs. Conceptual union links like `evidenced_by` and `cites` are split by target type in this seed.

Primary Object Explorer paths to verify:
1. `sup-h -> subcontractsTo -> sup-f -> supplies -> prime-x -> runs -> prog-sentinel`
2. `exp:micro-h:active -> of -> id:ops@micro-h.example -> belongsTo -> micro-h.example -> owns(reverse) -> sup-h`
3. `exp:micro-h:active -> targets -> vpn.prime-x.example -> primeOwns(reverse) -> prime-x -> runs -> prog-sentinel`
4. `incident:micro-h:active -> traverses_* -> Identity/Domain/Supplier/Prime/Program`
5. `draft:sup-h:2026-07-03 -> cites_* -> Exposure/Device/Incident/Risk`

This seed is synthetic. It contains no real secrets; `masked_value` is already redacted.
