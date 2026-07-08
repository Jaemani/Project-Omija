"""Create schema-aware Foundry datasets for the live measurement bundle.

These datasets are separate from ontology backing datasets. They are used to
prove live StealthMole-approved rows can be materialized and measured inside
Foundry without exposing raw provider payloads or secret material.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.foundry_live_dataset_upload import DATASETS, LIVE_DIR  # noqa: E402
from scripts.foundry_live_schema_put import SCHEMAS  # noqa: E402


OUT_JSON = LIVE_DIR / "schema_dataset_create_result.json"
DEFAULT_FOLDER = "/Omija-e4b739/Omija/Seed"

PRIMARY_KEYS: dict[str, list[str]] = {
    "supplier": ["id"],
    "program": ["id"],
    "domain": ["fqdn"],
    "identity": ["id"],
    "credential_exposure": ["id"],
    "infected_device": ["id"],
    "threat_source": ["id"],
    "owns": ["left-Supplier-primary-key", "right-Domain-primary-key"],
    "belongs_to": ["left-Identity-primary-key", "right-Domain-primary-key"],
    "of": ["left-CredentialExposure-primary-key", "right-Identity-primary-key"],
    "targets": ["left-CredentialExposure-primary-key", "right-Domain-primary-key"],
    "sourced_from": ["left-CredentialExposure-primary-key", "right-ThreatSource-primary-key"],
    "leaked": ["left-InfectedDevice-primary-key", "right-CredentialExposure-primary-key"],
    "compromises": ["left-InfectedDevice-primary-key", "right-Identity-primary-key"],
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


class McpClient:
    def __init__(self) -> None:
        host = os.environ["FOUNDRY_HOSTNAME"].replace("https://", "").replace("http://", "").strip("/")
        self.proc = subprocess.Popen(
            ["npx", "-y", "palantir-mcp", "--foundry-api-url", f"https://{host}"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        self._next_id = 1
        self.rpc(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "codex", "version": "1.0"},
            },
        )

    def close(self) -> None:
        self.proc.terminate()

    def rpc(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        ident = self._next_id
        self._next_id += 1
        msg: dict[str, Any] = {"jsonrpc": "2.0", "id": ident, "method": method}
        if params is not None:
            msg["params"] = params
        assert self.proc.stdin is not None
        assert self.proc.stdout is not None
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()
        while True:
            line = self.proc.stdout.readline()
            if line:
                data = json.loads(line)
                if data.get("id") == ident:
                    return data
            if self.proc.poll() is not None:
                stderr = self.proc.stderr.read() if self.proc.stderr else ""
                raise RuntimeError(f"palantir-mcp exited early: {stderr[:1000]}")

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return self.rpc("tools/call", {"name": name, "arguments": arguments})


def schema_for_measurement(name: str) -> list[dict[str, object]]:
    # The standalone measurement datasets are for lineage/count queries, not
    # ontology mapping, so timestamp-like fields stay strings to avoid CSV date
    # parser drift between provider modules.
    converted: list[dict[str, object]] = []
    for column in SCHEMAS[name]:
        out = dict(column)
        if out["type"] == "date":
            out["type"] = "string"
        converted.append(out)
    return converted


def create_dataset(client: McpClient, name: str, run_id: str, folder: str) -> dict[str, Any]:
    target = DATASETS[name]
    dataset_name = f"live_measurement_{target.csv_name.removesuffix('.csv')}_{run_id}"
    args = {
        "foundryLocation": {"folderPath": folder},
        "name": dataset_name,
        "branch": "master",
        "schema": schema_for_measurement(name),
        "primaryKey": {"columns": PRIMARY_KEYS[name]},
        "csvFilePath": str(target.csv_path),
    }
    response = client.call_tool("create_and_write_to_foundry_dataset", args)
    text = response.get("result", {}).get("content", [{}])[0].get("text", "")
    dataset_rids = re.findall(
        r"ri\.foundry\.main\.dataset\.[0-9a-f-]+",
        json.dumps(response, ensure_ascii=False),
    )
    return {
        "name": name,
        "dataset_name": dataset_name,
        "dataset_rid": dataset_rids[0] if dataset_rids else None,
        "source_csv": str(target.csv_path.relative_to(ROOT)),
        "rows_expected": sum(1 for _ in target.csv_path.open(encoding="utf-8")) - 1,
        "ok": not response.get("result", {}).get("isError", False),
        "response_preview": text[:1200],
        "response": response,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder", default=DEFAULT_FOLDER)
    parser.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"))
    parser.add_argument("--only", choices=sorted(DATASETS), default=None)
    args = parser.parse_args(argv)

    load_env()
    if not os.environ.get("FOUNDRY_HOSTNAME") or not os.environ.get("FOUNDRY_TOKEN"):
        print("FOUNDRY_HOSTNAME / FOUNDRY_TOKEN not configured; aborting.")
        return 1

    names = [args.only] if args.only else list(DATASETS)
    client = McpClient()
    try:
        results = [create_dataset(client, name, args.run_id, args.folder) for name in names]
    finally:
        client.close()

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "folder": args.folder,
        "run_id": args.run_id,
        "target_count": len(results),
        "ok_count": sum(1 for row in results if row.get("ok")),
        "results": results,
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    for row in results:
        print(f"{row['dataset_name']}: ok={row['ok']} rows={row['rows_expected']}")
    print(f"wrote {OUT_JSON.relative_to(ROOT)}")
    print("RESULT: OK" if payload["ok_count"] == payload["target_count"] else "RESULT: PARTIAL")
    return 0 if payload["ok_count"] == payload["target_count"] else 2


if __name__ == "__main__":
    sys.exit(main())
