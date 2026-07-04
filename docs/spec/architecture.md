# architecture.md — technical design (superseded live-feed assumptions)

Current status as of 2026-07-05: historical design details below may mention
live feeds. The active implementation is a no-live-data ontology-engine demo
with empty candidate evidence slots.

빌드용 정밀 설계. 전제: `direction.md`(백본) · `ontology.md`(척추) · `data-sources.md`(StealthMole 실계약+어댑터+목) · `aip-integration.md`(AIP 경로).

---

## 0. 설계 원칙
- **AIP-spine**: 공급망 그래프 온톨로지가 중심. 어댑터가 write, AIP Logic이 RiskAssessment/Incident/Draft를 Action으로 생성, 프론트는 OSDK read.
- **contract-first**: StealthMole 접근(내일) 전 목 어댑터로 전체 파이프 완성. day-1 hot-swap.
- **활성침해 우선**: 설계 전체가 "지금 뚫리는 신호"를 상단으로 편향.
- **provenance 강제**: 모든 위험판정 → 원 레코드(evidence 링크). 근거 없으면 Action 거부.
- **얇게 수직관통 먼저**: 업체 1개 → 조회 → 상관 → 스코어 → 순위 → 초안 끝단까지 먼저.
- **합법·방어 목적만**: 탐지·순위·초안 "생성"까지. 발송·공격 없음.
- **깊이 타협 금지.**

## 1. 컴포넌트
```
[StealthMole v2]  cds/ub/cl/cb ─ 어댑터(실|목) ─┐
[Supplier Registry]  합성/공개 도메인 ──────────┤ ingest → Foundry
                                                ▼
[Ontology (Foundry)]  Supplier·Prime·Program·Domain·Identity·Exposure·InfectedDevice·RiskAssessment·CompromiseIncident·ProgramExposure·NotificationDraft
      │  OSDK 타입드 접근                     ▲ Actions (human review, 발송 없음)
      ├──► [Correlation]  CorrelateExposure: Exposure→Identity(엔티티 해소)→Supplier
      ├──► [Risk (AIP Logic)]  ComputeRisk: 활성침해 가중 스코어(evidence)
      ├──► [Active]  FlagActiveCompromise: 경로 존재 탐지 → Incident(traverses+blast)
      ├──► [Propagate (AIP Logic)]  PropagateRisk: subcontracts 재귀 롤업 → ProgramExposure
      └──► [Draft (AIP agent)]  GenerateNotificationDraft: 근거 인용 초안
                    │
                    ▼
[Frontend]  순위 대시보드 + 드릴다운 + 전파 그래프 뷰 (OSDK read, Action 호출)
```

## 2. 데이터 파이프라인
1. **Ingest**: 어댑터가 도메인 단위로 StealthMole(또는 목) 조회 → Exposure/InfectedDevice raw → Foundry. Registry도 적재. 증분은 `start=<unix>`.
2. **Normalize**: 레코드 → Exposure 스키마(활성 신호 필드 보존). `source`·`module`·`source_ref` 채움(provenance).
3. **Correlate**: 이메일 도메인 = Supplier 도메인 → Identity belongs_to → Supplier. 서브도메인/별칭 처리.
4. **Entity resolution**: 같은 email/username 변형을 하나의 Identity로 병합(EntityResolver 보조, 사람 확인).
5. **Propagate**: 두 단계. (a) **경로 구성** — Supplier의 `subcontracts_to`(2차→1차→…, 가변깊이) 재귀 traverse + supplies→runs로 Supplier…→Prime→Program 경로 조립(`store.propagation_paths`, SQLite `WITH RECURSIVE`, 사이클 안전). 2차 말단만 subcontracts를 갖고 직결 supplies가 없어도 상위 Prime/Program에 도달. (b) **위험 롤업** — `PropagateRisk`가 각 Program에 닿는 모든 협력사 RiskAssessment를 집계해 **ProgramExposure** 생성(§4). "지금 어느 프로그램이 타나"를 점수로 답함. 활성 감염의 다운스트림 도달은 CompromiseIncident의 `blast_radius`(device 레벨)로 보존.

## 3. 위험 스코어링 (핵심 차별점)
`ComputeRisk` Action(AIP Logic). 점수 = base + 활성침해 가중 × criticality. 설명가능(기여분 표시), evidenced_by 필수.
| 요소 | 신호 | 방향 |
|---|---|---|
| 노출 규모 | Identity당 Exposure 수 | + |
| 최근성 | leak_date/infected_at 최근 | +↑ |
| 비밀 유형 | plaintext/cookie/token | +↑ |
| 모듈 신뢰도 | cds/ub(High) > cl(Med) > cb(Low) | 가중 |
| **활성침해** | 최근 InfectedDevice + has_session_cookie + account_type∈{vpn,admin} → 경로 성립 | **++ 상단** |
| criticality | tier1 / 핵심 Program 노출 | × |
- 정규화 0~100 + grade(즉시/주의/관찰). 각 점수에 evidence(원 레코드) 배열.

**프로그램 롤업(ProgramExposure)** — 협력사 점수는 귀속일 뿐이므로, `PropagateRisk`가 재귀 traverse로 한 Program에 닿는 모든 협력사 위험을 롤업: score = 지배 경로(최고 협력사 score) + breadth(distinct 활성 협력사, Supplier 기준 dedup) × program sensitivity. 활성 Program은 비활성보다 상단 밴드. evidenced_by(기여 Incident/Assessment) 비면 거부. 다이아몬드 공급망은 distinct Supplier/ref 기준 dedup(경로 수로 부풀림 금지). 경유 Prime은 별도 객체 없이 components 소계로 표기. (ontology.md §4-b)

## 4. 활성침해 탐지 (그래프 경로)
`FlagActiveCompromise`: `InfectedDevice(최근, has_session_cookie) → compromises → Identity → belongs_to → Supplier → [subcontracts_to → Supplier …(가변 홉)] → supplies → Prime → runs → Program` 경로가 성립하면 **CompromiseIncident** 생성(traverses 경로 필수, 가변길이). Supplier→…→Prime→Program 반부는 재귀 traverse(`propagation_paths`)로 해소하므로 subcontracts만 가진 2차 말단도 상위 Program에 도달·탐지된다. 이 경로 존재 자체가 경보 = "유출 나열"과의 근본 차이.

## 5. 조치 에이전트 (Action)
- `GenerateNotificationDraft`(AIP agent): 상위 업체별 방어 조치 권고(비번 리셋·세션 폐기·MFA·계정 격리) + 통보 초안 텍스트(근거 요약·출처 포함).
- **사람 검토 전제, 자동 발송 없음.** 근거 없는 단정·과장 금지. 비밀 마스킹.

## 6. 대시보드
- 순위 테이블: Supplier · score · grade · 활성침해 플래그 · 최근 신호 시각.
- 드릴다운: 업체 클릭 → Exposure/Device 상세(마스킹) + 출처 링크 + 타임라인.
- **전파 그래프 뷰**: Device→Identity→Supplier→Prime→Program 경로(AIP 깊이 시연).
- 필터: tier / 활성침해만 / 기간.

## 7. 스택
- 어댑터/ingest: Python(httpx, pyjwt). `data-sources.md`의 검증된 인증 스니펫.
- 온톨로지·추론: **Foundry Ontology + OSDK(Python) + AIP Logic** (spine). `aip-integration.md`.
- 프론트: React/Vite, OSDK read + Action.
- LLM: AIP Logic 내장(스코어 설명·초안) / 커스텀은 Claude(`claude-opus-4-8` 등).
- 폴백(보험): 로컬 SQLite 동일 온톨로지 스키마 → 후에 Foundry 이관.

## 8. 평가 (숫자로 증명)
- **상관 정확도**: 목/실 세트로 매칭 precision/recall.
- **활성침해 우선순위 유효성**: 주입한 활성 케이스가 상단에 오는가.
- **맨몸 대비**: 원 레코드 나열 vs 우리 그래프 트리아지의 대응속도(골든타임).

## 9. 리스크 & 대응
- StealthMole 접근 내일 → 오늘 목으로 완성, day-1 hot-swap + cds 실 스키마로 device 필드 확정.
- 실데이터에 샘플 도메인 매칭 0 → 목 활성 케이스로 데모 재현성(모의 명시).
- AIP 러닝커브 → P0에서 1객체+1액션 먼저(§`aip-integration.md`), Morph 멘토.
- 민감성 오해 → 방어 목적·합성 도메인·초안까지·마스킹을 데모에 명시.
