# Runbook — Foundry / OSDK day-1 (P0-A, part A)

Current status as of 2026-07-05: use this only for Foundry/OSDK ontology
operations. Do not use it to resume live credential-feed or public-feed work.

목적: **AIP가 spine**임을 증명하는 최소 왕복. Foundry 콘솔에서 Object/Link/Action을
손으로 만들고 OSDK를 발행해 Python으로 Supplier를 write/read 한다. 콘솔 단계는
자동화 불가라 유저가 직접 수행한다(코드 파이프 검증은 이미 SQLite로 완료 — ADR-0003).

전제: build.palantir.com Developer Tier 가입됨(무료). StealthMole 접근과 무관.

---

## 0. 체크리스트 (순서대로)
- [ ] 1. build.palantir.com 로그인 (Developer Tier)
- [ ] 2. Object Type `Supplier` 생성
- [ ] 3. Object Type `Domain` 생성 + Link `owns` (Supplier 1—N Domain)
- [ ] 4. Action Type `Compute Risk` 생성 (전제 A/B 선행 → Modify object rule로 `last_scored_at` 전이)
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

## 3. Action Type: Compute Risk (검증된 절차)

최소 버전: Action 실행이 Supplier의 `last_scored_at`(Timestamp)을 갱신하는 edit 하나.
(진짜 스코어링은 P3에서 AIP Logic으로. 오늘은 **Action이 상태를 전이**하는 것만 증명.)

절차는 2026-07-04 Palantir 공식문서로 검증됨:
- Action rules(Modify object): https://www.palantir.com/docs/foundry/action-types/rules
- 파라미터 기본값·컨텍스트 값(time of submission): https://www.palantir.com/docs/foundry/action-types/parameters-default-value
- Object edits 활성화: https://www.palantir.com/docs/foundry/object-link-types/edit-properties
- 파라미터 개요·검증: https://www.palantir.com/docs/foundry/action-types/parameter-overview
- inline edit 제약: https://www.palantir.com/docs/foundry/action-types/inline-edits
- edit 적용 방식: https://www.palantir.com/docs/foundry/object-edits/how-edits-applied

### 3-0. 개념 — Action Type = 3요소 (먼저 이해하면 안 헤맴)
Action Type은 아래 3개로 구성된다(docs: `action-types/rules`, `parameter-overview`).
- **(a) Parameters** — 사용자/앱이 채우는 **폼 입력**(어떤 Supplier를 채점하나 등). 그 자체로는 객체를 바꾸지 않음.
- **(b) Rules / edits** — 파라미터를 받아 **실제 객체를 수정**하는 부분. 세 종류: **Modify object**(기존 속성 변경 ← 오늘 이것), **Create object**(새 객체 생성 ← P3의 RiskAssessment), **Create/delete link**(링크 추가·삭제 ← P3의 evidenced_by). 적용 방식은 `object-edits/how-edits-applied`.
- **(c) Submission criteria / validation** — **제출 게이트**. 조건 불충족이면 제출이 막힘(예: 리스트 not-empty). 오늘은 최소라 안 걸고, **P3에서 provenance 강제(evidence 비면 거부)에 사용**.

### 3-A. 전제 A — Supplier에 `last_scored_at` (Timestamp) 프로퍼티
Ontology Manager → Supplier object type → **Properties** 탭 → 새 프로퍼티 `last_scored_at` (Timestamp).
백킹 옵션은 2갈래 — UI에 보이는 쪽으로:
- (a) **"Edits only"** 백킹 옵션이 보이면 그걸 선택 — 백킹 데이터셋 변경 불필요, 값은 Action edits로만 쓰인다. [확인필요 — Dev Tier UI에 노출되는지]
- (b) 안 보이면 백킹 데이터셋에 timestamp 컬럼 추가(빈 값 OK) 후 프로퍼티에 매핑.

프로퍼티를 **저장하고 온톨로지 변경을 배포(save/deploy)까지** 마쳐야 Action 편집기에서 보인다.

### 3-B. 전제 B — Supplier에 edits 활성화 (막힘 1순위 원인)
Object Storage V2 기준, Supplier object type의 **Datasources/설정에서 "enable edits" 토글 ON**
(출처: object-link-types/edit-properties). 이걸 안 켜면 Modify object rule이 **저장되지 않거나
Action 실행이 런타임에 거부**된다. Compute Risk가 막히면 여기부터 확인.

### 3-C. Action 생성
1. Ontology Manager → **Action types → New action type**.
2. 이름 `Compute Risk` — 생성 시 **API name을 기록**해 둔다(OSDK 호출명은 display name이 아니라 API name).
   - **inline edit로 만들지 말 것.** inline edit는 단일 객체·object-reference default 위주라 아래 4의 제출-시각 special value 매핑과 evidence의 object-set 수신이 어렵다(docs: `inline-edits`). **일반 액션(폼 제출형)** 으로 생성.
3. 파라미터 `supplier` = **Object reference** → 타입 Supplier, **Required**.
4. Rule = **Modify object** → 대상 오브젝트 = `supplier` 파라미터 →
   `last_scored_at` 값 = **contextual value "time of submission"** (= Current Time special value).
   (문서 검증: string/timestamp 프로퍼티는 제출 시각 컨텍스트 값을 지원 — 숨은 timestamp 파라미터 트릭 불필요.)
   - **콘솔 버전에 "Current Time"/"time of submission" special value가 안 보이면 대안**: 파라미터 `scored_at` = **Timestamp**, **default value = Current time**(`parameters-default-value`) 추가 → rule에서 `last_scored_at ← scored_at`. 결과 동일(제출 시각이 찍힘), 폼에서 자동 채워짐.

### 3-D. evidence 자리 (오늘은 선언만, 이유가 핵심)
- **목표 형태(P3에서 실사용)**: 파라미터 `evidence` = **Object set (list) → Exposure**, optional.
- **오늘은 자리만** 잡는다(거부 조건에 안 건다). 이유: RiskAssessment를 **실제로 create하는 건 P3**이고, "provenance 강제 = evidence 비면 거부"는 그때 **Submission criteria(§3-0 c)로 켠다.** 오늘 Modify object만 하는 액션엔 거부 게이트가 불필요.
- **Exposure object type이 아직 없으면**(오늘 체크리스트는 Supplier+Domain만 생성): object-set 파라미터를 못 만드니 자리표시로 `evidence_note`(String, optional)만 두고, Exposure object type 생성 후 `evidence` = Object set → Exposure로 격상.
- P3 격상 = evidence(**object set, required**) + **Submission criteria "list not empty"** → "근거 없으면 실행 거부". 로컬 `actions/compute_risk.py`가 이미 이 규칙(`EvidenceRequired`)을 구현 → 대응표 §3-G.

### 3-E. 검증 (성공기준)
Object Explorer → Supplier 객체 하나 열기 → **Actions → Compute Risk** 실행 →
`last_scored_at`이 제출 시각으로 갱신됐는지 확인. 이것이 "Action이 상태를 전이"의 증명.
(OSDK에서도 같은 Action을 API name으로 호출 — §5.)

### 3-F. 흔한 막힘
| 증상 | 원인 | 조치 |
|---|---|---|
| Modify object rule 저장 안 됨 / 실행 거부 | edits 미활성 (전제 B) | Datasources에서 enable edits ON |
| Action 편집기에 `last_scored_at` 안 보임 | 프로퍼티 미저장·미배포 상태로 Action 생성 시도 | 전제 A 저장·배포 후 재시도 |
| OSDK 호출 시 Action 못 찾음 | API name과 display name 혼동 | 콘솔에서 API name 재확인 |
| 파라미터 object type 목록에 Supplier 안 뜸 | 방금 만든 object type 인덱싱 지연 | 수 분 대기 후 새로고침 |
| Action은 성공했는데 `last_scored_at` 안 바뀜 | writeback(enable edits) 미활성 | 전제 B 재확인(§3-B) |

### 3-G. 개념 브리지 — 콘솔 최소버전 ↔ 로컬 최종버전
오늘 콘솔이 증명하는 것 = **"Supplier: 미채점 → 채점됨" 상태 전이**(스멜테스트 §3: 액션=상태전이). RiskAssessment 생성·evidence 거부·활성 가중은 **P3**. 로컬 `actions/compute_risk.py`가 이미 최종 규칙을 구현하므로 대응을 고정한다:

| 항목 | 오늘 콘솔 최소버전 | 로컬 최종버전 (`actions/compute_risk.py`) |
|---|---|---|
| 효과(edit) | **Modify object**: `Supplier.last_scored_at ← 제출 시각` | **Create object**: `RiskAssessment`(score·grade·active_flag·components) |
| provenance | `evidence` 파라미터 **선언만** | `evidenced_by` 비면 **`EvidenceRequired` 거부** |
| 활성침해 | 없음 | `CompromiseIncident` 존재로 `active_flag` → 밴드 상향 |
| 대상 링크 | 없음 | `RiskAssessment —evidenced_by→ Exposure/Device` 생성 |
| 제출 게이트 | 없음(최소) | evidence non-empty (P3에서 **Submission criteria**로) |

→ 오늘은 로컬 로직의 **상태 전이 뼈대만** 콘솔로 재현. P3에서 Modify → **Create object + evidenced_by 링크 + Submission criteria**로 확장해 로컬과 정합.

### 3-H. OSDK 왕복 확인 (발행 §4 후)
Action 발행 뒤 Python에서 호출 → read-back으로 상태 전이 확인 (패턴: `aip-integration.md` §2-(3)).
```python
# import/호출 경로는 발행된 OSDK 패키지명에 따름 [확인필요]
client.ontology.actions.compute_risk(
    supplier="sup-a",
    evidence=[],          # 오늘 optional; P3에서 Exposure id 리스트
)

sup = client.ontology.objects.Supplier.get("sup-a")
print(sup.last_scored_at)   # None → 방금 찍힌 제출 시각이면 상태 전이 왕복 성공
```
성공기준: 호출 전 `last_scored_at`=None → 호출 후 값 → **Action=상태전이 왕복 성공**. 값이 안 바뀌면 §3-B(writeback) 먼저 확인.

### 3-I. 막힘 대응 — Morph 멘토 질문 (Compute Risk 전용 4개)
1. Modify object rule에서 property 값으로 **"Current Time"/time-of-submission special value**를 넣는 정확한 위치는? (없으면 파라미터 `default = Current time` 우회가 맞나?)
2. Object Storage V2 객체에 Action write를 저장하려면 **edits / writeback 토글**을 정확히 어디서 켜는가?
3. **Exposure를 여러 개(리스트)로 받는 파라미터**의 정확한 타입 이름은? (**Object set** vs Object reference list — 어느 쪽?)
4. Submission criteria로 **"리스트 파라미터가 비어있지 않을 때만 제출 허용"**(evidence not empty)을 거는 정확한 설정 경로는? (P3 provenance 강제에 필요)

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
