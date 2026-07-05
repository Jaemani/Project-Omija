# Final Demo Alignment

작성일: 2026-07-05

이 문서는 최종 발표 직전 기준으로 Omija의 의도, 데이터 사용, 웹 구성, 발표 흐름, 캡처 작업을 맞추기 위한 단일 기준이다.

## 1. 한 줄 정의

Omija는 방산 공급망의 유출 자격증명 후보와 인포스틸러 감염기기 후보를 공급망 온톨로지에 연결해, 어떤 협력사와 프로그램을 먼저 확인해야 하는지 근거 경로와 함께 제시하는 조기경보 의사결정 시스템이다.

Omija는 침해 확정 시스템이 아니다. 외부에서 관측된 후보 신호를 분석관의 우선순위 판단으로 바꾸는 시스템이다.

## 2. 핵심 논리

발표는 "데이터가 많다"가 아니라 "데이터를 결정으로 바꾼다"를 증명해야 한다.

단순 유출 레코드 테이블은 다음 질문에 약하다.

- 이 계정은 누구의 것인가?
- 이 계정이 관측된 대상 자산은 어디인가?
- 계정 소유 조직과 대상 조직이 다른가?
- 2차·3차 협력사에서 원청과 프로그램까지 이어지는가?
- 과거 대량 유출보다 최근 활성 감염 후보를 먼저 볼 수 있는가?
- 사람이 어떤 근거로 어떤 조치를 검토해야 하는가?

Omija의 답은 온톨로지다.

- `CredentialExposure.of`: 유출/노출이 누구의 계정인지.
- `CredentialExposure.targets`: 그 자격증명이 어떤 자산에 대해 관측됐는지.
- `Supplier.subcontractsTo*`: 2차 이하 협력사를 가변 깊이로 상위 협력사/원청까지 추적.
- `traverses_*`: 인시던트가 어떤 Identity, Domain, Supplier, Prime, Program을 지나가는지.
- `RiskAssessment`, `CompromiseIncident`, `ProgramExposure`, `NotificationDraft`: 판단 결과를 객체로 남김.

## 3. 데이터 경계

발표에서 데이터는 세 층으로 분리한다.

| 층 | 상태 | 웹 표시 방식 | 설명 |
|---|---|---|---|
| 공개 OSINT | 실제 공개 스냅샷 | 정적 페이지에 표시 가능 | CISA KEV, NVD, EPSS, CISA RSS, MITRE ATT&CK, URLhaus aggregate, HIBP breach metadata |
| StealthMole 민감 신호 | live-only | 정적 페이지에 원문 row 저장 금지 | 발표 현장 승인 query 때만 count/schema/sanitized preview로 표시 |
| 데모 사건 데이터 | synthetic | 사건 보고서에 표시 | 실제 조직/계정/비밀값이 아니라 온톨로지 reasoning 증명용 |

중요 문장:

> 실제 유출 원문을 데모 페이지나 GitHub Pages에 저장하지 않습니다. 공개 OSINT는 실제 스냅샷으로 쓰고, 민감 유출 신호는 live-only 경계에서 조회한 뒤 정규화·마스킹된 요약만 판단 파이프에 넣습니다. 사건 시나리오는 synthetic이지만, 온톨로지 구조와 엔진 로직은 실제 구현입니다.

## 4. StealthMole 위치

StealthMole은 판단 엔진이 아니라 입력 공급원이다.

| 모듈 | Omija landing object | 발표에서 말할 역할 |
|---|---|---|
| CL | `CredentialExposure` | 협력사 도메인/계정 유출 후보의 출발점 |
| CDS | `InfectedDevice`, `CredentialExposure` | 세션 쿠키 존재, 감염 시점, 계정 유형 같은 active 후보 입력 |
| DT | `ThreatSource` | 다크웹 언급 맥락, provenance 보강 |
| TT | `ThreatSource` | 텔레그램 유출/거래 정황 보조 근거 |

현재 기술 상태:

- CL/CDS/CB: synthetic seed 기준 API 경계 연결 확인.
- DT: 현재 계정/스코프에서 403.
- TT: 현재 path/module 확인 필요, 404.
- 실제 민감 row는 미리 수집하지 않는다.
- 정적 웹에는 raw password, cookie, token, full account dump, provider raw payload를 절대 넣지 않는다.

## 5. 웹 구성

발표 권장 순서:

1. `out/omija_console_home.html`
   - 평시 콘솔.
   - 감시 범위, 조용함의 증명, 피드 상태, Foundry action readback을 보여줌.
   - 여기서 "사건이 없어도 운영 화면이 있다"를 설명.

2. `out/data_coverage_map.html`
   - 무엇을 어디서 관리하고 감시하는지 큰 지도.
   - synthetic seed, 공개 context, engine/live evidence, sensitive slot의 차이를 보여줌.

3. `out/data_evidence_brief.html`
   - 공개 OSINT 실제 스냅샷과 StealthMole live-only 경계를 같이 보여주는 새 페이지.
   - 공개 데이터가 실제로 존재한다는 근거와, 민감 데이터는 정적 저장하지 않는다는 정책을 동시에 설명.

4. `out/omija_demo.html`
   - 사건 발생 시 보고서.
   - `of` vs `targets`, active-on-top, path evidence, notification draft를 설명.

5. `out/program_threat_view.html`
   - 프로그램 역방향 뷰.
   - 본 발표 핵심이 길어지면 Q&A 백업으로만 사용.

배포는 정적 산출물 `out/*.html` 기준이다. GitHub Pages, Vercel, 또는 로컬 `scripts/serve.py` 중 어떤 표면이든 같은 파일을 서빙하면 된다.

Vercel을 쓸 경우 권장값:

```text
Framework Preset: Other
Build Command: make build
Output Directory: out
Install Command: uv sync
```

현재 `vercel.json`은 `outputDirectory: "out"`과 루트 rewrite만 둔 정적 배포 설정이다. `buildCommand: null`이면 Vercel은 커밋된 `out/`을 그대로 서빙한다. Vercel UI에서 빌드를 돌릴 경우 위 값처럼 `make build`/`uv sync`를 설정한다.

## 6. 발표 흐름 수정

현재 대본은 방향은 맞지만 다음을 고쳐야 한다.

1. `System Architecture`가 두 번 나온다.
   - 앞쪽은 `Data Boundary & Pipeline`.
   - 뒤쪽은 `Implementation`.

2. 초반에 데이터 경계를 말해야 한다.
   - 공개 OSINT는 실제.
   - StealthMole 민감 row는 live-only.
   - 사건 시나리오는 synthetic.
   - 엔진/온톨로지는 실제 구현.

3. 화면 순서를 대본에 박아야 한다.
   - 평시 콘솔 -> 커버리지/데이터 증거 -> 사건 보고서 -> 결과/한계.

4. Foundry/OSDK 표현은 조심한다.
   - 현재 Foundry 백킹 데이터셋 schema 이슈가 있으므로 "Foundry 전체 readback 완전 검증"처럼 말하지 않는다.
   - 안전한 표현: "Foundry 온톨로지 구조와 action 흐름을 구성했고, 로컬 SQLite 엔진에서 동일한 온톨로지 로직을 검증했다. Foundry 백킹 데이터셋 schema 정비는 남아 있다."

5. `Band A`는 침해 확정이 아니라 즉시 확인 후보라고 반복한다.

6. `targets`는 실제 접근 성공을 뜻하지 않는다.
   - "우선 확인해야 할 대상 자산 경로"라고 말한다.

## 7. 발표 대본의 권장 재배열

1. Project Overview
2. Problem: 공급망에서는 유출 건수보다 우선순위가 어렵다
3. Why Tables Fail: owner/target 분리, 멀티티어 경로, active-on-top
4. Data Boundary: 공개 OSINT 실제, 민감 feed live-only, 사건 synthetic, 엔진 실제
5. Ontology Core: `of`, `targets`, `subcontractsTo*`, derived decision objects
6. Live/Static Demo Flow: 평시 콘솔과 커버리지 맵
7. Incident Scenario: 사건 보고서에서 경로와 Band A 설명
8. Results: synthetic evaluation 결과와 active 후보 상위 배치
9. Limitations: 침해 확정 아님, 내부 로그/협력사 확인 필요, 자동 발송 없음
10. Vision: 분석관이 감사 가능한 우선순위 결정을 하도록 지원

## 8. 캡처 체크리스트

발표 슬라이드나 사건 보고서 슬롯에 넣을 Foundry 캡처:

| 파일 | 찍을 화면 | 목적 |
|---|---|---|
| `out/captures/objects-list.png` | Ontology Manager 객체 13종 목록 | 온톨로지가 실제로 구성됐음을 증명 |
| `out/captures/link-graph.png` | 링크 그래프, 특히 `of`/`targets`가 보이게 | flat table이 아니라 관계 모델임을 증명 |
| `out/captures/action-types.png` | Action Types 목록 | CRUD가 아니라 시맨틱 상태 전이임을 증명 |
| `out/captures/merged-proposal.png` | 승인/머지된 proposal | human-on-the-loop 증명 |
| `out/captures/incident-history.png` | `CompromiseIncident` History 탭 | 감사 가능한 상태 전이 증명 |
| `out/captures/osdk-020.png` | Developer Console SDK 0.2.0 | 코드/OSDK 연결 가능성 증명 |

캡처를 넣은 뒤:

```bash
uv run python scripts/omija_demo.py
```

## 9. Claude에게 넘길 웹 수정 요청

아래는 그대로 전달하면 된다.

```text
1. 모바일/태블릿 반응형 검증은 390/768/1280 기준으로 계속 진행.
2. data_evidence_brief.html을 발표 흐름에 맞는 보조 페이지로 스타일 정리.
   - 공개 OSINT 실제 스냅샷과 StealthMole live-only 경계를 한 화면에서 보여줘.
   - 민감 row가 정적 저장된 것처럼 보이면 안 됨.
3. data_coverage_map.html의 민감 feed 노드는 "locked/not queried"보다 "live-only sensitive rail"로 표현.
4. omija_demo.html 상단/발표 노트에서 "사건은 synthetic, 공개 OSINT는 실제 스냅샷, 민감 feed는 live-only"를 더 명확히 구분.
5. 좁은 화면에서 표는 카드형으로 리플로우, SVG는 가로 스크롤 컨테이너 유지.
6. 프로그램 역방향 뷰는 메인 발표 흐름이 아니라 Q&A backup으로 보이게 과도한 강조를 줄여도 됨.
7. 전역 nav에는 `data_evidence_brief.html`을 "데이터 증거" 항목으로 추가했다.
```

## 10. Codex 남은 작업

1. `data_evidence_brief.html` 생성과 배포 반영.
2. StealthMole 민감 row는 미리 수집하지 않고 live-only helper로 유지.
3. approved query를 발표 현장에서 실행할 경우에도 저장은 private/ignored 경로, 웹에는 sanitized count/schema만 반영.
4. Foundry schema issue는 `docs/review/codex-foundry-schema-handoff.md` 기준으로 별도 해결.
