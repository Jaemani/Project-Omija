# StealthMole API Integration Contract

> 2026-07-08 status note: the latest finals state is recorded in `README.md`,
> `docs/decisions/0009-approved-provider-foundry-lineage.md`, and
> `docs/review/foundry-live-measurement-update.md`. Approved filtered
> StealthMole hackathon rows have been used for sanitized lineage and Foundry
> measurement. This contract still defines the safe boundary: no raw provider
> envelope, raw password, cookie, token, API key, JWT, or reusable secret value
> may be committed or displayed.

This document defines how StealthMole can be connected to Omija without storing private API details or sensitive records in the public/tracked repository.

## Current Status

Tracked repo status:

- Live StealthMole client code is intentionally not present.
- Endpoint and runtime credential material are not stored in tracked files.
- `adapter/stealthmole.py` stays neutralized until an explicit sensitive-data handling plan is approved.

What is documented here:

- which StealthMole capabilities Omija expects;
- what query shapes Omija needs;
- how response fields map into Omija ontology objects;
- how an external/private connector can hand normalized candidate records to Omija.

## Local Validation Status

As of 2026-07-05 KST, the private connector has been validated locally without
committing endpoint/auth details or provider records:

| Capability | Status | Validation scope | Demo use |
|---|---|---|---|
| CL | Connected | synthetic supplier domain search returned cleanly with 0 records | `CredentialExposure` candidate input |
| CDS | Connected | synthetic supplier domain search returned cleanly with 0 records | `InfectedDevice` / active-candidate input |
| CB | Connected as auxiliary | synthetic supplier domain search returned cleanly with 0 records | optional exposure candidate input |
| DT | Not yet connected | local call reached provider boundary but returned permission/scope error | keep as `ThreatSource` design slot |
| TT | Not yet connected | local call did not match an enabled provider path/module name | keep as `ThreatSource` design slot |

This status proves the auth/search boundary for CL/CDS, not real exposure
coverage. Real supplier or keyword collection still requires an approved target
scope and private handling policy. Synthetic zero-row checks are enough for API
connectivity; they are not evidence about any real organization.

## Capability Mapping

| Capability | Omija use | Primary landing object | Secondary landing object |
|---|---|---|---|
| Credential Lookout (CL) | supplier-domain or email-domain leaked-account candidates | `CredentialExposure` | `Identity`, `ThreatSource` |
| Compromised Data Set (CDS) | infostealer/device candidates and active-risk hints | `InfectedDevice` | `CredentialExposure`, `Identity`, `ThreatSource` |
| Darkweb Tracker (DT) | forum/market mention context by supplier, domain, product, program, region | `ThreatSource` | review queue / `ProgramExposure.components` |
| Telegram Tracker (TT) | channel mention context by supplier, domain, product, program, region | `ThreatSource` | review queue / `ProgramExposure.components` |
| Country/region search | exposure trend and gap discovery | `ThreatSource` aggregate | collection coverage metrics |
| Keyword search | alias, target host, product, program discovery | `ThreatSource` | `MergeProposal`, asset discovery queue |

## Query Contract

Omija's collection planner emits query seeds in `out/collection_plan.json`.

Each seed has this shape:

```json
{
  "execute": false,
  "track": "private_exposure_candidate",
  "query_type": "domain_exact",
  "query_value": "supplier-a.example",
  "provider_capabilities": ["CL", "CDS"],
  "ontology_targets": ["CredentialExposure", "InfectedDevice", "Identity", "Domain"]
}
```

An external/private connector may execute these query seeds outside the tracked repo. The connector should not write raw provider responses into Git. It should emit a local JSONL file following the candidate signal envelope below.

## Candidate Signal Envelope

Each collected candidate line should be a JSON object:

```json
{
  "module": "cds",
  "scope": {
    "supplier_id": "sup-a",
    "query_type": "domain_exact",
    "query_value": "supplier-a.example"
  },
  "raw": {
    "id": "provider-record-id",
    "user": "ops@supplier-a.example",
    "host": "vpn.prime-x.example",
    "has_cookie": true,
    "infected_at": "2026-07-01T00:00:00Z",
    "malware": "ExampleStealer",
    "account_type": "vpn"
  }
}
```

Allowed module values:

```text
cl
cds
ub
cb
dt
tt
```

`cl`, `cds`, `ub`, and `cb` can normalize into exposure/device candidates. `dt` and `tt` are context signals and should land as `ThreatSource`/review queue unless a domain, identity, and target host are explicitly resolved.

## Field Mapping

The normalization boundary accepts provider-specific aliases conservatively.

| Candidate field aliases | Omija normalized field |
|---|---|
| `user`, `email`, `login`, `username`, `account` | `Identity.email` or `Identity.username` |
| `host`, `url`, `domain`, `site` | target host / `Domain` candidate |
| `password`, `passwd`, `pwd` | `Secret.present`, masked value, one-way fingerprint candidate |
| `session_cookie`, `cookie`, `session` | cookie presence only; raw value must not persist |
| `has_cookie`, `has_session_cookie` | `InfectedDevice.has_session_cookie` |
| `infected_at`, `infection_date`, `compromised_at`, `log_date` | `InfectedDevice.infected_at` |
| `malware`, `stealer`, `family`, `malware_name` | `InfectedDevice.malware` |
| `account_type`, `category`, `role`, `service` | active-risk account class |
| `id`, `_id`, `record_id`, `uuid` | `source_ref` |

## Import Command

Use a local, untracked JSONL file:

```bash
uv run python scripts/import_candidate_signals.py --input data/private_candidates/candidates.jsonl
```

Outputs:

```text
out/private_candidate_import.json
out/private_candidate_import.md
```

These outputs are intentionally ignored by Git. They are for local validation before Foundry/ontology ingestion.

## Required Runtime Guardrails

The private connector must enforce:

1. No raw password, cookie, token, or session value is committed.
2. Raw provider response files stay outside Git.
3. Every record has `source_ref` provenance.
4. Every exposure candidate has enough fields to resolve identity and target host, or it stays in a review queue.
5. Country/keyword hits land as `ThreatSource` context first.
6. Active-compromise wording remains "candidate" until VPN/SSO/IAM/EDR/mail/supplier confirmation exists.

## What Is Still Not Documented In Tracked Repo

The following must live in a private operational runbook, not in tracked project files:

- provider endpoint hostname and routes;
- runtime credential names and values;
- request signing procedure;
- full raw response samples containing real exposure records;
- rate limits tied to a private contract;
- any organization-specific target list not approved for public demo.

This split is intentional: the public repo documents the integration contract and ingestion boundary; the private runbook carries vendor and account-specific execution details.

Local private files, if present, live under ignored paths:

```text
docs/private/
scripts/private/
data/private_candidates/
```

The expected local flow is:

```text
private connector -> data/private_candidates/candidates.jsonl
  -> scripts/import_candidate_signals.py
  -> out/private_candidate_import.*
```

`data/private_candidates/` and `out/private_candidate_import.*` are ignored by Git.
