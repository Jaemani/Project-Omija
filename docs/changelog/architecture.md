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

## 2026-07-03 — P2: 엔티티 해소 + 전파 경로 질의
한 사람의 여러 신원 변형을 하나로 병합(제안→사람 확인)하고, 활성침해 탐지가 쓸 다중홉 경로 질의를 스토어에 추가. 온톨로지 스멜테스트 (2)엔티티 해소·(1)다중홉 질의를 실제 코드로 충족.
- **파생 객체 추가**: `MergeProposal`(id·후보쌍·basis·status=pending) — 온톨로지 §0 (2)엔티티 해소를 상태 있는 제안 객체로 못박음. `merge_proposal` 테이블(신원 컬럼은 **FK 없는 이력 참조** — confirm 시 변형 신원 행 삭제해도 감사 레코드 보존).
- **액션 추가**: `EntityResolver`(`actions/entity_resolver.py`) — **룰 기반**(LLM 없음, 데모 결정성; 의미 병합은 AIP Logic 담당). email local-part 정규화(소문자·`+tag` 제거·점 제거: `J.Kim+ci@`→`jkim`) 후 **같은 도메인 내** 동일 핸들 충돌 쌍을 MergeProposal로 기록. **자동 확정 금지**(human-on-the-loop): `confirm_merge()` 호출 시에만 `merge_identities`가 Exposure/Device/match 링크를 병합·변형 신원 삭제, 전 Exposure(provenance) 보존.
- **중복 제거 규칙**(decision 3): 같은 `(identity, host, secret_type)`가 여러 모듈에 걸치면(재유통 콤보) **노출 규모 카운트는 1**(`dedup_exposures`). provenance는 전 레코드 보존, 소스 다양성(모듈 수)은 **신뢰도 가산 신호**로 사용. `exposures_for_supplier`에 `identity_ref` 컬럼 추가(dedup 키).
- **다중홉 질의 추가**: `store.infected_device_paths()` — Device→Identity→Domain→Supplier 좌반부(활성침해 경로). Supplier→Prime→Program 우반부는 기존 `propagation_for_supplier`와 결합해 full path(Device→…→Program) 구성(P3 FlagActiveCompromise가 사용).
- **목 확장**(재현성): 엔티티 해소 시연용 변형쌍 `j.kim@`/`jkim@`(supplier-c, 서로 다른 host/type=신원병합 케이스) + dedup 시연용 재유통쌍(parts-d: ub 자격증명을 cb가 동일 identity·host·plaintext로 재포함). seed 결정성 유지, 레코드 22→25. **기존 테스트 42개 무회귀**(모두 관계형/부분문자열 단언이라 카운트 하드코딩 없음 — 갱신 불필요).
- **검증**: EntityResolver가 변형쌍 정확히 1건 제안(pending), confirm 후 신원 -1·Exposure 보존, dedup가 parts-d 5→4 카운트. Protocol(`store/base.py`)에 신규 메서드 선언(hot-swap 계약 유지).

## 2026-07-03 — P3: 활성침해 가중 스코어링 + 경로 존재 탐지 (핵심 차별점)
"유출 나열"이 아니라 "지금 뚫리는 중"을 순위 상단으로 강제. 활성침해를 **그래프 경로 존재**로 탐지하고, 스코어에 지배적 가중을 부여.
- **파생 객체 추가**: `RiskAssessment`(supplier_ref·score·grade·active_flag·computed_at·**components 기여분 JSON**·evidenced_by[]) + `CompromiseIncident`(supplier_ref·opened_at·status=open·**path[] traverses**). `risk_assessment`·`risk_evidence`·`compromise_incident` 테이블.
- **스코어링 설정 한 곳**(`actions/scoring.py`, decision 5): 가중치·임계값 투명 config(`SCORING` dict). 공식(architecture.md §3 준수): base = Σ(노출 규모[dedup] + 최근성 decay(반감기) + 비밀유형 가중[cookie/token/plaintext↑ > hash] + 모듈 신뢰도·소스 다양성) → criticality·tier 곱 → **[0,base_cap] 클램프**. **활성침해 성립 시 활성 밴드 [active_floor..100]로 상향** = 비활성(≤base_cap)보다 **구조적으로 항상 상단**(핵심 차별점 보장). 밴드 내부는 base 품질+기기 최근성으로 서열. 각 기여분 `components`에 저장(설명가능성). grade: 즉시(≥70)/주의(≥40)/관찰.
- **액션 추가**:
  - `ComputeRisk`(`actions/compute_risk.py`): RiskAssessment 생성. **evidenced_by 비면 액션 거부**(`EvidenceRequired` 예외) — provenance 강제(ontology.md §3). 활성 여부는 추측 없이 **CompromiseIncident 존재**로 판정. clean 업체는 근거 없어 미평가.
  - `FlagActiveCompromise`(`actions/flag_active.py`): 경로 성립 조건 = InfectedDevice(infected_at ≤14일) AND has_session_cookie AND account_type∈{vpn,admin} AND Device→Identity→Domain→Supplier 경로 AND Supplier→Prime→Program 연결. 성립 시 CompromiseIncident(full path traverses) 생성, **경로 미완성 시 거부**. 활성 판정은 정의된 필드·경로로만(추측 금지).
- **순위 스크립트**(`scripts/p3_rank.py`): 전체 파이프(mock→normalize→correlate→**resolve**→**flag**→**score**) → 순위 테이블(Supplier·score·grade·활성·최근 신호·evidence 수) + Incident 경로(Device→…→Program 텍스트 체인) + 상위 업체 기여분. RESULT가 "활성 업체 전부 비활성보다 상단" 불변식 검증.
- **검증**: 순위 상위 2 = 활성 업체(sup-a 96.67·sup-g 95.76, 즉시), 비활성 최고 56.97 → **활성-on-top 보장 성립**. Incident 정확히 2건(활성 도메인만, 각 6홉 full path). evidence 없는 ComputeRisk 거부, traverses 없는 Incident 거부, dedup 카운트, grade 임계값 모두 테스트. pytest **61/61 통과**(기존 42 + entity_resolver 6 + scoring 5 + flag_active 3 + compute_risk 4 + p3_rank 1). 원문 비밀 유출 0.
- 이유·설계원칙: 스코어링 가중 근거는 ADR-0005(활성침해 지배·dedup·decay). 새 파생 객체 3종은 스멜테스트 (3)액션 상태전이·(4)provenance 그래프를 코드로 충족(RiskAssessment→evidenced_by, CompromiseIncident→traverses). 기존 SQLite 검증 스토어(ADR-0003) 위 스키마 확장 — day-1 AIP Logic으로 hot-swap.

## 2026-07-03 — P5 조치 권고 + 통보 초안(발송 없음)
- **객체 추가**: `NotificationDraft`(supplier_ref·body·status=draft·created_at) + `draft_cites`(NotificationDraft **cites**→Exposure/Device) 테이블 신설(ontology.md §1 baseline 반영). `store/base.py` Protocol에 선언(hot-swap 계약 유지).
- **GenerateNotificationDraft 액션**(`actions/notify_draft.py`, ontology.md §5): **결정적 템플릿 기반**(LLM 호출 없음 — AIP Logic 단계 몫, 데모 재현성). 대상 = 순위 상위(활성 상단이므로 활성침해 업체 포함, top 3). 본문(한국어, 방산 협력사 보안담당 수신 가정): (a) 탐지 요약(관측됨) (b) 활성이면 경로 요약(감염기기→계정→귀사→원청 프로그램) (c) 방어 조치 권고(비밀번호 리셋·세션/쿠키 폐기·MFA·계정 격리·감염기기 재이미징·VPN 세션 감사) (d) 근거 목록(source_ref 인용) (e) 하단 고지("분석가 검토·승인 전 발송 금지"). "관측됨/추정됨" 구분, 과장·단정 금지. **cites(evidence_refs) 비면 액션 거부**(`CitationRequired`). status는 항상 `draft` — **코드베이스에 발송 경로 없음**(smtp/send 스모크 테스트로 강제).
- **스크립트**(`scripts/p5_drafts.py`): 파이프 실행 → 상위 3업체 초안 생성 → `out/drafts/<supplier_id>.md` 저장 + CLI 요약. 비밀 마스킹·발송 없음 불변식 RESULT 체크.
- **검증**: 신규 테스트 10 — cites 없는 초안 거부, 초안·대시보드 HTML 원문 비밀 부재, 활성 업체 초안에 경로·격리 권고 포함, 대시보드 활성 상단·그래프·드릴다운·필터, 발송 기능 부재 스모크. pytest **71/71 통과**(기존 61 무회귀). 파생 객체 NotificationDraft는 스멜테스트 (4)provenance(cites)를 코드로 충족 — day-1 AIP agent로 hot-swap.
