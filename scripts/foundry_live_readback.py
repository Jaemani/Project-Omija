"""Read back uploaded live-measurement objects through the generated Foundry OSDK."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.foundry_osdk_smoke import (  # noqa: E402
    ReadSpec,
    SmokeFailure,
    build_client,
    load_env_file,
    object_key,
    read_object,
)


LIVE_DIR = ROOT / "out" / "foundry_live_measurement"
OUT_JSON = LIVE_DIR / "readback_result.json"


@dataclass(frozen=True)
class ReadTarget:
    object_type: str
    csv_name: str
    primary_key_field: str


READ_TARGETS: dict[str, ReadTarget] = {
    "supplier": ReadTarget("Supplier", "01_supplier.csv", "id"),
    "program": ReadTarget("Program", "03_program.csv", "id"),
    "domain": ReadTarget("Domain", "04_domain.csv", "fqdn"),
    "identity": ReadTarget("Identity", "05_identity.csv", "id"),
    "credential_exposure": ReadTarget("CredentialExposure", "06_credential_exposure.csv", "id"),
    "infected_device": ReadTarget("InfectedDevice", "07_infected_device.csv", "id"),
    "threat_source": ReadTarget("ThreatSource", "08_threat_source.csv", "id"),
}


def first_id(csv_name: str, field: str) -> str:
    path = LIVE_DIR / csv_name
    with path.open(newline="", encoding="utf-8") as handle:
        row = next(csv.DictReader(handle))
    return row[field]


def try_read(client: Any, target: ReadTarget) -> dict[str, Any]:
    primary_key = first_id(target.csv_name, target.primary_key_field)
    try:
        obj = read_object(client, ReadSpec(target.object_type, primary_key))
    except Exception as exc:  # noqa: BLE001 - diagnostic artifact.
        return {
            "object_type": target.object_type,
            "csv": target.csv_name,
            "primary_key": primary_key,
            "ok": False,
            "error": type(exc).__name__,
            "message": str(exc),
        }
    return {
        "object_type": target.object_type,
        "csv": target.csv_name,
        "primary_key": primary_key,
        "ok": True,
        "readback_key": object_key(obj),
    }


def select_targets(args: argparse.Namespace) -> dict[str, ReadTarget]:
    if args.only:
        return {args.only: READ_TARGETS[args.only]}
    return READ_TARGETS


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--only", choices=sorted(READ_TARGETS), default=None)
    args = parser.parse_args(argv)

    load_env_file(args.env_file)
    client_args = SimpleNamespace(
        client_factory=None,
        module=None,
        client=None,
        auth=None,
    )

    try:
        client = build_client(client_args)
        results = [try_read(client, target) for target in select_targets(args).values()]
    except SmokeFailure as exc:
        results = [
            {
                "object_type": "client",
                "ok": False,
                "error": "SmokeFailure",
                "message": str(exc),
            }
        ]

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_dir": str(LIVE_DIR.relative_to(ROOT)),
        "ok": all(row.get("ok") for row in results),
        "readback_count": sum(1 for row in results if row.get("ok")),
        "target_count": len(results),
        "results": results,
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    for row in results:
        print(f"{row['object_type']}: ok={row.get('ok')} {row.get('error', '')}")
    print(f"wrote {OUT_JSON.relative_to(ROOT)}")
    print("RESULT: OK" if payload["ok"] else "RESULT: NOT_INDEXED")
    return 0 if payload["ok"] else 2


if __name__ == "__main__":
    sys.exit(main())
