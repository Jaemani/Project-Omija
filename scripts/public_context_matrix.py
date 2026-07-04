"""Generate a safe public-context matrix page for Omija."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "out"
SUMMARY_JSON = OUT_DIR / "public_context" / "summary.json"
OUT_HTML = OUT_DIR / "public_context_matrix.html"


def e(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def read_summary() -> dict[str, Any]:
    if not SUMMARY_JSON.exists():
        return {}
    return json.loads(SUMMARY_JSON.read_text(encoding="utf-8"))


def nvd_total(summary: dict[str, Any]) -> int:
    return sum(query.get("total_results", 0) or 0 for query in summary.get("nvd", {}).get("queries", []))


def source_row(name: str, count: Any, role: str, ontology_fit: str, boundary: str, tone: str) -> str:
    return f"""
    <tr>
      <td><span class="source {e(tone)}">{e(name)}</span></td>
      <td class="metric">{e(count)}</td>
      <td>{e(role)}</td>
      <td><code>{e(ontology_fit)}</code></td>
      <td>{e(boundary)}</td>
    </tr>
    """


def stat(label: str, value: Any, tone: str) -> str:
    return (
        f"<div class='stat {e(tone)}'>"
        f"<span>{e(label)}</span>"
        f"<strong>{e(value)}</strong>"
        "</div>"
    )


def render(summary: dict[str, Any]) -> str:
    kev = summary.get("cisa_kev", {})
    attack = summary.get("mitre_attack", {})
    urlhaus = summary.get("urlhaus", {})
    hibp = summary.get("hibp", {})
    epss = summary.get("first_epss", {})
    advisories = summary.get("cisa_advisories", {})
    advisory_all = advisories.get("all", {})
    advisory_ics = advisories.get("ics", {})

    rows = "".join(
        [
            source_row(
                "CISA KEV",
                f"{kev.get('access_relevant_count', 0)} / {kev.get('total_vulnerabilities', 0)}",
                "Known exploited vulnerability urgency for VPN, SSO, mail, firewall, remote access surfaces.",
                "RiskAssessment.components.public_context.kev",
                "CVE metadata only; no credential evidence.",
                "public",
            ),
            source_row(
                "NVD CVE",
                nvd_total(summary),
                "Broader asset-class vulnerability background for watched domain types.",
                "Domain.asset_type -> RiskAssessment.components.cve_context",
                "Summary counts and sampled CVE metadata.",
                "public",
            ),
            source_row(
                "FIRST EPSS",
                epss.get("high_probability_total", 0),
                "Exploit-likelihood prioritization for CVEs likely to matter operationally.",
                "RiskAssessment.components.epss_context",
                "CVE probability metadata only.",
                "public",
            ),
            source_row(
                "CISA Advisories",
                f"{advisory_all.get('access_relevant_count', 0)} / {advisory_all.get('total_items_sampled', 0)}",
                "Recent public advisory context around access, identity, remote services, and campaigns.",
                "ThreatSource.kind -> ProgramExposure.components.public_advisory_context",
                "RSS title/link/date; no raw victim data.",
                "public",
            ),
            source_row(
                "CISA ICS Advisories",
                advisory_ics.get("total_items_sampled", 0),
                "Industrial/production-system context useful for defense manufacturing supply chains.",
                "ProgramExposure.components.ics_context",
                "RSS title/link/date only.",
                "public",
            ),
            source_row(
                "MITRE ATT&CK",
                attack.get("selected_count", 0),
                "Credential-access and initial-access technique vocabulary.",
                "ThreatSource.kind, RiskAssessment.components.techniques",
                "Technique metadata only.",
                "public",
            ),
            source_row(
                "URLhaus",
                f"{urlhaus.get('stealer_or_loader_count', 0)} / {urlhaus.get('sampled_rows', 0)}",
                "Aggregate malware distribution context, especially stealer/loader prevalence.",
                "ProgramExposure.components.threat_context",
                "Aggregate tags only; raw URLs not displayed.",
                "aggregate",
            ),
            source_row(
                "HIBP metadata",
                hibp.get("breach_count", 0),
                "Public breach class scale: which data classes appear in breach corpuses.",
                "Presentation context, not core evidence object",
                "Breach metadata only; no account query.",
                "public",
            ),
        ]
    )

    stats = "".join(
        [
            stat("KEV access-relevant", kev.get("access_relevant_count", 0), "public"),
            stat("NVD asset hits", nvd_total(summary), "public"),
            stat("EPSS > 0.95", epss.get("high_probability_total", 0), "public"),
            stat("CISA RSS access-relevant", advisory_all.get("access_relevant_count", 0), "public"),
            stat("ATT&CK selected", attack.get("selected_count", 0), "public"),
            stat("HIBP breach metadata", hibp.get("breach_count", 0), "public"),
        ]
    )

    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Omija Public Context Matrix</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg:#0c0d0e;
      --panel:#15181b;
      --panel2:#1d2227;
      --line:#333a42;
      --ink:#f3f4f6;
      --muted:#aeb7c2;
      --public:#d6a21d;
      --aggregate:#2ea043;
      --locked:#f85149;
    }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:var(--bg); color:var(--ink); font:14px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif; }}
    header {{ padding:18px 22px; border-bottom:1px solid var(--line); background:#121518; }}
    .kicker {{ color:var(--muted); font:11px ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:1px; text-transform:uppercase; }}
    h1 {{ margin:5px 0 4px; font-size:23px; letter-spacing:0; }}
    h2 {{ margin:0 0 10px; font-size:15px; letter-spacing:0; }}
    p {{ margin:0; color:var(--muted); }}
    main {{ padding:18px 22px 42px; display:grid; gap:18px; }}
    .panel {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:14px; }}
    .stats {{ display:grid; grid-template-columns:repeat(6,minmax(0,1fr)); gap:8px; }}
    .stat {{ min-height:64px; padding:9px; border:1px solid var(--line); border-left:3px solid currentColor; border-radius:6px; background:var(--panel2); }}
    .stat span {{ display:block; color:var(--muted); font-size:11px; }}
    .stat strong {{ display:block; margin-top:4px; color:var(--ink); font:18px ui-monospace,SFMono-Regular,Menlo,monospace; }}
    .public {{ color:var(--public); }}
    .aggregate {{ color:var(--aggregate); }}
    .table-wrap {{ overflow-x:auto; border:1px solid var(--line); border-radius:8px; background:var(--panel); }}
    table {{ width:100%; min-width:980px; border-collapse:collapse; }}
    th, td {{ padding:11px 12px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }}
    th {{ color:var(--muted); font-size:11px; text-transform:uppercase; letter-spacing:.6px; background:#101316; }}
    td {{ color:var(--muted); }}
    code {{ color:var(--ink); font:12px ui-monospace,SFMono-Regular,Menlo,monospace; }}
    .source {{ display:inline-block; border:1px solid currentColor; border-radius:4px; padding:3px 6px; font:12px ui-monospace,SFMono-Regular,Menlo,monospace; }}
    .metric {{ color:var(--ink); font:14px ui-monospace,SFMono-Regular,Menlo,monospace; white-space:nowrap; }}
    .note {{ border:1px solid color-mix(in srgb, var(--locked) 45%, var(--line)); border-left:4px solid var(--locked); border-radius:7px; padding:12px; background:#170f10; color:#ffd8d8; }}
    .flow {{ display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:8px; }}
    .step {{ padding:11px; min-height:88px; border:1px solid var(--line); border-radius:7px; background:var(--panel2); }}
    .step strong {{ display:block; color:var(--ink); margin-bottom:4px; }}
    .step span {{ color:var(--muted); font-size:12px; }}
    @media (max-width:980px) {{ .stats, .flow {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body>
  <header>
    <div class="kicker">OMIJA PUBLIC CONTEXT MATRIX</div>
    <h1>공개 데이터는 증거가 아니라 판단 배경이다</h1>
    <p>Generated from <code>{e(SUMMARY_JSON.relative_to(REPO_ROOT))}</code> at <code>{e(summary.get("generated_at", "not generated"))}</code>. 민감 자격증명·세션·계정 식별자는 수집하지 않는다.</p>
  </header>
  <main>
    <section class="panel">
      <h2>Public context counts</h2>
      <div class="stats">{stats}</div>
    </section>

    <section class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Source</th>
            <th>Count</th>
            <th>Why it helps</th>
            <th>Ontology fit</th>
            <th>Boundary</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
    </section>

    <section class="panel">
      <h2>How this supports the demo</h2>
      <div class="flow">
        <div class="step"><strong>1. Asset surface</strong><span>VPN, SSO, mail, firewall, remote access domains become watched asset types.</span></div>
        <div class="step"><strong>2. Public context</strong><span>KEV, NVD, EPSS, advisories, and ATT&CK explain why those surfaces matter.</span></div>
        <div class="step"><strong>3. Private signal slot</strong><span>Approved credential or infostealer signals would enter behind masking and review boundaries.</span></div>
        <div class="step"><strong>4. Ontology path</strong><span>`of`, `targets`, `subcontractsTo`, and `traverses_*` determine blast radius.</span></div>
        <div class="step"><strong>5. Decision object</strong><span>Risk, incident, program exposure, and notification draft are produced for human review.</span></div>
      </div>
    </section>

    <div class="note">This page must not be presented as credential evidence. It is public, non-sensitive context that makes the monitoring scope credible while synthetic seed data proves the reasoning engine safely.</div>
  </main>
</body>
</html>
"""


def main() -> int:
    summary = read_summary()
    OUT_HTML.write_text(render(summary), encoding="utf-8")
    print(f"wrote {OUT_HTML.relative_to(REPO_ROOT)}")
    print("RESULT: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
