# Claims and Limitations

This document prevents overclaiming during demo, judging, or handoff.

## Safe Claims

1. Omija models defense supplier credential exposure as ontology objects and links.
2. Omija can ingest approved filtered StealthMole hackathon API rows through a normalization boundary.
3. Omija removes or blocks API secrets, JWTs, raw provider envelopes, and reusable password/cookie/token material from public artifacts.
4. Omija separates `CredentialExposure.of` from `CredentialExposure.targets` so owner organization and observed target asset can differ.
5. Omija uses `Supplier.subcontractsTo*` to propagate verification priority through variable-depth supply-chain paths.
6. Omija ranks active-compromise candidates above high-volume passive leaks when the configured evidence conditions are present.
7. Omija generates human-reviewed `NotificationDraft` objects; it does not automatically send notifications.
8. Foundry evidence currently proves ontology/workflow setup, of/targets backing dataset lineage, OSDK availability, and selected action readbacks.

## Do Not Claim

1. Omija confirms a real breach.
2. Band A means successful login or confirmed compromise.
3. `targets` means actual access succeeded.
4. Public demo artifacts contain raw leaked credentials.
5. Omija stores or displays raw passwords, cookies, tokens, JWTs, or provider response envelopes.
6. Foundry full end-to-end reasoning readback is completely solved.
7. Omija automatically contacts suppliers or sends notifications.

## Provenance Labels

| Label | Meaning | Safe use |
| --- | --- | --- |
| `SYNTHETIC` | Made-up suppliers, identities, devices, exposures | Incident corpus and engine proof |
| `PUBLIC_CONTEXT` | Public CVE/advisory/technique/breach metadata | Asset-risk background |
| `APPROVED_PROVIDER` | Filtered StealthMole hackathon API rows | Row-level lineage after redaction |
| `ENGINE` | Computed by local scoring/path logic | Ranking, incidents, program rollups |
| `LIVE_FOUNDRY` | Foundry ontology/action/readback evidence | Ontology and workflow proof |
| `LOCKED_SECRET` | API credentials, JWTs, raw provider envelopes, reusable secret values | Never exported or displayed |

## Current Limits

- Field mapping from non-zero provider rows is still conservative: expose only normalized object/link names, hashes, booleans, timestamps, module status, and counts.
- DT/TT coverage depends on the hackathon account scope. Current observed statuses can include 403/404.
- Actual compromise confirmation requires VPN, SSO, IAM, EDR, mail logs, or supplier confirmation.
- Some Foundry seed backing datasets still need schema repair, so use the Foundry evidence wording above rather than claiming complete Foundry E2E reasoning.
