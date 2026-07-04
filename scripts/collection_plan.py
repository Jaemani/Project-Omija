"""Generate a non-executing data collection plan from the supplier registry.

The output is a safe planning artifact: it contains query seeds, collection
tracks, ontology landing targets, and handling boundaries. It does not call any
private feed, public API, or external service.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO_ROOT / "registry" / "suppliers.yaml"
OUT_JSON = REPO_ROOT / "out" / "collection_plan.json"
OUT_MD = REPO_ROOT / "out" / "collection_plan.md"

ACCESS_HOST_PREFIXES = ("vpn", "sso", "mail", "owa", "groupware", "citrix", "dev", "admin", "portal")
REGIONAL_KEYWORDS = ("defense", "aerospace", "shipbuilding", "electronics", "radar", "avionics", "mro")


def load_registry(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _program_lookup(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {program["id"]: program for program in registry.get("programs", [])}


def _prime_lookup(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {prime["id"]: prime for prime in registry.get("primes", [])}


def _supplier_program_refs(supplier: dict[str, Any], primes: dict[str, dict[str, Any]]) -> list[str]:
    refs: set[str] = set()
    supplies = supplier.get("supplies")
    if isinstance(supplies, str):
        supplies = [supplies]
    for prime_id in supplies or []:
        refs.update(primes.get(prime_id, {}).get("runs", []) or [])
    return sorted(refs)


def _item(
    *,
    item_id: str,
    track: str,
    cadence: str,
    query_type: str,
    query_value: str,
    ontology_targets: list[str],
    purpose: str,
    supplier: dict[str, Any] | None = None,
    program_refs: list[str] | None = None,
    capabilities: list[str] | None = None,
    sensitivity: str = "private_candidate",
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": item_id,
        "execute": False,
        "track": track,
        "cadence": cadence,
        "query_type": query_type,
        "query_value": query_value,
        "provider_capabilities": capabilities or [],
        "ontology_targets": ontology_targets,
        "purpose": purpose,
        "sensitivity": sensitivity,
        "handling": {
            "raw_secret_storage": "forbidden",
            "raw_cookie_storage": "forbidden",
            "raw_token_storage": "forbidden",
            "landing_mode": "normalize_then_review",
        },
    }
    if supplier:
        payload["supplier"] = {
            "id": supplier.get("id"),
            "name": supplier.get("name"),
            "tier": supplier.get("tier"),
            "criticality": supplier.get("criticality"),
        }
    if program_refs:
        payload["program_refs"] = sorted(program_refs)
    return payload


def build_plan(registry: dict[str, Any]) -> dict[str, Any]:
    primes = _prime_lookup(registry)
    programs = _program_lookup(registry)
    items: list[dict[str, Any]] = []

    for supplier in registry.get("suppliers", []):
        supplier_id = supplier["id"]
        supplier_program_refs = _supplier_program_refs(supplier, primes)
        domains = supplier.get("domains") or []
        for domain in domains:
            items.append(
                _item(
                    item_id=f"domain:{supplier_id}:{domain}",
                    track="private_exposure_candidate",
                    cadence="daily",
                    query_type="domain_exact",
                    query_value=domain,
                    capabilities=["CL", "CDS"],
                    ontology_targets=["CredentialExposure", "InfectedDevice", "Identity", "Domain"],
                    purpose="Find exposure and infostealer candidates tied to the supplier domain.",
                    supplier=supplier,
                    program_refs=supplier_program_refs,
                )
            )
            items.append(
                _item(
                    item_id=f"email-domain:{supplier_id}:{domain}",
                    track="private_exposure_candidate",
                    cadence="daily",
                    query_type="email_domain",
                    query_value=f"*@{domain}",
                    capabilities=["CL"],
                    ontology_targets=["CredentialExposure", "Identity"],
                    purpose="Find leaked-account candidates for supplier-owned identities.",
                    supplier=supplier,
                    program_refs=supplier_program_refs,
                )
            )
            for prefix in ACCESS_HOST_PREFIXES:
                host = f"{prefix}.{domain}"
                items.append(
                    _item(
                        item_id=f"asset-host:{supplier_id}:{host}",
                        track="asset_surface_discovery",
                        cadence="weekly",
                        query_type="target_host_pattern",
                        query_value=host,
                        capabilities=["CDS", "DT", "TT"],
                        ontology_targets=["Domain", "ThreatSource", "InfectedDevice"],
                        purpose="Detect access-surface mentions or infostealer records targeting high-risk hosts.",
                        supplier=supplier,
                        program_refs=supplier_program_refs,
                    )
                )

        name = supplier.get("name") or supplier_id
        items.append(
            _item(
                item_id=f"alias:{supplier_id}",
                track="alias_and_keyword_discovery",
                cadence="weekly",
                query_type="company_alias",
                query_value=name,
                capabilities=["DT", "TT"],
                ontology_targets=["ThreatSource", "MergeProposal"],
                purpose="Discover unregistered aliases, domains, or repeated mentions for reviewer triage.",
                supplier=supplier,
                program_refs=supplier_program_refs,
            )
        )

    for prime in registry.get("primes", []):
        for program_ref in prime.get("runs", []) or []:
            program = programs.get(program_ref, {"name": program_ref})
            items.append(
                _item(
                    item_id=f"program:{program_ref}",
                    track="program_keyword_context",
                    cadence="weekly",
                    query_type="program_keyword",
                    query_value=f"{prime.get('name')} {program.get('name')}",
                    capabilities=["DT", "TT"],
                    ontology_targets=["ThreatSource", "ProgramExposure"],
                    purpose="Collect program-level mention context for reviewer triage and program rollup.",
                    program_refs=[program_ref],
                )
            )

    for keyword in REGIONAL_KEYWORDS:
        items.append(
            _item(
                item_id=f"regional:kr:{keyword}",
                track="regional_context",
                cadence="weekly",
                query_type="country_keyword",
                query_value=f"Korea {keyword}",
                capabilities=["DT", "TT"],
                ontology_targets=["ThreatSource"],
                purpose="Watch aggregate regional context and discover review candidates; not direct credential evidence.",
                sensitivity="context_only",
            )
        )

    public_jobs = [
        {
            "id": "public-context-snapshot",
            "execute": False,
            "track": "public_context",
            "command": "uv run python scripts/public_context_snapshot.py",
            "outputs": ["out/public_context/summary.json", "out/public_context/summary.md"],
            "ontology_targets": ["RiskAssessment.components", "ProgramExposure.components", "ThreatSource.kind"],
            "sensitivity": "public_metadata",
        },
        {
            "id": "public-context-matrix",
            "execute": False,
            "track": "public_context",
            "command": "uv run python scripts/public_context_matrix.py",
            "outputs": ["out/public_context_matrix.html"],
            "ontology_targets": ["presentation_context"],
            "sensitivity": "public_metadata",
        },
    ]

    counts = Counter(item["track"] for item in items)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "non_executing_collection_plan",
        "registry": str(REGISTRY_PATH.relative_to(REPO_ROOT)),
        "policy": {
            "private_feed_calls": "not executed",
            "raw_secret_storage": "forbidden",
            "credential_display": "forbidden",
            "notification_sending": "forbidden",
        },
        "summary": {
            "suppliers": len(registry.get("suppliers", [])),
            "primes": len(registry.get("primes", [])),
            "programs": len(registry.get("programs", [])),
            "query_items": len(items),
            "public_jobs": len(public_jobs),
            "by_track": dict(sorted(counts.items())),
        },
        "items": items,
        "public_jobs": public_jobs,
    }


def render_markdown(plan: dict[str, Any]) -> str:
    summary = plan["summary"]
    tracks = "\n".join(f"- `{name}`: {count}" for name, count in summary["by_track"].items())
    sample_items = "\n".join(
        f"- `{item['id']}` | `{item['query_type']}` | `{item['query_value']}` -> "
        f"{', '.join(item['ontology_targets'])}"
        for item in plan["items"][:20]
    )
    return f"""# Omija Collection Plan

Generated: `{plan['generated_at']}`

Mode: `{plan['mode']}`

This file is a non-executing plan. It contains query seeds and ontology landing
targets only. It does not call private feeds or store credential material.

## Summary

- Suppliers: `{summary['suppliers']}`
- Primes: `{summary['primes']}`
- Programs: `{summary['programs']}`
- Private/context query seeds: `{summary['query_items']}`
- Public context jobs: `{summary['public_jobs']}`

## Query Seeds By Track

{tracks}

## Sample Query Seeds

{sample_items}

## Public Jobs

```text
uv run python scripts/public_context_snapshot.py
uv run python scripts/public_context_matrix.py
```

## Guardrails

- `execute=false` for every private/context query seed.
- Raw password, cookie, token, session value storage is forbidden.
- Country/keyword hits land as `ThreatSource` or review candidates first.
- `CredentialExposure` and `InfectedDevice` require normalized identity/host evidence.
- `NotificationDraft` is human-reviewed; no automatic send action.
"""


def main() -> int:
    registry = load_registry()
    plan = build_plan(registry)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text(render_markdown(plan), encoding="utf-8")
    print(f"wrote {OUT_JSON.relative_to(REPO_ROOT)}")
    print(f"wrote {OUT_MD.relative_to(REPO_ROOT)}")
    print("RESULT: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
