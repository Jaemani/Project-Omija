# 데모 데이터 사용 결정과 활용 가능성

작성일: 2026-07-05. 본선 대비 업데이트. 해커톤용 StealthMole API 데이터는 이미 필터링된 승인 데이터로 확인되어 데모에 사용할 수 있다.

## 결론

1. **StealthMole 해커톤 API 데이터는 사용한다.**
   단, 공개 artifact에는 API key, JWT, raw provider envelope, password, cookie, token, full account dump를 넣지 않는다.

2. **공개 OSINT는 실제 스냅샷으로 사용한다.**
   CISA KEV, NVD, FIRST EPSS, MITRE ATT&CK, CISA RSS, URLhaus aggregate, HIBP breach metadata는 public context로 표시한다.

3. **사건 시나리오는 synthetic 유지한다.**
   협력사명, 프로그램명, credential/device 개체는 가상으로 두고, 판단 파이프라인과 온톨로지 경로를 증명한다.

4. **핵심 증명 방식은 lineage다.**
   "실제 유출 원문을 보여준다"가 아니라 "승인 provider row가 redaction boundary를 지나 ontology object, link, engine decision, human workflow로 변환된다"를 보여준다.

## 왜 정책을 바꾸는가

1차 심사 피드백은 명확했다. 컨셉은 흥미롭지만, data lineage와 실제 provider flow가 보이지 않아 아쉬웠다. 해커톤 API가 이미 필터링된 데이터라면 "민감 rail 잠금"만 강조하는 것은 방어적이고 설득력이 약하다.

따라서 본선 버전은 approved filtered StealthMole row-level lineage를 보여준다. 대신 raw secret과 재사용 가능한 credential material은 계속 차단한다.

## 표시 가능 / 금지

표시 가능:

- module: CL/CDS/CB/DT/TT
- run id, seed id, query type/value
- HTTP/module status, returned/written count
- source_ref hash
- account class, has_session_cookie boolean, infected_at timestamp, confidence
- normalized object names: `CredentialExposure`, `InfectedDevice`, `ThreatSource`
- link names: `of`, `targets`, `sourced_from`, `traverses`, `cites`
- decision object names: `RiskAssessment`, `CompromiseIncident`, `ProgramExposure`, `NotificationDraft`

금지:

- StealthMole access key / secret key
- JWT / Bearer token / refresh token
- raw provider response envelope
- raw password, cookie, token, session value
- full account dump
- 개인 식별 가능한 불필요 원문

## 발표 문장

> 첫 발표에서는 StealthMole rail을 너무 잠근 상태로 설명했습니다. 본선에서는 해커톤 API에서 이미 필터링된 승인 데이터를 사용해 row-level lineage를 보여줍니다. 단, API key, JWT, raw provider envelope, password/cookie/token은 공개 산출물에 남기지 않습니다. Omija가 보여주는 것은 유출 원문이 아니라, provider row가 온톨로지 객체와 판단 객체로 바뀌는 전 구간 계보입니다.

## 현재 산출물 연결

- `out/data_evidence_brief.html`: 공개 OSINT + approved StealthMole API 경계 설명.
- `out/data_lineage_live.html`: provider -> redaction -> ontology -> engine -> Foundry lineage.
- `out/data_lineage_live.json`: 공개 가능한 lineage summary. raw secret 없음.
- `out/private_candidate_import.json`: private/ignored validation artifact. 커밋 금지.
- `data/private_candidates/*.jsonl`: private raw/envelope probe. 커밋 금지.

## 여전히 과장하면 안 되는 것

- Band A는 침해 확정이 아니라 verify-first 후보.
- `targets`는 로그인 성공이 아니라 관측 대상 자산 경로.
- Foundry full E2E reasoning readback은 일부 backing dataset schema 이슈 때문에 완료 주장 금지.
- NotificationDraft는 사람 검토용 초안이며 자동 발송 기능이 아니다.
