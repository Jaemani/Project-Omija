# Omija Presentation Guide

발표자가 이 문서 하나만 읽어도 프로젝트의 취지, 온톨로지 설계 이유, StealthMole의 역할, 데이터 경계, 데모 화면 순서를 설명할 수 있게 정리한 가이드다.

## 0. 한 문장 요약

Omija는 다크웹/유출 자격증명 데이터를 보여주는 뷰어가 아니라, 그런 신호가 들어왔을 때 **방산 공급망 온톨로지 위에서 어느 협력사, 어느 자산, 어느 원청, 어느 프로그램까지 위험이 전파되는지 판단하고 조치 초안을 만드는 의사결정 시스템**이다.

발표 핵심 문장:

> 실제 유출 자격증명은 피해자 데이터라서 공개 시연에 올릴 수 없습니다. 그래서 기업과 자격증명 개체는 synthetic으로 두고, 시스템 자체는 실제로 구축했습니다. 신호가 들어오면 Omija는 그 신호가 어느 프로그램을 위험하게 만드는지 온톨로지 경로로 판단합니다.

## 1. 문제 정의

방산 공급망에서는 원청만 방어한다고 충분하지 않다. 1차·2차 협력사의 계정 하나가 VPN, SSO, mail, dev 자산을 통해 원청이나 프로그램 위험으로 이어질 수 있다.

일반적인 유출 계정 목록은 다음 질문에 답하지 못한다.

```text
계정이 누구 것인가?
계정이 접근하려는 자산은 누구 것인가?
그 협력사는 어느 원청과 프로그램에 연결되는가?
이 신호는 오래된 재유통인가, 활성 침해 정황인가?
어떤 근거로 누가 조치 상태를 바꿨는가?
```

Omija는 이 질문에 답하기 위해 테이블이 아니라 온톨로지로 문제를 모델링했다.

## 2. 왜 온톨로지가 필요한가

### 2.1 `of`와 `targets` 분리

가장 중요한 설계는 `CredentialExposure.of Identity`와 `CredentialExposure.targets Domain`을 분리한 것이다.

- `of`: 유출된 계정이 누구의 계정인가.
- `targets`: 그 계정이 접근하려는 자산이 무엇인가.

두 값은 같은 조직일 수도 있지만, 방산 공급망에서는 다를 수 있다.

```text
협력사 직원 계정(of: Supplier Identity)
  -> 원청 VPN(targets: Prime Domain)
```

flat table은 보통 회사, 도메인, 계정을 한 행에 뭉개기 때문에 이런 교차 조직 위험을 표현하기 어렵다. Omija는 소속과 접근 대상을 링크로 분리했기 때문에 활성 경로를 계산할 수 있다.

### 2.2 `subcontractsTo` 가변 깊이

공급망은 항상 1단계가 아니다.

```text
Supplier(T2) -> Supplier(T1) -> Prime -> Program
```

그래서 `Supplier.subcontractsTo Supplier`는 고정 컬럼이 아니라 재귀적으로 순회해야 하는 링크다. 이 구조가 있어야 말단 협력사의 신호가 어떤 원청/프로그램까지 닿는지 계산할 수 있다.

### 2.3 판단 객체

Omija는 점수 숫자만 만들지 않는다.

- `RiskAssessment`: 협력사 단위 위험 판단.
- `CompromiseIncident`: 활성 침해 경로가 성립한 사건.
- `ProgramExposure`: 프로그램 단위 영향 롤업.
- `NotificationDraft`: 사람 검토가 필요한 통보 초안.

객체가 있어야 "왜 판단이 나왔는지", "어떤 근거를 봤는지", "누가 상태를 바꿨는지"가 남는다.

### 2.4 경로와 근거 링크

- `traverses_identity`
- `traverses_asset`
- `traverses_supplier`
- `traverses_prime`
- `traverses_program`
- `cites`

이 링크들은 사건과 통보 초안이 어떤 근거와 경로를 갖는지 남긴다. 발표에서는 "Omija는 알림을 던지는 시스템이 아니라, 판단 경로와 조치 근거를 남기는 시스템"이라고 설명하면 된다.

## 3. StealthMole이 Omija에서 하는 역할

StealthMole은 Omija의 입력 공급원이다. 감지와 수집은 입력 공급원이 맡고, Omija는 그 신호를 온톨로지 경로 위에서 해석한다.

```text
StealthMole
  -> Adapter boundary
  -> Foundry Ontology
  -> Graph reasoning
  -> Decision objects
```

### 3.1 Credential Lookout (CL)

역할: 도메인 기반 유출 자격증명 후보.

Omija 객체:

```text
CL signal -> CredentialExposure -> of Identity -> belongs_to Domain / Supplier
```

발표 포인트: CL은 "어느 협력사 계정이 노출됐는가"의 출발점이다. 하지만 이것만으로는 위험 우선순위가 나오지 않는다. Omija는 그 계정이 어떤 자산을 향하는지, 어느 프로그램과 연결되는지를 계산한다.

### 3.2 Compromised Data Set (CDS)

역할: 인포스틸러 감염 기기에서 나온 단서.

Omija 객체:

```text
CDS signal -> InfectedDevice -> leaked CredentialExposure -> active compromise precondition
```

활성 판단에서 중요한 구조적 단서:

```text
recent infected_at
has_session_cookie
account_type in vpn/admin
```

발표 포인트: 오래된 유출과 최근 감염 기반 활성 위험은 대응 우선순위가 다르다. CDS 계열 신호는 Omija가 `CompromiseIncident`로 격상할지 판단하는 핵심 입력이다.

### 3.3 Darkweb Tracker (DT)

역할: 다크웹 포럼·마켓에서 협력사, 자산, 키워드 언급을 추적하는 provenance.

Omija 객체:

```text
DT signal -> ThreatSource
```

발표 포인트: DT는 단독 결론이 아니라 "이 신호가 어떤 위협 생태계 문맥에서 반복되는가"를 보강한다.

### 3.4 Telegram Tracker (TT)

역할: 텔레그램 채널의 유출·거래 정황.

Omija 객체:

```text
TT signal -> ThreatSource
```

발표 포인트: TT는 보조 출처 다양화와 반복 언급 확인에 쓴다. 최종 우선순위는 출처 개수가 아니라 온톨로지 경로와 활성 조건으로 결정된다.

## 4. 데이터 경계

### 진짜인 것

- Foundry에 구축한 온톨로지 구조.
- Object Type과 Link Type 설계.
- `of`, `targets`, `subcontractsTo`, `traverses_*`, `cites` 구조.
- 스코어링/경로/전파/역질의 엔진.
- 공개 context snapshot.
- Foundry action/readback audit evidence.
- HTML 운영 화면과 사건 화면 산출.

### Synthetic인 것

- 협력사 이름.
- 도메인.
- 계정.
- 자격증명.
- 감염 기기.

### 왜 synthetic이어야 하는가

실제 유출 자격증명은 피해자 데이터다. 공개 데모, GitHub Pages, 발표 녹화에 올리는 순간 새로운 노출 표면이 된다. 그래서 개체 데이터는 synthetic으로 두고, 시스템 구조와 판단 엔진을 증명한다.

### 공개 데이터의 역할

공개 데이터는 자격증명 증거가 아니라 배경 context다.

현재 snapshot:

```text
CISA KEV total: 1631
CISA KEV access-relevant: 863
MITRE ATT&CK selected techniques: 234
URLhaus sampled rows: 1000
URLhaus stealer/loader-tagged sample count: 42
HIBP public breach metadata count: 1015
NVD vpn/sso/citrix/fortinet/ivanti query totals: 73 / 25 / 309 / 672 / 379
```

발표에서는 "공개 데이터는 왜 VPN/SSO/mail/dev 자산을 감시해야 하는지 설명하는 배경이고, 자격증명 판단 자체는 승인된 입력 공급원과 온톨로지 경로가 담당한다"고 말한다.

## 5. 화면별 역할

### 5.1 Foundry Ontology Manager 캡처

목적: 실제로 온톨로지를 만들었다는 증거.

보여줄 것:

- `Supplier`, `Domain`, `Identity`, `CredentialExposure`, `InfectedDevice`.
- `RiskAssessment`, `CompromiseIncident`, `ProgramExposure`, `NotificationDraft`.
- `of`, `targets`, `subcontractsTo`, `supplies`, `runs`, `traverses_*`, `cites`.

### 5.2 StealthMole 역할 맵

파일:

```text
out/stealthmole_role_map.html
```

목적: 입력 공급원이 어떤 온톨로지 객체로 정규화되는지 보여준다.

설명:

> StealthMole은 신호를 제공하고, Omija는 그 신호를 방산 공급망 경로 위에서 판단합니다. CL은 `CredentialExposure`, CDS는 `InfectedDevice`, DT/TT는 `ThreatSource`로 들어오고, Omija는 이를 decision object로 바꿉니다.

### 5.3 데이터 커버리지 맵

파일:

```text
out/data_coverage_map.html
```

목적: 어디서 어떤 데이터가 관리되는지 한눈에 보여준다. synthetic seed, public context, engine result, live readback, locked sensitive slot을 색으로 구분한다.

설명:

> 이 화면은 지금 시스템이 무엇을 보고 있고 무엇을 일부러 잠가두었는지 보여줍니다. 가상 데이터, 공개 데이터, 엔진 산출, 민감 입력 슬롯이 섞이지 않게 분리되어 있습니다.

### 5.4 평시 콘솔

파일:

```text
out/omija_console_home.html
```

목적: 사건이 없을 때 분석가가 켜놓는 기본 화면. 감시 범위, 조용함의 증명, 피드 상태, action audit stream을 보여준다.

설명:

> 이 화면은 사건 보고서 생성기가 아니라 운영 시스템이라는 점을 보여줍니다. 조용하다는 것은 아무것도 보지 않았다는 뜻이 아니라, 정해진 범위를 보고 있고 활성 경로가 없다는 뜻입니다.

### 5.5 사건 보고서

파일:

```text
out/omija_demo.html
```

목적: 문제가 생겼을 때 Omija가 어떤 경로와 근거를 보여주는지 설명한다.

설명:

> 핵심은 데이터 양이 아니라 경로입니다. 협력사 계정이 원청 자산을 향하고, 공급망 체인을 통해 프로그램까지 닿는지를 보여줍니다.

### 5.6 프로그램 역방향 뷰

파일:

```text
out/program_threat_view.html
```

목적: 프로그램 책임자 관점에서 위험 협력사와 사건을 역추적한다.

발표에서의 위치: 시간 부족하면 생략 가능. 심사자가 "프로그램 책임자는 무엇을 보나?"라고 물을 때 보여준다.

설명:

> 앞 화면은 협력사에서 프로그램으로 올라갑니다. 이 화면은 반대로 프로그램에서 시작해 어떤 협력사와 사건이 위험을 만들었는지 내려갑니다. 같은 온톨로지를 반대로 질의한 것입니다.

## 6. 추천 발표 순서

```text
1. 문제 제기
2. Foundry Ontology Manager 캡처
3. out/stealthmole_role_map.html
4. out/data_coverage_map.html
5. out/omija_console_home.html
6. out/omija_demo.html
7. out/program_threat_view.html (질문이 있을 때 선택)
```

## 7. 3분 발표 스크립트

### 0:00-0:25 문제 제기

방산 공급망에서는 말단 협력사의 계정 하나가 원청 프로그램까지 이어질 수 있습니다. 단순 유출 목록은 "누가 털렸나"만 보여주고, 그 계정이 어떤 자산을 향하고 어떤 프로그램 위험으로 이어지는지는 알려주지 않습니다.

### 0:25-0:55 온톨로지

그래서 Omija는 데이터를 테이블로만 두지 않고 Foundry 온톨로지로 만들었습니다. 핵심은 `of`와 `targets`를 분리한 것입니다. 협력사 계정이 원청 VPN을 향할 수 있기 때문입니다. 또 `subcontractsTo`로 2차 협력사에서 1차 협력사, 원청, 프로그램까지 이어지는 경로를 계산합니다.

### 0:55-1:20 입력 공급원 역할

StealthMole은 입력 공급원입니다. CL은 `CredentialExposure`, CDS는 `InfectedDevice`, DT/TT는 `ThreatSource`로 들어옵니다. Omija의 역할은 그 신호를 그대로 보여주는 것이 아니라, 온톨로지 경로와 활성 조건을 적용해 어떤 협력사와 프로그램을 먼저 봐야 하는지 판단하는 것입니다.

### 1:20-1:45 데이터 경계

실제 유출 자격증명은 피해자 데이터라서 공개 화면에 올릴 수 없습니다. 그래서 개체 데이터는 synthetic으로 두고, 공개 데이터는 VPN/SSO 같은 자산 위험의 배경 context로만 씁니다. 화면의 칩과 맵은 synthetic, public context, engine output, locked sensitive slot을 분리해서 보여줍니다.

### 1:45-2:15 평시 운영

평시 콘솔은 사건이 없을 때의 화면입니다. 어떤 공급망 범위를 감시하고 있고, 어떤 입력은 잠겨 있으며, 조용함이 "안 본 것"이 아니라 "봤는데 활성 경로가 없는 것"임을 보여줍니다.

### 2:15-2:50 사건 발생

사건 화면에서는 같은 신호를 단순 유출량으로 정렬하지 않습니다. 최근 감염, 세션 존재, VPN/admin 계정, 교차 조직 target, 공급망 경로가 성립하면 `CompromiseIncident`로 격상하고, `RiskAssessment`, `ProgramExposure`, `NotificationDraft`까지 만듭니다.

### 2:50-3:00 클로징

Omija는 다크웹 데이터 뷰어가 아닙니다. 유출 신호가 들어왔을 때 그 신호가 공급망 어디를 지나 어느 프로그램을 위험하게 만드는지 계산하는 온톨로지 기반 운영 시스템입니다.

## 8. 차별점

### 유출 목록 뷰어

- 계정과 도메인 목록을 보여준다.
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

> 차이는 feed가 아니라 ontology입니다. 같은 신호라도 Omija는 "누가 털렸나"가 아니라 "그 신호가 어느 프로그램을 위험하게 만드는가"를 묻습니다.

## 9. 예상 질문과 답변

### Q1. 데이터가 synthetic이면 무엇을 증명했나?

개체는 synthetic이지만 시스템은 진짜다. 실제 유출 자격증명은 공개 시연에 올릴 수 없기 때문에 synthetic으로 대체했고, 온톨로지 구조, 경로 탐색, 스코어링, 상태 전이, 감사 가능한 판단 객체를 증명했다.

### Q2. StealthMole이 있으면 Omija가 왜 필요한가?

StealthMole은 신호를 제공한다. Omija는 그 신호가 방산 공급망에서 어떤 의미인지 판단한다. CL/CDS/DT/TT가 각각 객체로 들어와도, `of`, `targets`, `subcontractsTo`, `traverses_*` 경로가 없으면 프로그램 영향과 조치 우선순위를 계산하기 어렵다.

### Q3. 공개 데이터는 어떤 역할인가?

CISA KEV/NVD/MITRE/URLhaus/HIBP는 자격증명 증거가 아니라 배경 context다. VPN, SSO, firewall, mail, dev 같은 자산이 왜 감시 대상인지 설명하고, `RiskAssessment.components`나 `ProgramExposure.components`에 들어갈 수 있다.

### Q4. 왜 자동 통보를 안 하나?

방산/CERT 맥락에서는 사람이 검토해야 한다. Omija는 `NotificationDraft`까지만 만들고, `cites` 링크로 근거를 남긴다. 자동 발송 기능은 의도적으로 없다.

### Q5. 역방향 뷰는 왜 필요한가?

필수 발표 화면은 아니다. 다만 프로그램 책임자가 "내 프로그램 관점에서 위험 협력사가 누구인가"를 물을 때 필요하다. 공급사에서 프로그램으로 가는 질의와 프로그램에서 공급사로 내려오는 질의가 같은 온톨로지에서 가능하다는 증거다.

## 10. 파일과 링크

로컬 파일:

```text
ontology.md
out/stealthmole_role_map.html
out/data_coverage_map.html
out/omija_console_home.html
out/omija_demo.html
out/program_threat_view.html
docs/stealthmole-role-map.md
docs/open-data-catalog.md
docs/data-insertion-guide.md
docs/presentation-flow.md
docs/demo-script.md
```

GitHub raw.githack 링크:

```text
https://raw.githack.com/Jaemani/Project-Omija/main/out/stealthmole_role_map.html
https://raw.githack.com/Jaemani/Project-Omija/main/out/data_coverage_map.html
https://raw.githack.com/Jaemani/Project-Omija/main/out/omija_console_home.html
https://raw.githack.com/Jaemani/Project-Omija/main/out/omija_demo.html
https://raw.githack.com/Jaemani/Project-Omija/main/out/program_threat_view.html
```

## 11. 남은 수동 준비

- Foundry Ontology Manager 화면 캡처를 발표 자료 첫 부분에 넣기.
- Object Explorer에서 `Supplier`, `CredentialExposure`, `CompromiseIncident`, `NotificationDraft`가 연결되는 장면 캡처.
- 민감 입력 공급원은 실제 데이터 화면 대신 역할 맵과 locked slot으로 설명하기.
- 발표 중에는 "실데이터를 안 쓴 것"을 약점이 아니라 안전한 데모 설계로 설명하기.

## 12. 마지막 클로징

> Omija는 다크웹 데이터 뷰어가 아닙니다. 유출 신호가 들어왔을 때 그 신호가 공급망 어디를 지나 어느 프로그램을 위험하게 만드는지 계산하는 온톨로지 기반 운영 시스템입니다. 실제 자격증명은 화면에 올리지 않지만, 그 데이터를 받아 판단할 구조와 워크플로는 이미 만들어져 있습니다.
