# D4D Submission Guide

제출 폼 기준 최종 입력 가이드.

## Project Title

```text
Omija: Ontology-Based Supply-Chain Credential Exposure Early Warning
```

한국어 보조 제목이 필요하면:

```text
Omija: 방산 공급망 자격증명 노출 조기경보 시스템
```

## Track

선택:

```text
T2 · OSINT & 국방인텔
```

보조로 강조할 수 있는 연결성:

```text
T3 · 전장네트워크·C2
```

단일 선택이면 T2가 우선이다. 이유는 공개/민간 위협 신호, 유출 자격증명 후보, 인포스틸러 감염 후보, 공개 OSINT 컨텍스트를 공급망 지식그래프로 융합해 의사결정으로 바꾸는 프로젝트이기 때문이다.

## Repository

```text
https://github.com/Jaemani/Project-Omija
```

## Demo

Vercel 배포가 준비되면 Vercel URL을 우선 사용한다. 아직 없으면 아래 GitHub Pages URL을 fallback으로 쓴다.

Vercel 설정 권장값:

```text
Framework Preset: Other
Build Command: make build
Output Directory: out
Install Command: uv sync
```

현재 repo의 `vercel.json`은 `outputDirectory: "out"`과 `/ -> /omija_console_home.html` rewrite를 제공한다. Vercel UI에서 별도 build를 걸지 않으면 커밋된 `out/` 정적 파일을 그대로 서빙한다.

랜딩 fallback:

```text
https://jaemani.github.io/Project-Omija/
```

보조 데모 URL:

```text
https://jaemani.github.io/Project-Omija/omija_demo.html
https://jaemani.github.io/Project-Omija/data_coverage_map.html
https://jaemani.github.io/Project-Omija/data_evidence_brief.html
https://jaemani.github.io/Project-Omija/program_threat_view.html
```

폼에 Demo URL이 하나만 들어가면 랜딩만 넣는다.

## Description

아래 문안은 5,000자 제한 안에 맞춘 제출용 설명이다.

```markdown
## Summary

Omija is an ontology-based early warning system for supply-chain credential exposure in defense manufacturing. It connects leaked-credential candidates, infostealer-device candidates, public OSINT context, and supplier relationships into a graph-backed decision workflow.

The goal is not to display leaked records. The goal is to answer a harder operational question: which supplier and defense program should an analyst verify first, why, and through which evidence path?

## Problem

Defense supply chains are multi-tier networks. A risk signal may start from a second-tier supplier account, appear against a prime contractor VPN or admin asset, and affect a defense program several graph hops away.

Flat leak tables usually rank by volume: more leaked accounts appear more urgent. That misses the more important case: a small number of recent infostealer signals with session or privileged-access context that create an active-compromise candidate path.

## Approach

Omija models the problem as an ontology:

- `CredentialExposure.of` identifies whose account the exposure belongs to.
- `CredentialExposure.targets` identifies which asset the credential was observed against.
- `Supplier.subcontractsTo*` allows variable-depth traversal from lower-tier suppliers to primes and programs.
- `RiskAssessment`, `CompromiseIncident`, `ProgramExposure`, and `NotificationDraft` turn evidence paths into auditable decision objects.

This separation is the core design choice. A supplier employee credential observed against a prime VPN is not just "one leaked account"; it is a cross-organization verification path.

## Data Boundary

public demo separates data into three layers:

1. Public OSINT context: real non-sensitive snapshots CISA KEV, NVD, FIRST EPSS, MITRE ATT&CK, CISA advisories, URLhaus aggregate metadata, HIBP breach metadata.
2. Approved StealthMole hackathon signals: used as sanitized row-level lineage. API keys, JWTs, raw provider envelopes, and reusable secret material are not stored in the repository or static demo pages.
3. Synthetic incident scenario: fictional suppliers, credentials, devices used prove reasoning engine safely.

system keeps API credentials and reusable secret material out of the demo surface. Approved hackathon provider rows enter through the normalization boundary, preserve provenance, and emit candidate objects for human review.

## What We Built

- A Foundry-style ontology design with supplier, domain, identity, exposure, device, threat-source, risk, incident, program exposure, and notification draft objects.
- A local SQLite validation engine that runs correlation, active-candidate detection, risk ranking, blast-radius propagation, and notification draft generation.
- A static demo console showing steady-state monitoring, data coverage, public-context evidence, incident reasoning, and program-level rollup.
- A private connector boundary for approved sensitive exposure-provider checks, with raw-secret blocking and normalized import validation.
- A presentation-safe data evidence and lineage pages showing public OSINT counts plus approved StealthMole hackathon API row-level lineage.

## Risk Logic

Omija ranks by risk band before score:

- Band A: active-compromise candidate path exists.
- Band B: high-value correlated exposure, active condition incomplete.
- Band C: passive or stale credential exposure.
- Band D: weak or unlinked context.

Band A is not a confirmed breach. It means "verify this first" using VPN, SSO, IAM, EDR, mail logs, or supplier confirmation.

## Result

In the synthetic evaluation, active-compromise candidates are ranked above high-volume passive leaks, and supplier risk propagates through the supply-chain graph to program-level exposure. The system generates human-reviewed notification drafts with cited evidence rather than sending automatic notifications.

## Why It Matters

Omija demonstrates how OSINT and credential-exposure signals can become auditable defense intelligence. It is not a leak viewer; it is a graph-based prioritization and decision-support system for supply-chain security teams.
```

## Screenshots

최대 8장. 권장 순서:

1. `out/omija_console_home.html`
   - 평시 콘솔 전체.
   - 보여줄 내용: 감시 범위, 조용함의 증명, private provider readiness.

2. `out/data_coverage_map.html`
   - 데이터 커버리지 맵.
   - 보여줄 내용: synthetic seed, public context, engine/live evidence, sensitive slot 분리.

3. `out/data_evidence_brief.html` / `out/data_lineage_live.html`
   - 공개 데이터/StealthMole 해커톤 데이터 경계.
   - 보여줄 내용: CISA KEV/NVD/EPSS/ATT&CK 등 실제 공개 데이터 + 승인된 StealthMole 해커톤 API row-level lineage.

4. `out/omija_demo.html`
   - 사건 보고서 상단/트리아지.
   - 보여줄 내용: active-on-top 우선순위.

5. `out/omija_demo.html`
   - `of` vs `targets` 또는 blast radius 섹션.
   - 보여줄 내용: cross-organization path.

6. `out/omija_demo.html`
   - notification draft / response workflow.
   - 보여줄 내용: 자동 발송이 아니라 human-reviewed draft.

7. Foundry 캡처 `out/captures/objects-list.png`
   - Ontology Manager 객체 목록.

8. Foundry 캡처 `out/captures/link-graph.png` 또는 `out/captures/action-types.png`
   - 링크 그래프나 Action Types.

## Screenshot Capture Checklist

웹 캡처는 브라우저에서 아래 URL을 열고 찍는다.

```text
https://jaemani.github.io/Project-Omija/
https://jaemani.github.io/Project-Omija/data_coverage_map.html
https://jaemani.github.io/Project-Omija/data_evidence_brief.html
https://jaemani.github.io/Project-Omija/omija_demo.html
```

Foundry 캡처 파일명:

```text
out/captures/objects-list.png
out/captures/link-graph.png
out/captures/action-types.png
out/captures/merged-proposal.png
out/captures/incident-history.png
out/captures/osdk-020.png
```

캡처를 넣은 뒤 사건 보고서 재생성:

```bash
uv run python scripts/omija_demo.py
```

## Do Not Claim

제출 설명이나 발표에서 다음을 주장하지 않는다.

- 실제 침해를 확정했다.
- 실제 유출 자격증명 원문을 데모에 저장했다.
- `targets`가 실제 로그인 성공을 의미한다.
- Foundry OSDK readback 경로가 완전히 해결됐다.
- 자동 통보/자동 발송이 구현됐다.

안전한 표현:

- "active compromise candidate"
- "verification priority"
- "approved hackathon lineage rail"
- "synthetic incident scenario"
- "public OSINT context snapshot"
- "human-reviewed notification draft"
