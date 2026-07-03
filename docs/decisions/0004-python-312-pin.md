# ADR-0004: Python 3.12 고정 (OSDK 호환)

날짜: 2026-07-03
상태: 승인

## 맥락
Palantir OSDK(Python)는 **`>=3.9,<3.13`**을 요구한다(`docs/spec/aip-integration.md` §0).
개발 머신의 시스템 파이썬은 3.14로, 그대로 두면 day-1에 OSDK pip 설치·임포트가 깨진다.
어댑터·스토어·파이프를 오늘 만들되 내일 OSDK와 같은 인터프리터에서 돌아가야 한다.

## 결정
- 프로젝트 파이썬을 **3.12로 고정**한다: `uv python pin 3.12`(→ `.python-version`).
- `pyproject.toml`: `requires-python = ">=3.11,<3.13"` — OSDK 상한(<3.13) 준수, 하한은
  최신 문법(3.11+) 여유.
- 환경은 **uv**로 관리. 런타임 의존성 `httpx`, `pyjwt`; dev `pytest`.
- 앱 성격이라 패키지 빌드는 하지 않음(`[tool.uv] package = false`); 루트의 `conftest.py`가
  `adapter`/`store` 임포트 경로를 확보.

## 근거
- OSDK가 3.13+에서 미지원이라 상한 고정이 불가피. 3.12는 OSDK 지원창 상단이자 안정적.
- uv는 인터프리터 다운로드·잠금·재현 설치를 한 번에 처리 → 팀·심사 환경 재현성 확보.

## 영향
- `.python-version = 3.12`, `pyproject.toml requires-python = ">=3.11,<3.13"`.
- 실행: `uv sync` → `uv run pytest` / `uv run python scripts/p0_pipe.py`.
- day-1 OSDK 설치(`uv pip install <osdk>`)가 동일 3.12 venv에서 호환.
