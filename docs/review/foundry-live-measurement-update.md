# Foundry Live Measurement Update

작성일: 2026-07-05

## 결론

승인된 StealthMole 해커톤 API filtered data 150건은 Omija import boundary를 통과해 sanitized object/link CSV로 변환됐고, Foundry에도 두 레벨로 반영됐다.

1. 기존 ontology backing dataset 14개에 CSV 업로드와 explicit schema PUT 완료.
2. 별도 schema-aware `live_measurement_*` Foundry datasets 14개 생성.
3. Foundry SQL count 14/14가 local expected row count와 일치.
4. Ontology object OSDK readback은 아직 새 PK를 못 읽는다. 남은 작업은 Foundry ontology datasource/index refresh다.

## 실행 결과

### Provider collection

- Seed: `probe:domain:naver.com`
- Modules: CL/CDS/CB
- Returned: 150
- Written private raw: 150

### Import/normalization

- Input records: 150
- Normalized exposures: 150
- Rejected: 0
- Raw secret output: blocked
- Masking: `redacted:<hash>`

### Foundry-ready bundle

- Path: `out/foundry_live_measurement/`
- CredentialExposure: 150
- InfectedDevice: 150
- ThreatSource: 150
- Identity: 150 hashed IDs
- Domain: 17
- Link rows: 917 total

### Foundry load status

- Backing dataset CSV upload: 14/14 HTTP 200
- Backing dataset explicit schema PUT: 14/14 HTTP 200
- Separate schema-aware live measurement datasets: 14/14 created
- Foundry SQL counts: 14/14 matched expected counts
- Ontology OSDK readback: 0/7 live PKs visible yet

## 발표에서 말할 수 있는 것

> 실제 승인된 StealthMole 해커톤 row 150건을 Omija redaction boundary에서 안전 필드로 변환했고, Foundry schema-aware datasets에서 SQL count로 측정했다. 다만 Ontology object index readback은 아직 refresh 대기 상태라, “Foundry dataset 측정 완료 / Ontology readback pending”으로 분리해서 말한다.

## 근거 파일

- `out/foundry_live_measurement/measurement.html`
- `out/foundry_live_measurement/measurement.json`
- `out/foundry_live_measurement/upload_result.json`
- `out/foundry_live_measurement/schema_put_result.json`
- `out/foundry_live_measurement/schema_dataset_create_result.json`
- `out/foundry_live_measurement/sql_measurement_result.json`
- `out/foundry_live_measurement/readback_result.json`

## 남은 Foundry 작업

Ontology Manager 또는 MCP에서 datasource/index refresh를 수행해 `scripts/foundry_live_readback.py`가 `RESULT: OK`가 되게 한다. 이 전에는 full ontology E2E readback 완료라고 말하지 않는다.
