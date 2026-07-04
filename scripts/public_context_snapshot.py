"""Collect non-sensitive public context summaries for Omija.

This script deliberately avoids credential/leak feeds. It fetches public,
defensive context that can explain *why* a target asset class matters:
CISA KEV, NVD CVE search results, MITRE ATT&CK techniques, URLhaus aggregate
feed metadata, and HIBP breach metadata.

Outputs are summaries only. Raw malicious URLs, credentials, cookies, tokens,
and account identifiers are not stored.
"""

from __future__ import annotations

import csv
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
OUT_DIR = REPO_ROOT / "out" / "public_context"
OUT_JSON = OUT_DIR / "summary.json"
OUT_MD = OUT_DIR / "summary.md"

CISA_KEV_JSON = (
    "https://raw.githubusercontent.com/cisagov/kev-data/develop/"
    "known_exploited_vulnerabilities.json"
)
MITRE_ATTACK_JSON = (
    "https://raw.githubusercontent.com/mitre-attack/attack-stix-data/master/"
    "enterprise-attack/enterprise-attack.json"
)
NVD_CVE_API = "https://services.nvd.nist.gov/rest/json/cves/2.0"
URLHAUS_RECENT_CSV = "https://urlhaus.abuse.ch/downloads/csv_recent/"
HIBP_BREACHES = "https://haveibeenpwned.com/api/v3/breaches"

NVD_QUERIES = [
    ("vpn", {"keywordSearch": "vpn", "cvssV3Severity": "CRITICAL", "resultsPerPage": "20"}),
    ("sso", {"keywordSearch": "single sign on", "cvssV3Severity": "HIGH", "resultsPerPage": "20"}),
    ("citrix", {"keywordSearch": "citrix", "resultsPerPage": "20"}),
    ("fortinet", {"keywordSearch": "fortinet", "resultsPerPage": "20"}),
    ("ivanti", {"keywordSearch": "ivanti", "resultsPerPage": "20"}),
]

ACCESS_KEYWORDS = {
    "vpn",
    "remote",
    "gateway",
    "firewall",
    "sso",
    "identity",
    "citrix",
    "netscaler",
    "fortinet",
    "fortios",
    "ivanti",
    "confluence",
    "gitlab",
    "exchange",
}

ATTACK_TACTICS = {"credential-access", "initial-access", "discovery", "persistence"}
STEALER_TAGS = {"redline", "vidar", "lumma", "raccoon", "stealer", "loader"}


def fetch_text(url: str, *, timeout: int = 45) -> str:
    request = Request(url, headers={"User-Agent": "Project-Omija-PublicContext/1.0"})
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def fetch_json(url: str, *, timeout: int = 45) -> Any:
    return json.loads(fetch_text(url, timeout=timeout))


def summarize_kev(feed: dict[str, Any]) -> dict[str, Any]:
    vulnerabilities = feed.get("vulnerabilities", [])
    access_relevant = []
    for item in vulnerabilities:
        haystack = " ".join(
            str(item.get(key, ""))
            for key in (
                "vendorProject",
                "product",
                "vulnerabilityName",
                "shortDescription",
                "requiredAction",
                "notes",
            )
        ).lower()
        if any(keyword in haystack for keyword in ACCESS_KEYWORDS):
            access_relevant.append(
                {
                    "cveID": item.get("cveID"),
                    "vendorProject": item.get("vendorProject"),
                    "product": item.get("product"),
                    "dateAdded": item.get("dateAdded"),
                    "vulnerabilityName": item.get("vulnerabilityName"),
                    "requiredAction": item.get("requiredAction"),
                }
            )
    access_relevant.sort(key=lambda row: row.get("dateAdded") or "", reverse=True)
    return {
        "source": CISA_KEV_JSON,
        "total_vulnerabilities": len(vulnerabilities),
        "access_relevant_count": len(access_relevant),
        "recent_access_relevant": access_relevant[:20],
    }


def summarize_nvd() -> dict[str, Any]:
    summaries = []
    for label, params in NVD_QUERIES:
        try:
            feed = fetch_json(f"{NVD_CVE_API}?{urlencode(params)}", timeout=30)
        except Exception as exc:  # noqa: BLE001 - public source availability varies.
            summaries.append({"label": label, "error": str(exc), "result_count": 0, "items": []})
            continue
        items = []
        for row in feed.get("vulnerabilities", [])[:8]:
            cve = row.get("cve", {})
            descriptions = cve.get("descriptions", [])
            description = next(
                (item.get("value") for item in descriptions if item.get("lang") == "en"),
                "",
            )
            metrics = cve.get("metrics", {})
            score = None
            severity = None
            for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV40"):
                if metrics.get(key):
                    data = metrics[key][0].get("cvssData", {})
                    score = data.get("baseScore")
                    severity = data.get("baseSeverity")
                    break
            items.append(
                {
                    "id": cve.get("id"),
                    "published": cve.get("published"),
                    "score": score,
                    "severity": severity,
                    "description": description[:180],
                }
            )
        summaries.append(
            {
                "label": label,
                "source": f"{NVD_CVE_API}?{urlencode(params)}",
                "total_results": feed.get("totalResults"),
                "result_count": len(items),
                "items": items,
            }
        )
    return {"queries": summaries}


def summarize_attack(feed: dict[str, Any]) -> dict[str, Any]:
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
            }
        )
    techniques.sort(key=lambda row: (row["id"] or "", row["name"] or ""))
    return {
        "source": MITRE_ATTACK_JSON,
        "selected_count": len(techniques),
        "selected_techniques": techniques[:40],
    }


def summarize_urlhaus(csv_text: str, *, max_rows: int = 1000) -> dict[str, Any]:
    rows: list[str] = []
    for line in csv_text.splitlines():
        if not line:
            continue
        if line.startswith("# id,"):
            rows.append(line[2:])
            continue
        if line.startswith("#"):
            continue
        rows.append(line)
    reader = csv.DictReader(StringIO("\n".join(rows)))
    tag_counts: Counter[str] = Counter()
    threat_counts: Counter[str] = Counter()
    stealer_or_loader_count = 0
    for index, row in enumerate(reader):
        if index >= max_rows:
            break
        tags = [tag.strip() for tag in (row.get("tags") or "").split(",") if tag.strip()]
        tag_counts.update(tags)
        if row.get("threat"):
            threat_counts.update([row["threat"]])
        if any(tag.lower() in STEALER_TAGS or "stealer" in tag.lower() for tag in tags):
            stealer_or_loader_count += 1
    return {
        "source": URLHAUS_RECENT_CSV,
        "sampled_rows": sum(threat_counts.values()),
        "top_tags": tag_counts.most_common(20),
        "top_threats": threat_counts.most_common(10),
        "stealer_or_loader_count": stealer_or_loader_count,
    }


def summarize_hibp(feed: list[dict[str, Any]]) -> dict[str, Any]:
    classes: Counter[str] = Counter()
    recent = []
    for breach in feed:
        classes.update(breach.get("DataClasses") or [])
        recent.append(
            {
                "Name": breach.get("Name"),
                "Title": breach.get("Title"),
                "BreachDate": breach.get("BreachDate"),
                "PwnCount": breach.get("PwnCount"),
                "DataClasses": breach.get("DataClasses", [])[:8],
            }
        )
    recent.sort(key=lambda row: row.get("BreachDate") or "", reverse=True)
    return {
        "source": HIBP_BREACHES,
        "breach_count": len(feed),
        "top_data_classes": classes.most_common(20),
        "recent_breaches": recent[:20],
    }


def build_summary() -> dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "public_context_snapshot_non_sensitive",
        "policy": {
            "raw_credentials": "not collected",
            "account_identifiers": "not collected",
            "malicious_urls": "not stored",
            "main_demo": "not automatically wired",
        },
        "cisa_kev": summarize_kev(fetch_json(CISA_KEV_JSON)),
        "nvd": summarize_nvd(),
        "mitre_attack": summarize_attack(fetch_json(MITRE_ATTACK_JSON)),
        "urlhaus": summarize_urlhaus(fetch_text(URLHAUS_RECENT_CSV)),
        "hibp": summarize_hibp(fetch_json(HIBP_BREACHES)),
    }


def render_markdown(summary: dict[str, Any]) -> str:
    kev = summary["cisa_kev"]
    attack = summary["mitre_attack"]
    urlhaus = summary["urlhaus"]
    hibp = summary["hibp"]
    nvd_lines = []
    for query in summary["nvd"]["queries"]:
        nvd_lines.append(
            f"- `{query['label']}`: {query.get('total_results', 0)} total, "
            f"{query.get('result_count', 0)} sampled"
        )
    return f"""# Public Context Snapshot

Generated: `{summary['generated_at']}`

This file summarizes non-sensitive public context only. It is not wired into
the main demo automatically.

## Counts

- CISA KEV total: `{kev['total_vulnerabilities']}`
- CISA KEV access-relevant: `{kev['access_relevant_count']}`
- MITRE ATT&CK selected techniques: `{attack['selected_count']}`
- URLhaus sampled rows: `{urlhaus['sampled_rows']}`
- URLhaus stealer/loader-tagged sample count: `{urlhaus['stealer_or_loader_count']}`
- HIBP public breach metadata count: `{hibp['breach_count']}`

## NVD Queries

{chr(10).join(nvd_lines)}

## Where This Fits

- KEV/NVD -> `Domain.asset_type`, `RiskAssessment.components.public_context`
- MITRE ATT&CK -> `ThreatSource.kind`, `RiskAssessment.components.techniques`
- URLhaus aggregate tags -> `ProgramExposure.components.threat_context`
- HIBP breach metadata -> presentation-only explanation of breach classes
"""


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = build_summary()
    OUT_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text(render_markdown(summary), encoding="utf-8")
    print(f"wrote {OUT_JSON.relative_to(REPO_ROOT)}")
    print(f"wrote {OUT_MD.relative_to(REPO_ROOT)}")
    print("RESULT: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
