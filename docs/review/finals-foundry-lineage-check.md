# Finals — Foundry Lineage Check

작성: 2026-07-05. 민감 raw 필드는 조회·표시하지 않음.

## 현재 결론

Foundry에는 두 종류의 증거가 있다.

1. **Ontology 설계 증거**: of/targets 링크, action workflow, OSDK 0.2.0, action readback 5건.
2. **Live provider data 증거**: 승인된 StealthMole row 150건이 sanitized CSV로 변환되고, Foundry schema-aware datasets에서 SQL count 14/14로 측정됨.

아직 완결되지 않은 것은 live PK가 Ontology object index/OSDK readback에 보이는 단계다.

## 검증된 것

| 영역 | 상태 |
|---|---|
| 승인 StealthMole row 수집 | 150건 |
| Import/normalization | 150건, rejected 0 |
| Foundry-ready object/link CSV | 14개 생성 |
| 기존 ontology backing dataset upload | 14/14 HTTP 200 |
| 기존 ontology backing dataset schema PUT | 14/14 HTTP 200 |
| 별도 schema-aware live measurement datasets | 14/14 생성 |
| Foundry SQL count | 14/14 expected와 일치 |
| Workflow action readback | 5건 verified |
| OSDK object readback for live PK | index refresh pending |

## 발표에서 정확한 표현

말해도 되는 것:

> 실제 승인된 StealthMole 해커톤 데이터 150건을 redaction boundary를 거쳐 Foundry schema-aware datasets에 올렸고, SQL count로 Foundry 내부 측정까지 확인했습니다.

말하면 안 되는 것:

> live StealthMole row가 이미 Foundry Ontology object로 OSDK readback까지 완료됐다.

## 남은 캡처

- Foundry dataset list에서 `live_measurement_*_20260705_063216` dataset들이 보이는 화면
- SQL query result 또는 dataset preview에서 `CredentialExposure 150` count가 보이는 화면
- Ontology datasource/index refresh 후 `scripts/foundry_live_readback.py` 성공 화면
