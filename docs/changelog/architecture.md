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

## 2026-07-03 — P0-A: 어댑터 계약 + 목 + 로컬 검증 스토어
StealthMole 실접근 없이(내일 열림) 어댑터 계약·목·로컬 파이프를 완성해 왕복 검증.
- **어댑터 계약**(`adapter/`): `ExposureSource` Protocol(quotas/search) + 공통 `normalize(module, raw) → Exposure`(data-sources.md §5 스키마). 실(`stealthmole.py`)·목(`mock.py`)이 동일 인터페이스 → day-1 hot-swap. stealthmole은 §1 검증 계약(JWT HS256, /user/quotas, /{module}/search·export, start 증분)으로 구현하되 **P0-A에서 네트워크 호출 없음**(day-1 P0-B 연결). [확인필요] cds device 필드·추가 모듈은 주석 표시.
- **마스킹 경계**: `normalize()`에서 원문 비밀 제거 — masked_value(앞 2자+`***`)만 저장, 어떤 필드·로그에도 원문 부재. 활성침해 필드(device.infected_at·has_session_cookie·account_type) 보존. confidence cds/ub=0.9·cl=0.6·cb=0.3.
- **목 데이터**: 결정적(seed 고정) 합성 도메인 7개(2개 clean), 4모듈 전부, **활성침해 케이스 필수**(최근 infected_at + has_cookie + vpn/admin + RedLine). 동일 계정을 cds+ub, cl+cb에 걸쳐 재사용 → 엔티티 해소 시연.
- **로컬 검증 스토어**(`store/`): 온톨로지 동일 스키마(Supplier·Domain·Identity·CredentialExposure·InfectedDevice·ThreatSource + FK 링크)를 SQLite로 구현. `OntologyStore` Protocol 뒤에 두어 Foundry/OSDK 구현으로 hot-swap. **AIP=spine 불변, 이건 검증·보험**(ADR-0003).
- **파이프 검증**: `scripts/p0_pipe.py` 목→normalize→SQLite write→read-back 왕복 성공(22 레코드, 활성신호 2, 원문 비밀 유출 0). pytest 23/23 통과.
- 이유: Foundry 온톨로지 생성·OSDK 발행이 콘솔 수동 단계라 코드 파이프 검증을 블로킹하지 않도록 동일 스키마 로컬 스토어를 둠(ADR-0003). OSDK 호환 위해 Python 3.12 고정(ADR-0004).
