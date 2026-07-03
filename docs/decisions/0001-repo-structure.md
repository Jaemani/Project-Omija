# ADR-0001: repo 구조·문서 분리

날짜: 2026-07-03
상태: 승인

## 맥락
스펙·의사결정·변경이력이 한 폴더에 섞이면 해커톤 진행 중 추적이 불가능해지고, 콜드스타트하는 에이전트가 어떤 문서가 "현재 스펙"이고 어떤 것이 "왜 이렇게 됐는지 기록"인지 구분하지 못해 혼란을 겪는다.

## 결정
- `docs/spec/` — 기존 스펙 6문서(direction.md, ontology.md, data-sources.md, aip-integration.md, architecture.md, PROMPTS.md) 이동. 문서 내용·상호 참조는 그대로 유지(동일 폴더 이동이므로 파일명 기반 참조 유효).
- `docs/decisions/` — ADR(구조적 의사결정 기록).
- `docs/changelog/` — 온톨로지·아키텍처 변경로그.
- `CLAUDE.md`, `README.md`는 루트 유지.
- 코드는 스펙 문서(`docs/spec/data-sources.md` §2)가 정한 경로를 그대로 따라 `adapter/`를 루트 패키지로 둔다. 이후 correlation·frontend 등 모듈을 루트에 추가.

## 근거
- `CLAUDE.md`는 Claude Code가 루트에서 자동 로드하므로 루트 유지가 필수.
- 스펙 문서들은 서로 파일명만으로 참조하므로 같은 폴더로 함께 이동하면 참조가 깨지지 않는다.
- 용도별 분리(스펙=현재 상태, ADR=결정 이력, changelog=변경 이력)로 심사·회고 시 provenance를 확보한다 — CLAUDE.md 원칙 "provenance 강제"와 동일한 사고를 문서 운영에도 적용.

## 영향
- 앞으로 스펙 문서 참조 시 `docs/spec/...` 경로 사용(CLAUDE.md·README.md 갱신 완료).
- 구조적 결정은 이후 ADR로, 온톨로지/아키텍처 변경은 changelog로 남긴다(§CLAUDE.md 문서 운영 규칙).
- 코드 디렉토리(`adapter/` 등)는 루트에 위치, `docs/`와 분리.
