"""Attach explicit schemas to live-measurement Foundry datasets.

The file-upload endpoint accepts CSVs as raw files but does not guarantee a
tabular dataset schema. Ontology datasource-backed objects require schemas, so
run this after ``foundry_live_dataset_upload.py``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.foundry_live_dataset_upload import DATASETS, LIVE_DIR, ROOT


OUT_JSON = LIVE_DIR / "schema_put_result.json"


Column = dict[str, object]


def col(name: str, type_: str, *, nullable: bool = True) -> Column:
    return {"name": name, "type": type_, "nullable": nullable}


SCHEMAS: dict[str, list[Column]] = {
    "supplier": [
        col("id", "string", nullable=False),
        col("name", "string"),
        col("tier", "integer"),
        col("criticality", "string"),
        col("status", "string"),
        col("is_prime_candidate", "boolean"),
    ],
    "program": [
        col("id", "string", nullable=False),
        col("name", "string"),
        col("sensitivity", "string"),
        col("status", "string"),
    ],
    "domain": [
        col("fqdn", "string", nullable=False),
        col("host", "string"),
        col("url", "string"),
        col("asset_type", "string"),
        col("criticality", "string"),
        col("access_surface", "string"),
        col("verified_at", "date"),
    ],
    "identity": [
        col("id", "string", nullable=False),
        col("email", "string"),
        col("username", "string"),
        col("canonical_handle", "string"),
        col("account_type", "string"),
        col("status", "string"),
        col("merged_into", "string"),
    ],
    "credential_exposure": [
        col("id", "string", nullable=False),
        col("module", "string"),
        col("secret_type", "string"),
        col("secret_present", "boolean"),
        col("masked_value", "string"),
        col("secret_fingerprint", "string"),
        col("first_seen", "date"),
        col("last_seen", "date"),
        col("source_ref", "string"),
        col("confidence", "double"),
        col("status", "string"),
    ],
    "infected_device": [
        col("id", "string", nullable=False),
        col("device_fingerprint", "string"),
        col("malware", "string"),
        col("infected_at", "date"),
        col("has_session_cookie", "boolean"),
        col("os", "string"),
        col("status", "string"),
    ],
    "threat_source": [
        col("id", "string", nullable=False),
        col("kind", "string"),
        col("name", "string"),
        col("collected_at", "date"),
        col("reliability", "double"),
        col("status", "string"),
    ],
    "owns": [
        col("left-Supplier-primary-key", "string", nullable=False),
        col("right-Domain-primary-key", "string", nullable=False),
    ],
    "belongs_to": [
        col("left-Identity-primary-key", "string", nullable=False),
        col("right-Domain-primary-key", "string", nullable=False),
    ],
    "of": [
        col("left-CredentialExposure-primary-key", "string", nullable=False),
        col("right-Identity-primary-key", "string", nullable=False),
    ],
    "targets": [
        col("left-CredentialExposure-primary-key", "string", nullable=False),
        col("right-Domain-primary-key", "string", nullable=False),
    ],
    "sourced_from": [
        col("left-CredentialExposure-primary-key", "string", nullable=False),
        col("right-ThreatSource-primary-key", "string", nullable=False),
    ],
    "leaked": [
        col("left-InfectedDevice-primary-key", "string", nullable=False),
        col("right-CredentialExposure-primary-key", "string", nullable=False),
    ],
    "compromises": [
        col("left-InfectedDevice-primary-key", "string", nullable=False),
        col("right-Identity-primary-key", "string", nullable=False),
    ],
}


def load_env(path: Path = ROOT / ".env") -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = value


def request(method: str, path: str, *, body: dict[str, object] | None = None) -> tuple[int, bytes]:
    host = os.environ["FOUNDRY_HOSTNAME"].replace("https://", "").strip("/")
    token = os.environ["FOUNDRY_TOKEN"]
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(f"https://{host}/api/v2/{path}", data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def put_schema(name: str) -> dict[str, object]:
    target = DATASETS[name]
    body = {
        "branchName": "master",
        "schema": {"fieldSchemaList": SCHEMAS[name]},
    }
    status, raw = request("PUT", f"datasets/{target.dataset_rid}/putSchema", body=body)
    return {
        "name": name,
        "category": target.category,
        "dataset_rid": target.dataset_rid,
        "csv": str(target.csv_path.relative_to(ROOT)),
        "http_status": status,
        "ok": status == 200,
        "body_preview": raw[:300].decode("utf-8", errors="replace"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", choices=sorted(SCHEMAS), default=None)
    args = parser.parse_args(argv)

    load_env()
    if not os.environ.get("FOUNDRY_HOSTNAME") or not os.environ.get("FOUNDRY_TOKEN"):
        print("FOUNDRY_HOSTNAME / FOUNDRY_TOKEN not configured; aborting.")
        return 1

    names = [args.only] if args.only else list(DATASETS)
    results = [put_schema(name) for name in names]
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "put explicit tabular schemas on existing live-measurement backing datasets",
        "target_count": len(results),
        "ok_count": sum(1 for row in results if row.get("ok")),
        "results": results,
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    for row in results:
        print(f"{row['name']}: {row['http_status']} ok={row['ok']}")
    print(f"wrote {OUT_JSON.relative_to(ROOT)}")
    print("RESULT: OK" if payload["ok_count"] == payload["target_count"] else "RESULT: PARTIAL")
    return 0 if payload["ok_count"] == payload["target_count"] else 2


if __name__ == "__main__":
    sys.exit(main())
