# Practical Early-Warning Plan

Goal:

> 방산 1·2차 협력사 도메인을 대상으로 유출 자격증명·스틸러 감염기기를 자동 상관하여 업체별 위험 순위를 산출하고, 활성 침해 정황에는 가중치를 높여 즉시 조치를 권고하는 조기경보 체계를 개발한다.

이 문서는 과장 없이 실제 구현 가능한 범위를 정리한다.

## 1. What We Can Realistically Build

Omija가 실질적으로 만들 수 있는 것은 "침해 확정 시스템"이 아니라 **조기경보와 우선순위 결정 시스템**이다.

가능한 것:

- 협력사 도메인 watchlist를 기준으로 유출 자격증명 후보를 조회한다.
- 스틸러 감염 기기 후보를 같은 Identity/Domain/target asset에 상관한다.
- 계정 소속(`of`)과 접근 대상(`targets`)을 분리해 교차 조직 위험을 잡는다.
- 1차·2차 협력사 체인을 따라 Prime/Program 영향도를 계산한다.
- 활성 침해 후보를 Band A로 격상하고 사람 검토용 조치 초안을 만든다.

불가능하거나 과장하면 안 되는 것:

- 외부 피드만으로 "현재 세션이 실제로 살아있다"고 확정할 수는 없다.
- 실제 침해 확정은 원청/협력사 VPN, SSO, EDR, mail, IAM 로그 확인이 필요하다.
- 다크웹 언급만으로 APT 귀속을 확정하면 안 된다.
- 통보를 자동 발송하면 안 된다. `NotificationDraft`에서 사람 검토가 필요하다.

## 2. Input Strategy

### 2.1 Supplier Domain Watchlist

기본 입력은 협력사 registry다.

```text
Supplier
  -> owned domains
  -> asset surfaces: vpn, sso, mail, groupware, dev, web, admin
  -> tier
  -> prime/program relationships
  -> contact / reviewer
```

도메인만 있으면 부족하다. 다음 alias도 watchlist로 유지한다.

- 법인명 국문/영문.
- 약칭, 브랜드명, 제품명.
- 인수합병 전 이름.
- 주요 프로그램명 또는 프로젝트명.
- 협력사 이메일 도메인과 SSO/VPN host 패턴.

### 2.2 StealthMole Module Use

StealthMole은 입력 공급원이다. 실제 API 세부나 인증 방식은 이 문서에 넣지 않는다.

| Capability | Use in Omija | Ontology target | Risk role |
|---|---|---|---|
| Credential Lookout (CL) | 협력사 도메인/계정 유출 후보 | `CredentialExposure` | passive exposure 또는 credential reuse 후보 |
| Compromised Data Set (CDS) | 인포스틸러 감염 기기, 감염 시점, 세션/계정 단서 | `InfectedDevice` | active compromise 격상 핵심 입력 |
| Darkweb Tracker (DT) | 조직명, 도메인, 제품명, 프로그램 키워드 언급 | `ThreatSource` | provenance/context 보강 |
| Telegram Tracker (TT) | 채널 기반 유출·거래 언급 | `ThreatSource` | 반복 출처와 확산 정황 보강 |
| Country/region query | 특정 국가·권역 방산/제조 협력사 노출 추세 파악 | `ThreatSource`, coverage metrics | watchlist 공백·지역별 위험 heatmap |
| Keyword query | 회사 alias, 프로그램명, 제품명, 기술 키워드 검색 | `ThreatSource`, review queue | 미등록 domain/supplier 후보 발굴 |

중요: country/keyword query 결과는 바로 `CredentialExposure`로 넣지 않는다. 먼저 `ThreatSource`나 review queue로 넣고, 실제 domain/identity/target이 확인될 때만 evidence object로 승격한다.

## 3. Normalization Contract

외부 입력은 다음 형태로 정규화되어야 한다.

### CredentialExposure

필수 후보 필드:

```text
identity_hint       email/username/account handle
source_domain       계정 소속 추정 도메인
target_host         로그인 URL, VPN/SSO/mail/admin host
secret_type         password/cookie/token/unknown
secret_present      boolean only
secret_fingerprint  one-way hash only
first_seen
last_seen
source_ref
confidence
```

금지:

```text
raw password
raw cookie
raw token
full session value
```

### InfectedDevice

필수 후보 필드:

```text
device_fingerprint
malware
infected_at
has_session_cookie
os
linked_identity_hint
linked_target_host
source_ref
confidence
```

세션 쿠키는 원문을 저장하지 않는다. `has_session_cookie=true/false`와 evidence provenance만 저장한다.

### ThreatSource

필수 후보 필드:

```text
kind
name
collected_at
reliability
matched_keyword
matched_supplier_or_program_candidate
source_ref
```

DT/TT/country/keyword 검색은 주로 여기에 들어간다.

## 4. Correlation Pipeline

### Stage 1. Candidate collection

입력 쿼리:

- supplier domain exact match;
- email domain match;
- target host match: `vpn`, `sso`, `mail`, `groupware`, `admin`, `dev`;
- company alias/keyword;
- country/region + defense/manufacturing/security keywords.

산출:

- `CredentialExposure` 후보;
- `InfectedDevice` 후보;
- `ThreatSource` 후보.

### Stage 2. Identity and asset resolution

정규화:

```text
identity_hint -> Identity
source_domain -> Domain -> Supplier
target_host -> Domain -> Supplier or Prime
```

핵심 분기:

```text
CredentialExposure.of      -> Identity owner
CredentialExposure.targets -> target Domain
```

여기서 owner와 target이 다르면 교차 조직 위험으로 표시한다.

### Stage 3. Dedup

Dedup key:

```text
(canonical_identity, target_asset, secret_fingerprint)
```

재유통 콤보리스트는 같은 secret fingerprint로 반복되어도 freshness를 갱신하지 않는다. 단, cookie/session 계열은 `InfectedDevice.infected_at`을 freshness 기준으로 본다.

### Stage 4. Active compromise candidate detection

Band A로 올릴 수 있는 최소 조건:

```text
recent infected_at
has_session_cookie = true
account_type in vpn/admin/sso/mail/dev/privileged
target Domain.asset_type in vpn/sso/mail/admin/dev
Supplier -> Prime -> Program path exists
evidence count >= 1
path_confidence >= threshold
```

이것은 "침해 확정"이 아니라 "즉시 확인해야 하는 활성 침해 후보"다.

### Stage 5. Supplier risk ranking

Risk band는 score보다 먼저 정한다.

| Band | Meaning | Ranking rule |
|---|---|---|
| A | active compromise candidate path exists | always above passive volume |
| B | high-value target or repeated correlated exposure, but active condition incomplete | above stale/passive |
| C | passive credential exposure or old breach evidence | volume matters only within band |
| D | weak or unlinked mention | review/monitor only |

Score는 band 내부 정렬용이다. Band A 소량 증거가 Band C 대량 유출보다 위에 있어야 한다.

### Stage 6. Action recommendation

`NotificationDraft`와 incident playbook은 다음을 제안할 수 있다.

- affected identity password reset.
- SSO/MFA/session revocation request.
- VPN/SSO/mail login log review window.
- supplier security contact notification draft.
- infected endpoint owner identification request.
- target asset access review.
- program owner situational awareness.

자동 발송은 하지 않는다. 승인 전에는 draft다.

## 5. StealthMole Expansion Ideas

### 5.1 Regional Exposure Heatmap

Country/region query를 사용해 특정 국가·권역의 defense/manufacturing/supplier 키워드 노출 추세를 aggregate로 본다.

사용처:

- 어느 지역 협력사 pool에서 exposure mention이 늘어나는지 감시.
- 실제 협력사 registry coverage gap을 찾기.
- ProgramExposure의 context로 "지역별 신호 증가"를 붙이기.

주의:

- 회사 식별 전에는 risk evidence로 쓰지 않는다.
- heatmap은 `ThreatSource` aggregate 또는 dashboard context다.

### 5.2 Alias Discovery

회사명/브랜드명/제품명/프로그램명 키워드 검색으로 미등록 도메인과 alias를 찾는다.

사용처:

- Supplier registry quality 개선.
- `MergeProposal` 후보 생성.
- 잘못된 도메인 매핑 발견.

주의:

- alias 후보는 사람이 확인하기 전까지 `Supplier` 확정 객체로 만들지 않는다.

### 5.3 Target Asset Discovery

검색 결과의 URL/host 패턴에서 자주 등장하는 access surface를 분류한다.

예:

```text
vpn.*
sso.*
mail.*
owa.*
citrix.*
fortinet.*
ivanti.*
dev.*
admin.*
```

사용처:

- `Domain.asset_type` 보강.
- 감시 누락 asset surface 식별.
- public context와 결합한 asset-risk 설명.

### 5.4 Campaign Context

DT/TT에서 특정 제품, 방산 프로그램, 기술 키워드가 반복되는 경우 `ThreatSource`로 묶는다.

사용처:

- `ProgramExposure.components.threat_context`.
- notification draft의 "why now" 설명.
- active compromise가 없어도 watch 상태 강화.

주의:

- actor attribution은 "possible context"로만 표현한다.

### 5.5 Vendor/Program View

원청 또는 프로그램별로 다음을 roll up한다.

```text
Program
  <- Prime
  <- Supplier chain
  <- Suppliers with Band A/B/C
  <- exposure trend
  <- open incidents
```

사용처:

- 프로그램 책임자용 risk view.
- 협력사 우선순위 회의.
- 조치 완료 추적.

## 6. MVP Acceptance Criteria

MVP는 다음을 보여야 한다.

1. 협력사 12-20개, domain 25-50개, identity 40-100개 규모 synthetic corpus.
2. 최소 하나의 2차 -> 1차 -> 원청 -> 프로그램 active path.
3. 최소 하나의 `of`와 `targets`가 다른 교차 조직 exposure.
4. Band A active candidate가 Band C 대량 passive leak보다 상위 랭크.
5. `RiskAssessment`, `CompromiseIncident`, `ProgramExposure`, `NotificationDraft`가 모두 근거 링크를 가진다.
6. public context는 asset-risk 설명으로만 보이고, credential evidence처럼 보이지 않는다.
7. raw secret은 저장소와 페이지 어디에도 없다.

## 7. Production Prerequisites

실운영에는 다음이 필요하다.

- 승인된 supplier registry와 domain ownership evidence.
- private feed access agreement and handling policy.
- raw-secret destruction policy.
- role-based access control for sensitive evidence.
- audit logging for every status transition.
- supplier notification approval workflow.
- integration with VPN/SSO/IAM/EDR logs for incident confirmation.

Omija의 책임은 조기경보와 우선순위화다. 확정 판정은 내부 로그와 담당자 검토가 결합되어야 한다.
