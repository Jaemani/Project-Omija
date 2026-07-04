"""Collect non-sensitive public context summaries for Omija.

This script deliberately avoids credential/leak feeds. It fetches public,
defensive context that can explain why target asset classes matter:

- CISA KEV
- NVD CVE search results
- MITRE ATT&CK techniques
- URLhaus aggregate feed metadata
- HIBP breach metadata
- FIRST EPSS high-probability CVE metadata
- CISA advisory RSS counts

Outputs summaries only. Raw malicious URLs, credentials, cookies, tokens, and
account identifiers are not stored.
"""

from __future__ import annotations

import csv
import json
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any, Callable
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
FIRST_EPSS_API = "https://api.first.org/data/v1/epss"
CISA_ADVISORY_ALL_RSS = "https://www.cisa.gov/cybersecurity-advisories/all.xml"
CISA_ICS_ADVISORY_RSS = "https://www.cisa.gov/cybersecurity-advisories/ics-advisories.xml"

NVD_QUERIES = [
    ("vpn", {"keywordSearch": "vpn", "cvssV3Severity": "CRITICAL", "resultsPerPage": "20"}),
    ("sso", {"keywordSearch": "single sign on", "cvssV3Severity": "HIGH", "resultsPerPage": "20"}),
    ("citrix", {"keywordSearch": "citrix", "resultsPerPage": "20"}),
    ("fortinet", {"keywordSearch": "fortinet", "resultsPerPage": "20"}),
    ("ivanti", {"keywordSearch": "ivanti", "resultsPerPage": "20"}),
]

ACCESS_KEYWORDS = {
    "vpn",
    "sso",
    "single sign",
    "authentication",
    "credential",
    "password",
    "session",
    "cookie",
    "firewall",
    "remote",
    "citrix",
    "fortinet",
    "ivanti",
    "exchange",
    "mail",
    "mfa",
    "identity",
}
ATTACK_TACTICS = {"credential-access", "initial-access"}
STEALER_TAGS = {
    "agenttesla",
    "formbook",
    "infostealer",
    "loader",
    "lumma",
    "redline",
    "stealc",
    "stealer",
    "vidar",
}


def fetch_text(url: str, *, timeout: int = 45) -> str:
    request = Request(url, headers={"User-Agent": "Project-Omija-PublicContext/1.0"})
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def fetch_json(url: str, *, timeout: int = 45) -> Any:
    return json.loads(fetch_text(url, timeout=timeout))


def safe_summary(name: str, fn: Callable[[], dict[str, Any]], fallback: dict[str, Any]) -> dict[str, Any]:
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001 - public source availability varies.
        result = dict(fallback)
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["source"] = result.get("source", name)
        return result


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


def summarize_epss() -> dict[str, Any]:
    params = {"epss-gt": "0.95", "order": "!epss", "limit": "20"}
    feed = fetch_json(f"{FIRST_EPSS_API}?{urlencode(params)}", timeout=30)
    rows = feed.get("data", [])
    return {
        "source": f"{FIRST_EPSS_API}?{urlencode(params)}",
        "high_probability_total": feed.get("total", 0),
        "sampled_count": len(rows),
        "sampled": [
            {
                "cve": row.get("cve"),
                "epss": row.get("epss"),
                "percentile": row.get("percentile"),
                "date": row.get("date"),
            }
            for row in rows
        ],
    }


def parse_rss(xml_text: str, *, source: str) -> dict[str, Any]:
    root = ET.fromstring(xml_text)
    items = root.findall("./channel/item")
    access_relevant = []
    recent = []
    for item in items[:80]:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip()
        description = (item.findtext("description") or "").strip()
        compact = " ".join((title, description)).lower()
        row = {"title": title, "link": link, "pubDate": pub_date}
        recent.append(row)
        if any(keyword in compact for keyword in ACCESS_KEYWORDS):
            access_relevant.append(row)
    return {
        "source": source,
        "total_items_sampled": len(items[:80]),
        "access_relevant_count": len(access_relevant),
        "recent": recent[:12],
        "recent_access_relevant": access_relevant[:12],
    }


def summarize_cisa_advisories() -> dict[str, Any]:
    all_advisories = parse_rss(fetch_text(CISA_ADVISORY_ALL_RSS, timeout=30), source=CISA_ADVISORY_ALL_RSS)
    ics_advisories = parse_rss(fetch_text(CISA_ICS_ADVISORY_RSS, timeout=30), source=CISA_ICS_ADVISORY_RSS)
    return {
        "all": all_advisories,
        "ics": ics_advisories,
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
        "cisa_kev": safe_summary(
            "cisa_kev",
            lambda: summarize_kev(fetch_json(CISA_KEV_JSON)),
            {"source": CISA_KEV_JSON, "total_vulnerabilities": 0, "access_relevant_count": 0, "recent_access_relevant": []},
        ),
        "nvd": safe_summary("nvd", summarize_nvd, {"queries": []}),
        "mitre_attack": safe_summary(
            "mitre_attack",
            lambda: summarize_attack(fetch_json(MITRE_ATTACK_JSON)),
            {"source": MITRE_ATTACK_JSON, "selected_count": 0, "selected_techniques": []},
        ),
        "urlhaus": safe_summary(
            "urlhaus",
            lambda: summarize_urlhaus(fetch_text(URLHAUS_RECENT_CSV)),
            {"source": URLHAUS_RECENT_CSV, "sampled_rows": 0, "top_tags": [], "top_threats": [], "stealer_or_loader_count": 0},
        ),
        "hibp": safe_summary(
            "hibp",
            lambda: summarize_hibp(fetch_json(HIBP_BREACHES)),
            {"source": HIBP_BREACHES, "breach_count": 0, "top_data_classes": [], "recent_breaches": []},
        ),
        "first_epss": safe_summary(
            "first_epss",
            summarize_epss,
            {"source": FIRST_EPSS_API, "high_probability_total": 0, "sampled_count": 0, "sampled": []},
        ),
        "cisa_advisories": safe_summary(
            "cisa_advisories",
            summarize_cisa_advisories,
            {"all": {"total_items_sampled": 0, "access_relevant_count": 0}, "ics": {"total_items_sampled": 0, "access_relevant_count": 0}},
        ),
    }


def render_markdown(summary: dict[str, Any]) -> str:
    kev = summary["cisa_kev"]
    attack = summary["mitre_attack"]
    urlhaus = summary["urlhaus"]
    hibp = summary["hibp"]
    epss = summary["first_epss"]
    advisories = summary["cisa_advisories"]
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

- CISA KEV total: `{kev.get('total_vulnerabilities', 0)}`
- CISA KEV access-relevant: `{kev.get('access_relevant_count', 0)}`
- MITRE ATT&CK selected techniques: `{attack.get('selected_count', 0)}`
- URLhaus sampled rows: `{urlhaus.get('sampled_rows', 0)}`
- URLhaus stealer/loader-tagged sample count: `{urlhaus.get('stealer_or_loader_count', 0)}`
- HIBP public breach metadata count: `{hibp.get('breach_count', 0)}`
- FIRST EPSS probability > 0.95 total: `{epss.get('high_probability_total', 0)}`
- CISA advisory RSS sampled: `{advisories.get('all', {}).get('total_items_sampled', 0)}`
- CISA advisory RSS access-relevant: `{advisories.get('all', {}).get('access_relevant_count', 0)}`
- CISA ICS advisory RSS sampled: `{advisories.get('ics', {}).get('total_items_sampled', 0)}`

## NVD Queries

{chr(10).join(nvd_lines)}

## Where Fits

- KEV/NVD/EPSS -> `Domain.asset_type`, `RiskAssessment.components.public_context`
- CISA advisories -> `ThreatSource.kind`, `ProgramExposure.components.public_advisory_context`
- MITRE ATT&CK -> `ThreatSource.kind`, `RiskAssessment.components.techniques`
- URLhaus aggregate tags -> `ProgramExposure.components.threat_context`
- HIBP breach metadata -> presentation-only explanation of breach data classes
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
