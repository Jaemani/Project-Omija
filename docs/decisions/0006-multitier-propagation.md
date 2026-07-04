# ADR-0006: 멀티티어 전파 — subcontracts 재귀 traverse + ProgramExposure 롤업

날짜: 2026-07-04
상태: 승인

## 맥락
공급망 그래프가 이 트랙의 척추(ontology.md §0, CLAUDE.md)인데, 실제 구현은 그래프를
**귀속(attribution)에만** 쓰고 **전파(propagation)에는 쓰지 않았다.** 세 구멍:
1. **멀티티어 부재**: `supplies`는 Supplier→Prime 직결만. tier는 속성 라벨일 뿐이라
   ontology.md §2 간판 예시("2차 협력사→원청→프로그램")가 실제로 모델링되지 않음.
2. **위험 전파 없음**: 스코어가 협력사별 독립. Prime/Program은 종착 표시 노드일 뿐 파생
   위험이 0 — "지금 어느 프로그램이 타나"를 점수로 답하지 못함.
3. **blast-radius 폐기**: FlagActiveCompromise가 `prop[0]`만 쓰고 나머지 도달 Prime/
   Program을 버림.
즉 문서(ontology.md)가 코드보다 깊었다. 심사 차별점(전파·활성 트리아지)이 코드에서 죽어 있었다.

## 결정
- **Supplier —subcontracts_to→ Supplier (N:M)** 링크 신설(`subcontracts` 테이블). 의미:
  하위(2차) 협력사가 상위(1차)에 납품. 기존 `supplies`(Supplier→Prime)는 유지.
- **가변깊이 재귀 traverse**(`store.propagation_paths`): 한 Supplier에서 `subcontracts`를
  상향 재귀(2차→1차→…)로 따라가 `supplies→Prime→runs→Program`에 도달하는 **가변길이
  경로**를 조립. SQLite `WITH RECURSIVE` CTE — 이것이 "flat table로 불가능"의 증명.
  **사이클 안전 = depth cap(6) + 방문경로 문자열 검사(`instr`) 병용**(cap 단독은 cap 도달
  전 조합 폭발 가능).
- **ProgramExposure 파생객체 + PropagateRisk 액션**: 각 Program에 닿는 모든 협력사 경로를
  모아 RiskAssessment를 롤업. score = 지배 경로(최고 협력사 score) + breadth(distinct 활성
  협력사, **Supplier 기준 dedup**) × sensitivity. 활성 Program은 밴드 상향(비활성보다 항상
  상단, ADR-0005 철학). **evidenced_by(기여 Incident/Assessment) 비면 생성 거부**(ComputeRisk
  EvidenceRequired와 동일 provenance 규칙). 다이아몬드 공급망은 distinct Supplier/underlying
  ref 기준으로 dedup(경로 수로 부풀림 금지).
- **경유 tier-1/Prime은 별도 파생객체 금지**(스멜테스트 §5 스코프 규율): 경로 질의로 유도
  가능하고 상태전이가 없음. 기여는 ProgramExposure.components 소계 + Incident path 표시로만.
- **blast-radius 복원**: CompromiseIncident에 `blast_radius{primes[],programs[]}` 저장 —
  device가 compromise한(=leaked∘of) 모든 Supplier의 모든 도달 Prime/Program을 **device
  레벨**로 집계(대표 경로 하나로 축소하지 않음). belongs_to가 Identity→Domain N:1이라
  크로스-업체 blast는 Identity가 아니라 InfectedDevice→compromises→여러 Identity로만 성립.
- **compromises = leaked ∘ of 유도**: Device→Identity 링크는 감염기기가 leak한 Exposure의
  Identity로 채워 두 링크와 모순 없게(독립 사실로 손유지 금지).

## 근거
- **스멜테스트 강화(§1 다중홉·§4 provenance)**: subcontracts는 다중홉을 **가변깊이**로
  끌어올려 flat table 불가능성을 재귀 CTE로 증명(간판 근거). ProgramExposure는 다중홉
  **집계** + provenance를 동시 충족 → 억지/얕음 아님.
- **심사 전파 차별점**: "유출 나열" 대비 "2차 말단 감염이 2홉 위 프로그램을 태운다"를
  점수·경로로 시연 = 방산 배치성(Military Deployability)·창의성 점수원.
- **밴드 분리 재사용**: 활성 Program을 비활성 위로 강제하는 것은 ADR-0005의 협력사 밴드
  분리와 동일 불변식 → 튜닝 무관하게 "타는 프로그램 상단" 보장.
- **스코프 규율**: Prime/경유 Supplier 파생객체를 만들면 스멜테스트 탈락. ProgramExposure만
  추가하고 나머지는 경로·components로 표현 → 온톨로지 비대화 방지.

## 영향
- **스토어**(`store/sqlite.py`, ADR-0003 확장): `subcontracts`·`program_exposure`·
  `program_exposure_evidence` 테이블, `compromise_incident`에 blast 컬럼. 신규 메서드
  `link_subcontract`·`propagation_paths`(재귀 CTE)·`device_compromised_suppliers`(leaked∘of)·
  `record_program_exposure`/`program_exposures`/`program_exposure_evidence`. Protocol
  (`store/base.py`) + Foundry 스켈레톤(`store/foundry.py`)에 선언·스텁 — hot-swap 계약 유지.
- **액션**: `actions/propagate_risk.py`(신규, PropagateRisk+ProgramExposure), `flag_active.py`
  (재귀 traverse 사용 + 가변길이 path + device 레벨 blast).
- **레지스트리/목**: `registry/suppliers.yaml`에 2차 말단 `sup-h`(직결 supplies 없이
  subcontracts→sup-f만) + `adapter/mock.py`에 그 말단의 활성침해 감염기기. 합성 도메인 유지.
- **문서**: ontology.md(§0·§1·§2·§3·§4-b), architecture.md(§1·§2·§4), 이 ADR, changelog.
- **테스트**: 재귀 traverse·사이클 안전·ProgramExposure provenance/밴드·diamond dedup·
  device 레벨 blast·멀티티어 활성 케이스 추가. 기존 카운트 하드코딩 테스트(활성 2→3,
  ground_truth) 갱신 — changelog에 사유 명시.
- day-1: `propagation_paths`는 OSDK 그래프 traverse/AIP Logic, `PropagateRisk`는 AIP Logic
  Action으로 hot-swap(밴드 분리·evidence 강제·dedup 원칙 유지).
