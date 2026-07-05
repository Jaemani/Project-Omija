# Finals — Foundry Lineage Check (MCP verified)

작성: Fable, 2026-07-05. Palantir MCP로 온톨로지→데이터셋 lineage를 실사한 결과. raw 민감 필드는 조회·표시하지 않음.

Ontology: `ri.ontology.main.ontology.9dff216c-...` (apiName `ontology-cafadd0c-...`) · project `/Omija-e4b739/Omija` · Seed 폴더 `/Omija-e4b739/Omija/Seed`.

## 1. 검증된 Foundry lineage (증명 가능)

각 object/link type이 backing dataset을 가지고 있고, **차별점인 of/targets 링크 데이터셋은 스키마가 온전**하다.

| Ontology 엔티티 | Backing dataset (path) | 스키마 상태 |
|---|---|---|
| `of` 링크 (CredentialExposure→Identity) | `Seed/26_link_of` (`23f1a49e-…`) | **OK** — `left-CredentialExposure-primary-key`, `right-Identity-primary-key` |
| `targets` 링크 (CredentialExposure→Domain) | `Seed/27_link_targets` (`e6a2583b-…`) | **OK** — `left-CredentialExposure-primary-key`, `right-Domain-primary-key` |
| 워크플로 액션 8종 | ontology actions (merged proposal) | **OK** — acknowledge/assign/close incident, review/approve/export draft, confirm/reject merge |
| OSDK | `@omija/sdk` 0.2.0 | **published** — 액션 8종 포함 |
| 액션 readback | `out/foundry_action_chain.json` | **OK** — 5개 상태 전이가 오늘 실행·readback verified (HTTP 200) |

**즉 "provider→ontology→decision" lineage에서 `of`/`targets` 교차 조직 링크와 human-review 액션 감사가 Foundry 위에서 실증된다.** finals의 핵심 주장(of/targets 분리, human-on-the-loop)은 Foundry lineage로 뒷받침됨.

## 2. 막힌 부분 (overclaim 금지)

내가 벤더중립 rename 후 3개 seed 데이터셋에 raw CSV를 SNAPSHOT 업로드하면서 **스키마가 제거**됨 → 해당 object/link의 OSDK readback 차단.

| 엔티티 | Dataset (path) | 상태 |
|---|---|---|
| CredentialExposure object | `Seed/06_credential_exposure` (`7a4d3db0-…`) | **schemaNotFound** |
| ThreatSource object | `Seed/08_threat_source` (`4558faa7-…`) | **schemaNotFound** |
| `sourced_from` 링크 | `Seed/28_link_sourced_from` (`ea8ea557-…`) | **schemaNotFound** |

→ `ThreatSource.get('src:candidate:empty')` 등 이 3개 대상 readback은 재색인 불가. 원인·복구는 `docs/review/codex-foundry-schema-handoff.md` 참조. **Codex 작업**: 3개 데이터셋을 schema-aware로 재적재(또는 UI에서 schema 적용 + datasource sync).

**안전 표현 (finals):**
> Foundry 온톨로지와 액션 워크플로는 구성돼 있고, of/targets 링크와 액션 감사는 Foundry lineage로 확인했습니다. provider→decision 전체 reasoning은 로컬 SQLite 엔진에서 검증했으며, 일부 seed 데이터셋 스키마 정비는 진행 중입니다.

**금지:** "Foundry E2E readback 완전 해결" / "3개 데이터셋 정상".

## 3. finals에서 찍을 캡처 (정확한 위치)

이미 확보(3장): `objects-list`, `action-types`(=워크플로 액션 8종), `osdk-020`. 추가로 lineage 증명용:

1. **of 링크 datasource** — Ontology Manager → Link Types → `of` → Datasource 탭. `Seed/26_link_of` 매핑 보이게. (targets도 동일하게 `27_link_targets`)
2. **object type → backing dataset lineage** — 임의 object type(Supplier 등, 스키마 정상인 것) → Datasource 탭에서 dataset 연결.
3. **액션 감사 스트림** — CompromiseIncident 객체 → History 탭 (오늘 상태 전이). = `out/foundry_action_chain.json`과 동일 증거.
4. (스키마 정비 후) CredentialExposure readback 성공 화면 — 지금은 찍지 말 것(막힘).

> 캡처는 스키마 **정상인** 엔티티(of/targets 링크, Supplier, 액션)로만. 막힌 3개(CredentialExposure/ThreatSource object, sourced_from) 화면은 finals에서 노출하지 않음.

## 4. lineage 페이지 연계

`out/data_lineage_live.html`의 "Foundry Lineage Evidence" 섹션은 위 표1(검증됨)을 `LIVE_FOUNDRY`로, 표2(막힘)를 "스키마 정비 중"으로 렌더한다. sanitized StealthMole run 아티팩트가 없으면 provider/normalized 단계는 "waiting for approved sanitized run" empty-state로 둔다(가짜 데이터 금지).
