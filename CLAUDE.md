# CLAUDE.md 에이전트 운영 규칙

Project Omija의 현재 기준 문서입니다. 이전 live-feed/API 디버깅 방향은
2026-07-05에 중단됐고, 현재 데모는 no-live-data 온톨로지 엔진입니다.

## 콜드스타트 순서

1. `HANDOFF.md`를 먼저 읽고 현재 방향을 확인합니다.
2. `README.md`와 `docs/data-strategy.md`를 읽어 데이터 경계를 확인합니다.
3. 루트 `ontology.md`를 읽고 Foundry 온톨로지 구조를 확인합니다.
4. `docs/demo-runbook.md`와 `docs/demo.md`를 읽고 현재 데모 흐름을 확인합니다.
5. `docs/decisions/0007-osint-data-fusion.md`와
   `docs/decisions/0008-dashboard-first-demo-surface.md`를 읽습니다.
6. `docs/spec/` 문서는 historical context로만 읽습니다. live-feed 구현 지침으로
   사용하지 않습니다.

## 현재 하드 룰

- StealthMole/live credential-feed 코드는 되살리지 않습니다.
- 외부 credential feed 키, JWT, bearer token, cookie, raw secret을 저장하거나
  출력하지 않습니다.
- main demo에서 public feed를 fetch하지 않습니다.
- 데모 내러티브는 로컬 엔진이 합성 시드로 생성한, 명확히 라벨된 시나리오 데이터를
  렌더할 수 있습니다(2026-07-05 오너 승인). 실제/민감 값은 계속 금지합니다.
- `NotificationDraft`는 draft-only입니다. send/webhook/SMS/email 발송 기능을
  만들지 않습니다.
- 실제·민감 값(실조직명, 실자격증명, raw secret)은 비워두거나 마스킹합니다. 합성
  `*.example` 시나리오 값은 라벨(SYNTHETIC)을 붙여 데모에서 사용할 수 있습니다.

## 역할 분담

- Fable: 계획, 구조 판단, 온톨로지 검수에 우선 사용합니다.
- Codex: 코드 작성, 테스트, 문서 정합성, 산출물 생성과 검증을 담당합니다.
- Opus: 디자인/페이지 방향 판단에 사용합니다.
- Fable 응답이 Opus fallback으로 보이면 초안으로만 보고 Codex가 다시 검토합니다.

## 데모 핵심

가치는 데이터 수집이 아니라 온톨로지 기반 의사결정입니다.

- `CredentialExposure.of -> Identity`
- `CredentialExposure.targets -> Domain`
- `Supplier.subcontractsTo -> Supplier`
- `CompromiseIncident.traverses_*`
- `NotificationDraft.cites`

이 링크들이 flat table로는 어려운 교차 조직 접근, 가변 깊이 공급망 전파,
프로그램 blast radius, 감사 가능한 의사결정 객체를 설명합니다.

## 검증 명령

```bash
uv run pytest -q
uv run python scripts/intelligence_demo.py
uv run python scripts/palantir_pages.py
```

금지 패턴 스캔:

```bash
rg -n "eyJ|api\\.stealthmole|hackathon\\.stealthmole" .
```
