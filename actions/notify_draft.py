"""GenerateNotificationDraft action (ontology.md §5, architecture.md §5, P5).

Produces a defensive early-warning NOTIFICATION DRAFT for a supplier from its
correlated exposures. Three ontology/guardrail rules are enforced here:

  * provenance is MANDATORY — `cites` (evidence_refs) must be non-empty or the
    action is REFUSED (`CitationRequired`). No draft may exist without the
    original records backing it (ontology.md §4, CLAUDE.md §5). A supplier with
    no correlated exposures therefore gets no draft at all.
  * the body is DETERMINISTIC / template-based — no LLM call (that is the AIP
    Logic layer's job; the demo needs reproducibility). "관측됨" (observed) and
    "추정됨" (inferred) are kept distinct; no exaggeration or unqualified claims.
  * the draft is only ever CREATED — `status` is always "draft". There is no
    send capability anywhere in the codebase (CLAUDE.md: 통보는 초안 생성까지,
    자동 발송 없음). A human analyst must review before any real notification.

Every secret rendered into the body is the already-masked value from the store;
raw secrets never reach this layer.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from actions.flag_active import path_chain

# Defensive containment playbook (architecture.md §5). Item 4 ("계정 격리") is
# asserted by tests for active-compromise drafts.
_RECOMMENDATIONS = [
    "해당 계정 비밀번호 즉시 리셋(관측된 노출 계정 전체).",
    "세션·쿠키 전면 폐기: 강제 로그아웃 및 발급 토큰 무효화(비밀번호 변경만으로는 "
    "유효 세션이 유지될 수 있음).",
    "다중인증(MFA) 강제 적용 및 예외 계정 점검.",
    "해당 계정 일시 격리 후 접근 권한·권한상승 이력 재검토.",
    "감염 의심 기기 포렌식 확보 후 재이미징(정상화 전 재사용 금지).",
    "VPN·원격 접속 세션 감사: 비정상 로그인·동시 세션 추적.",
]

_MODULE_LABEL = {
    "cds": "인포스틸러 로그(darkweb)",
    "ub": "URL:LOGIN:PASS 바인더",
    "cl": "유출 서버(breach)",
    "cb": "재유통 combo list",
}


class CitationRequired(Exception):
    """GenerateNotificationDraft refused: cites (evidence_refs) would be empty —
    no draft without provenance (ontology.md §4, CLAUDE.md §5)."""


@dataclass
class NotificationDraft:
    id: str
    supplier_ref: str
    body: str
    evidence_refs: list = field(default_factory=list)   # list[(ref, kind)]
    created_at: int = 0
    status: str = "draft"


def _supplier(store: Any, supplier_id: str) -> dict:
    for s in store.suppliers():
        if s["id"] == supplier_id:
            return s
    raise ValueError(f"unknown supplier: {supplier_id}")


def _assessment(store: Any, supplier_id: str) -> dict | None:
    for a in store.risk_assessments():
        if a["supplier_ref"] == supplier_id:
            return a
    return None


def _cites(exposures: list[dict]) -> list[tuple[str, str]]:
    """cites = every backing Exposure, plus the InfectedDevice for any exposure
    that carries a stealer signal. Ordered + de-duplicated (mirrors ComputeRisk
    evidenced_by so a draft and its score cite the same records)."""
    ev: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def add(ref: str, kind: str) -> None:
        key = (ref, kind)
        if ref and key not in seen:
            seen.add(key)
            ev.append(key)

    for r in exposures:
        add(r["id"], "exposure")
    for r in exposures:
        if r.get("infected_at") is not None:
            add(f"dev:{r['source_ref']}", "device")
    return ev


def _fmt_ts(ts: Any) -> str:
    if not ts:
        return "—"
    return datetime.fromtimestamp(int(ts), timezone.utc).strftime("%Y-%m-%d")


def _detection_lines(exposures: list[dict]) -> list[str]:
    lines: list[str] = []
    for r in sorted(exposures, key=lambda x: -(x.get("infected_at") or x.get("observed_at") or 0)):
        module = r.get("module")
        label = _MODULE_LABEL.get(module, module)
        masked = r.get("masked_value") or "(비밀값 마스킹)"
        host = r.get("host") or "—"
        when = _fmt_ts(r.get("infected_at") or r.get("observed_at"))
        lines.append(
            f"- [{module}] {label} · host `{host}` · 관측일 {when} · "
            f"비밀유형 {r.get('secret_type')}(값 마스킹: `{masked}`) · "
            f"근거 `{r.get('source_ref')}`"
        )
    return lines


def _build_body(
    supplier: dict, exposures: list[dict], incidents: list[dict],
    assessment: dict | None, *, now: int,
) -> str:
    name = supplier.get("name", supplier.get("id"))
    grade = (assessment or {}).get("grade", "—")
    score = (assessment or {}).get("score")
    score_txt = "—" if score is None else f"{float(score):.2f}"
    active = bool(incidents)

    out: list[str] = []
    out.append(f"# [초안] 자격증명 노출 조기경보 통보 — {name}")
    out.append("")
    out.append(f"- 수신(가정): {name} 정보보안 담당")
    out.append("- 분류: 방어적 조기경보 · 분석가 검토 전 자동 생성 초안")
    out.append(f"- 작성 시각(UTC): {_fmt_ts(now)}")
    out.append(f"- 위험 등급(추정): {grade} · 점수 {score_txt}")
    out.append(
        f"- 활성 침해 정황: {'있음(경로 성립 — 추정)' if active else '현재 미탐지'}"
    )
    out.append("")

    # (a) detection summary — observed facts
    out.append("## 1. 탐지 요약 (관측됨)")
    out.append(
        "아래 자격증명 노출이 외부 위협 인텔리전스에서 관측되었습니다. "
        "본 데모는 모의 데이터(합성 `*.example` 도메인)이며, 비밀값은 전량 마스킹되어 있습니다."
    )
    out.extend(_detection_lines(exposures))
    out.append("")

    # (b) active-compromise path — inferred (only if an incident exists)
    if active:
        out.append("## 2. 활성 침해 경로 (경로 존재 — 추정)")
        out.append(
            "최근 감염 기기에서 유효 세션 정황이 관측되어, 아래 경로를 따라 "
            "귀사 계정에서 원청·방산 프로그램으로 위험이 전파될 수 있는 것으로 추정됩니다:"
        )
        out.append("")
        out.append("  감염기기 → 계정 → 귀사 도메인 → 원청 → 방산 프로그램")
        out.append("")
        for inc in incidents:
            out.append(f"- 경로: {path_chain(inc.get('path', []))}")
        out.append(
            "※ 세션 쿠키가 유효한 경우, 비밀번호 변경만으로는 공격자가 기존 세션으로 "
            "접근을 유지할 수 있어 세션 폐기가 함께 필요합니다(추정)."
        )
        out.append("")

    # (c) defensive recommendations
    sec = "3" if active else "2"
    out.append(f"## {sec}. 권고 방어 조치 (즉시)")
    for i, rec in enumerate(_RECOMMENDATIONS, 1):
        out.append(f"{i}. {rec}")
    out.append("")

    # (d) evidence list (source_ref citations)
    sec = "4" if active else "3"
    out.append(f"## {sec}. 근거 (provenance)")
    for r in exposures:
        out.append(
            f"- `{r.get('source_ref')}` — 모듈 {r.get('module')}, "
            f"관측 {_fmt_ts(r.get('infected_at') or r.get('observed_at'))}"
        )
    out.append("")

    # (e) footer notice
    out.append("---")
    out.append(
        "본 문서는 자동 생성된 **초안**이며, 분석가 검토·승인 전 발송을 금지합니다. "
        "방어적 조기경보 목적으로 작성되었으며, 관측된 사실과 추정을 구분해 기재했습니다. "
        "실제 대상 지정·통지는 사람 검토를 전제로 합니다."
    )
    return "\n".join(out)


def generate_notification_draft(
    store: Any, supplier_id: str, *, now: int | None = None,
) -> NotificationDraft:
    """Generate + persist a NotificationDraft for one supplier. Raises
    `CitationRequired` if the supplier has no exposures to cite (no draft
    without provenance)."""
    now = int(time.time()) if now is None else now
    supplier = _supplier(store, supplier_id)
    exposures = store.exposures_for_supplier(supplier_id)

    cites = _cites(exposures)
    if not cites:
        raise CitationRequired(
            f"GenerateNotificationDraft refused for {supplier_id!r}: cites is "
            "empty — no draft without provenance (ontology.md §4, CLAUDE.md §5)."
        )

    incidents = store.incidents_for_supplier(supplier_id)
    assessment = _assessment(store, supplier_id)
    body = _build_body(supplier, exposures, incidents, assessment, now=now)

    did = f"draft:{supplier_id}"
    store.record_notification_draft(
        id=did, supplier_ref=supplier_id, body=body, status="draft",
        created_at=now, cites=cites,
    )
    return NotificationDraft(
        id=did, supplier_ref=supplier_id, body=body, evidence_refs=cites,
        created_at=now, status="draft",
    )


def generate_drafts(
    store: Any, assessments: list, *, top: int = 3, now: int | None = None,
) -> list[NotificationDraft]:
    """GenerateNotificationDraft for the top-ranked suppliers (active ones
    already sit on top, so this covers the active-compromise suppliers). Any
    supplier without evidence is skipped (would be refused). `assessments` is the
    score-sorted output of `compute_all`."""
    now = int(time.time()) if now is None else now
    drafts: list[NotificationDraft] = []
    for a in assessments[: max(0, top)]:
        try:
            drafts.append(generate_notification_draft(store, a.supplier_ref, now=now))
        except CitationRequired:
            continue
    return drafts
