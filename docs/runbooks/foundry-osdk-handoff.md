# Foundry OSDK Handoff

이 문서는 Ontology Manager와 Object Explorer 검증이 끝난 뒤, 생성된 Python OSDK를
저장소에 연결하는 절차다. 목적은 실데이터 수집이 아니라 이미 올린 합성 seed가
OSDK에서 같은 객체/링크 경로로 보이는지 확인하는 것이다.

## User Inputs

비밀값은 채팅에 쓰지 말고 `.env`에 둔다. Codex에게 필요한 것은 다음 네 가지다.

1. Developer Console이 준 Python OSDK 설치 명령 또는 wheel/path.
2. 생성 패키지 import 이름. 예: `FOUNDRY_OSDK_MODULE=...`.
3. 인증 방식. 가장 안전한 방식은 `FOUNDRY_OSDK_CLIENT_FACTORY=module:function`로
   인증된 client를 반환하는 작은 factory를 제공하는 것이다.
4. 실제 생성 API 이름. 기본값과 다르면 `.env`의 `FOUNDRY_OSDK_OBJECT_*`,
   `FOUNDRY_OSDK_LINK_*` 변수로 덮어쓴다.

공식 기준: Palantir 문서는 OSDK가 Developer Console에서 관리되고, Python은 Pip
또는 Conda 패키지로 생성된다고 설명한다. 새 application 생성 시 Resources 단계에서
Ontology SDK 생성과 포함할 object/action type을 선택한다. Python bootstrap 문서는
토큰을 환경변수에 두고 source control에 커밋하지 말라고 한다.

## One-Time Foundry UI Step

Ontology가 이미 만들어졌으면 UI에서 남은 작업은 OSDK 발행뿐이다.

1. Foundry의 Developer Console로 이동한다.
2. `+ New application`을 만든다.
3. Resources 단계에서 `Yes, generate an Ontology SDK`를 선택한다.
4. 현재 Omija ontology를 선택한다.
5. 최소한 아래 리소스를 모두 포함한다.
   `Supplier`, `Prime`, `Program`, `Domain`, `Identity`,
   `CredentialExposure`, `InfectedDevice`, `ThreatSource`, `MergeProposal`,
   `RiskAssessment`, `CompromiseIncident`, `ProgramExposure`,
   `NotificationDraft`, 그리고 모든 link/action type.
6. Python OSDK 2.x로 generate/publish한다.
7. Developer Console의 install command, package import name, auth 예제를 `.env`에 옮긴다.

이 UI 단계가 끝나면 Codex가 로컬에서 설치, probe, smoke를 이어서 한다.

## `.env` Contract

가장 적게 필요한 값:

```bash
FOUNDRY_OSDK_INSTALL_CMD=<full pip/uv pip install command from Developer Console>
FOUNDRY_OSDK_PACKAGE=<Developer Console install package or wheel/path>
FOUNDRY_OSDK_MODULE=<generated import package>
FOUNDRY_HOSTNAME=https://<enrollment>.palantirfoundry.com
FOUNDRY_TOKEN=<personal-or-dev-console-token>
```

`FOUNDRY_OSDK_INSTALL_CMD`가 있으면 그것을 우선 사용한다. Developer Console이
`pip install ...` 전체 명령을 보여주면 그대로 넣고, 단일 package spec만 알면
`FOUNDRY_OSDK_PACKAGE`만 채운다.

생성 OSDK의 client/auth import path가 자동 탐지되지 않으면 추가한다.

```bash
FOUNDRY_OSDK_CLIENT=<module.path:FoundryClient>
FOUNDRY_OSDK_AUTH=<module.path:UserTokenAuth>
```

인증 코드가 특이하면 가장 확실한 방식은 factory다.

```bash
FOUNDRY_OSDK_CLIENT_FACTORY=<module.path:create_client>
```

이 경우 `create_client()`는 인자 없이 인증된 generated client를 반환해야 한다.

## Immediate Commands

```bash
uv pip install <generated-osdk-package>
uv run python scripts/foundry_osdk_smoke.py --probe --module "$FOUNDRY_OSDK_MODULE"
uv run python scripts/foundry_osdk_smoke.py
```

`--probe`는 패키지 import와 공개 symbol만 확인한다. 두 번째 명령은 Foundry에
실제로 붙어서 합성 seed 객체와 링크를 읽는다.

Codex가 개입 없이 실행할 때는 이 한 줄만 쓴다.

```bash
uv run python scripts/foundry_osdk_bootstrap.py
```

이 명령은 `.env`를 읽고, `FOUNDRY_OSDK_PACKAGE`가 있으면 설치하고, package probe를
돌린 뒤, 합성 seed smoke test를 실행한다. 토큰 값은 출력하지 않는다.

## Claude Code Palantir MCP

Palantir MCP를 Claude Code project scope로 붙일 때는 `.env` 토큰을 직접 `.mcp.json`에
저장하지 않는다. 이 저장소는 wrapper를 통해 `.env`를 읽는다.

```bash
claude mcp add palantir-mcp \
  --scope project \
  -- uv run python scripts/palantir_mcp.py
```

이후 `claude mcp list`에서 `palantir-mcp`가 연결되면 Claude Code를 통해 ontology와
Developer Console 상태를 질의할 수 있다.

## Smoke Criteria

첫 성공 기준은 쓰기가 아니라 읽기다.

1. `Supplier sup-h`, `Supplier sup-f`, `Prime prime-x`, `Program prog-sentinel`을 읽는다.
2. `sup-h -> subcontractsTo -> sup-f -> supplies -> prime-x -> runs -> prog-sentinel` 경로를 읽는다.
3. `CredentialExposure exp:micro-h:active`의 `of`와 `targets` 분리 링크를 읽는다.
4. `CompromiseIncident incident:micro-h:active`의 `traverses_supplier`, `traverses_program`을 읽는다.
5. `NotificationDraft draft:sup-h:2026-07-03`의 `cites_incident`를 읽는다.

이 다섯 개가 통과하면 Ontology Manager 설정, backing datasource, link API 이름,
OSDK 권한이 같은 방향으로 맞았다고 볼 수 있다.

## Diagnosing Link Backing

전체 링크 상태는 다음 명령으로 본다.

```bash
uv run python scripts/foundry_osdk_smoke.py --diagnose
```

현재 OSDK에서 join-table 링크는 정상이고, FK로 만든 일부 링크는 `None`으로
반환될 수 있다. 이 경우 generated CRUD action으로 링크를 직접 채우려고 하지 않는다.
FK link는 FK column 값과 target primary key가 정확히 맞아야 하며, action signature에
해당 FK property가 없으면 OSDK로 수정할 수 없다.

해커톤에서는 이미 검증된 join-table 방식이 가장 빠르다. `owns`, `prime_owns`,
`belongs_to`, `of`, `targets`, `sourced_from`, `leaked`가 OSDK에서 `None`이면
해당 Link Type을 join-table datasource 방식으로 바꾸고 `out/foundry_seed/23_*.csv`
부터 `29_*.csv`를 재사용한다.

## After Smoke

Smoke가 통과하면 `store/foundry.py`의 read-only 메서드부터 채운다.

1. `suppliers`, `primes`, `programs`
2. `propagation_paths`
3. `risk_assessments`, `incidents`, `notification_drafts`

Action Type 쓰기(`ComputeSupplierRisk`, `FlagActiveCompromise`,
`GenerateNotificationDraft`)는 실제 action API 이름과 submission criteria가 확인된
뒤에 연결한다. 읽기 검증 전에는 store 본체에 생성 OSDK import를 넣지 않는다.

## Final Demo Path

현재 해커톤 데모의 성공 기준은 Foundry Ontology를 읽어서 같은 의사결정 경로를 재현하는 것이다. 쓰기 Action Type은 데모 필수 경로가 아니다.

```bash
uv run python scripts/foundry_osdk_bootstrap.py --force-reinstall
uv run python scripts/foundry_osdk_smoke.py --diagnose
uv run python scripts/demo_e2e.py --compare --supplier sup-h
uv run python scripts/foundry_demo_report.py
open out/foundry_demo.html
```

정상 기준:

1. `foundry_osdk_smoke.py --diagnose`가 core object/link를 모두 `OK`로 출력한다.
2. `demo_e2e.py --compare`가 `RESULT: OK`를 출력한다.
3. `out/foundry_demo.html` 첫 화면에서 risk band, impacted programs, active path, provenance가 보인다.

`store/foundry.py`는 read-only adapter다. Foundry Action Type 쓰기는 API name, parameter mapping, submission criteria가 확정된 뒤 별도 연결한다.
