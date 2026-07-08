"""Run Foundry SQL counts against schema-aware live measurement datasets."""

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
LIVE_DIR = ROOT / "out" / "foundry_live_measurement"
CREATE_JSON = LIVE_DIR / "schema_dataset_create_result.json"
OUT_JSON = LIVE_DIR / "sql_measurement_result.json"


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


def dataset_rid(row: dict[str, Any]) -> str:
    if row.get("dataset_rid"):
        return str(row["dataset_rid"])
    text = json.dumps(row.get("response", {}), ensure_ascii=False)
    matches = re.findall(r"ri\.foundry\.main\.dataset\.[0-9a-f-]+", text)
    if not matches:
        raise ValueError(f"dataset RID not found for {row.get('name')}")
    return matches[0]


def extract_count(response: dict[str, Any]) -> int | None:
    text = response.get("result", {}).get("content", [{}])[0].get("text", "")
    match = re.search(r"\|\s*(\d+)\s*\|", text)
    return int(match.group(1)) if match else None


def run_count(client: McpClient, row: dict[str, Any]) -> dict[str, Any]:
    rid = dataset_rid(row)
    query = f"SELECT COUNT(*) AS c FROM `{rid}`"
    response = client.call_tool(
        "run_sql_query_on_foundry_dataset",
        {"sqlQuery": query, "rowLimit": 5},
    )
    count = extract_count(response)
    expected = row.get("rows_expected")
    return {
        "name": row.get("name"),
        "dataset_name": row.get("dataset_name"),
        "dataset_rid": rid,
        "rows_expected": expected,
        "sql_count": count,
        "ok": count == expected,
        "response_preview": response.get("result", {}).get("content", [{}])[0].get("text", "")[:500],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=str(CREATE_JSON))
    args = parser.parse_args(argv)

    load_env()
    if not os.environ.get("FOUNDRY_HOSTNAME") or not os.environ.get("FOUNDRY_TOKEN"):
        print("FOUNDRY_HOSTNAME / FOUNDRY_TOKEN not configured; aborting.")
        return 1

    source = Path(args.input)
    created = json.loads(source.read_text(encoding="utf-8"))
    rows = [row for row in created.get("results", []) if row.get("ok")]

    client = McpClient()
    try:
        results = [run_count(client, row) for row in rows]
    finally:
        client.close()

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": str(source.relative_to(ROOT)),
        "run_id": created.get("run_id"),
        "target_count": len(results),
        "ok_count": sum(1 for row in results if row.get("ok")),
        "results": results,
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    for row in results:
        print(f"{row['name']}: sql_count={row['sql_count']} expected={row['rows_expected']} ok={row['ok']}")
    print(f"wrote {OUT_JSON.relative_to(ROOT)}")
    print("RESULT: OK" if payload["ok_count"] == payload["target_count"] else "RESULT: PARTIAL")
    return 0 if payload["ok_count"] == payload["target_count"] else 2


if __name__ == "__main__":
    sys.exit(main())
