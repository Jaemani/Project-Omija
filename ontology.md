# Foundry Ontology Build Guide

방산 공급망 자격증명 노출 조기경보용 Foundry 온톨로지를 실제로 만들 때 따르는 루트 가이드다.

이 문서는 기존 v0.2 스펙/ADR/테스트와 Fable zero-shot 구조 제안을 합친 실행용 문서다. `docs/spec/ontology.md`는 현재 구현 스펙이고, 이 파일은 Foundry Ontology Manager에서 어떤 Object, Link, Action을 어떤 순서로 만들지 정리한 빌드 시트다.

## 0. 결론

현재 Foundry에는 **v0.2 호환 모델**로 만든다.

- `Supplier`, `Prime`, `Program`은 당장 분리해서 만든다. 현재 코드, 테스트, OSDK hot-swap skeleton이 이 형태를 기준으로 한다.
- 단, Fable zero-shot의 지적대로 장기 모델에서는 `Prime`을 `Supplier(is_prime=true, tier=0)`로 통합하는 안이 더 깔끔할 수 있다. 이건 v0.3 ADR 후보로 남긴다.
- `Domain`은 현재 코드 호환 이름으로 유지하되, Foundry에서는 **Asset-lite**로 설계한다. 즉 `asset_type`, `host`, `url`, `criticality`, `access_surface`를 둬서 VPN/SSO/mail/web 같은 target asset을 표현한다.
- 가장 중요한 신규 보강은 `CredentialExposure -targets-> Domain/Asset`이다. 기존 `of Identity`는 "누구의 자격증명인가"이고, `targets`는 "무엇에 접근 가능한 자격증명인가"다. 이 둘을 분리해야 협력사 계정이 원청 VPN을 타깃하는 교차 조직 경로를 표현할 수 있다.
- 트리아지는 순수 점수 가중치가 아니라 `risk_band + score` 사전식 정렬로 보장한다. `band=A` 활성 경로는 `band=C` 대량 유출보다 항상 위다.

운영 원칙:

- 비밀 원문 저장 금지. `masked_value`, `secret_fingerprint`만 저장.
- 자동 발송 금지. `NotificationDraft`는 draft/review/approved까지만 관리하고 실제 전송 action을 만들지 않는다.
- LLM은 설명/초안/merge 제안 보조만 맡는다. 경로 성립, active 판정, band, score, propagation은 deterministic rule 또는 AIP Logic이 맡는다.

## 1. Foundry 생성 순서

### Step 1. Foundation objects

먼저 공급망 뼈대를 만든다.

| Object Type | Primary key | 필수 속성 | 비고 |
|---|---|---|---|
| `Supplier` | `id` | `name`, `tier`, `criticality`, `status`, `is_prime_candidate` | 협력사. v0.3에서 Prime 통합 시 `is_prime`로 확장 가능 |
| `Prime` | `id` | `name`, `status` | 원청/주계약자. 현재 v0.2 호환을 위해 별도 타입 유지 |
| `Program` | `id` | `name`, `sensitivity`, `status` | 방산 프로그램, propagation 종점 |
| `Domain` | `fqdn` 또는 `asset_id` | `fqdn`, `host`, `url`, `asset_type`, `criticality`, `access_surface`, `verified_at` | 현재 코드명은 Domain이지만 Foundry에서는 Asset-lite로 사용 |

`Domain.asset_type` 예:

- `domain`
- `vpn`
- `sso`
- `mail`
- `groupware`
- `dev`
- `web`

`Domain.access_surface` 예:

- `admin`
- `remote_access`
- `employee_portal`
- `public_web`
- `email`

### Step 2. Foundation links

다음 링크를 만든다.

| Link Type | From | To | Cardinality | 목적 |
|---|---|---|---|---|
| `subcontracts_to` | `Supplier` | `Supplier` | N:M | 2차 이하 협력사가 상위 협력사에 납품하는 가변 깊이 전파 경로 |
| `supplies` | `Supplier` | `Prime` | N:M | 협력사가 원청에 납품하는 직결 경로 |
| `runs` | `Prime` | `Program` | N:M | 원청이 운영/계약한 프로그램 |
| `owns` | `Supplier` | `Domain` | 1:N 또는 N:M | 공급망 조직이 소유/운영하는 자산 |
| `prime_owns` | `Prime` | `Domain` | 1:N 또는 N:M | 원청 소유 VPN/SSO/mail 등 target asset |

핵심 그래프 질의:

```text
Supplier --subcontracts_to*--> Supplier --supplies--> Prime --runs--> Program
```

이 경로가 flat table 반박의 첫 번째 근거다. tier 컬럼으로는 몇 단계 하청을 거쳐 어떤 프로그램까지 닿는지 설명할 수 없다.

### Step 3. Intel/evidence objects

위협 인텔리전스와 신원 객체를 만든다.

| Object Type | Primary key | 필수 속성 | 저장 금지 |
|---|---|---|---|
| `Identity` | `id` | `email`, `username`, `canonical_handle`, `account_type`, `status`, `merged_into` | 원문 비밀번호 |
| `CredentialExposure` | `id` | `module`, `secret_type`, `secret_present`, `masked_value`, `secret_fingerprint`, `first_seen`, `last_seen`, `source_ref`, `confidence`, `status` | 원문 secret, 재사용 가능한 cookie/token |
| `InfectedDevice` | `id` | `device_fingerprint`, `malware`, `infected_at`, `has_session_cookie`, `os`, `status` | 원문 cookie/token |
| `ThreatSource` | `id` | `kind`, `name`, `collected_at`, `reliability`, `status` | 출처가 제공하지 않은 민감정보 |

`secret_fingerprint`는 upstream normalize 단계에서 단방향으로 계산하고 원문 secret은 즉시 폐기한다. Foundry에는 원문 secret이 들어오면 안 된다.

### Step 4. Intel/evidence links

| Link Type | From | To | Cardinality | 목적 |
|---|---|---|---|---|
| `belongs_to` | `Identity` | `Domain` | N:1 또는 N:M | 계정이 어느 조직/도메인에 속하는지 |
| `of` | `CredentialExposure` | `Identity` | N:1 | 이 유출이 누구의 계정인지 |
| `targets` | `CredentialExposure` | `Domain` | N:1 또는 N:M | 이 자격증명이 접근하려는 자산 |
| `sourced_from` | `CredentialExposure` | `ThreatSource` | N:1 또는 N:M | 원천 provenance |
| `leaked` | `InfectedDevice` | `CredentialExposure` | 1:N | 스틸러 감염기기가 어떤 credential을 흘렸는지 |
| `compromises` | `InfectedDevice` | `Identity` | N:M | 감염기기가 어떤 신원을 침해했는지 |

`of`와 `targets`는 반드시 분리한다.

예:

```text
CredentialExposure --of--> Identity(ops@supplier-a.example)
CredentialExposure --targets--> Domain(vpn.prime-x.example)
Identity --belongs_to--> Domain(supplier-a.example)
Domain(supplier-a.example) <--owns-- Supplier
Domain(vpn.prime-x.example) <--prime_owns-- Prime --runs--> Program
```

이 교차 조직 경로가 두 번째 flat table 반박 근거다. "협력사 계정이 원청 VPN에 접근 가능하다"는 신호는 exposure owner와 target asset을 분리해야만 보인다.

### Step 5. Derived decision objects

파생 판단은 컬럼이 아니라 객체로 만든다.

| Object Type | Primary key | 필수 속성 | 상태 |
|---|---|---|---|
| `MergeProposal` | `id` | `identity_a`, `identity_b`, `basis`, `confidence`, `created_at`, `reviewer` | `proposed`, `confirmed`, `rejected` |
| `RiskAssessment` | `id` | `supplier_ref`, `risk_band`, `score`, `grade`, `active_flag`, `computed_at`, `components`, `scoring_version`, `schema_version` | `active`, `superseded`, `acknowledged` |
| `CompromiseIncident` | `id` | `supplier_ref`, `risk_band`, `opened_at`, `path_snapshot`, `path_hash`, `blast_radius`, `path_confidence` | `open`, `acknowledged`, `assigned`, `closed` |
| `ProgramExposure` | `id` | `program_ref`, `risk_band`, `score`, `grade`, `active_flag`, `computed_at`, `components`, `contributing_paths`, `scoring_version` | `active`, `acknowledged`, `superseded`, `closed` |
| `NotificationDraft` | `id` | `recipient_ref`, `body`, `created_at`, `created_by`, `reviewer` | `draft`, `reviewed`, `approved`, `exported` |

`NotificationDraft.exported`는 "시스템 밖으로 사람이 가져갔다"는 종점일 뿐이다. Foundry에 email/SMS/webhook 발송 action을 만들지 않는다.

### Step 6. Derived decision links

| Link Type | From | To | Cardinality | 강제 규칙 |
|---|---|---|---|---|
| `merge_candidates` | `MergeProposal` | `Identity` | 1:N, 최소 2 | 후보 Identity 없으면 생성 금지 |
| `evidenced_by` | `RiskAssessment` | `CredentialExposure` / `InfectedDevice` / `CompromiseIncident` | N:M, 최소 1 | 증거 없으면 생성 금지 |
| `traverses_identity` | `CompromiseIncident` | `Identity` | N:M | path_snapshot과 일치해야 함 |
| `traverses_asset` | `CompromiseIncident` | `Domain` | N:M | target/source asset을 drill-down 가능하게 함 |
| `traverses_supplier` | `CompromiseIncident` | `Supplier` | N:M | 중간 Supplier hop 보존 |
| `traverses_prime` | `CompromiseIncident` | `Prime` | N:M | 영향을 받는 원청 |
| `traverses_program` | `CompromiseIncident` | `Program` | N:M | 영향을 받는 프로그램 |
| `program_evidenced_by` | `ProgramExposure` | `RiskAssessment` / `CompromiseIncident` | N:M, 최소 1 | 프로그램 롤업 근거 |
| `cites` | `NotificationDraft` | `CredentialExposure` / `InfectedDevice` / `CompromiseIncident` / `RiskAssessment` | N:M, 최소 1 | 초안 근거 |

`PathEvidence` 별도 객체는 만들지 않는다. Fable zero-shot과 독립 검토 모두 여기에는 동의한다. Foundry에서는 `path_snapshot`, `path_hash`, `traverses_*` 링크로 충분하다. 나중에 path 자체를 객체 검색/권한/감사 대상으로 삼아야 하면 `PathStep`을 추가한다. `PathEvidence`라는 래퍼 객체는 bloat다.

#### Foundry build note (2026-07-04)

현재 Foundry 빌드는 위 논리를 다음 방식으로 구현했다.

- `MergeProposal`, `RiskAssessment`, `CompromiseIncident`, `ProgramExposure`, `NotificationDraft`는 모두 `status`를 실제 string property로 가진다. 위 표의 상태 목록은 Foundry enum이 아니라 `status` 값의 controlled vocabulary다.
- `owns`, `prime_owns`, `belongs_to`, `of`, `targets`, `sourced_from`, `leaked`, `merge_candidates`는 현재 Foundry에서 foreign-key link로 구현했다. 이 링크들은 별도 seed CSV를 쓰지 않는다.
- `subcontracts_to`, `supplies`, `runs` 및 파생 판단 provenance 링크는 join-table datasource로 테스트한다.
- Foundry Link Type은 concrete From/To pair이므로 conceptual union link는 타입별로 나눈다. 예: `evidenced_by`는 `RiskAssessment -> CredentialExposure`, `RiskAssessment -> InfectedDevice`, `RiskAssessment -> CompromiseIncident`로 분리한다. `cites`, `program_evidenced_by`도 같은 방식이다.
- Object property가 `edit-only`면 CSV/backing datasource 값이 Object Explorer에 나타나지 않는다. Seed로 채우는 속성은 datasource-backed property로 설정한다. 사람 또는 Action이 나중에 채우는 lifecycle-only 속성만 edit-only로 둔다.

## 2. Action Types

Foundry Action Type은 세 가지를 반드시 갖는다.

- Parameters: 입력 객체/값
- Edits: 만들거나 수정할 객체/링크
- Submission criteria: evidence not empty, raw secret absent 같은 제출 게이트

### 2.1 CorrelateExposure

| 항목 | 내용 |
|---|---|
| Inputs | `CredentialExposure`, optional `Domain` |
| Preconditions | `CredentialExposure.of` 또는 identity 키가 존재, target host/url/domain이 존재 |
| Edits | `Identity` 생성/갱신, `belongs_to`, `of`, `targets`, `sourced_from` 링크 생성 |
| Refuse | identity도 target도 매칭 불가하면 파생 링크 생성 금지 |
| Human review | 낮은 confidence 매칭은 `MergeProposal` 또는 review queue로 보냄 |

### 2.2 ProposeEntityMerge

| 항목 | 내용 |
|---|---|
| Inputs | 2개 이상 `Identity` |
| Preconditions | normalized handle, domain, source evidence 등 basis 존재 |
| Edits | `MergeProposal(status=proposed)` 생성, `merge_candidates` 링크 |
| Refuse | basis 빈 값, 서로 다른 조직 고신뢰 충돌 |
| Human review | 필수 |

### 2.3 ConfirmEntityMerge

| 항목 | 내용 |
|---|---|
| Inputs | `MergeProposal` |
| Preconditions | status=`proposed`, reviewer 존재 |
| Edits | canonical `Identity` 지정, exposure/device/match 링크 재지향, proposal status=`confirmed` |
| Refuse | 이미 confirmed/rejected, reviewer 없음 |
| Human review | 액션 자체가 사람 승인 |

### 2.4 FlagActiveCompromise

| 항목 | 내용 |
|---|---|
| Inputs | `InfectedDevice`, evaluation window |
| Preconditions | recent `infected_at`, `has_session_cookie=true`, `account_type in {vpn, admin}`, complete path 존재 |
| Edits | `CompromiseIncident(status=open, risk_band=A)`, `traverses_*` 링크, `path_snapshot`, `blast_radius` |
| Refuse | session cookie 없음, account type 불충분, Supplier/Prime/Program 도달 경로 없음, evidence 없음 |
| Human review | incident acknowledge/assign/close는 별도 액션 |

활성 경로 후보:

```text
InfectedDevice
  -> CredentialExposure
  -> Identity
  -> owning Supplier
  -> subcontracts_to* / supplies
  -> Prime
  -> Program

and/or

CredentialExposure
  -> targets Domain(vpn/sso/admin asset)
  -> owning Supplier or Prime
  -> Program
```

### 2.5 ComputeSupplierRisk

| 항목 | 내용 |
|---|---|
| Inputs | `Supplier`, evidence object set |
| Preconditions | evidence 최소 1개 |
| Edits | `RiskAssessment`, `evidenced_by` links, previous assessment status=`superseded` |
| Refuse | evidence empty |
| Human review | high risk는 acknowledge 필요 |

### 2.6 PropagateProgramRisk

| 항목 | 내용 |
|---|---|
| Inputs | `Program` 또는 changed `Supplier` |
| Preconditions | Program까지 도달하는 path, contributing risk/incident 최소 1개 |
| Edits | `ProgramExposure`, `program_evidenced_by`, `contributing_paths`, previous exposure status=`superseded` |
| Refuse | path 없음, evidence 없음 |
| Human review | `acknowledge`, `close`, `mark_stale` 액션을 따로 둔다 |

### 2.7 GenerateNotificationDraft

| 항목 | 내용 |
|---|---|
| Inputs | `CompromiseIncident` 또는 acknowledged `RiskAssessment` |
| Preconditions | cites 최소 1개, raw secret 없음 |
| Edits | `NotificationDraft(status=draft)`, `cites` links |
| Refuse | cites empty, body에 원문 secret 포함, 발송 요청 |
| Human review | `reviewed`, `approved`, `exported` 전이는 사람만 |

### 2.8 Acknowledge / Assign / Close

Incident와 ProgramExposure에는 최소 lifecycle action을 둔다.

- `AcknowledgeIncident`
- `AssignIncident`
- `CloseIncident`
- `AcknowledgeProgramExposure`
- `MarkProgramExposureStale`
- `CloseProgramExposure`

이 액션들은 구조적 정당성보다는 운용 배치성을 강화한다. 데모에 시간이 없으면 Incident lifecycle만 만들고 ProgramExposure lifecycle은 문서로 남긴다.

## 3. Scoring and ranking

### 3.1 Supplier risk

정렬은 `(risk_band, score)`로 한다.

| Band | 의미 | 정렬 |
|---|---|---|
| `A` | 활성 침해 경로 성립. complete path + recent infected device + session cookie + privileged/remote target | 항상 최상단 |
| `B` | target asset이 민감하고 credential이 usable하지만 active device path는 미성립 | 중간 |
| `C` | passive leaked credential only | 하단 |

`score`는 band 안에서만 순서를 정한다. 가중치를 아무리 조정해도 `band=C` 대량 유출이 `band=A` 활성 경로를 넘을 수 없어야 한다.

현재 v0.2의 active floor 방식은 이 원칙과 같은 방향이다. Foundry에서는 `risk_band`를 명시 속성으로 추가해 UI와 AIP Logic에서 더 분명하게 보이게 한다.

### 3.2 Program rollup

ProgramExposure는 다음을 합친다.

- reaching suppliers 중 최고 `RiskAssessment`
- active incident 존재 여부
- distinct active supplier 수
- program sensitivity
- path hop attenuation
- active path floor

경로가 길다고 무조건 무시하면 말단 협력사 위험을 놓친다. hop attenuation을 쓰더라도 active incident 경로에는 하한을 둔다.

### 3.3 Dedup

정규 dedup 키:

```text
(canonical_identity, target_asset, secret_fingerprint)
```

규칙:

- 동일 키 재관측은 exposure scale을 늘리지 않는다.
- 재유통 콤보리스트는 `last_seen`이나 provenance는 갱신해도 freshness 점수는 갱신하지 않는다.
- 예외: `secret_type=cookie` 또는 live session evidence는 `InfectedDevice.infected_at`을 freshness 기준으로 삼는다.
- `ConfirmEntityMerge` 후 canonical identity가 바뀌면 dedup을 다시 계산하고 superseded chain을 남긴다.

### 3.4 Confidence

경로 confidence는 edge confidence의 곱이 아니라 **min(edge_confidence)**로 잡는다.

이유:

- 곱셈은 긴 경로를 중복 처벌한다.
- 전파 깊이에 대한 처벌은 path attenuation이 이미 처리한다.
- active incident 승격 여부는 "최약 고리"가 임계값 이상인지로 판단한다.

## 4. Foundry 작업 체크리스트

1. Ontology branch를 만든다.
2. `Supplier`, `Prime`, `Program`, `Domain` object type을 만든다.
3. `subcontracts_to`, `supplies`, `runs`, `owns`, `prime_owns` link type을 만든다.
4. 샘플 registry 데이터를 넣고 Object Explorer에서 다음 경로가 보이는지 확인한다.

```text
Supplier(Hotel Microelectronics)
  -> subcontracts_to Supplier(Foxtrot Metals)
  -> supplies Prime(Xenon Aerospace)
  -> runs Program(Harbor Sustainment)
```

5. `Identity`, `CredentialExposure`, `InfectedDevice`, `ThreatSource` object type을 만든다.
6. `belongs_to`, `of`, `targets`, `sourced_from`, `leaked`, `compromises` link type을 만든다.
7. `targets`가 들어간 교차 조직 예시를 하나 만든다.

```text
Identity(ops@supplier-a.example)
  -> CredentialExposure
  -> targets Domain(vpn.prime-x.example)
  -> prime_owns Prime(Xenon Aerospace)
```

8. `MergeProposal`, `RiskAssessment`, `CompromiseIncident`, `ProgramExposure`, `NotificationDraft` object type을 만든다.
9. evidence/cites/traverses 관련 link type을 만든다.
10. Action Type을 만든다.
11. 각 Action Type에 submission criteria를 넣는다.
12. Developer Console에서 OSDK를 발행한다.
13. OSDK로 최소 왕복을 검증한다.
14. 로컬 `OntologyStore` 구현을 `FoundryOntologyStore`로 hot-swap할 때 object/link/action API name을 맞춘다.

## 5. Submission criteria checklist

Foundry Action Type마다 아래 게이트를 설정한다.

| Action | 반드시 막을 것 |
|---|---|
| `ComputeSupplierRisk` | evidence object set empty |
| `FlagActiveCompromise` | incomplete path, no session cookie, stale infection, unprivileged account, no evidence |
| `PropagateProgramRisk` | no contributing RiskAssessment/Incident, no path to Program |
| `GenerateNotificationDraft` | cites empty, raw secret present, send/webhook/email side effect |
| `ConfirmEntityMerge` | reviewer empty, proposal not proposed |

Foundry에서 object-set "not empty" 조건을 걸 수 없거나 UI가 막히면, 우선 action function/AIP Logic 안에서 거부하고, 문서에 "Foundry submission criteria pending"으로 남긴다. 단, evidence 없는 파생 객체를 생성하는 우회는 하지 않는다.

## 6. Demo proof set

심사자가 "그냥 join table 아닌가?"라고 공격할 때는 스키마 설명보다 데이터 페어가 더 중요하다. 데모에는 반드시 아래 3개를 넣는다.

1. **3-tier or variable-depth chain**

```text
InfectedDevice -> Identity -> Supplier(tier-2)
  -> Supplier(tier-1)
  -> Prime
  -> Program
```

2. **cross-target credential**

```text
CredentialExposure --of--> supplier Identity
CredentialExposure --targets--> prime VPN/SSO asset
```

3. **band dominance**

```text
Band A: active path, few records
Band C: many passive leaks
Result: Band A ranks above Band C
```

이 세 화면이 있으면 "그래프 추론", "owner vs target 분리", "구조적 트리아지"를 한 번에 증명한다.

## 7. 만들지 말 것

지금 만들지 않는다.

- `PathEvidence` 독립 객체
- `EvidenceBundle` 래퍼 객체
- `PrimeRisk`
- `TierRisk`
- fixed-depth tier objects
- CVE/TTP/malware taxonomy tree
- Supplier 내부 조직도
- raw secret property
- send email/webhook/SMS action

특히 `PrimeRisk`, `TierRisk`는 graph path로 유도 가능한 중간 rollup이다. 상태 전이와 사람 workflow가 명확해지기 전에는 객체가 아니라 view/component로 둔다.

## 8. v0.3 ADR 후보

아래는 지금 Foundry day-1에서 바로 하지 말고 ADR로 검토한다.

1. `Prime`을 `Supplier(is_prime=true, tier=0)`로 통합할지.
2. `Domain`을 완전한 `Asset`으로 rename/migration할지.
3. `PathStep` object를 도입할지.
4. `ProgramExposure` lifecycle을 Incident 수준으로 승격할지.
5. confidence threshold와 min-confidence advisory band를 별도 band로 둘지.

## 9. Reference mapping

| 이 문서 | 현재 repo v0.2 |
|---|---|
| `Domain` as Asset-lite | `Domain` object, `Supplier owns Domain` |
| `targets` | 신규 제안. 현재는 host 문자열 중심 |
| `risk_band` | 현재 active floor/grade로 구현. Foundry에서는 명시 속성 권장 |
| `path_snapshot` | 현재 incident `path[]`, program `contributing_paths[]` |
| `MergeProposal` object | 현재 코드에 존재, `docs/spec/ontology.md`에는 명시 보강 필요 |
| `ProgramExposure lifecycle` | `docs/review/open-questions.md`의 보류 항목 |

## 10. Official Foundry docs

Foundry UI는 바뀔 수 있으므로, 최종 클릭 경로는 공식 문서에서 확인한다.

- Object type 생성/편집: https://www.palantir.com/docs/foundry/object-link-types/edit-properties
- Link type 생성/편집: https://www.palantir.com/docs/foundry/object-link-types/edit-properties
- Action parameters: https://www.palantir.com/docs/foundry/action-types/parameter-overview
- Action rules/edits/submission criteria: https://www.palantir.com/docs/foundry/action-types/rules
