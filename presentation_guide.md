# Omija Presentation Guide

발표자가 이 문서 하나만 읽어도 프로젝트의 취지, 논리, 시연 흐름, 데이터 경계,
StealthMole의 역할, Foundry 온톨로지의 필요성을 설명할 수 있게 정리한 가이드다.

## 0. 한 문장 요약

Omija는 다크웹/유출 자격증명 데이터를 직접 보여주는 서비스가 아니라, 그런 신호가
들어왔을 때 **방산 공급망 온톨로지 위에서 어느 협력사, 어느 자산, 어느 원청,
어느 프로그램까지 위험이 전파되는지 판단하고 조치 초안을 만드는 의사결정 시스템**이다.

발표 핵심 문장:

> 실제 유출 자격증명은 피해자 데이터라서 공개 시연에 올릴 수 없습니다. 그래서 기업과
> 자격증명 개체는 가상으로 두고, 시스템 자체는 실제로 구축했습니다. Foundry 온톨로지,
> 스코어링 엔진, 프로그램 역추적, 액션 상태 전이, 공개 threat context가 모두 실행 가능한
> 형태로 연결되어 있습니다.

## 1. 문제 정의

방산 공급망은 원청 하나와 협력사 몇 개로 끝나지 않는다. 1차 협력사, 2차 협력사,
하위 공급업체, 외주 계정, VPN/SSO/mail/dev 자산이 얽혀 있다.

공격자는 항상 원청 정문으로 들어오지 않는다. 말단 협력사의 계정이 유출되거나,
협력사 직원 PC가 인포스틸러에 감염되고, 그 계정이 원청 VPN이나 SSO를 향할 수 있다.

이때 단순한 유출 목록은 다음 질문에 답하지 못한다.

```text
이 계정이 누구 것인가?
이 계정이 접근하려는 자산은 누구 것인가?
그 협력사는 어느 원청/프로그램과 연결되는가?
지금 활성 침해로 봐야 하는가, 오래된 유출로 봐야 하는가?
누가 어떤 근거를 보고 어떤 조치를 승인해야 하는가?
```

Omija는 이 질문에 답하기 위해 만들어졌다.

## 2. 왜 온톨로지가 필요한가

이 프로젝트의 핵심은 대시보드가 아니라 **온톨로지 구조**다.

### 2.1 `of`와 `targets` 분리

가장 중요한 설계는 `CredentialExposure.of -> Identity`와
`CredentialExposure.targets -> Domain`을 분리한 것이다.

- `of`: 유출된 계정이 누구의 계정인가.
- `targets`: 그 계정이 접근하려는 자산이 무엇인가.

두 값은 같은 조직일 수도 있지만, 방산 공급망에서는 다를 수 있다.

예:

```text
협력사 직원 계정(of: Supplier Identity)
  -> 원청 VPN(targets: Prime Domain)
```

flat table에서는 보통 "도메인 하나, 회사 하나, 계정 하나"로 뭉개진다. 그러면 협력사
계정이 원청 자산을 향하는 교차 조직 위험을 표현하기 어렵다. Omija는 이 차이를 링크로
분리했기 때문에 공급망 경로를 계산할 수 있다.

### 2.2 `subcontractsTo` 가변 깊이

공급망은 항상 1단계가 아니다.

```text
Supplier(T2) -> Supplier(T1) -> Prime -> Program
```

하위 협력사가 직접 원청에 연결되지 않아도, 1차 협력사를 통해 프로그램에 영향을 줄 수
있다. 그래서 `Supplier.subcontractsTo -> Supplier`는 고정 컬럼이 아니라 재귀적으로
순회해야 하는 링크다.

### 2.3 판단 객체가 별도로 필요함

Omija는 단순히 점수 숫자만 만들지 않는다.

- `RiskAssessment`: 협력사 단위 위험 판단.
- `CompromiseIncident`: 활성 침해 경로가 성립한 사건.
- `ProgramExposure`: 프로그램 단위 영향 롤업.
- `NotificationDraft`: 사람 검토가 필요한 통보 초안.

이 객체들이 있어야 "왜 이 판단이 나왔는지", "어떤 근거를 봤는지", "누가 상태를
바꿨는지"가 남는다.

### 2.4 `traverses_*`와 `cites`

`CompromiseIncident.traverses_*`는 사건이 지나간 Identity, Domain, Supplier, Prime,
Program 경로를 남긴다.

`NotificationDraft.cites`는 통보 초안이 어떤 근거 객체를 인용하는지 남긴다.

이것이 없으면 보고서는 그럴듯하지만 감사가 불가능하다. 방산/CERT 맥락에서는
"왜 이 조치를 권고했는가"를 되짚을 수 있어야 한다.

## 3. StealthMole이 Omija에서 하는 역할

StealthMole은 Omija의 **입력단 후보**다. Omija가 다크웹을 직접 감지하거나 크롤링하는
시스템이 아니다. StealthMole이 이미 수집한 다크웹/유출/스틸러 관련 데이터를 승인된
경계에서 받아오고, Omija는 그것을 온톨로지에 맞게 정규화해 판단한다.

현재 공개 시연에서는 민감 데이터가 올라가지 않으므로 실제 private 결과를 보여주지
않는다. 대신 역할은 명확히 설명한다.

### 3.1 Credential Lookout (CL)

역할:

- 협력사 도메인 기준 유출 계정/자격증명 신호.
- Omija에서는 `CredentialExposure`의 원천 후보.

Omija에 들어오면:

```text
CL signal
  -> CredentialExposure
  -> of Identity
  -> belongs_to Domain / Supplier
```

설명 포인트:

> CL은 "어느 협력사 계정이 노출됐는가"의 출발점입니다. 하지만 그것만으로는 위험
> 우선순위가 나오지 않습니다. Omija는 이 계정이 어떤 자산을 향하는지, 어느 프로그램과
> 연결되는지를 계산합니다.

### 3.2 Compromised Data Set (CDS)

역할:

- 인포스틸러 감염 기기에서 나온 신호.
- 세션 쿠키, 계정 타입, 감염 시점 같은 활성 판단 단서가 중요하다.
- Omija에서는 `InfectedDevice`와 활성 침해 판단의 핵심 입력.

Omija에 들어오면:

```text
CDS signal
  -> InfectedDevice
  -> leaked CredentialExposure
  -> compromises Identity
  -> active compromise precondition
```

활성 판단에서 중요한 조건:

```text
recent infected_at
has_session_cookie
account_type in vpn/admin
```

설명 포인트:

> 단순 유출은 오래된 재유통일 수 있습니다. 하지만 최근 감염 기기, 살아있는 세션,
> VPN/admin 계정이면 대응 우선순위가 달라집니다. Omija의 Band A는 이 구조적 경로가
> 성립할 때 올라갑니다.

### 3.3 Darkweb Tracker (DT)

역할:

- 다크웹 포럼/마켓에서 협력사 또는 키워드 언급을 보강.
- Omija에서는 `ThreatSource` 또는 decision component의 보조 근거.

설명 포인트:

> DT는 단독으로 결론을 내리는 입력이 아니라, "이 신호가 어떤 지하 생태계 문맥에서
> 나온 것인가"를 보강하는 provenance입니다.

### 3.4 Telegram Tracker (TT)

역할:

- 텔레그램 채널의 유출/거래 정황.
- Omija에서는 보조 출처 다양화와 provenance 강화.

설명 포인트:

> TT는 같은 협력사나 자산이 여러 출처에서 반복 등장하는지 확인해 신뢰도를 보강할 수
> 있습니다. 하지만 자동 조치를 만들지는 않고, 사람이 검토할 근거로 남깁니다.

## 4. 데이터 흐름

전체 흐름은 다음과 같다.

```text
[StealthMole / 공개 context / synthetic seed]
        |
        v
[Adapter boundary]
  - ExposureSource protocol
  - 정규화
  - 마스킹
  - 원문 비밀값 폐기
        |
        v
[Foundry Ontology]
  - CredentialExposure
  - InfectedDevice
  - Identity
  - Domain
  - Supplier
  - Prime
  - Program
        |
        v
[Graph reasoning]
  - of / targets 분리
  - supplier chain traversal
  - active compromise 판단
        |
        v
[Decision objects]
  - RiskAssessment
  - CompromiseIncident
  - ProgramExposure
  - NotificationDraft
```

발표에서는 "StealthMole이 감지, Omija가 판단"이라고 말하면 된다.

## 5. 현재 데모에서 진짜인 것과 가상인 것

이 구분을 명확히 해야 한다. 그렇지 않으면 전체가 가짜 시나리오처럼 보인다.

### 진짜인 것

- Foundry에 만든 온톨로지 구조.
- Object Type과 Link Type 설계.
- `of`, `targets`, `subcontractsTo`, `traverses_*`, `cites` 구조.
- 스코어링/전파/역추적 엔진.
- 공개 context snapshot.
- Foundry action/readback audit evidence.
- HTML 운영 화면과 보고서 산출.

### 가상인 것

- 협력사 이름.
- 도메인.
- 계정.
- 자격증명.
- 감염 기기.

### 왜 가상이어야 하는가

실제 유출 자격증명은 피해자 데이터다. 공개 데모, GitHub Pages, 발표 녹화에 올리는
순간 새로운 노출 표면이 된다. 그래서 개체 데이터는 synthetic으로 두고, 시스템 구조와
판단 엔진을 증명한다.

## 6. 지금까지 만든 주요 산출물

### 6.1 Foundry ontology

루트 문서:

```text
ontology.md
```

설명할 내용:

- Supplier, Domain, Identity, CredentialExposure, InfectedDevice 등 핵심 객체.
- RiskAssessment, CompromiseIncident, ProgramExposure, NotificationDraft 등 판단 객체.
- `of`, `targets`, `subcontractsTo`, `supplies`, `runs`, `traverses_*`, `cites` 링크.

### 6.2 평시 콘솔

파일:

```text
out/omija_console_home.html
```

목적:

- 사건이 없을 때 분석가가 켜놓는 기본 화면.
- 감시 범위, 조용함의 증명, feed status, action audit stream을 보여준다.
- 민감 정보 구역은 잠긴 슬롯으로 둔다.

설명:

> 이 화면은 "사건 보고서 생성기"가 아니라 운영 시스템이라는 점을 보여줍니다. 지금
> 어떤 공급망 범위를 보고 있고, 어디가 잠겨 있으며, 어떤 판단이 감사 가능하게 남는지
> 보여줍니다.

### 6.3 데이터 커버리지 맵

파일:

```text
out/data_coverage_map.html
```

목적:

- 어디서 어떤 데이터가 관리되는지 한눈에 보여준다.
- synthetic seed, public context, engine result, live readback, locked sensitive slot을
  색으로 구분한다.

설명:

> 심사자가 "지금 뭘 보고 있는 건가?"라고 물을 때 이 화면을 보여주면 됩니다. 가상
> 데이터, 공개 데이터, 실제 엔진 산출, 잠긴 민감 구역이 분리되어 있습니다.

### 6.4 사건 보고서 / 케이스 페이지

파일:

```text
out/omija_demo.html
```

목적:

- 문제가 생겼을 때 Omija가 어떤 경로와 근거를 보여주는지 설명.
- provenance chip으로 LIVE / ENGINE / SEED / FRAME / PUBLIC_CONTEXT를 구분.
- "같은 입력을 유출 목록, SIEM, Omija가 어떻게 다르게 보는가"를 비교.

설명:

> 이 화면은 사건 발생 후 보고서입니다. 핵심은 데이터 양이 아니라 경로입니다. 협력사
> 계정이 원청 자산을 향하고, 그 경로가 프로그램까지 닿는지 보여줍니다.

### 6.5 프로그램 역방향 뷰

파일:

```text
out/program_threat_view.html
```

목적:

- 공급사에서 프로그램으로 가는 forward view가 아니라, 프로그램에서 위험 공급사를
  역추적하는 view.

발표에서의 위치:

- 시간 부족하면 생략 가능.
- 심사자가 "프로그램 책임자는 무엇을 보나?"라고 물을 때 보여주면 좋다.

설명:

> 앞 화면은 협력사에서 시작해 프로그램으로 올라갑니다. 이 화면은 반대로 프로그램에서
> 시작해 어떤 협력사와 사건이 위험을 만들었는지 내려갑니다. 같은 온톨로지를 반대로
> 질의한 것입니다.

### 6.6 공개 context snapshot

파일:

```text
out/public_context/summary.md
out/public_context/summary.json
docs/open-data-catalog.md
```

현재 확보한 공개 context:

```text
CISA KEV total: 1631
CISA KEV access-relevant: 863
MITRE ATT&CK selected techniques: 234
URLhaus sampled rows: 1000
URLhaus stealer/loader-tagged sample count: 42
HIBP public breach metadata count: 1015
NVD vpn/sso/citrix/fortinet/ivanti query totals: 73 / 25 / 309 / 672 / 379
```

주의:

이 데이터는 자격증명 증거가 아니라 context다. 즉 "왜 VPN/SSO/mail/dev 자산을 감시해야
하는가"를 설명하는 공개 배경이다.

## 7. 발표 추천 순서

### 1단계. 문제 제기

말할 것:

> 방산 공급망에서는 말단 협력사의 계정 하나가 원청 프로그램까지 이어질 수 있습니다.
> 문제는 유출 목록만 봐서는 그 경로를 알 수 없다는 점입니다.

### 2단계. 온톨로지 구축 근거

Foundry Ontology Manager 캡처를 보여준다.

말할 것:

> 그래서 먼저 데이터를 테이블로 나열하지 않고, 객체와 링크로 만들었습니다. 계정의
> 소속과 접근 대상 자산을 분리했고, 하도급 체인은 재귀 링크로 표현했습니다.

### 3단계. 데이터 커버리지 맵

`out/data_coverage_map.html`을 연다.

말할 것:

> 이 화면은 Omija가 무엇을 관리하고 무엇을 의도적으로 보지 않는지 보여줍니다. 회색은
> synthetic seed, 노란색은 공개 context, 초록은 엔진 계산, 파란색은 Foundry readback,
> 잠긴 구역은 민감 feed slot입니다.

### 4단계. 평시 콘솔

`out/omija_console_home.html`을 연다.

말할 것:

> 사건이 없을 때 분석가가 보는 화면입니다. 단순히 "0건"이 아니라, 어떤 범위를 봤고
> 왜 조용한지, 어떤 feed가 승인 대기인지, 어떤 상태 전이가 감사로 남는지 보여줍니다.

### 5단계. 사건 발생 시

`out/omija_demo.html`을 연다.

말할 것:

> 이제 후보 신호가 들어왔다고 가정합니다. Omija는 CredentialExposure를 Identity에
> 연결하고, 동시에 target Domain을 따로 봅니다. 그 다음 Supplier 체인을 따라 Prime과
> Program까지 닿는지 계산합니다.

### 6단계. 선택: 프로그램 역방향 뷰

`out/program_threat_view.html`을 연다.

말할 것:

> 프로그램 책임자 관점에서는 "내 프로그램에 영향을 주는 협력사와 사건이 무엇인가"가
> 중요합니다. 이 화면은 같은 그래프를 반대로 질의한 것입니다.

## 8. StealthMole 설명 문장

짧은 버전:

> StealthMole은 Omija의 감지 레이어가 아니라 데이터 공급 레이어입니다. CL은 유출
> 자격증명, CDS는 인포스틸러 감염 기기, DT/TT는 다크웹과 텔레그램 provenance를
> 제공합니다. Omija는 이 신호를 받아 Foundry 온톨로지에서 경로와 우선순위를 판단합니다.

긴 버전:

> StealthMole이 이미 다크웹과 유출 데이터를 수집합니다. Omija는 그 데이터를 직접
> 보여주는 것이 아니라, 어댑터 경계에서 정규화하고 마스킹한 뒤 Foundry 온톨로지에
> 올립니다. CL은 CredentialExposure로, CDS는 InfectedDevice와 활성 판단 근거로,
> DT/TT는 ThreatSource와 provenance로 들어갑니다. 그 다음 Omija가 of, targets,
> subcontractsTo, traverses, cites 링크를 따라 어느 프로그램까지 위험이 이어지는지
> 계산합니다.

## 9. 차별성

### 일반 유출 조회 서비스

- "이 도메인에 유출 계정이 몇 개 있다"를 보여준다.
- 볼륨 중심.
- 공급망 영향과 프로그램 blast radius는 별도 분석이 필요하다.

### SIEM

- 알림은 많지만, 방산 공급망 관계를 기본으로 알지 못한다.
- 원청/협력사/프로그램 관계는 별도 enrichment가 필요하다.

### Omija

- 계정 소속과 접근 대상 자산을 분리한다.
- 공급망 체인을 재귀적으로 탄다.
- 활성 침해 조건이 성립하면 volume보다 우선한다.
- 판단 객체와 근거 링크를 남긴다.
- 통보는 자동 발송하지 않고 사람 검토 초안으로 남긴다.

핵심 문장:

> 차이는 feed가 아니라 ontology입니다. 같은 신호라도 Omija는 "누가 털렸나"가 아니라
> "그 신호가 어느 프로그램을 위험하게 만드는가"를 묻습니다.

## 10. 예상 질문과 답변

### Q1. 데이터가 가짜인데 무엇을 증명했나?

개체는 가상이지만 시스템은 진짜다. 실제 유출 자격증명은 공개 시연에 올릴 수 없기
때문에 synthetic으로 대체했다. 대신 온톨로지 구조, 엔진 계산, Foundry readback, 공개
context snapshot, 상태 전이 감사는 실제로 실행된다.

### Q2. StealthMole 실데이터는 쓸 수 있나?

역할상 쓸 수 있는 입력단이다. 다만 발표/호스팅 화면에는 실유출 데이터를 올리지 않는다.
승인된 환경에서는 adapter boundary에서 정규화/마스킹 후 같은 온톨로지 경로로 들어오게
된다.

### Q3. 공개 데이터는 어디에 쓰이나?

CISA KEV/NVD/MITRE/URLhaus/HIBP는 자격증명 증거가 아니라 public context다. VPN, SSO,
mail, dev 같은 자산을 왜 봐야 하는지 설명하고 `RiskAssessment.components`나
`ProgramExposure.components`에 붙일 수 있다.

### Q4. 왜 자동 통보를 안 하나?

방산/CERT 맥락에서는 사람이 검토해야 한다. Omija는 `NotificationDraft`까지만 만들고,
`cites` 링크로 근거를 남긴다. 자동 발송 기능은 의도적으로 없다.

### Q5. 역방향 뷰는 왜 필요한가?

필수 발표 화면은 아니다. 다만 프로그램 책임자가 "내 프로그램 관점에서 위험 협력사가
누구인가"를 물을 때 필요하다. 공급사에서 프로그램으로 가는 질의와 프로그램에서 공급사로
내려오는 질의가 같은 온톨로지에서 가능하다는 증거다.

## 11. 발표 파일 순서

권장 순서:

```text
1. Foundry Ontology Manager 캡처
2. out/data_coverage_map.html
3. out/omija_console_home.html
4. out/omija_demo.html
5. out/program_threat_view.html (선택)
```

보조 문서:

```text
docs/open-data-catalog.md
docs/data-insertion-guide.md
docs/presentation-flow.md
docs/demo-script.md
```

## 12. 마지막 클로징

마지막에는 이렇게 닫으면 된다.

> Omija는 다크웹 데이터 뷰어가 아닙니다. 유출 신호가 들어왔을 때 그 신호가 공급망
> 어디를 지나 어느 프로그램을 위험하게 만드는지 계산하는 온톨로지 기반 운영 시스템입니다.
> 실제 자격증명은 화면에 올리지 않지만, 그 데이터를 받아 판단할 구조와 워크플로는 이미
> 만들어져 있습니다.
