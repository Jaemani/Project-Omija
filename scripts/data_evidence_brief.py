"""Generate a concise data-evidence page for Omija demo.

Public OSINT context is safe to render statically. Sensitive provider records
are not collected or baked into HTML; the page only shows the live-only contract
and the last synthetic connectivity check when available.
"""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.omija_style import nav_strip  # noqa: E402

OUT_DIR = REPO_ROOT / "out"
PUBLIC_CONTEXT = OUT_DIR / "public_context" / "summary.json"
PRIVATE_META = REPO_ROOT / "data" / "private_candidates" / "collection_meta.json"
OUT_HTML = OUT_DIR / "data_evidence_brief.html"


def e(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def fmt_int(value: Any) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "0"


def first(items: Any) -> dict[str, Any]:
    return items[0] if isinstance(items, list) and items and isinstance(items[0], dict) else {}


def nvd_total(summary: dict[str, Any]) -> int:
    return sum(int(query.get("total_results") or 0) for query in summary.get("nvd", {}).get("queries", []))


def module_status(meta: dict[str, Any]) -> list[tuple[str, str, int, int]]:
    modules = ((meta.get("collection") or {}).get("modules") or {})
    rows: list[tuple[str, str, int, int]] = []
    for name in ("cl", "cds", "cb", "dt", "tt"):
        module = modules.get(name) or {}
        status = module.get("status")
        label = str(status) if status is not None else "n/a"
        rows.append((name.upper(), label, int(module.get("returned") or 0), int(module.get("written") or 0)))
    return rows


def card(title: str, value: str, detail: str, tone: str = "public") -> str:
    return f"""
      <div class="card {e(tone)}">
        <div class="ct">{e(title)}</div>
        <div class="cv">{value}</div>
        <div class="cd">{detail}</div>
      </div>"""


def render_public(summary: dict[str, Any]) -> str:
    kev = summary.get("cisa_kev", {})
    epss = summary.get("first_epss", {})
    attack = summary.get("mitre_attack", {})
    urlhaus = summary.get("urlhaus", {})
    hibp = summary.get("hibp", {})
    advisory_all = (summary.get("cisa_advisories", {}).get("all") or {})

    recent_kev = first(kev.get("recent_access_relevant"))
    top_epss = first(epss.get("sampled"))
    recent_breach = first(hibp.get("recent_breaches"))
    top_technique = first(attack.get("selected_techniques"))
    top_tag = (urlhaus.get("top_tags") or [["n/a", 0]])[0]

    return "".join(
        [
            card(
                "CISA KEV",
                f"{fmt_int(kev.get('access_relevant_count'))} / {fmt_int(kev.get('total_vulnerabilities'))}",
                f"최근 access-relevant 예: {e(recent_kev.get('cveID'))} · {e(recent_kev.get('product'))}",
            ),
            card(
                "NVD asset context",
                fmt_int(nvd_total(summary)),
                "vpn, sso, citrix, fortinet, ivanti 같은 access-surface 키워드 CVE 배경.",
            ),
            card(
                "FIRST EPSS",
                fmt_int(epss.get("high_probability_total")),
                f"상위 예: {e(top_epss.get('cve'))} · EPSS {e(top_epss.get('epss'))}",
            ),
            card(
                "MITRE ATT&CK",
                fmt_int(attack.get("selected_count")),
                f"초기/자격증명 접근 technique 예: {e(top_technique.get('id'))} {e(top_technique.get('name'))}",
            ),
            card(
                "URLhaus aggregate",
                f"{fmt_int(urlhaus.get('stealer_or_loader_count'))} / {fmt_int(urlhaus.get('sampled_rows'))}",
                f"최근 공개 악성 URL 샘플 중 stealer/loader 태그. 최상위 tag: {e(top_tag[0])} ({fmt_int(top_tag[1])})",
            ),
            card(
                "HIBP breach metadata",
                fmt_int(hibp.get("breach_count")),
                f"최근 공개 breach 메타 예: {e(recent_breach.get('Name'))} · {e(recent_breach.get('BreachDate'))} · {fmt_int(recent_breach.get('PwnCount'))} accounts",
            ),
            card(
                "CISA advisory RSS",
                f"{fmt_int(advisory_all.get('access_relevant_count'))} / {fmt_int(advisory_all.get('total_items_sampled'))}",
                "최근 권고 title/link/date만 사용. 피해자·계정·비밀값 없음.",
            ),
        ]
    )


def render_private(meta: dict[str, Any]) -> str:
    rows = module_status(meta)
    row_html = "".join(
        f"<tr><td>{e(name)}</td><td>{e(status)}</td><td>{fmt_int(returned)}</td><td>{fmt_int(written)}</td></tr>"
        for name, status, returned, written in rows
    )
    generated = meta.get("generated_at") or "no local connectivity check"
    seed_id = (meta.get("collection") or {}).get("seed_id") or "none"
    return f"""
      <div class="private-box">
        <div class="box-head">
          <span class="eyebrow">StealthMole sensitive rail</span>
          <strong>민감 데이터는 정적 페이지에 저장하지 않고, 현장 live query 때만 보여준다</strong>
        </div>
        <p>
          아래 표는 <b>합성 seed 연결 체크</b>의 모듈 상태다. 실제 유출 row가 아니며,
          민감 데이터 수집 결과는 GitHub Pages나 out/*.html에 굽지 않는다.
        </p>
        <div class="split">
          <table>
            <thead><tr><th>Module</th><th>Status</th><th>Returned</th><th>Written</th></tr></thead>
            <tbody>{row_html}</tbody>
          </table>
          <div class="policy">
            <div><b>last check</b><span>{e(generated)}</span></div>
            <div><b>seed</b><span>{e(seed_id)}</span></div>
            <div><b>live-only fields</b><span>module, supplier, target asset, account class, has_session_cookie, infected_at, confidence, source_ref hash</span></div>
            <div><b>forbidden</b><span>password, cookie, token, full account dump, raw provider payload</span></div>
          </div>
        </div>
      </div>"""


def render(summary: dict[str, Any], meta: dict[str, Any]) -> str:
    generated = summary.get("generated_at") or "not generated"
    public_cards = render_public(summary)
    private_box = render_private(meta)
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Omija Data Evidence Brief</title>
  <style>
    :root {{ color-scheme: dark; --bg:#0b0c0d; --panel:#151719; --panel2:#1d2024; --line:#333942; --ink:#f2f4f8; --muted:#aeb7c2; --public:#d6a21d; --live:#58a6ff; --good:#2ea043; --warn:#f0b73f; --bad:#f85149; }}
    * {{ box-sizing:border-box; }}
    html,body {{ overflow-x:hidden; }}
    body {{ margin:0; background:var(--bg); color:var(--ink); font:14px/1.48 system-ui,-apple-system,"Segoe UI",sans-serif; }}
    header {{ padding:22px; border-bottom:1px solid var(--line); background:linear-gradient(180deg,#171a1e,#101214); }}
    main {{ padding:18px 22px 42px; display:grid; grid-template-columns:minmax(0,1fr); gap:18px; }}
    .kicker,.eyebrow {{ font:11px ui-monospace,SFMono-Regular,Menlo,monospace; color:var(--muted); letter-spacing:1.2px; text-transform:uppercase; }}
    h1 {{ margin:5px 0 6px; font-size:24px; letter-spacing:0; overflow-wrap:anywhere; }}
    header p,.cd {{ overflow-wrap:anywhere; }}
    h2 {{ margin:0 0 10px; font-size:16px; }}
    p {{ margin:0; color:var(--muted); }}
    a {{ color:var(--live); }}
    .nav {{ display:flex; flex-wrap:wrap; gap:8px; margin-top:14px; }}
    .nav a {{ color:var(--muted); text-decoration:none; border:1px solid var(--line); border-radius:4px; padding:5px 8px; font:11px ui-monospace,SFMono-Regular,Menlo,monospace; }}
    .nav a:hover {{ color:var(--ink); border-color:var(--live); }}
    .grid {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:10px; }}
    .card,.private-box,.flow {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:13px; }}
    .card {{ border-left:3px solid var(--public); min-height:126px; }}
    .ct {{ color:var(--muted); font:11px ui-monospace,SFMono-Regular,Menlo,monospace; text-transform:uppercase; letter-spacing:.8px; }}
    .cv {{ margin:5px 0; color:var(--ink); font:24px ui-monospace,SFMono-Regular,Menlo,monospace; }}
    .cd {{ color:var(--muted); font-size:12px; }}
    .box-head {{ display:grid; gap:3px; margin-bottom:10px; }}
    .box-head strong {{ font-size:16px; }}
    .split {{ display:grid; grid-template-columns:1.05fr 1fr; gap:12px; margin-top:12px; align-items:start; }}
    table {{ width:100%; border-collapse:collapse; background:var(--panel2); border:1px solid var(--line); border-radius:6px; overflow:hidden; }}
    th,td {{ padding:8px 9px; border-bottom:1px solid var(--line); text-align:left; font-size:12px; }}
    th {{ color:var(--muted); font:10px ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:.8px; text-transform:uppercase; }}
    td:first-child {{ color:var(--ink); font-family:ui-monospace,SFMono-Regular,Menlo,monospace; }}
    .policy {{ display:grid; gap:8px; }}
    .policy div {{ display:grid; grid-template-columns:130px 1fr; gap:9px; padding:8px; border:1px solid var(--line); border-radius:6px; background:var(--panel2); }}
    .policy b {{ color:var(--ink); font-size:12px; }}
    .policy span {{ color:var(--muted); font-size:12px; overflow-wrap:anywhere; }}
    .flow-grid {{ display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:8px; }}
    .step {{ border:1px solid var(--line); border-radius:7px; background:var(--panel2); padding:10px; min-height:96px; }}
    .step b {{ display:block; margin-bottom:5px; color:var(--ink); }}
    .step span {{ color:var(--muted); font-size:12px; }}
    .note {{ border:1px solid color-mix(in srgb,var(--warn) 48%,var(--line)); border-left:4px solid var(--warn); border-radius:8px; padding:12px; background:#17130a; color:#f3d58b; }}
    @media (max-width:900px) {{ .grid,.split,.flow-grid {{ grid-template-columns:1fr; }} .policy div {{ grid-template-columns:1fr; }} }}
    @media (max-width:560px) {{
      main {{ padding:16px 14px; }}
      h1 {{ font-size:20px; }}
      .split table {{ display:block; overflow-x:auto; white-space:nowrap; }}
    }}
  </style>
</head>
<body>
  {nav_strip("data_evidence_brief.html")}
  <header>
    <div class="kicker">OMIJA DATA EVIDENCE BRIEF</div>
    <h1>데이터는 이렇게 쓴다: 공개 OSINT는 정적 근거, 민감 유출 신호는 live-only</h1>
    <p>Generated from <code>out/public_context/summary.json</code> at <code>{e(generated)}</code>. 공개 데이터는 실제 스냅샷이고, StealthMole 민감 row는 정적 페이지에 저장하지 않는다.</p>
    <div class="nav">
      <a href="index.html">평시 콘솔</a>
      <a href="omija_demo.html">사건 보고서</a>
      <a href="data_coverage_map.html">커버리지 맵</a>
      <a href="program_threat_view.html">프로그램 뷰</a>
      <a href="public_context_matrix.html">공개데이터 매트릭스</a>
    </div>
  </header>
  <main>
    <section>
      <h2>실제 공개 데이터 예시</h2>
      <div class="grid">{public_cards}</div>
    </section>
    <section>{private_box}</section>
    <section class="flow">
      <h2>온톨로지에 들어가면 이렇게 쓰인다</h2>
      <div class="flow-grid">
        <div class="step"><b>1. Public context</b><span>KEV/NVD/EPSS/ATT&CK은 Domain.asset_type과 RiskAssessment.components를 설명한다.</span></div>
        <div class="step"><b>2. Live sensitive signal</b><span>발표 중 승인된 query만 즉시 실행. 결과는 count/schema/sanitized preview만 표시.</span></div>
        <div class="step"><b>3. Normalize boundary</b><span>raw secret 폐기, source_ref 보존, identity/target asset 후보로 분리.</span></div>
        <div class="step"><b>4. Graph reasoning</b><span>of, targets, subcontractsTo, traverses_* 링크로 공급망 경로를 만든다.</span></div>
        <div class="step"><b>5. Decision objects</b><span>RiskAssessment, CompromiseIncident, ProgramExposure, NotificationDraft가 human review로 이어진다.</span></div>
      </div>
    </section>
    <div class="note">심사장 설명: 실제 유출 원문을 보여주는 것이 아니라, 공개 데이터는 근거로, 민감 feed는 live-only 경계로, 온톨로지는 판단 엔진으로 분리한다. 이것이 안전성과 실전성을 동시에 만족시키는 구조다.</div>
  </main>
</body>
</html>"""


def main() -> int:
    summary = read_json(PUBLIC_CONTEXT)
    meta = read_json(PRIVATE_META)
    OUT_HTML.write_text(render(summary, meta), encoding="utf-8")
    print(f"wrote {OUT_HTML.relative_to(REPO_ROOT)}")
    print("RESULT: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
