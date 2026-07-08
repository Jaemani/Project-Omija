"""Import locally collected candidate signals through the normalization boundary.

This script does not call any provider API. It reads an untracked JSONL file
produced by the private connector, normalizes supported exposure/device modules,
and writes redacted validation output for local review.
"""

from __future__ import annotations

import argparse
import hashlib
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
    "access_token",
    "refresh_token",
    "jwt",
    "authorization",
    "bearer",
    "payload",
    "raw_payload",
}


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
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


def _hash_text(value: Any) -> str:
    text = "" if value is None else str(value)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _redact_raw(raw: dict[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in raw.items():
        if key.lower() in RAW_SECRET_KEYS:
            redacted[key] = "[redacted]"
        else:
            redacted[key] = value
    return redacted


def _removed_secret_fields(raw: dict[str, Any]) -> list[str]:
    return sorted(key for key, value in raw.items() if key.lower() in RAW_SECRET_KEYS and value)


def _scope(record: dict[str, Any]) -> dict[str, Any]:
    scope = record.get("scope") or {}
    if not isinstance(scope, dict):
        return {}
    return dict(scope)


def _threat_source(record: dict[str, Any], module: str) -> dict[str, Any]:
    raw = record.get("raw") or {}
    scope = _scope(record)
    source_ref = _source_ref(module, raw)
    return {
        "module": module,
        "source_ref": source_ref,
        "source_ref_hash": _hash_text(source_ref),
        "kind": "darkweb_context" if module == "dt" else "telegram_context",
        "query_type": scope.get("query_type"),
        "query_value": scope.get("query_value"),
        "matched_supplier": scope.get("supplier_id"),
        "matched_program": scope.get("program_ref"),
        "collected_at": record.get("collected_at"),
        "raw_redacted": _redact_raw(raw),
        "ontology_targets": ["ThreatSource"],
    }


def _exposure_lineage(
    *,
    index: int,
    module: str,
    record: dict[str, Any],
    payload: dict[str, Any],
) -> dict[str, Any]:
    raw = record.get("raw") or {}
    source_ref = payload.get("source_ref") or _source_ref(module, raw)
    links = ["of", "targets", "sourced_from", "evidenced_by"]
    if payload.get("device", {}).get("infected_at") is not None or module == "cds":
        links.extend(["leaked", "compromises", "traverses"])
    decision_outputs = ["RiskAssessment"]
    if payload.get("is_active_signal"):
        decision_outputs.extend(["CompromiseIncident", "ProgramExposure", "NotificationDraft"])
    return {
        "index": index,
        "module": module,
        "source_ref_hash": _hash_text(f"{module}:{source_ref}"),
        "raw_envelope": "data/private_candidates/candidates.jsonl",
        "raw_payload_exported": False,
        "redaction_boundary": "adapter.normalize",
        "scope": _scope(record),
        "normalized_objects": payload.get("ontology_targets", []),
        "links": links,
        "engine_consumers": [
            "CorrelateExposure",
            "FlagActiveCompromise",
            "ComputeRisk",
            "PropagateRisk",
            "GenerateNotificationDraft",
        ],
        "decision_outputs": decision_outputs,
        "removed_fields": _removed_secret_fields(raw),
        "masked_fields": ["secret.masked_value"],
        "policy": "raw_secret_removed",
    }


def _context_lineage(
    *,
    index: int,
    module: str,
    record: dict[str, Any],
    source: dict[str, Any],
) -> dict[str, Any]:
    raw = record.get("raw") or {}
    return {
        "index": index,
        "module": module,
        "source_ref_hash": source.get("source_ref_hash"),
        "raw_envelope": "data/private_candidates/candidates.jsonl",
        "raw_payload_exported": False,
        "redaction_boundary": "import_candidate_signals._threat_source",
        "scope": _scope(record),
        "normalized_objects": ["ThreatSource"],
        "links": ["sourced_from", "context_for_supplier", "context_for_program"],
        "engine_consumers": ["ContextComponents", "ComputeRisk", "PropagateRisk"],
        "decision_outputs": ["RiskAssessment.components", "ProgramExposure.components"],
        "removed_fields": _removed_secret_fields(raw),
        "masked_fields": ["raw_redacted"],
        "policy": "raw_secret_removed",
    }


def _force_safe_mask(payload: dict[str, Any], module: str) -> None:
    secret = payload.get("secret")
    if not isinstance(secret, dict) or not secret.get("present"):
        return
    source_ref = payload.get("source_ref") or "missing-ref"
    secret["masked_value"] = f"redacted:{_hash_text(f'{module}:{source_ref}:secret')}"


def import_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    exposures: list[dict[str, Any]] = []
    threat_sources: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    lineage: list[dict[str, Any]] = []

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
            _force_safe_mask(payload, module)
            payload["is_active_signal"] = exposure.is_active_signal
            payload["scope"] = _scope(record)
            payload["ontology_targets"] = [
                "CredentialExposure",
                "InfectedDevice",
                "Identity",
                "ThreatSource",
            ]
            payload["source_ref_hash"] = _hash_text(f"{module}:{payload.get('source_ref')}")
            exposures.append(payload)
            lineage.append(
                _exposure_lineage(
                    index=index,
                    module=module,
                    record=record,
                    payload=payload,
                )
            )
        elif module in CONTEXT_MODULES:
            source = _threat_source(record, module)
            threat_sources.append(source)
            lineage.append(
                _context_lineage(
                    index=index,
                    module=module,
                    record=record,
                    source=source,
                )
            )
        else:
            rejected.append({"index": index, "module": module, "reason": "unsupported module"})

    modules = Counter(str(record.get("module", "")).lower() for record in records)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "local_private_candidate_import",
        "policy": {
            "provider_api_called": False,
            "raw_secret_output": "redacted",
            "raw_payload_exported": False,
            "lineage_source_ref": "hashed",
            "git_tracking": "outputs intentionally ignored unless explicitly allowlisted",
        },
        "summary": {
            "input_records": len(records),
            "normalized_exposures": len(exposures),
            "threat_sources": len(threat_sources),
            "rejected": len(rejected),
            "lineage_entries": len(lineage),
            "modules": dict(sorted(modules.items())),
        },
        "lineage": lineage,
        "normalized_exposures": exposures,
        "threat_sources": threat_sources,
        "rejected": rejected,
    }


def _leaf_strings(value: Any) -> set[str]:
    if isinstance(value, dict):
        strings: set[str] = set()
        for child in value.values():
            strings.update(_leaf_strings(child))
        return strings
    if isinstance(value, list):
        strings: set[str] = set()
        for child in value:
            strings.update(_leaf_strings(child))
        return strings
    if value is None:
        return set()
    return {str(value)}


def _contains_raw_secret(output: Any, raw_values: set[str]) -> list[str]:
    leaf_values = _leaf_strings(output)
    text = json.dumps(output, ensure_ascii=False, sort_keys=True)
    leaked: set[str] = set()
    for value in raw_values:
        if not value:
            continue
        if value in leaf_values:
            leaked.add(value)
        elif len(value) >= 8 and value in text:
            leaked.add(value)
    return sorted(leaked)


def _raw_secret_values(records: list[dict[str, Any]]) -> set[str]:
    values: set[str] = set()
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
        f"- index `{row.get('index')}` `{row.get('module', '-')}`: {row.get('reason')}"
        for row in result["rejected"]
    )
    return f"""# Private Candidate Import

Generated: `{result['generated_at']}`

Mode: `{result['mode']}`

This file is a redacted validation artifact. Provider API was not called here; raw password,
cookie, token, and provider payload fields are not exported.

## Summary

- Input records: `{summary['input_records']}`
- Normalized exposures: `{summary['normalized_exposures']}`
- Threat sources: `{summary['threat_sources']}`
- Rejected: `{summary['rejected']}`
- Lineage entries: `{summary['lineage_entries']}`

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
