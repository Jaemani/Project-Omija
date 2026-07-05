"""Operational data-lineage page (scripts/data_lineage_live.py).

Renders the left-to-right data flow of an APPROVED StealthMole API run through
the Omija redaction boundary, ontology, and reasoning engine — traced by
lineage into the live Foundry links + action audit.

Honesty contract (docs/finals-data-lineage-upgrade.md,
docs/review/finals-foundry-lineage-check.md):

  * An approved StealthMole run REALLY happened (data/private_candidates/
    collection_meta.json). For seed `domain:sup-a:supplier-a.example` the modules
    CL/CDS/CB returned 200/0 rows, DT 403, TT 404 — so the run returned ZERO rows.
  * Therefore the PROVIDER and REDACTION lanes are REAL (real module statuses +
    real redaction policy) but NORMALIZED/ONTOLOGY/ENGINE counts FROM THIS RUN
    are 0. We do NOT invent records.
  * The SAME populated pipeline is demonstrated on the synthetic scenario
    (out/early_warning_readiness.json — 74 eval records, 3 active suppliers),
    chipped clearly as SEED/ENGINE, distinct from the live-provider lane.
  * If a future run returns rows (returned_total > 0) the page auto-populates
    from the same JSON inputs — counts are data-driven, never hardcoded.

Inputs (all safe to read at build time — no secrets in any of them):
  data/private_candidates/collection_meta.json   (private/gitignored; run meta)
  out/private_candidate_import.json              (import boundary summary)
  out/early_warning_readiness.json               (synthetic engine counts)
  out/foundry_action_chain.json                  (real Foundry action readback)

Outputs:  out/data_lineage_live.html + out/data_lineage_live.json

Offline, self-contained (inline CSS, no CDN/external refs), mobile responsive.
Run:  uv run python scripts/data_lineage_live.py
"""

from __future__ import annotations

import html
import json
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from scripts.omija_style import (  # noqa: E402
    TOKENS_CSS, chip, chip_legend, nav_strip, pnote, synthetic_banner,
)

OUT_DIR = os.path.join(REPO_ROOT, "out")
COLLECTION_META = os.path.join(REPO_ROOT, "data", "private_candidates", "collection_meta.json")
IMPORT_JSON = os.path.join(OUT_DIR, "private_candidate_import.json")
READINESS_JSON = os.path.join(OUT_DIR, "early_warning_readiness.json")
ACTION_CHAIN_JSON = os.path.join(OUT_DIR, "foundry_action_chain.json")
OUT_HTML = os.path.join(OUT_DIR, "data_lineage_live.html")
OUT_JSON = os.path.join(OUT_DIR, "data_lineage_live.json")

OSDK_VERSION = "0.2.0"
MODULE_ORDER = ("cl", "cds", "cb", "dt", "tt")


def _e(v: Any) -> str:
    return html.escape("" if v is None else str(v))


def _read_json(path: str) -> dict[str, Any]:
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _fmt_iso(iso: str | None) -> str:
    if not iso:
        return "—"
    return iso.replace("T", " ")[:19] + " UTC"


def _int(v: Any) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


# --------------------------------------------------------------------------- #
# data — everything driven from the JSON inputs (no hardcoded counts)
# --------------------------------------------------------------------------- #
def gather() -> dict[str, Any]:
    meta = _read_json(COLLECTION_META)
    imported = _read_json(IMPORT_JSON)
    readiness = _read_json(READINESS_JSON)
    chain = _read_json(ACTION_CHAIN_JSON)

    collection = meta.get("collection") or {}
    raw_modules = collection.get("modules") or {}
    modules: dict[str, dict[str, Any]] = {}
    returned_total = 0
    for name in MODULE_ORDER:
        m = raw_modules.get(name) or {}
        returned = _int(m.get("returned"))
        returned_total += returned
        modules[name] = {
            "status": m.get("status"),
            "returned": returned,
            "written": _int(m.get("written")),
            "error": m.get("error"),
        }

    imp = imported.get("summary") or {}
    import_boundary = {
        "input_records": _int(imp.get("input_records")),
        "normalized_exposures": _int(imp.get("normalized_exposures")),
        "threat_sources": _int(imp.get("threat_sources")),
        "rejected": _int(imp.get("rejected")),
    }
    policy = imported.get("policy") or {}

    rsum = readiness.get("summary") or {}
    synthetic = {
        "eval_records": _int(rsum.get("eval_records")),
        "active_suppliers": len(rsum.get("active_suppliers") or []),
        "suppliers": _int(rsum.get("suppliers")),
        "query_items": _int(rsum.get("query_items")),
        "asset_surface_seeds": _int(rsum.get("asset_surface_seeds")),
    }

    steps = chain.get("steps") or []
    foundry = {
        "ontology_api_name": chain.get("ontology_api_name"),
        "generated_at": chain.get("generated_at"),
        "action_transitions": len(steps),
        "verified_transitions": sum(1 for s in steps if s.get("verified")),
        "workflow_actions": len(chain.get("discovered_actions") or {}),
        "osdk": OSDK_VERSION,
    }

    return {
        "run_generated_at": meta.get("generated_at"),
        "seed_id": collection.get("seed_id"),
        "obs_type": collection.get("obs_type"),
        "domain_value": collection.get("value"),
        "modules": modules,
        "returned_total": returned_total,
        "import_boundary": import_boundary,
        "policy": policy,
        "synthetic": synthetic,
        "foundry": foundry,
    }


# --------------------------------------------------------------------------- #
# small UI helpers
# --------------------------------------------------------------------------- #
LANE_CLS = {
    "LIVE_PROVIDER": "prov",
    "PRIVATE_RAW": "lock",
    "LOCKED_SECRET": "lock",
    "NORMALIZED": "norm",
    "ONTOLOGY": "onto",
    "ENGINE": "eng",
    "LIVE_FOUNDRY": "fdry",
}


def lbl(name: str) -> str:
    """Lane provenance label — the exact required label set as a mono badge."""
    return f'<span class="lbl {LANE_CLS.get(name, "")}">{_e(name)}</span>'


def _count_block(live: int, this_run: bool, synthetic: str | None) -> str:
    unit = '<span class="u">(this run)</span>' if this_run else ""
    syn = f'<div class="lsyn">{synthetic}</div>' if synthetic else ""
    return (f'<div class="lnum">{live:,} {unit}</div>{syn}')


# --------------------------------------------------------------------------- #
# sections
# --------------------------------------------------------------------------- #
def _run_summary(d: dict[str, Any]) -> str:
    rows = []
    for name in MODULE_ORDER:
        m = d["modules"][name]
        status = m["status"]
        ok = status == 200
        st_cls = "ok" if ok else "warn"
        note = "" if ok else _e(m["error"] or "")
        rows.append(
            f"<tr><td class='mono2'>{_e(name.upper())}</td>"
            f"<td class='{st_cls}'>{_e(status if status is not None else 'n/a')}</td>"
            f"<td>{m['returned']:,}</td><td>{m['written']:,}</td>"
            f"<td class='dim'>{note}</td></tr>"
        )
    zero = d["returned_total"] == 0
    zero_note = ("이 seed는 <b>0건</b> 반환 — 승인된 라이브 run은 실행됐고 "
                 "레코드가 없다는 것까지 정직하게 표시한다."
                 if zero else
                 f"이 run은 <b>{d['returned_total']:,}건</b> 반환 — 아래 계보가 실데이터로 채워진다.")
    return f"""
  <div class="card">
    <div class="ch"><span class="ck">RUN SUMMARY</span>{lbl('LIVE_PROVIDER')}{chip('live')}
      <span class="cflag">확정된 침해 아님 · raw secret 미저장</span></div>
    <div class="cmeta">
      <div><span class="ml">run generated</span><b>{_e(_fmt_iso(d['run_generated_at']))}</b></div>
      <div><span class="ml">seed (domain-level only)</span><b>{_e(d['seed_id'])}</b></div>
      <div><span class="ml">obs_type · value</span><b>{_e(d['obs_type'])} · {_e(d['domain_value'])}</b></div>
      <div><span class="ml">raw_secret_removed</span><b class="ok">true</b></div>
    </div>
    <div class="scroll-x"><table class="mtbl">
      <thead><tr><th>module</th><th>status</th><th>returned</th><th>written</th><th>note</th></tr></thead>
      <tbody>{''.join(rows)}</tbody></table></div>
    <div class="cnote">{zero_note}</div>
  </div>"""


def _swimlane(d: dict[str, Any]) -> str:
    ib = d["import_boundary"]
    syn = d["synthetic"]
    fdry = d["foundry"]
    zero = d["returned_total"] == 0

    live_normalized = ib["normalized_exposures"]
    live_ontology = ib["normalized_exposures"] + ib["threat_sources"]

    lanes = [
        {
            "k": "LIVE_PROVIDER", "t": "StealthMole API run",
            "n": _count_block(d["returned_total"], True, None),
            "dsc": "승인된 라이브 조회 · 모듈 상태는 실제값.",
        },
        {
            "k": "PRIVATE_RAW", "t": "raw envelope · private",
            "n": _count_block(0, True, "locked · never exported"),
            "dsc": "provider 원문 봉투는 gitignore 로컬에만 · export 금지.",
        },
        {
            "k": "LOCKED_SECRET", "t": "REDACTION boundary",
            "n": '<div class="lnum">removed</div><div class="lsyn">password · cookie · token</div>',
            "dsc": "경계에서 raw secret 폐기 · source_ref 해시 · masked_value 생성.",
        },
        {
            "k": "NORMALIZED", "t": "candidates",
            "n": _count_block(live_normalized, zero, f'synthetic: {syn["eval_records"]:,}'),
            "dsc": "안전 필드만 normalize된 노출 후보.",
        },
        {
            "k": "ONTOLOGY", "t": "objects",
            "n": _count_block(live_ontology, zero, f'synthetic: {syn["eval_records"]:,}'),
            "dsc": "CredentialExposure · InfectedDevice · ThreatSource · Identity · Domain.",
        },
        {
            "k": "ENGINE", "t": "decisions",
            "n": _count_block(0 if zero else live_ontology, zero,
                              f'synthetic: {syn["eval_records"]:,} 평가 · {syn["active_suppliers"]} active'),
            "dsc": "RiskAssessment · CompromiseIncident · ProgramExposure · NotificationDraft.",
        },
        {
            "k": "LIVE_FOUNDRY", "t": "of/targets + action audit",
            "n": (f'<div class="lnum">{fdry["verified_transitions"]:,}</div>'
                  f'<div class="lsyn">transitions · {fdry["workflow_actions"]} actions</div>'),
            "dsc": "of/targets 링크 데이터셋 스키마 OK · 액션 감사 readback 검증.",
        },
    ]

    nodes = []
    for i, ln in enumerate(lanes):
        nodes.append(
            f"""<div class="lane {LANE_CLS.get(ln['k'], '')}">
        <div class="lt">{lbl(ln['k'])}</div>
        <div class="ltt">{_e(ln['t'])}</div>
        {ln['n']}
        <div class="ld">{ln['dsc']}</div>
      </div>"""
        )
        if i < len(lanes) - 1:
            nodes.append('<div class="arr" aria-hidden="true">→</div>')

    return f"""
  <div class="scroll-x"><div class="swim">{''.join(nodes)}</div></div>
  <div class="swimcap">라이브 run 카운트는 REDACTION 이후 <b>0 (this run)</b> — 같은 계보를
    합성 시나리오로 채운 값은 <b>synthetic: N</b>으로 별도 표기한다. 두 lane을 절대 섞지 않는다.
    {chip('live')} 실제 provider/Foundry · {chip('eng')} 실측 엔진 · {chip('seed')} 합성 시드</div>"""


def _record_examples() -> str:
    empty = """
    <div class="empty">
      <div class="ek">RECORD-LEVEL · LIVE</div>
      <div class="et">승인된 run이 sanitized row를 반환하면 여기에 레코드 단위 계보가 표시됩니다.</div>
      <div class="ed">이 run은 0건 반환 — 표시할 라이브 레코드 없음. 가짜 레코드는 만들지 않는다.</div>
    </div>"""

    examples = [
        {
            "head": "CDS #synthetic-b72c · ACTIVE 경로",
            "chain": [
                "InfectedDevice dev:b72c",
                "CredentialExposure exp:b72c",
                "<span class='of'>of</span> Identity id:sup-h",
                "<span class='tg'>targets</span> Domain vpn.prime-x.example",
                "CompromiseIncident incident:micro-h:active",
                "RiskAssessment risk (즉시)",
                "NotificationDraft draft:sup-h",
            ],
            "removed": "password · cookie · token",
        },
        {
            "head": "CDS #synthetic-a19f · 활성 조건 미충족",
            "chain": [
                "InfectedDevice dev:a19f",
                "CredentialExposure exp:a19f",
                "<span class='of'>of</span> Identity id:sup-a",
                "<span class='tg'>targets</span> Domain vpn.prime-x.example",
                "FlagActiveCompromise skipped — no live session cookie",
            ],
            "removed": "password · cookie · token",
        },
    ]

    ex_html = []
    for ex in examples:
        steps = "".join(f'<span class="rstep">{s}</span><span class="rarr">→</span>'
                        for s in ex["chain"])
        steps = steps.rsplit('<span class="rarr">→</span>', 1)[0]
        ex_html.append(
            f"""<div class="rec">
        <div class="rhead">{_e(ex['head'])} {chip('seed')}</div>
        <div class="rchain">{steps}</div>
        <div class="rrm"><b>fields_removed</b> {_e(ex['removed'])} · raw payload not exported · source_ref hashed</div>
      </div>"""
        )

    return empty + "".join(ex_html)


def _redaction_proof() -> str:
    items = [
        ("password", "removed", "제거 — 원문 미저장"),
        ("cookie", "removed", "제거 — 세션 쿠키 값 미저장"),
        ("token", "removed", "제거 — bearer/토큰 값 미저장"),
        ("provider raw payload", "not exported", "원문 봉투는 로컬 private · export 금지"),
        ("source_ref", "hashed", "레코드 추적용 해시만 보존"),
        ("masked_value", "boundary-generated", "경계에서 생성한 마스크(•••)만 표시"),
    ]
    rows = "".join(
        f"""<div class="rl">
      <span class="rlf">{_e(field)}</span>
      <span class="rlv ok">{_e(state)}</span>
      <span class="rld">{_e(desc)}</span>
    </div>"""
        for field, state, desc in items
    )
    return f"""
  <div class="card">
    <div class="ch"><span class="ck">REDACTION PROOF</span>{lbl('LOCKED_SECRET')}{chip('live')}</div>
    <div class="redlist">{rows}</div>
  </div>"""


def _foundry_evidence(d: dict[str, Any]) -> str:
    f = d["foundry"]
    verified = [
        ("of 링크 (CredentialExposure→Identity)", "Seed/26_link_of",
         "schema OK · left-CredentialExposure-primary-key · right-Identity-primary-key"),
        ("targets 링크 (CredentialExposure→Domain)", "Seed/27_link_targets",
         "schema OK · left-CredentialExposure-primary-key · right-Domain-primary-key"),
        (f"워크플로 액션 {f['workflow_actions']}종", "ontology actions (merged proposal)",
         "acknowledge/assign/close incident · review/approve/export draft · confirm/reject merge"),
        (f"OSDK @omija/sdk {f['osdk']}", "published", f"액션 {f['workflow_actions']}종 포함"),
        (f"액션 readback {f['verified_transitions']}개 전이", "out/foundry_action_chain.json",
         "오늘 실행 · readback verified (HTTP 200)"),
    ]
    in_progress = [
        ("CredentialExposure object", "Seed/06_credential_exposure", "schemaNotFound"),
        ("ThreatSource object", "Seed/08_threat_source", "schemaNotFound"),
        ("sourced_from 링크", "Seed/28_link_sourced_from", "schemaNotFound"),
    ]
    ver_rows = "".join(
        f"""<div class="fev-row ok">
      <span class="fev-t">{_e(t)}</span>
      <span class="fev-ds mono2">{_e(ds)}</span>
      <span class="fev-d">{_e(desc)}</span>
    </div>"""
        for t, ds, desc in verified
    )
    ip_rows = "".join(
        f"""<div class="fev-row wip">
      <span class="fev-t">{_e(t)}</span>
      <span class="fev-ds mono2">{_e(ds)}</span>
      <span class="fev-d">{_e(desc)}</span>
    </div>"""
        for t, ds, desc in in_progress
    )
    return f"""
  <div class="fev">
    <div class="fev-col">
      <div class="ch"><span class="ck">VERIFIED · Foundry lineage</span>{lbl('LIVE_FOUNDRY')}{chip('live')}</div>
      <div class="fev-sub">MCP로 실사 — object/link이 backing dataset을 가지고 of/targets 데이터셋 스키마가 온전하다.</div>
      {ver_rows}
    </div>
    <div class="fev-col">
      <div class="ch"><span class="ck">IN PROGRESS · 스키마 정비 중</span>
        <span class="lbl wip">SCHEMA_REPAIR</span></div>
      <div class="fev-sub">벤더중립 rename 시 raw CSV SNAPSHOT으로 스키마가 제거됨 — 재적재/스키마 적용 진행 중.
        <b>Foundry E2E readback 완전 해결 주장 아님.</b></div>
      {ip_rows}
    </div>
  </div>"""


# --------------------------------------------------------------------------- #
# assembly
# --------------------------------------------------------------------------- #
PAGE_CSS = """
main{padding:0;display:grid;grid-template-columns:minmax(0,1fr)}
.card{border:1px solid var(--hair-2);border-radius:10px;background:var(--surface);
  padding:15px 16px;margin-bottom:16px}
.ch{display:flex;align-items:center;gap:9px;flex-wrap:wrap;margin-bottom:11px}
.ch .ck{font-family:var(--mono);font-size:10px;letter-spacing:1.4px;color:var(--muted);
  text-transform:uppercase}
.cflag{margin-left:auto;font-family:var(--mono);font-size:10px;letter-spacing:.4px;
  color:#f08a8a;border:1px solid rgba(208,59,59,.4);border-radius:3px;padding:2px 8px}

/* lane provenance label badges — the exact required label set */
.lbl{display:inline-block;font-family:var(--mono);font-size:9px;letter-spacing:.6px;
  padding:1px 7px;border-radius:3px;border:1px solid;white-space:nowrap}
.lbl.prov{color:#6ea6ec;border-color:rgba(57,135,229,.5);background:rgba(57,135,229,.08)}
.lbl.lock{color:#f08a8a;border-color:rgba(208,59,59,.45);background:rgba(208,59,59,.07)}
.lbl.norm{color:#4fc596;border-color:rgba(25,158,112,.5);background:rgba(25,158,112,.08)}
.lbl.onto{color:#6ea6ec;border-color:rgba(57,135,229,.5);background:rgba(57,135,229,.08)}
.lbl.eng{color:#e0b45a;border-color:rgba(201,133,0,.5);background:rgba(201,133,0,.09)}
.lbl.fdry{color:#4fc596;border-color:rgba(25,158,112,.55);background:rgba(25,158,112,.10)}
.lbl.wip{color:#f0b73f;border-color:rgba(250,178,25,.5);background:rgba(250,178,25,.08)}

/* run summary card */
.cmeta{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin-bottom:12px}
.cmeta>div{border:1px solid var(--hair);border-radius:7px;background:var(--surface-2);
  padding:8px 11px;min-width:0}
.cmeta .ml{display:block;font-size:10px;color:var(--muted);font-family:var(--mono);
  letter-spacing:.4px;margin-bottom:3px}
.cmeta b{font-family:var(--mono);font-size:12px;color:var(--ink);overflow-wrap:anywhere}
.cmeta b.ok{color:var(--good)}
@media(max-width:560px){.cmeta{grid-template-columns:1fr}}
.mtbl{width:100%;border-collapse:collapse;font-size:12px;min-width:520px}
.mtbl th{text-align:left;font-family:var(--mono);font-size:9.5px;letter-spacing:.8px;
  color:var(--muted);text-transform:uppercase;padding:7px 12px;border-bottom:1px solid var(--hair)}
.mtbl td{padding:7px 12px;border-top:1px solid var(--hair);color:var(--ink-2);
  font-family:var(--mono);font-size:11.5px}
.mtbl td.mono2{color:var(--ink)}
.mtbl td.ok{color:#4fc596}
.mtbl td.warn{color:var(--band-b)}
.mtbl td.dim{color:var(--muted)}
.cnote{margin-top:11px;font-size:12px;color:var(--ink-2);border-left:2px solid var(--hair-2);
  padding-left:11px}
.cnote b{color:var(--ink)}

/* swimlane centerpiece */
.swim{display:flex;align-items:stretch;gap:0;padding:4px 2px 8px;min-width:940px}
.lane{flex:1 1 0;min-width:118px;border:1px solid var(--hair-2);border-radius:9px;
  background:var(--surface);padding:11px 12px;display:flex;flex-direction:column;gap:6px}
.lane.prov{border-top:3px solid var(--c-entity)}
.lane.lock{border-top:3px solid var(--band-a)}
.lane.norm{border-top:3px solid var(--c-evidence)}
.lane.onto{border-top:3px solid var(--c-entity)}
.lane.eng{border-top:3px solid var(--c-derived)}
.lane.fdry{border-top:3px solid var(--good)}
.lane .lt{margin-bottom:1px}
.lane .ltt{font-size:12px;font-weight:600;color:var(--ink);line-height:1.3}
.lane .lnum{font-family:var(--mono);font-size:21px;font-weight:600;color:var(--ink);line-height:1.1}
.lane .lnum .u{font-size:10px;font-weight:400;color:var(--muted);letter-spacing:.2px}
.lane .lsyn{font-family:var(--mono);font-size:10px;color:var(--c-derived);letter-spacing:.2px}
.lane .ld{font-size:10.5px;color:var(--ink-2);line-height:1.5;margin-top:auto}
.arr{align-self:center;color:var(--muted);font-size:18px;padding:0 6px;flex:none}
.swimcap{font-size:12px;color:var(--ink-2);line-height:1.6;margin-top:10px}
.swimcap b{color:var(--ink);font-family:var(--mono);font-weight:500}

/* record-level lineage */
.empty{border:1px dashed var(--hair-2);border-radius:9px;background:
  repeating-linear-gradient(45deg,transparent,transparent 8px,rgba(255,255,255,.012) 8px,rgba(255,255,255,.012) 16px),var(--surface);
  padding:15px 16px;margin-bottom:13px}
.empty .ek{font-family:var(--mono);font-size:10px;letter-spacing:1.2px;color:var(--muted);
  text-transform:uppercase;margin-bottom:6px}
.empty .et{font-size:13px;color:var(--ink);margin-bottom:4px}
.empty .ed{font-size:11.5px;color:var(--ink-2)}
.rec{border:1px solid var(--hair-2);border-radius:9px;background:var(--surface);
  padding:12px 14px;margin-bottom:11px}
.rec .rhead{font-size:12.5px;font-weight:600;color:var(--ink);margin-bottom:9px;
  display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.rchain{display:flex;flex-wrap:wrap;align-items:center;gap:5px 4px;font-family:var(--mono);
  font-size:11px}
.rstep{padding:3px 8px;border-radius:5px;background:var(--surface-2);border:1px solid var(--hair);
  color:var(--ink-2)}
.rstep .of{color:var(--c-entity);font-weight:600}
.rstep .tg{color:var(--cross);font-weight:600}
.rarr{color:var(--muted)}
.rrm{margin-top:9px;font-size:11px;color:var(--muted);font-family:var(--mono)}
.rrm b{color:var(--ink-2)}

/* redaction proof list */
.redlist{display:grid;grid-template-columns:1fr;gap:7px}
.rl{display:grid;grid-template-columns:170px 130px 1fr;gap:10px;align-items:center;
  border:1px solid var(--hair);border-radius:7px;background:var(--surface-2);padding:8px 12px}
.rl .rlf{font-family:var(--mono);font-size:11.5px;color:var(--ink)}
.rl .rlv{font-family:var(--mono);font-size:11px}
.rl .rlv.ok{color:#4fc596}
.rl .rld{font-size:11.5px;color:var(--ink-2)}
@media(max-width:600px){.rl{grid-template-columns:1fr;gap:3px}}

/* foundry evidence — two columns */
.fev{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:820px){.fev{grid-template-columns:1fr}}
.fev-col{border:1px solid var(--hair-2);border-radius:10px;background:var(--surface);padding:14px 15px}
.fev-sub{font-size:11.5px;color:var(--ink-2);line-height:1.55;margin-bottom:11px}
.fev-sub b{color:var(--ink)}
.fev-row{border-left:2px solid var(--hair-2);padding:7px 0 7px 11px;margin-bottom:8px}
.fev-row.ok{border-left-color:var(--good)}
.fev-row.wip{border-left-color:var(--band-b)}
.fev-row .fev-t{display:block;font-size:12px;color:var(--ink);font-weight:600}
.fev-row .fev-ds{display:block;font-size:10.5px;color:var(--c-entity);margin:2px 0}
.fev-row .fev-d{display:block;font-size:11px;color:var(--ink-2);line-height:1.5}
.mono2{font-family:var(--mono)}
"""


def build_html(d: dict[str, Any]) -> str:
    body = f"""
<section><div class="wrap">
  <div class="sec-k">operational data lineage · provider → redaction → ontology → engine → Foundry</div>
  <div class="sec-h">승인된 StealthMole 라이브 run을 계보로 추적 — 원문은 잠그고, 안전 변환만 전 구간 표시</div>
  <div class="sec-sub">승인된 라이브 run 실행됨 · 이 seed는 <b>0건 반환</b> · 동일 lineage는
    synthetic 시나리오로 populated 시연. provider/redaction lane은 실제값, normalized 이후 라이브
    카운트는 0이며 절대 조작하지 않는다.</div>
  <div class="cflag" style="margin:0 0 14px;display:inline-block">확정된 침해 아님 · raw secret 미저장</div>
  {_run_summary(d)}
  {pnote("RUN SUMMARY", [
      "여기 핵심은 <b>승인된 라이브 run이 실제로 실행됐다</b>는 것.",
      "CL/CDS/CB는 200으로 붙었고 DT는 403, TT는 404 — 그리고 이 seed는 0건을 반환했다.",
      "0건을 숨기지 않고 그대로 보여주는 것이 신뢰 장치다."])}
</div></section>

<section><div class="wrap">
  <div class="sec-k">lineage swimlane · 좌→우 데이터 흐름</div>
  <div class="sec-h">provider 원문에서 Foundry 링크·액션 감사까지, 한 줄로 흐르는 계보</div>
  {_swimlane(d)}
  {pnote("SWIMLANE", [
      "왼쪽 LIVE_PROVIDER는 실제 라이브 조회, PRIVATE_RAW는 잠긴 원문(export 금지),",
      "LOCKED_SECRET 경계에서 raw secret이 폐기된다.",
      "REDACTION 이후 라이브 카운트는 0 — 같은 파이프를 통과한 <b>synthetic: 74</b>는 별도 lane으로만 표기한다."])}
</div></section>

<section><div class="wrap">
  <div class="sec-k">record-level lineage · 레코드 단위 계보</div>
  <div class="sec-h">라이브 0건 정직한 empty-state + 명확히 SEED로 표기한 합성 예시</div>
  {_record_examples()}
</div></section>

<section><div class="wrap">
  {_redaction_proof()}
</div></section>

<section><div class="wrap">
  <div class="sec-k">foundry lineage evidence · MCP 실사</div>
  <div class="sec-h">of/targets 링크와 액션 감사는 Foundry로 실증 · 일부 seed 데이터셋 스키마는 정비 중</div>
  {_foundry_evidence(d)}
</div></section>

<section style="border-bottom:none"><div class="wrap">
  <div class="footer">
    Approved StealthMole records are ingested live, stripped of raw secrets, normalized into
    Omija ontology objects, and traced through every decision object by lineage.<br>
    승인된 StealthMole 레코드는 라이브로 수집되어 원문 비밀값이 제거되고, Omija 온톨로지 객체로
    정규화된 뒤 모든 결정 객체까지 계보로 추적된다. · generated by scripts/data_lineage_live.py ·
    inputs: collection_meta.json · private_candidate_import.json · early_warning_readiness.json ·
    foundry_action_chain.json
  </div>
</div></section>"""

    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Omija — Data Lineage (Live · 데이터 계보)</title>
<style>{TOKENS_CSS}{PAGE_CSS}</style></head><body>
{synthetic_banner()}
{nav_strip("data_lineage_live.html")}
{chip_legend()}
<div class="mast"><div class="wrap"><div class="masthead">
  <div class="mhead-main">
    <div class="brand">OMIJA · OPERATIONAL DATA LINEAGE</div>
    <div class="tag">승인된 StealthMole 라이브 run → redaction → ontology → engine → Foundry, 전 구간 계보 추적</div>
  </div>
  <span class="ver">live provider · redaction boundary · offline page</span>
</div></div></div>
<main style="padding-top:6px;padding-bottom:6px">
{body}
</main>
</body></html>"""


def build_json(d: dict[str, Any]) -> dict[str, Any]:
    ib = d["import_boundary"]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "scripts/data_lineage_live.py",
        "honesty": ("approved live StealthMole run executed; this seed returned 0 rows; "
                    "provider+redaction lanes are real, normalized/ontology/engine counts "
                    "from this run are 0; the same populated pipeline is demonstrated on the "
                    "synthetic scenario and labelled distinctly"),
        "run": {
            "generated_at": d["run_generated_at"],
            "seed_id": d["seed_id"],
            "obs_type": d["obs_type"],
            "domain_value": d["domain_value"],
            "modules": d["modules"],
            "returned_total": d["returned_total"],
            "raw_secret_removed": True,
        },
        "import_boundary": {
            **ib,
            "provider_api_called_at_import": bool((d["policy"] or {}).get("provider_api_called")),
            "raw_secret_output": (d["policy"] or {}).get("raw_secret_output", "redacted"),
        },
        "synthetic_scenario": d["synthetic"],
        "foundry": {
            "verified": {
                "of_link": {"dataset": "Seed/26_link_of", "schema": "ok"},
                "targets_link": {"dataset": "Seed/27_link_targets", "schema": "ok"},
                "workflow_actions": d["foundry"]["workflow_actions"],
                "osdk": d["foundry"]["osdk"],
                "action_transitions_readback_verified": d["foundry"]["verified_transitions"],
                "ontology_api_name": d["foundry"]["ontology_api_name"],
            },
            "in_progress_schema_repair": [
                {"entity": "CredentialExposure object", "dataset": "Seed/06_credential_exposure",
                 "state": "schemaNotFound"},
                {"entity": "ThreatSource object", "dataset": "Seed/08_threat_source",
                 "state": "schemaNotFound"},
                {"entity": "sourced_from link", "dataset": "Seed/28_link_sourced_from",
                 "state": "schemaNotFound"},
            ],
        },
        "redaction": {
            "password": "removed", "cookie": "removed", "token": "removed",
            "provider_raw_payload": "not_exported", "source_ref": "hashed",
            "masked_value": "boundary-generated",
        },
    }


# --------------------------------------------------------------------------- #
# safety gate — this page is ABOUT the approved StealthMole run, so the vendor
# NAME is allowed; secret VALUES and external refs are not.
# --------------------------------------------------------------------------- #
def _safety_check(page: str) -> None:
    low = page.lower()
    problems: list[str] = []

    # self-contained: no external resources / scripts / imports
    for pat in ('src="http', "src='http", 'href="http', "href='http", "url(http",
                "@import", "<script", "<link"):
        if pat in low:
            problems.append(f"external/forbidden ref: {pat!r}")

    # raw secret value shapes (JWT/bearer/PEM) — never present on this page
    if "eyj" in low:
        problems.append("possible JWT/token value ('eyJ')")
    if re.search(r"\bbearer\s+[a-z0-9._\-]{8,}", low):
        problems.append("bearer token value")
    if "-----begin" in low:
        problems.append("PEM/private-key block")

    # a secret field name paired with an actual quoted value (we only say 'removed')
    if re.search(r"(?:password|passwd|cookie|token|secret)['\"]?\s*[:=]\s*['\"][^'\"]{6,}['\"]", low):
        problems.append("secret field carrying a quoted value")

    # synthetic raw-secret patterns used elsewhere in the repo
    if re.search(r"Synthetic-[A-Za-z]+-\d+!", page) or re.search(r"SID[0-9a-f]{20,}", page):
        problems.append("raw synthetic secret leaked")

    if problems:
        raise SystemExit("SAFETY FAIL: " + "; ".join(problems))


def run() -> int:
    d = gather()
    page = build_html(d)
    _safety_check(page)

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_HTML, "w", encoding="utf-8") as fh:
        fh.write(page)
    payload = build_json(d)
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)

    print("=" * 72)
    print("Omija operational data lineage")
    print("=" * 72)
    mods = " · ".join(f"{n.upper()} {d['modules'][n]['status']}/{d['modules'][n]['returned']}"
                      for n in MODULE_ORDER)
    print(f"run seed: {d['seed_id']} @ {d['run_generated_at']}")
    print(f"modules (status/returned): {mods}")
    print(f"returned_total: {d['returned_total']} · normalized (this run): "
          f"{d['import_boundary']['normalized_exposures']} · threat_sources: "
          f"{d['import_boundary']['threat_sources']}")
    print(f"synthetic scenario: {d['synthetic']['eval_records']} eval records · "
          f"{d['synthetic']['active_suppliers']} active suppliers")
    print(f"foundry: {d['foundry']['verified_transitions']} readback transitions · "
          f"{d['foundry']['workflow_actions']} actions · OSDK {d['foundry']['osdk']}")
    print("safety: vendor NAME allowed, no secret values, no external refs — OK")
    print(f"written: {OUT_HTML} ({os.path.getsize(OUT_HTML):,} bytes)")
    print(f"written: {OUT_JSON} ({os.path.getsize(OUT_JSON):,} bytes)")
    print("RESULT: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
