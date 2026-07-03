# PROMPTS.md — 콜드스타트 실행 프롬프트 (Supply-chain Cred)

**contract-first**: StealthMole 접근은 내일 → 오늘은 목 어댑터로 전체 파이프 완성, 접근 열리면 P0-B로 hot-swap. 순서대로 던지고 실패/발견 로그로 다음을 조정.

공통 제약(매 프롬프트): `direction.md`·`ontology.md`·`data-sources.md`·`aip-integration.md`·`architecture.md` 준수. **AIP-spine**(온톨로지 중심). **StealthMole 제공 데이터 + 공개정보만. 무단 스캐닝·침투·크리덴셜 재사용 절대 금지. 데모=합성 도메인. 방어 목적·초안 생성까지. 비밀 마스킹.** provenance(evidence 링크) 강제. 온톨로지 스멜테스트 통과. 깊이 타협 금지.

---

## P0-A — AIP 파이프 + 어댑터 계약 뚫기 (오늘, 접근 없이)
```
목표: (A) Foundry/OSDK 파이프 검증, (B) StealthMole 어댑터 인터페이스+목 구현. StealthMole 실접근 불필요.
할 일:
A. Foundry Dev Tier에 Object Type 1개(Supplier) + Link 1개(owns Domain) + Action 1개(ComputeRisk) 생성. Developer Console에서 OSDK 발행 → pip 설치 → Python으로 Supplier write/read 왕복.
B. data-sources.md §2 인터페이스대로 adapter/base.py(Protocol) + adapter/mock.py(§3 목, 활성침해 케이스 포함) 구현. adapter/stealthmole.py는 §1 검증된 계약으로 스텁만(내일 연결).
성공기준: A) OSDK 객체 왕복 성공. B) 목 어댑터가 Exposure/InfectedDevice 레코드 산출.
제약: 키 환경변수. AIP 막히면 원인 기록 + Morph 질문 목록(폴백은 보험). 실 API 호출 금지(아직 접근 없음).
산출: aip-integration.md에 "확인된 OSDK 스니펫" 추가, 어댑터 3파일.
```

## P0-B — StealthMole 실접근 정찰 (내일, 접근 열리면 즉시)
```
목표: 실 StealthMole에 붙어 계약 확인 + 어댑터 hot-swap. data-sources.md의 [확인필요] 항목 채움.
할 일:
1. sm_headers()로 GET /v2/user/quotas → 인증 성공 + 열린 모듈 목록(cds/ub/cl/cb 및 dt/tt/rm/gm/lm 여부) 확인.
2. 본인/합성 도메인으로 각 열린 모듈 /search 1회 → 레코드 스키마 기록. 특히 cds의 device/malware/infected_at/cookie 필드 실측.
3. adapter/stealthmole.py 완성, 목과 동일 인터페이스로 swap. normalize()가 실 레코드도 Exposure로 변환.
성공기준: 실 데이터가 온톨로지 Exposure로 들어오고, 목→실 swap이 코드 한 줄.
제약: 제공 계정 정상 사용. 크레딧 절약(/quotas 확인 후 배치, start 증분). 타 실기업 대량 조회 금지.
산출: data-sources.md [확인필요] → [검증됨] 갱신, cds device 필드 확정.
```

## P1 — 수직관통: 업체 1개 → 조회 → 상관 → 온톨로지
```
목표: 레지스트리 1업체에 대해 어댑터 조회→정규화→상관→온톨로지 write→화면까지 한 줄.
할 일:
1. registry: 5~10 샘플 업체 {company, domain, tier, criticality, supplies→prime}. 합성/공개 도메인.
2. 어댑터(목)로 업체 도메인 조회 → Exposure/InfectedDevice 정규화(활성 필드 보존) → 온톨로지 write.
3. CorrelateExposure Action: Exposure→Identity→Supplier 링크(도메인 매칭). 최소 화면에 업체 노출 리스트+출처.
성공기준: 업체 1개의 노출이 상관되어 온톨로지 경유로 화면에(비밀 마스킹).
제약: 매칭 근거 기록. 무단 스캐닝 금지.
산출: registry, 상관 결과 샘플, 실행법.
```

## P2 — 엔티티 해소 + 위험 전파 그래프
```
목표: 신원 병합 + 공급망 상향 전파 경로 구성.
할 일:
1. EntityResolver(보조 LLM): 같은 email/username 변형을 하나의 Identity로 병합 제안(사람 확인).
2. Supplier supplies Prime runs Program 링크로 전파 경로 구성.
3. 중복 제거(같은 Identity 다수 Exposure 병합, 최신 우선, 소스 다양성=신뢰도).
성공기준: company_id → [Exposure...] + Identity 병합 + Supplier→Prime→Program 경로가 그래프에 존재.
제약: 병합 근거 기록, 자동 확정 말고 제안.
산출: correlation/resolution 모듈, 전파 경로 샘플.
```

## P3 — 활성침해 가중 스코어링 (AIP Logic, 핵심)
```
목표: ComputeRisk를 AIP Logic으로 구현, 활성침해를 가중 상향해 순위 상단으로.
할 일:
1. base(노출 규모·최근성·비밀유형·모듈 신뢰도) 점수.
2. FlagActiveCompromise: InfectedDevice(최근)+has_session_cookie+account_type∈{vpn,admin} 경로 성립 시 CompromiseIncident(traverses 경로) 생성.
3. 활성 가중 상향 + criticality 곱 + 0~100 정규화 + grade. 각 점수 evidenced_by(원 레코드).
성공기준: 목의 활성 케이스가 순위 상단, 점수 기여분 설명, Incident 경로 표시.
제약: 근거 없는 점수 금지. 활성 판정은 정의된 필드/경로로만.
산출: RiskScorer(AIP Logic), scoring 결과, 순위 샘플.
```

## P4 — 순위 대시보드 + 전파 그래프 뷰
```
목표: 업체 위험 순위 + 드릴다운 + 전파 그래프.
할 일:
1. 순위 테이블: Supplier·score·grade·활성 플래그·최근 신호 시각(OSDK read).
2. 드릴다운: 업체 → Exposure/Device 상세(마스킹) + 출처 + 타임라인.
3. 전파 그래프 뷰: Device→Identity→Supplier→Prime→Program 경로 하이라이트.
4. 필터: tier / 활성침해만 / 기간.
성공기준: 브라우저에서 순위→드릴다운→출처, 활성 경로 그래프가 도는다.
제약: 모든 항목 출처. 비밀 마스킹. 동작 우선.
산출: 대시보드, 스크린샷.
```

## P5 — 조치 에이전트 (권고 + 통보 초안)
```
목표: 상위 업체 방어 조치 권고 + 통보 초안 자동 생성(사람 검토 전제).
할 일:
1. GenerateNotificationDraft(AIP agent): 조치 권고(비번 리셋·세션 폐기·MFA·계정 격리) + 초안 텍스트(근거 요약·출처).
2. 상위 1~3업체 초안 생성, cites 링크 필수.
성공기준: 상위 업체 초안이 근거와 함께 생성(발송 없음).
제약: 실제 발송 금지. 과장·근거 없는 단정 금지. 방어 목적. 마스킹.
산출: NotificationDrafter, 초안 예시.
```

## P6 — 평가 + 데모·피칭 패키징
```
목표: 성능 숫자 증명 + 3분 발표 데모.
할 일:
1. 목/실 세트로 상관 precision/recall, 활성침해 우선순위 유효성.
2. 맨몸(레코드 나열) vs 우리(그래프 트리아지) 대응속도(골든타임) 비교.
3. 데모 대본 + 목 백업(접근 실패 대비) + 심사 매핑 슬라이드.
성공기준: 네트워크/접근 없어도 재현 + 심사 4항목 각 한 문장 + "AIP 얕지 않음"(전파 경로+Action 전이) 시연.
산출: 평가표, demo.md, 목 백업.
```

---

### 반복 규칙
- **P0-A(오늘) 먼저, P0-B(내일 접근)로 hot-swap.** 실 API 없이도 파이프 완성이 원칙.
- 매 단계 `direction.md` 5요소 + `ontology.md` 스멜테스트 + 합법 가드레일과 어긋남 자문.
- 막히면 넓히지 말고 수직관통(P1) 사수 후 재확장. **온톨로지 깊이 타협 금지.**
