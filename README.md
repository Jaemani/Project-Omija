# Project Omija

**방산 공급망 자격증명 노출 조기경보 시스템**

**Ontology-Based Supply-Chain Credential Exposure Early Warning**

Last updated: 2026-07-08 KST

Omija는 유출 자격증명 후보, 인포스틸러 감염기기 후보, 공개 OSINT 맥락, 방산 공급망 관계를 온톨로지로 연결해 **어느 협력사와 프로그램을 먼저 확인해야 하는지**를 근거 경로와 함께 제시하는 방어형 의사결정 지원 시스템이다.

중요한 경계: Omija는 침해 확정 시스템이 아니다. 외부에서 관측된 노출 후보를 분석관의 검증 우선순위로 바꾸는 시스템이다. 실제 침해 확정은 VPN, SSO, IAM, EDR, 메일 로그, 협력사 확인이 필요하다.

## 1. Competition Context

| 항목 | 내용 |
|---|---|
| 대회 | D4D \| Deploy for Defense Hackathon APAC - SEOUL |
| 일정 | 2026-07-03 ~ 2026-07-05. 공식 이벤트 페이지 기준 해커톤 본 일정은 2026-07-04 09:00 ~ 2026-07-05 16:00 KST |
| 성격 | APAC Defense Tech Builders Network, 24H defense-tech hackathon |
| 선택 트랙 | **T2 · OSINT & 국방인텔** |
| 관련 트랙 | T3 · 전장네트워크·C2. 공급망 위험이 프로그램/운영 의사결정으로 전파되기 때문 |
| 제출 문제 | 방산 1·2차 협력사 도메인을 대상으로 유출 자격증명·스틸러 감염기기를 자동 상관하여 업체별 위험 순위를 산출하고, 활성 침해 정황에는 가중치를 높여 즉시 조치를 권고하는 조기경보 체계를 개발 |

대회 정보 출처: [D4D Luma event page](https://luma.com/2ew4xn7b), [F4GE LinkedIn event note](https://www.linkedin.com/posts/f4ge_d4d-deploy-for-defense-hackathon-apac-activity-7477902840284315648-_oWT). 트랙명과 평가 기준은 D4D 제출 화면과 현장 안내 기준으로 정리했다.

평가 기준에 맞춘 프로젝트 초점:

| 평가 항목 | Omija가 보여주는 것 |
|---|---|
| Problem Fit | 방산 공급망에서 유출 계정/스틸러 신호가 단순 건수보다 경로와 우선순위 문제임을 모델링 |
| Military Deployability | 원문 비밀번호/쿠키 없이도 경보, 검토, 통보 초안, 감사 가능한 상태 전이를 구성 |
| Technical Execution | 온톨로지, 로컬 reasoning engine, Foundry seed/action/readback, provider lineage 측정 구현 |
| Creativity | `of`와 `targets` 분리, `subcontractsTo*` 가변 깊이 전파, active-on-top ranking |
| Impact / Scalability | 공급망 registry와 승인된 exposure feed가 늘어나면 같은 객체/링크 모델로 확장 |

## 2. Problem Statement

방산 공급망은 원청, 1차 협력사, 2차 이하 협력사, 프로그램이 얽힌 그래프 구조다. 공격자는 상대적으로 취약한 협력사를 초기 침투 지점으로 삼을 수 있다. 그러나 유출 자격증명과 인포스틸러 감염 데이터는 여러 출처에 흩어져 있고, 단순 리스트나 건수 정렬만으로는 다음 질문에 답하기 어렵다.

- 이 계정은 누구의 것인가?
- 이 계정이 관측된 대상 자산은 어디인가?
- 그 자산이 원청, 프로그램, 작전상 중요한 공급망 경로와 이어지는가?
- 과거 콤보리스트성 유출인가, 최근 감염기기/세션 정황이 있는 활성 침해 후보인가?
- 사람이 지금 확인해야 할 조치는 무엇인가?

Omija의 문제의식은 **유출 데이터 관리**가 아니라 **방산 공급망 의사결정**이다.

## 3. Approach

### Core Hypotheses

1. 유출 레코드는 공급망 온톨로지에 연결될 때 운영 우선순위가 된다.
2. 활성 침해 후보는 단순 노출 건수보다 먼저 올라와야 한다.
3. 원문 비밀번호, 쿠키, 토큰을 저장하지 않아도 판단에 필요한 provenance와 위험 신호는 남길 수 있다.
4. Foundry의 객체, 링크, 액션 모델은 사람이 검토하는 감사 가능한 workflow를 표현하는 데 적합하다.

### Ontology Design

핵심 객체:

| Object Type | 역할 |
|---|---|
| `Supplier`, `Prime`, `Program` | 방산 공급망과 프로그램 구조 |
| `Domain`, `Identity` | 자산 표면과 계정 신원 |
| `CredentialExposure` | 유출 자격증명 후보 |
| `InfectedDevice` | 인포스틸러 감염기기 후보와 활성 신호 |
| `ThreatSource` | CL/CDS/CB/DT/TT, 공개 OSINT, 기타 출처 |
| `RiskAssessment` | 협력사 단위 위험 판정 |
| `CompromiseIncident` | 활성 침해 후보 사건 객체 |
| `ProgramExposure` | 프로그램 단위 영향 롤업 |
| `NotificationDraft` | 사람 검토용 통보 초안 |

핵심 링크:

| Link Type | 의미 |
|---|---|
| `CredentialExposure.of -> Identity` | 이 유출은 누구의 계정인가 |
| `CredentialExposure.targets -> Domain` | 이 자격증명이 어떤 자산을 대상으로 관측됐는가 |
| `Identity.belongsTo -> Domain/Supplier` | 계정 신원의 소속 |
| `Supplier.subcontractsTo* -> Supplier` | 2차 이하 협력사의 위험을 가변 깊이로 상위 협력사까지 전파 |
| `Supplier.supplies -> Prime`, `Prime.runs -> Program` | 공급망 위험을 프로그램 영향으로 전파 |
| `RiskAssessment/ProgramExposure/NotificationDraft evidenced_by/cites` | 판단과 초안의 근거 보존 |

`of`와 `targets`를 분리한 것이 핵심 차별점이다. 협력사 직원 계정이 원청 VPN이나 관리자 자산을 대상으로 관측될 수 있기 때문에, 계정 소유 조직과 대상 조직을 같은 칸에 넣으면 교차 조직 위험 경로가 사라진다.

### Risk Logic

Risk band는 점수보다 먼저 적용한다.

| Band | 의미 |
|---|---|
| A | 최근 감염기기, 세션 쿠키 정황, VPN/admin 계정 유형, Supplier-to-Program 경로가 함께 있는 활성 침해 후보 |
| B | 위험도가 높지만 활성 조건이 일부 부족한 상관 노출 |
| C | 수동적 또는 과거 자격증명 유출 |
| D | 약한 언급 또는 아직 연결되지 않은 맥락 |

Band A는 침해 확정이 아니라 **즉시 확인해야 하는 후보**다. 근거와 경로가 없으면 `RiskAssessment`, `CompromiseIncident`, `ProgramExposure`, `NotificationDraft` 같은 파생 판단 객체를 만들지 않는다. 이것을 Omija에서는 Provenance Mandatory 원칙으로 둔다.

## 4. Data Used

### Internal / Project Data

| 데이터 | 위치 | 용도 |
|---|---|---|
| Synthetic supply-chain seed | `out/foundry_seed/`, generator scripts | 방산 공급망, 계정, 도메인, 사건 시나리오 검증 |
| Local SQLite/reasoning output | `scripts/p3_rank.py`, `scripts/p4_dashboard.py`, `scripts/p5_drafts.py`, `scripts/omija_demo.py` 등 | 상관분석, active-on-top ranking, incident/draft 생성 |
| Foundry ontology captures | `out/captures/` | 객체 타입, 액션 타입, OSDK 접근 화면 증빙 |
| Foundry action readback | `out/foundry_action_chain.json` | 사람 검토 상태 전이 5건 readback 증빙 |
| Approved provider measurement bundle | `out/foundry_live_measurement/` | 승인된 StealthMole row를 sanitized object/link CSV와 Foundry 측정 결과로 보존 |

### External / Public Data

| 출처 | 사용 방식 | 산출 위치 |
|---|---|---|
| StealthMole hackathon API CL/CDS/CB | 승인된 filtered row를 redaction boundary 뒤에서 lineage 측정에 사용 | `out/data_lineage_live.*`, `out/foundry_live_measurement/` |
| StealthMole DT/TT | 설계상 `ThreatSource` 입력. 현재 계정/경로 기준 DT 403, TT 404로 실측 제한 | `docs/stealthmole-api-integration.md` |
| CISA KEV | known exploited vulnerability context | `out/public_context/summary.*`, `out/data_evidence_brief.html` |
| NVD CVE API | VPN, SSO, Citrix, Fortinet, Ivanti 등 접근 자산 취약점 맥락 | `out/public_context/summary.*` |
| FIRST EPSS | CVE exploit likelihood context | `out/public_context/summary.*` |
| MITRE ATT&CK STIX | Credential Access / Initial Access technique vocabulary | `out/public_context/summary.*` |
| CISA advisory RSS / ICS RSS | 최신 공개 권고 맥락 | `out/public_context/summary.*` |
| URLhaus aggregate metadata | malware/loader context aggregate | `out/public_context/summary.*` |
| HIBP breach metadata | breach data class/scale presentation context | `out/public_context/summary.*` |

금지 데이터:

- raw password
- raw cookie
- raw token/session value
- API key, JWT, bearer token
- raw provider envelope
- 재사용 가능한 실자격증명

## 5. Current Implementation Level

### Implemented

| 영역 | 현재 수준 |
|---|---|
| Ontology model | 13개 객체 타입과 공급망/증거/경로 링크 설계. Foundry 캡처 일부 존재 |
| Local reasoning engine | synthetic corpus 기준 상관분석, risk band, active-on-top, program rollup, notification draft 생성 |
| Steady-state console | 평시 운영 콘솔 `out/omija_console_home.html` |
| Incident report | 사건 발생 시 triage, of/targets, blast radius, draft workflow를 보여주는 `out/omija_demo.html` |
| Data coverage map | synthetic/public/provider/engine/Foundry evidence를 분리한 `out/data_coverage_map.html` |
| Public evidence brief | 공개 OSINT와 민감 provider boundary를 설명하는 `out/data_evidence_brief.html` |
| Live data lineage page | 승인된 StealthMole run -> redaction -> normalized rows -> Foundry measurement 흐름을 보여주는 `out/data_lineage_live.html` |
| Foundry live measurement | sanitized CSV upload/schema/schema-aware dataset/SQL count 측정 |
| Tests | 현재 `uv run pytest -q` 기준 121 passed |

### Latest Provider / Foundry Measurement

기준 산출물: `out/foundry_live_measurement/measurement.json`, `out/foundry_live_measurement/sql_measurement_result.json`, `out/data_lineage_live.json`

| 항목 | 결과 |
|---|---|
| Approved provider seed | `probe:domain:naver.com` |
| Modules | CL 50, CDS 50, CB 50 |
| Provider rows | 150 returned / 150 normalized / 0 rejected |
| Sanitized object rows | CredentialExposure 150, InfectedDevice 150, ThreatSource 150, Identity 150, Domain 17, Supplier 1, Program 1 |
| Sanitized link rows | 917 total across owns, belongs_to, of, targets, sourced_from, leaked, compromises |
| Raw secret export | false. `password`, `cookie`, `token`, raw provider payload removed |
| Backing dataset upload | 14/14 OK |
| Explicit backing dataset schema PUT | 14/14 OK |
| Separate schema-aware `live_measurement_*` datasets | 14/14 created |
| Foundry SQL count verification | 14/14 matched expected counts |
| Ontology OSDK live PK readback | **pending**. Foundry ontology datasource/index refresh 필요 |

중요: approved provider run에는 방산 supplier-to-program path가 확인되지 않았으므로 `RiskAssessment`, `CompromiseIncident`, `NotificationDraft` 같은 파생 판단 객체를 생성하지 않았다. 이것은 실패가 아니라 Provenance Mandatory 원칙에 맞는 동작이다. 사건 판단 데모는 synthetic scenario를 사용한다.

## 6. Artifact Versions

| 산출물 | 파일 | 설명 | 상태 |
|---|---|---|---|
| V0 legacy no-live console | `out/intelligence_demo.html`, `out/omija_console_core.html`, `out/omija_console_graph.html`, `out/omija_console_response.html` | 초기의 no-live-data 온톨로지 설명용 화면 | 보존. 최신 발표 주화면은 아님 |
| V1 Palantir-style variants | `out/palantir_v1.html`, `out/palantir_v2.html`, `out/palantir_v3.html` | UI 방향 비교용 초기 페이지 | 참고용 |
| V2 steady-state console | `out/omija_console_home.html` | 사건이 없을 때 감시 범위, quiet proof, provider readiness를 보는 운영 화면 | 메인 랜딩 |
| V3 incident report | `out/omija_demo.html` | active-on-top, of/targets, blast radius, notification draft를 보여주는 사건 보고서 | 핵심 데모 |
| V4 data coverage map | `out/data_coverage_map.html` | 무엇을 어디서 관리하고 무엇으로 감시하는지 전체 지도 | 발표 보조 |
| V5 public/provider evidence | `out/data_evidence_brief.html` | 공개 OSINT와 민감 provider boundary 설명 | 발표 보조 |
| V6 live data lineage | `out/data_lineage_live.html` | 승인된 provider row가 redaction/ontology/Foundry measurement로 이어지는 계보 | 본선 보강 핵심 |
| V7 Foundry measurement report | `out/foundry_live_measurement.html`, `out/foundry_live_measurement/measurement.html` | sanitized row가 Foundry schema-aware dataset에서 측정된 결과 | 본선 보강 핵심 |
| V8 program reverse view | `out/program_threat_view.html` | 프로그램 기준 역방향 질의/rollup | Q&A 백업 |

GitHub Pages 배포 경로:

```text
https://jaemani.github.io/Project-Omija/
https://jaemani.github.io/Project-Omija/omija_demo.html
https://jaemani.github.io/Project-Omija/data_coverage_map.html
https://jaemani.github.io/Project-Omija/data_evidence_brief.html
https://jaemani.github.io/Project-Omija/data_lineage_live.html
https://jaemani.github.io/Project-Omija/foundry_live_measurement.html
https://jaemani.github.io/Project-Omija/program_threat_view.html
```

## 7. How To Run

Prerequisite: Python 3.11 or 3.12, `uv`.

```bash
uv sync
make build
uv run pytest -q
```

Open local static pages:

```bash
open out/omija_console_home.html
open out/data_lineage_live.html
open out/foundry_live_measurement.html
open out/omija_demo.html
```

Regenerate specific artifacts:

```bash
uv run python scripts/omija_console_home.py
uv run python scripts/data_coverage_map.py
uv run python scripts/data_evidence_brief.py
uv run python scripts/data_lineage_live.py
uv run python scripts/foundry_live_measurement.py
uv run python scripts/omija_demo.py
uv run python scripts/program_threat_view.py
```

Foundry measurement flow:

```bash
uv run python scripts/foundry_live_dataset_upload.py
uv run python scripts/foundry_live_schema_put.py
uv run python scripts/foundry_live_schema_dataset_create.py
uv run python scripts/foundry_live_sql_measurement.py
uv run python scripts/foundry_live_readback.py
```

Expected today: upload/schema/schema-aware SQL measurement succeeds; `foundry_live_readback.py` remains `NOT_INDEXED` until Foundry ontology datasource/index refresh is completed.

## 8. Repository Map

| 경로 | 역할 |
|---|---|
| `scripts/` | demo page generators, local reasoning scripts, Foundry upload/measurement scripts |
| `tests/` | import boundary, scoring, ranking, artifact safety tests |
| `docs/` | architecture, data strategy, decisions, runbooks, review notes |
| `docs/decisions/` | ADRs. 특히 ADR-0005, 0006, 0009가 핵심 |
| `docs/review/` | 심사/본선 대비 진단과 Foundry lineage 체크 |
| `out/` | generated static pages and public-safe artifacts |
| `out/foundry_seed/` | Foundry ontology seed CSV |
| `out/foundry_live_measurement/` | approved provider row measurement bundle |
| `out/captures/` | Foundry UI screenshots for presentation |
| `registry/` | supplier/domain/program seed registry |
| `HANDOFF.md` | conversation-free project handoff. 일부 정책 문구는 README/ADR-0009보다 오래됨 |
| `ontology.md` | Foundry Ontology Manager build guide |

## 9. Detailed Documents

| 문서 | 읽을 때 |
|---|---|
| `docs/final-demo-alignment.md` | 웹, 데이터, 발표 흐름을 맞출 때 |
| `docs/finals-data-lineage-upgrade.md` | 본선 피드백 이후 data lineage 보강 내역 |
| `docs/review/foundry-live-measurement-update.md` | Foundry live measurement 결과 요약 |
| `docs/decisions/0009-approved-provider-foundry-lineage.md` | 승인 provider row를 lineage 입력으로 쓰기로 한 결정 |
| `docs/review/finals-foundry-lineage-check.md` | Foundry MCP로 확인한 of/targets lineage 상태 |
| `docs/practical-early-warning-plan.md` | 실제 조기경보 체계로 구현 가능한 범위 |
| `docs/data-collection-playbook.md` | supplier registry, asset surface, StealthMole, public context 수집 지침 |
| `docs/stealthmole-api-integration.md` | StealthMole module-to-ontology mapping과 private connector contract |
| `docs/open-data-catalog.md` | 공개 OSINT 출처와 사용 경계 |
| `docs/submission-guide.md` | D4D 제출 폼용 제목, 설명, 스크린샷 가이드 |
| `docs/claims-and-limitations.md` | 발표에서 해도 되는 말과 하면 안 되는 말 |

주의: 일부 초기 문서는 “no live data mode”를 전제로 한다. 최신 기준은 ADR-0009와 이 README다. 현재 전략은 **승인된 filtered provider row는 sanitized lineage와 Foundry 측정에 사용하고, raw secret과 raw provider envelope은 저장/표시하지 않는다**이다.

## 10. Final Conclusion

현재 Omija가 실질적으로 증명한 것:

- 유출 자격증명/감염기기 신호를 flat table이 아니라 온톨로지 객체와 링크로 바꿔 공급망 경로 판단에 사용할 수 있다.
- `of`와 `targets` 분리로 계정 소유 조직과 대상 자산 조직이 다른 교차 조직 위험을 표현할 수 있다.
- synthetic incident scenario에서 active-on-top ranking, program rollup, human-reviewed notification draft가 동작한다.
- 승인된 StealthMole hackathon row 150건을 raw secret 없이 redaction boundary 뒤에서 Foundry-ready object/link rows로 만들고, Foundry schema-aware dataset에서 SQL count까지 검증했다.
- Foundry ontology/action/readback 일부는 구성되어 있으나, provider live PK가 Ontology object로 OSDK readback 되는 단계는 아직 index refresh가 필요하다.

따라서 현재 상태는 **production system**이 아니라 **심사 가능한 working prototype**이다. 가장 강한 주장도 “실제 침해를 찾았다”가 아니라 “승인된 provider 신호와 공개 맥락을 안전하게 받아 공급망 의사결정 객체로 변환하는 구조와 상당 부분의 실행 경로를 구현했다”이다.

## 11. Next Direction

우선순위 높은 후속 작업:

1. Foundry ontology datasource/index refresh를 완료해 `scripts/foundry_live_readback.py`가 `RESULT: OK`가 되도록 한다.
2. approved provider row가 실제 `CredentialExposure`, `InfectedDevice`, `ThreatSource` ontology object로 readback 되는 화면을 캡처한다.
3. 실제 방산 supplier registry와 domain ownership evidence를 승인된 범위에서 적재한다.
4. StealthMole CL/CDS 외 DT/TT, country/keyword query 결과를 `ThreatSource` review queue로 연결한다.
5. VPN/SSO/IAM/EDR/mail confirmation log 슬롯을 추가해 active candidate를 confirmed/closed 상태로 전환할 수 있게 한다.
6. Role-based access control, secret destruction audit, reviewer approval workflow를 production 전제 조건으로 설계한다.
7. precision/recall은 실제 확인 로그가 붙은 뒤 측정한다. 현재 synthetic 결과를 현장 정확도로 주장하지 않는다.
8. 정적 HTML 데모는 발표용으로 유지하고, 실시간 provider 조회가 필요한 경우에는 Vercel/Foundry/AIP Function 등 서버 측 proxy가 있는 구조로 분리한다.

## 12. Claim Boundary

Allowed:

- “Omija는 방산 공급망 자격증명 노출 조기경보 의사결정 시스템이다.”
- “승인된 StealthMole hackathon filtered row 150건을 sanitized lineage와 Foundry measurement에 사용했다.”
- “synthetic incident scenario에서 active-on-top ranking과 notification draft workflow가 동작한다.”
- “Foundry SQL 측정은 완료됐고, Ontology object readback은 index refresh 대기다.”

Not allowed:

- “실제 침해를 확정했다.”
- “실제 password/cookie/token을 저장하거나 보여준다.”
- “`targets`가 로그인 성공을 의미한다.”
- “Foundry full end-to-end ontology readback이 완전히 해결됐다.”
- “자동 통보/자동 발송을 구현했다.”
