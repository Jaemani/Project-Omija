"""Run the integrated OSINT + ontology dashboard demo.

The dashboard is intentionally product-facing rather than a raw verification
report. It shows operational value first, then the graph path, evidence context,
recommended response, draft notification, and feed status.
"""

from __future__ import annotations

import html
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "out"
OUT_JSON = OUT_DIR / "intelligence_demo.json"
OUT_HTML = OUT_DIR / "intelligence_demo.html"


def run_required(name: str, argv: list[str]) -> None:
    print(f"\n== {name}")
    print("$ " + " ".join(argv))
    proc = subprocess.run(
        argv,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.stdout.strip():
        print(proc.stdout.rstrip())
    if proc.stderr.strip():
        print(proc.stderr.rstrip(), file=sys.stderr)
    if proc.returncode:
        raise SystemExit(f"FAILED {name} rc={proc.returncode}")
    print(f"PASS {name}")


def run_optional(name: str, argv: list[str]) -> int:
    print(f"\n== {name}")
    print("$ " + " ".join(argv))
    proc = subprocess.run(
        argv,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.stdout.strip():
        print(proc.stdout.rstrip())
    if proc.stderr.strip():
        print(proc.stderr.rstrip(), file=sys.stderr)
    print(f"STATUS {name} rc={proc.returncode}")
    return proc.returncode


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def build_payload() -> dict[str, Any]:
    foundry = read_json(OUT_DIR / "demo_e2e_foundry.json", {})
    osint = read_json(OUT_DIR / "osint" / "osint_summary.json", {})
    stealth = read_json(OUT_DIR / "p0b" / "stealthmole_auth_evidence.json", {})

    exposure = (foundry.get("exposures") or [{}])[0]
    target = exposure.get("target")
    target_overlay = {}
    for row in osint.get("asset_overlays", []):
        if row.get("fqdn") == target:
            target_overlay = row
            break

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "foundry": foundry,
        "osint": {
            "nvd_critical_vpn_cves": (osint.get("nvd") or {}).get("result_count"),
            "cisa_kev_total": (osint.get("cisa_kev") or {}).get(
                "total_vulnerabilities"
            ),
            "cisa_kev_access_relevant": (osint.get("cisa_kev") or {}).get(
                "access_relevant_count"
            ),
            "attack_selected": (osint.get("mitre_attack") or {}).get(
                "selected_count"
            ),
            "urlhaus_sampled_rows": (osint.get("urlhaus") or {}).get(
                "sampled_rows"
            ),
            "target_asset_overlay": target_overlay,
            "top_nvd": (osint.get("nvd") or {}).get("critical_vpn_cves", [])[:5],
        },
        "stealthmole": {
            "status_code": stealth.get("quotas_status_code"),
            "endpoint": stealth.get("endpoint"),
            "iat_minus_server_seconds": stealth.get("iat_minus_server_seconds"),
            "diagnosis": stealth.get("diagnosis"),
        },
        "ontology_mapping": [
            "CredentialExposure.of -> Identity",
            "CredentialExposure.targets -> Domain",
            "Identity.belongs_to -> Domain",
            "Domain.owner -> Supplier / Prime",
            "Supplier.subcontractsTo -> Supplier",
            "Supplier.supplies -> Prime",
            "Prime.runs -> Program",
            "CompromiseIncident.traverses_* -> provenance path",
            "NotificationDraft.cites -> incident / evidence",
        ],
    }


def e(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def render_corroboration_rows(osint: dict[str, Any], overlay: dict[str, Any]) -> str:
    rows = [
        (
            "CISA KEV",
            "Known exploited vulnerabilities",
            f"{osint.get('cisa_kev_access_relevant')} access-relevant / "
            f"{osint.get('cisa_kev_total')} total",
            "Corroborated",
        ),
        (
            "NVD CVE API",
            "Critical VPN vulnerabilities",
            f"{osint.get('nvd_critical_vpn_cves')} matching CVEs",
            "Corroborated",
        ),
        (
            "MITRE ATT&CK",
            "Credential and initial-access tactics",
            f"{osint.get('attack_selected')} techniques selected",
            "Reference",
        ),
        (
            "abuse.ch URLhaus",
            "Recent malicious URL telemetry",
            f"{osint.get('urlhaus_sampled_rows')} recent rows sampled",
            "Reference",
        ),
    ]
    asset_rows = []
    for cve in (overlay.get("top_kev_matches") or [])[:4]:
        asset_rows.append(
            "<tr>"
            f"<td>{e(cve.get('cveID'))}</td>"
            f"<td>{e(cve.get('vendorProject'))}</td>"
            f"<td>{e(cve.get('product'))}</td>"
            f"<td>{e(cve.get('vulnerabilityName'))}</td>"
            "</tr>"
        )
    source_rows = [
        "<tr>"
        f"<td>{e(source)}</td>"
        f"<td>{e(signal)}</td>"
        f"<td>{e(summary)}</td>"
        f"<td><span class='badge'>{e(status)}</span></td>"
        "</tr>"
        for source, signal, summary, status in rows
    ]
    if asset_rows:
        source_rows.append(
            "<tr class='subhead'><td colspan='4'>Target asset KEV examples</td></tr>"
        )
        source_rows.extend(asset_rows)
    return "".join(source_rows)


def render_actions(foundry: dict[str, Any], osint: dict[str, Any]) -> str:
    supplier = foundry.get("supplier") or "unknown"
    programs = ", ".join(foundry.get("programs") or []) or "program owner"
    access_relevant = osint.get("cisa_kev_access_relevant") or 0
    actions = [
        (
            "P0",
            "Disable exposed session and rotate credential",
            supplier,
            "Active supplier identity reaches target asset path",
            "Supplier security owner",
            "Analyst review",
        ),
        (
            "P1",
            "Validate prime VPN / SSO access logs",
            programs,
            f"{access_relevant} access-relevant KEV items support urgency",
            "Prime SOC",
            "Queued",
        ),
        (
            "P2",
            "Send advisory draft after human sign-off",
            supplier,
            "Evidence package cites incident and graph path",
            "Program security lead",
            "Draft only",
        ),
    ]
    return "".join(
        "<tr>"
        f"<td><span class='priority'>{e(priority)}</span></td>"
        f"<td>{e(action)}</td>"
        f"<td>{e(target)}</td>"
        f"<td>{e(rationale)}</td>"
        f"<td>{e(owner)}</td>"
        f"<td><span class='badge hold'>{e(status)}</span></td>"
        "</tr>"
        for priority, action, target, rationale, owner, status in actions
    )


def render_html(payload: dict[str, Any]) -> str:
    foundry = payload["foundry"]
    osint = payload["osint"]
    stealth = payload["stealthmole"]
    exposure = (foundry.get("exposures") or [{}])[0]
    overlay = osint.get("target_asset_overlay") or {}

    supplier = foundry.get("supplier") or "unknown"
    programs = foundry.get("programs") or []
    program_label = ", ".join(programs) or "No program linked"
    target = exposure.get("target") or overlay.get("fqdn") or "unknown target"
    credential_status = (
        "LIVE"
        if stealth.get("status_code") == 200
        else f"DEGRADED / {stealth.get('status_code') or 'UNKNOWN'}"
    )
    generated_at = payload.get("generated_at")
    kev_matches = overlay.get("kev_match_count") or 0
    path_items = "".join(
        f"<li><span class='mono'>{e(path)}</span></li>"
        for path in foundry.get("paths", [])
    )
    mapping_items = "".join(
        f"<li>{e(item)}</li>" for item in payload.get("ontology_mapping", [])
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Project Omija Dashboard</title>
<style>
:root {{
  color-scheme: light;
  --bg: #f4f6f8;
  --panel: #ffffff;
  --ink: #172033;
  --muted: #5b6472;
  --line: #d8dde6;
  --alert: #b42318;
  --alert-soft: #fff3f0;
  --amber: #946200;
  --amber-soft: #fff7df;
  --blue: #175cd3;
  --blue-soft: #eff6ff;
  --green: #067647;
  --green-soft: #ecfdf3;
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
  color: #f9fafb;
  padding: 14px 24px;
  border-bottom: 4px solid var(--alert);
}}
.topline {{
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  justify-content: space-between;
}}
.kicker {{
  color: #cbd5e1;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0;
}}
h1 {{
  margin: 8px 0 4px;
  font-size: 24px;
  letter-spacing: 0;
}}
.header-copy {{
  color: #dbe4ef;
  margin: 0;
  max-width: 980px;
}}
main {{
  max-width: 1380px;
  margin: 0 auto;
  padding: 18px 24px 28px;
}}
.badge, .status {{
  border: 1px solid var(--line);
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}}
.status {{
  background: var(--amber-soft);
  border-color: #fedf89;
  color: var(--amber);
}}
.status.hot, .priority {{
  background: var(--alert-soft);
  border-color: #fecdca;
  color: var(--alert);
}}
.badge.hold {{
  background: var(--amber-soft);
  border-color: #fedf89;
  color: var(--amber);
}}
.badge.ok {{
  background: var(--green-soft);
  border-color: #abefc6;
  color: var(--green);
}}
.summary {{
  display: grid;
  grid-template-columns: 1.25fr repeat(4, minmax(145px, 1fr));
  gap: 12px;
  margin-bottom: 14px;
}}
.threat-picture, .metric, .panel {{
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 6px;
}}
.threat-picture {{
  border-left: 4px solid var(--alert);
  padding: 14px 16px;
}}
.threat-picture h2, .panel h2 {{
  margin: 0 0 8px;
  font-size: 13px;
  letter-spacing: 0;
  text-transform: uppercase;
}}
.threat-picture p {{
  margin: 0;
  color: var(--muted);
  max-width: 760px;
}}
.metric {{
  min-height: 88px;
  padding: 13px;
}}
.metric span {{
  color: var(--muted);
  display: block;
  font-size: 12px;
  font-weight: 700;
}}
.metric strong {{
  display: block;
  font-size: 24px;
  margin-top: 8px;
}}
.layout {{
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(330px, .9fr);
  gap: 14px;
}}
.panel {{
  padding: 16px;
  margin-bottom: 14px;
}}
.chain {{
  align-items: stretch;
  display: grid;
  grid-template-columns: repeat(5, minmax(120px, 1fr));
  gap: 8px;
  margin: 16px 0 12px;
}}
.node {{
  border: 1px solid var(--line);
  border-radius: 6px;
  min-height: 96px;
  padding: 10px;
  position: relative;
}}
.node.alert {{
  background: var(--alert-soft);
  border-color: #fecdca;
}}
.node.program {{
  background: var(--blue-soft);
  border-color: #b2ddff;
}}
.node .type {{
  color: var(--muted);
  display: block;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
}}
.node .name {{
  display: block;
  font-weight: 800;
  margin-top: 4px;
}}
.node .detail {{
  color: var(--muted);
  display: block;
  font-size: 12px;
  margin-top: 4px;
}}
.edge-labels {{
  display: grid;
  grid-template-columns: repeat(4, minmax(120px, 1fr));
  gap: 8px;
  color: var(--muted);
  font-size: 12px;
  margin-bottom: 12px;
}}
.edge-labels span {{
  border-top: 1px solid var(--line);
  padding-top: 6px;
}}
.mono {{
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12px;
}}
.sub {{
  color: var(--muted);
}}
.path-list {{
  margin: 8px 0 0;
  padding-left: 18px;
}}
table {{
  border-collapse: collapse;
  width: 100%;
}}
th, td {{
  border-bottom: 1px solid var(--line);
  padding: 8px 7px;
  text-align: left;
  vertical-align: top;
}}
th {{
  color: var(--muted);
  font-size: 12px;
  text-transform: uppercase;
}}
td {{
  font-size: 13px;
}}
.subhead td {{
  background: #f8fafc;
  color: var(--muted);
  font-weight: 800;
  text-transform: uppercase;
}}
.draft {{
  background: linear-gradient(135deg, #fff, #fff7df);
  border-color: #fedf89;
}}
.draft-watermark {{
  color: var(--amber);
  font-weight: 900;
  margin-bottom: 8px;
}}
.footer-grid {{
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}}
.feed-card {{
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 10px;
}}
.feed-card strong {{
  display: block;
  margin-bottom: 4px;
}}
@media (max-width: 980px) {{
  main {{ padding: 14px; }}
  .summary, .layout, .chain, .edge-labels, .footer-grid {{
    grid-template-columns: 1fr;
  }}
}}
</style>
</head>
<body>
<header>
  <div class="topline">
    <div class="kicker">EXPOSURE EARLY WARNING · UNCLASSIFIED // OSINT</div>
    <div class="status">FEED: {e(credential_status)}</div>
  </div>
  <h1>Current Threat Picture</h1>
  <p class="header-copy">Supplier credential exposure is connected to a target
  asset, supply-chain path, impacted programs, public OSINT context, and an
  approval-gated response draft.</p>
</header>

<main>
  <section class="summary" aria-label="Operational summary">
    <div class="threat-picture">
      <h2>Operational Value</h2>
      <p>Project Omija turns scattered exposure and OSINT signals into a
      decision: which supplier creates a live path to a protected defense
      program, why it matters now, and what should be reviewed first.</p>
    </div>
    <div class="metric"><span>Active Exposures</span><strong>1</strong></div>
    <div class="metric"><span>Programs At Risk</span><strong>{len(programs)}</strong></div>
    <div class="metric"><span>Supplier Affected</span><strong>{e(supplier)}</strong></div>
    <div class="metric"><span>Highest Severity</span><strong>A</strong></div>
  </section>

  <div class="layout">
    <section>
      <div class="panel">
        <h2>Ontology Path — Credential To Program</h2>
        <p class="sub">The graph separates who owns the exposed account from
        what asset it can access, then carries that path through supplier and
        program relationships.</p>
        <div class="chain">
          <div class="node alert">
            <span class="type">Supplier Account</span>
            <span class="name">{e(exposure.get("identity"))}</span>
            <span class="detail">{e(exposure.get("domain"))}</span>
          </div>
          <div class="node alert">
            <span class="type">Credential Artifact</span>
            <span class="name">{e(exposure.get("id"))}</span>
            <span class="detail">targets {e(target)}</span>
          </div>
          <div class="node alert">
            <span class="type">Subcontractor</span>
            <span class="name">{e(supplier)}</span>
            <span class="detail">active compromise candidate</span>
          </div>
          <div class="node">
            <span class="type">Prime</span>
            <span class="name">prime-x</span>
            <span class="detail">reachable via supplier chain</span>
          </div>
          <div class="node program">
            <span class="type">Impacted Programs</span>
            <span class="name">{e(program_label)}</span>
            <span class="detail">blast radius confirmed</span>
          </div>
        </div>
        <div class="edge-labels">
          <span>of / targets · confidence 0.90</span>
          <span>belongs_to / owns</span>
          <span>subcontractsTo / supplies</span>
          <span>runs / traverses_program</span>
        </div>
        <h2>Provenance Path</h2>
        <ul class="path-list">{path_items}</ul>
      </div>

      <div class="panel">
        <h2>Recommended Response — Analyst Review Required</h2>
        <table>
          <thead>
            <tr>
              <th>Priority</th>
              <th>Action</th>
              <th>Target Entity</th>
              <th>Rationale</th>
              <th>Owner</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>{render_actions(foundry, osint)}</tbody>
        </table>
      </div>
    </section>

    <aside>
      <div class="panel">
        <h2>Public Source Corroboration</h2>
        <p class="sub">Target asset <span class="mono">{e(overlay.get("fqdn") or target)}</span>
        is treated as <span class="mono">{e(overlay.get("asset_type") or "access surface")}</span>.
        Public feeds add context; they do not replace the credential evidence.</p>
        <table>
          <thead>
            <tr><th>Source</th><th>Signal</th><th>Summary</th><th>Status</th></tr>
          </thead>
          <tbody>{render_corroboration_rows(osint, overlay)}</tbody>
        </table>
      </div>

      <div class="panel draft">
        <h2>Unsent Advisory — Draft</h2>
        <div class="draft-watermark">DRAFT · NOT SENT · HUMAN SIGN-OFF REQUIRED</div>
        <p><strong>Recipient:</strong> {e(supplier)} security owner</p>
        <p><strong>Subject:</strong> Active credential exposure path to {e(program_label)}</p>
        <p><strong>Body preview:</strong> We observed a supplier identity linked
        to an exposure artifact targeting {e(target)}. The ontology path reaches
        {e(program_label)}. Please review credential rotation, session revocation,
        and access logs before export.</p>
        <p><strong>Evidence attached:</strong> incident {e((foundry.get("incidents") or [""])[0])},
        {kev_matches} target-asset KEV matches, Foundry path snapshot.</p>
      </div>

      <div class="panel">
        <h2>Collection Status</h2>
        <div class="footer-grid">
          <div class="feed-card">
            <strong>Public OSINT</strong>
            <span class="badge ok">Live public feeds</span>
            <p class="sub">NVD, CISA KEV, MITRE ATT&CK, URLhaus.</p>
          </div>
          <div class="feed-card">
            <strong>Foundry OSDK</strong>
            <span class="badge ok">Readback OK</span>
            <p class="sub">Core ontology links and blast radius verified.</p>
          </div>
          <div class="feed-card">
            <strong>Credential Feed</strong>
            <span class="badge hold">{e(credential_status)}</span>
            <p class="sub">{e(stealth.get("diagnosis"))}</p>
          </div>
        </div>
      </div>
    </aside>
  </div>

  <section class="panel">
    <h2>Ontology Contract</h2>
    <ul>{mapping_items}</ul>
    <p class="sub">Generated at <span class="mono">{e(generated_at)}</span>.
    Public OSINT is real public data. The Foundry credential seed is synthetic
    unless the authorized live credential pipeline succeeds.</p>
  </section>
</main>
</body>
</html>"""


def main() -> int:
    run_required(
        "OSINT public feed collection",
        [sys.executable, "scripts/osint_collect.py"],
    )
    run_required(
        "Foundry ontology demo check",
        [sys.executable, "scripts/final_demo_check.py"],
    )
    run_optional(
        "StealthMole auth evidence",
        [sys.executable, "scripts/stealthmole_auth_evidence.py"],
    )
    payload = build_payload()
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_HTML.write_text(render_html(payload), encoding="utf-8")
    print(f"wrote {OUT_JSON.relative_to(REPO_ROOT)}")
    print(f"wrote {OUT_HTML.relative_to(REPO_ROOT)}")
    print("RESULT: READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
