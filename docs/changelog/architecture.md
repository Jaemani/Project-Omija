# architecture.md changelog

Current status as of 2026-07-05: live credential-feed work is neutralized and
must not be resumed from historical notes. Previous endpoint/auth/debug details
have been redacted from this active changelog.

## 2026-07-05 — No-Live-Data Pivot

- Live credential-feed boundary emptied.
- Public-feed fetching removed from the main demo.
- Demo output pivoted to ontology-engine pages with empty candidate slots.
- Neutral placeholder source IDs use `src:candidate:empty`.
- Active source of truth:
  - `HANDOFF.md`
  - `README.md`
  - `docs/data-strategy.md`
  - `docs/demo-runbook.md`
  - `ontology.md`

## 2026-07-04 — Historical Work Redacted

Earlier work explored live-feed and Foundry transition boundaries. Those details
are superseded. Keep only the durable architecture lesson:

```text
candidate signal
  -> Identity via of
  -> target Domain via targets
  -> Supplier.subcontractsTo*
  -> Prime.runs Program
  -> RiskAssessment / CompromiseIncident / ProgramExposure
  -> NotificationDraft.cites
```

Do not use historical changelog entries to rebuild live integration.

## 2026-07-05 — Workflow Action Types Added To Foundry (branch, pending merge)

The Foundry ontology previously had only auto-generated CRUD actions. Eight
semantic workflow actions were created via Palantir MCP on global branch
`workflow-actions`, proposal pending owner approval in the Foundry UI:

- CompromiseIncident: `acknowledge-incident`, `assign-incident`,
  `close-incident` (flagged -> acknowledged -> assigned ->
  closed_remediated | closed_false_positive)
- NotificationDraft: `review-notification-draft`,
  `approve-notification-draft`, `export-notification-draft`
  (draft -> reviewed -> approved -> exported; deliberately no `sent` state)
- MergeProposal: `confirm-entity-merge`, `reject-entity-merge`
  (proposed -> accepted | rejected; merges never automatic)

Design constraints honored:

- Existing properties only (`status`, `reviewer`); no object type changes,
  so current OSDK readback and demo remain stable.
- Actor identity/timestamp accountability comes from the Foundry action
  audit log (platform-enforced), not custom fields.
- State values are controlled vocabulary documented in each action
  description; Foundry UI submission criteria can tighten transitions later.

After merge: publish a new OSDK version including the eight actions, then
drive acknowledge -> export on seed objects for the live demo path.

## 2026-07-05 — Seed Guarantees Confirmed/Added + Program-Reverse-Query Surface

Audited the synthetic mock corpus against the three seed guarantees the demo
narrative depends on, then added the missing structural piece and a new
reverse-direction query script. All data remains synthetic (`*.example`).

- **3+ tier chain** — already complete, no change: `sup-h` (tier-2, Hotel
  Microelectronics) `subcontractsTo` -> `sup-f` (tier-1, Foxtrot Metals)
  `supplies` -> `prime-x` (Xenon Aerospace) `runs` -> `prog-sentinel` /
  `prog-harbor`.
- **Cross-org `targets` record** — the raw fact already existed
  (`cds-micro-h.example-active`, identity `ops@micro-h.example` on
  `micro-h.example`, `host=vpn.prime-x.example`) in `adapter/mock.py` and in
  the Foundry seed CSVs, but the LOCAL SQLite store had no concept of a
  Prime-owned target Domain to make it structurally queryable. Added, additive
  only:
  - `prime_domain` table (`store/sqlite.py`) + `upsert_prime_domain` /
    `prime_owned_domains`.
  - `target_domain_ref` / `target_prime_ref` / `cross_org_target` columns on
    the exposure read-back (`_EXP_SELECT`, left-joined on `prime_domain`).
  - `prime_domains:` registry section (`registry/suppliers.yaml`,
    `registry/loader.py`) seeding `vpn.prime-x.example -> prime-x`.
  - No existing link/API name changed; `target_domain_ref` already matched
    the field name the Foundry-backed store and its tests expect.
- **Dominance pair** — added `sup-i` (India Fabrication, `supplier-i.example`)
  as the noisy counterpart to `sup-h`'s quiet-but-active case: 40 stale,
  re-circulated Band-C records (`adapter/mock.py _gen_flood`, mirrored in
  `registry/suppliers.yaml`) and no active-compromise path. `actions/scoring.py`'s
  hard `base_cap=60.0` clamp for non-active suppliers keeps `sup-i` at
  score 55.42 (주의), strictly below every active supplier's floor of 70 —
  verified via `scripts/p3_rank.py` (`active-on-top: True`, min active
  95.76 > max non-active 56.97). No scoring code changed.
- Corpus grew from 8 suppliers/30 records to 9 suppliers/74 records;
  `eval/ground_truth.yaml` and `scripts/p6_eval.py`'s `MOCK_LIMITATION` text
  updated to match (hand-authored, not reverse-engineered from pipeline
  output). `uv run pytest -q` stays green (112 passed).

New reverse-query surface: **`scripts/program_threat_view.py`**. PropagateRisk
(P3) walks the graph forward, Supplier -> Prime -> Program. This script asks
the SAME ontology in reverse, starting from a Program: which
Suppliers/Primes feed it (reverse-walking `subcontractsTo*` -> `supplies` ->
`runs`, variable depth, depth shown per row) -> which of those carry an open
`CompromiseIncident` / `RiskAssessment` right now, plus any cross-org
`targets` hit against an asset owned by a Prime running the program. Two
backends, mirroring `scripts/foundry_blast_radius.py` / `scripts/demo_e2e.py`:
local SQLite (always works offline, runs the full mock pipe in-process) and
Foundry OSDK read-back (skips gracefully — prints a clear message and exits
0 — if `FOUNDRY_OSDK_MODULE`/`FOUNDRY_OSDK_CLIENT` are not configured). Since
the Foundry-backed store does not carry `target_prime_ref`, its cross-org
detection falls back to an `domain_ref != target_domain_ref` heuristic
scoped to suppliers already confirmed in the contributing chain, labelled
`precision: heuristic` in the output (vs. `exact` on the local backend).
Output: CLI table, `out/program_threat_view.json`, and a self-contained
dark-themed `out/program_threat_view.html` (CSS variables lifted from
`out/palantir_v1.html`) carrying the caption "같은 온톨로지, 반대 방향 질의 —
협력사 관점과 프로그램 관점이 동일 그래프에서 나온다."
