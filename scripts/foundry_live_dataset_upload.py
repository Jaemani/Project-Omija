"""Upload the sanitized live-measurement CSV bundle to Foundry backing datasets.

This script only reads public-safe CSVs under ``out/foundry_live_measurement``.
It never reads ``data/private_candidates`` and never prints Foundry tokens or
provider secrets.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LIVE_DIR = ROOT / "out" / "foundry_live_measurement"
OUT_JSON = LIVE_DIR / "upload_result.json"


@dataclass(frozen=True)
class DatasetTarget:
    csv_name: str
    dataset_rid: str
    category: str

    @property
    def csv_path(self) -> Path:
        return LIVE_DIR / self.csv_name


DATASETS: dict[str, DatasetTarget] = {
    "supplier": DatasetTarget(
        "01_supplier.csv",
        "ri.foundry.main.dataset.a0b5ad66-08a2-4832-b1e5-9cf0c0cc50b5",
        "object",
    ),
    "program": DatasetTarget(
        "03_program.csv",
        "ri.foundry.main.dataset.78093ab2-406f-4887-8a37-dd160e0524b0",
        "object",
    ),
    "domain": DatasetTarget(
        "04_domain.csv",
        "ri.foundry.main.dataset.aabf581c-51b9-45d8-bbe5-6d491d53930e",
        "object",
    ),
    "identity": DatasetTarget(
        "05_identity.csv",
        "ri.foundry.main.dataset.33284285-d32a-44fa-a511-b404a0ed7f52",
        "object",
    ),
    "credential_exposure": DatasetTarget(
        "06_credential_exposure.csv",
        "ri.foundry.main.dataset.7a4d3db0-a649-4d05-936f-b67593f9a79d",
        "object",
    ),
    "infected_device": DatasetTarget(
        "07_infected_device.csv",
        "ri.foundry.main.dataset.4966e27f-e540-43d7-9a57-c8c1bddaab70",
        "object",
    ),
    "threat_source": DatasetTarget(
        "08_threat_source.csv",
        "ri.foundry.main.dataset.4558faa7-e05e-4de6-af86-9010fd899a8f",
        "object",
    ),
    "owns": DatasetTarget(
        "23_link_owns.csv",
        "ri.foundry.main.dataset.e9013808-7d72-47c0-bca9-af6ece44907c",
        "link",
    ),
    "belongs_to": DatasetTarget(
        "25_link_belongs_to.csv",
        "ri.foundry.main.dataset.a0b1f94e-f72c-4adb-81ad-61f8105e0d9c",
        "link",
    ),
    "of": DatasetTarget(
        "26_link_of.csv",
        "ri.foundry.main.dataset.23f1a49e-770a-4a02-a4de-172161808bf8",
        "link",
    ),
    "targets": DatasetTarget(
        "27_link_targets.csv",
        "ri.foundry.main.dataset.e6a2583b-4174-4721-8d33-00fee045c629",
        "link",
    ),
    "sourced_from": DatasetTarget(
        "28_link_sourced_from.csv",
        "ri.foundry.main.dataset.ea8ea557-af14-4d8c-9e74-b7cc7e43c886",
        "link",
    ),
    "leaked": DatasetTarget(
        "29_link_leaked.csv",
        "ri.foundry.main.dataset.47c0b157-b1eb-4041-b14b-eb59000f7877",
        "link",
    ),
    "compromises": DatasetTarget(
        "30_link_compromises.csv",
        "ri.foundry.main.dataset.428466cf-94e3-4813-8aa6-9e75b5274d8f",
        "link",
    ),
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


def request(
    method: str,
    path: str,
    *,
    data: bytes | None = None,
    content_type: str = "application/json",
) -> tuple[int, bytes]:
    host = os.environ["FOUNDRY_HOSTNAME"].replace("https://", "").strip("/")
    token = os.environ["FOUNDRY_TOKEN"]
    req = urllib.request.Request(f"https://{host}/api/v2/{path}", data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", content_type)
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def existing_file_name(dataset_rid: str, fallback: str) -> str:
    status, body = request("GET", f"datasets/{dataset_rid}/files?branchName=master")
    if status == 200:
        files = json.loads(body).get("data", [])
        if files:
            return str(files[0]["path"])
    return fallback


def row_count(csv_path: Path) -> int:
    with csv_path.open(encoding="utf-8") as handle:
        return max(sum(1 for _ in handle) - 1, 0)


def upload(name: str, target: DatasetTarget) -> dict[str, object]:
    if not target.csv_path.exists():
        return {
            "name": name,
            "category": target.category,
            "csv": str(target.csv_path.relative_to(ROOT)),
            "dataset_rid": target.dataset_rid,
            "ok": False,
            "status": "missing_csv",
        }

    file_name = existing_file_name(target.dataset_rid, target.csv_name)
    quoted = urllib.parse.quote(file_name, safe="")
    status, body = request(
        "POST",
        (
            f"datasets/{target.dataset_rid}/files/{quoted}/upload"
            "?branchName=master&transactionType=SNAPSHOT"
        ),
        data=target.csv_path.read_bytes(),
        content_type="application/octet-stream",
    )
    return {
        "name": name,
        "category": target.category,
        "csv": str(target.csv_path.relative_to(ROOT)),
        "dataset_rid": target.dataset_rid,
        "file_name": file_name,
        "rows": row_count(target.csv_path),
        "http_status": status,
        "ok": status in (200, 204),
        "body_preview": body[:200].decode("utf-8", errors="replace"),
    }


def select_targets(args: argparse.Namespace) -> dict[str, DatasetTarget]:
    if args.only:
        return {args.only: DATASETS[args.only]}
    if args.category:
        return {name: target for name, target in DATASETS.items() if target.category == args.category}
    return DATASETS


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", choices=sorted(DATASETS), default=None)
    parser.add_argument("--category", choices=("object", "link"), default=None)
    args = parser.parse_args(argv)

    load_env()
    if not os.environ.get("FOUNDRY_HOSTNAME") or not os.environ.get("FOUNDRY_TOKEN"):
        print("FOUNDRY_HOSTNAME / FOUNDRY_TOKEN not configured; aborting.")
        return 1

    targets = select_targets(args)
    results = [upload(name, target) for name, target in targets.items()]
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "full sanitized live-measurement bundle",
        "source_dir": str(LIVE_DIR.relative_to(ROOT)),
        "target_count": len(results),
        "uploaded_count": sum(1 for row in results if row.get("ok")),
        "results": results,
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    for row in results:
        status = row.get("http_status", row.get("status"))
        print(f"{row['name']}: {status} rows={row.get('rows', 0)} ok={row.get('ok', False)}")
    print(f"wrote {OUT_JSON.relative_to(ROOT)}")
    if not all(bool(row.get("ok")) for row in results):
        print("RESULT: PARTIAL")
        return 2
    print("RESULT: UPLOADED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
