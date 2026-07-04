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
