"""Small compatibility layer for generated Foundry Python OSDKs.

Generated OSDK names are shaped by Ontology Manager API names, so this module
keeps object/link lookup tolerant while still failing loudly when a required
path is absent.
"""

from __future__ import annotations

import importlib
import json
import os
from collections.abc import Iterable
from typing import Any


class OsdkError(RuntimeError):
    """Generated OSDK client or ontology path could not be resolved."""


def load_env_file(path: str = ".env") -> None:
    if not path or not os.path.exists(path):
        return
    logical_lines: list[str] = []
    pending = ""
    with open(path, encoding="utf-8") as fh:
        for raw_line in fh:
            line = raw_line.rstrip("\n").strip()
            if pending:
                pending += line
            else:
                pending = line
            if pending.endswith("\\"):
                pending = pending[:-1].rstrip() + " "
                continue
            logical_lines.append(pending)
            pending = ""
    if pending:
        logical_lines.append(pending)

    for line in logical_lines:
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if key and key not in os.environ:
            os.environ[key] = value


def import_symbol(path: str) -> Any:
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
        if not name:
            continue
        tried.append(name)
        if isinstance(obj, dict) and name in obj:
            return name, obj[name]
        if hasattr(obj, name):
            return name, getattr(obj, name)
    raise OsdkError(
        f"Could not find {label}. Tried: {', '.join(tried)}. "
        f"Available: {', '.join(public_names(obj)[:80])}"
    )


def resolve_attr_path(root: Any, dotted_path: str) -> Any:
    obj = root
    for part in dotted_path.split("."):
        if part:
            _, obj = get_attr_any(obj, candidate_names(part), dotted_path)
    return obj


def field_value(obj: Any, field: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        value = obj.get(field, default)
    else:
        value = getattr(obj, field, default)
    if callable(value):
        try:
            value = value()
        except TypeError:
            return default
    return value


def object_key(obj: Any) -> str:
    if obj is None:
        return "None"
    if hasattr(obj, "get_primary_key"):
        try:
            value = obj.get_primary_key()
            if value:
                return str(value)
        except TypeError:
            pass
    for field in ("id", "domain_fqdn", "fqdn", "primary_key", "primaryKey", "rid"):
        value = field_value(obj, field)
        if value:
            return str(value)
    return str(obj)


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


def parse_jsonish(value: Any, fallback: Any) -> Any:
    if value is None or value == "":
        return fallback
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return fallback
    return fallback


def object_root(client: Any) -> Any:
    return resolve_attr_path(client, os.getenv("FOUNDRY_OSDK_OBJECTS_PATH", "ontology.objects"))


def object_api(client: Any, object_type: str, env_name: str | None = None) -> Any:
    configured = os.getenv(env_name or f"FOUNDRY_OSDK_OBJECT_{snake_case(object_type).upper()}", "")
    names = [configured] if configured else candidate_names(object_type)
    _, api = get_attr_any(object_root(client), names, f"object type {object_type}")
    return api


def get_object(client: Any, object_type: str, primary_key: str, env_name: str | None = None) -> Any:
    api = object_api(client, object_type, env_name)
    for method_name in ("get", "get_by_primary_key", "get_by_pk", "by_primary_key"):
        if not hasattr(api, method_name):
            continue
        method = getattr(api, method_name)
        for kwargs in ((primary_key,),):
            try:
                return method(*kwargs)
            except TypeError:
                pass
        for kwargs in ({"id": primary_key}, {"primary_key": primary_key}):
            try:
                return method(**kwargs)
            except TypeError:
                pass
    if callable(api):
        return api(primary_key)
    raise OsdkError(f"{object_type} API has no supported get method")


def list_objects(client: Any, object_type: str, env_name: str | None = None) -> list[Any]:
    api = object_api(client, object_type, env_name)
    for method_name in ("iterate", "all", "list", "take"):
        if hasattr(api, method_name):
            method = getattr(api, method_name)
            try:
                return list(method())
            except TypeError:
                try:
                    return list(method(num_items=500))
                except TypeError:
                    continue
    raise OsdkError(f"{object_type} API has no supported list/iterate method")


def related(obj: Any, names: Iterable[str]) -> list[Any]:
    _, relation = get_attr_any(obj, names, "link")
    return materialize_relation(relation)


def first_related(obj: Any, names: Iterable[str]) -> Any | None:
    items = related(obj, names)
    return items[0] if items else None


def build_auth(auth_path: str | None, token: str | None) -> Any:
    if not auth_path:
        return None
    if not token:
        raise OsdkError("FOUNDRY_OSDK_AUTH is set but FOUNDRY_TOKEN is empty")
    auth_cls = import_symbol(auth_path)
    for kwargs in ({"token": token}, {"bearer_token": token}, {"access_token": token}):
        try:
            return auth_cls(**kwargs)
        except TypeError:
            continue
    return auth_cls(token)


def instantiate_client(cls: Any, *, hostname: str | None, token: str | None, auth: Any) -> Any:
    attempts: list[dict[str, Any]] = []
    if auth is not None and hostname:
        attempts += [
            {"hostname": hostname, "auth": auth},
            {"url": hostname, "auth": auth},
            {"base_url": hostname, "auth": auth},
        ]
    if auth is not None:
        attempts.append({"auth": auth})
    if token and hostname:
        attempts += [
            {"hostname": hostname, "token": token},
            {"url": hostname, "token": token},
            {"base_url": hostname, "token": token},
        ]
    if token:
        attempts.append({"token": token})
    if hostname:
        attempts.append({"hostname": hostname})
    attempts.append({})
    errors: list[str] = []
    for kwargs in attempts:
        try:
            return cls(**kwargs)
        except TypeError as exc:
            errors.append(f"{kwargs}: {exc}")
    raise OsdkError("Could not instantiate generated OSDK client: " + " | ".join(errors[:5]))


def build_client_from_env(env_file: str = ".env") -> Any:
    load_env_file(env_file)
    factory_path = os.getenv("FOUNDRY_OSDK_CLIENT_FACTORY", "")
    if factory_path:
        return import_symbol(factory_path)()

    module_name = os.getenv("FOUNDRY_OSDK_MODULE", "")
    client_path = os.getenv("FOUNDRY_OSDK_CLIENT", "")
    if client_path:
        client_cls = import_symbol(client_path)
    else:
        if not module_name:
            raise OsdkError("FOUNDRY_OSDK_MODULE or FOUNDRY_OSDK_CLIENT is required")
        module = importlib.import_module(module_name)
        _, client_cls = get_attr_any(module, ("FoundryClient", "Client"), "generated client")

    token = os.getenv("FOUNDRY_TOKEN") or None
    hostname = os.getenv("FOUNDRY_HOSTNAME") or None
    auth = build_auth(os.getenv("FOUNDRY_OSDK_AUTH", ""), token)
    return instantiate_client(client_cls, hostname=hostname, token=token, auth=auth)
