# Reviewer Guide

Use this page when handing the project to another teammate or judge. It lists
the exact files and checks needed to verify the current state.

## Review Order

1. Read [HANDOFF.md](../HANDOFF.md) for full project context and remaining work.
2. Read [README.md](../README.md) for the project entrypoint.
3. Read [docs/data-strategy.md](data-strategy.md) for data boundaries.
4. Read [docs/decisions/0007-osint-data-fusion.md](decisions/0007-osint-data-fusion.md) for the main design decision.
5. Read [docs/decisions/0008-dashboard-first-demo-surface.md](decisions/0008-dashboard-first-demo-surface.md) for the dashboard presentation decision.
6. Read [docs/changelog/intelligence-demo-2026-07-04.md](changelog/intelligence-demo-2026-07-04.md) for the change inventory.
7. Run the verification commands below.

## Verification Commands

```bash
uv run pytest -q
uv run python scripts/intelligence_demo.py
open out/intelligence_demo.html
```

Foundry-only fallback:

```bash
uv run python scripts/final_demo_check.py --full
uv run python scripts/foundry_blast_radius.py exp:micro-h:active
open out/foundry_demo.html
```

## Expected Artifacts

| Artifact | Meaning |
|---|---|
| `out/intelligence_demo.json` | Integrated machine-readable demo summary. |
| `out/intelligence_demo.html` | Main judging report. |
| `out/osint/osint_summary.json` | Public OSINT collection summary. |
| `out/osint/osint_report.html` | Public OSINT report. |
| `out/p0b/stealthmole_auth_evidence.json` | Secret-free StealthMole auth evidence. |
| `out/blast_radius_exp_micro-h_active.json` | Foundry OSDK blast-radius proof. |
| `out/foundry_demo.html` | Foundry-only report. |

## What To Confirm

- Public OSINT counts are present.
- The first viewport explains operational value, not just pipeline status.
- Foundry OSDK smoke check reports core links as `OK`.
- `exp:micro-h:active` reaches supplier `sup-h`.
- Blast radius includes `prog-sentinel` and `prog-harbor`.
- The active path is visible as `CredentialExposure -> Supplier -> Prime -> Program`.
- Recommended actions and the advisory are marked for analyst or human review.
- StealthMole status is shown as blocked if `/user/quotas` returns `401`.
- No generated artifact contains access keys, secret keys, JWTs, bearer tokens,
  raw passwords, or reusable cookies.

## Claim Boundary

Allowed:

- "The public OSINT layer uses real public data."
- "The Foundry path is live OSDK readback."
- "The live StealthMole integration boundary exists and records auth evidence."

Not allowed unless the live pipeline succeeds:

- "The seed credential exposure is real leaked data."
- "StealthMole live credential data was ingested."
- "A notification was sent."

Notifications remain drafts and require human approval.
