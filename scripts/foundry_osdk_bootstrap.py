"""Install/probe/smoke-test the generated Foundry Python OSDK.

This is the no-UI handoff entrypoint after the user has generated a Python OSDK
package in Developer Console and put non-secret package metadata plus secrets in
`.env`.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import shlex
import subprocess
import sys

try:
    from foundry_osdk_smoke import load_env_file, main as smoke_main
except ModuleNotFoundError:  # pragma: no cover - import path used by tests/tools.
    from scripts.foundry_osdk_smoke import load_env_file, main as smoke_main


def _mask(value: str) -> str:
    return "<set>" if value else "<empty>"


def _module_installed(module_name: str) -> bool:
    return bool(module_name and importlib.util.find_spec(module_name) is not None)


def _install_command(
    install_cmd: str, package_spec: str, *, force_reinstall: bool = False
) -> list[str]:
    if install_cmd:
        install_cmd = os.path.expandvars(install_cmd)
        parts = shlex.split(install_cmd)
        if parts[:3] == ["uv", "pip", "install"]:
            command = parts
            if force_reinstall and "--force-reinstall" not in command:
                command.insert(3, "--force-reinstall")
            return command
        if len(parts) >= 2 and parts[0] in {"pip", "pip3"} and parts[1] == "install":
            command = ["uv", "pip", "install", *parts[2:]]
            if force_reinstall and "--force-reinstall" not in command:
                command.insert(3, "--force-reinstall")
            return command
        if (
            len(parts) >= 4
            and parts[0] in {"python", "python3"}
            and parts[1:4] == ["-m", "pip", "install"]
        ):
            command = ["uv", "pip", "install", *parts[4:]]
            if force_reinstall and "--force-reinstall" not in command:
                command.insert(3, "--force-reinstall")
            return command
        return parts
    command = ["uv", "pip", "install", package_spec]
    if force_reinstall and "--force-reinstall" not in command:
        command.insert(3, "--force-reinstall")
    return command


def _sanitize(text: str) -> str:
    sanitized = text
    for key in ("FOUNDRY_TOKEN", "FOUNDRY_OSDK_INSTALL_CMD"):
        value = os.getenv(key, "")
        if value:
            sanitized = sanitized.replace(value, f"<{key.lower()}>")
    # Hide package indexes and auth-bearing URLs while keeping pip's error text.
    sanitized = " ".join(
        "<url>" if part.startswith(("http://", "https://")) else part
        for part in sanitized.split()
    )
    return sanitized


def _install_osdk(
    install_cmd: str, package_spec: str, *, force_reinstall: bool = False
) -> None:
    result = subprocess.run(
        _install_command(install_cmd, package_spec, force_reinstall=force_reinstall),
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if result.returncode != 0:
        output = _sanitize(result.stdout[-4000:] if result.stdout else "")
        raise RuntimeError(
            "OSDK install command failed. Inspect Developer Console package "
            f"access, package name, and token scope locally. Sanitized tail:\n{output}"
        )


def _required_missing() -> list[str]:
    missing: list[str] = []
    if not os.getenv("FOUNDRY_OSDK_CLIENT_FACTORY"):
        for key in ("FOUNDRY_OSDK_MODULE", "FOUNDRY_HOSTNAME", "FOUNDRY_TOKEN"):
            if not os.getenv(key):
                missing.append(key)
    return missing


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", default=".env")
    parser.add_argument(
        "--skip-install",
        action="store_true",
        help="Do not run uv pip install even if FOUNDRY_OSDK_PACKAGE is set.",
    )
    parser.add_argument(
        "--force-reinstall",
        action="store_true",
        help="Force reinstall the generated OSDK package even if module is importable.",
    )
    args = parser.parse_args(argv)

    load_env_file(args.env_file)

    module_name = os.getenv("FOUNDRY_OSDK_MODULE", "")
    install_cmd = os.getenv("FOUNDRY_OSDK_INSTALL_CMD", "")
    package_spec = os.getenv("FOUNDRY_OSDK_PACKAGE", "")

    print("Foundry OSDK bootstrap")
    for key in (
        "FOUNDRY_OSDK_INSTALL_CMD",
        "FOUNDRY_OSDK_PACKAGE",
        "FOUNDRY_OSDK_MODULE",
        "FOUNDRY_OSDK_CLIENT",
        "FOUNDRY_OSDK_AUTH",
        "FOUNDRY_OSDK_CLIENT_FACTORY",
        "FOUNDRY_HOSTNAME",
        "FOUNDRY_TOKEN",
    ):
        print(f" - {key}={_mask(os.getenv(key, ''))}")

    missing = _required_missing()
    if missing:
        print(
            "FOUNDRY OSDK BOOTSTRAP FAIL: missing "
            + ", ".join(missing)
            + ". Put values in .env; do not paste tokens in chat.",
            file=sys.stderr,
        )
        return 2

    should_install = (
        (install_cmd or package_spec)
        and not args.skip_install
        and (args.force_reinstall or not _module_installed(module_name))
    )
    if should_install:
        print("Installing generated OSDK package")
        _install_osdk(
            install_cmd,
            package_spec,
            force_reinstall=args.force_reinstall,
        )
    elif module_name:
        print(f"Install step skipped; module {module_name!r} is already importable or no package spec set.")

    if module_name:
        probe_status = smoke_main(["--env-file", args.env_file, "--probe", "--module", module_name])
        if probe_status != 0:
            return probe_status

    return smoke_main(["--env-file", args.env_file])


if __name__ == "__main__":
    raise SystemExit(main())
