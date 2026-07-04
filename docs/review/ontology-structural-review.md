# 온톨로지 구조 검토 (외부감사 기준 문서)

> **목적**: 외부 감사자·심사자가 콜드스타트로 "이 온톨로지가 진짜 그래프 추론인가, 아니면 flat table에 라벨만 붙였나"를 판정할 수 있게 하는 단일 아티팩트. 자기비판·알려진 구멍·보류 결정을 숨기지 않고 명시한다.
>
> **작성 맥락**: 2026-07-04, 온톨로지 v0.1 → v0.2 심화 작업 진행 중 시점의 스냅샷. 검토 주체 = 계획·검토 모델(Fable). 실행(코드)은 별도 서브에이전트.

## 0. 콜드스타트 포인터
읽는 순서: `../../CLAUDE.md`(규칙·가드레일) → `../spec/direction.md`(백본 5요소) → `../spec/ontology.md`(**핵심** 그래프 모델 + 스멜테스트 §0) → `../spec/data-sources.md`(StealthMole 계약+어댑터) → `../spec/aip-integration.md`(AIP/OSDK) → `../spec/architecture.md`(설계). 의사결정 이력 = `../decisions/`, 변경로그 = `../changelog/architecture.md`.

## 1. 스멜테스트 판정 (ontology.md §0 기준)
온톨로지 정당성 기준 4개 — **코드로 실재 확인** (립서비스 아님):

| 기준 | 통과 | 실재 근거(코드 위치) |
|---|---|---|
| ① 다중홉 질의 | ✅ | `FlagActiveCompromise`가 Device→Identity→Domain→Supplier→Prime→Program 경로를 join+전파질의로 조립. 활성침해 = 경로 존재. |
| ② 엔티티 해소 | ✅ | `EntityResolver`가 정규화 handle로 병합 제안, `merge_identities`가 노드 병합 + 모든 엣지(Exposure/Device/match) repoint. |
| ③ 액션=상태전이 | ✅ | MergeProposal pending→confirmed, CompromiseIncident open, RiskAssessment 생성, Draft status=draft. |
| ④ provenance 그래프 | ✅ | `risk_evidence`, `exposure_match.match_basis`, incident path, draft cites. 근거 없는 파생객체는 Action이 거부. |

**정직한 판정**: 스멜테스트는 4/4 실제 통과 — 억지 온톨로지 아님. **그러나 v0.1은 그래프를 "귀속(attribution)"에만 쓰고 "전파(propagation)"에 안 썼다.** 문서(ontology.md §2)가 약속한 다중티어 전파를 구현이 안 따라가서, 실질적으로 얕았다. v0.2가 그 격차를 메운다(§3).

## 2. 핵심 자기비판 — 귀속 vs 전파
v0.1의 그래프 사용 실태:
- **귀속은 진짜**: 유출→신원→업체 연결, 5홉 경로 표시, provenance 역추적. ✅
- **전파는 미사용**: 
  1. **멀티티어 부재** — `supplies`가 Supplier→Prime 직결만. tier는 속성 라벨. ontology.md §2 간판 예시("2차 협력사 말단 감염이 원청을 노출")가 실제로 모델링 안 됨.
  2. **위험 전파 안 됨** — 스코어가 업체별 독립. Prime/Program은 종착 표시노드, 파생 위험 0. "지금 어느 프로그램이 타나"를 점수로 못 답함.
  3. **blast-radius 폐기** — 한 감염이 닿는 여러 Prime/Program 중 첫 번째만 기록.

→ v0.1은 **"그래프 모양 데이터 + 고정 조인"**에 가까웠음. v0.2는 **"그래프 추론"**(가변깊이 traverse + 상향 전파 + 집계)로 승격.

## 3. v0.2 심화 (진행 중, 이 문서 시점 미커밋)
1. **`subcontracts_to` 링크(Supplier→Supplier, N:M)** + SQLite `WITH RECURSIVE` 가변깊이 traverse(2차→1차→…→원청→프로그램). 사이클 안전: depth cap + 경로 방문검사. → "flat table 불가"의 실증.
2. **`ProgramExposure` 파생객체** — 위험이 링크 따라 상향 집계돼 프로그램에 고임. active_flag = 도달 경로 중 활성 incident 존재. evidence 없으면 생성 거부(ComputeRisk와 동일 provenance 규칙).
3. **blast-radius** — 감염기기 1대가 닿는 모든 Prime/Program 집계.

관련 신규 코드(진행 중): `actions/propagate_risk.py`, `tests/test_propagation_paths.py`, `tests/test_propagate_risk.py`. 스토어에 `subcontracts`·`program_exposure` 테이블 + 재귀 `propagation_paths()`.

## 4. 적용된 정합성 교정 (검토에서 발견, 엔진에 반영 지시)
v0.2 설계에서 **그래프 모델 결함 3개**를 사전 발견해 교정:

1. **크로스-업체 blast는 Device로 흐른다, Identity 아님.** `belongs_to`가 Identity→Domain **N:1** → 한 Identity=한 업체. "한 감염이 여러 업체 노출"은 **Device→compromises→여러 Identity(N:M)** 로만 성립. blast 집계를 device 레벨에서 수행.
2. **ProgramExposure 이중계산 방지.** 다이아몬드 공급망에서 한 프로그램에 여러 경로 도달 시 — breadth는 distinct Supplier 기준, evidenced_by는 underlying exposure/incident ref 기준 dedup. 경로 수로 부풀리지 않음.
3. **`compromises` 링크 = `leaked`∘`of` 유도.** 독립 유지되는 별개 사실로 두지 않음(정합성). Device가 leak한 Exposure의 Identity면 compromises 성립.

## 5. 알려진 약점 — 심사관의 급소
**"그거 결국 조인 두 번 아니냐."** 멀티티어를 넣어도 데모가 항상 **깊이 2**(2차→1차→원청)만 보이면, 회의적 심사관은 "고정 조인을 재귀로 포장"이라 깎을 수 있음. 재귀 traverse의 진짜 정당성 = **같은 질의 하나가 깊이 1·2·3을 균일 처리**하는 것 = flat table 불가 지점. 이 약점의 보강은 §6(D)로 보류 중.

## 6. 보류된 심화 (판단 보류, `open-questions.md` 참조)
- **D. 깊이 무관성 증명** — mock에 깊이 3 체인 추가 + 피칭에 "동일 재귀 질의가 임의 깊이 처리" 명시.
- **E. ProgramExposure 액션 라이프사이클** — "타는 프로그램"을 ack/escalate 상태전이 객체로 승격(스멜테스트 §3 강화 + 프로그램 단위 에스컬레이션 = 군 배치성).

둘 다 **유저 지시로 판단 보류(2026-07-04)**. 재검토 트리거 = 데모 돌려보고 깊이 부족이 느껴질 때. 상세 맥락·근거는 `open-questions.md`.

## 7. 이 검토가 다루지 **않은** 것 (감사 범위 명시)
- **v0.2 착지 후 스펙 문서 정합성 감사 미완**: 이 문서 시점에 엔진이 `ontology.md`·`architecture.md`·`changelog`·ADR-0006을 재작성 중 → 그 문서들의 상호참조·스멜테스트 재통과 서술 정합성은 **엔진 커밋 후 별도 감사**로 확인해야 함(포스트-엔진 태스크).
- **자격증명 처리 코드 재검토 이번 세션 미수행**: 마스킹·정규화·통보초안 등 민감 경로 `.py`는 이번 검토에서 재열람 안 함. 해당 로직의 가드레일 준수는 기존 테스트(마스킹 leak 단언, 발송기능 부재 스모크)로 커버되며, 코드 레벨 재감사가 필요하면 별도 실행모델(비-Fable)로 진행.
- **결론**: 외부 감사는 이 문서 + `../spec/*` + `../decisions/*` + 테스트 결과를 surface로 삼으면 충분. 구조·아이디어 판정에 민감 코드 열람 불필요.
