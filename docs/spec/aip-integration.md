# aip-integration.md — Palantir AIP + OSDK 실사용 (Supply-chain Cred)

AIP는 옵션이 아니라 **척추**. 온톨로지(`ontology.md`)를 Foundry에 올리고 StealthMole 어댑터(`data-sources.md`)로 채운 뒤 OSDK/AIP Logic로 위험판정·경보·통보초안을 짓는 구체 경로. 검증된 사실 기반(2026-07 조사).

> 사전조건: build.palantir.com Developer Tier 가입됨(무료). StealthMole API는 **내일** 열림 → 그 전엔 목 어댑터로 온톨로지·AIP·화면을 완성.

---

## 0. 검증된 사실 (조사 결과)
- **OSDK**: Foundry enrollment마다 생성되는 타입드 SDK. Python(>=3.9,<3.13) pip. Object Type=클래스, Action/Query 직접 호출. Developer Console에서 내 온톨로지용 문서·패키지 발행.
- **Foundry Platform SDK**(`foundry-platform-sdk`, PyPI): 저수준. OSDK 2.x와 단일 client 통합.
- **AIP Logic**: 노코드 LLM 함수. 온톨로지 built-in 접근. 출력이 staged human review 후 온톨로지 edit로 적용(자동화). 플랫폼 보안모델로 함수 권한 제한.
- **OSDK ↔ AIP Logic**: OSDK 앱(Python/TS/Java)에서 AIP Logic 함수 호출.
- 문서: palantir.com/docs/foundry/ontology-sdk/python-osdk, /docs/foundry/logic/overview, build.palantir.com.

## 1. 아키텍처: AIP를 spine으로
```
[StealthMole API v2]  cds/ub/cl/cb  ── 어댑터(실|목) ──┐
[Supplier Registry]  합성/공개 도메인 ────────────────┤ ingest
                                                       ▼
[Ontology (Foundry)]  Supplier·Prime·Program·Domain·Identity·Exposure·InfectedDevice·RiskAssessment·Incident·NotificationDraft
      │  OSDK 타입드 접근                            ▲ Actions (human review, 발송 없음)
      ├──► [Correlation]  CorrelateExposure: Exposure→Identity→Supplier
      ├──► [Risk (AIP Logic)]  ComputeRisk: 활성침해 가중 스코어
      ├──► [Active (룰/agent)]  FlagActiveCompromise: 경로 존재 탐지
      └──► [Draft (AIP agent)]  GenerateNotificationDraft: 근거 인용 초안
                    │
                    ▼
[Frontend]  순위 대시보드 + 드릴다운 + 그래프 뷰 (OSDK read, Action 호출)
```

## 2. 단계별 구현
### (1) Ingest → Foundry
- 어댑터가 StealthMole(또는 목)을 도메인 단위로 조회 → Exposure/InfectedDevice raw → Foundry Dataset. Registry(Supplier/Domain)도 적재.
- 증분: `start=<unix>`로 신규만(조기경보). 크레딧 절약 위해 `/user/quotas` 확인 후 배치.

### (2) 온톨로지 정의
- `ontology.md`의 Object/Link/Action Type 생성. Identity 병합(엔티티 해소), Supplier→Prime→Program 전파 링크, evidence 필수 Action.

### (3) OSDK 생성·사용
```bash
pip install <생성된-osdk-패키지>   # Developer Console 발행 후
```
```python
from my_osdk import FoundryClient
client = FoundryClient(auth=..., hostname="...")
# 업체별 노출 read
sup = client.ontology.objects.Supplier.get("supplier-a")
# 활성침해 경로 탐지 결과로 Incident 생성 (human-on-the-loop)
client.ontology.actions.flag_active_compromise(
    supplier="supplier-a", path=[dev_id, ident_id, "supplier-a", prime_id], evidence=[exp_id])
```

### (4) AIP Logic 함수
- **RiskScorer**: Supplier + 링크된 Exposure/Device → 활성침해 가중 점수·grade·설명. 온톨로지 read 권한만.
- **NotificationDrafter**: 상위 Supplier + 근거 → 통보 초안(방어 조치 안내 포함). 출력 staged review, **발송 없음**.
- **EntityResolver**(보조): 유사 email/username 변형을 하나의 Identity로 제안(사람 확인).
- Logic 함수는 OSDK 앱에서 호출하거나 automation 트리거.

## 3. LLM 선택
- 온톨로지 내부 추론(스코어 설명·초안): **AIP Logic 내장 모델**(거버넌스 통합).
- 커스텀 에이전트 코드: Claude — `claude-opus-4-8`(초안·상관 추론), `claude-sonnet-5`(균형), `claude-haiku-4-5-20251001`(경량 분류/엔티티 매칭). 키 환경변수.
- 원칙: 상관·경로·스코어는 룰+온톨로지로 하드하게, 서술(설명·초안)만 LLM. 근거 없는 단정·과장 금지.

## 4. 데모에서 AIP가 "얕지 않게" 보이는 법
- **위험 전파 그래프**를 실제로 보여준다: 감염기기 클릭 → Identity → Supplier(tier2) → Prime → Program 경로 하이라이트(= CompromiseIncident).
- `ComputeRisk`/`FlagActiveCompromise`/`GenerateNotificationDraft` Action 호출 → 객체 상태 전이 → provenance 링크가 원 StealthMole 레코드로.
- "유출 나열 테이블"이 아니라 **경로·전파·액션**이 도는 걸 시연 → API-wrapper 아님을 증명.

## 5. 리스크 & 폴백
- **StealthMole 접근 타이밍**: 내일 열림 → 오늘은 목 어댑터로 전체 파이프 완성. day-1에 실 어댑터 hot-swap + `cds` 실 스키마로 device 필드 확정.
- **AIP 러닝커브**: P0에서 온톨로지 1객체(Supplier)+1링크(owns Domain)+1액션(ComputeRisk)+OSDK 왕복 먼저. Morph 멘토.
- **폴백(보험, plan A 아님)**: AIP 시간 내 안 되면 로컬 SQLite로 동일 온톨로지 스키마 → 화면 유지 → 후에 Foundry 이관. 온톨로지 설계는 재사용.
