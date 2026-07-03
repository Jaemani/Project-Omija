# ADR-0003: 로컬 검증 스토어 (Foundry 대기용)

날짜: 2026-07-03
상태: 승인

## 맥락
P0-A는 (A) Foundry/OSDK 파이프 검증과 (B) StealthMole 어댑터+목 구현을 요구한다.
그러나 Foundry 온톨로지 생성과 OSDK 발행은 **build.palantir.com 콘솔의 수동 단계**라
에이전트가 코드로 자동화할 수 없다(유저가 직접 수행 — `docs/runbooks/foundry-day1.md`).
오늘 안에 "목 레코드 → 정규화 → 온톨로지 객체 → 읽기" 왕복 파이프를 검증하려면
Foundry에 의존하지 않는 실행 가능한 스토어가 필요했다.

## 결정
- 오늘의 파이프 검증은 **로컬 SQLite 스토어**로 수행한다(`store/sqlite.py`).
  테이블은 온톨로지와 **동일 스키마**: Supplier · Domain · Identity ·
  CredentialExposure · InfectedDevice · ThreatSource + 링크(FK).
- 스토어는 **`OntologyStore` Protocol**(`store/base.py`) 뒤에 둔다. 어댑터와 같은
  contract-first 패턴 → 미래 `FoundryOntologyStore`(OSDK 백엔드)로 **hot-swap** 가능.
- **AIP(Foundry Ontology + OSDK + AIP Logic)가 spine**이라는 설계는 불변. 이 스토어는
  검증·보험(insurance)이며 plan A가 아님을 코드 docstring에 명시했다.
- 마스킹은 스토어 이전 경계(`adapter.base.normalize()`)에서 강제 — 스토어는 원문 비밀을
  수신·저장하지 않는다.

## 근거
- 콘솔 수동성 때문에 파이프 검증을 Foundry 발행까지 블로킹하면 오늘의 P0-A 성공기준
  ("목 어댑터가 Exposure/InfectedDevice 산출 + 왕복")을 못 만난다.
- 동일 스키마 + Protocol 경계를 두면 온톨로지 설계 자체가 그대로 재사용되고, day-1에
  스토어 구현 교체만으로 Foundry로 이관된다(어댑터 실|목 swap과 대칭).
- `docs/spec/architecture.md` §7·§9와 `docs/spec/aip-integration.md` §5가 이미 명시한
  "폴백(보험): 로컬 SQLite 동일 온톨로지 스키마 → 후에 Foundry 이관"과 일치.

## 영향
- `store/` 패키지 추가(`base.py` Protocol, `sqlite.py` 구현). 코드 루트에 위치(ADR-0001).
- 파이프 데모(`scripts/p0_pipe.py`)와 테스트가 이 스토어로 왕복을 검증(네트워크 없이).
- day-1: OSDK 발행 후 `FoundryOntologyStore`를 같은 Protocol로 구현해 교체. 온톨로지
  스키마·필드명은 SQLite 스토어와 정합 유지(runbook §6).
