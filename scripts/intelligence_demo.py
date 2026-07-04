"""Generate ontology-engine demo pages without touching live data.

Owner directive, 2026-07-05:
- do not connect to StealthMole;
- do not fetch public feeds;
- do not handle sensitive records;
- show the ontology-centered decision engine with empty candidate slots.
"""

from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "out"
OUT_JSON = OUT_DIR / "intelligence_demo.json"
OUT_HTML = OUT_DIR / "intelligence_demo.html"
OUT_CORE = OUT_DIR / "omija_console_core.html"
OUT_GRAPH = OUT_DIR / "omija_console_graph.html"
OUT_RESPONSE = OUT_DIR / "omija_console_response.html"


OBJECT_TYPES = [
    ("Supplier", "Supply-chain organization", "No live organization loaded"),
    ("Prime", "Prime or tier-0 program owner", "Kept separate for v0.2"),
    ("Program", "Protected mission or contract scope", "Impact endpoint"),
    ("Domain", "Asset-lite access surface", "fqdn and asset_type only"),
    ("Identity", "Account handle or principal", "No credential value stored"),
    ("CredentialExposure", "Potential exposure signal", "Candidate slot only"),
    ("InfectedDevice", "Infostealer device signal", "Candidate slot only"),
    ("ThreatSource", "Collection provenance", "Neutralized live source"),
    ("RiskAssessment", "Supplier risk decision", "Derived object"),
    ("CompromiseIncident", "Active path case", "Derived object"),
    ("ProgramExposure", "Program rollup", "Derived object"),
    ("NotificationDraft", "Human-reviewed advisory", "Draft only"),
]

LINK_TYPES = [
    ("of", "CredentialExposure", "Identity", "Whose account is involved"),
    ("targets", "CredentialExposure", "Domain", "What access surface is involved"),
    ("belongs_to", "Identity", "Domain", "Account ownership context"),
    ("owns", "Supplier", "Domain", "Supplier-operated asset"),
    ("subcontractsTo", "Supplier", "Supplier", "Recursive supply-chain path"),
    ("supplies", "Supplier", "Prime", "Supplier to prime relationship"),
    ("runs", "Prime", "Program", "Prime to protected program"),
    ("traverses_*", "CompromiseIncident", "Path nodes", "Audit drill-down"),
    ("cites", "NotificationDraft", "Evidence objects", "Draft provenance"),
]

DECISION_STEPS = [
    (
        "1",
        "Collect Candidate Signal",
        "Input slot is intentionally empty. No feed data is pulled in this build.",
    ),
    (
        "2",
        "Resolve Identity And Target",
        "`of` and `targets` remain separate so cross-organization access is visible.",
    ),
    (
        "3",
        "Traverse Supplier Path",
        "`Supplier -> Supplier -> Prime -> Program` explains blast radius.",
    ),
    (
        "4",
        "Create Decision Objects",
        "`RiskAssessment`, `CompromiseIncident`, and `ProgramExposure` hold the decision.",
    ),
    (
        "5",
        "Prepare Human Review",
        "`NotificationDraft` is never sent automatically.",
    ),
]

POLICY_GATES = [
    ("Live credential feed", "Disabled", "Code boundary intentionally empty"),
    ("Public feed fetching", "Disabled", "Use candidate slots, not direct collection"),
    ("Raw secrets", "Blocked", "No password, cookie, JWT, or bearer token storage"),
    ("Notification sending", "Blocked", "Draft only, human approval required"),
]


def e(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def build_payload() -> dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "ontology_engine_no_live_data",
        "claim_boundary": {
            "live_credential_feed": "disabled",
            "public_feed_collection": "disabled",
            "sensitive_data_handling": "blocked",
            "demo_data": "empty candidate slots only",
        },
        "object_types": [
            {"name": name, "purpose": purpose, "state": state}
            for name, purpose, state in OBJECT_TYPES
        ],
        "link_types": [
            {"name": name, "from": src, "to": dst, "purpose": purpose}
            for name, src, dst, purpose in LINK_TYPES
        ],
        "decision_steps": [
            {"order": order, "name": name, "purpose": purpose}
            for order, name, purpose in DECISION_STEPS
        ],
        "policy_gates": [
            {"surface": surface, "state": state, "reason": reason}
            for surface, state, reason in POLICY_GATES
        ],
    }


def table(headers: list[str], rows: list[list[Any]]) -> str:
    header_html = "".join(f"<th>{e(item)}</th>" for item in headers)
    row_html = []
    for row in rows:
        row_html.append(
            "<tr>" + "".join(f"<td>{e(item)}</td>" for item in row) + "</tr>"
        )
    return (
        f"<table><thead><tr>{header_html}</tr></thead>"
        f"<tbody>{''.join(row_html)}</tbody></table>"
    )


def render_shell(title: str, subtitle: str, body: str, active: str) -> str:
    nav = [
        ("Core Console", OUT_CORE.name, "core"),
        ("Graph Workbench", OUT_GRAPH.name, "graph"),
        ("Response Review", OUT_RESPONSE.name, "response"),
    ]
    nav_html = "".join(
        f"<a class='nav {'active' if key == active else ''}' href='{e(href)}'>{e(label)}</a>"
        for label, href, key in nav
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<style>
:root {{
  color-scheme: light;
  --ink: #111827;
  --muted: #5b6472;
  --line: #d7dde8;
  --panel: #ffffff;
  --bg: #f3f5f8;
  --blue: #174ea6;
  --blue-soft: #eef4ff;
  --red: #b42318;
  --red-soft: #fff3f0;
  --green: #067647;
  --green-soft: #ecfdf3;
  --amber: #946200;
  --amber-soft: #fff7df;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  background: var(--bg);
  color: var(--ink);
  font: 14px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}}
header {{
  background: #111827;
  color: white;
  padding: 16px 24px;
  border-bottom: 4px solid var(--blue);
}}
main {{ max-width: 1380px; margin: 0 auto; padding: 18px 24px 28px; }}
h1 {{ margin: 8px 0 4px; font-size: 25px; letter-spacing: 0; }}
h2 {{ margin: 0 0 10px; font-size: 13px; letter-spacing: 0; text-transform: uppercase; }}
p {{ margin: 0 0 10px; }}
.sub {{ color: var(--muted); }}
.kicker {{ color: #cbd5e1; font-size: 12px; font-weight: 800; }}
.tabs {{ display: flex; gap: 8px; margin-top: 14px; flex-wrap: wrap; }}
.nav {{
  color: #dbe4ef;
  border: 1px solid #334155;
  border-radius: 5px;
  padding: 6px 10px;
  text-decoration: none;
  font-weight: 700;
}}
.nav.active {{ background: white; color: #111827; }}
.grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }}
.layout {{ display: grid; grid-template-columns: minmax(0, 1.35fr) minmax(340px, .9fr); gap: 14px; }}
.panel, .metric {{
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 16px;
  margin-bottom: 14px;
}}
.metric strong {{ display: block; font-size: 24px; margin-top: 6px; }}
.metric span {{ color: var(--muted); font-size: 12px; font-weight: 800; }}
.badge {{
  display: inline-flex;
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 4px 8px;
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
}}
.badge.blocked {{ background: var(--red-soft); border-color: #fecdca; color: var(--red); }}
.badge.ready {{ background: var(--green-soft); border-color: #abefc6; color: var(--green); }}
.badge.hold {{ background: var(--amber-soft); border-color: #fedf89; color: var(--amber); }}
.chain {{ display: grid; grid-template-columns: repeat(5, minmax(120px, 1fr)); gap: 8px; }}
.node {{
  min-height: 106px;
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 10px;
  background: white;
}}
.node.core {{ background: var(--blue-soft); border-color: #b2ddff; }}
.node.empty {{ background: #fafafa; border-style: dashed; }}
.node .type {{ display: block; color: var(--muted); font-size: 11px; font-weight: 800; text-transform: uppercase; }}
.node .name {{ display: block; font-weight: 850; margin-top: 5px; }}
.node .detail {{ display: block; color: var(--muted); font-size: 12px; margin-top: 4px; }}
table {{ width: 100%; border-collapse: collapse; }}
th, td {{ border-bottom: 1px solid var(--line); padding: 8px 7px; text-align: left; vertical-align: top; }}
th {{ color: var(--muted); font-size: 12px; text-transform: uppercase; }}
.mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px; }}
@media (max-width: 980px) {{
  main {{ padding: 14px; }}
  .grid, .layout, .chain {{ grid-template-columns: 1fr; }}
}}
</style>
</head>
<body>
<header>
  <div class="kicker">OMIJA ONTOLOGY ENGINE - NO LIVE DATA MODE</div>
  <h1>{e(title)}</h1>
  <p>{e(subtitle)}</p>
  <nav class="tabs">{nav_html}</nav>
</header>
<main>{body}</main>
</body>
</html>"""


def render_core(payload: dict[str, Any]) -> str:
    metrics = [
        ("Live Data", "Disabled"),
        ("Sensitive Handling", "Blocked"),
        ("Ontology Core", "Ready"),
        ("Action Output", "Draft Only"),
    ]
    metric_html = "".join(
        f"<div class='metric'><span>{e(label)}</span><strong>{e(value)}</strong></div>"
        for label, value in metrics
    )
    gate_rows = [
        [item["surface"], item["state"], item["reason"]]
        for item in payload["policy_gates"]
    ]
    step_rows = [
        [step["order"], step["name"], step["purpose"]]
        for step in payload["decision_steps"]
    ]
    body = f"""
<section class="grid">{metric_html}</section>
<div class="layout">
  <section class="panel">
    <h2>Problem Solving Spine</h2>
    <p class="sub">The page shows how the ontology engine turns a candidate
    exposure into a supplier, program, risk, incident, and draft-review workflow.
    Evidence slots are intentionally empty.</p>
    {table(["Step", "Engine Function", "Why It Matters"], step_rows)}
  </section>
  <aside class="panel">
    <h2>Policy Gates</h2>
    {table(["Surface", "State", "Reason"], gate_rows)}
  </aside>
</div>
"""
    return render_shell(
        "Ontology Core Console",
        "A Palantir-style operating surface for the supply-chain exposure problem, without live data ingestion.",
        body,
        "core",
    )


def render_graph(payload: dict[str, Any]) -> str:
    link_rows = [
        [link["name"], link["from"], link["to"], link["purpose"]]
        for link in payload["link_types"]
    ]
    body = f"""
<section class="panel">
  <h2>Empty Candidate Path</h2>
  <div class="chain">
    <div class="node empty"><span class="type">Candidate Signal</span><span class="name">Empty</span><span class="detail">No feed data loaded</span></div>
    <div class="node core"><span class="type">Identity</span><span class="name">Resolved by `of`</span><span class="detail">Whose account</span></div>
    <div class="node core"><span class="type">Target Asset</span><span class="name">Resolved by `targets`</span><span class="detail">What access surface</span></div>
    <div class="node core"><span class="type">Supplier Path</span><span class="name">Supplier to Prime</span><span class="detail">Recursive graph path</span></div>
    <div class="node core"><span class="type">Program Impact</span><span class="name">ProgramExposure</span><span class="detail">Decision endpoint</span></div>
  </div>
</section>
<section class="panel">
  <h2>Ontology Links</h2>
  {table(["Link", "From", "To", "Purpose"], link_rows)}
</section>
"""
    return render_shell(
        "Investigation Graph Workbench",
        "The graph is ready for candidate evidence, but no evidence is loaded or displayed.",
        body,
        "graph",
    )


def render_response(payload: dict[str, Any]) -> str:
    object_rows = [
        [item["name"], item["purpose"], item["state"]]
        for item in payload["object_types"]
    ]
    body = f"""
<section class="panel">
  <h2>Decision Object Registry</h2>
  <p class="sub">Derived decisions are objects, not loose dashboard numbers.
  This keeps review, provenance, and lifecycle state explicit.</p>
  {table(["Object Type", "Purpose", "Current State"], object_rows)}
</section>
<section class="panel">
  <h2>Human Review Output</h2>
  <p><span class="badge hold">Draft only</span></p>
  <p class="sub">Notification text, recipient details, and evidence citations
  are candidate slots. They remain blank until an approved non-sensitive
  evidence package is available.</p>
</section>
"""
    return render_shell(
        "Response Review Surface",
        "Decision objects and draft outputs are prepared, but no sensitive record is handled.",
        body,
        "response",
    )


def main() -> int:
    payload = build_payload()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    core_html = render_core(payload)
    OUT_CORE.write_text(core_html, encoding="utf-8")
    OUT_GRAPH.write_text(render_graph(payload), encoding="utf-8")
    OUT_RESPONSE.write_text(render_response(payload), encoding="utf-8")
    OUT_HTML.write_text(core_html, encoding="utf-8")
    print(f"wrote {OUT_JSON.relative_to(REPO_ROOT)}")
    print(f"wrote {OUT_HTML.relative_to(REPO_ROOT)}")
    print(f"wrote {OUT_CORE.relative_to(REPO_ROOT)}")
    print(f"wrote {OUT_GRAPH.relative_to(REPO_ROOT)}")
    print(f"wrote {OUT_RESPONSE.relative_to(REPO_ROOT)}")
    print("RESULT: READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
