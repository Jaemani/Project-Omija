# Playwright Screenshot Inventory

작성일: 2026-07-08 KST

이 문서는 Omija 데모 페이지를 실제 Chromium 렌더링으로 캡처한 결과를 페이지/기능 단위로 정리한다. 이 Codex 세션에는 Playwright MCP namespace가 노출되지 않아 MCP 도구 호출은 불가했다. 대신 `npx playwright`가 제공한 로컬 Chromium과 Playwright API로 동일한 브라우저 렌더링 캡처를 수행했다.

## Capture Command

```bash
npx -y -p playwright sh -c 'NM=$(dirname $(dirname $(which playwright))); PLAYWRIGHT_MODULE="$NM/playwright/index.mjs" node scripts/capture_demo_screenshots.mjs'
```

Output:

```text
out/screenshots/playwright/
out/screenshots/playwright/manifest.json
```

Current capture set:

- Pages: 7
- PNG screenshots: 49
- Feature-level screenshots: 35
- Viewports: desktop `1366x900`, mobile `390x844`
- Total size: about 6.3 MB

## Page Map

| Page | Source HTML | Role | Primary screenshots |
|---|---|---|---|
| 평시 콘솔 | `out/omija_console_home.html` | 사건이 없을 때 감시 범위, quiet proof, provider readiness, Foundry action evidence를 보여주는 운영 콘솔 | [desktop](../../out/screenshots/playwright/01-console-home--desktop-full.png), [mobile](../../out/screenshots/playwright/01-console-home--mobile-top.png) |
| 데이터 커버리지 맵 | `out/data_coverage_map.html` | 무엇을 어디서 관리하고, 어떤 데이터와 엔진 산출로 감시하는지 보여주는 지도 | [desktop](../../out/screenshots/playwright/02-data-coverage-map--desktop-full.png), [mobile](../../out/screenshots/playwright/02-data-coverage-map--mobile-top.png) |
| 데이터 증거 | `out/data_evidence_brief.html` | 공개 OSINT, 승인된 StealthMole lineage, synthetic 사건 데이터 경계를 설명 | [desktop](../../out/screenshots/playwright/03-data-evidence-brief--desktop-full.png), [mobile](../../out/screenshots/playwright/03-data-evidence-brief--mobile-top.png) |
| 데이터 계보 | `out/data_lineage_live.html` | 승인 provider row가 redaction boundary, normalized objects, Foundry measurement로 이어지는 흐름 | [desktop](../../out/screenshots/playwright/04-data-lineage-live--desktop-full.png), [mobile](../../out/screenshots/playwright/04-data-lineage-live--mobile-top.png) |
| Foundry Live Measurement | `out/foundry_live_measurement.html` | sanitized provider rows가 Foundry schema-aware datasets에서 측정됐고 SQL count가 맞는지 증명 | [desktop](../../out/screenshots/playwright/05-foundry-live-measurement--desktop-full.png), [mobile](../../out/screenshots/playwright/05-foundry-live-measurement--mobile-top.png) |
| 사건 보고서 | `out/omija_demo.html` | synthetic incident scenario에서 active-on-top, of/targets, blast radius, human-reviewed draft를 설명 | [desktop](../../out/screenshots/playwright/06-incident-report--desktop-full.png), [mobile](../../out/screenshots/playwright/06-incident-report--mobile-top.png) |
| 프로그램 뷰 | `out/program_threat_view.html` | 프로그램 기준 역방향 질의/rollup Q&A 백업 화면 | [desktop](../../out/screenshots/playwright/07-program-threat-view--desktop-full.png), [mobile](../../out/screenshots/playwright/07-program-threat-view--mobile-top.png) |

## Feature Screenshots

### 1. 평시 콘솔

| Feature | Screenshot | What it proves |
|---|---|---|
| top / core concepts | [01-console-home--feature-steady-state-top.png](../../out/screenshots/playwright/01-console-home--feature-steady-state-top.png) | `of != targets`, `subcontractsTo*`, active-on-top, human-reviewed draft 네 가지 핵심 개념 |
| coverage + quiet proof | [01-console-home--feature-coverage-and-quiet-proof.png](../../out/screenshots/playwright/01-console-home--feature-coverage-and-quiet-proof.png) | 사건이 없을 때도 감시 범위와 "봤는데 없는 것"을 수치로 보여줌 |
| provider posture | [01-console-home--feature-provider-posture.png](../../out/screenshots/playwright/01-console-home--feature-provider-posture.png) | 승인 provider 연결 상태와 redaction boundary |
| decision audit | [01-console-home--feature-decision-audit.png](../../out/screenshots/playwright/01-console-home--feature-decision-audit.png) | Foundry action/readback 기반 감사 스트림 |
| sensitive access boundary | [01-console-home--feature-sensitive-access-boundary.png](../../out/screenshots/playwright/01-console-home--feature-sensitive-access-boundary.png) | 민감정보 원문 접근을 제품 표면에서 분리하고 승인/감사 경계로 둔 설계 |

### 2. 데이터 커버리지 맵

| Feature | Screenshot | What it proves |
|---|---|---|
| top map | [02-data-coverage-map--feature-map-top.png](../../out/screenshots/playwright/02-data-coverage-map--feature-map-top.png) | synthetic, public context, engine, live Foundry, sensitive rail의 분리 |
| managed synthetic | [02-data-coverage-map--feature-managed-synthetic.png](../../out/screenshots/playwright/02-data-coverage-map--feature-managed-synthetic.png) | 데모 시나리오 구조와 seed 관리 범위 |
| open public context | [02-data-coverage-map--feature-open-public-context.png](../../out/screenshots/playwright/02-data-coverage-map--feature-open-public-context.png) | CISA KEV, NVD, ATT&CK 등 공개 컨텍스트 규모 |
| engine/live evidence | [02-data-coverage-map--feature-engine-live-evidence.png](../../out/screenshots/playwright/02-data-coverage-map--feature-engine-live-evidence.png) | provider rows, Foundry SQL counts, action readbacks, reverse chains |

### 3. 데이터 증거

| Feature | Screenshot | What it proves |
|---|---|---|
| evidence top | [03-data-evidence-brief--feature-evidence-top.png](../../out/screenshots/playwright/03-data-evidence-brief--feature-evidence-top.png) | 공개 OSINT + 승인 provider lineage + synthetic 사건의 경계 |
| public OSINT examples | [03-data-evidence-brief--feature-public-osint-examples.png](../../out/screenshots/playwright/03-data-evidence-brief--feature-public-osint-examples.png) | 실제 공개 데이터가 위험 맥락으로 쓰이는 방식 |
| ontology use | [03-data-evidence-brief--feature-ontology-use.png](../../out/screenshots/playwright/03-data-evidence-brief--feature-ontology-use.png) | 공개/민감/합성 데이터가 온톨로지에 들어갈 때의 역할 구분 |

### 4. 데이터 계보

| Feature | Screenshot | What it proves |
|---|---|---|
| lineage top | [04-data-lineage-live--feature-lineage-top.png](../../out/screenshots/playwright/04-data-lineage-live--feature-lineage-top.png) | 승인 StealthMole run이 실제로 있었고 공개 artifact에는 hash/lineage만 남김 |
| run summary | [04-data-lineage-live--feature-run-summary.png](../../out/screenshots/playwright/04-data-lineage-live--feature-run-summary.png) | CL/CDS/CB 150 rows, normalized 150, rejected 0 |
| swimlane | [04-data-lineage-live--feature-swimlane.png](../../out/screenshots/playwright/04-data-lineage-live--feature-swimlane.png) | provider -> private raw -> redaction -> normalized -> ontology -> engine -> Foundry |
| record lineage | [04-data-lineage-live--feature-record-lineage.png](../../out/screenshots/playwright/04-data-lineage-live--feature-record-lineage.png) | row-level lineage가 source hash와 object/link 경로로 추적됨 |
| redaction proof | [04-data-lineage-live--feature-redaction-proof.png](../../out/screenshots/playwright/04-data-lineage-live--feature-redaction-proof.png) | password/cookie/token/raw payload 제거 정책 |
| Foundry evidence | [04-data-lineage-live--feature-foundry-evidence.png](../../out/screenshots/playwright/04-data-lineage-live--feature-foundry-evidence.png) | schema PUT, SQL counts, OSDK readback pending 경계 |

### 5. Foundry Live Measurement

| Feature | Screenshot | What it proves |
|---|---|---|
| measurement top | [05-foundry-live-measurement--feature-measurement-top.png](../../out/screenshots/playwright/05-foundry-live-measurement--feature-measurement-top.png) | Foundry measurement summary와 OSDK readback pending을 함께 표시 |
| module counts | [05-foundry-live-measurement--feature-module-counts.png](../../out/screenshots/playwright/05-foundry-live-measurement--feature-module-counts.png) | CL/CDS/CB 50 each, total 150 |
| generated CSVs | [05-foundry-live-measurement--feature-generated-csvs.png](../../out/screenshots/playwright/05-foundry-live-measurement--feature-generated-csvs.png) | sanitized Foundry-ready object/link CSV 14개 |
| upload/readback | [05-foundry-live-measurement--feature-upload-readback.png](../../out/screenshots/playwright/05-foundry-live-measurement--feature-upload-readback.png) | upload/schema/schema-aware dataset status와 readback limitation |
| SQL counts | [05-foundry-live-measurement--feature-sql-counts.png](../../out/screenshots/playwright/05-foundry-live-measurement--feature-sql-counts.png) | Foundry SQL count 14/14 expected match |

### 6. 사건 보고서

| Feature | Screenshot | What it proves |
|---|---|---|
| incident top | [06-incident-report--feature-incident-top.png](../../out/screenshots/playwright/06-incident-report--feature-incident-top.png) | synthetic scenario와 provenance legend |
| incident summary | [06-incident-report--feature-incident-summary.png](../../out/screenshots/playwright/06-incident-report--feature-incident-summary.png) | Band A active candidate가 어떤 경로로 도달했는지 |
| triage and bands | [06-incident-report--feature-triage-and-bands.png](../../out/screenshots/playwright/06-incident-report--feature-triage-and-bands.png) | active-on-top ranking이 볼륨보다 우선함 |
| comparison panel | [06-incident-report--feature-comparison-panel.png](../../out/screenshots/playwright/06-incident-report--feature-comparison-panel.png) | 같은 입력에서 leak viewer, SIEM, Omija가 다른 결과를 내는 이유 |
| blast radius path | [06-incident-report--feature-blast-radius-path.png](../../out/screenshots/playwright/06-incident-report--feature-blast-radius-path.png) | 감염기기 -> Identity -> Supplier -> Prime -> Program 경로 |
| human review draft | [06-incident-report--feature-human-review-draft.png](../../out/screenshots/playwright/06-incident-report--feature-human-review-draft.png) | 통보는 자동 발송이 아니라 사람 검토용 draft |
| Foundry object list capture | [06-incident-report--feature-foundry-object-list-capture.png](../../out/screenshots/playwright/06-incident-report--feature-foundry-object-list-capture.png) | Foundry Ontology object types가 구성됐다는 화면 증거 |
| Foundry action types capture | [06-incident-report--feature-foundry-action-types-capture.png](../../out/screenshots/playwright/06-incident-report--feature-foundry-action-types-capture.png) | CRUD가 아닌 workflow action 설계 |
| Foundry OSDK capture | [06-incident-report--feature-foundry-osdk-capture.png](../../out/screenshots/playwright/06-incident-report--feature-foundry-osdk-capture.png) | SDK/API로 접근 가능한 ontology |
| outcome summary | [06-incident-report--feature-outcome-summary.png](../../out/screenshots/playwright/06-incident-report--feature-outcome-summary.png) | synthetic engine run 결과: 74 records, active incidents 3, programs 2 |

### 7. 프로그램 뷰

| Feature | Screenshot | What it proves |
|---|---|---|
| program top | [07-program-threat-view--feature-program-top.png](../../out/screenshots/playwright/07-program-threat-view--feature-program-top.png) | Program 중심 rollup 화면 |
| program sections | [07-program-threat-view--feature-program-sections.png](../../out/screenshots/playwright/07-program-threat-view--feature-program-sections.png) | reverse-query Q&A 백업 경로 |

## Recommended 8 Submission Screenshots

D4D 제출 폼은 최대 8장을 받는다. 아래 순서가 가장 설명력이 높다.

1. [01-console-home--feature-steady-state-top.png](../../out/screenshots/playwright/01-console-home--feature-steady-state-top.png)
   평시 콘솔 + 4 core concepts.
2. [04-data-lineage-live--feature-swimlane.png](../../out/screenshots/playwright/04-data-lineage-live--feature-swimlane.png)
   승인 provider row의 end-to-end lineage.
3. [05-foundry-live-measurement--feature-sql-counts.png](../../out/screenshots/playwright/05-foundry-live-measurement--feature-sql-counts.png)
   Foundry schema-aware SQL measurement.
4. [06-incident-report--feature-triage-and-bands.png](../../out/screenshots/playwright/06-incident-report--feature-triage-and-bands.png)
   active-on-top ranking.
5. [06-incident-report--feature-blast-radius-path.png](../../out/screenshots/playwright/06-incident-report--feature-blast-radius-path.png)
   공급망 경로와 blast radius.
6. [06-incident-report--feature-human-review-draft.png](../../out/screenshots/playwright/06-incident-report--feature-human-review-draft.png)
   human-reviewed notification draft.
7. [06-incident-report--feature-foundry-object-list-capture.png](../../out/screenshots/playwright/06-incident-report--feature-foundry-object-list-capture.png)
   Foundry ontology object evidence.
8. [02-data-coverage-map--feature-engine-live-evidence.png](../../out/screenshots/playwright/02-data-coverage-map--feature-engine-live-evidence.png)
   public/provider/engine/live evidence status.

## Validation Notes

- Representative screenshots were visually inspected.
- `manifest.json` records source HTML, purpose, screenshot paths, feature selectors, and extracted text excerpts.
- Captures are public-safe static screenshots. They show redacted/hash lineage and synthetic scenario outputs, not raw leaked credentials.
- Known limitation remains unchanged: Foundry SQL measurement is verified, but OSDK live PK object readback is still index-refresh pending.
