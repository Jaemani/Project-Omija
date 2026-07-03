# demo.md — 3분 발표 대본 (Supply-chain Credential Exposure Early Warning)

D4D 해커톤 T2·특수상황. **방어적 조기경보.** 데이터=합성(`*.example`), 발송 없음, 비밀 마스킹.
아래 대본은 90초 라이브를 포함해 정확히 3분에 맞춘다. 숫자는 `scripts/p6_eval.py` 실측(과장 없음).

> 원클릭 준비: `uv sync && uv run pytest -q && uv run python scripts/p4_dashboard.py && uv run python scripts/p6_eval.py`
> 그러면 `out/dashboard.html`(라이브 화면)과 `out/eval.json`(숫자)이 만들어진다. **네트워크·실 API 불필요.**

---

## (a) 문제 — 30초
"한국은 방산수출 4위, 1·2차 협력사 네트워크가 방대합니다. 그런데 **말단 협력사가 APT의 첫 표적**입니다.
다크웹의 유출 자격증명과 인포스틸러 감염기기는 본격 침해의 **치명적 조기 신호**인데, 신호는 여러 출처에
파편화돼 있어 **어느 업체가 지금 위험한지 우선순위가 안 나옵니다.** 특히 '이미 유출됨'과 '지금 감염 중(활성)'을
구분 못 하면 대응 골든타임을 놓칩니다."

## (b) 해자 — 60초
"우리는 레코드를 나열하지 않습니다. **공급망 그래프 온톨로지**를 척추로 씁니다.
- **전파**: 유출·감염을 `InfectedDevice → Identity → Supplier →(supplies)→ Prime →(runs)→ Program`으로
  상향 전파시킵니다. 2차 협력사 말단의 감염이 **어느 원청·어느 방산 프로그램을 노출시키는지**가 다중홉 그래프
  질의로 나옵니다 — flat table로는 불가능합니다.
- **활성침해 = 경로 존재**: '유효 세션 쿠키를 든 최근 감염기기 → VPN/관리자 계정 → tier-1 협력사 → Program'
  이라는 **경로가 그래프에 존재하면 그 자체가 경보**입니다. 휴리스틱이 아니라 경로 존재로 판정합니다.
- 이게 **레코드 나열(API-wrapper)과의 근본 차이**입니다. 온톨로지 스멜테스트 4개 항목
  (다중홉 질의 · 엔티티 해소 · 액션 상태전이 · provenance 그래프)을 **4/4** 통과합니다(`docs/spec/ontology.md §0`)."

## (c) 라이브 — 90초  (`out/dashboard.html`)
1. **순위 테이블 (활성 상단)**: "활성침해 2개 업체가 순위 1·2위로 고정됩니다 — Alpha Precision, Golf Avionics.
   빨간 ACTIVE 배지. 비활성 업체는 아무리 유출이 많아도 그 아래입니다. 이게 스코어링이 강제하는 불변식입니다."
2. **드릴다운 (evidence·마스킹)**: 업체 클릭 → 유출 레코드 상세. "모든 항목에 출처(source_ref)가 붙고,
   비밀번호·쿠키는 `Sy***`처럼 **마스킹**됩니다. 원문 비밀은 `normalize()` 밖으로 절대 안 나갑니다."
3. **Incident 경로 그래프**: "활성침해는 경로 객체입니다 —
   `InfectedDevice(RedLine·세션쿠키) → Identity(ops@…) → Domain → Supplier → Prime(Xenon Aerospace) →
   Program(Harbor Sustainment)`. 감염기기 한 대가 방산 프로그램까지 어떻게 닿는지 한눈에 보입니다."
4. **통보 초안 (조치 권고, 발송 없음)**: "상위 업체는 통보 초안이 자동 생성됩니다 — 비번 리셋·세션 폐기·MFA·
   계정 격리 권고 + 근거 요약 + 인용. **status=draft, 발송 기능은 아예 없습니다.** 사람이 검토·발송합니다."

## (d) 숫자 — 20초  (`scripts/p6_eval.py` → `out/eval.json`)
"핸드-작성 ground truth 대비 실측입니다:
- **상관(exposure→업체 귀속) precision/recall 100% / 100%** (25/25 정확 귀속, 오귀속 0).
- **활성침해 탐지 precision/recall 100% / 100%** — TP 2, **FP 0, FN 0**.
- **순위 유효성**: 활성 2개 업체가 top-2를 정확히 차지(최소 활성 95.76 > 최대 비활성 56.97).
- **골든타임**: 맨몸(레코드 나열)은 활성 플래그·dedup·순위가 없어 25개 레코드를 다 검토(3분/건 = 75분).
  우리는 5개 업체 카드(15분, 검토단위 -80%)이고, **활성 2곳은 순위 1·2위로 6분 만에 도달(-92%)**.
- 정직 고지: 이 합성 코퍼스에선 활성 감염이 마침 가장 최근 레코드라 최신순 정렬만 해도 2위에서 만납니다 —
  하지만 맨몸엔 **활성 플래그가 없어 거기서 멈춰도 되는지 알 수 없습니다.** 우리 이점은 최신순 트릭이 아니라
  **사전 계산·근거첨부·상단 고정 트리아지 + dedup/집계**입니다.
- 한계 명시: mock은 합성·소규모·클린이라 P/R은 상한값(파이프가 올바르게 연결됐다는 증명)이지 실전 성능 주장 아님."

## (e) 배치 경로 — 20초
"내일 열리는 **StealthMole API는 day-1 hot-swap**입니다 — 어댑터 계약이 이미 검증됐고, 목→실 교체가 코드 한 줄
(`adapter/mock.py` → `adapter/stealthmole.py`, `docs/runbooks/foundry-day1.md`). 온톨로지는 **Foundry로 이식**
(같은 Object/Link/Action, `OntologyStore` Protocol이 OSDK 백엔드로 교체). **human-on-the-loop** — 통보는 사람이
승인·발송합니다. 방어적 조기경보, 그게 전부입니다."

---

## 실행 순서 (명령어)
```bash
uv sync                                  # .venv + 의존성 (httpx, pyjwt, pyyaml, pytest)
uv run pytest -q                         # 84 tests green (무회귀 게이트)
uv run python scripts/p1_report.py       # out/p1_report.html — 수직관통(상관) 화면
uv run python scripts/p3_rank.py         # CLI 순위표 + Incident 경로 (콘솔 데모용)
uv run python scripts/p4_dashboard.py    # out/dashboard.html — 메인 라이브 화면
uv run python scripts/p5_drafts.py       # out/drafts/*.md — 통보 초안
uv run python scripts/p6_eval.py         # out/eval.json — 성능 숫자
```
라이브는 `out/dashboard.html` 하나로 충분(자기완결 정적 HTML). 숫자 인용은 `out/eval.json` 또는 p6_eval CLI 출력.

## 데모 리허설 체크리스트
- [ ] `uv run pytest -q` → **84 passed** (레드면 데모 중단, 원인부터).
- [ ] `scripts/p6_eval.py` → **RESULT: OK**, 상관/활성 P/R 100%, 순위 top-2 = [sup-a, sup-g].
- [ ] `scripts/p4_dashboard.py` → **RESULT: OK**, `out/dashboard.html` 생성.
- [ ] 브라우저로 `out/dashboard.html` 열어 (1) 활성 상단 (2) 드릴다운·마스킹 (3) 경로 그래프 (4) 초안 미리보기 확인.
- [ ] 마스킹 육안 확인: 화면·JSON에 `Synthetic-…!`/`SID…` 원문 **0건** (테스트가 강제하지만 눈으로도).
- [ ] 발표 3분 타이머로 1회 리허설 (라이브 90초 넘기지 말 것).

## 실패 대비 (백업)
- **네트워크/실 API 불필요**: 전 파이프가 목 어댑터·오프라인. 심사장 와이파이가 죽어도 무관.
- **오프라인 백업 = 정적 HTML**: `out/dashboard.html`은 외부 CDN·폰트·스크립트 의존 0(자기완결).
  라이브 스크립트가 실패하면 **미리 생성해둔 `out/dashboard.html`을 브라우저에서 바로 연다.**
- **숫자 백업**: `out/eval.json`을 미리 생성·보관(`out/`은 gitignore — 로컬 산출물). p6_eval 재실행 없이 인용 가능.
- **콘솔 백업**: 화면이 안 되면 `scripts/p3_rank.py` 콘솔 출력(순위표 + Incident 경로 체인)으로 대체.
- 시연 전 `out/`의 `dashboard.html`·`eval.json`·`drafts/`를 한 번 생성해 **미리 열어두기.**

## 심사 4항목 매핑 (한 문장씩)
- **Problem Fit 25** — 방산 말단 협력사 = APT 초기침해 지점을 정조준, 활성/비활성 구분으로 골든타임 확보.
- **Military Deployability 30** — 그래프 전파 + 순위 + 즉시 조치 초안 + human-on-the-loop, Foundry 배포 패러다임 정합.
- **Technical Execution 25** — 자동 상관 + 엔티티 해소 + 활성 경로 탐지 + AIP 스코어링, P/R·순위 불변식 실측.
- **Creativity 20** — '유출 나열'이 아니라 **활성침해=경로 존재** 트리아지, 레코드 나열(API-wrapper)과의 근본 차이.
