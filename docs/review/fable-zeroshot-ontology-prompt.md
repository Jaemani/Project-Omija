# Fable Zero-Shot Prompt — Ontology Structure Proposal

목적: Fable에게 **프로젝트 코드 리뷰가 아니라**, 방산 공급망 자격증명 노출 조기경보를 위한 **온톨로지 구조 자체**를 from-scratch로 제안받는다. 아래 프롬프트는 현재 repo 구현·테스트·기존 ADR을 일부러 주지 않는 독립 검토용이다.

---

## Copy-Paste Prompt

너는 방어적 사이버 위협 인텔리전스와 공급망 리스크 관리를 위한 **온톨로지/그래프 모델 아키텍트**다.

중요한 운영 제약:

- 이 작업은 코드 작성, API 호출, 데이터 수집, 침투, 스캐닝, credential 사용이 아니다.
- 목적은 합법적 방어 시스템의 **개념 온톨로지 설계**다.
- 유출 비밀번호/쿠키/토큰 원문은 절대 다루지 않는다. 모든 비밀값은 존재 여부와 마스킹된 값만 표현한다.
- 자동 통보/자동 차단/자동 제재가 아니라, 사람이 검토하는 조기경보와 초안 생성까지다.
- 판단이 불가능하거나 안전가드에 걸릴 것 같으면 우회하지 말고, 어느 부분이 막히는지 설명하고 중단해라.

## Problem

한국 방산 공급망에는 원청, 1차 협력사, 2차 이하 협력사가 연결돼 있다. APT는 말단 협력사를 초기 침투 지점으로 삼을 수 있다. 외부 위협 인텔리전스에는 다음 신호가 흩어져 있다.

- 유출 자격증명: email/username, host/url/domain, secret type, leak date, source/module, confidence.
- 인포스틸러 감염기기: infected_at, malware family, host/url/domain, account type, whether session cookie exists.
- 공급망 레지스트리: Supplier, Prime, Program, Domain, tier, criticality, subcontract/supply relationships.

우리가 답하고 싶은 질문:

1. "지금 우리 공급망에서 실제 침해로 이어질 가능성이 높은 협력사는 어디인가?"
2. "말단 협력사의 감염이 어떤 원청/방산 프로그램까지 전파되는가?"
3. "단순 유출 목록이 아니라, 활성 침해 신호와 전파 경로를 근거와 함께 설명할 수 있는가?"
4. "위험 판정, 프로그램 롤업, 통보 초안이 모두 원천 증거를 인용하는가?"

## Design Goal

아래 기준을 만족하는 온톨로지 구조를 제안해라.

1. **Real graph, not flat table**
   - Supplier → Supplier → Prime → Program 같은 가변 깊이 전파가 가능해야 한다.
   - Device → Identity → Domain → Supplier → ... → Program 경로가 활성 침해의 핵심 근거가 되어야 한다.

2. **Entity resolution**
   - 같은 사람/계정이 다른 email handle, username 변형, 여러 노출 레코드로 나타날 수 있다.
   - 자동 확정이 아니라 병합 제안과 사람 검토가 가능해야 한다.

3. **Action as state transition**
   - 위험 점수, 활성 침해 경보, 프로그램 위험 롤업, 통보 초안은 단순 계산 컬럼이 아니라 파생 객체 또는 액션 결과여야 한다.
   - 각 액션은 상태 전이를 가져야 하며, 사람이 검토/승인/닫을 수 있어야 한다.

4. **Provenance mandatory**
   - 근거 없는 RiskAssessment, Incident, ProgramExposure, NotificationDraft는 생성하면 안 된다.
   - 모든 파생 판단은 Exposure, InfectedDevice, ThreatSource, traversed path 등 원천 근거를 링크해야 한다.

5. **Defensive constraints**
   - 비밀 원문 저장 금지.
   - 자동 발송 금지.
   - credential reuse, intrusion, scanning, exploitation workflow 금지.

## Required Output

다음 형식으로 답해라.

### 1. Proposed Ontology

객체를 표로 제안해라.

컬럼:

- Object
- Role
- Key properties
- Why it must be an object, not just a property
- Lifecycle/status if any

반드시 고려할 후보:

- Supplier
- Prime
- Program
- Domain / Asset
- Identity / Account
- CredentialExposure
- InfectedDevice
- ThreatSource
- RiskAssessment
- CompromiseIncident
- ProgramExposure or equivalent program-level rollup
- NotificationDraft
- MergeProposal or equivalent human-reviewed entity-resolution object

필요 없다고 판단되는 후보는 "do not create"로 명시하고 이유를 설명해라.

### 2. Links / Relationships

링크를 표로 제안해라.

컬럼:

- Link
- Cardinality
- Purpose
- What graph query it enables
- What evidence/provenance it carries

반드시 다뤄라:

- Supplier supplies Prime
- Supplier subcontracts_to Supplier
- Prime runs Program
- Supplier owns Domain/Asset
- Identity belongs_to Domain/Asset/Supplier
- CredentialExposure of Identity
- CredentialExposure sourced_from ThreatSource
- InfectedDevice leaked CredentialExposure
- InfectedDevice compromises Identity
- CompromiseIncident traverses path
- RiskAssessment evidenced_by evidence
- ProgramExposure evidenced_by evidence
- NotificationDraft cites evidence

### 3. Actions

액션을 표로 제안해라.

컬럼:

- Action
- Inputs
- Preconditions
- Output object/state transition
- Refusal conditions
- Human review point

반드시 다뤄라:

- CorrelateExposure
- ProposeEntityMerge
- ConfirmEntityMerge
- FlagActiveCompromise
- ComputeSupplierRisk
- PropagateProgramRisk
- GenerateNotificationDraft
- Acknowledge / Assign / Close Incident

### 4. Scoring / Ranking Logic

다음을 구분해서 제안해라.

- Supplier-level risk score
- Program-level rollup score
- Active compromise dominance rule
- Deduplication rule for re-circulated leaked credentials
- Confidence/provenance handling

수치가 필요하면 예시로만 제안하고, 핵심 불변식은 수치와 분리해라. 특히 "활성 침해 경로가 성립한 대상은 비활성 대량 유출보다 우선 triage된다"는 구조를 어떻게 보장할지 설명해라.

### 5. Smell Test

제안한 구조가 아래 4개 기준을 통과하는지 자체 평가해라.

1. Multi-hop graph query가 없으면 답할 수 없는 질문이 있는가?
2. Entity resolution이 객체/링크 수준에서 표현되는가?
3. Action이 실제 상태 전이를 만드는가?
4. 모든 파생 판단에 provenance가 강제되는가?

각 항목을 `pass / weak / fail`로 판정하고, weak/fail이면 보완안을 제안해라.

### 6. Minimal Demo Slice

24시간 해커톤 데모에 필요한 최소 구조와, 나중에 미뤄도 되는 구조를 나눠라.

출력:

- Must-have for demo
- Should-have if time
- Defer explicitly
- Things that would look impressive but are ontology bloat

### 7. Critical Review

마지막에 스스로 반대 입장에서 비판해라.

- 이 구조가 과한 부분은?
- 심사자가 "그냥 join table 아닌가?"라고 공격할 수 있는 부분은?
- 어떤 데이터/예시가 있어야 진짜 그래프 추론으로 보이는가?
- 어떤 객체는 속성으로 내려야 하는가?
- 어떤 액션은 추가하면 안 되는가?

## Important Answer Style

- 코드 구현 계획을 쓰지 마라.
- 특정 repo 파일을 가정하지 마라.
- API 호출 방법을 쓰지 마라.
- 보안 공격 절차를 쓰지 마라.
- 구조 제안과 판단 기준만 써라.
- 최종 답변은 실행 가능한 설계 리뷰 문서처럼 써라.

