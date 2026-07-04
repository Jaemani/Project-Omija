"""Project-local Palantir MCP launcher for Claude Code.

Claude Code project MCP config should not store Foundry tokens. This wrapper
loads `.env`, normalizes the hostname, and execs the official Palantir MCP
stdio server.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key not in {"FOUNDRY_HOSTNAME", "FOUNDRY_TOKEN"}:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if value:
            os.environ.setdefault(key, value)


def foundry_api_url() -> str:
    host = os.environ.get("FOUNDRY_HOSTNAME", "").strip()
    if not host:
        raise SystemExit("FOUNDRY_HOSTNAME is required in .env")
    host = host.removeprefix("https://").removeprefix("http://").rstrip("/")
    return f"https://{host}"


def main() -> None:
    load_env(REPO_ROOT / ".env")
    if not os.environ.get("FOUNDRY_TOKEN"):
        raise SystemExit("FOUNDRY_TOKEN is required in .env")
    os.environ.setdefault("PALANTIR_MCP_TOOL_SEARCH", "true")
    os.execvp(
        "npx",
        [
            "npx",
            "-y",
            "palantir-mcp",
            "--tool-search",
            "--foundry-api-url",
            foundry_api_url(),
        ],
    )


if __name__ == "__main__":
    main()
