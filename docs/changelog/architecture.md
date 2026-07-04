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
