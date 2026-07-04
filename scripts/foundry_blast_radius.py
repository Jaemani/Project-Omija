"""Read Foundry seed ontology and show blast radius for one exposure.

This is intentionally read-only. It proves the operational "so what" path:
one CredentialExposure -> owning Supplier -> reachable Programs, with provenance.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Protocol


REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "out"
sys.path.insert(0, str(REPO_ROOT))

from store.foundry import FoundryOntologyStore  # noqa: E402


class BlastRadiusStore(Protocol):
    def all_exposures(self) -> list[dict[str, Any]]: ...

    def propagation_paths(self, supplier_id: str, *, depth_cap: int = 6) -> list[list[dict[str, Any]]]: ...

    def incidents_for_supplier(self, supplier_id: str) -> list[dict[str, Any]]: ...


def _path_label(path: list[dict[str, Any]]) -> str:
    return " -> ".join(str(node.get("ref")) for node in path if node.get("ref"))


def _program_refs(paths: list[list[dict[str, Any]]]) -> list[str]:
    return sorted(
        {
            str(node["ref"])
            for path in paths
            for node in path
            if node.get("type") == "Program" and node.get("ref")
        }
    )


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_") or "exposure"


def summarize_blast_radius(store: BlastRadiusStore, exposure_id: str) -> dict[str, Any]:
    exposure = next((row for row in store.all_exposures() if row.get("id") == exposure_id), None)
    if not exposure:
        raise SystemExit(f"exposure not found: {exposure_id}")

    supplier_id = exposure.get("supplier_id")
    if not supplier_id:
        raise SystemExit(f"exposure has no supplier_id: {exposure_id}")

    paths_raw = store.propagation_paths(str(supplier_id))
    paths = [_path_label(path) for path in paths_raw]
    incidents = store.incidents_for_supplier(str(supplier_id))
    matching_incidents = [
        incident
        for incident in incidents
        if exposure_id in incident.get("path_snapshot", "")
        or exposure_id in {str(part) for part in incident.get("path", [])}
    ]
    incident = matching_incidents[0] if matching_incidents else (incidents[0] if incidents else {})

    return {
        "exposure": {
            "id": exposure.get("id"),
            "identity_ref": exposure.get("identity_ref"),
            "owner_domain": exposure.get("domain_ref"),
            "target_domain": exposure.get("target_domain_ref"),
            "source_ref": exposure.get("source_ref"),
            "has_session_cookie": exposure.get("has_session_cookie"),
        },
        "supplier": supplier_id,
        "programs": _program_refs(paths_raw),
        "paths": paths,
        "provenance": {
            "incident": incident.get("id"),
            "risk_band": incident.get("risk_band"),
            "path_confidence": incident.get("path_confidence"),
            "path_hash": incident.get("path_hash"),
        },
    }


def write_summary(summary: dict[str, Any], exposure_id: str) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"blast_radius_{_safe_name(exposure_id)}.json"
    out_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_path


def print_summary(summary: dict[str, Any], out_path: Path) -> None:
    exposure = summary["exposure"]
    provenance = summary["provenance"]
    print(f"Exposure: {exposure['id']}")
    print(f"Identity: {exposure['identity_ref']}")
    print(f"Owner domain: {exposure['owner_domain']}")
    print(f"Target domain: {exposure['target_domain']}")
    print(f"Supplier: {summary['supplier']}")
    print(f"Programs: {', '.join(summary['programs']) or 'none'}")
    print(f"Incident: {provenance.get('incident') or 'none'}")
    print(f"Risk band: {provenance.get('risk_band') or 'none'}")
    print(f"Path confidence: {provenance.get('path_confidence') or 'none'}")
    for path in summary["paths"]:
        print(f"Path: {path}")
    print(f"wrote {out_path.relative_to(REPO_ROOT)}")
    print("RESULT: OK")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exposure_id", nargs="?", default="exp:micro-h:active")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    store = FoundryOntologyStore()
    try:
        summary = summarize_blast_radius(store, args.exposure_id)
    finally:
        close = getattr(store, "close", None)
        if close:
            close()
    out_path = write_summary(summary, args.exposure_id)
    print_summary(summary, out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
