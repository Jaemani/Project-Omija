# CLAUDE.md — 에이전트 운영 규칙 (Supply-chain Credential Exposure)

이 폴더에서 콜드스타트하는 AI 에이전트의 상시 규칙. **가장 먼저 읽고**, 순서대로 문서를 읽은 뒤 작업 시작.

## 콜드스타트 순서 (context 없음 가정)
1. 이 파일(CLAUDE.md) — 규칙·가드레일(이 트랙은 합법성이 생명줄).
2. `docs/spec/direction.md` — 백본 5요소.
3. `docs/spec/ontology.md` — **핵심.** 공급망 그래프 온톨로지(전파·활성침해 경로) + 스멜테스트.
4. `docs/spec/data-sources.md` — **StealthMole v2 실계약(검증됨) + 어댑터 + 목.**
5. `docs/spec/aip-integration.md` — Palantir AIP + OSDK 실사용.
6. `docs/spec/architecture.md` — 상관·스코어링·대시보드·초안.
7. `docs/spec/PROMPTS.md` — **P0부터 순서대로.**
읽었으면 `docs/spec/PROMPTS.md`의 P0 시작.

## 정체성
D4D 해커톤 T2·특수상황 유형. 방산 공급망 자격증명 노출 조기경보. 목표: 우승. 수단: StealthMole 제공 API + 공개정보 + Palantir AIP. **방어적 조기경보.**

## 접근 타이밍 (중요)
StealthMole API는 **내일부터** 열림. 오늘은 **목(mock) 어댑터**로 온톨로지·AIP·화면 전체를 완성하고, 접근 열리면 실 어댑터만 hot-swap. → `docs/spec/data-sources.md`, `docs/spec/PROMPTS.md` P0.

## 최상위 원칙 (승부처)
1. **온톨로지가 척추 (AIP-spine).** StealthMole 레코드 나열은 API-wrapper. 우리는 공급망 그래프로 만들어 위험이 협력사→원청→프로그램 **전파**되게, 활성침해를 **경로 존재**로 탐지. → `docs/spec/ontology.md`
2. **온톨로지 억지/얕게 금지.** 모든 링크는 "flat table로 안 되는 그래프 추론" 정당화. 스멜테스트(docs/spec/ontology.md §0) 통과 못 하면 버려라.
3. **활성침해 우선 트리아지.** "유출됨" 나열이 아니라 "지금 뚫리는 중"을 상단으로.
4. **결정 루프.** 상관→스코어→활성 플래그→통보 초안. 분석가 승인(human-on-the-loop).
5. **provenance 강제.** 모든 위험판정 → StealthMole 원 레코드 역추적. 근거 객체 없는 점수·단정 금지.
6. **깊이 타협 금지.** 시간 걱정 말고 온톨로지·AIP 깊이 확보.

## 합법·윤리 가드레일 (절대 — 이 트랙의 생명줄)
- **StealthMole 제공 계정·API 정상 사용만.** 제공 범위 밖 유출 마켓·불법 소스 금지.
- **무단 스캐닝·침투·크리덴셜 재사용·계정 로그인 시도 절대 금지.** 조회·분석만.
- **협력사 실명단 미사용.** 데모=공개/합성 도메인. 실기업 겨냥·대량 조회 금지.
- **통보는 초안 "생성"까지.** 자동 발송·실제 통지 없음. 사람 검토 전제.
- 산출은 탐지·순위·방어조치 권고까지. 공격·악용 소지 출력 금지.
- **비밀 보호**: API 키는 환경변수/secret. 유출된 실제 비밀번호는 화면·로그·산출물에 원문 금지 → 마스킹.

## 기술 기준
- **AIP 우선, 폴백은 보험**: 온톨로지+AIP Logic/Agent+Action이 spine. 자체 스택은 보험.
- **contract-first**: 실 API 열리기 전 목으로 파이프 완성, day-1 hot-swap.
- **재현성**: 목 어댑터에 활성침해 케이스 포함(스코어링 검증·데모 백업).

## 심사 정렬
Problem Fit 25 · Military Deployability 30 · Technical Execution 25 · Creativity 20.
→ 공급망 그래프 전파 + 활성침해 우선 트리아지 + 즉시 조치 초안이 점수원.

## 문서 운영 규칙
- **스펙**: `docs/spec/` — direction·ontology·data-sources·aip-integration·architecture·PROMPTS 6문서. 콜드스타트 순서 위 참조.
- **구조적 의사결정**: `docs/decisions/`에 ADR로 기록. 번호 증가(0001, 0002, ...), 템플릿은 `docs/decisions/README.md`. 리포지토리 구조·모듈 경계·기술 스택 등 되돌리기 비싼 결정만 ADR 대상.
- **변경로그**: 온톨로지·아키텍처 변경(Object/Link/Action 추가·수정, 스코어링 로직 변경 등) 시 `docs/changelog/architecture.md`에 날짜·변경·이유 1줄씩 추가. 스펙 문서 수정과 동시에.
- **실행 위임**: 메인 에이전트(Fable)는 계획·오케스트레이션·검수만. 실제 실행(코드·문서 작성)은 opus(복잡 빌드)·sonnet(기계적 작업) 서브에이전트에 위임. 안전가드(safety guardrail) 발생 시 다른 모델·경로로 우회 시도 금지 — 작업 즉시 중단하고 유저에게 보고.
