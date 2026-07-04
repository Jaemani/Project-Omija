"""Re-upload seed CSVs to their backing Foundry datasets (SNAPSHOT).

The repo's out/foundry_seed/*.csv files are the source of truth; when a seed
id is renamed locally (e.g. the 2026-07-05 vendor-neutral rename to
src:candidate:empty) the Foundry datasets must be re-synced or OSDK readback
fails. Dataset RIDs below were resolved from the ontology's datasource
definitions (not by folder-name matching — the project folder contains
same-named stale datasets).

Usage: uv run python scripts/foundry_dataset_upload.py [--only threat_source]
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# mirror foundry_osdk_smoke's hand-rolled .env loading (no dotenv dependency)
_env_file = ROOT / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
            continue
        _key, _, _value = _line.partition("=")
        _key, _value = _key.strip(), _value.strip().strip('"').strip("'")
        if _key and _key not in os.environ:
            os.environ[_key] = _value

HOST = os.environ.get("FOUNDRY_HOSTNAME", "").replace("https://", "").strip("/")
TOKEN = os.environ.get("FOUNDRY_TOKEN", "")

# csv (relative to repo root) -> backing dataset rid (from ontology datasources)
DATASETS = {
    "threat_source": (
        "out/foundry_seed/08_threat_source.csv",
        "ri.foundry.main.dataset.4558faa7-e05e-4de6-af86-9010fd899a8f",
    ),
    "credential_exposure": (
        "out/foundry_seed/06_credential_exposure.csv",
        "ri.foundry.main.dataset.7a4d3db0-a649-4d05-936f-b67593f9a79d",
    ),
    "link_sourced_from": (
        "out/foundry_seed/28_link_sourced_from.csv",
        "ri.foundry.main.dataset.ea8ea557-af14-4d8c-9e74-b7cc7e43c886",
    ),
}


def _req(method: str, path: str, body: bytes | None = None,
         content_type: str = "application/json") -> tuple[int, bytes]:
    url = f"https://{HOST}/api/v2/{path}"
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", f"Bearer {TOKEN}")
    if body is not None:
        req.add_header("Content-Type", content_type)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:  # keep body for diagnostics, no headers
        return e.code, e.read()


def existing_file_name(dataset_rid: str) -> str | None:
    status, body = _req("GET", f"datasets/{dataset_rid}/files?branchName=master")
    if status != 200:
        return None
    import json

    files = json.loads(body).get("data", [])
    return files[0]["path"] if files else None


def upload(name: str, csv_rel: str, dataset_rid: str) -> bool:
    csv_path = ROOT / csv_rel
    if not csv_path.exists():
        print(f"[{name}] MISSING local csv: {csv_rel}")
        return False
    file_name = existing_file_name(dataset_rid) or csv_path.name
    quoted = urllib.parse.quote(file_name, safe="")
    path = (
        f"datasets/{dataset_rid}/files/{quoted}/upload"
        f"?branchName=master&transactionType=SNAPSHOT"
    )
    status, body = _req("POST", path, csv_path.read_bytes(),
                        content_type="application/octet-stream")
    ok = status in (200, 204)
    print(f"[{name}] upload as '{file_name}' -> HTTP {status}"
          + ("" if ok else f" body={body[:200]!r}"))
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=sorted(DATASETS), default=None)
    args = ap.parse_args()

    if not HOST or not TOKEN:
        print("FOUNDRY_HOSTNAME / FOUNDRY_TOKEN not configured; aborting.")
        return 1

    targets = {args.only: DATASETS[args.only]} if args.only else DATASETS
    results = [upload(n, csv, rid) for n, (csv, rid) in targets.items()]
    if not all(results):
        print("RESULT: FAIL")
        return 2
    print("RESULT: UPLOADED (object index refresh may take a minute)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
