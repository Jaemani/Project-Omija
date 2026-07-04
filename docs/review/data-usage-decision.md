# 데모 데이터 사용 결정과 활용 가능성

작성 조건: 민감 데이터 탐색·조회 시도 없음. 공개 문서와 현재 repo 상태만 기준.

## 결론

1. **호스팅/발표 화면:** 기업·자격증명·감염기기 개체는 synthetic 유지.
2. **공개 데이터:** CISA KEV, NVD, MITRE ATT&CK, URLhaus aggregate, HIBP breach
   metadata는 `PUBLIC_CONTEXT`로 사용 가능.
3. **StealthMole:** 기술적으로 활용 가능성은 있지만, 지금 repo에서는 live 조회를
   하지 않는다. 대신 공개 product/integration 문서에서 확인되는 field category와
   workflow를 data contract 카드로 보여준다.
4. **비공개 내부 검증:** 별도 승인·취급정책·비공개 환경이 있으면 raw가 아니라
   aggregate/readback/field-presence 수준으로만 검증할 수 있다. hosted page에는 올리지
   않는다.

## 왜 이렇게 나누는가

- 실제 유출 자격증명은 피해자 데이터라서 hosted demo와 녹화 화면에 올리면 2차 노출
  표면이 된다.
- 그렇다고 데이터를 전부 가상으로만 두면 설득력이 떨어진다. 그래서 공개 데이터는
  threat context로 넣고, private credential feed는 locked slot으로 표현한다.
- 심사자가 봐야 할 핵심은 "데이터를 얼마나 긁었나"가 아니라 "신호가 들어오면
  온톨로지가 어떤 판단을 강제하나"이다.

## StealthMole을 활용할 수 있는 방식

현재 가능한 방식:

- 공개 제품 페이지 기반으로 credential-protection field shape를 설명한다.
- 공개 integration 문서 기반으로 "도메인 기준 사용자/credential context를 가져오는
  risk-exchange류 워크플로가 가능하다"는 수준을 말한다.
- 데모 UI에는 locked feed slot, expected fields, masking/audit requirements만 둔다.

지금 하지 않는 방식:

- live API 호출;
- 실제 leaked username/password/cookie/session token 표시;
- private API 응답 저장;
- raw record를 hosted HTML/JSON에 포함.

## 공개 데이터 확보 결과

`uv run python scripts/public_context_snapshot.py` 결과:

```text
CISA KEV total: 1631
CISA KEV access-relevant: 863
MITRE ATT&CK selected techniques: 234
URLhaus sampled rows: 1000
URLhaus stealer/loader-tagged sample count: 42
HIBP public breach metadata count: 1015
NVD vpn/sso/citrix/fortinet/ivanti query totals: 73 / 25 / 309 / 672 / 379
```

이 데이터는 자격증명 증거가 아니라 "왜 VPN/SSO/mail/dev access surface를 감시해야
하는가"를 설명하는 public context다.

## 어디에 넣을지

- `out/data_coverage_map.html`: 공개 데이터, synthetic seed, engine result,
  locked sensitive slot을 한 화면에 표시.
- `RiskAssessment.components.public_context`: KEV/NVD/ATT&CK 요약.
- `ProgramExposure.components.threat_context`: URLhaus aggregate, program-facing
  access surface context.
- 발표 자료: HIBP/StealthMole 공개 자료는 "실제 유통 데이터가 어떤 형태인지"를
  설명하는 참고자료로만 사용.

## 발표 문장

> 실제 유출 자격증명은 시연 화면에 올릴 수 없는 피해자 데이터입니다. 그래서 개체는
> synthetic으로 두고, 공개 threat context와 실제 엔진/readback으로 시스템을 증명합니다.
> 승인된 private feed가 들어오면 같은 `of`, `targets`, `subcontractsTo`,
> `traverses`, `cites` 경로를 타게 됩니다.
