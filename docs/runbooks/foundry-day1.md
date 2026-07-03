# Runbook — Foundry / OSDK day-1 (P0-A, part A)

목적: **AIP가 spine**임을 증명하는 최소 왕복. Foundry 콘솔에서 Object/Link/Action을
손으로 만들고 OSDK를 발행해 Python으로 Supplier를 write/read 한다. 콘솔 단계는
자동화 불가라 유저가 직접 수행한다(코드 파이프 검증은 이미 SQLite로 완료 — ADR-0003).

전제: build.palantir.com Developer Tier 가입됨(무료). StealthMole 접근과 무관.

---

## 0. 체크리스트 (순서대로)
- [ ] 1. build.palantir.com 로그인 (Developer Tier)
- [ ] 2. Object Type `Supplier` 생성
- [ ] 3. Object Type `Domain` 생성 + Link `owns` (Supplier 1—N Domain)
- [ ] 4. Action Type `ComputeRisk` 생성 (Supplier 대상, RiskAssessment 파생)
- [ ] 5. Developer Console에서 OSDK 패키지 발행
- [ ] 6. `pip install <발행된-osdk>` (venv: `uv pip install ...`)
- [ ] 7. Python으로 Supplier write → read 왕복
- [ ] 8. 성공 로그를 `docs/spec/aip-integration.md` "확인된 OSDK 스니펫"에 반영

---

## 1. Object Type: Supplier
Foundry → Ontology Manager → **New object type**.
- API name: `Supplier`
- Primary key: `id` (String)
- 속성: `name` (String), `tier` (Integer, 1|2), `criticality` (String: high|medium|low)
- (백킹 데이터셋은 빈 것으로 시작 — Action/OSDK로 채움)

로컬 검증 스토어(`store/sqlite.py`)의 `supplier` 테이블과 **동일 스키마**여야 hot-swap이 성립.

## 2. Object Type: Domain + Link `owns`
- Object `Domain`: PK `fqdn` (String), 속성 `supplier_id` (String)
- Link type **`owns`**: `Supplier` (1) —owns→ `Domain` (N). Join key = `Domain.supplier_id` ↔ `Supplier.id`.
- 온톨로지 근거: `docs/spec/ontology.md` §2 "Supplier —owns→ Domain (1:N, 상관 키)".

## 3. Action Type: ComputeRisk
- Action `ComputeRisk`, 대상 파라미터 `supplier: Supplier`.
- 최소 버전: Supplier에 `last_scored_at`(Timestamp) 하나 세팅하는 edit만.
  (진짜 스코어링은 P3에서 AIP Logic으로. 오늘은 **Action이 상태를 전이**하는 것만 증명.)
- 규칙 메모: 파생 객체(RiskAssessment)는 evidence 링크 없으면 거부 — 온톨로지 레벨 provenance 강제(§ontology.md §3). 오늘 버전엔 evidence 파라미터 자리만 잡아둔다.

## 4. OSDK 발행
Developer Console → 앱 생성 → 위 온톨로지 선택 → **Python OSDK** 패키지 발행.
- 발행되면 pip 설치 URL/패키지명과 `hostname`, OAuth 클라이언트가 나온다.
- 패키지명 예: `myproject_sdk` (실제 이름은 콘솔에서 확인).

## 5. 설치 + 왕복 스니펫
```bash
uv pip install <발행된-osdk-패키지>       # Developer Console 발행 후
# 인증 값은 환경변수로 (하드코딩 금지)
export FOUNDRY_HOSTNAME="<your>.palantirfoundry.com"
export FOUNDRY_TOKEN="<oauth-or-token>"
```
```python
import os
from myproject_sdk import FoundryClient          # 발행된 패키지명으로 교체
from myproject_sdk.core.auth import UserTokenAuth # SDK 버전별 경로 상이 [확인필요]

client = FoundryClient(
    auth=UserTokenAuth(token=os.environ["FOUNDRY_TOKEN"]),
    hostname=os.environ["FOUNDRY_HOSTNAME"],
)

# write: Supplier 생성 (Action 경유가 정석; 최소검증은 직접 create)
client.ontology.actions.create_supplier(          # Action 이름은 콘솔 정의대로
    id="sup-a", name="Alpha Precision", tier=1, criticality="high",
)

# read 왕복
sup = client.ontology.objects.Supplier.get("sup-a")
print(sup.id, sup.name, sup.tier)                 # → sup-a Alpha Precision 1

# owns 링크 read (Domain)
for d in sup.owns.iterate():                      # 링크 API 이름 [확인필요]
    print(d.fqdn)
```
성공기준: `Supplier.get("sup-a")`가 방금 쓴 값을 돌려준다 = OSDK 왕복 성공.

## 6. 로컬 스토어와의 정합 (hot-swap 근거)
로컬 `OntologyStore`(SQLite)와 OSDK가 **같은 객체/링크 이름**을 쓰므로, 후속 코드는
스토어 구현만 바꾸면 된다(어댑터 hot-swap과 동일 패턴, ADR-0003).
- `store.base.OntologyStore` Protocol ↔ 미래 `FoundryOntologyStore`(OSDK 백엔드).
- 필드 매핑: `supplier(id,name,tier,criticality)` = Object `Supplier` 속성 그대로.

---

## 7. 막힐 때 — Morph 멘토 질문 목록
1. Developer Tier에서 Object Type 백킹 데이터셋 없이 Action-only write가 가능한가? 최소 경로는?
2. Python OSDK 2.x의 최신 auth 임포트 경로(`UserTokenAuth` vs client 통합)는? 토큰 스코프는?
3. Action에서 파생 객체(RiskAssessment)에 evidence 링크를 **필수**로 강제하는 설정 위치는?
4. Link type join key 설정 시 양쪽 데이터셋이 비어 있어도 되는가?
5. AIP Logic 함수(RiskScorer)를 OSDK 앱에서 호출하는 최소 예제/권한(read-only)?
6. Dev Tier 리소스/레이트 제한 — cds 대량 ingest 시 병목 지점은?
7. OSDK 패키지 재발행 시 버전 핀·캐시 무효화 베스트프랙티스?

## 8. 실패 시 폴백 (보험, plan A 아님)
콘솔/OSDK가 시간 내 안 되면 **로컬 SQLite 스토어로 화면·파이프 유지**(오늘 이미 검증됨).
온톨로지 설계는 재사용 → 후에 Foundry 이관. AIP=spine 목표는 유지, 데모는 안 멈춘다.
