# demo.md — 3분 발표 대본

D4D 해커톤 Track 2/3. 데이터는 합성 `*.example`, 통보는 draft, 비밀은 마스킹합니다. 숫자는 `scripts/p6_eval.py` 실측 기준입니다.

## 준비

```bash
uv sync
uv run pytest -q
uv run python scripts/p4_dashboard.py
uv run python scripts/p6_eval.py
```

산출물은 `out/dashboard.html`과 `out/eval.json`입니다. 네트워크나 live API 없이도 재현됩니다.

## 3분 흐름

### 문제 30초

"방산 공급망은 1차, 2차 협력사로 넓게 퍼져 있고, 공격자는 말단 협력사의 유출 계정과 인포스틸러 감염기기를 먼저 봅니다. 문제는 레코드가 많아도 지금 실제로 원청이나 프로그램 접근 경로가 열렸는지 알기 어렵다는 점입니다."

### 해결 40초

"우리는 유출 레코드를 Foundry 온톨로지에 올려 `CredentialExposure -> Identity -> Supplier -> Prime -> Program` 경로로 연결합니다. `of`는 누구의 계정인지, `targets`는 무엇에 접근하는지 분리합니다. 그래서 협력사 계정이 원청 VPN이나 관리자 자산에 닿는 교차 경로를 잡을 수 있습니다."

### 라이브 90초

1. `out/dashboard.html`을 열고 ACTIVE supplier가 순위 상단에 오는 것을 보여줍니다.
2. 상위 업체를 클릭해 노출, 감염기기, 세션 쿠키 여부, 계정 타입을 확인합니다.
3. 경로 그래프에서 Device -> Identity -> Supplier -> Prime -> Program 전파를 보여줍니다.
4. 통보 초안을 열고 비밀번호 리셋, 세션 폐기, MFA, 계정 격리 권고가 근거와 함께 draft 상태로 생성됨을 보여줍니다.

### 숫자 20초

"핸드 작성 ground truth 기준으로 상관 precision/recall은 100%/100%, 활성침해 precision/recall도 100%/100%입니다. 활성 업체 3곳은 top-3에 고정됩니다. 레코드 나열 방식이면 30건을 약 90분 검토하지만, 우리는 노출 업체 카드 6개로 줄이고 활성 3곳에 9분 만에 도달합니다."

### 마무리 20초

"이건 API wrapper가 아니라 방산 공급망 온톨로지 기반 트리아지입니다. live StealthMole과 Foundry OSDK는 같은 adapter/store 경계에 붙도록 준비되어 있고, 현재 데모는 네트워크 실패와 키 이슈에도 재현됩니다."

## 리허설 체크리스트

- [ ] `uv run pytest -q` -> 115 passed.
- [ ] `uv run python scripts/p6_eval.py` -> `RESULT: OK`, top active suppliers 확인.
- [ ] `uv run python scripts/p4_dashboard.py` -> `out/dashboard.html` 생성.
- [ ] 화면에서 active 상단, drilldown, path graph, draft preview 확인.
- [ ] `out/` 산출물에 raw secret, cookie, session token 원문이 없는지 확인.

## 실패 대비

- live API 실패: mock adapter로 발표한다.
- 네트워크 실패: `out/dashboard.html`은 정적 HTML이다.
- Foundry publish 지연: SQLite validation store로 동일 파이프를 시연하고 `ontology.md`로 Foundry 매핑을 설명한다.

## Foundry OSDK 추가 시연

Foundry 온톨로지까지 보여줄 때는 아래를 실행한다.

```bash
uv run python scripts/final_demo_check.py
open out/foundry_demo.html
```

전체 회귀까지 같이 확인할 때는 `uv run python scripts/final_demo_check.py --full`을 사용한다. `out/foundry_demo.html`은 Foundry Python OSDK로 읽은 seed 객체와 링크만 사용한다.
