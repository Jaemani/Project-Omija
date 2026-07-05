# Codex Handoff: Foundry OSDK Readback Broken

작성: Fable, 2026-07-05. 공개 repo용으로 provider-specific source ref는 redacted 처리했다.

## 증상

`uv run python scripts/final_demo_check.py` 내부의 `foundry_osdk_smoke.py --diagnose` 경로에서 `ThreatSource.get("src:candidate:empty")`가 `None`을 반환한다.

## 확정된 근본 원인

1. 벤더중립 rename 이후 로컬 seed의 `ThreatSource` PK는 `src:candidate:empty`가 됐다.
2. Foundry 백킹 데이터셋은 파일 교체가 되었지만 객체 인덱스는 과거 legacy vendor-specific source ref를 계속 반환한다.
3. 결정적 원인은 백킹 데이터셋 3개가 `schemaNotFound` 상태라는 점이다. raw CSV 파일만 있고 스키마가 없어서 객체 인덱싱이 새 CSV를 파싱하지 못한다.
4. MCP에는 이 상태를 강제로 재색인하는 트리거가 없고, create action은 PK를 자동 UUID로 만들기 때문에 특정 PK를 심는 해결책이 아니다.

영향 범위:

- 로컬 SQLite 엔진 기반 데모 페이지에는 영향 없음.
- Foundry OSDK smoke/readback 경로와 Foundry blast-radius 검증 경로에만 영향.

## 실행 옵션

### 옵션 A: 권장

Foundry UI에서 3개 백킹 데이터셋을 schema-aware dataset으로 다시 만든다.

- `08_threat_source`
- `06_credential_exposure`
- `28_link_sourced_from`

절차:

1. Foundry에서 각 CSV backing dataset의 schema를 명시한다.
2. Ontology Manager에서 object/link datasource mapping이 새 schema를 읽는지 확인한다.
3. materialization/indexing이 완료될 때까지 기다린다.
4. `ThreatSource.get("src:candidate:empty")`가 반환되는지 확인한다.
5. legacy vendor-specific source ref가 더 이상 반환되지 않는지 확인한다.

### 옵션 B: 빠른 우회

Foundry smoke 테스트를 일시적으로 로컬 SQLite backend 기준으로만 돌린다.

이 옵션은 발표 직전 데모 안정성을 위한 우회다. Foundry schema 문제 자체를 해결하지 않는다.

## 재검증 명령

```bash
uv run python scripts/foundry_osdk_smoke.py --diagnose
uv run python scripts/final_demo_check.py
```

목표:

```text
foundry_osdk_smoke.py --diagnose: PASS
final_demo_check.py: RESULT: READY
```

## 발표 시 표현

과장하지 않는다.

안전한 표현:

> Foundry 온톨로지 구조와 action 흐름은 구성했고, 로컬 SQLite 엔진에서 동일한 온톨로지 로직을 검증했습니다. Foundry 백킹 데이터셋 schema 정비는 남아 있어 OSDK readback 경로는 별도 보완 중입니다.
