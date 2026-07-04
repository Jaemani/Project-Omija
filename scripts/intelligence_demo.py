"""Run the integrated OSINT + ontology demo.

This is the final Track 2/3 story:
- public OSINT feeds provide real external intelligence context;
- Foundry OSDK proves the supply-chain ontology path;
- StealthMole auth evidence reports whether the credential feed is live.
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
    proc = subprocess.run(argv, cwd=REPO_ROOT, text=True, capture_output=True, check=False)
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
    proc = subprocess.run(argv, cwd=REPO_ROOT, text=True, capture_output=True, check=False)
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
    target = None
    exposures = foundry.get("exposures") or []
    if exposures:
        target = exposures[0].get("target")
    target_overlay = next(
        (row for row in osint.get("asset_overlays", []) if row.get("fqdn") == target),
        {},
    )
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "foundry": foundry,
        "osint": {
            "nvd_critical_vpn_cves": (osint.get("nvd") or {}).get("result_count"),
            "cisa_kev_total": (osint.get("cisa_kev") or {}).get("total_vulnerabilities"),
            "cisa_kev_access_relevant": (osint.get("cisa_kev") or {}).get("access_relevant_count"),
            "attack_selected": (osint.get("mitre_attack") or {}).get("selected_count"),
            "urlhaus_sampled_rows": (osint.get("urlhaus") or {}).get("sampled_rows"),
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
            "Domain.owner -> Supplier / Prime",
            "Supplier.subcontractsTo -> Supplier",
            "Supplier.supplies -> Prime",
            "Prime.runs -> Program",
            "RiskAssessment.components <- OSINT overlay + credential signal",
            "NotificationDraft.cites -> Incident / Evidence",
        ],
    }


def e(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def render_html(payload: dict[str, Any]) -> str:
    foundry = payload["foundry"]
    osint = payload["osint"]
    stealth = payload["stealthmole"]
    exposure = (foundry.get("exposures") or [{}])[0]
    overlay = osint.get("target_asset_overlay") or {}
    cves = overlay.get("top_kev_matches") or osint.get("top_nvd") or []
    cve_rows = "".join(
        "<tr>"
        f"<td>{e(row.get('cveID') or row.get('id'))}</td>"
        f"<td>{e(row.get('vendorProject') or row.get('baseSeverity'))}</td>"
        f"<td>{e(row.get('product') or row.get('baseScore'))}</td>"
        f"<td>{e(row.get('vulnerabilityName') or row.get('description'))}</td>"
        "</tr>"
        for row in cves[:8]
    )
    paths = "".join(f"<li>{e(path)}</li>" for path in foundry.get("paths", []))
    mapping = "".join(f"<li>{e(item)}</li>" for item in payload["ontology_mapping"])
    credential_status = (
        "LIVE AUTH OK" if stealth.get("status_code") == 200 else f"AUTH BLOCKED ({stealth.get('status_code')})"
    )
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Project Omija Intelligence Demo</title>
  <style>
    body {{ margin: 0; font: 14px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #172033; background: #f7f8fb; }}
    header {{ background: #fff; border-bottom: 1px solid #d9dee8; padding: 18px 28px; }}
    main {{ max-width: 1280px; margin: 0 auto; padding: 18px 28px 30px; }}
    h1 {{ margin: 0 0 6px; font-size: 26px; letter-spacing: 0; }}
    h2 {{ margin: 0 0 10px; font-size: 16px; }}
    .sub {{ color: #596276; }}
    .grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-bottom: 14px; }}
    section, .metric {{ background: #fff; border: 1px solid #d9dee8; border-radius: 8px; padding: 14px; }}
    .metric span {{ display: block; color: #596276; font-size: 12px; }}
    .metric strong {{ display: block; font-size: 22px; margin-top: 4px; }}
    .layout {{ display: grid; grid-template-columns: minmax(0, 1.25fr) minmax(320px, .75fr); gap: 14px; }}
    .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px; }}
    .hot {{ color: #b42318; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ text-align: left; border-bottom: 1px solid #d9dee8; padding: 7px; vertical-align: top; }}
    th {{ color: #596276; font-size: 12px; }}
    @media (max-width: 900px) {{ .grid, .layout {{ grid-template-columns: 1fr; }} header, main {{ padding-left: 16px; padding-right: 16px; }} }}
  </style>
</head>
<body>
  <header>
    <h1>Project Omija Intelligence Demo</h1>
    <p class="sub">OSINT 실제 공개 피드 + Foundry 온톨로지 경로 + credential feed 상태를 한 화면에 연결.</p>
  </header>
  <main>
    <div class="grid">
      <div class="metric"><span>Supplier</span><strong>{e(foundry.get("supplier"))}</strong></div>
      <div class="metric"><span>Impacted programs</span><strong>{len(foundry.get("programs", []))}</strong></div>
      <div class="metric"><span>Access-relevant KEV</span><strong>{e(osint.get("cisa_kev_access_relevant"))}</strong></div>
      <div class="metric"><span>Credential feed</span><strong class="hot">{e(credential_status)}</strong></div>
    </div>
    <div class="layout">
      <section>
        <h2>Ontology Path</h2>
        <p>Exposure <span class="mono">{e(exposure.get("id"))}</span> targets <span class="mono">{e(exposure.get("target"))}</span>.</p>
        <ul>{paths}</ul>
        <h2 style="margin-top:18px">Target Asset OSINT Overlay</h2>
        <p>Asset <span class="mono">{e(overlay.get("fqdn") or exposure.get("target"))}</span> type <span class="mono">{e(overlay.get("asset_type"))}</span> has {e(overlay.get("kev_match_count"))} CISA KEV matches by asset class.</p>
        <table><thead><tr><th>CVE</th><th>vendor/severity</th><th>product/score</th><th>description</th></tr></thead><tbody>{cve_rows}</tbody></table>
      </section>
      <section>
        <h2>Data Fusion Contract</h2>
        <ul>{mapping}</ul>
        <h2 style="margin-top:18px">Feed Status</h2>
        <p class="mono">StealthMole: {e(stealth.get("endpoint"))}</p>
        <p class="mono">status: {e(stealth.get("status_code"))}, iat skew: {e(stealth.get("iat_minus_server_seconds"))}s</p>
        <p class="sub">{e(stealth.get("diagnosis"))}</p>
        <h2 style="margin-top:18px">Public OSINT</h2>
        <p>NVD critical VPN CVEs: {e(osint.get("nvd_critical_vpn_cves"))}</p>
        <p>MITRE selected techniques: {e(osint.get("attack_selected"))}</p>
        <p>URLhaus sampled rows: {e(osint.get("urlhaus_sampled_rows"))}</p>
      </section>
    </div>
  </main>
</body>
</html>"""


def main() -> int:
    python = sys.executable
    run_required("OSINT public feed collection", [python, "scripts/osint_collect.py"])
    run_required("Foundry ontology demo check", [python, "scripts/final_demo_check.py"])
    run_optional("StealthMole auth evidence", [python, "scripts/stealthmole_auth_evidence.py"])
    payload = build_payload()
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_HTML.write_text(render_html(payload), encoding="utf-8")
    print(f"\nwrote {OUT_JSON.relative_to(REPO_ROOT)}")
    print(f"wrote {OUT_HTML.relative_to(REPO_ROOT)}")
    print("RESULT: READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
