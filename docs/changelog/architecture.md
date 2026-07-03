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

## 2026-07-03 — P1: 수직관통 (레지스트리 → 상관 → 리포트)
업체 1개가 아니라 레지스트리 전체에 대해 목 조회→정규화→**CorrelateExposure**→온톨로지 write→화면까지 한 줄로 관통.
- **객체 추가**: `Prime`(id,name) · `Program`(id,name,sensitivity) 테이블 신설(ontology.md §1). 기존 Supplier·Domain·Identity·CredentialExposure·InfectedDevice·ThreatSource에 상단(전파 최상단) 접합.
- **링크 추가**: `supplies`(Supplier→Prime, N:M) · `runs`(Prime→Program, N:M) 링크 테이블(온톨로지 링크명 보존). 위험이 협력사→원청→프로그램으로 **상향 전파**할 경로 구성(ontology.md §2). `store.propagation_for_supplier`로 Supplier→Prime→Program traverse 읽기.
- **레지스트리**(`registry/suppliers.yaml` + `loader.py`, pyyaml): 합성 업체 7개(mock SEED_SUPPLIERS와 id·도메인 1:1, 활성 2·clean 2 포함) + Prime 2 + Program 2 + supplies/runs. criticality는 P1 결정대로 numeric 1..3(mock의 문자열 라벨과 병존—같은 업체 기술). 로더가 스토어에 적재.
- **CorrelateExposure 액션**(`actions/correlate.py`, ontology.md §3): Exposure의 identity.email 도메인 ↔ 등록 도메인 매칭 → `Identity belongs_to Domain` 확정. 서브도메인은 등록 부모로 해소(`mail.supplier-a.example`→`supplier-a.example`, 최장 부모 우선). 매칭 근거(`match_basis`)를 `exposure_match` 테이블에 provenance로 기록—근거 없는 귀속 금지(CLAUDE.md §5). 미매칭 Exposure는 미귀속으로 남기고 개수 보고. 스코어링·발송 없음(순수 귀속).
- **화면**(`scripts/p1_report.py` → `out/p1_report.html`, gitignore): 업체별 노출 리스트(module·ThreatSource·source host·fetched_at·**마스킹** 비밀·source_ref) + Supplier→Prime→Program 전파 경로 + **활성 신호(최근 infected_at+cookie+vpn/admin) 상단 강조**. CLI 요약. 원문 비밀 렌더 0(정규식 스윕 가드).
- **검증**: registry→normalize→correlate→screen 22 레코드 전량 매칭(5개 업체, 활성 2, unmatched 0), 원문 비밀 유출 0. pytest 42/42 통과(기존 23 + registry 5 + correlate 9 + report 5).
- 이유: 얇게라도 끝단(화면)까지 관통해 온톨로지 경유 귀속·전파·활성 트리아지를 한 번에 시연하고, 이후 P2(엔티티 해소·전파 확장)·P3(스코어링) 확장점을 확정. 새 구조 결정(ADR)은 없음—기존 SQLite 검증 스토어(ADR-0003) 위 스키마 확장.
