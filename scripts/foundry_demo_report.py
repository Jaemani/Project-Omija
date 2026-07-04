"""Generate a Foundry-backed static demo report.

Design direction from Opus review: lead with severity and program impact, keep
the active path centered, show provenance chips, and keep raw records secondary.
"""

from __future__ import annotations

import html
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "out"
OUT_HTML = OUT_DIR / "foundry_demo.html"
sys.path.insert(0, str(REPO_ROOT))

from store.foundry import FoundryOntologyStore  # noqa: E402


CSS = """
:root {
  color-scheme: light;
  --ink: #172033;
  --muted: #596276;
  --line: #d9dee8;
  --paper: #f7f8fb;
  --panel: #ffffff;
  --danger: #b42318;
  --danger-soft: #fffbfa;
  --blue: #175cd3;
  --blue-soft: #eff8ff;
  --green: #067647;
  --green-soft: #ecfdf3;
  --amber: #b54708;
}
* {
  box-sizing: border-box;
}
body {
  margin: 0;
  font: 14px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  color: var(--ink);
  background: var(--paper);
}
header {
  background: var(--panel);
  border-bottom: 1px solid var(--line);
  padding: 22px 28px 16px;
}
main {
  max-width: 1280px;
  margin: 0 auto;
  padding: 18px 28px 30px;
}
.eyebrow {
  color: var(--muted);
  font-size: 12px;
  letter-spacing: 0;
  text-transform: uppercase;
}
h1 {
  margin: 4px 0 6px;
  font-size: 26px;
  line-height: 1.15;
  letter-spacing: 0;
}
h2 {
  margin: 0 0 10px;
  font-size: 15px;
  letter-spacing: 0;
}
p {
  margin: 0;
}
.sub {
  color: var(--muted);
  max-width: 900px;
}
.impact {
  display: grid;
  grid-template-columns: minmax(220px, 1.1fr) repeat(3, minmax(150px, .7fr));
  gap: 12px;
  margin-bottom: 14px;
}
.metric,
.panel {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
}
.metric {
  min-height: 92px;
  padding: 14px;
}
.metric.severity {
  border-left: 4px solid var(--danger);
}
.metric .label {
  color: var(--muted);
  display: block;
  font-size: 12px;
}
.metric strong {
  display: block;
  font-size: 24px;
  margin-top: 6px;
}
.metric.severity strong {
  color: var(--danger);
}
.workspace {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(300px, .85fr);
  gap: 14px;
  align-items: start;
}
.panel {
  padding: 16px;
}
.decision {
  min-height: 290px;
}
.chain {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 12px 0;
}
.node {
  align-items: center;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 6px;
  display: inline-flex;
  font-weight: 650;
  min-height: 34px;
  padding: 7px 10px;
  white-space: nowrap;
}
.node.supplier {
  border-color: #fecdca;
  color: var(--danger);
}
.node.prime {
  border-color: #b2ddff;
  color: var(--blue);
}
.node.program {
  border-color: #abefc6;
  color: var(--green);
}
.arrow {
  color: var(--muted);
  font-size: 18px;
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}
.chip {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 999px;
  color: var(--muted);
  font-size: 12px;
  padding: 6px 9px;
}
.chip.hot {
  background: var(--danger-soft);
  border-color: #fecdca;
  color: var(--danger);
}
.chip.blue {
  background: var(--blue-soft);
  border-color: #b2ddff;
  color: var(--blue);
}
.chip.green {
  background: var(--green-soft);
  border-color: #abefc6;
  color: var(--green);
}
.paths,
.programs {
  margin: 8px 0 0;
  padding-left: 18px;
}
.paths {
  list-style: none;
  padding-left: 0;
}
.paths li {
  margin-top: 8px;
}
.draft {
  background: #fbfcff;
  border: 1px solid var(--line);
  border-radius: 8px;
  color: #30384a;
  margin-top: 8px;
  max-height: 260px;
  overflow: auto;
  padding: 12px;
  white-space: pre-wrap;
}
details {
  margin-top: 14px;
}
summary {
  color: var(--blue);
  cursor: pointer;
  font-weight: 650;
}
table {
  border-collapse: collapse;
  margin-top: 10px;
  width: 100%;
}
th,
td {
  border-bottom: 1px solid var(--line);
  padding: 8px;
  text-align: left;
  vertical-align: top;
}
th {
  color: var(--muted);
  font-size: 12px;
  font-weight: 650;
}
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12px;
}
@media (max-width: 900px) {
  header,
  main {
    padding-left: 16px;
    padding-right: 16px;
  }
  .impact,
  .workspace {
    grid-template-columns: 1fr;
  }
  h1 {
    font-size: 22px;
  }
}
"""


def e(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def chain_nodes(path: str) -> list[str]:
    return [part.strip() for part in path.split("->") if part.strip()]


def node_class(ref: str) -> str:
    if ref.startswith("prog-"):
        return "program"
    if ref.startswith("prime-"):
        return "prime"
    if ref.startswith("sup-"):
        return "supplier"
    return "neutral"


def render_chain(path: str) -> str:
    nodes = chain_nodes(path)
    if not nodes:
        return '<span class="node neutral">No path</span>'

    parts: list[str] = []
    for index, node in enumerate(nodes):
        parts.append(f'<span class="node {node_class(node)}">{e(node)}</span>')
        if index < len(nodes) - 1:
            parts.append('<span class="arrow">&rarr;</span>')
    return "".join(parts)


def path_label(path: list[dict[str, Any]]) -> str:
    return " -> ".join(str(node.get("ref")) for node in path if node.get("ref"))


def unique_programs(paths: list[list[dict[str, Any]]]) -> list[str]:
    return sorted(
        {
            str(node["ref"])
            for path in paths
            for node in path
            if node.get("type") == "Program" and node.get("ref")
        }
    )


def render_report(supplier_id: str = "sup-h") -> str:
    store = FoundryOntologyStore()
    try:
        suppliers = {row["id"]: row for row in store.suppliers()}
        supplier = suppliers.get(supplier_id, {"id": supplier_id, "name": supplier_id})
        paths_raw = store.propagation_paths(supplier_id)
        exposures = store.exposures_for_supplier(supplier_id)
        incidents = store.incidents_for_supplier(supplier_id)
        draft = store.draft_for_supplier(supplier_id) or {}
    finally:
        close = getattr(store, "close", None)
        if close:
            close()

    paths = [path_label(path) for path in paths_raw]
    programs = unique_programs(paths_raw)
    incident = incidents[0] if incidents else {}
    exposure = exposures[0] if exposures else {}

    risk_band = incident.get("risk_band") or "A"
    path_confidence = incident.get("path_confidence") or "-"
    primary_path = paths[0] if paths else supplier_id
    supplier_name = supplier.get("name") or supplier_id

    program_items = "".join(f"<li>{e(program)}</li>" for program in programs) or "<li>No reachable program</li>"
    path_rows = "".join(f"<li>{render_chain(path)}</li>" for path in paths) or "<li>No path</li>"
    exposure_rows = "".join(
        "<tr>"
        f"<td class=\"mono\">{e(row.get('id'))}</td>"
        f"<td>{e(row.get('identity_ref'))}</td>"
        f"<td>{e(row.get('domain_ref'))}</td>"
        f"<td>{e(row.get('target_domain_ref'))}</td>"
        f"<td>{e(row.get('source_ref'))}</td>"
        f"<td>{e(row.get('masked_value'))}</td>"
        "</tr>"
        for row in exposures
    )
    if not exposure_rows:
        exposure_rows = '<tr><td colspan="6">No exposure rows found.</td></tr>'

    cookie_chip = '<span class="chip hot">session cookie</span>' if exposure.get("has_session_cookie") else ""
    draft_body = draft.get("body") or "No notification draft found."
    incident_id = incident.get("id") or "none"
    draft_id = draft.get("id") or "none"

    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Project Omija Foundry Demo</title>
  <style>{CSS}</style>
</head>
<body>
  <header>
    <div class="eyebrow">Project Omija · Foundry Ontology + Python OSDK</div>
    <h1>{e(supplier_name)} active compromise reaches defense programs</h1>
    <p class="sub">Foundry seed read through OSDK. This screen proves the decision path, not a flat leaked-credential table.</p>
  </header>

  <main>
    <section class="impact" aria-label="Impact summary">
      <div class="metric severity"><span class="label">Risk band</span><strong>{e(risk_band)}</strong></div>
      <div class="metric"><span class="label">Impacted programs</span><strong>{len(programs)}</strong></div>
      <div class="metric"><span class="label">Evidence records</span><strong>{len(exposures)}</strong></div>
      <div class="metric"><span class="label">Path confidence</span><strong>{e(path_confidence)}</strong></div>
    </section>

    <div class="workspace">
      <section class="panel decision">
        <h2>Active Path</h2>
        <p class="sub">Credential exposure belongs to the supplier identity, while the target asset belongs upstream.</p>
        <div class="chain">{render_chain(primary_path)}</div>
        <div class="chips">
          {cookie_chip}
          <span class="chip">identity: {e(exposure.get("identity_ref"))}</span>
          <span class="chip">owner domain: {e(exposure.get("domain_ref"))}</span>
          <span class="chip blue">target: {e(exposure.get("target_domain_ref"))}</span>
          <span class="chip">source: {e(exposure.get("source_ref"))}</span>
        </div>
        <details open>
          <summary>All reachable paths</summary>
          <ul class="paths">{path_rows}</ul>
        </details>
      </section>

      <section class="panel">
        <h2>Program Impact</h2>
        <p class="sub">Tiered supplier exposure rolls up to protected programs through ontology links.</p>
        <ul class="programs">{program_items}</ul>

        <h2 style="margin-top:18px">Notification Draft</h2>
        <div class="draft">{e(draft_body)}</div>
      </section>
    </div>

    <section class="panel" style="margin-top:14px">
      <h2>Provenance</h2>
      <div class="chips">
        <span class="chip hot">incident: {e(incident_id)}</span>
        <span class="chip green">draft: {e(draft_id)}</span>
        <span class="chip">supplier: {e(supplier_id)}</span>
      </div>
      <details>
        <summary>Raw record view</summary>
        <table>
          <thead>
            <tr>
              <th>exposure</th>
              <th>identity</th>
              <th>owner domain</th>
              <th>target</th>
              <th>source</th>
              <th>masked secret</th>
            </tr>
          </thead>
          <tbody>{exposure_rows}</tbody>
        </table>
      </details>
    </section>
  </main>
</body>
</html>"""


def main(argv: list[str] | None = None) -> int:
    supplier_id = argv[0] if argv else "sup-h"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(render_report(supplier_id), encoding="utf-8")
    print(f"wrote {OUT_HTML.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
