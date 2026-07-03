# architecture.md — 온톨로지·아키텍처 변경로그

온톨로지·아키텍처 변경(Object/Link/Action 추가·수정, 스코어링 로직 변경 등) 시 날짜·변경·이유 1줄씩 추가한다. 스펙 문서(`docs/spec/`) 수정과 동시에 기록.

---

## 2026-07-03 — 온톨로지 v0.1 (baseline)
`docs/spec/ontology.md` 기준으로 baseline 온톨로지 확정.
- **객체 11종**: Supplier · Prime · Program · Domain · Identity · CredentialExposure · InfectedDevice · ThreatSource · RiskAssessment · CompromiseIncident · NotificationDraft.
- **링크 11종**: Supplier-supplies→Prime · Prime-runs→Program · Supplier-owns→Domain · Identity-belongs_to→Domain · CredentialExposure-of→Identity · CredentialExposure-sourced_from→ThreatSource · InfectedDevice-leaked→CredentialExposure · InfectedDevice-compromises→Identity · RiskAssessment-evidenced_by→Exposure/Device · CompromiseIncident-traverses→[Device,Identity,Supplier,Prime] · NotificationDraft-cites→Exposure/Device.
- **액션 5종**: CorrelateExposure · ComputeRisk · FlagActiveCompromise · GenerateNotificationDraft · AcknowledgeAlert/AssignAnalyst.
- **규칙**: evidence/cites/traverses 링크 없는 파생 객체(RiskAssessment, CompromiseIncident, NotificationDraft)는 Action 생성이 거부됨 — provenance·경로 강제를 온톨로지 레벨에 못박음.
- 근거: 스멜테스트(다중홉 질의·엔티티 해소·액션 상태전이·provenance 그래프) 4/4 통과(`docs/spec/ontology.md` §0).
