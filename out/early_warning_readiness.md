# Early Warning Readiness

Generated: `2026-07-04T21:20:51.742843+00:00`

Ready: `True`

## Summary

- Checks: `10/10`
- Suppliers: `9`
- Query seeds: `118`
- Asset surface seeds: `81`
- Eval records: `74`
- Active suppliers in synthetic eval: `sup-a, sup-g, sup-h`

## Checks

- [x] `collection_plan_non_executing` — Every private/context query seed and public job has execute=false.
- [x] `domain_exact_coverage` — 9 supplier-domain exact query seeds expected.
- [x] `email_domain_coverage` — 9 email-domain query seeds expected.
- [x] `asset_surface_coverage` — 81 access-host query seeds expected.
- [x] `ontology_targets_present` — Every query seed names at least one ontology landing target.
- [x] `secret_storage_forbidden` — Raw password/cookie/token storage is forbidden for every private/context seed.
- [x] `regional_context_not_evidence` — Country/keyword monitoring lands only as ThreatSource context.
- [x] `engine_eval_pass` — Current synthetic engine evaluation reports pass=true.
- [x] `active_on_top_invariant` — Active compromise candidates rank strictly above non-active suppliers.
- [x] `active_detection_clean` — Synthetic active-compromise evaluation has no false positives or false negatives.

## Limitations

- Evaluation uses a synthetic clean mock corpus; it proves wiring, not field precision.
- Private feed query seeds are not executed by this check.
- Live compromise confirmation still requires VPN/SSO/IAM/EDR or supplier response evidence.
