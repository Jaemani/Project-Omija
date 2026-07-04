# 2026-07-04 — Foundry Ontology Seed / Explorer Verification

Foundry Ontology Manager에서 foundation, intel/evidence, derived decision object backing datasources와 핵심 link types를 seed CSV로 검증했다. Object Explorer에서 원천 경로와 파생 판단 경로를 traversal할 수 있음을 확인했다.

## Implemented Notes

- `MergeProposal`, `RiskAssessment`, `CompromiseIncident`, `ProgramExposure`, `NotificationDraft`에 `status` string property를 추가했다.
- 상태값은 별도 Foundry enum/status base type이 아니라 controlled vocabulary로 운영한다.
- `owns`, `prime_owns`, `belongs_to`, `of`, `targets`, `sourced_from`, `leaked`, `merge_candidates`는 현재 Foundry에서 foreign-key link로 구현했다.
- `merge_candidates`는 foreign-key link이므로 별도 seed CSV를 쓰지 않는다.
- `subcontracts_to`, `supplies`, `runs` 및 파생 판단 provenance 링크는 join-table datasource로 테스트한다.
- Foundry Link Type은 concrete From/To pair이므로 conceptual union link는 target type별로 나눴다. 예: `evidenced_by`는 `RiskAssessment -> CredentialExposure`, `RiskAssessment -> InfectedDevice`, `RiskAssessment -> CompromiseIncident`로 분리한다.
- `cites`, `program_evidenced_by`도 같은 concrete-pair 방식으로 분리한다.
- `PathEvidence` 객체는 만들지 않고 `path_snapshot`, `path_hash`, `traverses_*` 링크로 충분하다는 v0.2 결정을 유지한다.
- CSV/backing datasource에서 채우는 속성은 datasource-backed property여야 한다. `edit-only` property는 Object Explorer에서 seed 값이 비어 보인다.

## Next

1. Foundry에서 `FlagActiveCompromise`, `ComputeSupplierRisk`, `GenerateNotificationDraft` custom Action Type을 만든다.
2. 각 Action은 이미 seed로 검증한 decision object와 provenance link를 생성하도록 설계한다.
3. Action 생성 후 Object Explorer에서 `CompromiseIncident -> RiskAssessment -> NotificationDraft` 흐름을 재확인한다.
