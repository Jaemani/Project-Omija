"""Smoke-test a published Foundry Python OSDK against the synthetic ontology seed.

This script intentionally avoids importing any OSDK package at module import
time. The generated package name and auth classes are only known after
Developer Console publishes the OSDK.

Typical flow after OSDK publish:

    uv pip install <generated-osdk-package>
    uv run python scripts/foundry_osdk_smoke.py --probe --module <package>
    uv run python scripts/foundry_osdk_smoke.py

Required env for live smoke depends on the generated OSDK. The most reliable
handoff is to provide a zero-argument client factory via
FOUNDRY_OSDK_CLIENT_FACTORY=module:function. The factory can read secrets from
.env and return an authenticated generated client.
"""

from __future__ import annotations

import argparse
import importlib
import inspect
import os
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any


class SmokeFailure(RuntimeError):
    """Expected seed path could not be read through the generated OSDK."""


@dataclass(frozen=True)
class ReadSpec:
    object_type: str
    primary_key: str
    expected_name: str | None = None
    name_field: str = "name"


READ_SPECS = {
    "supplier_h": ReadSpec("Supplier", "sup-h", "Hotel Microelectronics"),
    "supplier_f": ReadSpec("Supplier", "sup-f", "Foxtrot Metals"),
    "prime_x": ReadSpec("Prime", "prime-x", "Xenon Aerospace"),
    "program_sentinel": ReadSpec(
        "Program", "prog-sentinel", "Sentinel ISR Program"
    ),
    "domain_micro": ReadSpec("Domain", "micro-h.example"),
    "domain_vpn": ReadSpec("Domain", "vpn.prime-x.example"),
    "identity": ReadSpec("Identity", "id:ops@micro-h.example"),
    "exposure": ReadSpec("CredentialExposure", "exp:micro-h:active"),
    "device": ReadSpec("InfectedDevice", "dev:micro-h:laptop1"),
    "source": ReadSpec("ThreatSource", "src:stealthmole:mock"),
    "incident": ReadSpec("CompromiseIncident", "incident:micro-h:active"),
    "draft": ReadSpec("NotificationDraft", "draft:sup-h:2026-07-03"),
}

OBJECTS_PATH_ENV = "FOUNDRY_OSDK_OBJECTS_PATH"

OBJECT_ENV = {
    "Supplier": "FOUNDRY_OSDK_OBJECT_SUPPLIER",
    "Prime": "FOUNDRY_OSDK_OBJECT_PRIME",
    "Program": "FOUNDRY_OSDK_OBJECT_PROGRAM",
    "CredentialExposure": "FOUNDRY_OSDK_OBJECT_CREDENTIAL_EXPOSURE",
    "CompromiseIncident": "FOUNDRY_OSDK_OBJECT_COMPROMISE_INCIDENT",
    "NotificationDraft": "FOUNDRY_OSDK_OBJECT_NOTIFICATION_DRAFT",
}

LINK_ENV = {
    "subcontracts_to": "FOUNDRY_OSDK_LINK_SUBCONTRACTS_TO",
    "supplies": "FOUNDRY_OSDK_LINK_SUPPLIES",
    "runs": "FOUNDRY_OSDK_LINK_RUNS",
    "owns": "FOUNDRY_OSDK_LINK_OWNS",
    "prime_owns": "FOUNDRY_OSDK_LINK_PRIME_OWNS",
    "belongs_to": "FOUNDRY_OSDK_LINK_BELONGS_TO",
    "of": "FOUNDRY_OSDK_LINK_OF",
    "targets": "FOUNDRY_OSDK_LINK_TARGETS",
    "sourced_from": "FOUNDRY_OSDK_LINK_SOURCED_FROM",
    "leaked": "FOUNDRY_OSDK_LINK_LEAKED",
    "traverses_supplier": "FOUNDRY_OSDK_LINK_TRAVERSES_SUPPLIER",
    "traverses_program": "FOUNDRY_OSDK_LINK_TRAVERSES_PROGRAM",
    "cites_incident": "FOUNDRY_OSDK_LINK_CITES_INCIDENT",
}

LINK_DEFAULTS = {
    "subcontracts_to": ["subcontractsTo", "subcontracts_to"],
    "supplies": ["supplies", "primes"],
    "runs": ["runs", "programs"],
    "owns": ["owns", "domains"],
    "prime_owns": ["primeOwns", "prime_owns", "domains"],
    "belongs_to": ["belongsTo", "belongs_to", "domain"],
    "of": ["of", "identity"],
    "targets": ["targets", "domain"],
    "sourced_from": ["sourcedFrom", "sourced_from", "threat_source"],
    "leaked": ["leaked", "credential_exposures", "infected_device"],
    "traverses_supplier": [
        "traversesSupplier",
        "traverses_supplier",
        "traversesSuppliers",
        "suppliers",
    ],
    "traverses_program": [
        "traversesProgram",
        "traverses_program",
        "traversesPrograms",
        "programs",
    ],
    "cites_incident": [
        "citesIncident",
        "cites_incident",
        "incidents",
        "compromise_incidents",
        "cites",
    ],
}


def load_env_file(path: str) -> None:
    """Load simple KEY=VALUE lines without adding a runtime dependency."""

    if not path or not os.path.exists(path):
        return

    with open(path, encoding="utf-8") as fh:
        logical_lines: list[str] = []
        pending = ""
        for raw_line in fh:
            line = raw_line.rstrip("\n")
            stripped = line.strip()
            if pending:
                pending += stripped
            else:
                pending = stripped
            if pending.endswith("\\"):
                pending = pending[:-1].rstrip() + " "
                continue
            logical_lines.append(pending)
            pending = ""
        if pending:
            logical_lines.append(pending)

        for line in logical_lines:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if (
                len(value) >= 2
                and value[0] == value[-1]
                and value[0] in {"'", '"'}
            ):
                value = value[1:-1]
            if key and key not in os.environ:
                os.environ[key] = value


def import_symbol(path: str) -> Any:
    """Import `package.module:attr` or `package.module.attr`."""

    if ":" in path:
        module_name, attr_path = path.split(":", 1)
    else:
        parts = path.split(".")
        if len(parts) < 2:
            return importlib.import_module(path)
        module_name = ".".join(parts[:-1])
        attr_path = parts[-1]

    obj = importlib.import_module(module_name)
    for part in attr_path.split("."):
        obj = getattr(obj, part)
    return obj


def public_names(obj: Any) -> list[str]:
    return sorted(name for name in dir(obj) if not name.startswith("_"))


def lower_first(name: str) -> str:
    return name[:1].lower() + name[1:] if name else name


def snake_case(name: str) -> str:
    chars: list[str] = []
    for index, char in enumerate(name):
        if char.isupper() and index > 0:
            chars.append("_")
        chars.append(char.lower())
    return "".join(chars)


def candidate_names(name: str) -> list[str]:
    candidates = [
        name,
        lower_first(name),
        snake_case(name),
        name.replace("_", ""),
        lower_first(name.replace("_", "")),
    ]
    seen: set[str] = set()
    return [item for item in candidates if not (item in seen or seen.add(item))]


def get_attr_any(obj: Any, names: Iterable[str], label: str) -> tuple[str, Any]:
    tried: list[str] = []
    for name in names:
        tried.append(name)
        if isinstance(obj, dict) and name in obj:
            return name, obj[name]
        if hasattr(obj, name):
            return name, getattr(obj, name)
    raise SmokeFailure(
        f"Could not find {label}. Tried: {', '.join(tried)}. "
        f"Available: {', '.join(public_names(obj)[:80])}"
    )


def resolve_attr_path(root: Any, dotted_path: str) -> Any:
    obj = root
    for part in dotted_path.split("."):
        if not part:
            continue
        _, obj = get_attr_any(obj, candidate_names(part), dotted_path)
    return obj


def object_api(objects_root: Any, object_type: str) -> Any:
    env_name = OBJECT_ENV.get(object_type)
    configured = os.getenv(env_name, "") if env_name else ""
    names = [configured] if configured else candidate_names(object_type)
    _, api = get_attr_any(objects_root, names, f"object type {object_type}")
    return api


def call_get(api: Any, primary_key: str, object_type: str) -> Any:
    for method_name in ("get", "get_by_primary_key", "get_by_pk", "by_primary_key"):
        if not hasattr(api, method_name):
            continue
        method = getattr(api, method_name)
        attempts = (
            lambda: method(primary_key),
            lambda: method(id=primary_key),
            lambda: method(primary_key=primary_key),
        )
        for attempt in attempts:
            try:
                return attempt()
            except TypeError:
                continue

    if callable(api):
        try:
            return api(primary_key)
        except TypeError as exc:
            raise SmokeFailure(
                f"{object_type} API is callable but did not accept primary key "
                f"{primary_key!r}: {exc}"
            ) from exc

    raise SmokeFailure(
        f"Object API for {object_type} has no supported get method. "
        "Expected get(primary_key) or get_by_primary_key(primary_key)."
    )


def read_object(client: Any, spec: ReadSpec) -> Any:
    objects_path = os.getenv(OBJECTS_PATH_ENV, "ontology.objects")
    objects_root = resolve_attr_path(client, objects_path)
    obj = call_get(object_api(objects_root, spec.object_type), spec.primary_key, spec.object_type)
    if obj is None:
        raise SmokeFailure(f"{spec.object_type}.get({spec.primary_key!r}) returned None")
    if spec.expected_name is not None:
        actual = field_value(obj, spec.name_field)
        if actual != spec.expected_name:
            raise SmokeFailure(
                f"{spec.object_type} {spec.primary_key} {spec.name_field} mismatch: "
                f"expected {spec.expected_name!r}, got {actual!r}"
            )
    return obj


def field_value(obj: Any, field: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(field)
    return getattr(obj, field, None)


def object_key(obj: Any) -> str:
    if hasattr(obj, "get_primary_key"):
        try:
            value = obj.get_primary_key()
            if value:
                return str(value)
        except TypeError:
            pass
    for field in ("id", "domain_fqdn", "fqdn", "primary_key", "primaryKey", "rid"):
        value = field_value(obj, field)
        if callable(value):
            try:
                value = value()
            except TypeError:
                continue
        if value:
            return str(value)
    return str(obj)


def link_names(key: str) -> list[str]:
    configured = os.getenv(LINK_ENV[key], "")
    return [configured] if configured else LINK_DEFAULTS[key]


def materialize_relation(value: Any) -> list[Any]:
    if value is None:
        return []
    if callable(value):
        value = value()
    for method_name in ("iterate", "all", "list", "to_list"):
        if hasattr(value, method_name):
            method = getattr(value, method_name)
            try:
                value = method()
                break
            except TypeError:
                continue
    if isinstance(value, dict):
        return list(value.values())
    if isinstance(value, (str, bytes)):
        return [value]
    if isinstance(value, Iterable):
        return list(value)
    return [value]


def related_ids(obj: Any, key: str) -> set[str]:
    _, relation = get_attr_any(obj, link_names(key), f"link {key}")
    try:
        return {object_key(item) for item in materialize_relation(relation)}
    except Exception as exc:  # OSDK raises while ontology/indexing is syncing.
        raise SmokeFailure(f"{type(exc).__name__}: {exc}") from exc


def require_related(obj: Any, key: str, expected_id: str, label: str) -> None:
    ids = related_ids(obj, key)
    if expected_id not in ids:
        raise SmokeFailure(
            f"{label} missing {expected_id!r} via {key}. Found: {sorted(ids)}"
        )


def check_related(obj: Any, key: str, expected_id: str, label: str) -> str:
    try:
        ids = related_ids(obj, key)
    except SmokeFailure as exc:
        return f"FAIL {label}: {exc}"
    if expected_id not in ids:
        return f"FAIL {label}: missing {expected_id!r} via {key}; found {sorted(ids)}"
    return f"OK {label}"


def read_specs(client: Any, names: Iterable[str]) -> dict[str, Any]:
    return {name: read_object(client, READ_SPECS[name]) for name in names}


def run_smoke(client: Any) -> list[str]:
    """Return human-readable passed checks or raise SmokeFailure."""

    objects = read_specs(
        client,
        (
            "supplier_h",
            "supplier_f",
            "prime_x",
            "program_sentinel",
            "exposure",
            "incident",
            "draft",
        ),
    )
    checks: list[str] = [
        "read Supplier sup-h/sup-f, Prime prime-x, Program prog-sentinel",
        "read CredentialExposure exp:micro-h:active",
        "read CompromiseIncident incident:micro-h:active",
        "read NotificationDraft draft:sup-h:2026-07-03",
    ]

    require_related(
        objects["supplier_h"],
        "subcontracts_to",
        "sup-f",
        "sup-h -> subcontractsTo",
    )
    require_related(objects["supplier_f"], "supplies", "prime-x", "sup-f -> supplies")
    require_related(objects["prime_x"], "runs", "prog-sentinel", "prime-x -> runs")
    checks.append(
        "verified supplier path sup-h -> sup-f -> prime-x -> prog-sentinel"
    )

    require_related(
        objects["exposure"],
        "of",
        "id:ops@micro-h.example",
        "exp:micro-h:active -> of",
    )
    require_related(
        objects["exposure"],
        "targets",
        "vpn.prime-x.example",
        "exp:micro-h:active -> targets",
    )
    checks.append("verified exposure of/targets split")

    require_related(
        objects["incident"],
        "traverses_supplier",
        "sup-h",
        "incident -> traverses_supplier",
    )
    require_related(
        objects["incident"],
        "traverses_program",
        "prog-sentinel",
        "incident -> traverses_program",
    )
    checks.append("verified incident traverses_supplier/traverses_program")

    require_related(
        objects["draft"],
        "cites_incident",
        "incident:micro-h:active",
        "draft -> cites_incident",
    )
    checks.append("verified draft cites incident provenance")
    return checks


def run_diagnostics(client: Any) -> list[str]:
    objects = read_specs(client, READ_SPECS.keys())
    checks = [
        check_related(
            objects["supplier_h"],
            "subcontracts_to",
            "sup-f",
            "sup-h -> subcontractsTo",
        ),
        check_related(objects["supplier_f"], "supplies", "prime-x", "sup-f -> supplies"),
        check_related(objects["prime_x"], "runs", "prog-sentinel", "prime-x -> runs"),
        check_related(objects["supplier_h"], "owns", "micro-h.example", "sup-h -> owns"),
        check_related(
            objects["prime_x"],
            "prime_owns",
            "vpn.prime-x.example",
            "prime-x -> prime_owns",
        ),
        check_related(
            objects["identity"],
            "belongs_to",
            "micro-h.example",
            "identity -> belongs_to",
        ),
        check_related(
            objects["exposure"],
            "of",
            "id:ops@micro-h.example",
            "exp:micro-h:active -> of",
        ),
        check_related(
            objects["exposure"],
            "targets",
            "vpn.prime-x.example",
            "exp:micro-h:active -> targets",
        ),
        check_related(
            objects["exposure"],
            "sourced_from",
            "src:stealthmole:mock",
            "exp:micro-h:active -> sourced_from",
        ),
        check_related(
            objects["device"],
            "leaked",
            "exp:micro-h:active",
            "dev:micro-h:laptop1 -> leaked",
        ),
        check_related(
            objects["incident"],
            "traverses_supplier",
            "sup-h",
            "incident -> traverses_supplier",
        ),
        check_related(
            objects["incident"],
            "traverses_program",
            "prog-sentinel",
            "incident -> traverses_program",
        ),
        check_related(
            objects["draft"],
            "cites_incident",
            "incident:micro-h:active",
            "draft -> cites_incident",
        ),
    ]
    return checks


def instantiate(cls: Any, *, hostname: str | None, token: str | None, auth: Any) -> Any:
    kwargs_options: list[dict[str, Any]] = []
    if auth is not None and hostname:
        kwargs_options += [
            {"hostname": hostname, "auth": auth},
            {"url": hostname, "auth": auth},
            {"base_url": hostname, "auth": auth},
        ]
    if auth is not None:
        kwargs_options.append({"auth": auth})
    if token and hostname:
        kwargs_options += [
            {"hostname": hostname, "token": token},
            {"url": hostname, "token": token},
            {"base_url": hostname, "token": token},
        ]
    if token:
        kwargs_options.append({"token": token})
    if hostname:
        kwargs_options.append({"hostname": hostname})
    kwargs_options.append({})

    errors: list[str] = []
    for kwargs in kwargs_options:
        try:
            return cls(**kwargs)
        except TypeError as exc:
            errors.append(f"{cls}({', '.join(kwargs)}) -> {exc}")

    raise SmokeFailure(
        "Could not instantiate OSDK client from env. Prefer setting "
        "FOUNDRY_OSDK_CLIENT_FACTORY=module:function. Attempts: "
        + " | ".join(errors[:6])
    )


def build_auth(auth_path: str | None, token: str | None) -> Any:
    if not auth_path:
        return None
    if not token:
        raise SmokeFailure("FOUNDRY_OSDK_AUTH is set but FOUNDRY_TOKEN is empty")
    auth_cls = import_symbol(auth_path)
    for kwargs in ({"token": token}, {"bearer_token": token}, {"access_token": token}):
        try:
            return auth_cls(**kwargs)
        except TypeError:
            continue
    try:
        return auth_cls(token)
    except TypeError as exc:
        raise SmokeFailure(f"Could not instantiate auth class {auth_path}: {exc}") from exc


def build_client(args: argparse.Namespace) -> Any:
    factory_path = args.client_factory or os.getenv("FOUNDRY_OSDK_CLIENT_FACTORY", "")
    if factory_path:
        return import_symbol(factory_path)()

    module_name = args.module or os.getenv("FOUNDRY_OSDK_MODULE", "")
    client_path = args.client or os.getenv("FOUNDRY_OSDK_CLIENT", "")
    if not module_name and not client_path:
        raise SmokeFailure(
            "Set FOUNDRY_OSDK_CLIENT_FACTORY, or set FOUNDRY_OSDK_MODULE plus "
            "FOUNDRY_OSDK_CLIENT."
        )

    if client_path:
        client_cls = import_symbol(client_path)
    else:
        module = importlib.import_module(module_name)
        _, client_cls = get_attr_any(
            module,
            ("FoundryClient", "Client"),
            "generated OSDK client class",
        )

    token = os.getenv("FOUNDRY_TOKEN") or None
    hostname = os.getenv("FOUNDRY_HOSTNAME") or None
    auth = build_auth(args.auth or os.getenv("FOUNDRY_OSDK_AUTH", ""), token)
    return instantiate(client_cls, hostname=hostname, token=token, auth=auth)


def probe_module(module_name: str) -> list[str]:
    if not module_name:
        raise SmokeFailure("--module or FOUNDRY_OSDK_MODULE is required for --probe")
    module = importlib.import_module(module_name)
    lines = [f"module: {module_name}", f"top-level: {', '.join(public_names(module)[:80])}"]
    for path in ("ontology", "ontology.objects", "ontology.actions"):
        try:
            obj = resolve_attr_path(module, path)
        except SmokeFailure:
            continue
        lines.append(f"{path}: {', '.join(public_names(obj)[:80])}")
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--module", default="")
    parser.add_argument("--client", default="")
    parser.add_argument("--auth", default="")
    parser.add_argument("--client-factory", default="")
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--diagnose", action="store_true")
    args = parser.parse_args(argv)

    load_env_file(args.env_file)

    try:
        if args.probe:
            for line in probe_module(args.module or os.getenv("FOUNDRY_OSDK_MODULE", "")):
                print(line)
            return 0

        client = build_client(args)
        if args.diagnose:
            for line in run_diagnostics(client):
                print(line)
            return 0

        checks = run_smoke(client)
    except SmokeFailure as exc:
        print(f"FOUNDRY OSDK SMOKE FAIL: {exc}", file=sys.stderr)
        return 2

    print("FOUNDRY OSDK SMOKE OK")
    for check in checks:
        print(f" - {check}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
