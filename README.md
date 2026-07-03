# Supply-chain Credential Exposure Early Warning (T2 · 특수상황)

**D4D Hackathon · Track T2 · 특수상황 유형**
방산 공급망 자격증명 노출 조기경보 — StealthMole 유출 자격증명·스틸러 감염기기를 **Palantir 공급망 온톨로지**로 상관하여 업체별 위험 순위를 산출하고, **활성 침해**를 그래프 경로로 탐지해 즉시 조치를 권고하는 조기경보 체계.

## 한 줄
> "우리 공급망 말단에서, 지금 뚫리고 있는 협력사 어디냐?" — 유출·감염을 협력사→원청→프로그램으로 **전파**시키고, 활성침해를 **경로 존재**로 탐지해 순위 + 통보 초안을 낸다.

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

## 합법·윤리 (반드시)
StealthMole 제공 데이터 + 공개정보만. 무단 스캐닝·침투·크리덴셜 재사용 **절대 금지**. 데모=합성 도메인. 통보는 초안 "생성"까지(발송 없음). 유출 비밀번호 **마스킹**. 방어적 조기경보 목적.

## 파일
`CLAUDE.md`(규칙) · `docs/spec/direction.md`(백본) · `docs/spec/ontology.md`(척추) · `docs/spec/data-sources.md`(StealthMole 계약+어댑터+목) · `docs/spec/aip-integration.md`(AIP) · `docs/spec/architecture.md`(설계) · `docs/spec/PROMPTS.md`(실행)
