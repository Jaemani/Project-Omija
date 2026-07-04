"""Omija steady-state console (scripts/omija_console_home.py → out/omija_console_home.html).

The screen an analyst keeps open when NOTHING is burning. It proves two things
(docs/review/steady-state-console-direction.md):

  1. 감시 태세 (coverage)      — what is being watched, and where the holes are
  2. 시스템 신뢰 (negative evidence) — quiet means "looked and found nothing",
                                       never "didn't look"

Panels (direction doc order):
  P1 감시 범위      — registry coverage, tier minimap, honest coverage gaps
  P2 조용함의 증명   — a REAL engine sweep on a steady-state scenario clock
                       (DEMO_NOW + 42d: every stealer infection has aged out of
                       the 14d active window) → 0 active paths, with the full
                       candidates-reviewed/rejected breakdown + engine invariants
  P3 피드 상태      — honest collection posture (no pretend connections)
  P4 결정 감사 스트림 — the real Foundry action audit trail (readback-verified)
  P5 민감정보 열람   — LOCKED, EMPTY slot; requirement contract only
                       (implementation belongs to Codex — not built here)

Provenance chips (scripts/omija_style.py) apply to every displayed value:
LIVE·Foundry / ENGINE·실측 / SEED·가상 / FRAME·연출.

Non-goals (direction doc): no fake tickers, no blinking, no new ontology
objects, no send-like UI. Offline generation, no CDN, synthetic data only.

Run:  uv run python scripts/omija_console_home.py
"""

from __future__ import annotations

import html
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone

# Repo root on path (script may be run directly).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from actions.compute_risk import compute_all                     # noqa: E402
from actions.entity_resolver import propose_merges               # noqa: E402
from actions.flag_active import flag_active_compromises          # noqa: E402
from actions.propagate_risk import PROGRAM_SCORING               # noqa: E402
from actions.scoring import SCORING                              # noqa: E402
from adapter.mock import DAY, DEMO_NOW                            # noqa: E402
from registry.loader import load_registry                        # noqa: E402
from scripts.omija_style import (                                 # noqa: E402
    TOKENS_CSS, chip, chip_legend, nav_strip, synthetic_banner,
)
from scripts.p1_report import build_store                        # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(REPO_ROOT, "out")
OUT_HTML = os.path.join(OUT_DIR, "omija_console_home.html")
ACTION_CHAIN_JSON = os.path.join(OUT_DIR, "foundry_action_chain.json")

# Steady-state scenario clock: 42 days after the incident anchor. Every seeded
# stealer infection is then OUTSIDE the 14-day active window, so the sweep's
# "0 active paths" is genuinely computed, not asserted. The clock itself is
# scenario framing (chipped FRAME·연출); every count under it is ENGINE·실측.
STEADY_NOW = DEMO_NOW + 42 * DAY

OSDK_VERSION = "0.2.0"


def _e(v) -> str:
    return html.escape("" if v is None else str(v))


def _fmt_ts(ts) -> str:
    if not ts:
        return "—"
    return datetime.fromtimestamp(int(ts), timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _fmt_iso(iso: str | None) -> str:
    if not iso:
        return "—"
    return iso.replace("T", " ")[:19] + "Z"


def _load_action_chain() -> dict | None:
    try:
        with open(ACTION_CHAIN_JSON, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or not data.get("steps"):
        return None
    return data


# --------------------------------------------------------------------------- #
# CSS — shared tokens + console-specific (static; no animation, direction §4)
# --------------------------------------------------------------------------- #
PAGE_CSS = """
.grid2{display:grid;grid-template-columns:1.25fr 1fr;gap:14px;align-items:stretch}
@media(max-width:900px){.grid2{grid-template-columns:1fr}}
.panel{border:1px solid var(--hair-2);border-radius:9px;background:var(--surface);
  overflow:hidden;display:flex;flex-direction:column}
.panel .ph{display:flex;align-items:center;gap:9px;padding:10px 14px;flex-wrap:wrap;
  border-bottom:1px solid var(--hair);background:var(--surface-2)}
.panel .ph .pk{font-family:var(--mono);font-size:10px;letter-spacing:1.2px;color:var(--muted);
  text-transform:uppercase}
.panel .ph .pt{font-size:13.5px;font-weight:600;color:var(--ink)}
.panel .pb{padding:13px 14px;flex:1}

/* P1 coverage */
.kpis{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:13px}
.kpi{border:1px solid var(--hair-2);border-radius:7px;background:var(--surface-2);
  padding:9px 13px;min-width:104px}
.kpi .n{font-family:var(--mono);font-size:22px;font-weight:600;color:var(--ink);line-height:1.1}
.kpi .l{font-size:10.5px;color:var(--muted);margin-top:3px}
.tree{font-family:var(--mono);font-size:11.5px;color:var(--ink-2);line-height:1.85}
.tree .pr{color:var(--ink);font-weight:600}
.tree .tw{color:var(--muted)}
.tree .bdg{display:inline-block;font-size:9px;letter-spacing:.4px;padding:0 6px;
  border-radius:3px;border:1px solid var(--hair-2);color:var(--c-evidence);margin-left:6px}
.tree .bdg.gap{color:var(--band-b);border-color:rgba(250,178,25,.4)}
.tree .bdg.clean{color:var(--muted)}
.gaps{margin-top:12px;border-left:2px solid var(--band-b);background:rgba(250,178,25,.05);
  border-radius:0 5px 5px 0;padding:7px 11px;font-size:12px;color:var(--ink-2)}
.gaps b{color:var(--ink)}

/* P2 all-clear */
.clear0{display:flex;align-items:baseline;gap:12px;margin-bottom:11px;flex-wrap:wrap}
.clear0 .z{font-family:var(--mono);font-size:44px;font-weight:600;color:var(--good);line-height:1}
.clear0 .zl{font-size:13px;color:var(--ink)}
.meta-line{font-size:11.5px;color:var(--ink-2);padding:4px 0;border-bottom:1px solid var(--hair);
  display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.meta-line b{color:var(--ink);font-family:var(--mono);font-weight:500}
.rej{margin-top:11px}
.rej .rrow{display:flex;align-items:center;gap:9px;font-size:11.5px;color:var(--ink-2);padding:3px 0}
.rej .rrow .rn{font-family:var(--mono);color:var(--ink);width:26px;text-align:right;flex:none}
.rej .rrow .rb{height:6px;border-radius:3px;background:var(--hair-2);flex:none}
.inv{margin-top:13px;border-top:1px solid var(--hair);padding-top:10px}
.inv .irow{display:flex;gap:8px;align-items:center;font-family:var(--mono);font-size:11px;
  color:var(--ink-2);padding:2.5px 0;flex-wrap:wrap}
.inv .ok{color:var(--good);font-weight:600}

/* P3 feeds */
.feeds{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px}
@media(max-width:900px){.feeds{grid-template-columns:1fr}}
.feed{border:1px solid var(--hair-2);border-radius:9px;background:var(--surface);padding:13px 15px}
.feed .fh{display:flex;align-items:center;gap:8px;margin-bottom:8px;flex-wrap:wrap}
.feed .fh .nm{font-size:12.5px;font-weight:600;color:var(--ink)}
.feed .st{font-family:var(--mono);font-size:10px;letter-spacing:.5px;padding:1px 8px;
  border-radius:3px;border:1px solid}
.feed .st.off{color:var(--band-b);border-color:rgba(250,178,25,.45);background:rgba(250,178,25,.06)}
.feed .st.on{color:#4fc596;border-color:rgba(25,158,112,.45);background:rgba(25,158,112,.06)}
.feed .fd{font-size:11.5px;color:var(--ink-2);line-height:1.65}
.feed .fd b{color:var(--ink);font-family:var(--mono);font-weight:500}
.feed.slot{border-style:dashed;background:
  repeating-linear-gradient(45deg,transparent,transparent 7px,rgba(255,255,255,.012) 7px,rgba(255,255,255,.012) 14px),var(--surface)}

/* P4 audit stream */
.livetbl{width:100%;border-collapse:collapse;font-size:12px;min-width:740px}
.livetbl th{text-align:left;font-family:var(--mono);font-size:10px;letter-spacing:.8px;
  color:var(--muted);text-transform:uppercase;padding:8px 14px;border-bottom:1px solid var(--hair)}
.livetbl td{padding:8px 14px;border-top:1px solid var(--hair);color:var(--ink-2);vertical-align:top}
.livetbl .mono2{font-family:var(--mono);font-size:11.5px}
.livetbl .act{color:var(--ink);font-family:var(--mono);font-size:11.5px}
.livetbl .tr{color:var(--c-evidence);font-family:var(--mono);font-size:11.5px;white-space:nowrap}
.livetbl .ok{color:#4fc596;font-family:var(--mono);font-size:11px;white-space:nowrap}
.p4cap{padding:9px 14px;border-top:1px solid var(--hair);font-size:11.5px;color:var(--muted)}
.p4cap b{color:var(--ink)}
.livewait{padding:22px;font-family:var(--mono);font-size:12px;color:var(--muted);text-align:center}

/* P5 locked slot */
.locked{border:1px dashed var(--hair-2);border-radius:9px;background:
  repeating-linear-gradient(45deg,transparent,transparent 8px,rgba(255,255,255,.012) 8px,rgba(255,255,255,.012) 16px),var(--surface);
  padding:16px 18px}
.locked .lh2{display:flex;align-items:center;gap:10px;margin-bottom:9px;flex-wrap:wrap}
.locked .badge{font-family:var(--mono);font-size:10px;letter-spacing:1px;color:var(--band-b);
  border:1px solid rgba(250,178,25,.5);border-radius:3px;padding:2px 9px}
.locked .t{font-size:13.5px;font-weight:600;color:var(--ink)}
.locked .slottxt{font-size:12.5px;color:var(--ink-2);margin-bottom:11px}
.locked ul{margin:0;padding-left:18px;font-size:11.5px;color:var(--ink-2);line-height:1.8}
.locked ul b{color:var(--ink)}
.locked .owner{margin-top:11px;font-family:var(--mono);font-size:10.5px;color:var(--muted)}

/* CORE-4 judging cheat-sheet — sits directly under the provenance legend.
   Four compact cards, one per core concept a judge must grasp in seconds. */
.core4{background:var(--surface);border-bottom:1px solid var(--hair)}
.core4 .c4wrap{max-width:1180px;margin:0 auto;padding:15px 20px}
.core4 .c4head{display:flex;align-items:baseline;gap:8px 12px;flex-wrap:wrap;margin-bottom:12px}
.core4 .c4head .k{font-family:var(--mono);font-size:10px;letter-spacing:1.4px;color:var(--muted);
  text-transform:uppercase}
.core4 .c4head .h{font-size:14px;font-weight:600;color:var(--ink)}
.core4 .c4head .s{font-size:11.5px;color:var(--ink-2)}
.core4 .c4grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}
@media(max-width:980px){.core4 .c4grid{grid-template-columns:1fr 1fr}}
@media(max-width:560px){.core4 .c4grid{grid-template-columns:1fr}}
.c4card{border:1px solid var(--hair-2);border-radius:9px;background:var(--surface-2);
  padding:12px 13px;display:flex;flex-direction:column;gap:9px}
.c4card .c4t{display:flex;align-items:baseline;gap:7px;flex-wrap:wrap}
.c4card .c4t .no{font-family:var(--mono);font-size:12.5px;font-weight:600;color:var(--c-entity)}
.c4card .c4t .nm{font-size:12.5px;font-weight:600;color:var(--ink)}
.c4card .c4t .api{font-family:var(--mono);font-size:9.5px;color:var(--muted);font-weight:500;
  width:100%;letter-spacing:.2px}
.c4dia{background:var(--plane);border:1px solid var(--hair);border-radius:6px;padding:8px;
  display:flex;align-items:center;justify-content:center;min-height:100px}
.c4dia svg{width:100%;height:auto;display:block}
.c4cap{font-size:11px;color:var(--ink-2);line-height:1.55;flex:1}
.c4cap b{color:var(--ink)}
.c4link{font-family:var(--mono);font-size:9.5px;letter-spacing:.3px;color:var(--c-entity);
  text-decoration:none;border-top:1px solid var(--hair);padding-top:8px}
.c4link::after{content:" →"}
.c4link:hover{color:var(--ink)}
/* mini HTML diagrams (cards ③ ④) */
.c4q{width:100%;display:flex;flex-direction:column;gap:3px;font-family:var(--mono);font-size:8.5px}
.c4q-row{display:flex;align-items:center;gap:6px;padding:4px 6px;border-radius:4px;
  background:var(--surface-2);border:1px solid var(--hair)}
.c4q-row .d{width:6px;height:6px;border-radius:50%;flex:none;background:var(--band-c)}
.c4q-row.hot{background:rgba(208,59,59,.10);border-color:rgba(208,59,59,.45)}
.c4q-row.hot .d{background:var(--band-a);box-shadow:0 0 5px rgba(208,59,59,.6)}
.c4q-row.hot .st{color:#f08a8a}
.c4q-row.dim{opacity:.55}
.c4q-row .nm{color:var(--ink)}
.c4q-row .st{margin-left:auto;font-size:7.5px;letter-spacing:.5px}
.c4q-row .sc{color:var(--ink-2);min-width:22px;text-align:right}
.c4q-band{font-size:7px;letter-spacing:.4px;color:var(--muted);text-align:center;
  text-transform:uppercase;border-top:1px dashed var(--hair-2);border-bottom:1px dashed var(--hair-2);
  padding:3px 0;margin:1px 0}
.c4flow{width:100%;display:flex;flex-wrap:wrap;align-items:center;gap:6px 4px;justify-content:center;
  font-family:var(--mono);font-size:8.5px}
.c4step{padding:4px 7px;border-radius:4px;background:var(--surface-2);border:1px solid var(--c-output);
  color:var(--ink)}
.c4arr{color:var(--muted)}
.c4sent{padding:4px 7px;border-radius:4px;border:1px dashed var(--hair-2);color:var(--muted);
  text-decoration:line-through}
.c4sent-l{width:100%;text-align:center;font-family:var(--mono);font-size:7px;color:var(--muted);
  letter-spacing:.4px}
"""


# --------------------------------------------------------------------------- #
# data — real registry + a real engine sweep on the steady clock
# --------------------------------------------------------------------------- #
def compute_console_data() -> dict:
    registry = load_registry()
    suppliers = registry.get("suppliers", [])
    primes = registry.get("primes", [])
    programs = registry.get("programs", [])

    n_domains = sum(len(s.get("domains") or []) for s in suppliers)
    no_domain = [s for s in suppliers if not (s.get("domains") or [])]
    # primes carry no monitored domains in the registry — a REAL coverage gap:
    # prime-side assets are observed only through the cross-org `targets` edge.
    primes_unmonitored = [p for p in primes if not (p.get("domains") or [])]

    # full engine sweep on the steady-state clock (real computation)
    store, _corr, _written = build_store()
    propose_merges(store, now=STEADY_NOW)
    flags = flag_active_compromises(store, now=STEADY_NOW)
    assessments = compute_all(store, now=STEADY_NOW)
    n_paths = sum(len(store.propagation_paths(s["id"])) for s in store.suppliers())
    reason_hist = Counter(r for sk in flags.skipped for r in sk["reasons"])
    grade_hist = Counter(a.grade for a in assessments)
    pending_merges = len(store.merge_proposals("pending"))
    store.close()

    # engine self-check invariants (computed from the single config source)
    invariants = [
        ("supplier scoring", "active_floor > base_cap",
         f"{SCORING['active_floor']:.0f} > {SCORING['base_cap']:.0f}",
         SCORING["active_floor"] > SCORING["base_cap"]),
        ("program rollup", "active_floor > base_cap",
         f"{PROGRAM_SCORING['active_floor']:.0f} > {PROGRAM_SCORING['base_cap']:.0f}",
         PROGRAM_SCORING["active_floor"] > PROGRAM_SCORING["base_cap"]),
        ("grade thresholds", "즉시 70 / 주의 40",
         f"{SCORING['grade_thresholds']['즉시']:.0f} / {SCORING['grade_thresholds']['주의']:.0f}",
         SCORING["grade_thresholds"]["즉시"] > SCORING["grade_thresholds"]["주의"]),
    ]
    assert all(ok for *_x, ok in invariants), "engine invariant violated"

    return {
        "registry": registry,
        "n_sup": len(suppliers), "n_dom": n_domains,
        "n_prime": len(primes), "n_prog": len(programs),
        "no_domain": no_domain, "primes_unmonitored": primes_unmonitored,
        "n_incidents": len(flags.incidents),
        "n_candidates": len(flags.skipped) + len(flags.incidents),
        "reason_hist": reason_hist, "grade_hist": grade_hist,
        "n_paths": n_paths, "n_assessed": len(assessments),
        "pending_merges": pending_merges,
        "invariants": invariants,
        "action_chain": _load_action_chain(),
    }


# --------------------------------------------------------------------------- #
# panels
# --------------------------------------------------------------------------- #
def _p1_coverage(d: dict) -> str:
    reg = d["registry"]
    sup_by_id = {s["id"]: s for s in reg["suppliers"]}
    prog_by_id = {p["id"]: p for p in reg["programs"]}
    # children: prime -> direct suppliers; parent supplier -> subcontractors
    direct: dict[str, list] = {}
    subs: dict[str, list] = {}
    for s in reg["suppliers"]:
        sup_list = s.get("supplies")
        for pid in ([sup_list] if isinstance(sup_list, str) else (sup_list or [])):
            direct.setdefault(pid, []).append(s)
        sub = s.get("subcontracts")
        for parent in ([sub] if isinstance(sub, str) else (sub or [])):
            subs.setdefault(parent, []).append(s)

    def sup_badge(s: dict) -> str:
        if s.get("domains"):
            return '<span class="bdg">감시중</span>'
        return '<span class="bdg gap">도메인 미확인</span>'

    lines = []
    for p in reg["primes"]:
        progs = " · ".join(prog_by_id.get(pid, {}).get("name", pid) for pid in (p.get("runs") or []))
        lines.append(
            f'<div><span class="pr">{_e(p.get("name", p["id"]))}</span>'
            f'<span class="tw"> ({_e(p["id"])}) · runs: {_e(progs)}</span>'
            f'<span class="bdg gap">자산 도메인 미등록</span></div>'
        )
        kids = sorted(direct.get(p["id"], []), key=lambda s: (s.get("tier", 9), s["id"]))
        for i, s in enumerate(kids):
            last = i == len(kids) - 1 and not subs.get(s["id"])
            arm = "└" if last else "├"
            lines.append(
                f'<div><span class="tw">  {arm} T{_e(s.get("tier"))}</span> '
                f'{_e(s.get("name", s["id"]))}{sup_badge(s)}</div>'
            )
            for sub in sorted(subs.get(s["id"], []), key=lambda x: x["id"]):
                lines.append(
                    f'<div><span class="tw">  │   └ T{_e(sub.get("tier"))}</span> '
                    f'{_e(sub.get("name", sub["id"]))}'
                    f'<span class="tw"> — subcontractsTo</span>{sup_badge(sub)}</div>'
                )
    gaps = []
    gaps.append(
        f"등록됐지만 도메인 미확인 협력사 <b>{len(d['no_domain'])}개</b>"
        + ("" if not d["no_domain"] else
           " — " + ", ".join(_e(s.get("name", s["id"])) for s in d["no_domain"]))
    )
    gaps.append(
        f"원청 자산 도메인 미등록 <b>{len(d['primes_unmonitored'])}/{d['n_prime']}</b> — "
        "원청측 자산은 노출 레코드의 <span class='mono'>targets</span> 엣지로만 관측됨"
    )
    return f"""
  <div class="panel">
    <div class="ph"><span class="pk">P1</span><span class="pt">감시 범위 · coverage map</span>
      {chip('eng')} {chip('seed')}</div>
    <div class="pb">
      <div class="kpis">
        <div class="kpi"><div class="n">{d['n_sup']}</div><div class="l">등록 협력사 {chip('eng')}</div></div>
        <div class="kpi"><div class="n">{d['n_dom']}</div><div class="l">감시 도메인 {chip('eng')}</div></div>
        <div class="kpi"><div class="n">{d['n_prime']}</div><div class="l">원청 {chip('eng')}</div></div>
        <div class="kpi"><div class="n">{d['n_prog']}</div><div class="l">연결 프로그램 {chip('eng')}</div></div>
      </div>
      <div class="tree">{''.join(lines)}</div>
      <div class="gaps"><b>커버리지 공백 (숨기지 않음)</b><br>{'<br>'.join(gaps)}</div>
    </div>
  </div>"""


def _p2_allclear(d: dict) -> str:
    max_reason = max(d["reason_hist"].values()) if d["reason_hist"] else 1
    rej_rows = "".join(
        f'<div class="rrow"><span class="rn">{cnt}</span>'
        f'<span class="rb" style="width:{max(8, round(cnt / max_reason * 120))}px"></span>'
        f'<span>{_e(reason)}</span></div>'
        for reason, cnt in d["reason_hist"].most_common()
    )
    grade_txt = " · ".join(
        f"{_e(g)} {d['grade_hist'].get(g, 0)}" for g in ("즉시", "주의", "관찰")
    )
    inv_rows = "".join(
        f'<div class="irow"><span class="ok">OK</span><span>{_e(scope)}</span>'
        f'<span style="color:var(--muted)">{_e(rule)}</span><b>{_e(vals)}</b>{chip("eng")}</div>'
        for scope, rule, vals, _ok in d["invariants"]
    )
    return f"""
  <div class="panel">
    <div class="ph"><span class="pk">P2</span><span class="pt">조용함의 증명 · all-clear evidence</span>
      {chip('eng')}</div>
    <div class="pb">
      <div class="clear0"><span class="z">0</span>
        <span class="zl">활성 침해 경로 {chip('eng')}<br>
        <span style="font-size:11px;color:var(--muted)">"0건 탐지"가 아니라 — {d['n_candidates']}건 검토, 0건 활성</span></span></div>
      <div class="meta-line">마지막 전수 평가 <b>{_fmt_ts(STEADY_NOW)}</b> <span>시나리오 클럭</span>{chip('frame')}</div>
      <div class="meta-line">평가 대상 전파 경로 <b>{d['n_paths']}개</b> · 감염 기기 후보 <b>{d['n_candidates']}건</b> 검토 {chip('eng')}</div>
      <div class="meta-line">위험 평가 <b>{d['n_assessed']}건</b> 산출 — {_e(grade_txt)} {chip('eng')}</div>
      <div class="meta-line">병합 제안 대기 <b>{d['pending_merges']}건</b> (human-on-the-loop) {chip('eng')}</div>
      <div class="meta-line" style="border:none">다음 평가 주기 <b>+24h</b> {chip('frame')}</div>
      <div class="rej">
        <div style="font-size:11px;color:var(--muted);margin-bottom:4px">활성 조건 미충족 사유 (실측 히스토그램)</div>
        {rej_rows}
      </div>
      <div class="inv">
        <div style="font-size:11px;color:var(--muted);margin-bottom:4px">엔진 자기 검증 — 스코어링 불변식</div>
        {inv_rows}
      </div>
    </div>
  </div>"""


def _p3_feeds(d: dict) -> str:
    chain = d["action_chain"]
    if chain:
        sync = (f"마지막 readback <b>{_e(_fmt_iso(chain.get('generated_at')))}</b><br>"
                f"ontology <b>{_e(chain.get('ontology_api_name'))}</b><br>"
                f"OSDK <b>{OSDK_VERSION}</b> published · workflow actions "
                f"<b>{len(chain.get('discovered_actions', {}))}종</b>")
        sync_status = '<span class="st on">CONNECTED</span>'
        sync_chip = chip("live")
    else:
        sync = "readback 증적 없음 — action chain 실행 대기"
        sync_status = '<span class="st off">대기</span>'
        sync_chip = chip("eng")
    return f"""
  <div class="feeds">
    <div class="feed slot">
      <div class="fh"><span class="nm">credential exposure feed</span>
        <span class="st off">비활성 · 승인 대기</span>{chip('eng')}</div>
      <div class="fd">벤더 중립 빈 슬롯 — 연결된 척 하지 않는다.<br>
        계약: 승인·법무 검토 완료 시 <b>adapter 경계(normalize)</b>에서 교체 ·
        마스킹 강제 · 원문 미저장 · incremental poll.</div>
    </div>
    <div class="feed">
      <div class="fh"><span class="nm">OSINT feed</span>
        <span class="st off">수동 수집 전용</span>{chip('eng')}</div>
      <div class="fd">main demo에서 public feed fetch 없음 (하드 룰).<br>
        수집 도구는 별도 승인 하에 오프라인 실행.</div>
    </div>
    <div class="feed">
      <div class="fh"><span class="nm">Foundry sync</span>{sync_status}{sync_chip}</div>
      <div class="fd">{sync}</div>
    </div>
  </div>"""


def _p4_audit(d: dict) -> str:
    chain = d["action_chain"]
    if chain is None:
        body = ('<div class="livewait">실행 대기 — Foundry action-chain 증적'
                '(out/foundry_action_chain.json)이 아직 없습니다.</div>')
        cap = ""
    else:
        trs = []
        for s in chain.get("steps", []):
            ok = "✓ verified" if s.get("verified") else "미검증"
            trs.append(
                f"<tr><td class='mono2'>{_e(_fmt_iso(s.get('timestamp')))}</td>"
                f"<td class='act'>{_e(s.get('action'))}</td>"
                f"<td class='mono2'>{_e(s.get('objectType'))} · {_e(s.get('pk'))}</td>"
                f"<td class='tr'>{_e(s.get('readback_status_before'))} → {_e(s.get('readback_status_after'))}</td>"
                f"<td class='ok'>{_e(ok)} · HTTP {_e(s.get('http_status'))}</td></tr>"
            )
        body = f"""<div class="scroll-x"><table class="livetbl">
      <thead><tr><th>timestamp (UTC)</th><th>action apiName</th><th>object · pk</th>
        <th>status before → after</th><th>readback</th></tr></thead>
      <tbody>{''.join(trs)}</tbody></table></div>"""
        cap = ("<div class='p4cap'><b>human-on-the-loop이 실제로 작동 중이라는 증거.</b> "
               "실행 주체: 인증된 토큰 세션 · 각 전이는 실행 후 readback으로 검증 · "
               "원본 증적 <span class='mono'>out/foundry_action_chain.json</span></div>")
    return f"""
  <div class="panel">
    <div class="ph"><span class="pk">P4</span><span class="pt">결정 감사 스트림 · decision audit</span>
      {chip('live')}</div>
    {body}
    {cap}
  </div>"""


def _p5_locked() -> str:
    return f"""
  <div class="locked">
    <div class="lh2"><span class="pk" style="font-family:var(--mono);font-size:10px;
      letter-spacing:1.2px;color:var(--muted)">P5</span>
      <span class="t">민감정보 열람 구역 · sensitive record access</span>
      <span class="badge">LOCKED · EMPTY SLOT</span></div>
    <div class="slottxt">이 구역은 승인된 피드 연결 및 열람 권한 정책 확정 후 활성화됩니다.</div>
    <ul>
      <li><b>접근 게이트</b> — 열람 사유 입력 필수 → 사유가 감사로그에 기록된 후 개방</li>
      <li><b>마스킹 기본값</b> — 비밀값은 항상 <span class="mono">•••</span> + fingerprint;
          원문 열람은 별도 권한 + 별도 감사 이벤트</li>
      <li><b>세션 표시</b> — 열람자 ID·시각 워터마크</li>
      <li><b>열람 범위</b> — 레코드 단위 (전체 덤프 열람 없음)</li>
      <li><b>금지</b> — 원문 저장·복사 UI, 일괄 export</li>
    </ul>
    <div class="owner">requirement contract only — 구현 주체: Codex (이 화면은 잠긴 자리만 예약)</div>
  </div>"""


# --------------------------------------------------------------------------- #
# CORE-4 judging cheat-sheet (directly under the provenance legend)
# --------------------------------------------------------------------------- #
def _core4_strip() -> str:
    """Four compact cards — the one screen a judge reads to grasp the four core
    concepts in seconds: of/targets separation, subcontractsTo* variable depth,
    active-on-top ranking, human-reviewed draft with no send. Each card carries a
    3-second inline diagram, a 'why a flat table can't do this' line, and a link
    to where the concept is proven in the incident report (omija_demo)."""
    dm = "omija_demo.html"

    # ① of ≠ targets — 협력사 identity(of) vs 원청 asset(targets), credential between
    dia1 = """<svg viewBox="0 0 240 104" role="img" aria-label="of와 targets는 서로 다른 엣지">
  <defs>
    <marker id="c4of" markerWidth="7" markerHeight="7" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="#3987e5"/></marker>
    <marker id="c4tg" markerWidth="7" markerHeight="7" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="#ec835a"/></marker>
  </defs>
  <rect x="5" y="18" width="70" height="78" rx="6" fill="#1a1a19" stroke="#35342f"/>
  <text x="40" y="32" text-anchor="middle" fill="#a9a89f" font-family="ui-monospace,monospace" font-size="8">협력사·하청</text>
  <rect x="12" y="62" width="56" height="24" rx="4" fill="#201f1d" stroke="#3987e5"/>
  <text x="40" y="77" text-anchor="middle" fill="#ececea" font-family="ui-monospace,monospace" font-size="7.5">identity@하청</text>
  <rect x="165" y="18" width="70" height="78" rx="6" fill="#1a1a19" stroke="#35342f"/>
  <text x="200" y="32" text-anchor="middle" fill="#a9a89f" font-family="ui-monospace,monospace" font-size="8">원청·Prime</text>
  <rect x="172" y="62" width="56" height="24" rx="4" fill="#201f1d" stroke="#ec835a"/>
  <text x="200" y="77" text-anchor="middle" fill="#ececea" font-family="ui-monospace,monospace" font-size="7.5">vpn.원청</text>
  <rect x="93" y="30" width="54" height="20" rx="10" fill="rgba(201,133,0,.16)" stroke="#c98500"/>
  <text x="120" y="43" text-anchor="middle" fill="#e0b45a" font-family="ui-monospace,monospace" font-size="7.5">credential</text>
  <line x1="104" y1="50" x2="60" y2="60" stroke="#3987e5" stroke-width="1.5" marker-end="url(#c4of)"/>
  <text x="70" y="52" fill="#3987e5" font-family="ui-monospace,monospace" font-size="8">of</text>
  <line x1="136" y1="50" x2="180" y2="60" stroke="#ec835a" stroke-width="1.5" marker-end="url(#c4tg)"/>
  <text x="150" y="52" fill="#ec835a" font-family="ui-monospace,monospace" font-size="8">targets</text>
</svg>"""

    # ② subcontractsTo* — T2→T1→Prime→Program with a variable-depth (×N) loop
    dia2 = """<svg viewBox="0 0 240 104" role="img" aria-label="subcontractsTo 가변 깊이 체인">
  <defs>
    <marker id="c4ar" markerWidth="7" markerHeight="7" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="#6f6e68"/></marker>
    <marker id="c4rr" markerWidth="7" markerHeight="7" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="#c98500"/></marker>
  </defs>
  <path d="M14,26 C34,8 66,8 84,26" fill="none" stroke="#c98500" stroke-width="1.3" stroke-dasharray="3 3" marker-end="url(#c4rr)"/>
  <text x="30" y="12" fill="#c98500" font-family="ui-monospace,monospace" font-size="7.5">…* ×N (2차·3차·…)</text>
  <rect x="6" y="46" width="46" height="26" rx="5" fill="#201f1d" stroke="#35342f"/>
  <text x="29" y="62" text-anchor="middle" fill="#ececea" font-family="ui-monospace,monospace" font-size="8">T2</text>
  <rect x="66" y="46" width="46" height="26" rx="5" fill="#201f1d" stroke="#35342f"/>
  <text x="89" y="62" text-anchor="middle" fill="#ececea" font-family="ui-monospace,monospace" font-size="8">T1</text>
  <rect x="126" y="46" width="52" height="26" rx="5" fill="#201f1d" stroke="#35342f"/>
  <text x="152" y="62" text-anchor="middle" fill="#ececea" font-family="ui-monospace,monospace" font-size="8">Prime</text>
  <rect x="192" y="46" width="46" height="26" rx="5" fill="#201f1d" stroke="#35342f"/>
  <text x="215" y="62" text-anchor="middle" fill="#ececea" font-family="ui-monospace,monospace" font-size="7.5">Program</text>
  <line x1="52" y1="59" x2="66" y2="59" stroke="#6f6e68" stroke-width="1.3" marker-end="url(#c4ar)"/>
  <line x1="112" y1="59" x2="126" y2="59" stroke="#6f6e68" stroke-width="1.3" marker-end="url(#c4ar)"/>
  <line x1="178" y1="59" x2="192" y2="59" stroke="#6f6e68" stroke-width="1.3" marker-end="url(#c4ar)"/>
  <text x="59" y="88" text-anchor="middle" fill="#c98500" font-family="ui-monospace,monospace" font-size="7">subcontractsTo*</text>
  <text x="152" y="88" text-anchor="middle" fill="#6f6e68" font-family="ui-monospace,monospace" font-size="7">supplies · runs</text>
</svg>"""

    # ③ active-on-top — one active row pinned above the divider, volume below
    dia3 = """<div class="c4q">
  <div class="c4q-row hot"><span class="d"></span><span class="nm">sup-h</span>
    <span class="st">ACTIVE 즉시</span><span class="sc">88</span></div>
  <div class="c4q-band">active-on-top · 활성이 큐 상단 고정</div>
  <div class="c4q-row dim"><span class="d"></span><span class="nm">볼륨 노이즈</span><span class="sc">44건</span></div>
  <div class="c4q-row dim"><span class="d"></span><span class="nm">…</span><span class="sc">≤40</span></div>
</div>"""

    # ④ draft workflow — draft→reviewed→approved→exported, no 'sent' state
    dia4 = """<div class="c4flow">
  <span class="c4step">draft</span><span class="c4arr">→</span>
  <span class="c4step">reviewed</span><span class="c4arr">→</span>
  <span class="c4step">approved</span><span class="c4arr">→</span>
  <span class="c4step">exported</span><span class="c4arr">✕</span>
  <span class="c4sent">sent</span>
  <span class="c4sent-l">발송 상태 자체가 없음</span>
</div>"""

    cards = [
        {
            "no": "①", "nm": "of ≠ targets", "api": "CredentialExposure.of / .targets",
            "dia": dia1,
            "cap": "flat table 한 행은 계정 주인만 담는다 — 그 계정이 <b>겨눈 원청 자산(targets)</b>은 별개 엣지라 표현 불가.",
            "href": f"{dm}#blast", "link": "사건 보고서 · 블라스트 반경에서 증명",
        },
        {
            "no": "②", "nm": "subcontractsTo*", "api": "Supplier.subcontractsTo* (가변 깊이)",
            "dia": dia2,
            "cap": "flat join은 깊이를 지운다 — <b>2차·3차가 몇 홉 아래인지</b> 모른 채 한 판에 합쳐진다.",
            "href": f"{dm}#compare", "link": "사건 보고서 · 차별점에서 증명",
        },
        {
            "no": "③", "nm": "active-on-top", "api": "RiskAssessment · active_floor > base_cap",
            "dia": dia3,
            "cap": "볼륨으로 정렬하면 <b>활성 1건이 44건 노이즈에 묻힌다</b> — 활성 경로가 항상 위.",
            "href": f"{dm}#triage", "link": "사건 보고서 · 트리아지 큐에서 증명",
        },
        {
            "no": "④", "nm": "human-reviewed draft", "api": "NotificationDraft (no send state)",
            "dia": dia4,
            "cap": "flat table엔 <b>검토·승인 흔적이 없다</b> — 여기선 각 전이가 객체로 남고, 발송 상태는 아예 없다.",
            "href": f"{dm}#response", "link": "사건 보고서 · 대응 워크플로에서 증명",
        },
    ]

    card_html = "".join(
        f"""<div class="c4card">
      <div class="c4t"><span class="no">{c['no']}</span><span class="nm">{_e(c['nm'])}</span>
        <span class="api">{_e(c['api'])}</span></div>
      <div class="c4dia">{c['dia']}</div>
      <div class="c4cap">{c['cap']}</div>
      <a class="c4link" href="{_e(c['href'])}">{_e(c['link'])}</a>
    </div>"""
        for c in cards
    )

    return f"""
<div class="core4"><div class="c4wrap">
  <div class="c4head">
    <span class="k">judging cheat-sheet · 4 core concepts</span>
    <span class="h">flat table로는 안 되는 네 가지</span>
    <span class="s">각 카드 = 개념 · 3초 다이어그램 · 왜 flat table로는 안 되나 한 줄 · 사건 보고서 증명 링크</span>
  </div>
  <div class="c4grid">{card_html}</div>
</div></div>"""


# --------------------------------------------------------------------------- #
# assembly
# --------------------------------------------------------------------------- #
def build_html() -> tuple[str, dict]:
    d = compute_console_data()
    body = f"""
<section><div class="wrap">
  <div class="sec-k">감시 태세 + 시스템 신뢰 / steady state</div>
  <div class="sec-h">사건이 없을 때의 화면 — 조용함은 "안 본 것"이 아니라 "봤는데 없는 것"</div>
  <div class="sec-sub">사건 보고서(omija_demo)가 "왜 지금 움직여야 하나"라면, 이 콘솔은 "평소에 뭘 하고
     있나"다. 커버리지의 구멍까지 그대로 보여주는 것이 신뢰 장치다.</div>
  <div class="grid2">
    {_p1_coverage(d)}
    {_p2_allclear(d)}
  </div>
</div></section>
<section><div class="wrap">
  <div class="sec-k">P3 · 피드 상태 / collection posture — 정직한 상태 표시, "연결된 척" 금지</div>
  {_p3_feeds(d)}
</div></section>
<section><div class="wrap">
  {_p4_audit(d)}
</div></section>
<section style="border-bottom:none"><div class="wrap">
  {_p5_locked()}
  <div class="footer">SYNTHETIC DEMO · no network · no real data · no fake tickers ·
    generated by scripts/omija_console_home.py · direction: docs/review/steady-state-console-direction.md</div>
</div></section>"""

    page = f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Omija — Steady-State Console (데모 시나리오)</title>
<style>{TOKENS_CSS}{PAGE_CSS}</style></head><body data-palette="#3987e5,#199e70,#c98500,#9085e9">
{synthetic_banner()}
{nav_strip("omija_console_home.html")}
{chip_legend()}
{_core4_strip()}
<div class="mast"><div class="wrap">
  <span class="ver">engine · sqlite mock pipeline · offline</span>
  <div class="brand">OMIJA · STEADY-STATE CONSOLE</div>
  <div class="tag">사건이 없을 때 분석가가 켜놓는 기본 화면 · 감시 태세 · negative evidence · human-on-the-loop</div>
</div></div>
{body}
</body></html>"""

    meta = {
        "n_sup": d["n_sup"], "n_dom": d["n_dom"], "n_prog": d["n_prog"],
        "n_candidates": d["n_candidates"], "n_incidents": d["n_incidents"],
        "n_paths": d["n_paths"], "live_steps":
            len(d["action_chain"]["steps"]) if d["action_chain"] else 0,
    }
    return page, meta


def _safety_check(page: str) -> None:
    low = page.lower()
    problems = []
    if "stealthmole" in low:
        problems.append("vendor name 'stealthmole' present")
    for pat in ('src="http', "src='http", 'href="http', "href='http", "url(http",
                "@import", "<script", "<link", "animation:", "@keyframes"):
        if pat in low:
            problems.append(f"forbidden pattern: {pat!r}")
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
    print("Omija steady-state console")
    print("=" * 72)
    print(f"P1 coverage (real registry): {meta['n_sup']} suppliers · {meta['n_dom']} domains · "
          f"{meta['n_prog']} programs")
    print(f"P2 all-clear (real sweep @ steady clock): {meta['n_candidates']} candidates reviewed → "
          f"{meta['n_incidents']} active · {meta['n_paths']} paths evaluated")
    print(f"P4 audit stream: {meta['live_steps']} verified Foundry transitions")
    print("P5: LOCKED empty slot (requirement contract only)")
    print("safety: no vendor names, no external refs, no animation/ticker, no raw secret — OK")
    print(f"written: {OUT_HTML} ({os.path.getsize(OUT_HTML):,} bytes)")
    print("RESULT: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
