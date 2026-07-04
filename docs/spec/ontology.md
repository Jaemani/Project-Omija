# ontology.md — 도메인 온톨로지 (Supply-chain Credential Exposure)

**이 프로젝트의 지적 척추.** StealthMole 레코드를 나열하는 대시보드는 API-wrapper다. 우리는 그걸 **공급망 그래프**로 만들어, 위험이 협력사→원청→프로그램으로 **전파**되게 하고, 활성침해를 그래프의 **경로 존재**로 탐지한다. 여기가 해자.

> ⚠️ 유저 우려 = "온톨로지가 억지로/얕게". 그래서 스멜테스트를 먼저 두고, 이 도메인이 강하게 통과함을 보인다.

---

## 0. 온톨로지 스멜테스트 (억지/얕음 방지)
아래 중 최소 2개 만족 못 하면 온톨로지 아님. (`air`와 동일 기준)
1. 다중홉 질의 2. 엔티티 해소 3. 액션이 상태 전이 4. provenance 그래프.

**이 도메인은 4개 전부, 특히 (1)이 압도적으로 통과:**
- **위험 전파**: `InfectedDevice → Identity → Supplier → (supplies) → Prime → Program`. 2차 협력사 말단 감염이 어느 원청/프로그램을 노출시키는지 = **다중홉 그래프 질의**. flat table 불가. → (1)
- **엔티티 해소**: 한 Identity가 cds+cl+cb+ub 여러 모듈·유출에 흩어짐 → 하나의 Identity 객체로 병합, 모든 Exposure 링크. → (2)
- **활성침해 = 경로 존재**: "유효 세션 쿠키를 든 감염기기 → 기업 Identity → tier-1 Supplier → Program X" 라는 **경로가 그래프에 존재하면** 그 자체가 경보. → (1)(3)
- **액션**: FlagActiveCompromise / GenerateNotificationDraft / AcknowledgeAlert = 상태 전이. → (3)
- **provenance**: RiskAssessment → evidenced_by → Exposure/Device. → (4)

**멀티티어 심화 재통과(v0.2, subcontracts + ProgramExposure)**: `subcontracts`(Supplier→Supplier, N:M)는 (1) 다중홉을 **가변깊이**로 끌어올린다 — 2차 말단 감염이 몇 홉이든 상위 Prime/Program으로 전파되는지를 `WITH RECURSIVE` 재귀 traverse로만 답할 수 있어 flat table로 불가(간판 근거 강화). ProgramExposure는 (1) 다중홉 **집계**(한 Program에 닿는 모든 Supplier 경로 롤업) + (4) provenance(evidenced_by 비면 거부)를 동시에 충족 → §5 스코프 규율 통과(경로 질의로 유도 불가한 상태·집계 객체).

---

## 1. 객체 타입 (Object Types)
| 객체 | 핵심 속성 | 역할 |
|---|---|---|
| **Supplier** | id(PK), name, domains[], tier(1\|2), criticality | 협력사 (엔티티) |
| **Prime** | id(PK), name, program_refs[] | 원청/주계약 |
| **Program** | id(PK), name, sensitivity | 방산 프로그램(전파 최상단) |
| **Domain** | fqdn(PK), supplier_ref | 업체 자산(상관 키) |
| **Identity** | id(PK), email?, username?, domain_ref | 계정 신원 (**엔티티 해소 대상**) |
| **CredentialExposure** | module, secret_type, masked, leak_date, source_ref | StealthMole 유출 레코드 = **증거** |
| **InfectedDevice** | fingerprint?, malware, infected_at, has_session_cookie, os | 스틸러 감염기기 = **활성 신호**(cds) |
| **ThreatSource** | id, kind(darkweb/telegram/combo/breach), name | 유출이 관측된 곳(provenance) |
| **RiskAssessment** | supplier_ref, score, grade, active_flag, computed_at | **파생** 위험판정(협력사 단위) |
| **CompromiseIncident** | supplier_ref, opened_at, status, path[], blast_radius{primes[],programs[]} | **파생** 활성침해 경보(대표 경로 + blast) |
| **ProgramExposure** | program_ref, score, grade, active_flag, computed_at, components, contributing_paths[], evidenced_by[] | **파생** 프로그램 단위 롤업(전파 최상단 위험) |
| **NotificationDraft** | supplier_ref, body, evidence_refs[], created_at | **산출** 통보 초안 |

## 2. 링크 타입 (Link Types) — 깊이의 원천
| 링크 | 카디널리티 | 왜 필요(flat table로 안 되는 이유) |
|---|---|---|
| **Supplier —supplies→ Prime** | N:M | **위험 전파** 상향 경로(직결) |
| **Supplier —subcontracts_to→ Supplier** | N:M | **멀티티어 위험 전파**: 하위(2차) 협력사가 상위(1차)에 납품 → 2차 말단 감염이 상위 Prime/Program까지 **가변깊이**로 전파. 직결 supplies 없이도 재귀 traverse로 도달. flat table로 불가 |
| **Prime —runs→ Program** | N:M | 전파 최상단 도달 |
| Supplier —owns→ Domain | 1:N | 상관 키 |
| Identity —belongs_to→ Domain | N:1 | 신원→업체 귀속 (**한 Identity = 정확히 한 Supplier** — 크로스업체는 Identity로 불가) |
| **CredentialExposure —of→ Identity** | N:1 | **엔티티 해소**(한 신원 다수 유출) |
| CredentialExposure —sourced_from→ ThreatSource | N:1 | provenance |
| **InfectedDevice —leaked→ CredentialExposure** | 1:N | 한 감염기기가 다수 자격증명 유출 |
| **InfectedDevice —compromises→ Identity** | N:M | 활성침해 경로 시작점. **compromises = leaked ∘ of 유도**(감염기기가 leak한 Exposure의 Identity) — 손으로 유지하는 별개 사실이 아니라 두 링크의 합성. **크로스-업체 blast는 여기서만 성립**(한 Device가 여러 Identity→여러 Supplier compromise) → blast 집계는 **device 레벨** |
| **RiskAssessment —evidenced_by→ Exposure/Device** | 1:N | **provenance/citation** |
| **CompromiseIncident —traverses→ [Device,Identity,Supplier…,Prime]** | 경로(가변길이) | **활성침해 = 경로 객체**. Supplier hop이 여러 개(멀티티어)면 경로가 길어짐 |
| **ProgramExposure —evidenced_by→ CompromiseIncident/RiskAssessment** | 1:N | **provenance**: 프로그램 롤업의 기여 근거. 비면 생성 거부 |
| NotificationDraft —cites→ Exposure/Device | 1:N | 초안 근거 |

### 깊이 증명 — "flat table이면 못 하는 질의" 예시 (가변깊이 재귀 traverse)
> **질의**: "지금 유효 세션을 든 감염기기가 **2차 말단** 협력사 계정을 통해, 그 협력사가 (직접 원청에 납품하지 않고) **1차 협력사에 하도급**할 때, 몇 홉을 거쳐 어느 방산 프로그램을 노출시키나?"
> **그래프 traverse(가변깊이)**: `InfectedDevice(has_session_cookie=true, infected_at 최근)` → compromises → `Identity` → belongs_to → `Domain` → `Supplier(2차)` → **subcontracts_to → `Supplier(1차)` → …(가변 홉)…** → supplies → `Prime` → runs → `Program`.
> subcontracts 체인 깊이가 **미리 알려지지 않으므로** SQLite `WITH RECURSIVE` CTE로만 접힌다(사이클 안전: 방문경로 문자열 검사 + depth cap 병용). 이 **경로 전체가 하나의 CompromiseIncident**(traverses, 가변길이). flat table은 이 미지-깊이 전파를 한 행으로 못 냄 → **온톨로지 정당.** 이게 "유출 나열" 제품과의 근본 차이이자, 이 트랙의 해자.

## 3. 액션 타입 (Action Types) — human-on-the-loop
| 액션 | 행위자 | 효과 |
|---|---|---|
| `CorrelateExposure` | 파이프라인 | Exposure → Identity/Supplier 링크(도메인/이메일 매칭) |
| `ComputeRisk` | AIP Logic | RiskAssessment 생성(evidence 필수) |
| `FlagActiveCompromise` | 룰/agent | 경로 존재 시 CompromiseIncident 생성(traverses 경로 필수, blast_radius 기록) |
| `PropagateRisk` | AIP Logic | 협력사 위험을 재귀 traverse로 Program까지 롤업 → ProgramExposure 생성(evidenced_by 필수) |
| `GenerateNotificationDraft` | AIP agent | 초안 생성(cites 필수), **발송 아님** |
| `AcknowledgeAlert` / `AssignAnalyst` | 분석가 | Incident status 전이(사람 승인) |

**규칙**: evidence/cites/traverses 링크 없는 파생 객체는 Action이 거부. = provenance·경로 강제를 온톨로지 레벨에서 못박음. **NotificationDraft는 "생성"까지, 자동 발송 없음.**

## 4. 위험 스코어링 → 온톨로지 (핵심 차별점)
점수 = base 노출 + **활성침해 가중** × criticality. `ComputeRisk` Action이 산출, evidenced_by로 근거 고정.
| 요소 | 신호(객체/속성) | 방향 |
|---|---|---|
| 노출 규모 | Identity당 Exposure 수 | + |
| 최근성 | leak_date / infected_at 최근 | +↑ |
| 비밀 유형 | secret_type=plaintext/cookie/token | +↑ |
| 모듈 신뢰도 | cds/ub(High) > cl(Med) > cb(Low) | 가중 |
| **활성침해** | InfectedDevice(최근)+has_session_cookie+account_type∈{vpn,admin} → 경로 존재 | **++ (상단)** |
| criticality | tier1 / 핵심 Program 노출 | × |

활성 = `FlagActiveCompromise`의 경로가 성립할 때. 별도 grade(즉시/주의/관찰).

### 4-b. 프로그램 롤업 스코어링 (ProgramExposure) — 전파의 종착
협력사 점수는 **귀속**일 뿐. `PropagateRisk`가 재귀 traverse로 한 Program에 닿는 **모든 협력사 경로**를 모아 프로그램 단위로 롤업한다.
| 요소 | 신호 | 방향 |
|---|---|---|
| 지배 경로 | 도달 협력사 중 최고 RiskAssessment score | 주도 |
| breadth | 그 Program에 닿는 **distinct 활성 협력사 수** | + (경로 수 아님 — Supplier 기준 dedup) |
| sensitivity | Program.sensitivity(high/med/low) | × |
| 활성 여부 | 도달 경로 중 활성 CompromiseIncident가 **하나라도 존재**(경로 존재로 판정) | 밴드 상향 |
- 활성 Program은 밴드 `[active_floor..100]`, 비활성은 `[0..base_cap]` → **활성 Program이 항상 상단**(협력사 스코어링과 동일 철학, ADR-0005).
- **evidenced_by 필수**: 기여 CompromiseIncident + RiskAssessment refs. 비면 **ProgramExposure 생성 거부**(§3 provenance 규칙, ComputeRisk의 EvidenceRequired와 동일). 도달 노출 0인 Program은 ProgramExposure 없음.
- **중복 제거**: breadth·evidenced_by는 다이아몬드 공급망(2차 X가 1차 Y·Z 둘에 하도급, 둘 다 같은 Prime→Program)에서도 **distinct Supplier / underlying ref 기준** dedup — 경로 수로 부풀리지 않음. 공유 Prime·공유 Identity 이중계산 금지.
- 경유 Prime/Supplier는 **별도 파생객체를 만들지 않는다**(§5 스코프 규율): 기여는 `components`의 per-Prime 소계 + Incident path 표시로만.
- **blast_radius**: 한 활성 감염의 다운스트림 도달을 대표 경로 하나로 축소하지 않고, device가 compromise한 **모든 Supplier의 모든 도달 Prime/Program**을 CompromiseIncident에 기록(device 레벨 집계).

## 5. AIP/OSDK 구현 노트
- Object/Link/Action을 Foundry Ontology에 정의. OSDK로 타입드 접근. 어댑터(`data-sources.md`)가 Exposure/Device write, AIP Logic이 RiskAssessment/Incident/Draft를 Action으로 생성. 상세 `aip-integration.md`.

### 스코프 규율
객체 추가 전 §0 스멜테스트 재통과. 통과 못 하면 속성이지 객체 아님.
