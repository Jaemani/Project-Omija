"""Generate a Foundry-backed static demo report.

Design changes here are limited to the Opus review received for the final demo:
incident bar, risk/confidence first, labeled path edges, clear origin/program
endpoints, visible provenance, and an unsent approval-gated draft.
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
  --critical: #b42318;
  --critical-soft: #fffbfa;
  --program: #175cd3;
  --program-soft: #eff8ff;
  --ok: #067647;
  --ok-soft: #ecfdf3;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font: 14px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  color: var(--ink);
  background: var(--paper);
}
header {
  background: var(--panel);
  border-bottom: 1px solid var(--line);
  padding: 18px 28px 16px;
}
main {
  max-width: 1280px;
  margin: 0 auto;
  padding: 18px 28px 30px;
}
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12px;
}
.incident-bar {
  align-items: center;
  color: var(--muted);
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}
.status-pill,
.tag,
.chip {
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  white-space: nowrap;
}
.status-pill {
  background: var(--critical-soft);
  border: 1px solid #fecdca;
  color: var(--critical);
  font-size: 11px;
  font-weight: 700;
  padding: 4px 8px;
  text-transform: uppercase;
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
p { margin: 0; }
.sub {
  color: var(--muted);
  max-width: 900px;
}
.impact {
  display: grid;
  grid-template-columns: minmax(240px, 1fr) repeat(3, minmax(150px, .65fr));
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
  min-height: 104px;
  padding: 14px;
}
.metric.severity { border-left: 4px solid var(--critical); }
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
.metric small {
  color: var(--muted);
  display: block;
  margin-top: 6px;
}
.metric.severity strong { color: var(--critical); }
.workspace {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(300px, .85fr);
  gap: 14px;
  align-items: start;
}
.panel { padding: 16px; }
.decision { min-height: 310px; }
.chain {
  align-items: stretch;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  margin: 14px 0;
}
.node {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 6px;
  min-width: 150px;
  padding: 9px 10px;
}
.node .type {
  color: var(--muted);
  display: block;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
}
.node .name {
  display: block;
  font-weight: 700;
  margin-top: 2px;
}
.node .qualifier {
  color: var(--muted);
  display: block;
  font-size: 12px;
  margin-top: 2px;
}
.node.supplier.origin {
  background: var(--critical-soft);
  border-color: #fecdca;
}
.node.prime { border-color: #b2ddff; }
.node.program {
  background: var(--program-soft);
  border-color: #b2ddff;
}
.edge {
  align-items: center;
  color: var(--muted);
  display: flex;
  flex-direction: column;
  font-size: 11px;
  justify-content: center;
  min-width: 72px;
}
.edge .arrow {
  color: var(--muted);
  font-size: 18px;
  line-height: 1;
}
.tag {
  border: 1px solid var(--line);
  color: var(--muted);
  font-size: 11px;
  gap: 4px;
  margin-top: 6px;
  padding: 4px 7px;
}
.tag.hot {
  border-color: #fecdca;
  color: var(--critical);
}
.tag.program {
  border-color: #b2ddff;
  color: var(--program);
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
  color: var(--muted);
  font-size: 12px;
  padding: 6px 9px;
}
.chip.hot {
  background: var(--critical-soft);
  border-color: #fecdca;
  color: var(--critical);
}
.chip.blue {
  background: var(--program-soft);
  border-color: #b2ddff;
  color: var(--program);
}
.chip.green {
  background: var(--ok-soft);
  border-color: #abefc6;
  color: var(--ok);
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
.paths li { margin-top: 8px; }
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
details { margin-top: 14px; }
summary {
  color: var(--program);
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
  .chain {
    justify-content: flex-start;
  }
  h1 { font-size: 22px; }
}
"""


def e(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


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


def edge_label(left: dict[str, Any], right: dict[str, Any]) -> str:
    pair = (left.get("type"), right.get("type"))
    if pair == ("Supplier", "Supplier"):
        return "subcontractsTo"
    if pair == ("Supplier", "Prime"):
        return "supplies"
    if pair == ("Prime", "Program"):
        return "runs"
    return "links"


def node_qualifier(node: dict[str, Any], index: int, last_index: int) -> str:
    node_type = node.get("type")
    if index == 0:
        return "credential exposed"
    if node_type == "Supplier":
        return "supplier hop"
    if node_type == "Prime":
        return "prime contractor"
    if node_type == "Program":
        return "crown-jewel program"
    return "on path"


def node_class(node: dict[str, Any], index: int, last_index: int) -> str:
    classes = [str(node.get("type", "node")).lower()]
    if index == 0:
        classes.append("origin")
    if index == last_index:
        classes.append("endpoint")
    return " ".join(classes)


def render_path(path: list[dict[str, Any]]) -> str:
    if not path:
        return '<span class="node"><span class="name">No path</span></span>'

    parts: list[str] = []
    last_index = len(path) - 1
    for index, node in enumerate(path):
        ref = str(node.get("ref") or "")
        display = node.get("name") or ref
        tag = ""
        if index == 0:
            tag = '<span class="tag hot">compromised origin</span>'
        elif index == last_index:
            tag = '<span class="tag program">target program</span>'
        parts.append(
            f'<div class="node {node_class(node, index, last_index)}">'
            f'<span class="type">{e(node.get("type"))}</span>'
            f'<span class="name">{e(display)}</span>'
            f'<span class="qualifier mono">{e(ref)}</span>'
            f'<span class="qualifier">{e(node_qualifier(node, index, last_index))}</span>'
            f"{tag}</div>"
        )
        if index < last_index:
            parts.append(
                '<div class="edge">'
                '<span class="arrow">&rarr;</span>'
                f'<span class="mono">{e(edge_label(node, path[index + 1]))}</span>'
                "</div>"
            )
    return "".join(parts)


def render_compact_path(path: str) -> str:
    return e(path).replace(" -&gt; ", ' <span class="mono">-&gt;</span> ')


def score_text(value: Any) -> str:
    if value is None or value == "":
        return "-"
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return str(value)


def render_report(supplier_id: str = "sup-h") -> str:
    store = FoundryOntologyStore()
    try:
        suppliers = {row["id"]: row for row in store.suppliers()}
        supplier = suppliers.get(supplier_id, {"id": supplier_id, "name": supplier_id})
        paths_raw = store.propagation_paths(supplier_id)
        exposures = store.exposures_for_supplier(supplier_id)
        incidents = store.incidents_for_supplier(supplier_id)
        risk = next(
            (row for row in store.risk_assessments() if row.get("supplier_ref") == supplier_id),
            {},
        )
        draft = store.draft_for_supplier(supplier_id) or {}
    finally:
        close = getattr(store, "close", None)
        if close:
            close()

    paths = [path_label(path) for path in paths_raw]
    programs = unique_programs(paths_raw)
    incident = incidents[0] if incidents else {}
    exposure = exposures[0] if exposures else {}

    risk_band = incident.get("risk_band") or risk.get("risk_band") or "A"
    risk_score = score_text(risk.get("score"))
    path_confidence = score_text(incident.get("path_confidence"))
    supplier_name = supplier.get("name") or supplier_id
    primary_path = paths_raw[0] if paths_raw else []
    opened_at = incident.get("opened_at") or risk.get("computed_at") or "unknown time"
    incident_status = incident.get("status") or "open"
    evidence_count = len(exposures)
    record_count = len(exposures) + len(incidents) + (1 if draft else 0)
    source_count = len({row.get("source_ref") for row in exposures if row.get("source_ref")})

    risk_driver = "active path to program, credential verified"
    program_items = "".join(f"<li>{e(program)}</li>" for program in programs) or "<li>No reachable program</li>"
    path_rows = "".join(f"<li>{render_compact_path(path)}</li>" for path in paths) or "<li>No path</li>"
    exposure_rows = "".join(
        "<tr>"
        f'<td class="mono">{e(row.get("id"))}</td>'
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
    draft_status = draft.get("status") or "draft"

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
    <div class="incident-bar mono">
      <span>{e(incident_id)}</span>
      <span>{e(opened_at)}</span>
      <span>owner {e(supplier_id)}</span>
      <span class="status-pill">{e(incident_status)}</span>
    </div>
    <div class="eyebrow">Project Omija · Foundry Ontology + Python OSDK</div>
    <h1>{e(supplier_name)} active compromise reaches defense programs</h1>
    <p class="sub">Synthetic Foundry seed read through OSDK. This screen proves the decision path, not a flat leaked-credential table.</p>
  </header>

  <main>
    <section class="impact" aria-label="Impact summary">
      <div class="metric severity">
        <span class="label">Risk band</span>
        <strong>{e(risk_band)} · {e(risk_score)}</strong>
        <small>{e(risk_driver)}</small>
      </div>
      <div class="metric">
        <span class="label">Path confidence</span>
        <strong>{e(path_confidence)}</strong>
        <small>source: {e(incident_id)}</small>
      </div>
      <div class="metric">
        <span class="label">Impacted programs</span>
        <strong>{len(programs)}</strong>
        <small>via supplier-to-prime chain</small>
      </div>
      <div class="metric">
        <span class="label">Evidence records</span>
        <strong>{evidence_count}</strong>
        <small>{record_count} records · {source_count or 0} sources</small>
      </div>
    </section>

    <div class="workspace">
      <section class="panel decision">
        <h2>Active Path</h2>
        <p class="sub">Credential exposure belongs to the supplier identity, while the target asset belongs upstream.</p>
        <div class="chain">{render_path(primary_path)}</div>
        <div class="chips">
          {cookie_chip}
          <span class="chip">identity: {e(exposure.get("identity_ref"))}</span>
          <span class="chip">owner domain: {e(exposure.get("domain_ref"))}</span>
          <span class="chip blue">target: {e(exposure.get("target_domain_ref"))}</span>
          <span class="chip">source: {e(exposure.get("source_ref"))}</span>
        </div>
        <details open>
          <summary>All reachable paths ({len(paths)})</summary>
          <ul class="paths">{path_rows}</ul>
        </details>
      </section>

      <section class="panel">
        <h2>Program Impact</h2>
        <p class="sub">Tiered supplier exposure rolls up to protected programs through ontology links.</p>
        <ul class="programs">{program_items}</ul>

        <h2 style="margin-top:18px">Notification Draft</h2>
        <div class="chips">
          <span class="chip hot">UNSENT</span>
          <span class="chip">approval required</span>
          <span class="chip">status: {e(draft_status)}</span>
        </div>
        <div class="draft">{e(draft_body)}</div>
      </section>
    </div>

    <section class="panel" style="margin-top:14px">
      <h2>Provenance</h2>
      <div class="chips">
        <span class="chip hot">incident: {e(incident_id)}</span>
        <span class="chip green">draft: {e(draft_id)}</span>
        <span class="chip">supplier: {e(supplier_id)}</span>
        <span class="chip">{record_count} records · {source_count or 0} sources</span>
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
