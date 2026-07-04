"""Check whether the Omija early-warning MVP evidence is wired together.

This is an operational readiness check, not a UI artifact. It verifies that the
collection plan is non-executing and complete enough, and that the current mock
engine evaluation still proves the active-on-top ranking invariant.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.collection_plan import ACCESS_HOST_PREFIXES, build_plan, load_registry  # noqa: E402
from scripts.p6_eval import evaluate  # noqa: E402

OUT_JSON = REPO_ROOT / "out" / "early_warning_readiness.json"
OUT_MD = REPO_ROOT / "out" / "early_warning_readiness.md"


def _check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "pass": bool(passed), "detail": detail}


def build_readiness() -> dict[str, Any]:
    registry = load_registry()
    plan = build_plan(registry)
    evaluation = evaluate()

    items = plan["items"]
    domains = [
        (supplier["id"], domain)
        for supplier in registry.get("suppliers", [])
        for domain in supplier.get("domains", [])
    ]
    by_id = {item["id"]: item for item in items}
    domain_query_ids = {f"domain:{supplier_id}:{domain}" for supplier_id, domain in domains}
    email_query_ids = {f"email-domain:{supplier_id}:{domain}" for supplier_id, domain in domains}
    asset_query_ids = {
        f"asset-host:{supplier_id}:{prefix}.{domain}"
        for supplier_id, domain in domains
        for prefix in ACCESS_HOST_PREFIXES
    }

    all_non_executing = all(item.get("execute") is False for item in items) and all(
        job.get("execute") is False for job in plan.get("public_jobs", [])
    )
    all_have_targets = all(item.get("ontology_targets") for item in items)
    all_secret_storage_forbidden = all(
        item.get("handling", {}).get("raw_secret_storage") == "forbidden"
        and item.get("handling", {}).get("raw_cookie_storage") == "forbidden"
        and item.get("handling", {}).get("raw_token_storage") == "forbidden"
        for item in items
    )
    regional_items = [item for item in items if item["track"] == "regional_context"]
    regional_context_only = all(item["ontology_targets"] == ["ThreatSource"] for item in regional_items)

    checks = [
        _check(
            "collection_plan_non_executing",
            all_non_executing,
            "Every private/context query seed and public job has execute=false.",
        ),
        _check(
            "domain_exact_coverage",
            domain_query_ids <= set(by_id),
            f"{len(domain_query_ids)} supplier-domain exact query seeds expected.",
        ),
        _check(
            "email_domain_coverage",
            email_query_ids <= set(by_id),
            f"{len(email_query_ids)} email-domain query seeds expected.",
        ),
        _check(
            "asset_surface_coverage",
            asset_query_ids <= set(by_id),
            f"{len(asset_query_ids)} access-host query seeds expected.",
        ),
        _check(
            "ontology_targets_present",
            all_have_targets,
            "Every query seed names at least one ontology landing target.",
        ),
        _check(
            "secret_storage_forbidden",
            all_secret_storage_forbidden,
            "Raw password/cookie/token storage is forbidden for every private/context seed.",
        ),
        _check(
            "regional_context_not_evidence",
            bool(regional_items) and regional_context_only,
            "Country/keyword monitoring lands only as ThreatSource context.",
        ),
        _check(
            "engine_eval_pass",
            bool(evaluation.get("pass")),
            "Current synthetic engine evaluation reports pass=true.",
        ),
        _check(
            "active_on_top_invariant",
            bool(evaluation.get("ranking", {}).get("strictly_on_top")),
            "Active compromise candidates rank strictly above non-active suppliers.",
        ),
        _check(
            "active_detection_clean",
            evaluation.get("active_compromise", {}).get("fp") == 0
            and evaluation.get("active_compromise", {}).get("fn") == 0,
            "Synthetic active-compromise evaluation has no false positives or false negatives.",
        ),
    ]
    ready = all(check["pass"] for check in checks)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "early_warning_readiness_check",
        "ready": ready,
        "summary": {
            "checks_passed": sum(1 for check in checks if check["pass"]),
            "checks_total": len(checks),
            "suppliers": plan["summary"]["suppliers"],
            "query_items": plan["summary"]["query_items"],
            "asset_surface_seeds": len(asset_query_ids),
            "eval_records": evaluation.get("corpus", {}).get("records"),
            "active_suppliers": evaluation.get("ranking", {}).get("top_k_ids", []),
        },
        "checks": checks,
        "limitations": [
            "Evaluation uses a synthetic clean mock corpus; it proves wiring, not field precision.",
            "Private feed query seeds are not executed by this check.",
            "Live compromise confirmation still requires VPN/SSO/IAM/EDR or supplier response evidence.",
        ],
    }


def render_markdown(readiness: dict[str, Any]) -> str:
    checks = "\n".join(
        f"- [{'x' if check['pass'] else ' '}] `{check['name']}` — {check['detail']}"
        for check in readiness["checks"]
    )
    limitations = "\n".join(f"- {item}" for item in readiness["limitations"])
    summary = readiness["summary"]
    return f"""# Early Warning Readiness

Generated: `{readiness['generated_at']}`

Ready: `{readiness['ready']}`

## Summary

- Checks: `{summary['checks_passed']}/{summary['checks_total']}`
- Suppliers: `{summary['suppliers']}`
- Query seeds: `{summary['query_items']}`
- Asset surface seeds: `{summary['asset_surface_seeds']}`
- Eval records: `{summary['eval_records']}`
- Active suppliers in synthetic eval: `{', '.join(summary['active_suppliers'])}`

## Checks

{checks}

## Limitations

{limitations}
"""


def main() -> int:
    readiness = build_readiness()
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(readiness, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text(render_markdown(readiness), encoding="utf-8")
    print(f"wrote {OUT_JSON.relative_to(REPO_ROOT)}")
    print(f"wrote {OUT_MD.relative_to(REPO_ROOT)}")
    print("RESULT:", "READY" if readiness["ready"] else "NOT_READY")
    return 0 if readiness["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
