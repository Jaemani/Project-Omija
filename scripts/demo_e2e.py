"""End-to-end demo proof for the store boundary.

This is the hackathon "does the spine actually work?" command:

    uv run python scripts/demo_e2e.py --store foundry --supplier sup-h
    uv run python scripts/demo_e2e.py --compare --supplier sup-h

`--store sqlite` runs the deterministic local pipeline. `--store foundry`
reads the synthetic seed from the published ontology through Python OSDK.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Literal


REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "out"
sys.path.insert(0, str(REPO_ROOT))

from actions.notify_draft import generate_drafts  # noqa: E402
from adapter.mock import DEMO_NOW  # noqa: E402
from scripts.p5_drafts import TOP_N, build_pipeline  # noqa: E402
from store.foundry import FoundryOntologyStore  # noqa: E402


StoreKind = Literal["sqlite", "foundry"]


def _path_label(path: list[dict[str, Any]]) -> str:
    return " -> ".join(str(node.get("ref")) for node in path)


def _build_sqlite_store():
    store, assessments = build_pipeline(DEMO_NOW)
    generate_drafts(store, assessments, now=DEMO_NOW, top=TOP_N)
    return store


def _build_store(kind: StoreKind):
    if kind == "sqlite":
        return _build_sqlite_store()
    return FoundryOntologyStore()


def summarize_store(store, supplier_id: str) -> dict[str, Any]:
    paths = store.propagation_paths(supplier_id)
    exposures = store.exposures_for_supplier(supplier_id)
    incidents = store.incidents_for_supplier(supplier_id)
    draft = store.draft_for_supplier(supplier_id)
    programs = {
        node["ref"]
        for path in paths
        for node in path
        if node.get("type") == "Program" and node.get("ref")
    }
    active_programs = {
        program_ref
        for incident in incidents
        for program_ref in incident.get("traverses_programs", [])
    }
    return {
        "supplier": supplier_id,
        "paths": [_path_label(path) for path in paths],
        "programs": sorted(programs),
        "active_programs": sorted(active_programs),
        "exposures": [
            {
                "id": row.get("id"),
                "identity": row.get("identity_ref"),
                "domain": row.get("domain_ref"),
                "target": row.get("target_domain_ref") or row.get("host"),
                "source": row.get("source_ref"),
            }
            for row in exposures
        ],
        "incidents": [row.get("id") for row in incidents],
        "draft": draft.get("id") if draft else None,
    }


def validate_summary(summary: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if not summary["paths"]:
        failures.append("no propagation path")
    if not summary["programs"]:
        failures.append("no reachable program")
    if not summary["exposures"]:
        failures.append("no supplier exposure")
    if not summary["incidents"]:
        failures.append("no active incident")
    if not summary["draft"]:
        failures.append("no notification draft")
    return failures


def print_summary(kind: StoreKind, summary: dict[str, Any]) -> None:
    print(f"E2E store={kind} supplier={summary['supplier']}")
    for path in summary["paths"]:
        print(f" - path: {path}")
    for exposure in summary["exposures"]:
        print(
            " - exposure: "
            f"{exposure['id']} of={exposure['identity']} "
            f"domain={exposure['domain']} targets={exposure['target']} "
            f"source={exposure['source']}"
        )
    print(f" - incidents: {', '.join(summary['incidents']) or 'none'}")
    print(f" - draft: {summary['draft'] or 'none'}")


def run_one(kind: StoreKind, supplier_id: str, *, write_json: bool = True) -> int:
    store = _build_store(kind)
    try:
        summary = summarize_store(store, supplier_id)
    finally:
        close = getattr(store, "close", None)
        if close:
            close()

    print_summary(kind, summary)
    failures = validate_summary(summary)
    if write_json:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUT_DIR / f"demo_e2e_{kind}.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    if failures:
        print("RESULT: FAIL")
        for failure in failures:
            print(f"FAIL {failure}")
        return 1
    print("RESULT: OK")
    return 0


def run_compare(supplier_id: str) -> int:
    summaries: dict[StoreKind, dict[str, Any]] = {}
    for kind in ("sqlite", "foundry"):
        store = _build_store(kind)
        try:
            summaries[kind] = summarize_store(store, supplier_id)
        finally:
            close = getattr(store, "close", None)
            if close:
                close()

    for kind, summary in summaries.items():
        print_summary(kind, summary)

    failures = []
    for kind, summary in summaries.items():
        failures.extend(f"{kind}: {failure}" for failure in validate_summary(summary))

    sqlite_programs = set(summaries["sqlite"]["programs"])
    foundry_programs = set(summaries["foundry"]["programs"])
    if not sqlite_programs.intersection(foundry_programs):
        failures.append(
            "sqlite/foundry reachable programs do not overlap: "
            f"{sorted(sqlite_programs)} vs {sorted(foundry_programs)}"
        )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "demo_e2e_compare.json").write_text(
        json.dumps(summaries, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    if failures:
        print("RESULT: FAIL")
        for failure in failures:
            print(f"FAIL {failure}")
        return 1
    print("RESULT: OK")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", choices=("sqlite", "foundry"), default="foundry")
    parser.add_argument("--supplier", default="sup-h")
    parser.add_argument("--compare", action="store_true")
    args = parser.parse_args(argv)

    if args.compare:
        return run_compare(args.supplier)
    return run_one(args.store, args.supplier)


if __name__ == "__main__":
    raise SystemExit(main())
