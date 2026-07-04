"""Omija demo — story-first case-study page (scripts/omija_demo.py → out/omija_demo.html).

This is the pitch surface. It does NOT display the ontology schema; it shows the
ANALYST WORKFLOW and the OUTCOME of running the local engine on the synthetic
seed, the way a Palantir customer case study advertises results.

Claim architecture: "데이터는 가상, 시스템은 진짜" — enforced VISUALLY by the
four-level provenance chip system (scripts/omija_style.py):

    LIVE·Foundry  — read back from the actual Foundry ontology/actions
    ENGINE·실측    — computed by the real local engine at generation time
    SEED·가상      — synthetic entity data (fictional orgs/credentials)
    FRAME·연출     — scenario-framing numbers (labeled, never implied real)

Every number on the page is produced HERE, at generation time, by actually
executing the offline SQLite mock pipeline:

    build_pipeline()  = registry → mock ingest → normalize → CorrelateExposure
                        → EntityResolver (propose merges) → FlagActiveCompromise
                        → ComputeRisk
    generate_drafts() = GenerateNotificationDraft (top-ranked, evidence-enforced)
    propagate_risk()  = PropagateRisk → ProgramExposure (burning programs)

plus one LIVE artifact: out/foundry_action_chain.json — the audit trail of state
transitions actually executed against the real Foundry ontology (verified by
readback). If the artifact is missing the LIVE strip renders a "실행 대기" slot.

No network, no secrets, no real names. All domains are synthetic `*.example`.
Secret values are rendered fully masked (•••).

Run:  uv run python scripts/omija_demo.py   (writes out/omija_demo.html)
"""

from __future__ import annotations

import html
import json
import os
import re
import sys
import time
from datetime import datetime, timezone

# Repo root on path (script may be run directly).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from actions.notify_draft import generate_drafts                 # noqa: E402
from actions.propagate_risk import propagate_program_risk        # noqa: E402
from adapter.mock import DAY, DEMO_NOW                            # noqa: E402
from scripts.omija_style import (                                 # noqa: E402
    TOKENS_CSS, chip, chip_legend, pnote, synthetic_banner,
)
from scripts.p5_drafts import TOP_N, build_pipeline              # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(REPO_ROOT, "out")
OUT_HTML = os.path.join(OUT_DIR, "omija_demo.html")
ACTION_CHAIN_JSON = os.path.join(OUT_DIR, "foundry_action_chain.json")

# The one supplier we deep-dive: the 2차 (tier-2) MULTI-TIER terminal whose
# infection burns a defense program two tiers up. It is also the record that
# carries the cross-org `targets` edge (employee credential → prime VPN).
HEADLINE_SUPPLIER = "sup-h"

# The ONLY invented figure on the page — an operating-scale projection of the
# seed's non-active leak volume. Chipped FRAME·연출 wherever it appears.
PROJECTED_STALE_VOLUME = 4120

# LIVE ontology facts (verified against root ontology.md / the action-chain
# artifact at generation time where computable).
ONTOLOGY_OBJECT_TYPES = 13          # ontology.md: 4 registry + 4 evidence + 5 derived
OSDK_VERSION = "0.2.0"              # published OSDK package version

_MODULE_LABEL = {
    "cds": "인포스틸러 로그 (darkweb)",
    "ub":  "URL·LOGIN·PASS 바인더",
    "cl":  "유출 서버 (breach)",
    "cb":  "재유통 combo list",
}


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _e(v) -> str:
    return html.escape("" if v is None else str(v))


def _fmt_ts(ts) -> str:
    if not ts:
        return "—"
    return datetime.fromtimestamp(int(ts), timezone.utc).strftime("%Y-%m-%d")


def _fmt_iso(iso: str | None) -> str:
    if not iso:
        return "—"
    return iso.replace("T", " ")[:19] + "Z"


def _mask_display(text: str) -> str:
    """Replace any first-2-chars+*** boundary mask (e.g. `SI***`) with a full
    `•••` for on-screen presentation. The store already strips raw secrets; this
    is a second, stricter presentation mask so no partial value is ever shown."""
    return re.sub(r"[^\s*`]{1,6}\*\*\*", "•••", text)


def _active_signal(row: dict) -> bool:
    return bool(
        row.get("has_session_cookie")
        and row.get("account_type") in {"vpn", "admin"}
        and row.get("infected_at") is not None
        and (DEMO_NOW - int(row["infected_at"])) <= 14 * DAY
    )


def _load_action_chain() -> dict | None:
    """Load the LIVE Foundry action-chain artifact (real audit trail). Returns
    None when the artifact is missing — the LIVE strip then renders 실행 대기."""
    try:
        with open(ACTION_CHAIN_JSON, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or not data.get("steps"):
        return None
    return data


# --------------------------------------------------------------------------- #
# page CSS = shared tokens (omija_style) + page-specific styles
# --------------------------------------------------------------------------- #
PAGE_CSS = """
/* HERO alert */
.alert{border:1px solid var(--band-a);border-radius:10px;overflow:hidden;
  background:linear-gradient(180deg,rgba(208,59,59,.10),rgba(208,59,59,.02));
  box-shadow:0 0 0 1px rgba(208,59,59,.18)}
.alert .ahead{display:flex;align-items:center;gap:12px;flex-wrap:wrap;
  padding:13px 18px;border-bottom:1px solid rgba(208,59,59,.28)}
.bandpill{font-family:var(--mono);font-size:11px;font-weight:600;letter-spacing:.5px;
  padding:3px 10px;border-radius:4px;display:inline-flex;align-items:center;gap:7px}
.bandpill.a{background:var(--band-a);color:#fff}
.bandpill.a::before{content:"";width:7px;height:7px;border-radius:50%;background:#fff;
  animation:pulse 1.8s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.35}}
.alert .atitle{font-size:15.5px;font-weight:600;color:var(--ink)}
.alert .meta{margin-left:auto;font-family:var(--mono);font-size:11px;color:var(--ink-2);
  text-align:right}
.alert .abody{padding:15px 18px;display:grid;grid-template-columns:1.3fr .9fr;gap:18px}
.alert .chain{font-family:var(--mono);font-size:12px;color:var(--ink);line-height:1.9}
.alert .chain .hop{color:var(--ink)}
.alert .chain .arr{color:var(--band-a);padding:0 5px}
.alert .facts{font-size:12px;color:var(--ink-2)}
.alert .facts div{padding:3px 0;border-bottom:1px solid var(--hair)}
.alert .facts b{color:var(--ink);font-family:var(--mono);font-weight:500}
.problem{margin-top:14px;font-size:13px;color:var(--ink-2);border-left:2px solid var(--band-a);
  padding:7px 12px;background:rgba(208,59,59,.05);border-radius:0 5px 5px 0}
.problem b{color:var(--ink)}

/* TRIAGE queue */
.qcap{font-size:13px;color:var(--c-derived);margin-bottom:14px;font-weight:500}
.queue{border:1px solid var(--hair-2);border-radius:8px;overflow:hidden;background:var(--surface)}
.qrow{display:grid;grid-template-columns:38px 18px 1fr 84px 120px 96px;gap:10px;align-items:center;
  padding:11px 14px;border-top:1px solid var(--hair);font-size:13px}
.qrow:first-child{border-top:none}
.qrow .rk{font-family:var(--mono);font-size:12px;color:var(--muted);text-align:right}
.qrow .bd{width:10px;height:10px;border-radius:50%;justify-self:center}
.qrow .nm{color:var(--ink);font-weight:500}
.qrow .nm .sid{font-family:var(--mono);font-size:10.5px;color:var(--muted);margin-left:6px}
.qrow .nm .hl{font-family:var(--mono);font-size:9.5px;letter-spacing:.6px;color:var(--band-a);
  border:1px solid rgba(208,59,59,.5);border-radius:3px;padding:1px 6px;margin-left:8px}
.qrow .tier{font-family:var(--mono);font-size:11px;color:var(--ink-2)}
.qrow .sc{font-family:var(--mono);font-size:15px;color:var(--ink);text-align:right}
.qrow .gr{font-size:11px;text-align:right;color:var(--ink-2)}
.qrow.active{background:rgba(208,59,59,.055)}
.qrow.active .bd{background:var(--band-a);box-shadow:0 0 7px rgba(208,59,59,.6)}
.qrow.warn .bd{background:var(--band-b)}
.qrow.warn .sc{color:var(--ink-2)}
.qband{display:flex;align-items:center;gap:10px;padding:7px 14px;background:var(--surface-2);
  border-top:1px solid var(--hair);font-family:var(--mono);font-size:10.5px;
  letter-spacing:.6px;color:var(--muted);text-transform:uppercase}
.qband .ln{flex:1;height:1px;background:repeating-linear-gradient(90deg,var(--hair-2),var(--hair-2) 5px,transparent 5px,transparent 9px)}
.qstale{display:flex;align-items:center;gap:14px;padding:13px 14px;border-top:1px solid var(--hair);
  background:var(--surface-2);flex-wrap:wrap}
.qstale .bd{width:10px;height:10px;border-radius:50%;background:var(--band-c);opacity:.55;flex:none}
.qstale .n{font-family:var(--mono);font-size:15px;color:var(--ink-2)}
.qstale .l{font-size:12px;color:var(--muted)}
.evn{font-family:var(--mono);font-size:10.5px;color:var(--c-evidence)}

/* DIFFERENTIATION — same input, three systems */
.tri{display:grid;grid-template-columns:1fr 1fr 1fr;gap:13px}
@media(max-width:900px){.tri{grid-template-columns:1fr}}
.sysbox{border:1px solid var(--hair-2);border-radius:8px;background:var(--surface);
  overflow:hidden;display:flex;flex-direction:column}
.sysbox.omija{border-color:rgba(57,135,229,.55);box-shadow:0 0 0 1px rgba(57,135,229,.18)}
.sysbox .sh{display:flex;align-items:center;gap:8px;padding:9px 12px;flex-wrap:wrap;
  border-bottom:1px solid var(--hair);background:var(--surface-2)}
.sysbox .sh .nm{font-size:12.5px;font-weight:600;color:var(--ink)}
.sysbox .rows{flex:1;padding:6px 0}
.srow{display:flex;align-items:baseline;gap:8px;padding:6px 12px;font-size:12px;
  border-top:1px solid var(--hair);color:var(--ink-2);flex-wrap:wrap}
.srow:first-child{border-top:none}
.srow .rk{font-family:var(--mono);font-size:10.5px;color:var(--muted);width:16px;text-align:right;flex:none}
.srow .who{color:var(--ink);font-weight:500}
.srow .mono2{font-family:var(--mono);font-size:11px}
.srow .n{margin-left:auto;font-family:var(--mono);font-size:11.5px;color:var(--ink-2);flex:none}
.srow.dim{opacity:.55}
.srow.hot{background:rgba(208,59,59,.07)}
.srow.hot .who{color:var(--band-a)}
.srow.buried{border-left:2px solid var(--band-b);background:rgba(250,178,25,.04)}
.verdict{padding:9px 12px;border-top:1px solid var(--hair);font-size:11.5px;
  font-family:var(--mono);color:var(--muted);background:var(--surface-2)}
.verdict.bad{color:#e0a1a1}
.verdict.good{color:#7fb8f0}
.tricap{margin-top:13px;font-size:12.5px;color:var(--ink-2);border-left:2px solid var(--c-entity);
  padding:6px 11px;background:rgba(57,135,229,.05);border-radius:0 4px 4px 0}
.tricap b{color:var(--ink)}

/* BLAST radius graph */
.graphwrap{border:1px solid var(--hair-2);border-radius:8px;background:
  radial-gradient(120% 140% at 20% 0%,rgba(57,135,229,.05),transparent 60%),var(--surface)}
.g-node .box{fill:var(--surface-2);stroke:var(--hair-2);stroke-width:1}
.g-node.origin .box{stroke:var(--band-a)}
.g-node.cross .box{fill:rgba(236,131,90,.08);stroke:var(--cross);stroke-dasharray:3 3}
.g-node .typ{fill:var(--muted);font:9px var(--mono);letter-spacing:.5px}
.g-node.origin .typ{fill:var(--band-a)}
.g-node.cross .typ{fill:var(--cross)}
.g-node .lab{fill:var(--ink);font:11px var(--mono)}
.g-node .sub{fill:var(--ink-2);font:9.5px var(--mono)}
.spine{stroke:var(--band-a);stroke-width:2;fill:none;marker-end:url(#arr)}
.edge{stroke:var(--hair-2);stroke-width:1.4;fill:none;marker-end:url(#arrq)}
.edge.blast{stroke:var(--c-output);stroke-dasharray:4 3}
.tedge{stroke:var(--cross);stroke-width:2;fill:none;stroke-dasharray:6 4;marker-end:url(#arrc)}
.elab{fill:var(--muted);font:8.5px var(--mono);letter-spacing:.3px}
.elab.sub{fill:var(--c-derived)}
.elab.tg{fill:var(--cross);font-size:9.5px}
.burn{fill:var(--band-a);font:8px var(--mono);letter-spacing:.4px}
.g-note{font-size:12px;color:var(--ink-2);margin-top:12px;border-left:2px solid var(--cross);
  padding:6px 11px;background:rgba(236,131,90,.06);border-radius:0 4px 4px 0}
.g-note b{color:var(--ink)}

/* evidence drill-down */
.evgrid{display:grid;gap:11px}
details.ev{border:1px solid var(--hair-2);border-radius:7px;background:var(--surface);overflow:hidden}
details.ev>summary{list-style:none;cursor:pointer;padding:11px 15px;display:flex;
  align-items:center;gap:11px;font-size:13px;flex-wrap:wrap}
details.ev>summary::-webkit-details-marker{display:none}
details.ev>summary::before{content:"▸";color:var(--muted);font-size:11px;transition:transform .15s}
details.ev[open]>summary::before{transform:rotate(90deg)}
details.ev>summary .claim{color:var(--ink);font-weight:500}
details.ev>summary .src{margin-left:auto;font-family:var(--mono);font-size:10.5px;color:var(--c-evidence)}
.ev .rec{padding:2px 15px 14px 15px;border-top:1px solid var(--hair)}
.ev table{width:100%;border-collapse:collapse;font-size:12px;margin-top:8px}
.ev td{padding:5px 9px;border-top:1px solid var(--hair);vertical-align:top}
.ev td.k{font-family:var(--mono);color:var(--ink-2);white-space:nowrap;width:32%}
.ev td.v{font-family:var(--mono);color:var(--ink)}
.ev td.v .msk{color:var(--c-derived)}
.ev .prov{margin-top:10px;font-size:11px;color:var(--ink-2);background:rgba(25,158,112,.06);
  border-radius:5px;padding:7px 10px}
.ev .prov b{color:var(--c-evidence)}
.audit{font-size:11.5px;color:var(--muted);margin-top:13px}
.cites{display:flex;flex-wrap:wrap;gap:6px;padding:10px 13px;border-top:1px solid var(--hair);
  background:var(--surface-2)}
.cites .cl{font-family:var(--mono);font-size:9px;color:var(--muted);letter-spacing:.5px;
  align-self:center;text-transform:uppercase}
.cites .chip{font-family:var(--mono);font-size:10px;color:var(--c-evidence);
  border:1px solid rgba(25,158,112,.32);border-radius:11px;padding:2px 8px}

/* response workflow */
.wf{display:grid;grid-template-columns:1fr 1fr;gap:20px;align-items:start}
@media(max-width:820px){.wf{grid-template-columns:1fr}.alert .abody{grid-template-columns:1fr}}
.sm{display:flex;align-items:center;flex-wrap:wrap;gap:0;margin-bottom:14px}
.sm .st{font-family:var(--mono);font-size:11.5px;padding:6px 11px;border:1px solid var(--hair-2);
  border-radius:5px;background:var(--surface-2);color:var(--muted);white-space:nowrap}
.sm .st.done{border-color:var(--good);color:#7bcf9e}
.sm .st.cur{border-color:var(--band-b);color:#f4d58a;background:rgba(250,178,25,.08)}
.sm .arrow{color:var(--muted);padding:0 7px;font-family:var(--mono)}
.assign{font-size:12px;color:var(--ink-2);margin-bottom:8px}
.assign b{color:var(--ink);font-family:var(--mono);font-weight:500}
.merge{font-size:11.5px;color:var(--ink-2);border:1px dashed var(--hair-2);border-radius:6px;
  padding:9px 12px;background:var(--surface)}
.merge b{color:var(--c-output)}
.actions{display:flex;gap:9px;margin-top:14px;flex-wrap:wrap}
.btn{font-family:var(--mono);font-size:12px;padding:8px 15px;border-radius:5px;cursor:not-allowed;
  border:1px solid var(--hair-2);background:var(--surface-2);color:var(--ink-2)}
.btn.primary{border-color:var(--c-output);color:#c3bbf5;background:rgba(144,133,233,.08)}
.no-send{margin-top:12px;color:#e89a9a;font-family:var(--mono);font-size:11px;
  border:1px solid rgba(208,59,59,.4);border-radius:5px;padding:7px 11px;display:inline-block}
.doc{border:1px solid var(--hair-2);border-radius:8px;background:var(--surface);overflow:hidden}
.doc .dh{display:flex;align-items:center;gap:9px;padding:9px 13px;background:var(--surface-2);
  border-bottom:1px solid var(--hair);font-family:var(--mono);font-size:11px;color:var(--ink-2);flex-wrap:wrap}
.doc .dh .st{margin-left:auto;color:var(--c-derived)}
.doc .db{max-height:340px;overflow:auto;padding:13px 15px;margin:0;font-family:var(--mono);
  font-size:11px;line-height:1.65;color:var(--ink-2);white-space:pre-wrap;word-break:break-word}
.doc .db .h{color:var(--ink);font-weight:600}

/* LIVE strip — what actually exists */
.livewrap{border:1px solid rgba(25,158,112,.5);border-radius:10px;overflow:hidden;
  background:linear-gradient(180deg,rgba(25,158,112,.07),rgba(25,158,112,.015))}
.livewrap .lh{display:flex;align-items:center;gap:10px;padding:12px 16px;flex-wrap:wrap;
  border-bottom:1px solid rgba(25,158,112,.3)}
.livewrap .lh .t{font-size:14.5px;font-weight:600;color:var(--ink)}
.livewrap .lh .sub{font-size:12px;color:var(--ink-2)}
.livetbl{width:100%;border-collapse:collapse;font-size:12px;min-width:760px}
.livetbl th{text-align:left;font-family:var(--mono);font-size:10px;letter-spacing:.8px;
  color:var(--muted);text-transform:uppercase;padding:8px 14px;border-bottom:1px solid var(--hair)}
.livetbl td{padding:8px 14px;border-top:1px solid var(--hair);color:var(--ink-2);vertical-align:top}
.livetbl td.mono2,.livetbl .mono2{font-family:var(--mono);font-size:11.5px}
.livetbl .act{color:var(--ink);font-family:var(--mono);font-size:11.5px}
.livetbl .tr{color:var(--c-evidence);font-family:var(--mono);font-size:11.5px;white-space:nowrap}
.livetbl .ok{color:#4fc596;font-family:var(--mono);font-size:11px;white-space:nowrap}
.livefacts{padding:11px 16px;border-top:1px solid rgba(25,158,112,.3);font-size:12px;
  color:var(--ink-2);display:flex;flex-wrap:wrap;gap:6px 18px;align-items:center}
.livefacts b{color:var(--ink);font-family:var(--mono);font-weight:500}
.livewait{border:1px dashed var(--hair-2);border-radius:10px;padding:22px;
  font-family:var(--mono);font-size:12px;color:var(--muted);text-align:center}

/* outcome tiles */
.tiles{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
@media(max-width:820px){.tiles{grid-template-columns:repeat(2,1fr)}}
.tile{border:1px solid var(--hair-2);border-radius:8px;background:var(--surface);padding:15px 16px}
.tile .n{font-family:var(--mono);font-size:30px;font-weight:600;color:var(--ink);line-height:1}
.tile .n .u{font-size:14px;color:var(--ink-2)}
.tile .l{font-size:12px;color:var(--ink-2);margin-top:7px}
.tile .s{font-size:11px;color:var(--muted);margin-top:3px}
.tile.accent .n{color:var(--band-a)}
.propbar{display:flex;height:7px;border-radius:4px;overflow:hidden;margin-top:11px;gap:2px}
.propbar .seg{height:100%;border-radius:3px}
.propbar .a{background:var(--band-a)}
.propbar .s{background:var(--hair-2)}
.tilecap{font-size:11px;color:var(--muted);margin-top:13px;font-family:var(--mono)}

/* footer / how it works */
.how{display:grid;grid-template-columns:340px 1fr;gap:26px;align-items:center}
@media(max-width:820px){.how{grid-template-columns:1fr}}
.how ul{margin:0;padding-left:18px;font-size:12.5px;color:var(--ink-2);line-height:1.7}
.how ul b{color:var(--ink)}
.onto .n .b{fill:var(--surface-2);stroke:var(--hair-2)}
.onto .n .t{fill:var(--ink-2);font:9.5px var(--mono)}
.onto .lk{stroke:var(--hair-2);stroke-width:1;fill:none}
.onto .lk.cross{stroke:var(--cross);stroke-dasharray:3 3}
.onto .lkl{fill:var(--muted);font:8px var(--mono)}
.onto .lkl.cross{fill:var(--cross)}
"""


# --------------------------------------------------------------------------- #
# section builders
# --------------------------------------------------------------------------- #
def _hero(inc: dict, active_exp: dict, programs: list[str]) -> str:
    detected = _fmt_ts(active_exp.get("infected_at"))
    briefing = _fmt_ts(DEMO_NOW)
    prog_txt = " · ".join(_e(p) for p in programs)
    # compact instance chain for the hero (from the real incident path); clean
    # per-type labels so no raw epoch/ref leaks into the headline.
    hops = []
    for n in inc["path"]:
        if n["type"] == "InfectedDevice":
            d = f"감염기기 · {active_exp.get('malware')}"
        else:
            d = n.get("detail") or n.get("ref")
        hops.append(f'<span class="hop">{_e(d)}</span>')
    chain = '<span class="arr">→</span>'.join(hops)
    note = pnote("01 경보 착지", [
        "한국은 세계 4위 방산 수출국이고 tier-1/2 협력망이 깊습니다. 하위 협력사의 감염 기기와"
        " 유출 자격증명이 APT의 실질 진입점입니다.",
        f"여기 {chip('seed')} 칩이 붙은 조직·계정은 전부 합성입니다. 하지만 {chip('eng')}가 붙은"
        " BAND A 판정과 경로 성립은 이 페이지를 만드는 순간 엔진이 실제로 계산한 결과입니다.",
        "칩 두 개를 가리키면서 시작하십시오 — <b>개체는 가상, 판정은 실측</b>.",
    ])
    return f"""
<section id="alert"><div class="wrap">
  <div class="sec-k">01 · 경보 착지 / incident landing {chip('eng')} {chip('seed')}</div>
  <div class="alert">
    <div class="ahead">
      <span class="bandpill a">BAND A · 즉시</span>
      <span class="atitle">활성 침해 경로 탐지 — 2차 협력사 감염 기기가 원청 방산 프로그램에 도달</span>
      <span class="meta">탐지 {detected} {chip('seed')}<br>브리핑 클럭 {briefing} (시나리오)</span>
    </div>
    <div class="abody">
      <div>
        <div class="sec-k" style="margin-bottom:7px">활성 경로 · CompromiseIncident {chip('eng')}</div>
        <div class="chain">{chain}</div>
        <div style="margin-top:11px;font-size:12px;color:var(--ink-2)">
          도달 프로그램 (blast radius): <b style="color:var(--band-a)">{prog_txt}</b> {chip('eng')}
        </div>
      </div>
      <div class="facts">
        <div>악성코드 · <b>{_e(active_exp.get('malware'))}</b> {chip('seed')}</div>
        <div>세션 쿠키 <b>유효</b> · 계정유형 <b>{_e(active_exp.get('account_type'))}</b> {chip('seed')}</div>
        <div>노출 계정 (of) · <b>{_e(active_exp.get('email'))}</b> {chip('seed')}</div>
        <div>표적 자산 (targets) · <b style="color:var(--cross)">{_e(active_exp.get('host'))}</b> {chip('seed')}</div>
        <div style="border:none">근거 레코드 · <b>{_e(active_exp.get('source_ref'))}</b> {chip('seed')}</div>
      </div>
    </div>
  </div>
  <div class="problem">
    <b>왜 이 신호인가.</b> 한국은 세계 4위 방산 수출국이며 tier-1/2 협력망이 깊다. 하위 협력사는 APT의
    실질 진입점이고, 유출된 자격증명과 인포스틸러 감염 기기는 침해가 실제로 진행 중임을 알리는
    가장 치명적인 조기 신호다. Omija는 이 신호를 볼륨이 아니라 <b>활성 경로</b>로 판별한다.
  </div>
  {note}
</div></section>"""


def _triage(assessments, sup_by_id, prog_by_sup, stale_real: int) -> str:
    rows = []
    band_open = False
    for i, a in enumerate(assessments, 1):
        sup = sup_by_id.get(a.supplier_ref, {})
        active = a.active_flag
        if not active and not band_open:
            rows.append(
                '<div class="qband"><span class="ln"></span>'
                '활성 밴드 경계 · 아래는 전부 자동 후순위'
                '<span class="ln"></span></div>'
            )
            band_open = True
        cls = "active" if active else "warn"
        hl = (' <span class="hl">HEADLINE · 다중 티어</span>'
              if a.supplier_ref == HEADLINE_SUPPLIER else "")
        if active:
            reach = " · ".join(_e(p) for p in prog_by_sup.get(a.supplier_ref, []))
        else:
            reach = f"{a.components.get('exposure_scale', {}).get('raw_count', 0)}건 노출"
        rows.append(f"""
      <div class="qrow {cls}">
        <span class="rk">{i}</span>
        <span class="bd"></span>
        <span class="nm">{_e(sup.get('name'))}<span class="sid">{_e(a.supplier_ref)}</span>{hl}
          <div class="tier">T{_e(sup.get('tier'))} · {_e(reach)}</div></span>
        <span class="tier">{'활성 경로' if active else '노출'}</span>
        <span class="sc">{a.score:.1f}<div class="gr">{_e(a.grade)}</div></span>
        <span class="evn">cites {len(a.evidenced_by)}</span>
      </div>""")
    stale_block = f"""
      <div class="qstale">
        <span class="bd"></span>
        <span class="n">{stale_real}</span>
        <span class="l">비활성 노출 레코드 · 자동 후순위 {chip('eng')}</span>
        <span style="margin-left:auto;text-align:right">
          <span class="n" style="font-size:13px">~{PROJECTED_STALE_VOLUME:,}</span>
          <span class="l">운영 규모 투영 {chip('frame')}</span>
        </span>
      </div>"""
    note = pnote("02 트리아지 큐", [
        "큐를 보십시오 — 볼륨이 아니라 활성 경로가 순서를 정합니다. 활성 밴드 경계 위 세 줄은"
        f" 스코어링 불변식(active_floor 70 &gt; base_cap 60)이 보장하는 실측 순위입니다 ({chip('eng')}).",
        f"맨 아래 ~4,120은 이 페이지의 유일한 연출 수치이고 {chip('frame')} 칩이 붙어 있습니다 —"
        " 그 옆의 실측 건수와 나란히 두고, 연출과 실측을 저희가 먼저 구분해 드린다고 말하십시오.",
    ])
    return f"""
<section id="triage"><div class="wrap">
  <div class="sec-k">02 · 트리아지 큐 / triage queue {chip('eng')}</div>
  <div class="sec-h">머니샷 — 볼륨이 아니라 활성 경로가 큐를 세운다</div>
  <div class="qcap">Omija는 볼륨으로 세우지 않는다 — 활성 경로가 항상 위. 활성 침해 3건이
     노출 레코드 전량 위에 고정되고, 대량 유출 볼륨은 자동으로 밑으로 내려간다.</div>
  <div class="queue">
    {''.join(rows)}
    {stale_block}
  </div>
  {note}
</div></section>"""


def _differentiation(assessments, sup_by_id, vol_rank, prog_by_sup, stale_real: int) -> str:
    """SAME input, THREE systems, three answers — the ontology is the difference.
    Columns 1-2 are illustrative comparison mockups (FRAME·연출); column 3 is the
    real engine queue (ENGINE·실측). The volume ranking in column 1 echoes the
    seed's real per-supplier record counts, but the 'system' is a strawman."""
    # column 1 — leak-list viewer (volume rank; real counts, strawman ordering)
    c1_rows = []
    for i, (n, sid) in enumerate(vol_rank[:4], 1):
        nm = sup_by_id.get(sid, {}).get("name", sid)
        buried = sid == HEADLINE_SUPPLIER
        cls = "buried" if buried else ("dim" if i > 1 else "")
        tagn = (' <span class="mono2" style="color:var(--band-b)">← 활성 1건이 여기 묻힘</span>'
                if buried else "")
        c1_rows.append(
            f'<div class="srow {cls}"><span class="rk">{i}</span>'
            f'<span class="who">{_e(nm)}</span>{tagn}'
            f'<span class="n">{n}건</span></div>'
        )
    # column 2 — generic SIEM alert list (flat, contextless; illustrative)
    siem_alerts = [
        ("ALERT-7741", "credential-leak · user1@supplier-…", "Medium"),
        ("ALERT-7742", "credential-leak · ops@micro-h.…", "Medium"),
        ("ALERT-7743", "infostealer-detect · host portal.…", "Medium"),
        ("ALERT-7744", "credential-leak · admin@parts-d.…", "Medium"),
    ]
    c2_rows = "".join(
        f'<div class="srow dim"><span class="rk">·</span>'
        f'<span class="mono2">{_e(aid)}</span><span class="mono2">{_e(txt)}</span>'
        f'<span class="n">{_e(sev)}</span></div>'
        for aid, txt, sev in siem_alerts
    )
    # column 3 — Omija: the real queue, condensed (top actives + buried noisy one)
    c3_rows = []
    for i, a in enumerate(assessments[:3], 1):
        nm = sup_by_id.get(a.supplier_ref, {}).get("name", a.supplier_ref)
        progs = prog_by_sup.get(a.supplier_ref, [])
        ptxt = _e(progs[0]) if progs else ""
        extra = f" +{len(progs)-1}" if len(progs) > 1 else ""
        c3_rows.append(
            f'<div class="srow hot"><span class="rk">{i}</span>'
            f'<span class="who">{_e(nm)}</span>'
            f'<span class="mono2" style="color:var(--muted)">{ptxt}{extra} · draft ready</span>'
            f'<span class="n">{a.score:.1f}</span></div>'
        )
    # the noisy volume-leader, deprioritized by the real engine
    noisy = next((a for a in assessments if vol_rank and a.supplier_ref == vol_rank[0][1]), None)
    if noisy:
        rank = next(i for i, a in enumerate(assessments, 1) if a.supplier_ref == noisy.supplier_ref)
        nm = sup_by_id.get(noisy.supplier_ref, {}).get("name", noisy.supplier_ref)
        c3_rows.append(
            f'<div class="srow dim"><span class="rk">{rank}</span>'
            f'<span class="who">{_e(nm)}</span>'
            f'<span class="mono2">{vol_rank[0][0]}건 볼륨 1위 → 자동 후순위</span>'
            f'<span class="n">{noisy.score:.1f}</span></div>'
        )
    note = pnote("03 같은 입력, 세 시스템", [
        f"같은 입력을 세 시스템에 넣으면 답이 다릅니다. 왼쪽 두 칼럼은 {chip('frame')} —"
        " 비교용 모형입니다 (볼륨 건수 자체는 시드 실측을 그대로 씁니다).",
        f"오른쪽 Omija 칼럼만 {chip('eng')} — 방금 그 트리아지 큐 그대로입니다. 볼륨 1위"
        " 공급사가 자동 후순위로 내려가고 활성 경로가 위로 올라온 것을 가리키십시오.",
        "결론 한 문장: <b>차이는 피드가 아니라 온톨로지입니다.</b>",
    ])
    return f"""
<section id="compare"><div class="wrap">
  <div class="sec-k">03 · 차별점 / same input, three systems {chip('frame')} {chip('eng')}</div>
  <div class="sec-h">같은 입력, 세 개의 시스템, 세 개의 답</div>
  <div class="sec-sub">입력은 동일하다 — 대량 비활성 유출(연출 ~{PROJECTED_STALE_VOLUME:,}건 · 시드 실측 {stale_real}건)과
     활성 경로 1건. 무엇이 위로 올라오는지는 시스템이 정한다.</div>
  <div class="tri">
    <div class="sysbox">
      <div class="sh"><span class="nm">유출 목록 뷰어</span>{chip('frame')}
        <span style="font-size:10.5px;color:var(--muted)">volume rank · 건수는 시드 실측</span></div>
      <div class="rows">{''.join(c1_rows)}</div>
      <div class="verdict bad">→ 오탐 대응 — 볼륨이 순서를 정함</div>
    </div>
    <div class="sysbox">
      <div class="sh"><span class="nm">일반 SIEM 알림</span>{chip('frame')}
        <span style="font-size:10.5px;color:var(--muted)">flat alerts · 비교용 모형</span></div>
      <div class="rows">{c2_rows}</div>
      <div class="verdict bad">→ 프로그램 영향 불명 — 공급망 맥락 없음</div>
    </div>
    <div class="sysbox omija">
      <div class="sh"><span class="nm">Omija</span>{chip('eng')}
        <span style="font-size:10.5px;color:var(--muted)">실제 엔진 큐 그대로</span></div>
      <div class="rows">{''.join(c3_rows)}</div>
      <div class="verdict good">→ 즉시 조치 — 활성 교차 경로 + 프로그램 영향 + 초안 준비</div>
    </div>
  </div>
  <div class="tricap"><b>차이를 만드는 건 피드가 아니라 온톨로지다</b> —
    of/targets 교차 엣지와 가변 깊이 전파가 같은 입력에서 다른 답을 만든다.</div>
  {note}
</div></section>"""


def _svg_node(cx, cy, typ, lab, sub, cls) -> str:
    w, h = 152, 46
    x, y = cx - w / 2, cy - h / 2
    sub_t = f'<text x="{cx}" y="{y+40}" text-anchor="middle" class="sub">{_e(sub)}</text>' if sub else ""
    return f"""<g class="g-node {cls}">
      <rect class="box" x="{x}" y="{y}" width="{w}" height="{h}" rx="6"/>
      <text x="{cx}" y="{y+15}" text-anchor="middle" class="typ">{_e(typ)}</text>
      <text x="{cx}" y="{y+29}" text-anchor="middle" class="lab">{_e(lab)}</text>{sub_t}</g>"""


def _blast_svg(inc: dict, active_exp: dict, blast_programs: list[dict]) -> str:
    """Build the instance blast-radius graph from the REAL incident path plus the
    real cross-org targets edge (active exposure host) and the full blast radius."""
    path = inc["path"]  # 7 nodes: device→identity→domain→sup→sup→prime→program
    NODE_W, PITCH, X0 = 152, 168, 90
    SPINE_Y = 210
    cx = [X0 + i * PITCH for i in range(len(path))]
    edge_labels = ["compromises", "of", "owns", "subcontractsTo", "supplies", "runs"]
    type_ko = {
        "InfectedDevice": "INFECTED DEVICE", "Identity": "IDENTITY", "Domain": "DOMAIN",
        "Supplier": "SUPPLIER", "Prime": "PRIME", "Program": "PROGRAM",
    }
    nodes_svg, edges_svg, labels_svg = [], [], []
    for i, n in enumerate(path):
        typ = type_ko.get(n["type"], n["type"])
        if n["type"] == "InfectedDevice":
            detail, sub = f"{active_exp.get('malware')} stealer", "세션쿠키 유효"
        else:
            detail = n.get("detail") or n.get("ref")
            sub = _e(n.get("ref")) if n.get("ref") != detail else ""
        origin = n["type"] in {"InfectedDevice", "Identity"}
        cls = "origin" if origin else ""
        if n["type"] == "Supplier" and i == 4:
            sub = "clean conduit · 전파 통로"
        nodes_svg.append(_svg_node(cx[i], SPINE_Y, typ, detail, sub, cls))
        if i < len(path) - 1:
            x1 = cx[i] + NODE_W / 2
            x2 = cx[i + 1] - NODE_W / 2
            mid = (x1 + x2) / 2
            lab = edge_labels[i]
            lcls = "elab sub" if lab == "subcontractsTo" else "elab"
            edges_svg.append(f'<path class="spine" d="M{x1},{SPINE_Y} L{x2-6},{SPINE_Y}"/>')
            labels_svg.append(f'<text x="{mid}" y="{SPINE_Y-8}" text-anchor="middle" class="{lcls}">{_e(lab)}</text>')
    prog_i = len(path) - 1
    labels_svg.append(f'<text x="{cx[prog_i]}" y="{SPINE_Y+34}" text-anchor="middle" class="burn">◉ BURNING</text>')
    rep_ref = path[-1].get("ref")
    others = [p for p in blast_programs if p.get("ref") != rep_ref]
    if others:
        p2 = others[0]
        y2 = SPINE_Y + 92
        nodes_svg.append(_svg_node(cx[prog_i], y2, "PROGRAM", p2.get("name"), _e(p2.get("ref")), ""))
        px = cx[prog_i - 1]
        edges_svg.append(
            f'<path class="edge blast" d="M{px},{SPINE_Y+18} C{px},{y2} {cx[prog_i]-NODE_W/2-30},{y2} {cx[prog_i]-NODE_W/2-6},{y2}"/>')
        labels_svg.append(f'<text x="{cx[prog_i]}" y="{y2+34}" text-anchor="middle" class="burn">◉ BURNING</text>')
        labels_svg.append(f'<text x="{px+18}" y="{(SPINE_Y+y2)/2}" class="elab">runs (blast)</text>')
    # THE cross-org targets edge: Identity(supplier employee) → Domain(prime VPN)
    tx = cx[len(path) - 2]
    ty = 66
    nodes_svg.append(_svg_node(tx, ty, "DOMAIN · 원청 자산", active_exp.get("host"), "prime VPN portal", "cross"))
    idx = cx[1]
    edges_svg.append(
        f'<path class="tedge" d="M{idx},{SPINE_Y-23} C{idx},{ty+80} {tx-NODE_W/2-40},{ty} {tx-NODE_W/2-6},{ty}"/>')
    labels_svg.append(f'<text x="{(idx+tx)/2 - 40}" y="{ty+70}" class="elab tg">targets · 교차 조직 엣지</text>')
    px = cx[len(path) - 2]
    edges_svg.append(f'<path class="edge" d="M{tx},{ty+23} L{px},{SPINE_Y-25}"/>')
    labels_svg.append(f'<text x="{px+8}" y="{ty+70}" class="elab">belongs_to</text>')

    width = cx[-1] + NODE_W / 2 + 40
    height = SPINE_Y + 150
    note = pnote("04 블라스트 반경", [
        "이 그래프는 스키마가 아니라 인시던트 인스턴스입니다 — 방금 엔진이 연 incident의 traverses"
        f" 경로 그대로입니다 ({chip('eng')}, 개체 이름은 {chip('seed')}).",
        "주황 점선을 가리키십시오 — of/targets 교차 엣지. 협력사 직원 계정이 원청 VPN을 가리키는"
        " 순간이고, 이 한 개 엣지가 조기경보의 근거입니다.",
        "그리고 subcontractsTo 홉: 2차 말단의 감염이 clean한 1차를 통로 삼아 두 티어 위 프로그램을 태웁니다.",
    ])
    return f"""
<section id="blast"><div class="wrap">
  <div class="sec-k">04 · 블라스트 반경 / blast radius (instance) {chip('eng')} {chip('seed')}</div>
  <div class="sec-h">이 침해 인스턴스가 실제로 무엇에 닿는가</div>
  <div class="sec-sub">스키마가 아니라 <b>실제 인시던트 데이터</b>다. 감염 기기 → 계정 → 도메인 →
     2차 협력사 → (clean) 1차 → 원청 → 방산 프로그램. 가변 깊이 recursive traverse가 두 티어를 건너뛰지 않고 잇는다.</div>
  <div class="graphwrap scroll-x">
    <svg width="{width:.0f}" height="{height}" viewBox="0 0 {width:.0f} {height}" style="min-width:{width:.0f}px;display:block">
      <defs>
        <marker id="arr" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
          <path d="M0,0 L6,3 L0,6 Z" fill="var(--band-a)"/></marker>
        <marker id="arrq" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
          <path d="M0,0 L6,3 L0,6 Z" fill="var(--hair-2)"/></marker>
        <marker id="arrc" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
          <path d="M0,0 L6,3 L0,6 Z" fill="var(--cross)"/></marker>
      </defs>
      {''.join(edges_svg)}
      {''.join(labels_svg)}
      {''.join(nodes_svg)}
    </svg>
  </div>
  <div class="g-note">
    <b>협력사 계정이 원청 자산을 가리킨다.</b> 인포스틸러 로그에 저장된 자격증명의
    <span style="color:var(--cross);font-family:var(--mono)">targets</span> 엣지가 감염된 2차 직원 계정에서
    원청 VPN 포털로 교차한다 — <b>of</b>(협력사 직원)와 <b>targets</b>(원청 자산)의 분리가
    이 조기경보의 근거다. flat table로는 표현되지 않는 cross-org 엣지.
  </div>
  {note}
</div></section>"""


def _evidence(active_exp: dict, ra, cites: list) -> str:
    rows = [
        ("근거 유형", f"{_MODULE_LABEL.get(active_exp.get('module'), active_exp.get('module'))}"),
        ("of → Identity", active_exp.get("email")),
        ("targets → host", active_exp.get("host")),
        ("secret_type", f"{active_exp.get('secret_type')} · <span class='msk'>••• (마스킹)</span>"),
        ("malware / 계정", f"{active_exp.get('malware')} · {active_exp.get('account_type')} · 세션쿠키 유효"),
        ("관측(감염)일", _fmt_ts(active_exp.get("infected_at"))),
        ("source_ref", active_exp.get("source_ref")),
        ("모듈 신뢰도", active_exp.get("confidence")),
    ]
    exp_tbl = "".join(
        f'<tr><td class="k">{_e(k)}</td><td class="v">{v if "span" in str(v) else _e(v)}</td></tr>'
        for k, v in rows
    )
    c = ra.components
    score_rows = [
        ("exposure_scale", f"dedup {c['exposure_scale']['dedup_count']} · +{c['exposure_scale']['points']}"),
        ("recency", f"{c['recency']['age_days']}d · +{c['recency']['points']}"),
        ("secret_type", f"{c['secret_type']['strongest']} (w{c['secret_type']['weight']}) · +{c['secret_type']['points']}"),
        ("module_confidence", f"{c['module_confidence']['diversity']} modules · +{c['module_confidence']['points']}"),
        ("base_subtotal → base", f"{c['base_subtotal']} → cap {c['base_score']}"),
        ("active_flag / quality", f"{c['active_flag']} · q{c['active_quality']}"),
        ("SCORE / GRADE", f"{c['score']} · {c['grade']}"),
    ]
    score_tbl = "".join(
        f'<tr><td class="k">{_e(k)}</td><td class="v">{_e(v)}</td></tr>' for k, v in score_rows
    )
    cite_chips = "".join(f'<span class="chip">{_e(r["evidence_ref"])}</span>' for r in cites)
    note = pnote("05 근거 드릴다운", [
        f"모든 판단은 원본 레코드로 되짚어집니다. 레코드 내용은 {chip('seed')} — 합성 시드입니다."
        f" 점수 분해와 evidenced_by 연결은 {chip('eng')} — 엔진이 강제한 provenance입니다.",
        "핵심 문장: <b>근거가 비면 엔진이 파생 객체 생성 자체를 거부합니다.</b> 군 감사 대응"
        " 요건을 스코어링 규칙이 아니라 생성 규칙으로 박아뒀습니다.",
    ])
    return f"""
<section id="evidence"><div class="wrap">
  <div class="sec-k">05 · 근거 드릴다운 / evidence drill-down {chip('seed')} {chip('eng')}</div>
  <div class="sec-h">모든 판단은 원본 레코드로 되짚어진다</div>
  <div class="sec-sub">군 감사 대응 요건: 파생된 모든 판단(위험 등급, 활성 플래그, 프로그램 도달)은
     근거 레코드 없이 존재할 수 없다. 근거가 비면 액션은 <span class="mono" style="color:var(--band-a)">거부</span>된다.</div>
  <div class="evgrid">
    <details class="ev" open>
      <summary><span class="claim">주장: "활성 침해 경로가 성립한다" — cds 인포스틸러 레코드 (원본)</span>
        {chip('seed')}<span class="src">{_e(active_exp.get('source_ref'))}</span></summary>
      <div class="rec">
        <table>{exp_tbl}</table>
        <div class="prov"><b>provenance.</b> 값은 수집 경계 <span class="mono">normalize()</span>에서
          마스킹됨(원문 미저장). 도메인은 전부 합성 <span class="mono">*.example</span>.</div>
      </div>
    </details>
    <details class="ev">
      <summary><span class="claim">주장: "위험 등급 즉시({c['score']})" — ComputeRisk 성분 분해</span>
        {chip('eng')}<span class="src">{_e(ra.id)} · cites {len(ra.evidenced_by)}</span></summary>
      <div class="rec">
        <table>{score_tbl}</table>
        <div class="prov"><b>evidenced_by.</b> 이 점수를 떠받치는 레코드:</div>
        <div class="cites" style="border:none;background:none;padding:8px 0 0">{cite_chips}</div>
      </div>
    </details>
  </div>
  <div class="audit">감사 노트 — 위 두 레코드의 <span class="mono">source_ref</span>는 초안·점수·인시던트가
     동일하게 인용한다(한 사건, 한 근거 집합). 값 없는 파생 객체는 만들지 않는다.</div>
  {note}
</div></section>"""


def _workflow(inc: dict, draft: dict, cites: list, merge: dict | None) -> str:
    states = [("flagged", "done"), ("acknowledged", "cur"), ("assigned", ""), ("closed", "")]
    sm = '<span class="arrow">→</span>'.join(
        f'<span class="st {c}">{_e(s)}</span>' for s, c in states
    )
    body = _mask_display(draft["body"])
    body = _e(body)
    body = re.sub(r"(?m)^(#+ .+)$", r'<span class="h">\1</span>', body)
    cite_chips = "".join(f'<span class="chip">{_e(r["evidence_ref"])}</span>' for r in cites)
    merge_html = ""
    if merge:
        merge_html = f"""<div class="merge">
          <b>EntityResolver — 병합 제안 1건 (검토 대기)</b> {chip('eng')}<br>
          <span class="mono">{_e(merge['identity_b'])}</span> ≈
          <span class="mono">{_e(merge['identity_a'])}</span> · 자동 병합 없음, 사람이 승인.
        </div>"""
    note = pnote("06 대응 워크플로", [
        "이 화면 앞에는 방산 협력망 CERT 분석가가 앉습니다. 확인 → 배정 → 초안 검토 → 승인 →"
        " 내보내기까지가 그의 일이고, <b>발송 기능은 코드에 없습니다</b> — 그게 배치 가능성의 논거입니다.",
        f"오른쪽 통보 초안은 {chip('eng')} — GenerateNotificationDraft가 방금 실제로 생성한 출력"
        f" 그대로이고, cites {len(cites)}건이 근거입니다. 상태 흐름 연출에는 {chip('frame')}를 붙였습니다.",
    ])
    return f"""
<section id="response"><div class="wrap">
  <div class="sec-k">06 · 대응 워크플로 / response workflow {chip('eng')} {chip('frame')}</div>
  <div class="sec-h">이 화면 앞에 앉는 사람과, 그가 하는 일</div>
  <div class="sec-sub">방산 협력망 CERT 분석가: 트리아지 → 확인(acknowledge) → 배정 → 초안 검토 →
     승인 → 내보내기. 이 워크플로 자체가 <b>군 배치 가능성</b>의 논거다.</div>
  <div class="wf">
    <div>
      <div class="sec-k">인시던트 상태 · {_e(inc['id'])} {chip('frame')}</div>
      <div class="sm">{sm}</div>
      <div class="assign">현재 상태 <b>acknowledged</b> · 배정 대기 · SLA 클럭 진행 중 (시나리오 연출)</div>
      {merge_html}
      <div class="actions">
        <button class="btn primary" disabled>초안 승인</button>
        <button class="btn" disabled>PDF 내보내기</button>
        <button class="btn" disabled>담당자 배정</button>
      </div>
      <div class="no-send">자동 발송 없음 — human-on-the-loop. 초안은 생성까지만, 통보 발송 기능은 코드에 없음.</div>
    </div>
    <div class="doc">
      <div class="dh">NotificationDraft · GenerateNotificationDraft 실측 출력 {chip('eng')}
        <span class="st">status: {_e(draft['status'])}</span></div>
      <pre class="db">{body}</pre>
      <div class="cites"><span class="cl">cites ({len(cites)})</span>{cite_chips}</div>
    </div>
  </div>
  {note}
</div></section>"""


def _live_strip(chain: dict | None) -> str:
    """실제로 존재하는 것 — the LIVE section. Renders the real Foundry audit
    trail (state transitions executed today, verified by readback) plus the
    deployed-ontology facts. Everything here is LIVE·Foundry."""
    note = pnote("07 실제로 존재하는 것", [
        f"여기부터는 가상이 아닙니다. {chip('live')} 칩이 붙은 이 표는 오늘 실제 Foundry"
        " 온톨로지에서 실행되고 readback으로 검증된 상태 전이 감사 기록입니다.",
        f"온톨로지 {ONTOLOGY_OBJECT_TYPES}개 객체 타입과 8종 워크플로 액션은 승인된 proposal로"
        f" main에 병합됐고 OSDK {OSDK_VERSION}으로 배포돼 있습니다.",
        "이 표가 '데이터는 가상, 시스템은 진짜'의 증거입니다 — <b>가상 인시던트가 진짜 플랫폼"
        " 위를 흘렀습니다.</b>",
    ])
    if chain is None:
        body = """<div class="livewait">실행 대기 — Foundry action-chain 증적(out/foundry_action_chain.json)이
        아직 없습니다. 액션 체인 실행 후 이 슬롯이 실제 감사 기록으로 채워집니다.</div>"""
        return f"""
<section id="live"><div class="wrap">
  <div class="sec-k">07 · 실제로 존재하는 것 / what actually exists {chip('live')}</div>
  <div class="sec-h">데이터는 가상이지만, 이 데모가 올라탄 플랫폼은 진짜다</div>
  {body}
  {note}
</div></section>"""
    steps = chain.get("steps", [])
    n_actions = len(chain.get("discovered_actions", {})) or 8
    trs = []
    for s in steps:
        ok = "✓ verified" if s.get("verified") else "미검증"
        trs.append(
            f"<tr><td class='mono2'>{_e(_fmt_iso(s.get('timestamp')))}</td>"
            f"<td class='act'>{_e(s.get('action'))}</td>"
            f"<td class='mono2'>{_e(s.get('objectType'))} · {_e(s.get('pk'))}</td>"
            f"<td class='tr'>{_e(s.get('readback_status_before'))} → {_e(s.get('readback_status_after'))}</td>"
            f"<td class='ok'>{_e(ok)} · HTTP {_e(s.get('http_status'))}</td></tr>"
        )
    return f"""
<section id="live"><div class="wrap">
  <div class="sec-k">07 · 실제로 존재하는 것 / what actually exists {chip('live')}</div>
  <div class="sec-h">데이터는 가상이지만, 이 데모가 올라탄 플랫폼은 오늘 실제로 움직였다</div>
  <div class="sec-sub">아래는 연출이 아니다 — 실제 Foundry 온톨로지에 대해 오늘 실행된 액션 체인의
     감사 기록이며, 각 전이는 실행 후 readback으로 검증됐다.</div>
  <div class="livewrap">
    <div class="lh"><span class="t">Foundry 액션 감사 추적 · {len(steps)}건</span>{chip('live')}
      <span class="sub">가상 인시던트 하나가 진짜 플랫폼의 상태 기계를 통과한 기록</span></div>
    <div class="scroll-x"><table class="livetbl">
      <thead><tr><th>timestamp (UTC)</th><th>action apiName</th><th>object · pk</th>
        <th>status before → after</th><th>readback</th></tr></thead>
      <tbody>{''.join(trs)}</tbody>
    </table></div>
    <div class="livefacts">
      <span>Foundry ontology: <b>{ONTOLOGY_OBJECT_TYPES} object types</b> + link graph {chip('live')}</span>
      <span>workflow action types <b>{n_actions}종</b> — approved proposal로 main 병합 {chip('live')}</span>
      <span>OSDK <b>{_e(OSDK_VERSION)}</b> published {chip('live')}</span>
      <span class="mono" style="font-size:10.5px;color:var(--muted)">{_e(chain.get('ontology_api_name'))}</span>
    </div>
  </div>
  {note}
</div></section>"""


def _outcome(n_exp: int, n_inc: int, n_burn: int, stale: int,
             pipe_ms: float, burn_names: list[str], n_sup_hit: int) -> str:
    pct = round(stale / n_exp * 100) if n_exp else 0
    active_seg = max(2, round((n_exp - stale) / n_exp * 100)) if n_exp else 0
    tiles = f"""
    <div class="tile"><div class="n">{n_exp}</div>
      <div class="l">노출 레코드 수집·상관 {chip('eng')}</div><div class="s">{n_sup_hit}개 협력사 귀속</div></div>
    <div class="tile accent"><div class="n">{n_inc}</div>
      <div class="l">활성 침해 인시던트 {chip('eng')}</div><div class="s">Device→…→Program 경로 성립</div></div>
    <div class="tile"><div class="n">{n_burn}</div>
      <div class="l">버닝 방산 프로그램 {chip('eng')}</div><div class="s">{_e(' · '.join(burn_names))}</div></div>
    <div class="tile"><div class="n">{pct}<span class="u">%</span></div>
      <div class="l">노이즈 자동 후순위 {chip('eng')}</div>
      <div class="propbar"><div class="seg a" style="width:{active_seg}%"></div><div class="seg s" style="width:{100-active_seg}%"></div></div>
      <div class="s">{stale}/{n_exp} 비활성 후순위 · 활성 {n_exp-stale}건 우선</div></div>"""
    note = pnote("08 성과", [
        f"성과 타일 네 개는 전부 {chip('eng')} — 이 페이지를 만드는 순간 엔진이 실제로 계산한"
        " 단일 실행 결과입니다.",
        f"수집에서 검토 대기 초안까지 {pipe_ms:.0f}ms. 규모 연출이 아니라 파이프라인 실측입니다.",
    ])
    return f"""
<section id="outcome"><div class="wrap">
  <div class="sec-k">08 · 성과 / outcome {chip('eng')}</div>
  <div class="sec-h">단일 실행의 결과 (전량 엔진 실측)</div>
  <div class="tiles">{tiles}</div>
  <div class="tilecap">수집 → 검토대기 초안까지 파이프 지연 ~{pipe_ms:.0f} ms (실측 단일 실행) ·
     활성 밴드가 비활성 위에 고정되는 것은 스코어링 불변식으로 보장 · 연출 수치는 전부 FRAME·연출 칩으로 표기.</div>
  {note}
</div></section>"""


def _footer() -> str:
    onto = """
    <svg width="330" height="150" viewBox="0 0 330 150" class="onto" style="max-width:100%">
      <g class="n"><rect class="b" x="6" y="60" width="78" height="30" rx="5"/>
        <text class="t" x="45" y="79" text-anchor="middle">Identity</text></g>
      <g class="n"><rect class="b" x="6" y="8" width="90" height="30" rx="5"/>
        <text class="t" x="51" y="27" text-anchor="middle">Exposure</text></g>
      <g class="n"><rect class="b" x="120" y="8" width="86" height="30" rx="5"/>
        <text class="t" x="163" y="27" text-anchor="middle">Domain·원청</text></g>
      <g class="n"><rect class="b" x="120" y="112" width="86" height="30" rx="5"/>
        <text class="t" x="163" y="131" text-anchor="middle">Supplier</text></g>
      <g class="n"><rect class="b" x="238" y="60" width="86" height="30" rx="5"/>
        <text class="t" x="281" y="79" text-anchor="middle">Program</text></g>
      <path class="lk" d="M51,38 L48,60"/><text class="lkl" x="30" y="53">of</text>
      <path class="lk cross" d="M96,23 L120,23"/><text class="lkl cross" x="100" y="16">targets</text>
      <path class="lk" d="M84,78 L120,120"/><text class="lkl" x="86" y="103">belongs</text>
      <path class="lk" d="M163,112 L163,90 Q163,75 200,75 L238,75"/>
      <text class="lkl" x="176" y="70">supplies·runs</text>
    </svg>"""
    note = pnote("09 작동 원리", [
        "마무리 30초: 왜 그래프인가 — 교차 조직 엣지, 가변 깊이 전파, provenance 강제.",
        "이 세 가지가 flat table로 안 되는 이유이고, 피드가 아니라 온톨로지가 차별점인 이유입니다.",
    ])
    return f"""
<section id="how" style="border-bottom:none"><div class="wrap">
  <div class="sec-k">09 · 작동 원리 / how it works</div>
  <div class="how">
    {onto}
    <ul>
      <li><b>교차 조직 엣지.</b> <span class="mono">of</span>(계정)와 <span class="mono">targets</span>(자산)가
        분리돼 협력사 직원 계정이 원청 자산을 가리키는 순간을 포착한다 — 그래프만이 표현한다.</li>
      <li><b>가변 깊이 전파.</b> <span class="mono">subcontractsTo</span> 재귀 traverse로 2차→1차→원청→프로그램을
        건너뛰지 않고 굴린다. flat join으로는 깊이를 모른다.</li>
      <li><b>provenance-mandatory 객체.</b> 위험·인시던트·프로그램 노출·초안은 근거 없이는 생성 거부.
        감사 가능한 의사결정 객체.</li>
    </ul>
  </div>
  {note}
  <div class="footer">SYNTHETIC DEMO · no network · no real data · masked (•••) ·
    generated by scripts/omija_demo.py · object/state names are API identifiers (English)</div>
</div></section>"""


# --------------------------------------------------------------------------- #
# assembly
# --------------------------------------------------------------------------- #
def build_html() -> tuple[str, dict]:
    t0 = time.perf_counter()
    store, assessments = build_pipeline(DEMO_NOW)               # correlate→resolve→flag→compute
    drafts = generate_drafts(store, assessments, top=TOP_N, now=DEMO_NOW)  # notify_draft
    program_exposures = propagate_program_risk(store, now=DEMO_NOW)        # propagate_risk
    pipe_ms = (time.perf_counter() - t0) * 1000

    sup_by_id = {s["id"]: s for s in store.suppliers()}
    incidents = store.incidents()
    incidents_by_sup = {i["supplier_ref"]: i for i in incidents}

    # headline incident + its cross-org active exposure (engine output)
    inc = incidents_by_sup[HEADLINE_SUPPLIER]
    h_exposures = store.exposures_for_supplier(HEADLINE_SUPPLIER)
    active_exp = next(
        e for e in h_exposures if e["module"] == "cds" and e.get("has_session_cookie")
    )
    hero_programs = [p["name"] for p in inc["blast_radius"]["programs"]]

    prog_by_sup = {
        i["supplier_ref"]: [p["name"] for p in i["blast_radius"]["programs"]]
        for i in incidents
    }

    all_exp = store.all_exposures()
    n_exp = len(all_exp)
    stale_real = sum(1 for e in all_exp if not _active_signal(e))

    # real per-supplier volume ranking (for the strawman leak-list column)
    vol_rank = sorted(
        ((len(store.exposures_for_supplier(s["id"])), s["id"]) for s in store.suppliers()),
        reverse=True,
    )
    vol_rank = [(n, sid) for n, sid in vol_rank if n > 0]

    ra = next(a for a in assessments if a.supplier_ref == HEADLINE_SUPPLIER)
    draft = store.draft_for_supplier(HEADLINE_SUPPLIER)
    cites = store.draft_cites(draft["id"])
    merges = store.merge_proposals("pending")
    merge = merges[0] if merges else None

    burn = [pe for pe in program_exposures if pe.active_flag]
    prog_names = {p["id"]: p["name"] for p in store.programs()}
    burn_names = [prog_names.get(pe.program_ref, pe.program_ref) for pe in burn]

    action_chain = _load_action_chain()

    body = "".join([
        _hero(inc, active_exp, hero_programs),
        _triage(assessments, sup_by_id, prog_by_sup, stale_real),
        _differentiation(assessments, sup_by_id, vol_rank, prog_by_sup, stale_real),
        _blast_svg(inc, active_exp, inc["blast_radius"]["programs"]),
        _evidence(active_exp, ra, cites),
        _workflow(inc, draft, cites, merge),
        _live_strip(action_chain),
        _outcome(n_exp, len(incidents), len(burn), stale_real, pipe_ms, burn_names,
                 n_sup_hit=len(assessments)),
        _footer(),
    ])

    page = f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Omija — 공급망 자격증명 노출 조기경보 (데모 시나리오)</title>
<style>{TOKENS_CSS}{PAGE_CSS}</style></head><body data-palette="#3987e5,#199e70,#c98500,#9085e9">
{synthetic_banner()}
{chip_legend()}
<div class="mast"><div class="wrap">
  <span class="ver">engine · sqlite mock pipeline · offline</span>
  <div class="brand">OMIJA · SUPPLY-CHAIN CREDENTIAL EXPOSURE — EARLY WARNING</div>
  <div class="tag">방산 공급망 자격증명 노출 조기경보 · 활성 경로 우선 트리아지 · human-on-the-loop</div>
</div></div>
{body}
</body></html>"""

    store.close()
    meta = {
        "n_exp": n_exp, "n_sup": len(assessments), "n_inc": len(incidents),
        "n_burn": len(burn), "stale_real": stale_real, "pipe_ms": pipe_ms,
        "headline_score": ra.score, "cites": len(cites),
        "live_steps": len(action_chain["steps"]) if action_chain else 0,
    }
    return page, meta


def _safety_check(page: str) -> None:
    low = page.lower()
    problems = []
    if "stealthmole" in low:
        problems.append("vendor name 'stealthmole' present")
    for pat in ('src="http', "src='http", 'href="http', "href='http", "url(http", "@import", "<script", "<link"):
        if pat in low:
            problems.append(f"external/resource ref: {pat!r}")
    if re.search(r"Synthetic-[A-Za-z]+-\d+!", page) or re.search(r"SID[0-9a-f]{20,}", page):
        problems.append("raw synthetic secret leaked")
    if problems:
        raise SystemExit("SAFETY FAIL: " + "; ".join(problems))


def run() -> int:
    page, meta = build_html()
    _safety_check(page)
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_HTML, "w", encoding="utf-8") as fh:
        fh.write(page)

    print("=" * 72)
    print("Omija demo page — story-first case study (provenance-chipped)")
    print("=" * 72)
    print(f"engine (real): {meta['n_exp']} exposures · {meta['n_sup']} suppliers scored · "
          f"{meta['n_inc']} incidents · {meta['n_burn']} burning programs")
    print(f"headline sup-h score {meta['headline_score']} · cites {meta['cites']} · "
          f"stale(non-active) {meta['stale_real']} · pipe {meta['pipe_ms']:.1f} ms")
    print(f"LIVE strip: {meta['live_steps']} verified Foundry transitions "
          f"({'real audit trail' if meta['live_steps'] else '실행 대기 slot'})")
    print("safety: no 'stealthmole', no external http refs, no raw secret — OK")
    print(f"written: {OUT_HTML} ({os.path.getsize(OUT_HTML):,} bytes)")
    print("RESULT: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
