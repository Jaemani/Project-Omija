# Supply-chain Credential Exposure Early Warning (T2 · 특수상황)

**D4D Hackathon · Track T2 · 특수상황 유형**
방산 공급망 자격증명 노출 조기경보 — StealthMole 유출 자격증명·스틸러 감염기기를 **Palantir 공급망 온톨로지**로 상관하여 업체별 위험 순위를 산출하고, **활성 침해**를 그래프 경로로 탐지해 즉시 조치를 권고하는 조기경보 체계.

## 한 줄
> "우리 공급망 말단에서, 지금 뚫리고 있는 협력사 어디냐?" — 유출·감염을 협력사→원청→프로그램으로 **전파**시키고, 활성침해를 **경로 존재**로 탐지해 순위 + 통보 초안을 낸다.

## 현재 상태 (2026-07-03)
**P0-A ~ P6 완료 · 테스트 84 green.** 목 어댑터로 전체 파이프(상관→엔티티 해소→활성침해 탐지→
가중 스코어링→대시보드→통보 초안→평가)가 오프라인·네트워크 없이 재현된다.
- **P0-B(StealthMole 실접근)만 day-1 대기** — 어댑터 계약 검증됨, 목→실 교체가 코드 한 줄(`docs/runbooks/foundry-day1.md`).
- 실측(`scripts/p6_eval.py`): 상관 P/R 100%/100%(25/25 귀속), 활성침해 탐지 P/R 100%/100%(TP 2·FP 0·FN 0),
  활성 2개 업체가 순위 top-2 고정(95.76 > 56.97), 골든타임 맨몸 75분 → 활성 도달 6분(-92%).
  *mock은 합성·소규모·클린이라 P/R은 상한값(파이프 정합성 증명)이지 실전 성능 주장 아님.* 3분 발표 대본은 `docs/demo.md`.

## 콜드스타트 (context 없이 시작하는 에이전트용)
`CLAUDE.md`가 자동 로드된다. 없으면 순서대로:
1. `CLAUDE.md` — 규칙·가드레일(합법성=생명줄) 2. `docs/spec/direction.md` — 백본 5요소
3. `docs/spec/ontology.md` — **핵심**: 공급망 그래프(전파·활성 경로) + 스멜테스트
4. `docs/spec/data-sources.md` — **StealthMole v2 실계약(검증됨) + 어댑터 + 목**
5. `docs/spec/aip-integration.md` — AIP+OSDK 6. `docs/spec/architecture.md` — 설계
→ 그 다음 `docs/spec/PROMPTS.md`의 **P0-A**(오늘, 접근 없이) 실행.

## 접근 타이밍
StealthMole API는 **내일** 열림. 오늘 P0-A로 목 어댑터+온톨로지+AIP+화면 완성 → 내일 P0-B로 실 어댑터 hot-swap. 계약은 이미 검증됨(`docs/spec/data-sources.md`).

## 왜 이 방향 (전략)
- **온톨로지 = 척추(AIP-spine)**: 레코드 나열은 API-wrapper. 우리는 공급망 그래프로 위험을 전파시킨다. 심사 "군 적용성 30%" = Palantir 배포 패러다임 적합성.
- **StealthMole = 해커톤 제공 합법 데이터**(OSINT 트랙 상금 500만원 제공사). 이 API를 제대로 쓰는 팀이 유리.
- **활성침해 우선**이 차별점: "유출됨" 나열이 아니라 "지금 뚫리는 중"을 앞세운다.

## 지표 (심사 기준 매핑)
| 심사 항목 | 대응 |
|---|---|
| Problem Fit 25% | 방산 말단 협력사 = APT 초기침해 지점 정조준 |
| Military Deployability 30% | 그래프 전파 + 순위 + 즉시 조치 초안, 방어 목적 명확 |
| Technical Execution 25% | 자동 상관 + 엔티티 해소 + 활성 경로 탐지 + AIP 스코어링 |
| Creativity 20% | "유출 나열" 아닌 active-compromise 경로 트리아지 |

## MVP 우선순위 (24H, 깊이 타협 없이)
목 어댑터(P0-A) → 샘플 협력사 5~10 → 상관+엔티티 해소 → 활성침해 가중 스코어 → 순위 대시보드 → 전파 그래프 뷰 → 상위 업체 통보 초안. 내일 실 데이터 swap. **온톨로지·AIP 깊이 타협 금지.**

## 퀵스타트 (목 어댑터 + 로컬 파이프, 네트워크·시크릿 불필요)
Python 3.12 고정(OSDK 호환, ADR-0004), uv 관리. StealthMole 실 API 호출 없음.
```bash
uv sync                              # .venv 생성 + 의존성(httpx, pyjwt, pyyaml, pytest)
uv run pytest -q                     # 84 tests green (어댑터·정규화·상관·스코어·평가 …)
uv run python scripts/p4_dashboard.py   # out/dashboard.html — 메인 라이브 화면
```
전체 산출물:
```bash
uv run python scripts/p1_report.py   # out/p1_report.html — 수직관통(상관) 화면
uv run python scripts/p3_rank.py     # CLI 순위표 + 활성침해 Incident 경로
uv run python scripts/p5_drafts.py   # out/drafts/*.md — 통보 초안(발송 없음)
uv run python scripts/p6_eval.py     # out/eval.json — 성능 숫자(상관·활성 P/R·골든타임)
```
- 키는 `.env`(gitignore) — `.env.example`에 이름만. day-1(P0-B)에 실 어댑터 연결.

## 아키텍처 요약
레지스트리(`registry/suppliers.yaml`)가 공급망 그래프 상단(Supplier·Domain·Prime·Program + supplies/runs)을
시드하고, 어댑터(`adapter/`, 실|목 hot-swap + `normalize`=마스킹 경계)가 StealthMole 레코드를 `Exposure`로 정규화한다.
`OntologyStore`(`store/`, SQLite 검증 스토어 = Foundry/OSDK Protocol seam)에 적재 후 액션들(`actions/`)이
파생 객체를 만든다 — CorrelateExposure(귀속) → EntityResolver(신원 병합 제안) → FlagActiveCompromise
(Device→…→Program 경로 존재 시 CompromiseIncident) → ComputeRisk(활성 가중·evidence 강제) →
GenerateNotificationDraft(초안·발송 없음). 화면·평가는 `scripts/`(p1·p3·p4·p5·p6). AIP가 척추, SQLite/자체 스택은 보험.

## 합법·윤리 (반드시)
StealthMole 제공 데이터 + 공개정보만. 무단 스캐닝·침투·크리덴셜 재사용 **절대 금지**. 데모=합성 도메인. 통보는 초안 "생성"까지(발송 없음). 유출 비밀번호 **마스킹**. 방어적 조기경보 목적.

## 문서 지도
- **규칙**: `CLAUDE.md`(가드레일·콜드스타트 순서).
- **스펙** `docs/spec/`: `direction.md`(백본 5요소) · `ontology.md`(**척추**: 그래프·전파·활성 경로 + 스멜테스트) ·
  `data-sources.md`(StealthMole v2 계약 + 어댑터 + 목) · `aip-integration.md`(AIP+OSDK) · `architecture.md`(설계) ·
  `PROMPTS.md`(P0~P6 실행 프롬프트).
- **결정(ADR)** `docs/decisions/`: 0001 리포 구조 · 0002 실행 위임 · 0003 로컬 검증 스토어 · 0004 Python 3.12 핀 · 0005 스코어링 가중.
- **변경로그** `docs/changelog/architecture.md`(온톨로지·아키텍처 변경 이력, P0-A~P6).
- **런북** `docs/runbooks/foundry-day1.md`(Foundry/OSDK 콘솔 수동 단계, day-1 hot-swap).
- **데모** `docs/demo.md`(3분 발표 대본 · 실행 순서 · 리허설 체크리스트 · 오프라인 백업 · 심사 매핑).
