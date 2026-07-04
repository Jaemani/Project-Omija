"""P4: risk-ranking SOC dashboard (self-contained static HTML).

Runs the full mock pipe (via `scripts.p5_drafts.build_pipeline`), generates the
top notification drafts (P4↔P5 link), then renders ONE self-contained file at
`out/dashboard.html` — no CDN, no network, vanilla JS + inline CSS/SVG — so the
demo is safe offline (hackathon backup).

Layout (architecture.md §6):
  * ranking table — Supplier · score · grade(즉시/주의/관찰 색상) · active flag ·
    freshest signal · evidence count. ACTIVE suppliers pinned to the top.
  * drilldown (click a row) — Exposure/Device detail (module, host, MASKED secret,
    ThreatSource, source_ref, fetched_at), score component breakdown, a
    leak/infected timeline, and the supplier's notification-draft preview.
  * propagation graph — the CompromiseIncident path
    Device→Identity→Domain→Supplier→Prime→Program as an SVG node/edge diagram,
    active paths highlighted red; non-active suppliers show the
    Supplier→Prime→Program skeleton.
  * filters — tier / active-only / grade.

Guardrails: every value is masked or a provenance handle; raw secrets never reach
the page. Data is synthetic (`*.example`). No send capability anywhere.

Run: `uv run python scripts/p4_dashboard.py`  (writes out/dashboard.html)
"""

from __future__ import annotations

import html
import os
import sys
from datetime import datetime, timezone

# Repo root on path (script may be run directly).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from actions.notify_draft import generate_drafts                   # noqa: E402
from actions.propagate_risk import propagate_program_risk          # noqa: E402
from adapter.mock import DEMO_NOW                                   # noqa: E402
from scripts.p5_drafts import build_pipeline                       # noqa: E402

OUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out"
)
OUT_HTML = os.path.join(OUT_DIR, "dashboard.html")

_CRIT_LABEL = {3: "high", 2: "medium", 1: "low"}
_GRADE_CLASS = {"즉시": "g-now", "주의": "g-warn", "관찰": "g-watch"}


# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #

def _e(v) -> str:
    return html.escape("" if v is None else str(v))


def _fmt_ts(ts) -> str:
    if not ts:
        return "—"
    return datetime.fromtimestamp(int(ts), timezone.utc).strftime("%Y-%m-%d")


def _trunc(s: str, n: int) -> str:
    s = "" if s is None else str(s)
    return s if len(s) <= n else s[: n - 1] + "…"


# --------------------------------------------------------------------------- #
# ranking table
# --------------------------------------------------------------------------- #

def _ranking_rows(assessments, sup_by_id, store) -> str:
    rows = []
    for i, a in enumerate(assessments, 1):
        sup = sup_by_id.get(a.supplier_ref, {})
        crit = _CRIT_LABEL.get(sup.get("criticality"), str(sup.get("criticality")))
        fresh = a.components.get("recency", {}).get("age_days")
        fresh_txt = "—" if fresh is None else f"{fresh:.0f}d"
        gcls = _GRADE_CLASS.get(a.grade, "")
        active = a.active_flag
        flag = '<span class="flag active">● ACTIVE</span>' if active else \
               '<span class="flag">—</span>'
        rows.append(
            f'<tr class="rrow{" is-active" if active else ""}" '
            f'data-sup="{_e(a.supplier_ref)}" data-active="{1 if active else 0}" '
            f'data-tier="{_e(sup.get("tier"))}" data-grade="{_e(a.grade)}" '
            f'onclick="showDrill(\'{_e(a.supplier_ref)}\')">'
            f'<td class="rank">{i}</td>'
            f'<td class="name">{_e(sup.get("name", a.supplier_ref))}'
            f'<span class="sid">{_e(a.supplier_ref)}</span></td>'
            f'<td>T{_e(sup.get("tier"))}</td>'
            f'<td>{_e(crit)}</td>'
            f'<td class="score">{a.score:.2f}</td>'
            f'<td><span class="grade {gcls}">{_e(a.grade)}</span></td>'
            f'<td>{flag}</td>'
            f'<td>{fresh_txt} ago</td>'
            f'<td class="ev">{len(a.evidenced_by)}</td>'
            f'</tr>'
        )
    return "".join(rows)


# --------------------------------------------------------------------------- #
# drilldown panels
# --------------------------------------------------------------------------- #

def _exposure_table(exposures) -> str:
    head = (
        '<table class="exp"><thead><tr>'
        '<th>module</th><th>threat source</th><th>host</th>'
        '<th>secret (masked)</th><th>observed</th><th>fetched</th>'
        '<th>source_ref</th></tr></thead><tbody>'
    )
    body = []
    for r in exposures:
        active = r.get("infected_at") is not None and r.get("has_session_cookie") \
            and r.get("account_type") in ("vpn", "admin")
        dev = ""
        if r.get("infected_at"):
            dev = (
                f'<div class="dev">device: malware={_e(r.get("malware"))} · '
                f'acct={_e(r.get("account_type"))} · '
                f'cookie={"yes" if r.get("has_session_cookie") else "no"} · '
                f'infected={_fmt_ts(r.get("infected_at"))}</div>'
            )
        badge = ' <span class="mini-active">ACTIVE</span>' if active else ""
        body.append(
            f'<tr class="{"exp-active" if active else ""}">'
            f'<td>{_e(r.get("module"))}{badge}</td>'
            f'<td>{_e(r.get("threat_kind"))}</td>'
            f'<td class="mono">{_e(r.get("host") or "—")}</td>'
            f'<td class="mono secret">{_e(r.get("secret_type"))}: '
            f'{_e(r.get("masked_value") or "—")}{dev}</td>'
            f'<td>{_fmt_ts(r.get("observed_at"))}</td>'
            f'<td>{_fmt_ts(r.get("fetched_at"))}</td>'
            f'<td class="mono ref" title="{_e(r.get("match_basis") or "")}">'
            f'{_e(r.get("source_ref"))}</td>'
            f'</tr>'
        )
    return head + "".join(body) + "</tbody></table>"


def _components_html(components: dict) -> str:
    def c(k):
        return components.get(k, {})
    es, rc, st, mc = c("exposure_scale"), c("recency"), c("secret_type"), c("module_confidence")
    chips = [
        ("exposure scale", f'{es.get("dedup_count")} (raw {es.get("raw_count")}) → {es.get("points")}pt'),
        ("recency", f'{rc.get("age_days")}d → {rc.get("points")}pt'),
        ("secret type", f'{st.get("strongest")} (w{st.get("weight")}) → {st.get("points")}pt'),
        ("module conf.", f'{"/".join(mc.get("modules", []))} → {mc.get("points")}pt'),
        ("base subtotal", f'{components.get("base_subtotal")}'),
        ("crit × tier", f'{components.get("criticality_multiplier")} × {components.get("tier_multiplier")}'),
        ("base score", f'{components.get("base_score")}'),
        ("active weight", f'{components.get("active_flag")} · q={components.get("active_quality")}'),
        ("SCORE", f'{components.get("score")} ({components.get("grade")})'),
    ]
    items = "".join(
        f'<div class="chip"><span class="ck">{_e(k)}</span>'
        f'<span class="cv">{_e(v)}</span></div>'
        for k, v in chips
    )
    return f'<div class="chips">{items}</div>'


def _timeline_html(exposures) -> str:
    events = []
    for r in exposures:
        ts = r.get("infected_at") or r.get("observed_at")
        kind = "infected" if r.get("infected_at") else "leak"
        events.append((int(ts) if ts else 0, kind, r))
    events.sort(key=lambda e: -e[0])
    rows = []
    for ts, kind, r in events:
        dot = "ti-infected" if kind == "infected" else "ti-leak"
        rows.append(
            f'<li><span class="tidot {dot}"></span>'
            f'<span class="tidate">{_fmt_ts(ts)}</span> '
            f'<span class="tikind">{kind}</span> · '
            f'[{_e(r.get("module"))}] {_e(r.get("host") or "—")} '
            f'({_e(r.get("secret_type"))})</li>'
        )
    return f'<ul class="timeline">{"".join(rows)}</ul>'


def _draft_html(draft: dict | None) -> str:
    if not draft:
        return '<p class="muted">이 업체에 대해 생성된 통보 초안이 없습니다.</p>'
    return (
        '<div class="draftbox"><div class="draftmeta">'
        f'status=<strong>{_e(draft.get("status"))}</strong> · '
        '자동 생성 초안 · 분석가 검토·승인 전 발송 금지</div>'
        f'<pre class="draft">{_e(draft.get("body"))}</pre></div>'
    )


def _drilldown_panels(assessments, sup_by_id, store) -> str:
    panels = []
    for a in assessments:
        sup = sup_by_id.get(a.supplier_ref, {})
        exposures = store.exposures_for_supplier(a.supplier_ref)
        incidents = store.incidents_for_supplier(a.supplier_ref)
        draft = store.draft_for_supplier(a.supplier_ref)

        inc_html = ""
        if incidents:
            chains = "".join(
                f'<div class="chain">{_e(_path_chain(inc.get("path", [])))}</div>'
                for inc in incidents
            )
            inc_html = (
                '<div class="block"><h4>활성 침해 경로 (traverses)</h4>'
                f'{chains}</div>'
            )

        panels.append(
            f'<div class="panel" id="drill-{_e(a.supplier_ref)}" hidden>'
            f'<div class="panel-head"><h3>{_e(sup.get("name", a.supplier_ref))} '
            f'<span class="sid">{_e(a.supplier_ref)}</span></h3>'
            f'<div class="score-big {_GRADE_CLASS.get(a.grade, "")}">'
            f'{a.score:.2f} <span>{_e(a.grade)}</span></div></div>'
            f'{inc_html}'
            '<div class="block"><h4>점수 기여분 (components)</h4>'
            f'{_components_html(a.components)}</div>'
            '<div class="block"><h4>노출/기기 상세 (마스킹)</h4>'
            f'{_exposure_table(exposures)}</div>'
            '<div class="block"><h4>타임라인</h4>'
            f'{_timeline_html(exposures)}</div>'
            '<div class="block"><h4>통보 초안 미리보기 (P5)</h4>'
            f'{_draft_html(draft)}</div>'
            '</div>'
        )
    return "".join(panels)


def _path_chain(path: list) -> str:
    return " → ".join(
        f'{n.get("type")}({n.get("detail") or n.get("ref")})' for n in path
    )


# --------------------------------------------------------------------------- #
# program exposure roll-up (risk propagated UP onto defense Programs)
# --------------------------------------------------------------------------- #

def _program_section(store) -> str:
    """ProgramExposure ranking: which defense Program is burning, and through
    which supplier chain. Empty (returns '') if PropagateRisk was not run."""
    pes = store.program_exposures()
    if not pes:
        return ""
    prog_by_id = {p["id"]: p for p in store.programs()}
    rows = []
    for pe in pes:
        comp = pe.get("components", {})
        prog = prog_by_id.get(pe["program_ref"], {})
        active = pe.get("active_flag")
        gcls = _GRADE_CLASS.get(pe.get("grade"), "")
        flag = ('<span class="flag active">● BURNING</span>' if active
                else '<span class="flag">—</span>')
        contrib = comp.get("contributing_suppliers", [])
        contrib_txt = ", ".join(
            f'{c["id"]}{"*" if c.get("active") else ""}' for c in contrib
        )
        # surface the multi-tier active chains (the money-shot)
        chains = "".join(
            f'<div class="chain">{_e(cp.get("chain"))}</div>'
            for cp in pe.get("contributing_paths", [])
            if cp.get("active") and cp.get("multi_tier")
        )
        chain_block = (f'<tr class="pe-detail"><td colspan="6">{chains}</td></tr>'
                       if chains else "")
        rows.append(
            f'<tr class="rrow{" is-active" if active else ""}">'
            f'<td class="name">{_e(prog.get("name", pe["program_ref"]))}'
            f'<span class="sid">{_e(pe["program_ref"])}</span></td>'
            f'<td>{_e(comp.get("sensitivity") or "—")}</td>'
            f'<td class="score">{pe.get("score", 0):.2f}</td>'
            f'<td><span class="grade {gcls}">{_e(pe.get("grade"))}</span></td>'
            f'<td>{flag}</td>'
            f'<td class="mono ref">{_e(contrib_txt)}</td>'
            f'</tr>{chain_block}'
        )
    return (
        '<h2>프로그램 노출 (전파 롤업 — 활성 프로그램 상단)</h2>'
        '<p class="sub" style="margin:-4px 0 8px">협력사 위험이 subcontracts→supplies→runs를 타고 '
        '방산 프로그램으로 전파된 결과. <code>*</code>=활성침해 기여 협력사. '
        '아래 다중티어 경로는 2차 말단 감염이 프로그램을 태우는 경로입니다.</p>'
        '<table class="rank"><thead><tr>'
        '<th>program</th><th>sensitivity</th><th>score</th><th>grade</th>'
        '<th>status</th><th>contributing suppliers</th>'
        '</tr></thead><tbody>' + "".join(rows) + '</tbody></table>'
    )


# --------------------------------------------------------------------------- #
# propagation graph (inline SVG)
# --------------------------------------------------------------------------- #

_COL = {  # center-x per layer
    "dev": 95, "idn": 300, "dom": 510, "sup": 720, "prime": 945, "prog": 1150,
}
_COL_LABEL = [
    (95, "Device"), (300, "Identity"), (510, "Domain"),
    (720, "Supplier"), (945, "Prime"), (1150, "Program"),
]
_NODE_W = 168
_NODE_H = 38
_TOP = 96
_ROW_H = 66


def _graph_svg(store, assessments) -> str:
    assess_by_sup = {a.supplier_ref: a for a in assessments}
    incidents = store.incidents()
    inc_by_sup = {inc["supplier_ref"]: inc for inc in incidents}
    suppliers = store.suppliers()

    # order: active first, then exposed by score desc, then clean; keep those
    # that have a propagation path (skeleton is meaningful).
    def sort_key(s):
        sid = s["id"]
        active = sid in inc_by_sup
        a = assess_by_sup.get(sid)
        exposed = a is not None
        score = a.score if a else -1.0
        return (0 if active else (1 if exposed else 2), -score, sid)

    ordered = [s for s in sorted(suppliers, key=sort_key)
               if store.propagation_for_supplier(s["id"])]

    sup_y = {s["id"]: _TOP + i * _ROW_H for i, s in enumerate(ordered)}
    nodes: dict[str, dict] = {}
    active_keys: set[str] = set()

    # active-path edges (red) + left-half nodes from incident paths
    active_edges: set[tuple[str, str]] = set()
    for inc in incidents:
        sid = inc["supplier_ref"]
        if sid not in sup_y:
            continue
        y = sup_y[sid]
        keys = []
        for n in inc.get("path", []):
            t = n.get("type")
            if t == "InfectedDevice":
                k = f"dev:{sid}"
                nodes.setdefault(k, dict(cx=_COL["dev"], cy=y, label="InfectedDevice",
                                         sub=_trunc(n.get("detail") or n.get("ref"), 22), cls="dev"))
            elif t == "Identity":
                k = f"idn:{sid}"
                nodes.setdefault(k, dict(cx=_COL["idn"], cy=y, label="Identity",
                                         sub=_trunc(n.get("detail") or n.get("ref"), 22), cls="idn"))
            elif t == "Domain":
                k = f"dom:{sid}"
                nodes.setdefault(k, dict(cx=_COL["dom"], cy=y, label="Domain",
                                         sub=_trunc(n.get("detail") or n.get("ref"), 22), cls="dom"))
            elif t == "Supplier":
                k = f"sup:{sid}"
            elif t == "Prime":
                k = f"prime:{n.get('ref')}"
            elif t == "Program":
                k = f"prog:{n.get('ref')}"
            else:
                continue
            keys.append(k)
            active_keys.add(k)
        for a_, b_ in zip(keys, keys[1:]):
            active_edges.add((a_, b_))

    # supplier nodes
    for s in ordered:
        sid = s["id"]
        a = assess_by_sup.get(sid)
        if sid in inc_by_sup:
            cls = "sup active"
        elif a is not None:
            cls = "sup exposed"
        else:
            cls = "sup clean"
        sub = "clean" if a is None else f"{a.grade} · {a.score:.0f}"
        nodes[f"sup:{sid}"] = dict(cx=_COL["sup"], cy=sup_y[sid],
                                   label=_trunc(s.get("name", sid), 20), sub=sub, cls=cls)

    # skeleton edges + collect primes/programs (shared, deduped)
    skeleton: set[tuple[str, str]] = set()
    prime_ys: dict[str, list] = {}
    prime_name: dict[str, str] = {}
    prog_primes: dict[str, set] = {}
    prog_name: dict[str, str] = {}
    for s in ordered:
        sid = s["id"]
        for row in store.propagation_for_supplier(sid):
            pid = row.get("prime_id")
            if not pid:
                continue
            skeleton.add((f"sup:{sid}", f"prime:{pid}"))
            prime_ys.setdefault(pid, []).append(sup_y[sid])
            prime_name[pid] = row.get("prime_name") or pid
            gid = row.get("program_id")
            if gid:
                skeleton.add((f"prime:{pid}", f"prog:{gid}"))
                prog_primes.setdefault(gid, set()).add(pid)
                prog_name[gid] = row.get("program_name") or gid

    for pid, ys in prime_ys.items():
        uy = sorted(set(ys))
        k = f"prime:{pid}"
        nodes[k] = dict(cx=_COL["prime"], cy=sum(uy) / len(uy),
                        label=_trunc(prime_name[pid], 18), sub="Prime",
                        cls="prime" + (" active" if k in active_keys else ""))
    for gid, pids in prog_primes.items():
        pys = [nodes[f"prime:{p}"]["cy"] for p in pids if f"prime:{p}" in nodes]
        k = f"prog:{gid}"
        nodes[k] = dict(cx=_COL["prog"], cy=(sum(pys) / len(pys)) if pys else _TOP,
                        label=_trunc(prog_name[gid], 18), sub="Program",
                        cls="prog" + (" active" if k in active_keys else ""))

    height = _TOP + max(1, len(ordered)) * _ROW_H + 20
    width = 1260

    # --- render ---
    parts = [
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        'class="graph" role="img" aria-label="supply-chain propagation graph">',
        '<defs>'
        '<marker id="ar" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto">'
        '<path d="M0,0 L7,3 L0,6 Z" fill="#3d444d"/></marker>'
        '<marker id="arA" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto">'
        '<path d="M0,0 L7,3 L0,6 Z" fill="#ff6b6b"/></marker>'
        '</defs>',
    ]
    # column headers
    for cx, lab in _COL_LABEL:
        parts.append(
            f'<text x="{cx}" y="52" text-anchor="middle" class="col-h">{lab}</text>'
        )

    def edge(a_, b_, active):
        na, nb = nodes.get(a_), nodes.get(b_)
        if not na or not nb:
            return ""
        x1 = na["cx"] + _NODE_W / 2
        x2 = nb["cx"] - _NODE_W / 2
        cls = "edge active" if active else "edge"
        mk = "arA" if active else "ar"
        return (f'<line x1="{x1:.0f}" y1="{na["cy"]:.0f}" x2="{x2:.0f}" '
                f'y2="{nb["cy"]:.0f}" class="{cls}" marker-end="url(#{mk})"/>')

    # skeleton first (gray), skip those overridden by an active edge
    for a_, b_ in sorted(skeleton - active_edges):
        parts.append(edge(a_, b_, active=False))
    for a_, b_ in sorted(active_edges):
        parts.append(edge(a_, b_, active=True))

    # nodes on top
    for k, n in nodes.items():
        cx, cy = n["cx"], n["cy"]
        x = cx - _NODE_W / 2
        yy = cy - _NODE_H / 2
        parts.append(
            f'<g class="gnode {n["cls"]}">'
            f'<title>{_e(n["label"])} · {_e(n["sub"])}</title>'
            f'<rect x="{x:.0f}" y="{yy:.0f}" width="{_NODE_W}" height="{_NODE_H}" rx="7"/>'
            f'<text x="{cx}" y="{cy - 2:.0f}" text-anchor="middle" class="nlabel">'
            f'{_e(n["label"])}</text>'
            f'<text x="{cx}" y="{cy + 11:.0f}" text-anchor="middle" class="nsub">'
            f'{_e(n["sub"])}</text>'
            f'</g>'
        )
    parts.append('</svg>')
    return "".join(parts)


# --------------------------------------------------------------------------- #
# page assembly
# --------------------------------------------------------------------------- #

def build_dashboard_html(store, assessments, now: int) -> str:
    sup_by_id = {s["id"]: s for s in store.suppliers()}
    active_n = sum(1 for a in assessments if a.active_flag)
    incidents = store.incidents()

    rows = _ranking_rows(assessments, sup_by_id, store)
    panels = _drilldown_panels(assessments, sup_by_id, store)
    program_section = _program_section(store)
    svg = _graph_svg(store, assessments)
    program_exposures = store.program_exposures()
    burning_programs = sum(1 for pe in program_exposures if pe.get("active_flag"))

    return f"""<!DOCTYPE html><html lang="ko"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Supply-chain Credential Exposure — 위험 순위 대시보드</title>
<style>
:root {{ color-scheme: dark; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: #0d1117; color: #e6edf3;
       font: 14px/1.5 -apple-system, "Segoe UI", system-ui, sans-serif; }}
.wrap {{ max-width: 1300px; margin: 0 auto; padding: 20px 22px 60px; }}
header h1 {{ font-size: 20px; margin: 0 0 4px; }}
header .sub {{ color: #8b949e; font-size: 12.5px; margin: 0 0 2px; }}
.guard {{ margin: 10px 0 18px; padding: 9px 12px; border-radius: 8px;
         background: #17212b; border: 1px solid #21313d; color: #79c0ff; font-size: 12px; }}
.kpis {{ display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 18px; }}
.kpi {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px;
       padding: 10px 16px; min-width: 118px; }}
.kpi .n {{ font-size: 22px; font-weight: 700; }}
.kpi .l {{ font-size: 10.5px; color: #8b949e; text-transform: uppercase; letter-spacing: .05em; }}
.kpi.alert .n {{ color: #ff6b6b; }}
.filters {{ display: flex; gap: 14px; align-items: center; flex-wrap: wrap;
           margin-bottom: 12px; font-size: 12.5px; color: #8b949e; }}
.filters select {{ background: #161b22; color: #e6edf3; border: 1px solid #30363d;
                  border-radius: 6px; padding: 4px 8px; }}
.filters label {{ display: inline-flex; gap: 5px; align-items: center; }}
h2 {{ font-size: 14px; color: #8b949e; text-transform: uppercase; letter-spacing: .05em;
     margin: 24px 0 8px; border-bottom: 1px solid #21262d; padding-bottom: 6px; }}
table.rank {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
table.rank th {{ text-align: left; color: #8b949e; font-weight: 600; padding: 7px 10px;
                border-bottom: 1px solid #30363d; font-size: 11px; text-transform: uppercase; }}
table.rank td {{ padding: 8px 10px; border-bottom: 1px solid #21262d; }}
tr.rrow {{ cursor: pointer; }}
tr.rrow:hover td {{ background: #161b22; }}
tr.rrow.is-active td {{ background: #1b0f12; }}
tr.rrow.is-active:hover td {{ background: #241115; }}
tr.rrow.sel td {{ box-shadow: inset 3px 0 0 #58a6ff; }}
td.rank {{ color: #8b949e; width: 30px; }}
td.name {{ font-weight: 600; }}
td.name .sid {{ color: #6e7681; font-weight: 400; font-size: 11px; margin-left: 6px; }}
td.score {{ font-variant-numeric: tabular-nums; font-weight: 700; }}
td.ev {{ text-align: right; color: #8b949e; }}
.grade {{ padding: 2px 8px; border-radius: 20px; font-size: 11px; font-weight: 700; }}
.g-now {{ background: #2d0f12; color: #ff6b6b; border: 1px solid #6e2329; }}
.g-warn {{ background: #2b230c; color: #e3b341; border: 1px solid #5c4a15; }}
.g-watch {{ background: #14261a; color: #56d364; border: 1px solid #23503a; }}
.flag {{ color: #6e7681; font-size: 12px; }}
.flag.active {{ color: #ff6b6b; font-weight: 700; }}
.panel {{ background: #161b22; border: 1px solid #30363d; border-radius: 10px;
         padding: 16px 18px; margin-top: 12px; }}
.panel-head {{ display: flex; justify-content: space-between; align-items: center;
              border-bottom: 1px solid #21262d; padding-bottom: 8px; margin-bottom: 10px; }}
.panel-head h3 {{ margin: 0; font-size: 16px; }}
.panel-head .sid {{ color: #6e7681; font-weight: 400; font-size: 12px; }}
.score-big {{ font-size: 22px; font-weight: 800; padding: 2px 12px; border-radius: 8px; }}
.score-big span {{ font-size: 12px; }}
.block {{ margin: 14px 0; }}
.block h4 {{ margin: 0 0 8px; font-size: 12px; color: #8b949e; text-transform: uppercase;
            letter-spacing: .04em; }}
.chain {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px;
         color: #ffa198; background: #1b0f12; border: 1px solid #6e2329; border-radius: 6px;
         padding: 8px 10px; margin-bottom: 6px; overflow-x: auto; }}
.chips {{ display: flex; flex-wrap: wrap; gap: 8px; }}
.chip {{ background: #0d1117; border: 1px solid #30363d; border-radius: 6px;
        padding: 5px 9px; font-size: 11.5px; }}
.chip .ck {{ color: #8b949e; margin-right: 6px; }}
.chip .cv {{ font-variant-numeric: tabular-nums; }}
table.exp {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
table.exp th {{ text-align: left; color: #8b949e; font-weight: 600; padding: 5px 8px;
               border-bottom: 1px solid #30363d; }}
table.exp td {{ padding: 6px 8px; border-bottom: 1px solid #21262d; vertical-align: top; }}
tr.exp-active td {{ background: #1b0f12; }}
.mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
.secret {{ color: #d2a8ff; }}
.ref {{ color: #7d8590; font-size: 11px; }}
.dev {{ color: #8b949e; font-size: 11px; margin-top: 3px; }}
.mini-active {{ color: #ff6b6b; font-size: 10px; font-weight: 700; margin-left: 4px; }}
.timeline {{ list-style: none; padding: 0; margin: 0; font-size: 12px; }}
.timeline li {{ padding: 3px 0; }}
.tidot {{ display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 7px; }}
.ti-infected {{ background: #ff6b6b; }}
.ti-leak {{ background: #d29922; }}
.tidate {{ font-variant-numeric: tabular-nums; color: #adbac7; }}
.tikind {{ color: #8b949e; }}
.draftbox {{ border: 1px solid #30363d; border-radius: 8px; overflow: hidden; }}
.draftmeta {{ background: #17212b; color: #79c0ff; font-size: 11px; padding: 6px 10px;
             border-bottom: 1px solid #21313d; }}
pre.draft {{ margin: 0; padding: 12px 14px; font-size: 11.5px; line-height: 1.55;
            white-space: pre-wrap; word-break: break-word; max-height: 420px; overflow: auto;
            color: #c9d1d9; }}
.muted {{ color: #6e7681; }}
.graph-wrap {{ overflow-x: auto; background: #0b0f14; border: 1px solid #21262d;
              border-radius: 10px; padding: 6px; }}
svg.graph {{ display: block; }}
.col-h {{ fill: #6e7681; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .05em; }}
.edge {{ stroke: #3d444d; stroke-width: 1.4; }}
.edge.active {{ stroke: #ff6b6b; stroke-width: 2; }}
.gnode rect {{ fill: #161b22; stroke: #30363d; stroke-width: 1.4; }}
.gnode .nlabel {{ fill: #e6edf3; font-size: 11px; font-weight: 600; }}
.gnode .nsub {{ fill: #8b949e; font-size: 9.5px; }}
.gnode.sup.exposed rect {{ stroke: #d29922; }}
.gnode.sup.clean rect {{ stroke: #30363d; }}
.gnode.active rect, .gnode.sup.active rect {{ stroke: #ff6b6b; fill: #1b0f12; }}
.gnode.dev rect, .gnode.idn rect, .gnode.dom rect {{ stroke: #ff6b6b; fill: #1b0f12; }}
.legend {{ display: flex; gap: 16px; font-size: 11.5px; color: #8b949e; margin: 8px 2px 0; }}
.legend span::before {{ content: ""; display: inline-block; width: 10px; height: 10px;
                       border-radius: 2px; margin-right: 5px; vertical-align: middle; }}
.lg-active::before {{ background: #ff6b6b; }}
.lg-exposed::before {{ background: #d29922; }}
.lg-clean::before {{ background: #30363d; }}
footer {{ margin-top: 30px; color: #6e7681; font-size: 11.5px; border-top: 1px solid #21262d;
         padding-top: 12px; }}
</style></head><body>
<div class="wrap">
<header>
  <h1>공급망 자격증명 노출 — 위험 순위 대시보드</h1>
  <p class="sub">활성침해 우선 트리아지 · Device→Identity→Domain→Supplier→Prime→Program 전파 그래프 · 통보 초안(발송 없음)</p>
  <p class="sub">anchor DEMO_NOW = {_fmt_ts(now)} UTC</p>
</header>
<div class="guard">모의 데이터(합성 <code>*.example</code> 도메인) · 방어적 조기경보 데모 · 비밀값 전량 마스킹(<code>**·</code>) · 자동 발송 없음(초안 생성까지)</div>

<div class="kpis">
  <div class="kpi"><div class="n">{len(assessments)}</div><div class="l">ranked suppliers</div></div>
  <div class="kpi alert"><div class="n">{active_n}</div><div class="l">active compromise</div></div>
  <div class="kpi"><div class="n">{len(incidents)}</div><div class="l">incidents opened</div></div>
  <div class="kpi alert"><div class="n">{burning_programs}</div><div class="l">programs burning</div></div>
</div>

<h2>위험 순위 (활성 상단 고정)</h2>
<div class="filters">
  <label>tier <select id="f-tier" onchange="applyFilters()">
    <option value="">all</option><option value="1">T1</option><option value="2">T2</option></select></label>
  <label>grade <select id="f-grade" onchange="applyFilters()">
    <option value="">all</option><option value="즉시">즉시</option><option value="주의">주의</option><option value="관찰">관찰</option></select></label>
  <label><input type="checkbox" id="f-active" onchange="applyFilters()"> 활성침해만</label>
  <span id="f-count" class="muted"></span>
</div>
<table class="rank"><thead><tr>
  <th>#</th><th>supplier</th><th>tier</th><th>crit</th><th>score</th><th>grade</th>
  <th>active</th><th>freshest</th><th>ev</th>
</tr></thead><tbody id="rank-body">{rows}</tbody></table>

{program_section}

<h2>드릴다운 (행 클릭 — 노출·기여분·타임라인·초안)</h2>
<div id="drill-host">
  <p class="muted" id="drill-hint">위 순위 표에서 업체 행을 클릭하면 상세가 표시됩니다.</p>
  {panels}
</div>

<h2>전파 그래프 (활성 경로 빨강)</h2>
<div class="graph-wrap">{svg}</div>
<div class="legend">
  <span class="lg-active">활성 침해 경로 / 노드</span>
  <span class="lg-exposed">노출(비활성) 업체</span>
  <span class="lg-clean">clean / 골격</span>
</div>

<footer>
  방어적 조기경보 데모 · 모든 위험 판정은 원 레코드(source_ref)로 역추적 · 통보는 초안 생성까지이며 실제 발송 기능은 존재하지 않습니다 · 합성 데이터.
</footer>
</div>
<script>
function showDrill(sid) {{
  document.querySelectorAll('#drill-host .panel').forEach(function(p) {{ p.hidden = true; }});
  document.querySelectorAll('tr.rrow').forEach(function(r) {{ r.classList.remove('sel'); }});
  var hint = document.getElementById('drill-hint');
  if (hint) hint.hidden = true;
  var panel = document.getElementById('drill-' + sid);
  if (panel) panel.hidden = false;
  var row = document.querySelector('tr.rrow[data-sup="' + sid + '"]');
  if (row) {{ row.classList.add('sel'); }}
}}
function applyFilters() {{
  var tier = document.getElementById('f-tier').value;
  var grade = document.getElementById('f-grade').value;
  var activeOnly = document.getElementById('f-active').checked;
  var shown = 0;
  document.querySelectorAll('#rank-body tr.rrow').forEach(function(r) {{
    var ok = true;
    if (tier && r.dataset.tier !== tier) ok = false;
    if (grade && r.dataset.grade !== grade) ok = false;
    if (activeOnly && r.dataset.active !== '1') ok = false;
    r.style.display = ok ? '' : 'none';
    if (ok) shown++;
  }});
  document.getElementById('f-count').textContent = shown + ' shown';
}}
applyFilters();
</script>
</body></html>"""


def run() -> int:
    now = DEMO_NOW
    store, assessments = build_pipeline(now)
    generate_drafts(store, assessments, top=3, now=now)   # P4↔P5 link
    propagate_program_risk(store, now=now)                # P4 program roll-up

    os.makedirs(OUT_DIR, exist_ok=True)
    html_str = build_dashboard_html(store, assessments, now)
    with open(OUT_HTML, "w", encoding="utf-8") as fh:
        fh.write(html_str)

    # CLI summary + self-checks
    active = [a for a in assessments if a.active_flag]
    nonactive = [a for a in assessments if not a.active_flag]
    active_on_top = bool(active) and (
        not nonactive or min(a.score for a in active) > max(a.score for a in nonactive)
    )

    from adapter.mock import MockExposureSource
    raw = MockExposureSource().raw_secrets()
    leaked = [s for s in raw if s in html_str]

    print("=" * 72)
    print("P4 dashboard — self-contained SOC ranking + propagation graph")
    print(f"anchor DEMO_NOW = {_fmt_ts(now)} UTC")
    print("=" * 72)
    print(f"ranked suppliers      : {len(assessments)}")
    print(f"active compromise     : {len(active)}  (on top: {active_on_top})")
    print(f"incidents / panels    : {len(store.incidents())} / {len(assessments)}")
    print(f"raw secrets in HTML   : {len(leaked)}")
    print(f"output                : {OUT_HTML}")
    print("=" * 72)

    ok = (bool(assessments) and active_on_top and not leaked
          and os.path.exists(OUT_HTML))
    print("RESULT:", "OK" if ok else "FAIL")
    store.close()
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(run())
