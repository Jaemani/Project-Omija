# data-sources.md — StealthMole 실계약 + 어댑터 + 목 (Supply-chain Cred)

**핵심**: 이 트랙은 StealthMole API에 설계가 종속. 접근은 **내일부터** 열림 → 오늘은 **contract-first**로 어댑터 인터페이스+목(mock)을 만들고, 접근 열리면 어댑터만 hot-swap.

아래 API 계약은 StealthMole 공식 통합 코드(Cisco XDR/Netskope CRE 플러그인, v2)에서 **역설계·검증**했다. `[검증됨]` = 소스에서 확인, `[확인필요]` = day-1 접근 시 실측할 것.

> ⚠️ 합법성: StealthMole **제공 계정·API 정상 사용만**. 무단 스캐닝/침투/크리덴셜 재사용 금지. 협력사 실명단 미사용(데모=합성 도메인). 유출 비밀번호는 화면에 원문 표시 말고 마스킹.

---

## 1. StealthMole API v2 — 검증된 계약

### 베이스 · 인증 [검증됨]
- Base URL: `https://api.stealthmole.com/v2/`
- 자격: **access_key + secret_key** 페어(해커톤 이메일로 발급). 환경변수: `STEALTHMOLE_ACCESS_KEY`, `STEALTHMOLE_SECRET_KEY`.
- 인증: **JWT (HS256)**. 요청마다 새 토큰 생성. payload = access_key + nonce(uuid4) + iat(현재 UTC epoch). secret_key로 서명. 헤더 `Authorization: Bearer <jwt>`.

```python
# 검증된 인증 (StealthMole 공식 통합 코드 기반)
import jwt, uuid, datetime, requests
from datetime import timezone

def sm_headers(access_key: str, secret_key: str) -> dict:
    payload = {
        "access_key": access_key,
        "nonce": str(uuid.uuid4()),
        "iat": int(datetime.datetime.now(timezone.utc).timestamp()),
    }
    token = jwt.encode(payload, secret_key)   # HS256 default
    return {"Authorization": f"Bearer {token}"}
```

### 엔드포인트 [검증됨]
| 목적 | 메서드/경로 | 파라미터 | 응답 |
|---|---|---|---|
| 인증확인·쿼터 | `GET /v2/user/quotas` | — | `{"CDS":{"allowed":N}, ...}`, 401 시 `{"detail":...}` |
| 모듈 검색 | `GET /v2/{module}/search` | `query="{type}:{value}"`, `order=asc` | `{"data":[...]}` |
| 모듈 익스포트(대량+시간필터) | `GET /v2/{module}/export` | `query`, `limit=0`(=전체), `exportType=json`, `start=<unix>` | `{"data":[{...}, ...]}` |

- `{module}` 자리에 모듈 코드 소문자. observable `{type}` ∈ `email` `domain` `ip` `url`. 예: `query=domain:example-supplier.com`.
- `start`(unix epoch) = 이 시각 이후 레코드만 → **증분 폴링**에 사용(조기경보 핵심).

### 모듈 코드 [검증됨 — 상관에 쓸 것]
| 코드 | 이름 | 소스 | 신뢰도 | observable | 우리 용도 |
|---|---|---|---|---|---|
| **cds** | Compromised Dataset | Infostealer Malware | High | email,domain,ip,url | **스틸러 감염기기 = 활성침해 핵심** |
| **ub** | ULP Binder | URL:LOGIN:PASS 로그 | High | url,domain,email | 어떤 서비스에 어느 계정 유출됐나 |
| **cl** | Credential Lookout | Breached Servers | Medium | email,domain | 유출 자격증명 |
| **cb** | Combo Binder | Combo Lists | Low | email,domain | 재유통 콤보(저신뢰) |

### 모듈 코드 [확인필요 — 발급 계정에 있으면 활용]
`dt`(Darkweb Tracker), `tt`(Telegram Tracker), `rm`(Ransomware Monitoring), `gm`(Government Monitoring), `lm`(Leaked Monitoring). day-1에 `/user/quotas`로 **어떤 모듈이 열렸는지 먼저 확인**하고 상관 대상 확정.

### 레코드 스키마
- `ub/export` 레코드 [검증됨]: `{"user": <이메일/로그인>, "password": <비번>, "host": <소스 호스트/URL>}`.
- **`cds` 레코드 [확인필요]**: 스틸러 로그 → 감염기기·malware·감염일시·쿠키/세션 필드가 있을 것으로 기대(활성침해 판별의 핵심). **day-1에 실측해 아래 Exposure 스키마의 device.* 필드 채움.** 없으면 감염 최근성(레코드 timestamp)으로 대체.

### 쿼터/레이트 [검증됨 개념]
- 모듈별 `allowed` 크레딧. 쿼리 전 `/user/quotas`로 잔량 확인(코드에서 `CDS.allowed <= 0` 체크). **크레딧 절약**: 도메인 단위 배치, 캐시, `start`로 증분.

---

## 2. 어댑터 인터페이스 (contract-first, 오늘 구현)
StealthMole 응답을 온톨로지 객체로 정규화하는 단일 관문. 실 API와 목이 **같은 인터페이스**를 구현 → hot-swap.

```python
# adapter/base.py
from typing import Protocol, Iterable

class ExposureSource(Protocol):
    def quotas(self) -> dict: ...
    def search(self, module: str, obs_type: str, value: str,
               start: int | None = None) -> list[dict]: ...   # raw records

# adapter/stealthmole.py  → 실 API (위 §1 계약)  [day-1 연결]
# adapter/mock.py         → 합성 레코드 (아래 §3)  [오늘 사용, 데모 백업]
```
정규화 함수 `normalize(module, raw) -> Exposure`는 두 소스 공통. 온톨로지 매핑은 `ontology.md`.

## 3. 목(Mock) 데이터 계약 (오늘 빌드·데모 재현성)
`adapter/mock.py`가 검증된 스키마대로 합성 레코드 생성. **모의 데이터임을 명시**. 활성침해 케이스를 의도적으로 포함(스코어링 검증용).
```
mock cds record 예: {"user":"kim@supplier-a.example","password":"***","host":"vpn.supplier-a.example",
                     "malware":"RedLine","infected_at":<최근 unix>,"has_cookie":true,"account_type":"vpn"}
mock cl record 예: {"user":"admin@supplier-b.example","password":"***","host":"mail.supplier-b.example"}
```

## 4. 협력사 도메인 레지스트리 (합법·샘플)
- 실명단 민감 → **공개/합성 도메인 시드**. 각 업체 `{company, domain(s), tier(1|2), criticality, supplies→prime, assets(이메일 도메인)}`.
- 5~10개 샘플. 일부는 목 Exposure와 매칭되게(데모), 일부는 clean.
- 무단 스캐닝 금지 — 공개 도메인/이메일 패턴만.

## 5. 정규화 스키마 (Exposure → 온톨로지)
```
Exposure {
  id, source:"stealthmole", module:"cds|ub|cl|cb", source_ref, fetched_at,
  identity: { email?, username? },            # → Identity 객체
  secret: { type:"plaintext|hash|cookie|token", masked_value, present:bool },
  host,                                         # 소스 서비스
  device: { infected_at?, malware?, has_session_cookie?, account_type? },  # cds=활성 신호
  observed_at, confidence: 0..1                 # 모듈 신뢰도 반영(cds/ub High..cb Low)
}
```
활성침해 판별 필드(`device.infected_at` 최근성, `has_session_cookie`, `account_type∈{vpn,admin}`)를 **반드시 보존** — 스코어링 핵심. citation = `source`+`module`+`source_ref`+`fetched_at`.
