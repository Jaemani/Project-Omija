# 2026-07-04 Intelligence Demo Integration

This changelog records the current demo integration so another reviewer can
verify what changed, why it changed, and what is still unresolved.

## What Changed

### Public OSINT

- Added `scripts/osint_collect.py`.
- Pulls real public summaries from NVD, CISA KEV, MITRE ATT&CK, and abuse.ch
  URLhaus.
- Writes:
  - `out/osint/osint_summary.json`
  - `out/osint/osint_report.html`

### Integrated Demo

- Added `scripts/intelligence_demo.py`.
- Runs public OSINT collection.
- Runs Foundry OSDK ontology demo check.
- Runs StealthMole auth evidence collection as an optional status step.
- Writes:
  - `out/intelligence_demo.json`
  - `out/intelligence_demo.html`

### StealthMole Auth Evidence

- Added `scripts/stealthmole_auth_evidence.py`.
- Produces a secret-free `/user/quotas` debugging package.
- Records endpoint, server date, local date, JWT `iat` skew, key lengths, and
  HTTP status only.
- Does not write access keys, secret keys, JWTs, raw credentials, cookies, or
  bearer headers.

### Foundry Blast Radius

- Added `scripts/foundry_blast_radius.py`.
- Reads the Foundry OSDK store and shows:
  - exposure id;
  - owning supplier;
  - reachable programs;
  - incident provenance;
  - path confidence.
- Writes `out/blast_radius_exp_micro-h_active.json`.

### Documentation

- Added `docs/data-strategy.md` for feed classes, ontology mapping, and claim
  boundaries.
- Added `docs/decisions/0007-osint-data-fusion.md` for the OSINT overlay
  decision.
- Added `docs/decisions/0008-dashboard-first-demo-surface.md` for the
  dashboard-first presentation decision.
- Added `docs/demo-runbook.md` for the exact demo sequence.
- Added `docs/reviewer-guide.md` for independent verification.
- Updated README and demo notes to point to the integrated demo.

### Dashboard Surface

- Reworked `out/intelligence_demo.html` from a verification-style report into a
  dashboard-first surface.
- The first viewport now shows operational value, active exposures, programs at
  risk, affected supplier, and severity.
- The main panel shows `Ontology Path — Credential To Program`.
- Side panels show public OSINT corroboration, ranked analyst actions, an
  unsent advisory draft, and collection status.
- Design direction came from Claude Opus; implementation stayed in repo code.

## Why

The project is an OSINT and defense-intelligence data-fusion system. The demo
must show more than "call one credential API." It should connect heterogeneous
signals through the ontology and produce a decision: which supplier and program
need action first.

## Data Status

| Layer | Status | Reviewer claim |
|---|---|---|
| Public OSINT | Real public data | Safe to say "real public OSINT feeds were collected." |
| Foundry ontology path | Live OSDK readback from current ontology seed | Safe to say "the graph path is read back from Foundry." |
| Foundry credential seed | Synthetic | Do not claim it is real leaked credential data. |
| StealthMole live feed | Current `/user/quotas` auth returns `401` | Safe to say "integration boundary exists, but live auth is blocked." |

## Latest Verification

Run:

```bash
uv run pytest -q
uv run python scripts/intelligence_demo.py
```

Latest observed result:

- `121 passed`
- OSINT: `kev=1200/1631 nvd=20 attack=234 urlhaus_sample=1000`
- Foundry OSDK link smoke: all core links `OK`
- Intelligence demo: `RESULT: READY`
- Dashboard surface: `out/intelligence_demo.html`

## Known Open Issue

StealthMole auth still returns `401` at the hackathon endpoint even with JWT
timing aligned. The likely remaining causes are external to this repo: issued
key pair, account activation, API product enablement, or IP allowlist.
