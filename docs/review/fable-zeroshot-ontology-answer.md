# Fable Zero-Shot Answer — Ontology Structure Proposal

> `fable-zeroshot-ontology-prompt.md`에 대한 독립 답변. 작성 시점에 repo의 기존 온톨로지 스펙·구현·ADR을 참조하지 않음(프롬프트 파일 단독 입력). 기존 설계와의 비교·수렴 검증용.
> 작성: Fable 5, 2026-07-04.

---

## 0. 설계 관점 요약

이 문제의 그래프적 본질은 두 가지다.

1. **가변 깊이 전파**: 말단 협력사의 침해가 몇 단계의 하청 관계를 거쳐 어느 프로그램에 닿는지는 조회 시점의 그래프 순회로만 답할 수 있다. 하청 깊이는 고정돼 있지 않으므로 flat table의 고정 join으로는 표현 불가.
2. **교차 조직 자격증명**: 유출 자격증명은 "누구의 것인가(Identity의 소속)"와 "무엇에 대한 접근인가(target Asset의 소유자)"가 **다른 조직**일 수 있다. 협력사 직원 계정이 원청 VPN을 대상으로 하는 유출 — 이 교차 엣지가 활성 침해 경로의 핵심이며, 단일 테이블에는 자연스럽게 담기지 않는다.

온톨로지 전체는 이 두 축(전파 그래프, 교차 자격증명 그래프)을 지탱하도록 구성하고, 나머지 객체는 (a) 증거 원자, (b) 사람 워크플로 단위, 둘 중 하나가 아니면 만들지 않는다.

---

## 1. Proposed Ontology

| Object | Role | Key properties | Why object, not property | Lifecycle/status |
|---|---|---|---|---|
| **Supplier** | 공급망 노드(원청 포함, §아래 Prime 참조) | name, tier(0=prime), criticality, sector, is_prime | 가변 깊이 순회의 노드. 도메인·하청·프로그램과 다대다 관계의 허브 | active / under_review / inactive |
| **Prime** | — | — | **do not create.** Prime은 `Supplier(tier=0, is_prime=true)`로 통합. 별도 타입이면 supplies/subcontracts 링크가 타입별로 분화되어 재귀 순회가 균질하지 않게 됨. "원청도 다른 프로그램에선 협력사"인 현실도 단일 타입이 자연스럽게 수용 | — |
| **Program** | 방산 프로그램(롤업 대상) | name, criticality, classification_marker(비밀 아님), owning_primes | 다수 협력사가 하나의 프로그램에 수렴하고, 한 협력사가 다수 프로그램에 기여 — 롤업의 종점이자 심사 질문 2의 답 단위 | active / archived |
| **Domain/Asset** | 인터넷 노출 자산(도메인·호스트·URL 서비스) | fqdn, asset_type(vpn/sso/mail/groupware/dev/web), criticality, verification_source | 위협 인텔이 보는 것(host/url)과 레지스트리가 아는 것(회사)의 **접합점**. 자산 유형별 가중치(VPN≫마케팅 사이트)가 여기 산다 | verified / unverified / retired |
| **Identity** | 사람/계정 추상화 | canonical_key, handles[], account_type(employee/admin/service), privilege_hint | 동일 인물의 복수 유출 레코드가 수렴하는 지점. 이게 없으면 dedup도, Device→Identity→Asset 경로도 성립 안 함 | unverified / verified / merged(→merged_into) |
| **CredentialExposure** | 유출 자격증명 관측 1건(정규화·중복제거 후) | secret_type, secret_present(bool), masked_value, secret_fingerprint, first_seen, last_seen, confidence | **증거 원자.** 모든 파생 판단의 provenance 체인이 여기서 끝남. 원문 비밀 저장 금지 — fingerprint(단방향)와 masked만 | new / triaged / superseded / archived |
| **InfectedDevice** | 인포스틸러 감염기기 관측 | infected_at, malware_family, device_fingerprint(해시), has_session_cookie | 최강의 활성 신호. 기기 1대가 복수 Identity·복수 Exposure에 연결 — 속성으로 내리면 "같은 기기" 추론 불가 | active / stale / remediated |
| **ThreatSource** | 인텔 출처(스틸러 로그 배치, 콤보리스트, 포럼 덤프) | source_type, collected_at, reliability | 재유통 dedup("같은 콤보리스트가 또 돎")과 confidence가 출처 정체성에 의존. provenance 인용 대상 | active / deprecated |
| **RiskAssessment** | 특정 시점 Supplier 위험 판정 | score, band, computed_at, algo_version | 계산 컬럼이면 (a) 증거 링크 못 담고 (b) 분석가 acknowledge 상태가 없고 (c) 시점 T의 판정 재구성 불가 | draft / active / acknowledged / superseded |
| **CompromiseIncident** | 활성 침해 판정(경로 성립 시 생성) | severity, detected_at, path_snapshot, resolution_code | 사람 워크플로의 단위(승인·배정·종결). "지금 뚫리는 중"을 상단에 올리는 트리아지 키가 여기서 나옴 | flagged / acknowledged / assigned / closed(remediated·false_positive) |
| **ProgramExposure** | 프로그램 수준 롤업 | exposure_level, contributing_supplier_count, computed_at | 프로그램 책임자의 소비 단위. 기여 경로를 증거로 인용해야 하므로 뷰(view)가 아니라 객체 | active / acknowledged / superseded |
| **NotificationDraft** | 통보 초안(발송 없음) | recipient_org, subject, body(마스킹), export_format | human-on-the-loop 게이트가 사는 곳. 상태 전이가 곧 통제 지점 | draft / reviewed / approved / exported — **sent 상태 없음(시스템이 발송 불가)** |
| **MergeProposal** | Identity 병합 제안 | candidate_ids[], match_features, match_score | ER을 자동 확정하지 않기 위한 객체. 검토·기각·감사가 가능해야 하므로 링크 속성으로는 부족 | proposed / accepted / rejected |

경로 자체(PathEvidence)를 별도 객체로 둘지 고민했으나 **만들지 않는다**: CompromiseIncident·ProgramExposure의 `path_snapshot`(순서 있는 엣지 참조 목록 + 조회 시각)으로 충분하며, 별도 객체화는 bloat(§7). 단 snapshot은 엣지 **ID 참조**여야 함 — 문자열 요약이면 provenance 소급 불가.

---

## 2. Links / Relationships

| Link | Cardinality | Purpose | Enables graph query | Evidence/provenance carried |
|---|---|---|---|---|
| Supplier **supplies_to** Supplier | N:M, self-ref, **DAG 제약** | 하청·납품 관계 통합(원청이 Supplier로 통합됐으므로 supplies와 subcontracts_to는 동일 링크의 tier 차이) | `(:Supplier)-[:supplies_to*1..]->(:Supplier {is_prime})` 가변 깊이 상향 순회 | 계약 유형, 부품/용역 구분, 유효기간, 등록 출처 |
| Supplier **runs** Program | N:M | 원청↔프로그램 (is_prime인 Supplier만) | 전파 종점 도달 | 레지스트리 출처 |
| Supplier **feeds_program** Program | N:M, optional | 하위 협력사가 특정 프로그램에 직접 기여함이 알려진 경우의 지름길 | 원청 경유 추정보다 정밀한 롤업 | 레지스트리 출처, 확실도 |
| Supplier **owns** Domain/Asset | 1:N (공유 인프라 예외 시 N:M 허용) | 인텔↔레지스트리 접합 | domain 매칭으로 유출→회사 귀속 | 검증 방법(등록정보/공표자료), 검증일 |
| Identity **belongs_to** Domain | N:M (병합 후 복수 도메인 가능) | 계정의 소속 도메인 | Identity→Supplier 귀속(owns 역방향 경유) | 매칭 방법(email host), confidence |
| CredentialExposure **of** Identity | N:1 | 유출이 누구 것인가 | Identity 단위 노출 집계 | 정규화 규칙, 원 레코드 필드 |
| CredentialExposure **targets** Domain/Asset | N:1 (미매칭 시 null→unmatched 큐) | 유출이 **무엇에 대한 접근인가.** of와 분리하는 것이 이 설계의 핵심 — 협력사 직원 계정이 원청 자산을 target하는 교차 엣지 | "우리 VPN을 target하는, 남의 회사 소속 계정의 유출" — flat table 불가 질의 | 원 레코드의 host/url 필드 |
| CredentialExposure **sourced_from** ThreatSource | N:M | 재유통 표현(동일 exposure, 복수 출처) | dedup·freshness 판정 | 수집일, 출처별 관측 시각 |
| InfectedDevice **leaked** CredentialExposure | 1:N | 이 기기에서 나온 유출 | 기기 기준 blast radius | 스틸러 로그 레코드 ID |
| InfectedDevice **compromises** Identity | N:M | 기기가 장악한 계정(쿠키 포함) | Device→Identity→…→Program 활성 경로의 시작 엣지 | 쿠키 존재 여부, 계정 유형 |
| Identity **merged_into** Identity | N:1 | ER 확정 이력(파괴적 병합 금지) | 병합 전 레코드 소급 | 승인된 MergeProposal 참조, 승인자, 시각 |
| MergeProposal **proposes** Identity | 1:N (2+) | 병합 후보 묶음 | 검토 큐 | match feature별 근거 |
| CompromiseIncident **traverses** path | 1개 incident당 snapshot 1개(엣지 참조 목록) | 활성 침해의 경로 근거 | "이 침해가 성립하는 이유" 재현 | 순회 시각, 각 엣지 ID + 당시 상태 |
| RiskAssessment **assesses** Supplier | N:1 (이력=복수 assessment) | 판정 대상 | 시계열 비교 | — |
| RiskAssessment **evidenced_by** {Exposure, Device, Incident} | N:M, **최소 1 강제** | 근거 없는 점수 금지 | 점수 클릭→원 레코드 drill-down | 각 증거의 기여 가중치 |
| ProgramExposure **concerns** Program | N:1 | 롤업 대상 | — | — |
| ProgramExposure **evidenced_by** {RiskAssessment, Incident} + path_snapshot | N:M, 최소 1 강제 | 롤업의 근거 | "이 프로그램이 왜 위험한가" 경로 제시 | 기여 supplier별 경로 |
| NotificationDraft **notifies** Supplier | N:1 | 수신 조직 | — | — |
| NotificationDraft **about** {Incident, RiskAssessment} | N:1 | 통보 사유 | — | — |
| NotificationDraft **cites** evidence | N:M, 최소 1 강제 | 초안 본문의 모든 주장에 인용 | 수신자가 검증 가능한 통보 | 마스킹된 증거 발췌 |

**요구 목록 대비**: `Supplier supplies Prime`과 `Supplier subcontracts_to Supplier`는 Prime 통합에 따라 `supplies_to` 하나로 흡수(위 1행). 나머지 요구 링크는 전부 커버.

---

## 3. Actions

| Action | Inputs | Preconditions | Output / state transition | Refusal conditions | Human review point |
|---|---|---|---|---|---|
| **CorrelateExposure** | 원천 인텔 레코드 | 레코드에 host 또는 email 중 1+ 존재 | Identity·Asset 매칭/생성 → CredentialExposure(new) 생성, 또는 기존 exposure에 dedup 병합(sourced_from 추가, last_seen 갱신) | 원문 비밀 포함 시 마스킹 전 저장 거부. 어떤 Supplier에도 귀속 불가 시 링크 조작(fabrication) 대신 unmatched 큐 격리 | 자동 실행 허용(증거 생성만, 판정 아님) |
| **ProposeEntityMerge** | Identity 후보 집합 + match features | match_score ≥ floor | MergeProposal(proposed) | floor 미달, 후보 간 소속 Supplier 상충인데 근거 없음 | 생성은 자동, **확정은 절대 안 함** |
| **ConfirmEntityMerge** | MergeProposal + 분석가 결정 | status=proposed | accepted → merged_into 링크 생성, exposure 재지향(원본 보존) / rejected → 종결 | 이미 처리된 proposal | **액션 자체가 리뷰 지점** |
| **FlagActiveCompromise** | 경로 질의 결과 | InfectedDevice(active, infected_at ≤ 신선도 창) ∧ has_session_cookie 또는 고위험 secret_type ∧ 대상 Asset criticality ≥ 임계 ∧ Asset→…→Program 경로 성립 | CompromiseIncident(flagged) + path_snapshot | 경로 엣지 하나라도 미검증이면 incident 미생성(갭 로깅). 증거 신선도 창 초과. **자격증명 유효성 실증 시도 절대 금지 — 활성 판정은 수동적 신호만으로** | flagged → 분석가 acknowledge 전까지 하위 액션 차단 |
| **ComputeSupplierRisk** | Supplier + 평가 창 | evidenced_by 대상이 될 증거 ≥ 1 | RiskAssessment(active) 생성, 직전 assessment → superseded | **증거 0건이면 객체 미생성**(빈 점수 금지 — provenance 원칙의 액션 수준 강제) | acknowledge로 분석가 확인 기록 |
| **PropagateProgramRisk** | Program 또는 변경된 Supplier | supplies_to/feeds_program 경유 Program 도달 경로 존재 | ProgramExposure(active) 생성/갱신, 기여 경로를 evidence로 | 경로 없음. 기여 assessment가 전부 superseded/미확인 | 프로그램 책임자 acknowledge |
| **GenerateNotificationDraft** | Incident 또는 RiskAssessment | **status=acknowledged**(사람이 이미 1차 확인한 건만) | NotificationDraft(draft) — cites 최소 1, 본문 전량 마스킹 | 인용 가능 증거 없음. 본문에 원문 비밀 포함. 발송 요청(전이 자체가 없음) | draft→reviewed→approved 각 단계 사람. **exported가 종점 — 발송은 시스템 밖** |
| **AcknowledgeIncident / AssignIncident / CloseIncident** | Incident + actor + 사유 | 상태기계 순서 준수 | flagged→acknowledged→assigned→closed. close는 resolution_code 필수 | 사유 없는 close | 전 단계 사람. **false_positive 종결은 해당 증거의 후속 스코어 가중치 억제로 피드백** |

추가하지 말아야 할 액션은 §7에.

---

## 4. Scoring / Ranking Logic

### 핵심 불변식 (수치와 분리)

> **트리아지 정렬 키는 `(band, score)`의 사전식(lexicographic) 순서다. band는 활성 침해 경로 존재로 결정되며, 어떤 score도 band를 넘을 수 없다.**

- band A: open CompromiseIncident 보유(활성 경로 성립)
- band B: 신선한 고위험 증거 있으나 경로 미완성
- band C: 비활성/재유통 유출만 보유

비활성 유출 10,000건의 supplier가 band C인 한, 활성 경로 1건의 band A supplier를 절대 추월하지 못한다. 이것은 가중치 튜닝이 아니라 **정렬 구조**로 보장한다 — 수치 합산으로 우선순위를 흉내 내면 언젠가 대량 유출이 활성 침해를 밀어낸다.

### Supplier-level risk score (band 내 순서용)

성분(예시 수치는 교체 가능):

- 신선도 감쇠: `exp(-λ·days_since_first_seen)` — 기준은 **first_seen**(재유통이 신선도를 되살리지 못하게)
- 자산 가중치: vpn/sso 1.0, mail 0.6, dev 0.5, web 0.2 (예시)
- 계정 권한: admin/service > employee
- 인포스틸러 계수: 연결된 active InfectedDevice 존재 시 승수
- 볼륨: `log(1+n)` — 수확 체감, 대량 콤보리스트의 선형 부풀림 차단

### Program-level rollup

합산이 아니라 **최대 경로 기반**:

```
program_exposure = max over 기여 supplier of
   (supplier_risk × path_attenuation^hops × path_criticality)
 + breadth_term(독립 침해 supplier 수)
```

- hop당 감쇠하되, **active incident 경유 경로는 감쇠 하한(floor) 적용** — 활성 침해는 4단계 하청이어도 0으로 사라지지 않는다.
- breadth_term은 "여러 협력사가 동시에 뚫림"을 별도 신호로 — max만 쓰면 다발성 침해가 안 보임.

### Deduplication rule

- 정규 키: `(identity_canonical, target_asset, secret_fingerprint)`
- 동일 키 재관측 = 기존 exposure에 sourced_from 추가. **freshness 갱신 없음.**
- 예외: `secret_type=cookie` — 세션 쿠키는 감염 시점 자체가 신호이므로 감염기기의 infected_at 기준으로 별도 신선도.
- ConfirmEntityMerge 후 canonical key 충돌 시 exposure 병합 재실행(superseded 체인 유지).

### Confidence / provenance

- 경로 confidence = 경로 상 엣지 confidence의 **min** (최약 고리 원칙). 곱셈은 긴 경로를 부당하게 벌줌 — 전파 깊이는 이미 attenuation이 처리.
- min-confidence < 임계 → incident 대신 advisory(band 승격 없음).
- 모든 표시 점수는 evidenced_by drill-down 필수. 증거 0건 객체는 액션 수준에서 생성 자체가 거부됨(§3 ComputeSupplierRisk).

---

## 5. Smell Test

| # | 기준 | 판정 | 근거 / 보완 |
|---|---|---|---|
| 1 | Multi-hop 없이는 못 답하는 질문 존재 | **pass** | "이 감염기기에서 도달 가능한 프로그램은?" = Device→compromises→Identity→(of⁻¹)→Exposure→targets→Asset→(owns⁻¹)→Supplier→supplies_to*→runs→Program. 가변 깊이 + 교차 조직 targets 엣지 — 고정 join 불가 |
| 2 | ER이 객체/링크 수준 | **pass** | MergeProposal(객체, 상태기계) + merged_into(비파괴 이력 링크) + ConfirmEntityMerge(사람 액션) |
| 3 | Action이 실제 상태 전이 | **pass** | 모든 파생물이 상태 있는 객체로 생성되고, 모든 액션이 명시적 전이. 계산 컬럼 0개 |
| 4 | 파생 판단에 provenance 강제 | **weak → 보완** | evidenced_by 최소 1은 액션 수준에서 강제되나, **path_snapshot이 속성이라 엣지가 나중에 변하면 스냅샷과 현재 그래프가 어긋날 수 있음.** 보완: snapshot에 엣지 ID + 당시 상태 해시를 저장하고, drill-down UI는 "스냅샷 당시" 뷰를 재구성. 이 비용으로 PathEvidence 객체화(bloat)를 회피 |

---

## 6. Minimal Demo Slice (24h)

**Must-have for demo**
- 객체: Supplier(+is_prime), Program, Domain/Asset, Identity, CredentialExposure, InfectedDevice, CompromiseIncident, NotificationDraft
- 링크: supplies_to, runs, owns, belongs_to, of, **targets**, leaked, compromises, evidenced_by, cites
- 액션: CorrelateExposure, FlagActiveCompromise, ComputeSupplierRisk, Acknowledge, GenerateNotificationDraft
- 불변식: band 사전식 트리아지 — **이거 없으면 데모가 유출 목록 뷰어로 전락**

**Should-have if time**
- ProgramExposure + PropagateProgramRisk (심사 질문 2의 직답 — 여력 되면 must에 준함)
- Assign/Close 워크플로, false_positive 피드백
- MergeProposal 1건 canned 시연(제안→승인→exposure 재지향)

**Defer explicitly**
- 전면 자동 ER 파이프라인(데모 데이터는 pre-merged로 준비)
- ThreatSource reliability 등급 체계(객체는 두되 등급은 상수)
- confidence 전파 수식의 정밀 튜닝
- RiskAssessment 시계열 UI

**Ontology bloat (있어 보이지만 금지)**
- Prime 별도 타입 · CVE/TTP/멀웨어 패밀리 분류 객체 트리 · Supplier 내부 조직도 · Identity와 별개의 Person 객체 · EvidenceBundle 래퍼 · PathEvidence 독립 객체

---

## 7. Critical Review (자기 반박)

**과한 부분**
- ThreatSource: 데모 스케일에선 exposure의 문자열 속성 2개로 충분할 수 있다. 객체 유지 근거는 재유통 dedup 하나 — 심사에서 그 시나리오를 안 보여줄 거면 내려라.
- RiskAssessment 이력(superseded 체인): mock 데이터에선 세리머니로 보일 위험. 데모에선 최신 1개만 노출.

**"그냥 join table 아닌가?" 공격 지점**
- supplies_to + runs만 보면 맞는 말이다. 방어는 두 가지뿐: (1) **가변 깊이** — 3티어 이상 하청 체인이 데모 데이터에 실제로 있어야 하고, (2) **교차 조직 targets** — "협력사 소속 Identity의 exposure가 원청 Asset을 target"하는 레코드가 있어야 한다. 둘 다 없으면 그래프 주장은 무너진다. **데이터 요구사항이지 스키마 요구사항이 아님을 명심.**

**진짜 그래프 추론으로 보이게 하는 최소 데이터 페어**
1. tier-2 감염기기 → 세션 쿠키 → 원청 VPN target → 프로그램 도달 (band A, 소량 증거)
2. 재유통 콤보리스트 500건 보유한 조용한 tier-1 (band C, 대량 증거)
→ 1번이 2번 위에 랭크되는 화면 하나가 dominance 불변식과 그래프 필요성을 동시에 증명한다.

**속성으로 내려야 할 후보**
- malware_family: InfectedDevice 속성으로 충분(분류 객체 금지)
- ThreatSource: 위 조건부
- classification_marker: Program 속성(비밀 등급 체계 객체화 금지)

**추가하면 안 되는 액션**
- 자동 Identity 병합(ER 신뢰 붕괴)
- 자동 발송/자동 차단/자동 비밀번호 리셋(권한 밖 + 가드레일 위반)
- **자격증명 유효성 검증(로그인 시도) — 어떤 형태로도 금지.** "활성" 판정은 감염 신선도·쿠키 존재 등 수동 신호로만
- 스캐닝/자산 발견 자동화(무단 스캐닝 금지 원칙)
- 테이크다운 요청 자동화(통보와 동일하게 초안까지만이라면 별도 액션이 아니라 NotificationDraft의 변형)
