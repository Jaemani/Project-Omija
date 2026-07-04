#!/usr/bin/env python3
"""Palantir-style analyst pages — STRUCTURE ONLY, ALL DATA SLOTS EMPTY.

Generates three alternative "analyst console" pages that showcase the project's
ontology-core engine *structurally*. There is deliberately NO data: every slot
renders its EMPTY state and, next to it, a "data contract card" describing the
candidate input shape (expected fields / types) with obviously-masked
placeholders (``•••``, ``‹fqdn›``, ``‹ISO-8601›``). The owner picks which of the
three to keep.

Every version is organised around one question:

    "Which supplier appears to create an ACTIVE path into a protected defense
     program, why does it matter now, and what action should be prepared first?"

Three outputs (one generator, three files):
  * out/palantir_v1.html  "Investigation"   — object-type browser + schema graph
                                               + inspector (Gotham-like)
  * out/palantir_v2.html  "Ops Triage"       — band-ordered queue + entity-360 +
                                               incident state machine + draft
                                               workspace (Workshop-like)
  * out/palantir_v3.html  "Data Contracts"   — per-type contract cards + pipeline
                                               flow + candidate feed shapes

Guardrails honoured: no network, no data ingestion, no synthetic credentials or
real org names (``*.example`` / ``‹placeholder›`` only), vendor-neutral language
(no feed-vendor names), no secrets. NEW FILE — nothing existing is modified.

Schema sourcing (hybrid — see docs/review/palantir-page-versions.md):
  * LIVE from the engine (imported, truthful): scoring bands / thresholds /
    weights (``actions.scoring.SCORING``), the active-compromise window and
    privileged-account set (``actions.flag_active``), program-rollup config
    (``actions.propagate_risk.PROGRAM_SCORING``), feed-module confidences
    (``adapter.base.CONFIDENCE``), and the refusal exception names.
  * HARDCODED (this file, ``OBJECT_TYPES`` / ``LINK_TYPES``): object property
    shapes and lifecycle state names. The prose ontology docs are not reliably
    machine-parseable and some lifecycle states are the *target* Foundry model
    (the SQLite engine currently emits only the initial state), so a single
    well-commented schema dict here is the honest source.

Run: ``uv run python scripts/palantir_pages.py``  (writes the three files)
"""

from __future__ import annotations

import html
import os
import sys

# Repo root on path (script may be run directly).
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

# --- LIVE engine constants (truthful — imported, never re-typed) -------------
from actions.scoring import SCORING                                  # noqa: E402
from actions.flag_active import ACTIVE_WINDOW_DAYS, _ACTIVE_ACCOUNTS  # noqa: E402
from actions.propagate_risk import (                                 # noqa: E402
    PROGRAM_SCORING,
    ProgramEvidenceRequired,
)
from actions.compute_risk import EvidenceRequired                    # noqa: E402
from actions.notify_draft import CitationRequired                    # noqa: E402
from actions.flag_active import PathIncomplete                       # noqa: E402
from adapter.base import CONFIDENCE                                  # noqa: E402

OUT_DIR = os.path.join(_ROOT, "out")

# Derived, from the live scoring config — these guarantee the triage invariant.
ACTIVE_FLOOR = SCORING["active_floor"]        # 70 — active band starts here
ACTIVE_CEIL = SCORING["active_ceiling"]       # 100
BASE_CAP = SCORING["base_cap"]                # 60 — non-active clamp ceiling
GR = SCORING["grade_thresholds"]             # {즉시:70, 주의:40}

# Vendor-neutral labels for the (abstracted) feed-module confidence tiers. The
# raw codes stay internal; the page shows only semantic names + numeric weight.
_MODULE_LABELS = {
    "cds": "stealer-log (infostealer device)",
    "ub": "url · login · pass binder",
    "cl": "breach dump (leaked server)",
    "cb": "combo list (recirculated)",
}
FEED_TIERS = sorted(
    ({_MODULE_LABELS.get(k, k): v} for k, v in CONFIDENCE.items()),
    key=lambda d: -list(d.values())[0],
)


def _e(v) -> str:
    return html.escape("" if v is None else str(v))


def _why(key: str) -> str:
    """Compact 'why ontology' annotation for a panel (WHY key or literal text)."""
    text = WHY.get(key, key)
    return (f'<div class="why"><span class="whytag">WHY ONTOLOGY</span>'
            f'{_e(text)}</div>')


# --------------------------------------------------------------------------- #
# SCHEMA METADATA  (hardcoded — the honest source for property/lifecycle shape)
# --------------------------------------------------------------------------- #
# kind → visual family (drives colour + legend). English API names throughout;
# Korean is only used for explanatory role captions.
KINDS = {
    "entity": ("Entity / registry", "var(--c-entity)"),
    "evidence": ("Evidence (observed)", "var(--c-evidence)"),
    "derived": ("Derived judgment", "var(--c-derived)"),
    "output": ("Human-review / output", "var(--c-output)"),
}

# Masked placeholder vocabulary (obviously-empty, never real values).
M = {
    "pk": "‹id›",
    "str": "‹string›",
    "secret": "••••••",
    "fqdn": "‹asset›.example",
    "email": "‹local›@‹org›.example",
    "iso": "‹ISO-8601›",
    "epoch": "‹epoch-secs›",
    "score": "‹0–100›",
    "bool": "◦ true | false",
}

# Each object type:  name, kind, role(ko), props[(name,type,placeholder)],
# lifecycle(optional), provenance(optional: link/targets/min/refuse).
OBJECT_TYPES = [
    {
        "name": "Supplier", "kind": "entity", "role": "협력사 (엔티티)",
        "props": [
            ("id", "PK · string", M["pk"]),
            ("name", "string", M["str"]),
            ("domains", "string[]", "[ ‹fqdn›, … ]"),
            ("tier", "enum 1 | 2", "•"),
            ("criticality", "enum high | medium | low", "•••"),
        ],
        "self_link": "subcontractsTo ▸ / ◂ subcontractors",
    },
    {
        "name": "Prime", "kind": "entity", "role": "원청 / 주계약",
        "props": [
            ("id", "PK · string", M["pk"]),
            ("name", "string", M["str"]),
            ("program_refs", "ref[] → Program", "[ ‹program:id›, … ]"),
        ],
    },
    {
        "name": "Program", "kind": "entity", "role": "방산 프로그램 (전파 최상단)",
        "props": [
            ("id", "PK · string", M["pk"]),
            ("name", "string", M["str"]),
            ("sensitivity", "enum high | med | low", "•••"),
        ],
    },
    {
        "name": "Domain", "kind": "entity", "role": "업체 자산 (상관 키)",
        "props": [
            ("fqdn", "PK · string", M["fqdn"]),
            ("supplier_ref", "ref → Supplier", "‹supplier:id›"),
            ("asset_type", "enum domain|vpn|sso|mail|dev|web", "•••"),
            ("access_surface", "enum admin|remote_access|portal|…", "•••"),
        ],
    },
    {
        "name": "Identity", "kind": "entity", "role": "계정 신원 (엔티티 해소 대상)",
        "props": [
            ("id", "PK · string", M["pk"]),
            ("email", "string?", M["email"]),
            ("username", "string?", M["str"]),
            ("domain_ref", "ref → Domain", "‹fqdn›"),
        ],
    },
    {
        "name": "CredentialExposure", "kind": "evidence", "role": "유출 레코드 = 증거",
        "props": [
            ("id", "PK · string", M["pk"]),
            ("module", "enum feed-module", "‹stealer|url-pass|breach|combo›"),
            ("secret_type", "enum plaintext|hash|cookie|token", "•••"),
            ("masked_value", "string (masked at boundary)", M["secret"]),
            ("host", "string?", M["fqdn"]),
            ("source_ref", "provenance handle", "‹src:id›"),
            ("observed_at", "epoch-secs", M["epoch"]),
            ("confidence", "float 0–1", "0.•"),
        ],
    },
    {
        "name": "InfectedDevice", "kind": "evidence", "role": "스틸러 감염기기 = 활성 신호",
        "props": [
            ("device_id", "PK · string", M["pk"]),
            ("malware", "string?", M["str"]),
            ("infected_at", "epoch-secs", M["epoch"]),
            ("has_session_cookie", "bool", M["bool"]),
            ("account_type", "enum vpn | admin | user", "•••"),
            ("os", "string?", M["str"]),
        ],
    },
    {
        "name": "ThreatSource", "kind": "evidence", "role": "관측 출처 (provenance)",
        "props": [
            ("id", "PK · string", M["pk"]),
            ("kind", "enum darkweb|telegram|combo|breach", "•••"),
            ("name", "string", M["str"]),
        ],
    },
    {
        "name": "RiskAssessment", "kind": "derived", "role": "파생 · 협력사 위험판정",
        "props": [
            ("id", "PK · string", "risk:‹supplier›"),
            ("supplier_ref", "ref → Supplier", "‹supplier:id›"),
            ("score", "float 0–100", M["score"]),
            ("grade", "enum 즉시 | 주의 | 관찰", "•••"),
            ("active_flag", "bool (from path existence)", M["bool"]),
            ("computed_at", "epoch-secs", M["epoch"]),
            ("components", "json (explainable breakdown)", "{ … }"),
        ],
        "provenance": {
            "link": "evidenced_by", "targets": "CredentialExposure / InfectedDevice",
            "min": 1, "refuse": EvidenceRequired.__name__,
        },
    },
    {
        "name": "CompromiseIncident", "kind": "derived", "role": "파생 · 활성침해 경보",
        "props": [
            ("id", "PK · string", "incident:‹supplier›"),
            ("supplier_ref", "ref → Supplier", "‹supplier:id›"),
            ("opened_at", "epoch-secs", M["epoch"]),
            ("status", "enum (lifecycle ↓)", "•••"),
            ("path", "node[] (traverses, variable-length)", "[ … ]"),
            ("blast_radius", "json { primes[], programs[] }", "{ … }"),
        ],
        "lifecycle": {
            "states": ["flagged", "acknowledged", "assigned", "closed"],
            "terminal": ["remediated", "false_positive"],
            "note": "human-on-the-loop · engine emits 'flagged' (open); ack/assign/close = analyst actions",
        },
        "provenance": {
            "link": "traverses", "targets": "Device → Identity → Supplier… → Prime → Program",
            "min": "complete path", "refuse": PathIncomplete.__name__,
        },
    },
    {
        "name": "ProgramExposure", "kind": "derived", "role": "파생 · 프로그램 단위 롤업",
        "props": [
            ("id", "PK · string", "progexp:‹program›"),
            ("program_ref", "ref → Program", "‹program:id›"),
            ("score", "float 0–100", M["score"]),
            ("grade", "enum 즉시 | 주의 | 관찰", "•••"),
            ("active_flag", "bool (any contributing incident)", M["bool"]),
            ("contributing_paths", "json[] (per distinct supplier)", "[ … ]"),
        ],
        "lifecycle": {
            "states": ["open", "acknowledged", "closed"],
            "terminal": ["stale"],
            "note": "PropagateRisk rollup · acknowledge / mark_stale / close = analyst actions",
        },
        "provenance": {
            "link": "evidenced_by", "targets": "CompromiseIncident / RiskAssessment",
            "min": 1, "refuse": ProgramEvidenceRequired.__name__,
        },
    },
    {
        "name": "MergeProposal", "kind": "output", "role": "엔티티 해소 후보 (사람 승인)",
        "props": [
            ("id", "PK · string", "merge:‹a›|‹b›"),
            ("identity_a", "ref → Identity (keep)", "‹identity:id›"),
            ("identity_b", "ref → Identity (drop-on-confirm)", "‹identity:id›"),
            ("basis", "string (rule provenance)", M["str"]),
            ("status", "enum (lifecycle ↓)", "•••"),
        ],
        "lifecycle": {
            "states": ["pending", "confirmed"],
            "terminal": ["rejected"],
            "note": "confirm/reject only by a human — nothing merges automatically",
        },
    },
    {
        "name": "NotificationDraft", "kind": "output", "role": "산출 · 통보 초안",
        "props": [
            ("id", "PK · string", "draft:‹supplier›"),
            ("supplier_ref", "ref → Supplier", "‹supplier:id›"),
            ("body", "string (masked, template)", "‹markdown, secrets masked›"),
            ("evidence_refs", "ref[] (cites)", "[ … ]"),
            ("created_at", "epoch-secs", M["epoch"]),
            ("status", "enum (lifecycle ↓)", "•••"),
        ],
        "lifecycle": {
            "states": ["draft", "reviewed", "approved", "exported"],
            "terminal": [],
            "note": "NO 'sent' state — the system never sends. Human review before every transition.",
        },
        "provenance": {
            "link": "cites", "targets": "Exposure / Device / Incident / RiskAssessment",
            "min": 1, "refuse": CitationRequired.__name__,
        },
    },
]
OBJ_BY_NAME = {o["name"]: o for o in OBJECT_TYPES}

# Link types (from, to, cardinality, kind, note). `path`=core credential→program
# chain, `cross`=the of/targets cross-org edge, others as labelled.
LINK_TYPES = [
    ("of", "CredentialExposure", "Identity", "N:1", "path",
     "whose credential — the Identity's HOME org"),
    ("belongs_to", "Identity", "Domain", "N:1", "path",
     "Identity → its home Domain (one Supplier)"),
    ("owns", "Supplier", "Domain", "1:N", "path",
     "home Domain owned_by Supplier (traverse uses reverse)"),
    ("subcontractsTo", "Supplier", "Supplier", "N:M", "path",
     "variable-depth tier chain (2차 → 1차 → …)"),
    ("supplies", "Supplier", "Prime", "N:M", "path",
     "supplier delivers to prime"),
    ("runs", "Prime", "Program", "N:M", "path",
     "prime runs the defense program (top of propagation)"),
    ("targets", "CredentialExposure", "Domain", "N:1", "cross",
     "what asset it accesses — may be a DIFFERENT org's Domain (the point)"),
    ("sourced_from", "CredentialExposure", "ThreatSource", "N:1", "evidence",
     "where it was observed (provenance)"),
    ("leaked", "InfectedDevice", "CredentialExposure", "1:N", "evidence",
     "one infected device leaks many credentials"),
    ("compromises", "InfectedDevice", "Identity", "N:M", "evidence",
     "= leaked ∘ of; cross-org blast is device-level"),
    ("evidenced_by", "RiskAssessment", "CredentialExposure", "1:N", "prov",
     "provenance / citation (min 1, else refuse)"),
    ("traverses", "CompromiseIncident", "Supplier", "path", "prov",
     "the active-compromise path object (variable length)"),
    ("evidenced_by", "ProgramExposure", "CompromiseIncident", "1:N", "prov",
     "rollup provenance (min 1, else refuse)"),
    ("cites", "NotificationDraft", "RiskAssessment", "1:N", "output",
     "draft evidence (min 1, else refuse)"),
    ("merge_candidates", "MergeProposal", "Identity", "2", "output",
     "identity-resolution candidate pair"),
]

# The organising problem — printed on every version.
QUESTION = ("Which supplier appears to create an ACTIVE path into a protected "
            "defense program, why does it matter now, and what action should be "
            "prepared first?")

# --- "Why ontology" — the load-bearing justifications, surfaced in the UI -----
# The project scores WHERE the ontology is used and WHY. Every major panel
# carries one of these: what it does that a flat table / join cannot.
WHY = {
    "of_targets": (
        "of ≠ targets — 자격증명의 소유 조직(of→Identity 홈)과 접근 대상 자산"
        "(targets→Domain, 다른 조직일 수 있음)을 분리해야 '프로그램으로 가는 활성 경로'가 "
        "표현된다. flat table은 한 행에 두 조직을 담지 못한다."),
    "variable_depth": (
        "subcontractsTo* 가변깊이 — 하도급 체인 깊이는 미리 정해지지 않는다. Program "
        "도달 여부는 재귀 그래프 질의(WITH RECURSIVE)이지 고정 JOIN이 아니다."),
    "provenance": (
        "provenance 강제 — RiskAssessment/Incident/ProgramExposure/NotificationDraft "
        "는 evidenced_by/cites 링크 없이는 생성이 거부된다. 감사가능성이 앱 코드가 아니라 "
        "온톨로지 레벨에서 강제된다."),
    "state_machine": (
        "액션 = 객체 상태 전이 — flagged→acknowledged→assigned→closed, "
        "draft→reviewed→approved→exported. human-on-the-loop 이 앱 로직이 아니라 "
        "객체 모델의 속성이다."),
    "band": (
        "트리아지 밴드 = 그래프 결과 — 밴드는 경로 존재(active_flag)에서 파생된다. "
        f"active_floor({ACTIVE_FLOOR:.0f}) > base_cap({BASE_CAP:.0f}) 이므로 활성 경로 "
        "1건이 비활성 누적 유출 전체를 항상 상회한다. 스코어 튜닝이 아니라 그래프 불변식."),
    "entity_res": (
        "엔티티 해소 — 한 사람이 여러 이메일 스펠링·여러 피드에 흩어진다. Identity 병합은 "
        "MergeProposal 상태 전이(사람 승인)로, 링크 재지향이지 문자열 정렬이 아니다."),
    "rollup": (
        "다중홉 집계 — 한 Program에 닿는 모든 협력사 경로를 롤업. distinct Supplier "
        "기준 dedup(다이아몬드 공급망 이중계산 금지)은 경로 그래프에서만 정확히 나온다."),
}

# The highlighted credential→program chain — each hop carries WHY it exists.
PATH_HOPS = [
    {"node": "CredentialExposure", "edge": "of",
     "why": "어느 신원의 자격증명인가 — 소유 조직으로 귀속 (targets 와 분리)"},
    {"node": "Identity", "edge": "belongs_to",
     "why": "신원 → 홈 Domain (한 Identity = 정확히 한 협력사)"},
    {"node": "Domain", "edge": "owned_by⁻¹ (owns)",
     "why": "홈 도메인을 소유한 Supplier 로 귀속"},
    {"node": "Supplier", "edge": "subcontractsTo* · supplies",
     "why": "가변깊이 하도급 → 원청 (재귀 traverse — JOIN 불가)"},
    {"node": "Prime", "edge": "runs",
     "why": "원청이 운영/계약한 프로그램"},
    {"node": "Program", "edge": None,
     "why": "전파 최상단 — 보호 대상 (여기 닿으면 경보)"},
]


# --------------------------------------------------------------------------- #
# shared CSS  (dark, dense, Palantir-esque — committed single look)
# --------------------------------------------------------------------------- #
PATH_CHAIN = [(hop["node"], hop["edge"]) for hop in PATH_HOPS]

CSS = """
:root{
  --plane:#0d0d0d; --surface:#141413; --surface-2:#1a1a19; --raised:#201f1d;
  --ink:#ececea; --ink-2:#a9a89f; --muted:#6f6e68;
  --hair:#262624; --hair-2:#35342f;
  /* validated dark-mode CATEGORICAL hues (dataviz reference palette, dark col) */
  --c-entity:#3987e5;    /* blue   slot1 — entity/registry */
  --c-evidence:#199e70;  /* aqua   slot2 — observed evidence */
  --c-derived:#c98500;   /* yellow slot3 — derived judgment (NOT the status amber) */
  --c-output:#9085e9;    /* violet slot5 — human/output */
  --cross:#ec835a;       /* status 'serious' — the single targets cross-edge (labelled) */
  /* triage bands = fixed status ramp (never a series colour) */
  --band-a:#d03b3b;      /* critical — active compromise path */
  --band-b:#fab219;      /* warning  — elevated exposure */
  --band-c:#3987e5;      /* recessive— observed / passive */
  --mono:ui-monospace,SFMono-Regular,Menlo,"Cascadia Code",monospace;
  --sans:system-ui,-apple-system,"Segoe UI",sans-serif;
}
*{box-sizing:border-box}
html,body{margin:0;background:var(--plane);color:var(--ink);
  font-family:var(--sans);font-size:14px;line-height:1.5;-webkit-font-smoothing:antialiased}
body{overflow-x:hidden}
a{color:var(--c-entity)}
h1,h2,h3{margin:0;font-weight:600;letter-spacing:.2px}
code,kbd,.mono{font-family:var(--mono)}
.scroll-x{overflow-x:auto;overflow-y:hidden}
.topbar{display:flex;align-items:center;gap:14px;padding:10px 18px;
  border-bottom:1px solid var(--hair);background:var(--surface);position:sticky;top:0;z-index:5}
.topbar .brand{font-family:var(--mono);font-size:12px;letter-spacing:1.5px;
  color:var(--ink);text-transform:uppercase}
.topbar .ver{font-family:var(--mono);font-size:11px;color:var(--muted);
  border:1px solid var(--hair-2);border-radius:3px;padding:2px 7px}
.topbar .empty-pill{margin-left:auto;font-family:var(--mono);font-size:11px;
  color:var(--band-b);border:1px solid var(--hair-2);border-radius:3px;padding:2px 8px;
  display:flex;gap:7px;align-items:center}
.topbar .empty-pill::before{content:"";width:7px;height:7px;border-radius:50%;
  background:var(--band-b);box-shadow:0 0 6px var(--band-b)}
.qbar{padding:10px 18px;border-bottom:1px solid var(--hair);background:var(--surface-2);
  font-size:12.5px;color:var(--ink-2)}
.qbar b{color:var(--ink);font-weight:600}
.lbl{font-family:var(--mono);font-size:10.5px;letter-spacing:1px;color:var(--muted);
  text-transform:uppercase}
.count0{font-family:var(--mono);font-size:11px;color:var(--muted);
  border:1px solid var(--hair-2);border-radius:10px;padding:0 7px;min-width:20px;
  display:inline-flex;justify-content:center}
.dot{width:8px;height:8px;border-radius:50%;display:inline-block;flex:none}
.empty-slot{border:1px dashed var(--hair-2);border-radius:5px;background:
  repeating-linear-gradient(45deg,transparent,transparent 7px,rgba(255,255,255,.012) 7px,rgba(255,255,255,.012) 14px);
  color:var(--muted);font-family:var(--mono);font-size:11px;padding:10px 12px}
.contract{border:1px solid var(--hair-2);border-radius:6px;background:var(--surface);
  overflow:hidden}
.contract .chead{display:flex;align-items:center;gap:8px;padding:7px 11px;
  border-bottom:1px solid var(--hair);background:var(--surface-2)}
.contract .chead .nm{font-family:var(--mono);font-size:12.5px;color:var(--ink)}
.contract .chead .role{font-size:11px;color:var(--muted);margin-left:auto}
.contract table{width:100%;border-collapse:collapse;font-size:12px}
.contract td{padding:5px 11px;border-top:1px solid var(--hair);vertical-align:top}
.contract td.k{font-family:var(--mono);color:var(--ink-2);white-space:nowrap;width:38%}
.contract td.t{color:var(--muted);font-size:11px;width:34%}
.contract td.v{font-family:var(--mono);color:var(--c-evidence);text-align:right;
  opacity:.75}
.prov{padding:7px 11px;border-top:1px solid var(--hair);font-size:11px;color:var(--ink-2);
  background:rgba(250,178,25,.05)}
.prov b{color:var(--c-derived)}
.refuse{color:var(--band-a);font-family:var(--mono);font-size:10.5px}
.legend{display:flex;flex-wrap:wrap;gap:14px;font-size:11px;color:var(--ink-2)}
.legend span{display:flex;align-items:center;gap:6px}
/* state machine pills */
.sm{display:flex;align-items:center;gap:0;flex-wrap:wrap}
.sm .st{font-family:var(--mono);font-size:11.5px;padding:5px 11px;border:1px solid var(--hair-2);
  border-radius:4px;background:var(--surface-2);color:var(--ink-2);white-space:nowrap}
.sm .st.start{border-color:var(--c-entity);color:var(--ink)}
.sm .arrow{color:var(--muted);padding:0 8px;font-family:var(--mono)}
.sm .term{font-family:var(--mono);font-size:11px;padding:4px 9px;border-radius:4px;
  border:1px dashed var(--hair-2);color:var(--muted);margin-left:6px}
.sm .term.ok{border-color:rgba(12,163,12,.5);color:#7bcf7b}
.sm .term.bad{border-color:rgba(208,59,59,.5);color:#e88}
.smnote{font-size:11px;color:var(--muted);margin-top:6px}
.no-send{color:var(--band-a);font-family:var(--mono);font-size:11px;
  border:1px solid rgba(208,59,59,.4);border-radius:4px;padding:3px 9px;display:inline-block}
.footer{padding:14px 18px;border-top:1px solid var(--hair);color:var(--muted);
  font-size:11px;font-family:var(--mono)}
/* "why ontology" annotation - the project's load-bearing argument */
.why{font-size:11px;color:var(--ink-2);border-left:2px solid var(--c-output);
  padding:5px 10px;margin:6px 0;background:rgba(144,133,233,.06);border-radius:0 4px 4px 0}
.why .whytag{font-family:var(--mono);font-size:9px;letter-spacing:1.2px;color:var(--c-output);
  display:inline-block;margin-right:8px;vertical-align:1px}
.why b{color:var(--ink)}
.whybar{display:flex;flex-wrap:wrap;gap:8px;margin:8px 0}
.whybar .chip{font-family:var(--mono);font-size:10px;color:var(--c-output);
  border:1px solid rgba(144,133,233,.35);border-radius:12px;padding:2px 9px}
"""


# --------------------------------------------------------------------------- #
# shared render helpers
# --------------------------------------------------------------------------- #
def _page(title: str, ver: str, subtitle: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_e(title)}</title>
<style>{CSS}</style></head>
<body>
<div class="topbar">
  <span class="brand">OMIJA · SUPPLY-CHAIN CREDENTIAL EXPOSURE</span>
  <span class="ver">{_e(ver)}</span>
  <span style="font-size:12px;color:var(--ink-2)">{_e(subtitle)}</span>
  <span class="empty-pill">EMPTY STATE · 데이터 슬롯 전부 비어있음</span>
</div>
<div class="qbar"><b>조직 질문 / organising question — </b>{_e(QUESTION)}</div>
{body}
<div class="footer">structure-only preview · no network · no data · masked placeholders only ·
object/link/state names are API identifiers (English) · generated by scripts/palantir_pages.py</div>
</body></html>"""


def _contract_card(obj: dict, *, show_prov: bool = True) -> str:
    """Full empty-state data-contract card for one object type."""
    color = KINDS[obj["kind"]][1]
    rows = "".join(
        f'<tr><td class="k">{_e(n)}</td><td class="t">{_e(t)}</td>'
        f'<td class="v">{_e(v)}</td></tr>'
        for n, t, v in obj["props"]
    )
    prov = ""
    if show_prov and obj.get("provenance"):
        p = obj["provenance"]
        prov = (
            f'<div class="prov">provenance <b>{_e(p["link"])}</b> → '
            f'{_e(p["targets"])} · min {_e(p["min"])} · '
            f'empty ⇒ <span class="refuse">{_e(p["refuse"])}</span> (거부)</div>'
        )
    life = ""
    if obj.get("lifecycle"):
        life = f'<div class="prov" style="background:rgba(57,135,229,.05)">' \
               f'{_state_machine(obj["lifecycle"], inline=True)}</div>'
    return (
        f'<div class="contract">'
        f'<div class="chead"><span class="dot" style="background:{color}"></span>'
        f'<span class="nm">{_e(obj["name"])}</span>'
        f'<span class="role">{_e(obj.get("role",""))}</span></div>'
        f'<table>{rows}</table>{life}{prov}</div>'
    )


def _state_machine(life: dict, *, inline: bool = False) -> str:
    parts = []
    states = life["states"]
    for i, s in enumerate(states):
        cls = "st start" if i == 0 else "st"
        parts.append(f'<span class="{cls}">{_e(s)}</span>')
        if i < len(states) - 1:
            parts.append('<span class="arrow">→</span>')
    for t in life.get("terminal", []):
        good = t in ("remediated", "confirmed", "approved", "exported")
        bad = t in ("false_positive", "rejected", "stale")
        tc = "term ok" if good else ("term bad" if bad else "term")
        parts.append(f'<span class="{tc}">{_e(t)}</span>')
    note = f'<div class="smnote">{_e(life.get("note",""))}</div>' if not inline else \
           f'<span class="smnote" style="margin-left:8px">{_e(life.get("note",""))}</span>'
    return f'<div class="sm">{"".join(parts)}</div>{note}'


# --------------------------------------------------------------------------- #
# schema graph SVG  (object types = nodes, link types = labelled edges)
# --------------------------------------------------------------------------- #
NODE_W, NODE_H = 138, 42
_POS = {
    "InfectedDevice": (150, 118), "ThreatSource": (400, 118),
    "CredentialExposure": (150, 300), "Identity": (400, 300),
    "Domain": (610, 300), "Supplier": (820, 300),
    "Prime": (1010, 300), "Program": (1180, 300),
    "MergeProposal": (400, 500), "CompromiseIncident": (610, 500),
    "RiskAssessment": (820, 500), "NotificationDraft": (1010, 500),
    "ProgramExposure": (1180, 500),
}
# graph edges: (from, to, label, cls)  cls ∈ path|cross|evidence|prov|output
_GEDGES = [
    ("CredentialExposure", "Identity", "of", "path"),
    ("Identity", "Domain", "belongs_to", "path"),
    ("Supplier", "Domain", "owns", "path"),
    ("Supplier", "Prime", "supplies", "path"),
    ("Prime", "Program", "runs", "path"),
    ("InfectedDevice", "CredentialExposure", "leaked", "evidence"),
    ("InfectedDevice", "Identity", "compromises", "evidence"),
    ("CredentialExposure", "ThreatSource", "sourced_from", "evidence"),
    ("RiskAssessment", "Supplier", "risk_of", "prov"),
    ("CompromiseIncident", "Supplier", "traverses", "prov"),
    ("ProgramExposure", "Program", "exposure_of", "prov"),
    ("ProgramExposure", "CompromiseIncident", "evidenced_by", "prov"),
    ("NotificationDraft", "RiskAssessment", "cites", "output"),
    ("MergeProposal", "Identity", "merge_candidates", "output"),
]
_EDGE_COLOR = {
    "path": "var(--c-entity)", "cross": "var(--cross)",
    "evidence": "var(--c-evidence)", "prov": "var(--c-derived)",
    "output": "var(--c-output)",
}


def _border_point(cx, cy, tx, ty):
    """Point on the (cx,cy) node's rectangle border along the line toward (tx,ty)."""
    dx, dy = tx - cx, ty - cy
    if dx == 0 and dy == 0:
        return cx, cy
    hw, hh = NODE_W / 2 + 3, NODE_H / 2 + 3
    sx = hw / abs(dx) if dx else 1e9
    sy = hh / abs(dy) if dy else 1e9
    s = min(sx, sy)
    return cx + dx * s, cy + dy * s


def _schema_graph_svg() -> str:
    W, H = 1330, 620
    out = [
        f'<svg viewBox="0 0 {W} {H}" width="100%" '
        f'style="min-width:1000px;display:block" role="img" '
        f'aria-label="Ontology schema rendered as a graph (empty data)">',
        '<defs>',
    ]
    for cls, col in _EDGE_COLOR.items():
        out.append(
            f'<marker id="ah-{cls}" markerWidth="9" markerHeight="9" refX="7.5" '
            f'refY="3" orient="auto"><path d="M0,0 L8,3 L0,6 Z" fill="{col}"/></marker>'
        )
    out.append('</defs>')

    # straight edges
    for frm, to, label, cls in _GEDGES:
        fx, fy = _POS[frm]
        tx, ty = _POS[to]
        x1, y1 = _border_point(fx, fy, tx, ty)
        x2, y2 = _border_point(tx, ty, fx, fy)
        col = _EDGE_COLOR[cls]
        dash = ' stroke-dasharray="4 4"' if cls in ("evidence", "prov", "output") else ""
        op = "0.9" if cls == "path" else "0.55"
        out.append(
            f'<line x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" y2="{y2:.0f}" '
            f'stroke="{col}" stroke-width="{2 if cls=="path" else 1.4}"{dash} '
            f'opacity="{op}" marker-end="url(#ah-{cls})"/>'
        )
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        out.append(
            f'<rect x="{mx-len(label)*3.4-4:.0f}" y="{my-8:.0f}" '
            f'width="{len(label)*6.8+8:.0f}" height="15" rx="2" fill="#0d0d0d" opacity="0.85"/>'
        )
        out.append(
            f'<text x="{mx:.0f}" y="{my+3:.0f}" text-anchor="middle" '
            f'font-family="ui-monospace,monospace" font-size="10.5" fill="{col}">{_e(label)}</text>'
        )

    # subcontractsTo self-loop on Supplier (variable-depth)
    sx, sy = _POS["Supplier"]
    lx = sx
    ly = sy - NODE_H / 2 - 3
    out.append(
        f'<path d="M{lx-24},{ly} C{lx-46},{ly-46} {lx+46},{ly-46} {lx+24},{ly}" '
        f'fill="none" stroke="var(--c-entity)" stroke-width="2" opacity="0.9" '
        f'marker-end="url(#ah-path)"/>'
    )
    out.append(
        f'<text x="{lx}" y="{ly-46}" text-anchor="middle" '
        f'font-family="ui-monospace,monospace" font-size="10.5" '
        f'fill="var(--c-entity)">subcontractsTo* (N:M · variable depth)</text>'
    )

    # targets cross-edge — curved below spine so it avoids the Identity node
    cx, cy = _POS["CredentialExposure"]
    dx2, dy2 = _POS["Domain"]
    x1, y1 = cx, cy + NODE_H / 2 + 3
    x2, y2 = dx2 - NODE_W / 2 - 3, dy2 + NODE_H / 2 - 6
    ctrlx, ctrly = (cx + dx2) / 2, cy + 128
    out.append(
        f'<path d="M{x1:.0f},{y1:.0f} Q{ctrlx:.0f},{ctrly:.0f} {x2:.0f},{y2:.0f}" '
        f'fill="none" stroke="var(--cross)" stroke-width="2" stroke-dasharray="6 4" '
        f'opacity="0.95" marker-end="url(#ah-cross)"/>'
    )
    out.append(
        f'<rect x="{ctrlx-118:.0f}" y="{ctrly-8:.0f}" width="236" height="16" rx="2" '
        f'fill="#0d0d0d" opacity="0.9"/>'
        f'<text x="{ctrlx:.0f}" y="{ctrly+4:.0f}" text-anchor="middle" '
        f'font-family="ui-monospace,monospace" font-size="10.5" fill="var(--cross)">'
        f'targets → asset Domain (may be a DIFFERENT org)</text>'
    )

    # nodes on top
    for name, (x, y) in _POS.items():
        obj = OBJ_BY_NAME[name]
        col = KINDS[obj["kind"]][1]
        rx = x - NODE_W / 2
        ry = y - NODE_H / 2
        out.append(
            f'<g class="gnode" data-obj="{_e(name)}" style="cursor:pointer">'
            f'<rect x="{rx:.0f}" y="{ry:.0f}" width="{NODE_W}" height="{NODE_H}" rx="6" '
            f'fill="var(--surface-2)" stroke="{col}" stroke-width="1.4"/>'
            f'<rect x="{rx:.0f}" y="{ry:.0f}" width="4" height="{NODE_H}" rx="2" fill="{col}"/>'
            f'<text x="{x:.0f}" y="{y-2:.0f}" text-anchor="middle" '
            f'font-family="ui-monospace,monospace" font-size="12" fill="var(--ink)">{_e(name)}</text>'
            f'<text x="{x:.0f}" y="{y+12:.0f}" text-anchor="middle" '
            f'font-family="ui-monospace,monospace" font-size="9" fill="var(--muted)">'
            f'{_e(KINDS[obj["kind"]][0].split(" ")[0].lower())} · count 0</text>'
            f'</g>'
        )
    out.append('</svg>')
    return "".join(out)


def _kind_legend() -> str:
    items = "".join(
        f'<span><span class="dot" style="background:{col}"></span>{_e(lbl)}</span>'
        for lbl, col in KINDS.values()
    )
    items += (
        '<span><span class="dot" style="background:var(--cross)"></span>'
        'targets cross-edge (of ≠ targets)</span>'
        '<span><span class="dot" style="background:var(--c-entity)"></span>'
        'highlighted credential→program path</span>'
    )
    return f'<div class="legend">{items}</div>'


# --------------------------------------------------------------------------- #
# V1 — "Investigation"  (object browser + schema graph + inspector)
# --------------------------------------------------------------------------- #
def build_v1() -> str:
    import json as _json
    # left rail grouped by kind
    rail = []
    for kind, (label, col) in KINDS.items():
        members = [o for o in OBJECT_TYPES if o["kind"] == kind]
        rows = "".join(
            f'<div class="ot" data-obj="{_e(o["name"])}">'
            f'<span class="dot" style="background:{col}"></span>'
            f'<span class="otn">{_e(o["name"])}</span>'
            f'<span class="count0">0</span></div>'
            for o in members
        )
        rail.append(
            f'<div class="otgroup"><div class="lbl">{_e(label)}</div>{rows}</div>'
        )
    rail_html = "".join(rail)

    # embed schema for the JS inspector
    inspector_data = {}
    for o in OBJECT_TYPES:
        outl = [(l[0], l[2], l[5]) for l in LINK_TYPES if l[1] == o["name"]]
        inl = [(l[0], l[1], l[5]) for l in LINK_TYPES if l[2] == o["name"]]
        inspector_data[o["name"]] = {
            "kind": o["kind"], "role": o.get("role", ""),
            "props": o["props"], "out": outl, "in": inl,
            "lifecycle": o.get("lifecycle"), "prov": o.get("provenance"),
        }
    data_json = _json.dumps(inspector_data, ensure_ascii=False)
    why_json = _json.dumps(WHY, ensure_ascii=False)
    # per-hop path with WHY each hop exists (owner priority: label the chain)
    hop_rows = []
    for i, h in enumerate(PATH_HOPS):
        col = KINDS[OBJ_BY_NAME[h["node"]]["kind"]][1]
        edge = (f'<span class="hopedge mono">—{_e(h["edge"])}→</span>'
                if h["edge"] else '<span class="hopedge mono">◉ 최상단</span>')
        hop_rows.append(
            f'<div class="hop"><span class="hopn mono">'
            f'<span class="dot" style="background:{col}"></span>{_e(h["node"])}</span>'
            f'{edge}<span class="hopwhy">{_e(h["why"])}</span></div>'
        )
    hops_html = "".join(hop_rows)

    body = f"""
<div class="v1wrap">
  <aside class="v1rail scroll-x">
    <div class="railhd"><span class="lbl">Object types</span><span class="count0">13</span></div>
    <div class="railsub">all counts 0 · click a type or a graph node</div>
    {rail_html}
  </aside>
  <main class="v1center">
    <div class="centerhd">
      <span class="lbl">Ontology schema — rendered as the graph</span>
      <span class="centernote">데이터가 없으므로 <b>스키마 자체가 그래프</b>다. 강조된 경로 =
      자격증명이 방산 프로그램으로 닿는 활성 경로 후보.</span>
      <div class="whybar">
        <span class="chip">of ≠ targets</span>
        <span class="chip">subcontractsTo* 가변깊이</span>
        <span class="chip">provenance 강제</span>
        <span class="chip">액션 = 상태전이</span>
      </div>
    </div>
    <div class="graphbox scroll-x">{_schema_graph_svg()}</div>
    {_kind_legend()}
    {_why("variable_depth")}
    <div class="pathstrip">
      <div class="lbl">Highlighted credential → program path — WHY each hop exists</div>
      <div class="hoplist">{hops_html}</div>
      <div class="pathnote"><span class="dot" style="background:var(--c-entity)"></span>
      <b>of</b> = 누구의 자격증명인가 (Identity의 홈 조직).
      <span class="dot" style="background:var(--cross)"></span>
      <b>targets</b> = 무슨 자산에 접근하는가 (다른 조직의 Domain일 수 있음 — 크로스-조직 엣지가 핵심).</div>
      {_why("of_targets")}
    </div>
  </main>
  <aside class="v1insp" id="insp">
    <div class="insphd"><span class="lbl">Inspector</span></div>
    <div id="inspbody" class="inspbody">
      <div class="empty-slot">Select an object type — 속성·링크·lifecycle·provenance 계약이
      여기에 (전부 빈 상태로) 표시됩니다.</div>
    </div>
  </aside>
</div>
<style>
.v1wrap{{display:grid;grid-template-columns:236px minmax(0,1fr) 340px;
  height:calc(100vh - 118px);min-height:560px}}
.v1rail{{border-right:1px solid var(--hair);background:var(--surface);padding:10px 0;overflow-y:auto}}
.railhd{{display:flex;justify-content:space-between;align-items:center;padding:2px 14px 6px}}
.railsub{{padding:0 14px 8px;font-size:11px;color:var(--muted)}}
.otgroup{{padding:6px 0 4px}}
.otgroup .lbl{{padding:2px 14px 4px}}
.ot{{display:flex;align-items:center;gap:9px;padding:5px 14px;cursor:pointer;
  border-left:2px solid transparent}}
.ot:hover{{background:var(--surface-2)}}
.ot.sel{{background:var(--raised);border-left-color:var(--c-entity)}}
.ot .otn{{font-family:var(--mono);font-size:12px;color:var(--ink-2);flex:1}}
.ot.sel .otn{{color:var(--ink)}}
.v1center{{padding:12px 16px;overflow:auto}}
.centerhd{{display:flex;flex-direction:column;gap:3px;margin-bottom:8px}}
.centernote{{font-size:11.5px;color:var(--muted)}}
.centernote b{{color:var(--ink-2)}}
.graphbox{{border:1px solid var(--hair);border-radius:8px;background:
  radial-gradient(circle at 30% 20%,#151514,#0f0f0e);padding:8px}}
.legend{{margin:10px 2px}}
.pathstrip{{margin-top:12px;border:1px solid var(--hair);border-radius:8px;
  background:var(--surface);padding:10px 12px}}
.pathchain{{font-size:12.5px;color:var(--ink);margin:6px 0;word-break:break-word}}
.pathnote{{font-size:11px;color:var(--ink-2);display:flex;gap:6px;flex-wrap:wrap;align-items:center}}
.pathnote b{{color:var(--ink)}}
.v1insp{{border-left:1px solid var(--hair);background:var(--surface);overflow-y:auto}}
.insphd{{padding:10px 14px;border-bottom:1px solid var(--hair);position:sticky;top:0;
  background:var(--surface)}}
.inspbody{{padding:12px 14px;display:flex;flex-direction:column;gap:12px}}
.isec .lbl{{margin-bottom:5px;display:block}}
.ilink{{font-family:var(--mono);font-size:11.5px;color:var(--ink-2);padding:4px 0;
  border-top:1px solid var(--hair)}}
.ilink .lk{{color:var(--c-entity)}} .ilink .tg{{color:var(--ink)}}
.ilink .nt{{color:var(--muted);display:block;font-size:10.5px}}
.hoplist{{margin:6px 0}}
.hop{{display:flex;align-items:baseline;gap:10px;padding:5px 0;border-top:1px solid var(--hair);
  flex-wrap:wrap}}
.hopn{{font-size:12px;color:var(--ink);display:flex;align-items:center;gap:7px;width:180px;flex:none}}
.hopedge{{font-size:10.5px;color:var(--c-entity);width:210px;flex:none}}
.hopwhy{{font-size:11px;color:var(--ink-2);flex:1;min-width:180px}}
</style>
<script>
const SCHEMA = {data_json};
const WHYJS = {why_json};
const KINDCOL = {{entity:"var(--c-entity)",evidence:"var(--c-evidence)",
  derived:"var(--c-derived)",output:"var(--c-output)"}};
function esc(s){{return String(s==null?"":s).replace(/[&<>]/g,c=>({{"&":"&amp;","<":"&lt;",">":"&gt;"}}[c]));}}
function whyBox(t){{return '<div class="why"><span class="whytag">WHY ONTOLOGY</span>'+esc(t)+'</div>';}}
function renderInspector(name){{
  const o = SCHEMA[name]; if(!o) return;
  const col = KINDCOL[o.kind];
  let h = '<div class="contract"><div class="chead">'+
    '<span class="dot" style="background:'+col+'"></span>'+
    '<span class="nm">'+esc(name)+'</span>'+
    '<span class="role">'+esc(o.role)+'</span></div><table>';
  o.props.forEach(p=>{{ h += '<tr><td class="k">'+esc(p[0])+'</td>'+
    '<td class="t">'+esc(p[1])+'</td><td class="v">'+esc(p[2])+'</td></tr>'; }});
  h += '</table></div>';

  // lifecycle
  if(o.lifecycle){{
    let sm='<div class="sm">';
    o.lifecycle.states.forEach((s,i)=>{{ sm+='<span class="st'+(i===0?' start':'')+'">'+esc(s)+'</span>';
      if(i<o.lifecycle.states.length-1) sm+='<span class="arrow">→</span>'; }});
    (o.lifecycle.terminal||[]).forEach(t=>{{
      const good=["remediated","confirmed","approved","exported"].includes(t);
      const bad=["false_positive","rejected","stale"].includes(t);
      sm+='<span class="term '+(good?'ok':(bad?'bad':''))+'">'+esc(t)+'</span>'; }});
    sm+='</div><div class="smnote">'+esc(o.lifecycle.note)+'</div>';
    h += '<div class="isec"><span class="lbl">Lifecycle (state machine)</span>'+sm+
      whyBox(WHYJS.state_machine)+'</div>';
  }}
  // provenance drill-down (empty but present)
  if(o.prov){{
    h += '<div class="isec"><span class="lbl">Provenance — evidence drill-down</span>'+
      '<div class="prov">link <b>'+esc(o.prov.link)+'</b> → '+esc(o.prov.targets)+
      ' · min '+esc(o.prov.min)+' · empty ⇒ <span class="refuse">'+esc(o.prov.refuse)+
      '</span> (거부)</div>'+
      '<div class="empty-slot" style="margin-top:6px">0 evidence rows — drill-down empty</div>'+
      whyBox(WHYJS.provenance)+'</div>';
  }}
  if(name==="Identity"||name==="MergeProposal") h += whyBox(WHYJS.entity_res);
  if(name==="CredentialExposure") h += whyBox(WHYJS.of_targets);
  if(name==="Supplier"||name==="Program") h += whyBox(WHYJS.variable_depth);
  // links
  let lo = o.out.map(l=>'<div class="ilink"><span class="lk">'+esc(l[0])+'</span> → '+
     '<span class="tg">'+esc(l[1])+'</span><span class="nt">'+esc(l[2])+'</span></div>').join('');
  let li = o.in.map(l=>'<div class="ilink"><span class="tg">'+esc(l[1])+'</span> —'+
     '<span class="lk">'+esc(l[0])+'</span>→ <span class="tg">'+esc(name)+'</span>'+
     '<span class="nt">'+esc(l[2])+'</span></div>').join('');
  if(lo) h += '<div class="isec"><span class="lbl">Links out</span>'+lo+'</div>';
  if(li) h += '<div class="isec"><span class="lbl">Links in</span>'+li+'</div>';

  h += '<div class="isec"><span class="lbl">Property values</span>'+
    '<div class="empty-slot">0 instances — every property slot empty (see contract above)</div></div>';
  document.getElementById('inspbody').innerHTML = h;
  document.querySelectorAll('.ot').forEach(e=>e.classList.toggle('sel', e.dataset.obj===name));
  document.querySelectorAll('.gnode rect').forEach(r=>r.setAttribute('stroke-width','1.4'));
}}
document.addEventListener('click',e=>{{
  const t = e.target.closest('[data-obj]');
  if(t) renderInspector(t.dataset.obj);
}});
renderInspector('CredentialExposure');
</script>
"""
    return _page("Omija · V1 Investigation", "V1 · INVESTIGATION",
                 "object browser · schema-as-graph · inspector", body)


# --------------------------------------------------------------------------- #
# V2 — "Ops Triage"  (band queue + entity-360 + incident SM + draft workspace)
# --------------------------------------------------------------------------- #
_BANDS = [
    {
        "id": "A", "grade": "즉시", "color": "var(--band-a)",
        "title": "Band A · ACTIVE compromise path established",
        "range": f"score [{ACTIVE_FLOOR:.0f} … {ACTIVE_CEIL:.0f}]",
        "fill": ("한 항목을 채우려면: RiskAssessment(active_flag=true) + 그 근거인 "
                 "CompromiseIncident 의 traverses 경로가 Program까지 완성 — "
                 f"감염 ≤ {ACTIVE_WINDOW_DAYS}d · has_session_cookie=true · "
                 f"account_type ∈ {{{', '.join(sorted(_ACTIVE_ACCOUNTS))}}}."),
        "shape": "InfectedDevice → Identity → Domain → Supplier → …subcontractsTo… → Prime → Program",
    },
    {
        "id": "B", "grade": "주의", "color": "var(--band-b)",
        "title": "Band B · elevated exposure, no active path",
        "range": f"score [{GR['주의']:.0f} … {BASE_CAP:.0f}]",
        "fill": ("한 항목을 채우려면: RiskAssessment (활성 incident 없음) — 신선한 "
                 "secret_type(cookie/token/plaintext) · dedup된 다수 노출 · "
                 "high-confidence 피드 모듈 · tier-1/criticality 배수. 완성된 활성 경로는 없음."),
        "shape": "CredentialExposure[] → Identity → Domain → Supplier  (no complete Device→Program path)",
    },
    {
        "id": "C", "grade": "관찰", "color": "var(--band-c)",
        "title": "Band C · observed / passive leaks",
        "range": f"score [0 … {GR['주의']:.0f})",
        "fill": ("한 항목을 채우려면: 오래된/재유통 노출만 (hash·combo, 세션 없음). "
                 "기록용으로 보존 — 아무리 쌓여도 Band A 한 건을 넘어서지 못함."),
        "shape": "CredentialExposure[] (stale / recirculated) → Identity → Supplier",
    },
]


def _band_lane(b: dict) -> str:
    return (
        f'<div class="lane">'
        f'<div class="laneh"><span class="badge" style="background:{b["color"]}">{b["id"]}</span>'
        f'<span class="lanet">{_e(b["title"])}</span>'
        f'<span class="laner mono">{_e(b["range"])} · grade {_e(b["grade"])}</span>'
        f'<span class="count0">0</span></div>'
        f'<div class="empty-slot">비어있음 — 이 밴드를 채울 항목 없음</div>'
        f'<div class="lanefill"><span class="lbl">채울 데이터 형태</span>{_e(b["fill"])}</div>'
        f'<div class="laneshape mono">{_e(b["shape"])}</div>'
        f'</div>'
    )


def build_v2() -> str:
    lanes = "".join(_band_lane(b) for b in _BANDS)

    # entity-360 slots (empty) — the supplier-centric template
    e360_slots = [
        ("Identity", "belongs_to Domain — 신원(엔티티 해소 후)"),
        ("CredentialExposure", "of Identity — 노출 레코드 (masked)"),
        ("InfectedDevice", "compromises Identity — 활성 신호"),
        ("CompromiseIncident", "traverses — 활성 경로 (있으면)"),
        ("RiskAssessment", "evidenced_by — 점수·grade·컴포넌트"),
        ("ProgramExposure", "닿는 프로그램 롤업 (blast)"),
        ("NotificationDraft", "cites — 통보 초안 (있으면)"),
    ]
    e360 = "".join(
        f'<div class="e360row"><span class="e360k mono">{_e(k)}</span>'
        f'<span class="e360d">{_e(d)}</span><span class="count0">0</span></div>'
        for k, d in e360_slots
    )

    incident_sm = _state_machine(OBJ_BY_NAME["CompromiseIncident"]["lifecycle"])
    draft_life = OBJ_BY_NAME["NotificationDraft"]["lifecycle"]
    draft_sm = _state_machine(draft_life)
    dp = OBJ_BY_NAME["NotificationDraft"]["provenance"]

    body = f"""
<div class="v2wrap">
  <section class="v2queue">
    <div class="secthd"><span class="lbl">Triage queue — lexicographic order (band, score)</span>
      <span class="count0">0</span></div>
    <div class="ordernote">
      정렬은 <b>사전식 (band, score)</b>. 밴드가 1순위 — active_floor
      <b class="mono">{ACTIVE_FLOOR:.0f}</b> &gt; base_cap <b class="mono">{BASE_CAP:.0f}</b>
      이므로 <b>활성 경로 1건이 비활성 누적 유출 전체를 항상 상회</b>한다.
      밴드 안에서만 score로 정렬.
    </div>
    {_why("band")}
    {lanes}
  </section>

  <aside class="v2side">
    <div class="card">
      <div class="secthd"><span class="lbl">Entity-360 · Supplier</span></div>
      <div class="e360head"><span class="mono">Supplier</span>
        <span class="e360sub">id {{M_pk}} · tier • · criticality •••</span></div>
      <div class="empty-slot" style="margin:8px 0">선택된 협력사 없음 — 아래는 채울 슬롯 형태</div>
      {e360}
      {_why("of_targets")}
    </div>

    <div class="card">
      <div class="secthd"><span class="lbl">CompromiseIncident · state machine</span></div>
      <div class="empty-slot" style="margin-bottom:8px">0 incidents</div>
      {incident_sm}
      <div class="smnote">human-on-the-loop — 자동 전이 없음. flagged 는 엔진의 초기 상태(open).</div>
      {_why("state_machine")}
    </div>

    <div class="card">
      <div class="secthd"><span class="lbl">NotificationDraft · workspace</span></div>
      <div class="draftmeta">
        <span class="no-send">NO SEND — 시스템은 절대 발송하지 않음</span>
      </div>
      <div class="editor empty-slot">초안 에디터 (비어있음) · 본문은 결정론적 템플릿, 모든 secret 마스킹</div>
      <div class="citesnote">cites <b>필수</b> — <span class="mono">{_e(dp['link'])}</span> →
        {_e(dp['targets'])} (min {_e(dp['min'])}). 비면
        <span class="refuse">{_e(dp['refuse'])}</span> 로 <b>거부</b>.</div>
      <div style="margin-top:8px">{draft_sm}</div>
      {_why("provenance")}
    </div>
  </aside>
</div>
<style>
.v2wrap{{display:grid;grid-template-columns:minmax(0,1fr) 380px;gap:0;
  min-height:calc(100vh - 118px)}}
.v2queue{{padding:14px 16px;border-right:1px solid var(--hair)}}
.secthd{{display:flex;align-items:center;gap:10px;margin-bottom:8px}}
.ordernote{{font-size:12px;color:var(--ink-2);border:1px solid var(--hair);border-left:3px solid var(--band-a);
  border-radius:6px;padding:9px 12px;margin-bottom:14px;background:var(--surface)}}
.ordernote b{{color:var(--ink)}}
.lane{{border:1px solid var(--hair);border-radius:8px;background:var(--surface);
  padding:10px 12px;margin-bottom:12px}}
.laneh{{display:flex;align-items:center;gap:10px;margin-bottom:8px}}
.badge{{width:24px;height:24px;border-radius:5px;color:#0d0d0d;font-family:var(--mono);
  font-weight:700;display:flex;align-items:center;justify-content:center;font-size:13px}}
.lanet{{font-size:13px;color:var(--ink);font-weight:600}}
.laner{{font-size:11px;color:var(--muted);margin-left:auto}}
.lanefill{{margin-top:8px;font-size:11.5px;color:var(--ink-2)}}
.lanefill .lbl{{display:block;margin-bottom:3px}}
.laneshape{{margin-top:6px;font-size:11px;color:var(--c-entity);
  border-top:1px dashed var(--hair-2);padding-top:6px;word-break:break-word}}
.v2side{{padding:14px 16px;display:flex;flex-direction:column;gap:14px;background:var(--surface-2)}}
.card{{border:1px solid var(--hair);border-radius:8px;background:var(--surface);padding:12px}}
.e360head{{display:flex;justify-content:space-between;align-items:baseline;
  border-bottom:1px solid var(--hair);padding-bottom:6px}}
.e360sub{{font-size:11px;color:var(--muted);font-family:var(--mono)}}
.e360row{{display:flex;align-items:center;gap:10px;padding:6px 0;border-top:1px solid var(--hair)}}
.e360k{{font-size:12px;color:var(--ink-2);width:150px;flex:none}}
.e360d{{font-size:11px;color:var(--muted);flex:1}}
.draftmeta{{margin-bottom:8px}}
.editor{{min-height:64px;margin-bottom:8px}}
.citesnote{{font-size:11px;color:var(--ink-2)}} .citesnote b{{color:var(--c-derived)}}
</style>
""".replace("{M_pk}", _e(M["pk"]))
    return _page("Omija · V2 Ops Triage", "V2 · OPS TRIAGE",
                 "band queue · entity-360 · state machines", body)


# --------------------------------------------------------------------------- #
# V3 — "Data Contracts"  (per-type cards + pipeline flow + feed candidates)
# --------------------------------------------------------------------------- #
_PIPELINE = [
    {
        "action": "CorrelateExposure", "fn": "correlate_exposures",
        "inp": "CredentialExposure + registered Domains",
        "out": "Identity belongs_to Domain · match_basis (provenance)",
        "refuse": "no email / no registered-domain match → left unmatched (counted)",
    },
    {
        "action": "FlagActiveCompromise", "fn": "flag_active_compromises",
        "inp": f"InfectedDevice (≤{ACTIVE_WINDOW_DAYS}d · cookie · vpn/admin)",
        "out": "CompromiseIncident(status=flagged) · traverses path · blast_radius",
        "refuse": f"incomplete Device→…→Program path → {PathIncomplete.__name__} (skip)",
    },
    {
        "action": "ComputeRisk", "fn": "compute_risk",
        "inp": "Supplier + correlated CredentialExposure[]",
        "out": "RiskAssessment(score, grade, active_flag) · evidenced_by",
        "refuse": f"evidenced_by empty → {EvidenceRequired.__name__} (거부)",
    },
    {
        "action": "PropagateRisk", "fn": "propagate_program_risk",
        "inp": "Program + reaching Supplier paths (recursive traverse)",
        "out": "ProgramExposure(score, grade) · evidenced_by · contributing_paths",
        "refuse": f"no contributing incident/assessment → {ProgramEvidenceRequired.__name__} (거부)",
    },
    {
        "action": "GenerateNotificationDraft", "fn": "generate_notification_draft",
        "inp": "Supplier + exposures (+ incident/assessment)",
        "out": "NotificationDraft(status=draft) · cites · NO send",
        "refuse": f"cites empty → {CitationRequired.__name__} (거부)",
    },
]

# vendor-neutral candidate feed shapes (JSON-shape cards, masked values)
_FEEDS = [
    {
        "name": "credential-exposure record", "fills": "CredentialExposure",
        "json": [
            ('"identity"', '"' + M["email"] + '"'),
            ('"secret_type"', '"cookie | token | plaintext | hash"'),
            ('"secret"', '"' + M["secret"] + '"   // masked at boundary'),
            ('"host"', '"' + M["fqdn"] + '"'),
            ('"observed_at"', '"' + M["iso"] + '"'),
            ('"source_ref"', '"‹opaque-handle›"'),
        ],
    },
    {
        "name": "infostealer device observation", "fills": "InfectedDevice",
        "json": [
            ('"device_id"', '"' + M["pk"] + '"'),
            ('"malware"', '"‹family›"'),
            ('"infected_at"', '"' + M["iso"] + '"'),
            ('"has_session_cookie"', 'true | false'),
            ('"account_type"', '"vpn | admin | user"'),
            ('"os"', '"‹os›"'),
        ],
    },
    {
        "name": "supplier registry row", "fills": "Supplier + Domain",
        "json": [
            ('"supplier_id"', '"' + M["pk"] + '"'),
            ('"name"', '"‹supplier-name›"'),
            ('"domains"', '["' + M["fqdn"] + '", …]'),
            ('"tier"', '1 | 2'),
            ('"criticality"', '"high | medium | low"'),
            ('"subcontracts_to"', '["‹supplier:id›", …]'),
        ],
    },
]


def _pipe_stage(s: dict, last: bool) -> str:
    arrow = '' if last else '<div class="parrow">→</div>'
    return (
        f'<div class="pstage">'
        f'<div class="psh"><span class="mono pact">{_e(s["action"])}</span>'
        f'<span class="count0">0</span></div>'
        f'<div class="psfn mono">{_e(s["fn"])}()</div>'
        f'<div class="psio"><span class="lbl">in</span>{_e(s["inp"])}</div>'
        f'<div class="psio"><span class="lbl">out</span>{_e(s["out"])}</div>'
        f'<div class="psrefuse">⊘ {_e(s["refuse"])}</div>'
        f'</div>{arrow}'
    )


def _feed_card(f: dict) -> str:
    rows = "".join(
        f'<div class="jline"><span class="jk">{_e(k)}</span>'
        f'<span class="jc">:</span> <span class="jv">{_e(v)}</span></div>'
        for k, v in f["json"]
    )
    return (
        f'<div class="feedcard"><div class="feedh">'
        f'<span class="mono feedn">{_e(f["name"])}</span>'
        f'<span class="feedf">→ fills {_e(f["fills"])}</span></div>'
        f'<div class="jbody">'
        f'<div class="jline"><span class="jc">{{</span></div>{rows}'
        f'<div class="jline"><span class="jc">}}</span></div>'
        f'</div></div>'
    )


def build_v3() -> str:
    cards = "".join(f'<div class="ccell">{_contract_card(o)}</div>' for o in OBJECT_TYPES)
    pipe = "".join(_pipe_stage(s, i == len(_PIPELINE) - 1) for i, s in enumerate(_PIPELINE))
    feeds = "".join(_feed_card(f) for f in _FEEDS)
    tiers = "".join(
        f'<span class="tier"><b>{list(d.values())[0]:.1f}</b> {_e(list(d.keys())[0])}</span>'
        for d in FEED_TIERS
    )

    body = f"""
<div class="v3wrap">
  <section class="v3sec">
    <div class="secthd"><span class="lbl">Object-type contracts — 13 types, every slot empty</span>
      <span class="count0">13</span></div>
    <div class="v3note">각 카드 = 후보 입력 형태 (속성·타입·마스킹 placeholder) + lifecycle +
      필수 provenance 링크. 값은 전부 비어있음.</div>
    {_why("provenance")}
    <div class="cgrid">{cards}</div>
  </section>

  <section class="v3sec">
    <div class="secthd"><span class="lbl">Pipeline — correlate → flag_active → compute_risk → propagate → notify_draft</span></div>
    <div class="v3note">각 단계의 입력/출력 계약과 <b>거부 조건</b>(provenance 없으면 파생객체 생성 거부).
      카운터는 전부 0.</div>
    <div class="pipe scroll-x">{pipe}</div>
    {_why("rollup")}
  </section>

  <section class="v3sec">
    <div class="secthd"><span class="lbl">Candidate feed shapes — vendor-neutral, masked</span></div>
    <div class="v3note">2–3개 후보 피드 형태. 어느 object-type 슬롯을 채우는지 표기.
      모든 값 마스킹. 피드 모듈 신뢰도 tier(엔진 값):&nbsp; {tiers}</div>
    {_why("of_targets")}
    <div class="feedgrid">{feeds}</div>
  </section>
</div>
<style>
.v3wrap{{padding:14px 16px;display:flex;flex-direction:column;gap:20px}}
.v3sec{{}}
.secthd{{display:flex;align-items:center;gap:10px;margin-bottom:6px}}
.v3note{{font-size:11.5px;color:var(--muted);margin-bottom:12px}}
.v3note b{{color:var(--ink-2)}}
.cgrid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:12px}}
.ccell{{min-width:0}}
.pipe{{display:flex;align-items:stretch;gap:0;padding:6px 2px 12px}}
.pstage{{flex:0 0 250px;border:1px solid var(--hair);border-radius:8px;background:var(--surface);
  padding:10px 12px;display:flex;flex-direction:column;gap:5px}}
.psh{{display:flex;justify-content:space-between;align-items:center}}
.pact{{font-size:12.5px;color:var(--ink)}}
.psfn{{font-size:10.5px;color:var(--c-evidence);opacity:.8}}
.psio{{font-size:11px;color:var(--ink-2)}}
.psio .lbl{{display:inline-block;width:26px}}
.psrefuse{{margin-top:auto;font-size:10.5px;color:var(--band-a);font-family:var(--mono);
  border-top:1px dashed var(--hair-2);padding-top:6px}}
.parrow{{display:flex;align-items:center;color:var(--muted);font-family:var(--mono);
  padding:0 6px;font-size:18px}}
.feedgrid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px}}
.feedcard{{border:1px solid var(--hair);border-radius:8px;background:var(--surface);overflow:hidden}}
.feedh{{display:flex;justify-content:space-between;align-items:baseline;gap:8px;
  padding:8px 11px;border-bottom:1px solid var(--hair);background:var(--surface-2)}}
.feedn{{font-size:12.5px;color:var(--ink)}}
.feedf{{font-size:10.5px;color:var(--c-output)}}
.jbody{{padding:9px 12px;font-family:var(--mono);font-size:11.5px;line-height:1.7}}
.jline{{white-space:nowrap}}
.jk{{color:var(--c-entity)}} .jc{{color:var(--muted)}} .jv{{color:var(--c-evidence);opacity:.85}}
.tier{{display:inline-block;margin-right:10px;font-family:var(--mono);color:var(--ink-2)}}
.tier b{{color:var(--c-derived)}}
</style>
"""
    return _page("Omija · V3 Data Contracts", "V3 · DATA CONTRACTS",
                 "per-type contracts · pipeline flow · feed candidates", body)


# --------------------------------------------------------------------------- #
def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    outputs = {
        "palantir_v1.html": build_v1(),
        "palantir_v2.html": build_v2(),
        "palantir_v3.html": build_v3(),
    }
    for name, htmltext in outputs.items():
        path = os.path.join(OUT_DIR, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(htmltext)
        print(f"wrote {path}  ({len(htmltext):,} bytes)")


if __name__ == "__main__":
    main()
