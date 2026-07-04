"""Import locally collected candidate signals through the normalization boundary.

This script does not call any provider API. It reads an untracked JSONL file
produced by a private connector, normalizes supported exposure/device modules,
and writes redacted validation output for local review.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from adapter.base import normalize  # noqa: E402


DEFAULT_OUT_JSON = REPO_ROOT / "out" / "private_candidate_import.json"
DEFAULT_OUT_MD = REPO_ROOT / "out" / "private_candidate_import.md"
EXPOSURE_MODULES = {"cl", "cds", "ub", "cb"}
CONTEXT_MODULES = {"dt", "tt"}
RAW_SECRET_KEYS = {
    "password",
    "passwd",
    "pwd",
    "session_cookie",
    "cookie",
    "session",
    "token",
}


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{lineno}: invalid JSON: {exc}") from exc
        if not isinstance(record, dict):
            raise ValueError(f"{path}:{lineno}: expected object")
        records.append(record)
    return records


def _source_ref(module: str, raw: dict[str, Any]) -> str:
    for key in ("id", "_id", "record_id", "uuid"):
        value = raw.get(key)
        if value:
            return f"{module}:{value}"
    return f"{module}:missing-ref"


def _redact_raw(raw: dict[str, Any]) -> dict[str, Any]:
    redacted = {}
    for key, value in raw.items():
        if key.lower() in RAW_SECRET_KEYS:
            redacted[key] = "[redacted]"
        else:
            redacted[key] = value
    return redacted


def _threat_source(record: dict[str, Any], module: str) -> dict[str, Any]:
    raw = record.get("raw") or {}
    scope = record.get("scope") or {}
    return {
        "module": module,
        "source_ref": _source_ref(module, raw),
        "kind": "darkweb_context" if module == "dt" else "telegram_context",
        "query_type": scope.get("query_type"),
        "query_value": scope.get("query_value"),
        "matched_supplier": scope.get("supplier_id"),
        "matched_program": scope.get("program_ref"),
        "collected_at": record.get("collected_at"),
        "raw_redacted": _redact_raw(raw),
        "ontology_targets": ["ThreatSource"],
    }


def import_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    exposures = []
    threat_sources = []
    rejected = []

    for index, record in enumerate(records, 1):
        module = str(record.get("module", "")).lower()
        raw = record.get("raw") or {}
        if not module:
            rejected.append({"index": index, "reason": "missing module"})
            continue
        if not isinstance(raw, dict):
            rejected.append({"index": index, "module": module, "reason": "raw must be object"})
            continue
        if module in EXPOSURE_MODULES:
            exposure = normalize(module, raw)
            payload = asdict(exposure)
            payload["is_active_signal"] = exposure.is_active_signal
            payload["scope"] = record.get("scope") or {}
            payload["ontology_targets"] = ["CredentialExposure", "InfectedDevice", "Identity", "ThreatSource"]
            exposures.append(payload)
        elif module in CONTEXT_MODULES:
            threat_sources.append(_threat_source(record, module))
        else:
            rejected.append({"index": index, "module": module, "reason": "unsupported module"})

    modules = Counter(str(record.get("module", "")).lower() for record in records)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "local_private_candidate_import",
        "policy": {
            "provider_api_called": False,
            "raw_secret_output": "redacted",
            "git_tracking": "outputs intentionally ignored unless explicitly allowlisted",
        },
        "summary": {
            "input_records": len(records),
            "normalized_exposures": len(exposures),
            "threat_sources": len(threat_sources),
            "rejected": len(rejected),
            "modules": dict(sorted(modules.items())),
        },
        "normalized_exposures": exposures,
        "threat_sources": threat_sources,
        "rejected": rejected,
    }


def _contains_raw_secret(output: Any, raw_values: set[str]) -> list[str]:
    text = json.dumps(output, ensure_ascii=False, sort_keys=True)
    return sorted(value for value in raw_values if value and value in text)


def _raw_secret_values(records: list[dict[str, Any]]) -> set[str]:
    values = set()
    for record in records:
        raw = record.get("raw") or {}
        if not isinstance(raw, dict):
            continue
        for key, value in raw.items():
            if key.lower() in RAW_SECRET_KEYS and value:
                values.add(str(value))
    return values


def render_markdown(result: dict[str, Any]) -> str:
    summary = result["summary"]
    modules = "\n".join(f"- `{name}`: {count}" for name, count in summary["modules"].items())
    rejected = "\n".join(
        f"- index `{row.get('index')}` module `{row.get('module', '-')}`: {row.get('reason')}"
        for row in result["rejected"]
    ) or "- none"
    return f"""# Private Candidate Import

Generated: `{result['generated_at']}`

Mode: `{result['mode']}`

This file is local validation output. It should not contain raw password,
cookie, token, or session values.

## Summary

- Input records: `{summary['input_records']}`
- Normalized exposures: `{summary['normalized_exposures']}`
- Threat sources: `{summary['threat_sources']}`
- Rejected: `{summary['rejected']}`

## Modules

{modules}

## Rejected

{rejected}
"""


def run(input_path: Path, out_json: Path = DEFAULT_OUT_JSON, out_md: Path = DEFAULT_OUT_MD) -> int:
    records = _load_jsonl(input_path)
    result = import_records(records)
    leaked = _contains_raw_secret(result, _raw_secret_values(records))
    if leaked:
        raise RuntimeError(f"normalized output contains raw sensitive values: {len(leaked)}")
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    out_md.write_text(render_markdown(result), encoding="utf-8")
    print(f"wrote {out_json.relative_to(REPO_ROOT)}")
    print(f"wrote {out_md.relative_to(REPO_ROOT)}")
    print("RESULT: OK")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Local untracked candidate JSONL file.")
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    args = parser.parse_args(argv)
    return run(args.input, args.out_json, args.out_md)


if __name__ == "__main__":
    raise SystemExit(main())
