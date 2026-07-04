# PROMPTS.md — 콜드스타트 실행 프롬프트

목표는 이틀짜리 해커톤에서 바로 결과를 내는 것입니다. 날짜를 나눠 기다리지 않습니다. live API/OSDK가 막히면 mock+SQLite 보험 파이프로 데모를 유지하고, 열리는 즉시 같은 adapter/store 경계에서 교체합니다.

공통 제약:

- `direction.md`, `ontology.md`, `data-sources.md`, `aip-integration.md`, `architecture.md`, 루트 `ontology.md`를 준수합니다.
- AIP/Foundry Ontology가 spine입니다.
- StealthMole 제공 데이터와 공개정보만 사용합니다. 무단 스캐닝, 침투, 자격증명 재사용 금지.
- 데모는 합성 도메인과 마스킹된 값만 사용합니다.
- provenance, evidence link, path snapshot 없는 점수와 초안은 만들지 않습니다.

## P0 — adapter/store 계약과 Foundry 전환점

목표: mock+SQLite 파이프를 즉시 재현하고, live StealthMole/Foundry OSDK 전환점을 명확히 둡니다.

할 일:

1. `adapter/base.py`, `adapter/mock.py`, `adapter/stealthmole.py`가 같은 `ExposureSource` 계약을 지키는지 확인합니다.
2. `store/base.py`, `store/sqlite.py`, `store/foundry.py`가 같은 `OntologyStore` 경계를 유지하는지 확인합니다.
3. `scripts/p0_pipe.py`로 mock records -> normalize -> store -> read-back -> masking check를 실행합니다.
4. Foundry ontology는 루트 `ontology.md` 기준으로 생성합니다.

성공 기준: 네트워크 없이 전체 파이프가 통과하고, live store/source 전환 지점이 코드에서 분명합니다.

## P0-live — StealthMole live recon

목표: 제공된 키로 live 계약을 확인하고 막히면 지원 요청 가능한 근거를 남깁니다.

할 일:

1. `scripts/p0b_recon.py --quotas-only`로 `/user/quotas`를 먼저 확인합니다.
2. 성공하면 열린 모듈별 `/search` 1회만 수행해 schema only 파일을 `out/p0b/`에 저장합니다.
3. `cds`의 device, malware, infected_at, cookie 계열 필드를 확인해 normalize 매핑을 갱신합니다.
4. 401이면 키 원문 없이 timestamp, endpoint, status, response body, 추정 원인(activation/product/IP allowlist)을 기록합니다.

성공 기준: quotas와 schema가 저장되거나, 지원 요청 가능한 401 evidence package가 남습니다.

## P1 — 수직관통

목표: 업체 1개 이상의 domain -> exposure -> identity -> supplier 귀속을 화면까지 연결합니다.

할 일:

1. `registry/suppliers.yaml`의 합성 협력사와 도메인을 seed합니다.
2. adapter에서 받은 레코드를 `normalize()`로 마스킹하고 store에 기록합니다.
3. `CorrelateExposure`가 Identity -> Domain -> Supplier를 연결합니다.
4. `scripts/p1_report.py`로 보고서를 만듭니다.

성공 기준: 업체별 exposure가 근거와 함께 표시됩니다.

## P2 — 엔티티 해소와 공급망 전파

목표: 같은 사람/계정 후보를 병합 제안하고 Supplier -> Prime -> Program 전파 경로를 만듭니다.

할 일:

1. email/username 변형은 `MergeProposal`로만 제안합니다.
2. Supplier self-link는 `subcontractsTo` / `subcontractors` 방향을 유지합니다.
3. 전파는 depth cap과 visited set으로 cycle-safe 하게 계산합니다.

성공 기준: 2차 협력사에서 원청/프로그램까지 이어지는 path가 화면과 incident 근거로 재사용됩니다.

## P3 — 활성침해 구조 트리아지

목표: 단순 가중치가 아니라 `risk_band + score` 구조로 활성 경로를 상단에 고정합니다.

할 일:

1. `InfectedDevice`가 최근 감염, session cookie, vpn/admin 계정을 만족하는지 확인합니다.
2. `CredentialExposure.of`와 `CredentialExposure.targets`를 분리해 교차 접근 경로를 잡습니다.
3. Band A(active path)는 Band C 대량 유출보다 항상 위에 오게 합니다.
4. incident는 완전한 path 없이 만들지 않습니다.

성공 기준: mock의 활성 케이스가 top rank를 차지하고 path가 설명됩니다.

## P4 — 대시보드

목표: 심사자가 90초 안에 문제, 경로, 조치 초안을 볼 수 있게 합니다.

할 일:

1. supplier rank table, active filter, drilldown, path graph를 확인합니다.
2. 모든 secret/cookie/token은 마스킹 상태로만 표시합니다.
3. `scripts/p4_dashboard.py`로 정적 HTML을 생성합니다.

성공 기준: `out/dashboard.html` 하나로 오프라인 발표가 됩니다.

## P5 — 통보 초안

목표: 상위 위험 업체에 대한 방어 조치 초안을 생성합니다.

할 일:

1. `GenerateNotificationDraft`는 password reset, session revocation, MFA, account isolation을 근거와 함께 제안합니다.
2. 상태는 `draft`입니다. 실제 발송 기능은 만들지 않습니다.
3. cites/evidence 없는 초안은 금지합니다.

성공 기준: `out/drafts/*.md`가 생성되고 raw secret이 없습니다.

## P6 — 평가와 발표 패키징

목표: 심사 기준에 맞는 숫자와 대본을 고정합니다.

할 일:

1. `scripts/p6_eval.py`로 correlation P/R, active-compromise P/R, rank validity, golden-time 개선을 산출합니다.
2. `docs/demo.md`의 숫자가 `out/eval.json`과 일치하는지 확인합니다.
3. live 실패, Foundry publish 지연, 네트워크 실패별 백업 메시지를 준비합니다.

성공 기준: 3분 발표와 90초 라이브가 재현됩니다.
