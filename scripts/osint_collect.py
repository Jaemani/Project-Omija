"""Collect public OSINT feeds and build a defense-intelligence overlay.

Sources are public, non-secret, and safe to commit as derived summaries:
- CISA Known Exploited Vulnerabilities catalog
- MITRE ATT&CK Enterprise STIX
- abuse.ch URLhaus recent URL feed

This is not credential dumping. It adds public threat/vulnerability context to
the supply-chain credential exposure graph.
"""

from __future__ import annotations

import csv
import html
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "out" / "osint"
OUT_JSON = OUT_DIR / "osint_summary.json"
OUT_HTML = OUT_DIR / "osint_report.html"

CISA_KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
MITRE_ATTACK_URL = (
    "https://raw.githubusercontent.com/mitre-attack/attack-stix-data/master/"
    "enterprise-attack/enterprise-attack.json"
)
URLHAUS_RECENT_CSV_URL = "https://urlhaus.abuse.ch/downloads/csv_recent/"
NVD_CVE_API_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
NVD_QUERY = {
    "keywordSearch": "vpn",
    "cvssV3Severity": "CRITICAL",
    "resultsPerPage": "20",
}

ACCESS_KEYWORDS = {
    "vpn",
    "remote",
    "gateway",
    "firewall",
    "router",
    "sso",
    "identity",
    "exchange",
    "sharepoint",
    "confluence",
    "gitlab",
    "jira",
    "fortinet",
    "fortios",
    "citrix",
    "netscaler",
    "ivanti",
    "palo alto",
    "cisco",
    "sonicwall",
    "pulse",
    "vmware",
    "zimbra",
    "f5",
    "microsoft",
    "apache",
    "nginx",
    "openssl",
    "mail",
    "email",
}

ASSET_KEYWORDS = {
    "vpn": {"vpn", "gateway", "firewall", "fortinet", "fortios", "citrix", "netscaler", "ivanti", "palo alto", "sonicwall", "pulse", "cisco"},
    "sso": {"sso", "identity", "microsoft", "ad fs", "active directory"},
    "mail": {"exchange", "zimbra", "mail", "email", "microsoft"},
    "groupware": {"confluence", "jira", "sharepoint"},
    "dev": {"gitlab", "confluence", "jira", "jenkins"},
    "web": {"apache", "nginx", "openssl", "tomcat"},
    "domain": {"microsoft", "windows", "active directory"},
}

STEALER_TAGS = {
    "stealer",
    "infostealer",
    "redline",
    "vidar",
    "raccoon",
    "lumma",
    "azorult",
    "formbook",
    "agenttesla",
    "clearfake",
    "socgholish",
}

ATTACK_TACTICS = {"credential-access", "initial-access", "discovery", "persistence"}


def fetch_text(url: str, *, timeout: int = 45) -> str:
    req = Request(url, headers={"User-Agent": "Project-Omija-OSINT/1.0"})
    with urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def fetch_json(url: str) -> dict[str, Any]:
    return json.loads(fetch_text(url))


def fetch_nvd() -> dict[str, Any]:
    return fetch_json(f"{NVD_CVE_API_URL}?{urlencode(NVD_QUERY)}")


def _contains_keyword(text: str, keywords: set[str]) -> bool:
    low = text.lower()
    return any(keyword in low for keyword in keywords)


def summarize_kev(feed: dict[str, Any], *, limit: int = 40) -> dict[str, Any]:
    vulnerabilities = feed.get("vulnerabilities", [])
    access_relevant = []
    for item in vulnerabilities:
        haystack = " ".join(
            str(item.get(key, ""))
            for key in ("vendorProject", "product", "vulnerabilityName", "shortDescription", "requiredAction", "notes")
        )
        if _contains_keyword(haystack, ACCESS_KEYWORDS):
            access_relevant.append(
                {
                    "cveID": item.get("cveID"),
                    "vendorProject": item.get("vendorProject"),
                    "product": item.get("product"),
                    "vulnerabilityName": item.get("vulnerabilityName"),
                    "dateAdded": item.get("dateAdded"),
                    "knownRansomwareCampaignUse": item.get("knownRansomwareCampaignUse"),
                    "requiredAction": item.get("requiredAction"),
                }
            )

    access_relevant.sort(key=lambda row: row.get("dateAdded") or "", reverse=True)
    return {
        "source": CISA_KEV_URL,
        "catalog_version": feed.get("catalogVersion"),
        "date_released": feed.get("dateReleased"),
        "total_vulnerabilities": len(vulnerabilities),
        "access_relevant_count": len(access_relevant),
        "recent_access_relevant": access_relevant[:limit],
    }


def summarize_attack(feed: dict[str, Any], *, limit: int = 40) -> dict[str, Any]:
    techniques = []
    for obj in feed.get("objects", []):
        if obj.get("type") != "attack-pattern" or obj.get("revoked") or obj.get("x_mitre_deprecated"):
            continue
        tactics = sorted(
            {
                phase.get("phase_name")
                for phase in obj.get("kill_chain_phases", [])
                if phase.get("kill_chain_name") == "mitre-attack"
            }
        )
        if not set(tactics).intersection(ATTACK_TACTICS):
            continue
        external_id = next(
            (
                ref.get("external_id")
                for ref in obj.get("external_references", [])
                if ref.get("source_name") == "mitre-attack" and ref.get("external_id")
            ),
            None,
        )
        techniques.append(
            {
                "id": external_id,
                "name": obj.get("name"),
                "tactics": tactics,
                "modified": obj.get("modified"),
                "description": (obj.get("description") or "")[:220],
            }
        )

    techniques.sort(key=lambda row: ("credential-access" not in row["tactics"], row.get("id") or ""))
    return {
        "source": MITRE_ATTACK_URL,
        "total_attack_patterns": sum(1 for obj in feed.get("objects", []) if obj.get("type") == "attack-pattern"),
        "selected_count": len(techniques),
        "selected_techniques": techniques[:limit],
    }


def summarize_urlhaus(csv_text: str, *, max_rows: int = 1000) -> dict[str, Any]:
    rows = []
    csv_lines = [line for line in csv_text.splitlines() if line and not line.startswith("#")]
    reader = csv.DictReader(StringIO("\n".join(csv_lines)))
    tag_counts: Counter[str] = Counter()
    stealer_rows = []
    for index, row in enumerate(reader):
        if index >= max_rows:
            break
        rows.append(row)
        tags = [tag.strip() for tag in (row.get("tags") or "").split(",") if tag.strip()]
        tag_counts.update(tags)
        if any(tag.lower() in STEALER_TAGS or "stealer" in tag.lower() for tag in tags):
            stealer_rows.append(
                {
                    "id": row.get("id"),
                    "dateadded": row.get("dateadded"),
                    "url_status": row.get("url_status"),
                    "threat": row.get("threat"),
                    "tags": tags,
                    "urlhaus_link": row.get("urlhaus_link"),
                }
            )

    return {
        "source": URLHAUS_RECENT_CSV_URL,
        "sampled_rows": len(rows),
        "top_tags": tag_counts.most_common(20),
        "stealer_or_loader_rows": stealer_rows[:40],
        "stealer_or_loader_count": len(stealer_rows),
    }


def summarize_nvd(feed: dict[str, Any]) -> dict[str, Any]:
    items = []
    for row in feed.get("vulnerabilities", []):
        cve = row.get("cve", {})
        descriptions = cve.get("descriptions", [])
        description = next(
            (item.get("value") for item in descriptions if item.get("lang") == "en"),
            "",
        )
        metrics = cve.get("metrics", {})
        cvss = None
        for key in ("cvssMetricV31", "cvssMetricV30"):
            if metrics.get(key):
                cvss = metrics[key][0].get("cvssData", {})
                break
        items.append(
            {
                "id": cve.get("id"),
                "published": cve.get("published"),
                "lastModified": cve.get("lastModified"),
                "baseScore": cvss.get("baseScore") if cvss else None,
                "baseSeverity": cvss.get("baseSeverity") if cvss else None,
                "description": description[:260],
            }
        )
    return {
        "source": f"{NVD_CVE_API_URL}?{urlencode(NVD_QUERY)}",
        "query": NVD_QUERY,
        "total_results": feed.get("totalResults"),
        "result_count": len(items),
        "critical_vpn_cves": items,
    }


def read_foundry_seed_assets() -> list[dict[str, str]]:
    path = REPO_ROOT / "out" / "foundry_seed" / "04_domain.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def build_asset_overlays(assets: list[dict[str, str]], kev_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    overlays = []
    for asset in assets:
        asset_type = (asset.get("asset_type") or "domain").lower()
        keywords = ASSET_KEYWORDS.get(asset_type, ASSET_KEYWORDS["domain"])
        matches = []
        for item in kev_items:
            haystack = " ".join(
                str(item.get(key, ""))
                for key in ("vendorProject", "product", "vulnerabilityName", "requiredAction")
            ).lower()
            if any(keyword in haystack for keyword in keywords):
                matches.append(item)
        overlays.append(
            {
                "fqdn": asset.get("fqdn") or asset.get("domain_fqdn"),
                "asset_type": asset_type,
                "criticality": asset.get("criticality"),
                "kev_match_count": len(matches),
                "top_kev_matches": matches[:8],
            }
        )
    return overlays


def build_summary() -> dict[str, Any]:
    nvd = summarize_nvd(fetch_nvd())
    kev = summarize_kev(fetch_json(CISA_KEV_URL))
    attack = summarize_attack(fetch_json(MITRE_ATTACK_URL))
    urlhaus = summarize_urlhaus(fetch_text(URLHAUS_RECENT_CSV_URL))
    assets = read_foundry_seed_assets()
    overlays = build_asset_overlays(assets, kev["recent_access_relevant"])
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources": {
            "cisa_kev": CISA_KEV_URL,
            "nvd": nvd["source"],
            "mitre_attack": MITRE_ATTACK_URL,
            "urlhaus_recent": URLHAUS_RECENT_CSV_URL,
        },
        "nvd": nvd,
        "cisa_kev": kev,
        "mitre_attack": attack,
        "urlhaus": urlhaus,
        "asset_overlays": overlays,
    }


def e(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def render_html(summary: dict[str, Any]) -> str:
    kev_rows = "".join(
        "<tr>"
        f"<td>{e(row.get('cveID'))}</td>"
        f"<td>{e(row.get('vendorProject'))}</td>"
        f"<td>{e(row.get('product'))}</td>"
        f"<td>{e(row.get('dateAdded'))}</td>"
        f"<td>{e(row.get('vulnerabilityName'))}</td>"
        "</tr>"
        for row in summary["cisa_kev"]["recent_access_relevant"][:20]
    )
    technique_rows = "".join(
        "<tr>"
        f"<td>{e(row.get('id'))}</td>"
        f"<td>{e(row.get('name'))}</td>"
        f"<td>{e(', '.join(row.get('tactics') or []))}</td>"
        "</tr>"
        for row in summary["mitre_attack"]["selected_techniques"][:20]
    )
    overlay_rows = "".join(
        "<tr>"
        f"<td>{e(row.get('fqdn'))}</td>"
        f"<td>{e(row.get('asset_type'))}</td>"
        f"<td>{e(row.get('kev_match_count'))}</td>"
        f"<td>{e(', '.join(match.get('cveID', '') for match in row.get('top_kev_matches', [])[:5]))}</td>"
        "</tr>"
        for row in summary["asset_overlays"]
    )
    nvd_rows = "".join(
        "<tr>"
        f"<td>{e(row.get('id'))}</td>"
        f"<td>{e(row.get('baseScore'))}</td>"
        f"<td>{e(row.get('published'))}</td>"
        f"<td>{e(row.get('description'))}</td>"
        "</tr>"
        for row in summary["nvd"]["critical_vpn_cves"][:20]
    )
    tag_rows = "".join(
        f"<tr><td>{e(tag)}</td><td>{count}</td></tr>"
        for tag, count in summary["urlhaus"]["top_tags"][:15]
    )
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Project Omija OSINT Overlay</title>
  <style>
    body {{ margin: 0; font: 14px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #172033; background: #f7f8fb; }}
    header, main {{ max-width: 1280px; margin: 0 auto; padding: 20px 28px; }}
    header {{ background: #fff; border-bottom: 1px solid #d9dee8; max-width: none; }}
    h1 {{ margin: 0 0 6px; font-size: 26px; letter-spacing: 0; }}
    h2 {{ margin: 22px 0 10px; font-size: 16px; }}
    .grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }}
    .metric, section {{ background: #fff; border: 1px solid #d9dee8; border-radius: 8px; padding: 14px; }}
    .metric span {{ color: #596276; display: block; font-size: 12px; }}
    .metric strong {{ display: block; font-size: 24px; margin-top: 4px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ text-align: left; border-bottom: 1px solid #d9dee8; padding: 7px; vertical-align: top; }}
    th {{ color: #596276; font-size: 12px; }}
    .sub {{ color: #596276; }}
    @media (max-width: 900px) {{ .grid {{ grid-template-columns: 1fr; }} header, main {{ padding-left: 16px; padding-right: 16px; }} }}
  </style>
</head>
<body>
  <header>
    <h1>Project Omija OSINT Overlay</h1>
    <p class="sub">Public feeds: CISA KEV, MITRE ATT&CK, abuse.ch URLhaus. Generated {e(summary["generated_at"])}.</p>
  </header>
  <main>
    <div class="grid">
      <div class="metric"><span>CISA KEV total</span><strong>{summary["cisa_kev"]["total_vulnerabilities"]}</strong></div>
      <div class="metric"><span>Access-relevant KEV</span><strong>{summary["cisa_kev"]["access_relevant_count"]}</strong></div>
      <div class="metric"><span>NVD critical VPN CVEs</span><strong>{summary["nvd"]["result_count"]}</strong></div>
      <div class="metric"><span>URLhaus sampled rows</span><strong>{summary["urlhaus"]["sampled_rows"]}</strong></div>
    </div>
    <section>
      <h2>Asset Overlay</h2>
      <table><thead><tr><th>asset</th><th>type</th><th>KEV matches</th><th>top CVEs</th></tr></thead><tbody>{overlay_rows}</tbody></table>
    </section>
    <section>
      <h2>NVD Critical VPN CVEs</h2>
      <table><thead><tr><th>CVE</th><th>score</th><th>published</th><th>description</th></tr></thead><tbody>{nvd_rows}</tbody></table>
    </section>
    <section>
      <h2>Recent Access-Relevant CISA KEV</h2>
      <table><thead><tr><th>CVE</th><th>vendor</th><th>product</th><th>date</th><th>name</th></tr></thead><tbody>{kev_rows}</tbody></table>
    </section>
    <section>
      <h2>MITRE ATT&CK Techniques</h2>
      <table><thead><tr><th>ID</th><th>name</th><th>tactics</th></tr></thead><tbody>{technique_rows}</tbody></table>
    </section>
    <section>
      <h2>URLhaus Top Tags</h2>
      <table><thead><tr><th>tag</th><th>count</th></tr></thead><tbody>{tag_rows}</tbody></table>
    </section>
  </main>
</body>
</html>"""


def main() -> int:
    summary = build_summary()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_HTML.write_text(render_html(summary), encoding="utf-8")
    print(f"wrote {OUT_JSON.relative_to(REPO_ROOT)}")
    print(f"wrote {OUT_HTML.relative_to(REPO_ROOT)}")
    print(
        "OSINT "
        f"kev={summary['cisa_kev']['access_relevant_count']}/"
        f"{summary['cisa_kev']['total_vulnerabilities']} "
        f"nvd={summary['nvd']['result_count']} "
        f"attack={summary['mitre_attack']['selected_count']} "
        f"urlhaus_sample={summary['urlhaus']['sampled_rows']}"
    )
    print("RESULT: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
