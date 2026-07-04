# Supply-chain Credential Exposure Early Warning

**D4D Hackathon · Track 2/3 · 방산 공급망 자격증명 노출 조기경보**

StealthMole 유출 자격증명과 인포스틸러 감염기기를 Palantir Foundry 온톨로지로 상관해, 협력사별 위험 순위와 활성 침해 경로를 보여주는 방어형 조기경보 체계입니다.

## 한 줄

"우리 공급망 말단에서, 지금 뚫리고 있는 협력사는 어디인가?"

유출 레코드를 단순 나열하지 않고 `CredentialExposure -> Identity -> Supplier -> Prime -> Program` 경로로 전파시켜, 활성 침해가 성립한 협력사를 상단에 올리고 조치 초안을 생성합니다.

## 현재 상태

**P0-P6 로컬 파이프 완료 · 106 tests green.**

- mock adapter 기반 상관, 엔티티 해소, 활성침해 탐지, 위험 점수, 대시보드, 통보 초안, 평가 파이프가 동작합니다.
- `ontology.md`는 Foundry Ontology Manager에서 만들 객체, 링크, 파생 데이터셋, API 이름을 바로 입력할 수 있게 정리했습니다.
- StealthMole live adapter는 JWT 계약까지 맞췄고, 현재 live auth는 `401 Invalid token or expired token`으로 막혀 있습니다. 키 활성화, API product provisioning, IP allowlist 이슈로 보고 지원 요청 근거를 남깁니다.
- Foundry ontology/OSDK가 준비되면 `OntologyStore` 경계에서 SQLite 보험 스토어를 Foundry store로 교체합니다.

실측(`scripts/p6_eval.py`): correlation precision/recall 100%/100%, active-compromise precision/recall 100%/100%, 활성 업체 3곳 top-3 고정, active set 도달 9분(-90%).

## 실행

Python은 OSDK 호환을 위해 3.12를 사용합니다.

```bash
uv sync
uv run pytest -q
uv run python scripts/p4_dashboard.py
uv run python scripts/p6_eval.py
```

주요 산출물:

```bash
uv run python scripts/p1_report.py     # out/p1_report.html
uv run python scripts/p3_rank.py       # CLI 위험 순위 + Incident 경로
uv run python scripts/p4_dashboard.py  # out/dashboard.html
uv run python scripts/p5_drafts.py     # out/drafts/*.md
uv run python scripts/p6_eval.py       # out/eval.json
```

StealthMole 키는 `.env`에만 둡니다. `.env.example`에는 변수 이름만 있습니다.

## 구조

- `adapter/`: `ExposureSource` Protocol, mock/live StealthMole adapter, normalize/masking boundary.
- `store/`: `OntologyStore` Protocol, SQLite validation store, Foundry/OSDK hot-swap target.
- `actions/`: correlation, entity resolution proposal, active-compromise flagging, scoring, propagation, notification draft.
- `scripts/`: report, rank, dashboard, draft, eval, live recon commands.
- `registry/`: synthetic supply-chain seed data.
- `docs/spec/`: direction, ontology, data sources, AIP integration, architecture, execution prompts.
- `ontology.md`: Foundry Ontology Manager build guide.

## 가드레일

StealthMole 제공 데이터와 공개정보만 사용합니다. 무단 스캐닝, 침투, 자격증명 재사용은 금지입니다. 데모는 합성 도메인과 마스킹된 값만 사용하고, 통보는 `draft` 생성까지입니다.
