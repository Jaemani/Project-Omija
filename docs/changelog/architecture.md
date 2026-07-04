# architecture.md — 온톨로지·아키텍처 변경로그

Current status as of 2026-07-05: live credential-feed work is neutralized and
must not be resumed from this historical changelog. Use `HANDOFF.md`,
`docs/data-strategy.md`, and `docs/demo-runbook.md` for the active no-live-data
ontology-engine direction.

온톨로지·아키텍처 변경(Object/Link/Action 추가·수정, 스코어링 로직 변경 등) 시 날짜·변경·이유 1줄씩 추가한다. 스펙 문서(`docs/spec/`) 수정과 동시에 기록.

---

## 2026-07-04 — P0-C StealthMole live end-to-end entrypoint
- `scripts/p0c_live_pipeline.py`: 인가된 registry/domain을 명시해야만 CDS/CL/CB 첫 페이지를 조회하고 `normalize → correlate → merge proposal → active incident → supplier risk → program propagation → notification draft`를 로컬 SQLite에서 실행한다. `--authorized` 확인, registry membership, 예약/합성 도메인 거부, DT/UB 및 미지원 모듈 거부, quota 선확인을 강제한다.
- `adapter/base.py`: live 플랜별 필드 차이를 위해 identity/secret/host/timestamp/malware 별칭을 보수적으로 정규화한다. URL·username으로 privilege를 추측하지 않으며, raw password/cookie는 기존과 같이 masking boundary 밖으로 나가지 않는다.
- live registry template와 `.env.example` 설정을 추가했다. 실제 registry는 `registry/suppliers.live.yaml`로 gitignore하며, 결과 DB/요약은 기존 gitignored `out/live/`에 저장한다.
- 데이터 후보를 현재 객체에 직접 맞는 CDS/CL/CB와 별도 객체가 필요한 CDF/TT/RM/GM/LM으로 분리했다. Foundry/OSDK 구현은 별도 담당 범위라 변경하지 않았다.
- 검증: 관련 20 tests, 전체 110 tests 통과. live fake record가 Exposure→Incident→RiskAssessment→ProgramExposure→NotificationDraft까지 도달하고 raw password/cookie가 DB·초안에 남지 않음을 고정했다.

## 2026-07-04 — P0-B hackathon live API verified
- 해커톤 전용 Base URL로 교정한 후 `/user/quotas` JWT 인증과 `/cds/search` 합성 도메인 조회가 200으로 성공했다. 운영 API URL에서의 기존 401은 키 결함이 아니라 endpoint 불일치였다.
- 해커톤 미제공 DT/UB를 기본 정찰에서 제외하고 CDS 1회만 기본으로 제한했다. quotas는 `allowed-used`로 잔량을 계산하고 실응답 `totalCount/cursor/limit/queryCost`를 스키마 증거에 보존한다.
- 실행 산출물: `out/p0b/quotas.json`, `out/p0b/schema_cds.json`. 합성 도메인은 0건이므로 CDS 레코드 필드 매핑은 자기 도메인 결과가 생기면 후속 검증한다. 비밀값·JWT·원문 자격증명 저장은 0건이다.
- 검증: 관련 10 tests, 전체 107 tests 통과.

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

## 2026-07-03 — P4 순위 대시보드 + 전파 그래프 뷰
- **화면(`scripts/p4_dashboard.py` → `out/dashboard.html`)**: 전체 파이프 실행 후 **자기완결 정적 HTML 1파일** 생성. 외부 CDN·네트워크 의존 0(오프라인 데모 안전 — 해커톤 백업). 바닐라 JS + inline CSS/SVG. *구조 결정 아님(ADR 불요)이나 자기완결 HTML 선택 이유는 이 1줄로 기록: 심사장 네트워크·CDN 불확실성 하에 재현성 확보.*
- **구성(architecture.md §6)**: (1) 순위 테이블 — Supplier·score·grade(즉시/주의/관찰 색상)·활성 플래그·최근 신호 시각·evidence 수, **활성 상단 고정**(`data-active` 정렬 불변식). (2) 드릴다운 — 행 클릭 시 Exposure/Device 상세(module·host·마스킹 비밀·ThreatSource·source_ref·fetched_at) + 점수 기여분(components) + leak/infected 타임라인 + **P5 통보 초안 미리보기**(P4↔P5 연결). (3) **전파 그래프 뷰** — Incident 경로 Device→Identity→Domain→Supplier→Prime→Program를 SVG 노드-엣지로, 활성 경로 빨강 하이라이트; 비활성/clean 업체는 Supplier→Prime→Program 골격(Prime·Program 노드는 공유·dedup되어 다수 협력사→동일 원청 수렴 시각화). (4) 필터 tier/활성만/grade.
- 헤더에 "모의 데이터(합성 도메인) · 방어적 조기경보 데모 · 비밀 마스킹 · 자동 발송 없음" 명시. 원문 비밀 렌더 0(마스킹 스윕 테스트). 테스트 +4: 대시보드 원문 비밀 부재·활성 상단·그래프/드릴다운/필터 존재·자기완결(외부 리소스 참조 0)·p4 스모크. pytest 71/71.

## 2026-07-03 — P5 조치 권고 + 통보 초안(발송 없음)
- **객체 추가**: `NotificationDraft`(supplier_ref·body·status=draft·created_at) + `draft_cites`(NotificationDraft **cites**→Exposure/Device) 테이블 신설(ontology.md §1 baseline 반영). `store/base.py` Protocol에 선언(hot-swap 계약 유지).
- **GenerateNotificationDraft 액션**(`actions/notify_draft.py`, ontology.md §5): **결정적 템플릿 기반**(LLM 호출 없음 — AIP Logic 단계 몫, 데모 재현성). 대상 = 순위 상위(활성 상단이므로 활성침해 업체 포함, top 3). 본문(한국어, 방산 협력사 보안담당 수신 가정): (a) 탐지 요약(관측됨) (b) 활성이면 경로 요약(감염기기→계정→귀사→원청 프로그램) (c) 방어 조치 권고(비밀번호 리셋·세션/쿠키 폐기·MFA·계정 격리·감염기기 재이미징·VPN 세션 감사) (d) 근거 목록(source_ref 인용) (e) 하단 고지("분석가 검토·승인 전 발송 금지"). "관측됨/추정됨" 구분, 과장·단정 금지. **cites(evidence_refs) 비면 액션 거부**(`CitationRequired`). status는 항상 `draft` — **코드베이스에 발송 경로 없음**(smtp/send 스모크 테스트로 강제).
- **스크립트**(`scripts/p5_drafts.py`): 파이프 실행 → 상위 3업체 초안 생성 → `out/drafts/<supplier_id>.md` 저장 + CLI 요약. 비밀 마스킹·발송 없음 불변식 RESULT 체크.
- **검증**: 신규 테스트 10 — cites 없는 초안 거부, 초안·대시보드 HTML 원문 비밀 부재, 활성 업체 초안에 경로·격리 권고 포함, 대시보드 활성 상단·그래프·드릴다운·필터, 발송 기능 부재 스모크. pytest **71/71 통과**(기존 61 무회귀). 파생 객체 NotificationDraft는 스멜테스트 (4)provenance(cites)를 코드로 충족 — day-1 AIP agent로 hot-swap.

## 2026-07-03 — P6 평가 + 데모·피칭 패키징
- **Ground truth(핸드-작성)**: `eval/ground_truth.yaml` 신설 — 활성 업체(sup-a·sup-g)·clean(sup-e·sup-f)·비활성 노출(sup-b/c/d) 분류 + exposure→업체 귀속 정답(25개 source_ref, 도메인 기준). **mock 상수(adapter/mock.py·registry)에서 손으로 도출**(파이프 출력 역산 금지 — 순환 차단). 각 블록에 근거 상수 주석. 목의 합성·소규모·클린 한계를 파일·평가 출력에 명시.
- **평가 스크립트**(`scripts/p6_eval.py`): 전체 파이프 실행 후 ground truth 대비 결정적 지표 산출 — (1) **상관 precision/recall**(exposure→supplier 귀속) (2) **활성침해 탐지 precision/recall**(FlagActiveCompromise vs 정답, FP/FN 명시) (3) **순위 유효성**(활성이 전부 비활성보다 상위 = top-k 정합) (4) **골든타임**(맨몸 레코드 나열 vs 그래프 트리아지, 검토항목수→분 환산). 출력: CLI 표 + `out/eval.json`. 순수 지표 함수(prf_from_sets·attribution_metrics·ranking_validity·golden_time)로 분리해 단위테스트.
- **실측 결과**(anchor DEMO_NOW=2026-07-03): 상관 **P/R 100%/100%**(25/25 정확 귀속·오귀속 0), 활성침해 탐지 **P/R 100%/100%**(TP 2·**FP 0·FN 0**), 순위 top-2 = [sup-a, sup-g](최소 활성 95.76 > 최대 비활성 56.97), 골든타임 맨몸 25레코드·75분 → 우리 5업체·15분(검토단위 -80%)·활성 2곳 도달 6분(**-92%**, 3분/건 가정). *정직 고지: 이 코퍼스는 활성 감염이 최신 레코드라 최신순 정렬 first-contact도 2위 — 그러나 맨몸엔 활성 플래그가 없어 정지 판단 불가; 이점은 사전계산·근거첨부·상단고정+dedup이지 최신순 트릭 아님.* 숫자 과장·조작 없음(계산되는 대로).
- **데모**: `docs/demo.md` — 3분 대본(문제 30s·해자 60s·라이브 90s·숫자·배치경로) + 실행 순서 명령어 + 리허설 체크리스트 + 오프라인 백업(정적 HTML·eval.json) + 심사 4항목 매핑. `README.md` 최종 정리(현재 상태 P0-A~P6·P0-B day-1 대기, 퀵스타트, 아키텍처 요약, 문서 지도).
- **검증**: 신규 테스트 13 — 지표 수식 단위테스트(작은 합성 케이스로 P/R·FP/FN·귀속·순위·골든타임 검증), ground truth 파일 없으면 eval 실패(FileNotFoundError, 무증거 통과 차단), 전체 eval green·기대 상한 도달, eval.json 원문 비밀 부재. pytest **84/84 통과**(기존 71 무회귀).

## 2026-07-04 — 온톨로지 v0.2: 멀티티어 전파 + ProgramExposure 롤업 + blast-radius (ADR-0006)
그래프가 **귀속에만** 쓰이고 전파에 안 쓰이던 구멍(멀티티어 없음·위험 전파 없음·blast 폐기)을 메움. 문서(ontology.md §2 간판)가 코드보다 깊던 상태를 코드로 따라잡음. 상세·근거 ADR-0006.
- **링크 추가**: `Supplier —subcontracts_to→ Supplier`(N:M, `subcontracts` 테이블) — 하위(2차)→상위(1차) 납품. **멀티티어 위험 전파** 엣지. 2차 말단이 직결 `supplies` 없이 subcontracts만으로 상위 Prime/Program에 **가변깊이**로 도달.
- **가변깊이 재귀 traverse**(`store.propagation_paths`, SQLite `WITH RECURSIVE`): Supplier에서 subcontracts 상향 재귀 → supplies→runs로 Supplier…→Prime→Program **가변길이 경로** 조립. **사이클 안전 = depth cap(6) + 방문경로 문자열 검사(`instr`) 병용**(cap 단독은 조합 폭발 가능). 이것이 flat table 불가능성의 증명(ontology.md §2 깊이 질의 갱신).
- **파생 객체 추가**: `ProgramExposure`(program_ref·score·grade·active_flag·components·contributing_paths[]·evidenced_by[]) + `program_exposure`/`program_exposure_evidence` 테이블. **PropagateRisk 액션**(`actions/propagate_risk.py`): 각 Program에 닿는 모든 협력사 경로를 롤업 — score = 지배 경로(최고 협력사 score) + breadth(distinct 활성 협력사, **Supplier 기준 dedup**) × sensitivity. 활성 Program은 밴드 `[70..100]`, 비활성 `[0..60]` → **활성 Program 항상 상단**(ADR-0005 밴드 분리 재사용). **evidenced_by 비면 생성 거부**(도달 노출 0인 Program은 ProgramExposure 없음). 다이아몬드 공급망은 distinct Supplier/underlying ref 기준 dedup(경로 수로 부풀림·공유 Prime/Identity 이중계산 금지). 경유 Prime/tier-1은 **별도 파생객체 없이** components 소계 + Incident path로만(스멜테스트 §5 스코프 규율).
- **blast-radius 복원**: `FlagActiveCompromise`가 `prop[0]`만 쓰던 것 폐기 → CompromiseIncident에 `blast_radius{primes[],programs[]}` 저장. **device 레벨 집계**(device가 compromise한 = `leaked∘of` 유도된 모든 Supplier의 모든 도달 Prime/Program). belongs_to가 Identity→Domain N:1이라 크로스-업체 blast는 InfectedDevice→여러 Identity로만 성립 → 구조를 device 레벨로 정합화. `store.device_compromised_suppliers`(leaked∘of) 추가. path는 **가변길이**로(멀티티어 Supplier hop 포함).
- **정합성 핀**: (1) 크로스-업체 blast는 Device 레벨(Identity N:1이라 Identity 레벨 불가), (2) 롤업 breadth·evidence는 distinct Supplier/ref dedup, (3) compromises = leaked∘of 유도(ontology.md §2 명시).
- **레지스트리/목**: `registry/suppliers.yaml`에 2차 말단 `sup-h`(Hotel Microelectronics, micro-h.example — **직결 supplies 제거, subcontracts→sup-f(clean tier-1)만**) + `adapter/mock.py`에 그 말단의 활성침해 감염기기(RedLine·admin·cookie·최근). 데모 머니샷: 2차 말단 감염이 sup-h→sup-f→prime-x→prog-sentinel/harbor로 2홉 위 프로그램을 태움. 전부 합성 도메인. **레코드 25→30, 협력사 7→8**.
- **기존 테스트 파급(정직 처리)**: 활성 협력사 2→3(sup-h 추가)로 카운트 하드코딩 5개 갱신 — `test_flag_active`(incident 2→3·고정 6홉 path→가변길이 shape 검사), `test_compute_risk`(활성셋 +sup-h), `test_p6_eval`(top_k 리스트→집합 비교), `eval/ground_truth.yaml`(active_suppliers·exposure_attribution에 sup-h 5레코드 **손 재유도**, 파이프 역산 아님), `p6_eval.py` MOCK_LIMITATION 카운트. `test_p4_dashboard` 프로그램 롤업 섹션 단언 추가.
- **화면**(`scripts/p4_dashboard.py`): "프로그램 노출(전파 롤업)" 섹션 + burning KPI + 멀티티어 활성 경로 표시(머니샷). `scripts/p3_rank.py`에 PropagateRisk 단계·blast·프로그램 순위 출력 + RESULT에 "2차 말단→프로그램 burning" 불변식.
- **검증**: 신규 테스트 16(재귀 traverse·가변깊이·사이클/자기루프 종료·subcontracts-only 활성 incident+중간 hop·ProgramExposure provenance 거부·활성 밴드·diamond dedup·device 레벨 blast·멀티티어 burning·blast 전량 기록). pytest **106/106 통과**(기존 93 무회귀+갱신, 네트워크 0, 원문 비밀 유출 0). 재귀 예시 경로: `InfectedDevice → Identity(ops@micro-h.example) → Domain → Supplier(Hotel Microelectronics) → Supplier(Foxtrot Metals) → Prime(Xenon Aerospace) → Program(Harbor Sustainment)`.

## 2026-07-04 — P0-B day-1 준비: 정찰 스크립트 + Foundry 스토어 스켈레톤 + ComputeRisk 런북 상세화
실 StealthMole 접근·Foundry 이관 직전 준비. 코드 파이프는 P0-A~P6로 이미 검증됨 → 여기선 day-1에 사람이 실행할 라이브 접점과 hot-swap 대상을 얇게 붙임(온톨로지 스키마 변경 없음).
- **런북 ComputeRisk 상세화**(`docs/runbooks/foundry-day1.md` §3): 콘솔 수동 절차라 코드는 못 짜므로 정확한 클릭 경로+개념을 초보자용으로. Palantir 검증 문서(action-types/rules·parameter-overview·inline-edits·parameters-default-value·object-link-types/edit-properties·object-edits/how-edits-applied) 기준. 추가: Action Type=3요소(파라미터·edits·submission criteria) 개념, 선행조건(Supplier `last_scored_at` Timestamp 속성 먼저), 오늘 최소버전(supplier=Object ref required / evidence=Object set→Exposure optional 자리만 / Modify object로 last_scored_at←제출시각, special value 없으면 default=Current time 우회), inline edit 금지 이유, writeback 토글, **콘솔 최소↔로컬 최종(compute_risk.py) 대응표**, OSDK 왕복 read-back 스니펫, Compute Risk 전용 Morph 질문 4개. 오늘 증명=상태 전이(미채점→채점), RiskAssessment 생성·evidence 거부는 P3.
- **P0-B 정찰 스크립트**(`scripts/p0b_recon.py`): day-1 라이브 계약 실측(PROMPTS.md P0-B). **키 없으면 네트워크 0·소스 미생성·exit 0**(에러 아님). 순서: /user/quotas 먼저(인증+열린 모듈, 크레딧 절약) → 열린 모듈마다 합성/자기 도메인 1개로 /search 1회 → 레코드 **스키마(필드명·타입)만** 기록, cds device/malware/infected_at/cookie 필드 강조. **비밀 원문 절대 미출력·미저장**(마스킹, adapter.base.mask_secret 재사용). 결과 `out/p0b`(gitignore). [확인필요]→[검증됨] 갱신 후보 CLI 안내. 저자는 키 없이 코드만 작성(직접 실행 안 함).
- **Foundry 스토어 스켈레톤**(`store/foundry.py`): `OntologyStore` Protocol 구현 `FoundryOntologyStore` — 36개 메서드 전부 스텁(NotImplementedError + OSDK 호출형 주석: `client.ontology.objects.Supplier.get(...)`·`client.ontology.actions.compute_risk(...)` 등). **OSDK 패키지명 미정이라 모듈 상단 import 없음**(import 시 안 깨짐), 클라이언트는 생성자 지연 주입. SQLite와 동일 인터페이스 → **hot-swap 1줄 교체**(AIP=spine, SQLite=검증/보험, 이 클래스가 실 이관 대상; ADR-0003). day-1에 메서드 본문 채움.
- **테스트 +9**: `test_p0b_recon.py`(키 없을 때 exit 0·소스 미생성으로 네트워크 0 검증, 안내 출력, 마스킹 함수 원문 비밀 미노출, 스키마 수집이 raw secret 미포함) + `test_foundry_store.py`(OSDK 없이 import·생성, OntologyStore Protocol 구조 충족=hot-swap 계약, read/write/action 메서드 NotImplementedError). 기존 84 무회귀 → **93/93**.
- 이유: 코드 파이프는 이미 완성(P0-A~P6)이라, day-1에 필요한 건 (1) 사람이 따라올 콘솔 런북 (2) 실 API 정찰 도구 (3) hot-swap 대상 스토어뿐. 셋 다 온톨로지 스키마 변경 없이 얇게 붙임. 실 접근·Foundry 이관 시 이 3개만 hot-swap.

## 2026-07-04 P0-B live auth 시도: StealthMole 401 block
실 키로 `/v2/user/quotas`까지 네트워크 도달했으나 `401 {"detail":"Invalid token or expired token."}`에서 차단. 공개 Netskope CRE StealthMole 플러그인과 auth contract(payload `access_key`/`nonce`/`iat`, HS256, Bearer, User-Agent `netskope-ce-5.1.1-cre-stealthmole-v1.0.0`)를 대조해 `adapter/stealthmole.py`에 User-Agent를 추가하고 테스트 갱신. no-auth/garbage bearer/valid-shaped JWT가 같은 401이라 schema 실측은 미수행. 키 활성화/API product enablement/IP allowlist/발급값 종류 확인 전까지 `cds` schema는 `[확인필요]` 유지.
