"""P0-C: StealthMole live data -> local ontology -> defensive actions.

This is the production-data entry point. It deliberately requires an explicit
authorized domain and registry membership, queries only CDS/CL/CB, reads one
page per domain/module, masks secrets at ``normalize()``, and never sends a
notification. Foundry is outside this script's scope; the local SQLite store is
the validation/runtime target until the separate OSDK work is complete.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from actions.compute_risk import compute_all  # noqa: E402
from actions.correlate import correlate_exposures  # noqa: E402
from actions.entity_resolver import propose_merges  # noqa: E402
from actions.flag_active import flag_active_compromises  # noqa: E402
from actions.notify_draft import generate_drafts  # noqa: E402
from actions.propagate_risk import propagate_program_risk  # noqa: E402
from adapter.base import normalize  # noqa: E402
from adapter.stealthmole import StealthMoleSource  # noqa: E402
from registry.loader import load_into_store, load_registry  # noqa: E402
from store.sqlite import SqliteOntologyStore  # noqa: E402

SAFE_MODULES = ("cds", "cl", "cb")
DEFAULT_DB = REPO_ROOT / "out" / "live" / "omija-live.sqlite"
DEFAULT_SUMMARY = REPO_ROOT / "out" / "live" / "summary.json"
_DOMAIN_RE = re.compile(r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")
_RESERVED_SUFFIXES = (".example", ".invalid", ".test", ".localhost")


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip("'\"")
        if key and value and key not in os.environ:
            os.environ[key] = value


def _csv(value: str | None) -> list[str]:
    return list(dict.fromkeys(
        item.strip().lower() for item in (value or "").split(",") if item.strip()
    ))


def _registry_domains(registry: dict[str, Any]) -> set[str]:
    return {
        str(domain).strip().lower()
        for supplier in registry.get("suppliers", [])
        for domain in supplier.get("domains", []) or []
    }


def validate_live_scope(
    *, domains: list[str], modules: list[str], registry: dict[str, Any]
) -> None:
    if not domains:
        raise ValueError(
            "no live query domains configured; set STEALTHMOLE_QUERY_DOMAINS "
            "or pass --domains"
        )
    unknown_modules = sorted(set(modules) - set(SAFE_MODULES))
    if unknown_modules:
        raise ValueError(
            f"unsupported live module(s): {', '.join(unknown_modules)}; "
            f"allowed: {', '.join(SAFE_MODULES)} (DT/UB unavailable)"
        )
    registered = _registry_domains(registry)
    for domain in domains:
        if not _DOMAIN_RE.fullmatch(domain):
            raise ValueError(f"invalid domain: {domain!r}")
        if domain.endswith(_RESERVED_SUFFIXES):
            raise ValueError(f"reserved/synthetic domain cannot be live-queried: {domain}")
        if domain not in registered:
            raise ValueError(
                f"live domain {domain!r} is not present in the selected supplier registry"
            )


def _remaining(quota: Any) -> int | float | None:
    if not isinstance(quota, dict):
        return quota if isinstance(quota, (int, float)) else None
    allowed, used = quota.get("allowed"), quota.get("used", 0)
    return allowed - used if isinstance(allowed, (int, float)) else None


def run_live_pipeline(
    *, source: StealthMoleSource, store: SqliteOntologyStore,
    registry: dict[str, Any], domains: list[str], modules: list[str],
    now: int | None = None, top: int = 3,
) -> dict[str, Any]:
    """Execute one bounded live pass. Returned summary contains no raw records."""
    now = int(time.time()) if now is None else now
    validate_live_scope(domains=domains, modules=modules, registry=registry)
    registry_counts = load_into_store(store, registry)

    quotas = source.quotas()
    for module in modules:
        remaining = _remaining(quotas.get(module.upper()))
        if remaining is None:
            raise RuntimeError(f"module {module} is absent from the quotas response")
        if remaining <= 0:
            raise RuntimeError(f"module {module} has no remaining quota")

    before = len(store.all_exposures())
    received = 0
    query_meta: list[dict[str, Any]] = []
    for domain in domains:
        for module in modules:
            records = source.search(module, "domain", domain)
            received += len(records)
            for raw in records:
                store.write_exposure(normalize(module, raw, fetched_at=now))
            query_meta.append({
                "domain": domain,
                "module": module,
                "records": len(records),
                "response": dict(source.last_response_meta),
            })

    after = len(store.all_exposures())
    correlation = correlate_exposures(store, now=now)
    merges = propose_merges(store, now=now)
    incidents = flag_active_compromises(store, now=now)
    assessments = compute_all(store, now=now)
    programs = propagate_program_risk(store, now=now)
    drafts = generate_drafts(store, assessments, top=top, now=now)

    return {
        "run_at": now,
        "source": "stealthmole-live",
        "domains": domains,
        "modules": modules,
        "registry_counts": registry_counts,
        "queries": query_meta,
        "records_received": received,
        "records_new": after - before,
        "records_total": after,
        "correlation": {
            "matched": correlation.matched_exposures,
            "unmatched": correlation.unmatched_exposures,
        },
        "merge_proposals_pending": len(merges.proposals),
        "incidents_opened": len(incidents.incidents),
        "risk_assessments": len(assessments),
        "program_exposures": len(programs),
        "notification_drafts": len(drafts),
        "guardrails": {
            "raw_secrets_persisted": False,
            "automatic_send": False,
            "pagination_followed": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    _load_dotenv(REPO_ROOT / ".env")
    parser = argparse.ArgumentParser(
        description="Authorized StealthMole live data -> Omija local risk pipeline"
    )
    parser.add_argument("--registry", default=os.getenv("OMIJA_LIVE_REGISTRY", ""))
    parser.add_argument("--domains", default=os.getenv("STEALTHMOLE_QUERY_DOMAINS", ""))
    parser.add_argument("--modules", default=os.getenv("STEALTHMOLE_MODULES", "cds"))
    parser.add_argument("--db", default=os.getenv("OMIJA_LIVE_DB", str(DEFAULT_DB)))
    parser.add_argument("--summary", default=str(DEFAULT_SUMMARY))
    parser.add_argument("--top", type=int, default=3)
    parser.add_argument(
        "--authorized", action="store_true",
        help="confirm that every query domain is authorized for this API use",
    )
    args = parser.parse_args(argv)

    if not args.authorized:
        print("REFUSED: pass --authorized after confirming query authorization.", file=sys.stderr)
        return 2
    if not args.registry:
        print(
            "REFUSED: set OMIJA_LIVE_REGISTRY or pass --registry with an authorized "
            "supplier registry.", file=sys.stderr,
        )
        return 2

    try:
        registry = load_registry(args.registry)
        domains, modules = _csv(args.domains), _csv(args.modules)
        validate_live_scope(domains=domains, modules=modules, registry=registry)
        db_path, summary_path = Path(args.db), Path(args.summary)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        store = SqliteOntologyStore(str(db_path))
        try:
            summary = run_live_pipeline(
                source=StealthMoleSource(), store=store, registry=registry,
                domains=domains, modules=modules, top=max(0, args.top),
            )
        finally:
            store.close()
        summary_path.write_text(
            json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except Exception as exc:
        print(f"FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"database: {db_path}")
    print(f"summary : {summary_path}")
    if summary["records_received"] == 0:
        print("NOTE: live connection succeeded, but the authorized query returned 0 records.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
