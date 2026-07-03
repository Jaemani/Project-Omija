# ADR-0005: 스코어링 가중 설계 원칙 (활성침해 지배)

날짜: 2026-07-03
상태: 승인

## 맥락
P3의 위험 스코어링은 이 프로젝트의 **핵심 차별점**이다(심사: Creativity·Technical
Execution). 경쟁 제품은 StealthMole 유출 레코드를 나열한다. 우리는 "지금 뚫리는 중"
(활성침해)을 순위 상단으로 강제해야 트리아지 골든타임을 확보한다. 따라서 스코어 공식은
두 가지를 동시에 만족해야 했다:
1. **활성침해가 항상 지배** — 활성 경로가 성립한 업체는 노출 규모가 큰 비활성 업체보다
   **반드시** 상단(architecture.md §3·§8, ontology.md §4).
2. **설명가능** — 각 기여분을 근거 레코드까지 역추적(provenance, CLAUDE.md §5).
수치를 코드 곳곳에 흩뿌리면 튜닝·심사 설명·재현이 어렵다. 가중 설계 원칙과 그 배치를
못박을 필요가 있었다.

## 결정
- **가중치·임계값은 한 곳**(`actions/scoring.py`의 `SCORING` dict)에만 둔다. 액션·스크립트·
  테스트는 이 config를 참조하며, **테스트는 매직넘버가 아니라 불변식**(활성>비활성, dedup
  카운트, grade 임계)을 고정한다. 구체 수치는 코드가 단일 출처.
- **활성침해 밴드 분리로 지배를 구조적으로 보장**: 비활성 점수는 `[0, base_cap]`(=60)로
  클램프, 활성 점수는 `[active_floor, 100]`(=70~100) 밴드로 상향. 밴드가 겹치지 않으므로
  **어떤 비활성 업체도 어떤 활성 업체를 앞설 수 없다**(튜닝과 무관하게 성립). 활성 여부는
  `FlagActiveCompromise`가 연 CompromiseIncident(경로 존재)로만 판정 — 스코어러는 가중만.
- **base 공식**(architecture.md §3): `Σ(노출 규모[dedup] + 최근성 decay + 비밀유형 가중 +
  모듈 신뢰도·소스 다양성) × criticality × tier`. 각 성분 상한(cap)으로 base 유계.
  - **노출 규모는 dedup 후**(ADR-없음, decision 3): 같은 `(identity, host, secret_type)`
    재유통은 1로 카운트해 콤보 리스트 부풀림 방지. 소스 다양성(모듈 수)은 별도 가산 신호.
  - **최근성 decay**: 반감기(half-life) 지수 감쇠 — 오래된 유출은 자연 감가.
  - **비밀유형**: 즉시 악용 가능한 plaintext/live cookie/token↑ > hash.
  - **모듈 신뢰도**: cds/ub(0.9) > cl(0.6) > cb(0.3) (어댑터 `CONFIDENCE` 재사용).
- **grade**: 즉시(≥70)/주의(≥40)/관찰. 활성 밴드(≥70) ⇒ 항상 "즉시".
- **provenance 강제**: `ComputeRisk`는 evidenced_by가 비면 액션 거부(예외). 근거 없는 점수
  금지.

## 근거
- **밴드 분리 vs 큰 가산치**: 활성에 큰 점수를 더하는 방식은 비활성 base가 충분히 크면
  역전 가능해 "항상 상단"을 보장 못 한다. 겹치지 않는 밴드는 수치 튜닝과 무관하게 불변식을
  보장 → 데모·테스트가 견고.
- **config 단일화 vs 산재**: 심사에서 "왜 이 업체가 1위인가"를 config 한 장으로 설명하고,
  기여분(components)으로 성분별 역추적. 재현성·설명가능성 확보.
- **dedup를 규모에만 적용**: provenance는 전 레코드 보존해야 근거 추적이 되지만, 규모
  카운트에 재유통을 그대로 넣으면 저신뢰 콤보가 순위를 왜곡. 규모=dedup, 근거=전량이 균형.

## 영향
- `actions/scoring.py`(config+공식), `actions/compute_risk.py`(evidence 강제),
  `actions/flag_active.py`(경로=활성 판정) 추가. 스토어에 risk_assessment·risk_evidence·
  compromise_incident 테이블(ADR-0003 스토어 확장).
- 가중 수치 변경은 이 ADR이 아니라 `SCORING` config에서 수행(이 ADR은 원칙만 규정). 원칙
  변경(밴드 분리 폐기 등) 시에만 새 ADR.
- day-1: 동일 공식을 AIP Logic으로 이관해도 밴드 분리·evidence 강제 원칙은 유지(hot-swap).
