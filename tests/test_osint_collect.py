from scripts.osint_collect import summarize_kev, summarize_nvd, summarize_urlhaus


def test_summarize_kev_selects_access_relevant_items():
    feed = {
        "catalogVersion": "test",
        "dateReleased": "now",
        "vulnerabilities": [
            {
                "cveID": "CVE-1",
                "vendorProject": "Fortinet",
                "product": "FortiOS",
                "vulnerabilityName": "VPN issue",
                "dateAdded": "2026-01-02",
            },
            {
                "cveID": "CVE-2",
                "vendorProject": "Unrelated",
                "product": "Printer",
                "vulnerabilityName": "Local issue",
                "dateAdded": "2026-01-01",
            },
        ],
    }

    summary = summarize_kev(feed)

    assert summary["total_vulnerabilities"] == 2
    assert summary["access_relevant_count"] == 1
    assert summary["recent_access_relevant"][0]["cveID"] == "CVE-1"


def test_summarize_nvd_extracts_cvss_and_description():
    feed = {
        "totalResults": 1,
        "vulnerabilities": [
            {
                "cve": {
                    "id": "CVE-2026-0001",
                    "published": "2026-01-01T00:00:00.000",
                    "lastModified": "2026-01-02T00:00:00.000",
                    "descriptions": [{"lang": "en", "value": "Critical VPN bug"}],
                    "metrics": {
                        "cvssMetricV31": [
                            {"cvssData": {"baseScore": 9.8, "baseSeverity": "CRITICAL"}}
                        ]
                    },
                }
            }
        ],
    }

    summary = summarize_nvd(feed)

    assert summary["total_results"] == 1
    assert summary["critical_vpn_cves"][0]["id"] == "CVE-2026-0001"
    assert summary["critical_vpn_cves"][0]["baseScore"] == 9.8


def test_summarize_urlhaus_counts_tags_and_stealer_rows():
    csv_text = """# comment
id,dateadded,url,url_status,last_online,threat,tags,urlhaus_link,reporter
"1","2026-01-01","http://x","online","","malware_download","RedLine,stealer","https://u/1","r"
"2","2026-01-01","http://y","online","","malware_download","elf","https://u/2","r"
"""

    summary = summarize_urlhaus(csv_text)

    assert summary["sampled_rows"] == 2
    assert summary["stealer_or_loader_count"] == 1
    assert ("RedLine", 1) in summary["top_tags"]
