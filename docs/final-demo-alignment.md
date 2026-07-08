# Final Demo Alignment

작성일: 2026-07-05. 본선 대비 기준 문서다. 웹, 데이터, 발표, 캡처 설명은 이 문서를 기준으로 맞춘다.

## 1. 한 줄 정의

Omija는 방산 공급망의 유출 자격증명 후보와 인포스틸러 감염기기 후보를 공급망 온톨로지에 연결해, 어떤 협력사와 프로그램을 먼저 확인해야 하는지 근거 경로와 함께 제시하는 조기경보 의사결정 시스템이다.

Omija는 침해 확정 시스템이 아니라, 외부에서 관측된 후보 신호를 분석관의 우선순위 판단으로 바꾸는 시스템이다.

## 2. 최종 데이터 정책

| 데이터 층 | 사용 방식 | 공개 artifact에 표시 가능 | 금지 |
| --- | --- | --- | --- |
| 공개 OSINT | 실제 공개 스냅샷 | CISA KEV, NVD, EPSS, CISA RSS, MITRE ATT&CK, URLhaus aggregate, HIBP breach metadata | 개인 credential 원문처럼 오해되는 표시 |
| StealthMole 해커톤 API | 승인된 filtered row를 사용 | module status, returned/written count, source_ref hash, normalized object/link lineage, account class, boolean flags, timestamps | API key, JWT, raw provider envelope, password, cookie, token, full account dump |
| Synthetic incident | reasoning 검증용 사건 | supplier/program/credential/device 가상 개체, active-on-top 결과, notification draft | 실제 침해 확정처럼 표현 |
| Foundry evidence | 온톨로지/액션 증명 | objects list, action types, OSDK screen, of/targets backing dataset lineage, action readback | Foundry E2E가 완전 해결됐다고 과장 |

발표 문장:

> 공개 OSINT는 실제 스냅샷으로 쓰고, StealthMole 해커톤 API는 이미 필터링된 승인 데이터를 row-level lineage로 보여줍니다. 다만 API key, JWT, raw provider payload, password/cookie/token은 공개 산출물에 남기지 않습니다. 사건 자체는 synthetic이지만, 데이터가 온톨로지 객체와 판단 객체로 바뀌는 파이프라인은 구현되어 있습니다.

## 3. StealthMole 위치

StealthMole은 Omija의 탐지 엔진이 아니라 입력단이다. Omija는 StealthMole이 수집한 외부 노출 후보를 받아 공급망 온톨로지와 상관분석한다.

| 모듈 | Omija 객체 | 쓰임 |
| --- | --- | --- |
| CL Credential Lookout | `CredentialExposure` | 협력사 도메인/계정 유출 후보의 출발점 |
| CDS Compromised Data Set | `InfectedDevice`, `CredentialExposure` | 감염 시점, 세션 쿠키 존재 boolean, VPN/admin 계정 유형 같은 active 후보 입력 |
| DT Darkweb Tracker | `ThreatSource` | 다크웹 언급 맥락과 provenance 보강 |
| TT Telegram Tracker | `ThreatSource` | 텔레그램 유출·거래 정황 보조 근거 |

현재 상태:

- CL/CDS/CB: 해커톤 API 연결 및 filtered row 반환 확인.
- DT: 현재 계정/스코프에서 403.
- TT: 현재 path/module 기준 404.
- 공개 산출물에는 raw secret과 raw provider envelope을 넣지 않는다.

## 4. 웹 발표 순서

1. `out/omija_console_home.html`
   평시 콘솔. 감시 범위, 조용함의 증명, provider readiness, Foundry action readback을 보여준다.

2. `out/data_coverage_map.html`
   무엇을 어디서 관리하고 무엇으로 감시하는지 큰 지도. synthetic seed, public context, engine/live evidence, sensitive provider rail을 분리해 보여준다.

3. `out/data_evidence_brief.html`
   공개 OSINT와 승인된 StealthMole 해커톤 API 경계. "실제 공개 데이터 + filtered provider row + 금지 필드"를 짧게 설명한다.

4. `out/data_lineage_live.html`
   본선 핵심 보강 페이지. provider module -> raw/private -> redaction -> normalized ontology rows -> engine gate -> Foundry measurement 흐름을 보여준다. 이 live run은 active/path 조건이 없어 decision 객체를 만들지 않았고, 그 경계도 같이 설명한다.

5. `out/omija_demo.html`
   사건 보고서. active-on-top, of/targets, blast radius, notification draft를 설명한다.

6. `out/program_threat_view.html`
   Q&A 백업. 프로그램에서 역으로 어떤 supplier/exposure 경로가 걸리는지 설명할 때만 사용한다.

## 5. 발표 흐름

3분 안에서는 페이지 기준으로 간다.

1. 평시 콘솔: "사건 후 보고서가 아니라 운영 콘솔이다."
2. 커버리지/데이터 증거: "무엇을 감시하고, 어떤 데이터가 실제/filtered/synthetic인지 구분한다."
3. 데이터 계보: "StealthMole 해커톤 API row가 redaction을 지나 온톨로지 객체와 판단 객체로 간다."
4. 사건 보고서: "그래프 경로와 active 조건으로 우선순위를 만든다."
5. Foundry 캡처: "온톨로지와 액션 workflow가 실제로 구성되어 있다."
6. 한계: "Band A는 침해 확정이 아니라 verify-first 후보이며, 내부 로그/협력사 확인이 필요하다."

## 6. Foundry 캡처 체크

필수 3장:

- `out/captures/objects-list.png`: Ontology Manager object types. 목적은 13개 객체 구조 증명.
- `out/captures/action-types.png`: acknowledge/assign/close, review/approve/export, confirm/reject. 목적은 human-reviewed workflow 증명.
- `out/captures/osdk-020.png`: Developer Console / SDK. 목적은 코드 접근 가능한 ontology임을 증명.

있으면 좋은 추가 3장:

- `out/captures/link-graph.png`: of/targets/subcontractsTo 관계.
- `out/captures/merged-proposal.png`: 사람이 승인해 반영된 proposal.
- `out/captures/incident-history.png`: 상태 전이 history.

주의 문장:

> Foundry에는 온톨로지 구조와 action workflow를 구성했고, MCP로 of/targets backing dataset lineage와 일부 action readback을 확인했습니다. 다만 일부 seed dataset schema 정비가 남아 있어 Foundry 전체 E2E reasoning 완료라고 말하지는 않습니다.

## 7. Claude에게 넘길 웹 수정 요청

```text
1. data_evidence_brief.html / data_lineage_live.html 문구를 예전 잠금 중심 표현이 아니라 "approved filtered hackathon API row-level lineage"로 맞춰줘.
2. data_coverage_map.html의 민감 feed 노드는 "locked/not queried"보다 "approved provider rail / raw secret blocked"로 바꿔줘.
3. omija_console_home.html의 P5도 "empty locked slot"보다는 "approved connector boundary"로 바꿔줘. 단 raw secret/export 금지는 유지.
4. 390/768/1280 반응형 검증 계속. 표는 카드형 또는 가로 스크롤, SVG는 overflow-x 컨테이너.
5. 프로그램 역방향 뷰는 메인 발표 흐름이 아니라 Q&A backup처럼 비중 낮춰도 됨.
```

## 8. Do Not Claim

- 실제 침해를 확정했다.
- 실제 password/cookie/token을 저장하거나 보여준다.
- `targets`가 로그인 성공을 의미한다.
- Foundry full E2E reasoning readback이 완전히 해결됐다.
- 자동 통보/자동 발송이 구현됐다.

안전한 표현:

- "approved filtered StealthMole hackathon API lineage"
- "active compromise candidate"
- "verification priority"
- "synthetic incident scenario"
- "public OSINT context snapshot"
- "human-reviewed notification draft"
