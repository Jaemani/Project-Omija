# CLAUDE.md 에이전트 운영 규칙

Supply-chain Credential Exposure 프로젝트에서 콜드스타트하는 에이전트의 상시 규칙입니다.

## 콜드스타트 순서

1. `CLAUDE.md` 규칙과 합법 가드레일을 먼저 읽습니다.
2. `docs/spec/direction.md` 백본 5요소를 읽습니다.
3. `docs/spec/ontology.md`와 루트 `ontology.md`를 읽습니다.
4. `docs/spec/data-sources.md`를 읽고 StealthMole live 계약과 현재 401 상태를 확인합니다.
5. `docs/spec/aip-integration.md`를 읽고 Foundry/OSDK 전환 경계를 확인합니다.
6. `docs/spec/architecture.md`를 읽습니다.
7. `docs/spec/PROMPTS.md`를 읽고 현재 단계에 맞게 실행합니다.

## 운영 원칙

- **Fable 우선**: 계획, 구조 판단, 온톨로지 검수는 `claude -p --model fable`을 우선 사용한다. 응답 모델이 Opus fallback이면 초안으로만 보고 Codex가 다시 검토한다.
- **Codex 실행**: 코드, 문서, 테스트, 커밋은 Codex가 수행한다.
- **AIP spine**: Foundry Ontology, AIP Logic/Agent, Action이 중심이다. SQLite와 정적 HTML은 검증 및 데모 보험이다.
- **contract-first**: live API가 막혀도 mock adapter로 전체 파이프를 유지하고, 키/OSDK가 열리면 경계에서 즉시 교체한다.
- **human-on-the-loop**: 엔티티 병합, 통보, 조치 확정은 사람이 검토한다. 자동 발송 금지.
- **provenance mandatory**: risk, incident, program exposure, draft는 근거 링크나 path 없이는 만들지 않는다.

## 현재 상태 메모

- 로컬 mock+SQLite 파이프는 P0-P6까지 동작하고 테스트는 106개 통과 기준이다.
- StealthMole live auth는 `401 Invalid token or expired token` 상태다. 서명 계약은 공식 통합 코드 기준으로 맞췄으므로 키 활성화/API product/IP allowlist 문제 가능성이 높다.
- **Live 갱신**: 위 401은 운영 API URL 시도 기록이다. 해커톤 전용 API에서 quotas/CDS 검색이 성공했다. DT/UB는 미제공이며 기본 정찰은 CDS 1회로 제한한다.
- Foundry ontology는 루트 `ontology.md`를 따라 수동 생성 중이다. API 이름은 문서에 맞춰 만들고, Supplier self-link는 `subcontractsTo` / `subcontractors`로 둔다.

## 문서 운영

- 스펙은 `docs/spec/` 6문서가 기준이다.
- 구조적 결정은 `docs/decisions/`에 ADR로 기록한다.
- 온톨로지, 링크, 액션, 스코어링 변경은 `docs/changelog/architecture.md`에 남긴다.
- 비밀값, access key, 이메일 원문, 쿠키, 세션 토큰은 출력하거나 커밋하지 않는다.
