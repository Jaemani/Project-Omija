# StealthMole Role Map

이 문서는 StealthMole을 Omija의 "판단 엔진"이 아니라 "입력 공급원"으로 설명하기 위한 발표용 맥락이다. 민감 데이터 탐색이나 실데이터 표시를 전제로 하지 않는다.

## 핵심 결론

StealthMole은 다크웹·유출 데이터 쪽에서 신호를 모으는 입력단이다. Omija의 차별점은 그 신호를 그대로 보여주는 것이 아니라, Foundry 온톨로지 위에서 소속, 접근 대상, 공급망 경로, 프로그램 영향, 사람 검토 액션으로 바꾸는 데 있다.

```text
StealthMole modules
  -> Adapter boundary
  -> Foundry ontology objects
  -> graph reasoning
  -> decision objects
```

## Module Mapping

| Module | 입력 의미 | Omija 객체 | 판단에서의 역할 |
|---|---|---|---|
| Credential Lookout (CL) | 도메인 기반 유출 계정 후보 | `CredentialExposure` | "누구의 계정이 노출됐는가"의 출발점 |
| Compromised Data Set (CDS) | 인포스틸러 감염 기기 단서 | `InfectedDevice` | 최근 감염, 세션 존재, VPN/admin 계정 같은 활성 침해 격상 입력 |
| Darkweb Tracker (DT) | 포럼·마켓 언급 맥락 | `ThreatSource` | 위협 행위자/거래 정황 provenance 보강 |
| Telegram Tracker (TT) | 텔레그램 유출·거래 언급 | `ThreatSource` | 반복 출처와 보조 근거 다양화 |

## Why Omija Still Needs Ontology

CL만 있으면 유출 계정 목록이다. CDS만 있으면 감염 기기 목록이다. DT/TT만 있으면 출처 맥락이다. Omija는 이 신호들을 다음 질문으로 바꾼다.

```text
CredentialExposure.of Identity
CredentialExposure.targets Domain
Identity.belongs_to Domain / Supplier
Supplier.subcontractsTo Supplier
Supplier.supplies Prime
Prime.runs Program
CompromiseIncident.traverses_*
NotificationDraft.cites
```

이 구조 때문에 협력사 계정이 원청 VPN을 향하는 교차 조직 위험을 표현할 수 있고, 2차 협력사에서 시작한 신호가 어떤 프로그램까지 닿는지 계산할 수 있다.

## Safe Demo Boundary

발표와 호스팅 페이지에서 실제 계정, 비밀번호, 쿠키, 세션 원문을 표시하지 않는다. 실제 입력 공급원이 연결되는 경우에도 데모 표면에서는 마스킹·집계·상태 전이 결과만 다룬다.

현재 데모의 설명 방식:

- 개체 데이터: synthetic seed.
- 공개 context: CISA KEV, NVD, MITRE ATT&CK, URLhaus aggregate, HIBP breach metadata.
- 엔진 산출: risk band, incident path, program exposure, notification draft.
- 민감 입력: locked slot으로만 표현.

## Visual Page

생성 명령:

```bash
uv run python scripts/stealthmole_role_map.py
```

출력:

```text
out/stealthmole_role_map.html
```

발표 위치는 온톨로지 캡처 직후가 가장 좋다. 온톨로지 구조를 보여준 다음, "그 구조로 어떤 입력 신호를 받아 어떤 판단 객체로 바꾸는가"를 이 화면으로 설명한다.
