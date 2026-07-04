"""Execute an auditable Action Type state-transition chain on Foundry SEED objects.

This proves the "the ontology does work, humans stay on the loop" claim for
the demo: it drives the 8 newly merged workflow Action Types through the live
Foundry REST API v2 against the seeded `CompromiseIncident` and
`NotificationDraft` objects, verifying `status` via object readback before and
after every apply, and writes masked evidence to
`out/foundry_action_chain.json`.

Action Types discovered (kebab-case apiNames as merged into the ontology):
    CompromiseIncident : acknowledge-incident, assign-incident, close-incident
    NotificationDraft  : review-notification-draft, approve-notification-draft,
                         export-notification-draft
    MergeProposal       : confirm-entity-merge, reject-entity-merge

Only the following chain is *applied* (human-on-the-loop: no auto-close, no
merge confirm/reject — those two MergeProposal actions and close-incident are
discovered/reported but never applied by this script):

    CompromiseIncident (incident:micro-h:active):
        acknowledge-incident(status=acknowledged)
        -> assign-incident(status=assigned)

    NotificationDraft (draft:sup-h:2026-07-03):
        review-notification-draft(status=reviewed, reviewer=analyst-1 (demo))
        -> approve-notification-draft(status=approved, reviewer=approver-1 (demo))
        -> export-notification-draft(status=exported)

Auth: reads FOUNDRY_HOSTNAME / FOUNDRY_TOKEN from `.env` (same pattern as
scripts/foundry_osdk_smoke.py / scripts/palantir_mcp.py). Never prints the
token, the Authorization header, or any URL with query secrets. Re-runnable:
each step just re-applies the target status.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

try:
    from foundry_osdk_smoke import load_env_file
except ModuleNotFoundError:  # pragma: no cover - import path used by tests/tools.
    from scripts.foundry_osdk_smoke import load_env_file

import os

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = REPO_ROOT / "out" / "foundry_action_chain.json"

DEFAULT_ONTOLOGY_API_NAME = "ontology-cafadd0c-45e2-4808-98ab-787ee7f2903a"
ONTOLOGY_API_NAME_ENV = "FOUNDRY_ONTOLOGY_API_NAME"

INCIDENT_OBJECT_TYPE = "CompromiseIncident"
DRAFT_OBJECT_TYPE = "NotificationDraft"
MERGE_OBJECT_TYPE = "MergeProposal"

INCIDENT_PK = "incident:micro-h:active"
DRAFT_PK = "draft:sup-h:2026-07-03"

REQUEST_TIMEOUT_SECONDS = 30


class FoundryActionChainError(RuntimeError):
    """Raised when discovery or an action apply fails after reasonable retries."""


@dataclass(frozen=True)
class ChainStep:
    action_name: str  # kebab-case apiName as merged into the ontology
    object_type: str
    primary_key: str
    values: dict[str, str]  # semantic param name ("status"/"reviewer") -> value


# Applied chain: acknowledge/assign only (incident stays open/assigned, not
# closed) and the full draft review -> approve -> export path.
CHAIN: list[ChainStep] = [
    ChainStep("acknowledge-incident", INCIDENT_OBJECT_TYPE, INCIDENT_PK, {"status": "acknowledged"}),
    ChainStep("assign-incident", INCIDENT_OBJECT_TYPE, INCIDENT_PK, {"status": "assigned"}),
    ChainStep(
        "review-notification-draft",
        DRAFT_OBJECT_TYPE,
        DRAFT_PK,
        {"status": "reviewed", "reviewer": "analyst-1 (demo)"},
    ),
    ChainStep(
        "approve-notification-draft",
        DRAFT_OBJECT_TYPE,
        DRAFT_PK,
        {"status": "approved", "reviewer": "approver-1 (demo)"},
    ),
    ChainStep("export-notification-draft", DRAFT_OBJECT_TYPE, DRAFT_PK, {"status": "exported"}),
]

# Discovered and reported, but never applied (human-on-the-loop guardrail:
# do not auto-close the incident, do not auto-confirm/reject entity merges).
DISCOVER_ONLY_ACTIONS = ["close-incident", "confirm-entity-merge", "reject-entity-merge"]

ALL_NEW_ACTION_NAMES = [step.action_name for step in CHAIN] + DISCOVER_ONLY_ACTIONS


def _sanitize(text: str, secrets: list[str]) -> str:
    sanitized = text
    for secret in secrets:
        if secret:
            sanitized = sanitized.replace(secret, "<redacted>")
    return sanitized


def _quote(value: str) -> str:
    return urllib.parse.quote(str(value), safe="")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def foundry_api_base(hostname: str) -> str:
    host = hostname.strip().removeprefix("https://").removeprefix("http://").rstrip("/")
    return f"https://{host}/api"


class FoundryRestClient:
    """Thin wrapper over the Foundry REST API v2 ontology endpoints."""

    def __init__(self, *, hostname: str, token: str, ontology_api_name: str) -> None:
        self.base_url = foundry_api_base(hostname)
        self.ontology_api_name = ontology_api_name
        self._token = token
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
        )

    def _sanitize(self, text: str) -> str:
        return _sanitize(text, [self._token])

    def _check(self, resp: requests.Response, context: str) -> dict[str, Any]:
        if not resp.ok:
            body = self._sanitize(resp.text[:4000])
            raise FoundryActionChainError(f"{context} failed: HTTP {resp.status_code} - {body}")
        if not resp.content:
            return {}
        return resp.json()

    def list_action_types(self) -> dict[str, dict[str, Any]]:
        by_api_name: dict[str, dict[str, Any]] = {}
        page_token: str | None = None
        url = f"{self.base_url}/v2/ontologies/{_quote(self.ontology_api_name)}/actionTypes"
        while True:
            params: dict[str, Any] = {"pageSize": 500}
            if page_token:
                params["pageToken"] = page_token
            resp = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
            body = self._check(resp, "GET actionTypes")
            for item in body.get("data", []):
                by_api_name[item["apiName"]] = item
            page_token = body.get("nextPageToken")
            if not page_token:
                break
        return by_api_name

    def get_object(self, object_type: str, primary_key: str) -> tuple[int, dict[str, Any]]:
        url = (
            f"{self.base_url}/v2/ontologies/{_quote(self.ontology_api_name)}"
            f"/objects/{_quote(object_type)}/{_quote(primary_key)}"
        )
        resp = self.session.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
        body = self._check(resp, f"GET object {object_type}/{primary_key}")
        return resp.status_code, body

    def apply_action(self, action_api_name: str, parameters: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        url = (
            f"{self.base_url}/v2/ontologies/{_quote(self.ontology_api_name)}"
            f"/actions/{_quote(action_api_name)}/apply"
        )
        payload = {"parameters": parameters, "options": {"returnEdits": "ALL"}}
        resp = self.session.post(url, json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
        body = self._check(resp, f"POST apply {action_api_name}")
        return resp.status_code, body


def api_name_variants(kebab: str) -> list[str]:
    parts = kebab.split("-")
    camel = parts[0] + "".join(p.capitalize() for p in parts[1:])
    pascal = "".join(p.capitalize() for p in parts)
    variants = [kebab, camel, pascal, kebab.replace("-", "_"), "".join(parts)]
    seen: set[str] = set()
    ordered = []
    for variant in variants:
        if variant not in seen:
            seen.add(variant)
            ordered.append(variant)
    return ordered


def resolve_action_type(by_api_name: dict[str, dict[str, Any]], kebab: str) -> dict[str, Any]:
    for variant in api_name_variants(kebab):
        if variant in by_api_name:
            return by_api_name[variant]
    target = kebab.replace("-", "").lower()
    for api_name, record in by_api_name.items():
        if api_name.replace("_", "").lower() == target:
            return record
    raise FoundryActionChainError(
        f"Could not resolve action type apiName for {kebab!r}. "
        f"Tried variants {api_name_variants(kebab)}. "
        f"Available apiNames: {sorted(by_api_name)}"
    )


def resolve_object_param_id(action_type: dict[str, Any]) -> str:
    params: dict[str, Any] = action_type.get("parameters", {})
    object_param_ids = [
        pid for pid, spec in params.items() if (spec.get("dataType") or {}).get("type") == "object"
    ]
    if len(object_param_ids) != 1:
        raise FoundryActionChainError(
            f"Expected exactly 1 object-reference parameter for action "
            f"{action_type.get('apiName')!r}, found {object_param_ids} "
            f"(all params: {params})"
        )
    return object_param_ids[0]


def resolve_string_param_ids(action_type: dict[str, Any], wanted: dict[str, str]) -> dict[str, str]:
    """Map semantic keys ("status", "reviewer") to actual string parameter ids."""
    params: dict[str, Any] = action_type.get("parameters", {})
    string_ids = sorted(
        pid for pid, spec in params.items() if (spec.get("dataType") or {}).get("type") == "string"
    )
    if len(string_ids) < len(wanted):
        raise FoundryActionChainError(
            f"Action {action_type.get('apiName')!r} has {len(string_ids)} string "
            f"parameters ({string_ids}) but {len(wanted)} are required for {sorted(wanted)}"
        )

    remaining = list(string_ids)
    resolved: dict[str, str] = {}
    unresolved_keys: list[str] = []
    for key in wanted:
        matches = [
            pid
            for pid in remaining
            if key in pid.lower() or key in (params[pid].get("displayName") or "").lower()
        ]
        if len(matches) == 1:
            resolved[matches[0]] = wanted[key]
            remaining.remove(matches[0])
        else:
            unresolved_keys.append(key)

    if unresolved_keys:
        if len(unresolved_keys) == len(remaining):
            for key, pid in zip(sorted(unresolved_keys), remaining):
                resolved[pid] = wanted[key]
        else:
            raise FoundryActionChainError(
                f"Ambiguous string parameters for action {action_type.get('apiName')!r}: "
                f"could not resolve {unresolved_keys} among remaining ids {remaining} "
                f"(displayNames: {[params[p].get('displayName') for p in remaining]})"
            )
    return resolved


def build_apply_parameters(action_type: dict[str, Any], primary_key: str, values: dict[str, str]) -> dict[str, Any]:
    object_param_id = resolve_object_param_id(action_type)
    string_params = resolve_string_param_ids(action_type, values)
    parameters: dict[str, Any] = {object_param_id: primary_key}
    parameters.update(string_params)
    return parameters


def describe_action_type(kebab: str, action_type: dict[str, Any]) -> dict[str, Any]:
    params: dict[str, Any] = action_type.get("parameters", {})
    return {
        "requested": kebab,
        "apiName": action_type.get("apiName"),
        "rid": action_type.get("rid"),
        "status": action_type.get("status"),
        "parameters": {
            pid: (spec.get("dataType") or {}).get("type") for pid, spec in params.items()
        },
    }


def run_chain(client: FoundryRestClient, *, apply: bool = True) -> dict[str, Any]:
    by_api_name = client.list_action_types()

    discovered = {name: describe_action_type(name, resolve_action_type(by_api_name, name)) for name in ALL_NEW_ACTION_NAMES}

    steps_evidence: list[dict[str, Any]] = []
    if apply:
        for step in CHAIN:
            action_type = resolve_action_type(by_api_name, step.action_name)
            action_api_name = action_type["apiName"]
            parameters = build_apply_parameters(action_type, step.primary_key, step.values)

            before_status_code, before_obj = client.get_object(step.object_type, step.primary_key)
            readback_before = before_obj.get("status")

            apply_status_code, _apply_body = client.apply_action(action_api_name, parameters)

            after_status_code, after_obj = client.get_object(step.object_type, step.primary_key)
            readback_after = after_obj.get("status")

            requested_status = step.values.get("status")
            steps_evidence.append(
                {
                    "action": action_api_name,
                    "action_requested": step.action_name,
                    "objectType": step.object_type,
                    "pk": step.primary_key,
                    "requested_status": requested_status,
                    "readback_status_before": readback_before,
                    "readback_status_after": readback_after,
                    "readback_before_http_status": before_status_code,
                    "readback_after_http_status": after_status_code,
                    "http_status": apply_status_code,
                    "timestamp": _now(),
                    "verified": readback_after == requested_status,
                }
            )

    return {"discovered": discovered, "steps": steps_evidence}


def write_evidence(result: dict[str, Any], *, ok: bool, error: str | None = None) -> Path:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": _now(),
        "ontology_api_name": result.get("ontology_api_name"),
        "status": "OK" if ok else "FAILED",
        "error": error,
        "discovered_actions": result.get("discovered"),
        "steps": result.get("steps", []),
    }
    OUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return OUT_PATH


def print_summary(result: dict[str, Any], out_path: Path) -> None:
    print("Discovered action types:")
    for kebab, info in result.get("discovered", {}).items():
        applied = " (discover-only)" if kebab in DISCOVER_ONLY_ACTIONS else ""
        print(f"  - {kebab} -> apiName={info['apiName']!r} rid={info['rid']}{applied}")
        print(f"      parameters: {info['parameters']}")

    steps = result.get("steps", [])
    if steps:
        print()
        print(f"{'action':<30}{'objectType':<20}{'pk':<26}{'before':<14}{'after':<14}{'http':<6}{'ok'}")
        for step in steps:
            print(
                f"{step['action']:<30}{step['objectType']:<20}{step['pk']:<26}"
                f"{str(step['readback_status_before']):<14}{str(step['readback_status_after']):<14}"
                f"{step['http_status']:<6}{step['verified']}"
            )
    print()
    print(f"wrote {out_path.relative_to(REPO_ROOT)}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", default=".env")
    parser.add_argument(
        "--discover-only",
        action="store_true",
        help="Only list/resolve the 8 action types; do not apply any actions.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    load_env_file(args.env_file)

    hostname = os.getenv("FOUNDRY_HOSTNAME", "").strip()
    token = os.getenv("FOUNDRY_TOKEN", "").strip()
    ontology_api_name = os.getenv(ONTOLOGY_API_NAME_ENV, "").strip() or DEFAULT_ONTOLOGY_API_NAME

    if not hostname or not token:
        print(
            "FOUNDRY ACTION CHAIN FAIL: set FOUNDRY_HOSTNAME and FOUNDRY_TOKEN in .env. "
            "Do not paste tokens in chat.",
            file=sys.stderr,
        )
        return 2

    client = FoundryRestClient(hostname=hostname, token=token, ontology_api_name=ontology_api_name)

    result: dict[str, Any] = {"ontology_api_name": ontology_api_name, "discovered": {}, "steps": []}
    try:
        result = {"ontology_api_name": ontology_api_name, **run_chain(client, apply=not args.discover_only)}
    except FoundryActionChainError as exc:
        write_evidence(result, ok=False, error=str(exc))
        print(f"FOUNDRY ACTION CHAIN FAIL: {exc}", file=sys.stderr)
        return 2
    except requests.RequestException as exc:
        write_evidence(result, ok=False, error=_sanitize(str(exc), [token]))
        print(f"FOUNDRY ACTION CHAIN FAIL: network error: {exc}", file=sys.stderr)
        return 2

    unverified = [step for step in result.get("steps", []) if not step["verified"]]
    out_path = write_evidence(result, ok=not unverified)
    print_summary(result, out_path)

    if unverified:
        print(
            f"FOUNDRY ACTION CHAIN WARNING: {len(unverified)} step(s) did not verify via readback",
            file=sys.stderr,
        )
        return 1

    print("FOUNDRY ACTION CHAIN OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
