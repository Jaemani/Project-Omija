"""Generate minimal Foundry seed CSVs for Object Explorer path validation.

The output is deliberately small: one multi-tier supplier path, one active
credential exposure, one infected device, and one cross-target VPN asset.

Run:
    uv run python scripts/foundry_seed.py

Then import CSVs in the order listed in out/foundry_seed/README.md, or use the
rows as values for Foundry's auto-generated Create/Edit actions.
"""

from __future__ import annotations

import csv
import os
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "out" / "foundry_seed"


def write_csv(name: str, rows: list[dict[str, object]]) -> None:
    path = OUT_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"{name} has no rows")

    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    now = "2026-07-03T00:00:00Z"
    infected_at = "2026-07-01T00:00:00Z"

    objects: dict[str, list[dict[str, object]]] = {
        "01_supplier.csv": [
            {
                "id": "sup-h",
                "name": "Hotel Microelectronics",
                "tier": 2,
                "criticality": "high",
                "status": "active",
                "is_prime_candidate": "false",
            },
            {
                "id": "sup-f",
                "name": "Foxtrot Metals",
                "tier": 1,
                "criticality": "medium",
                "status": "active",
                "is_prime_candidate": "false",
            },
        ],
        "02_prime.csv": [
            {"id": "prime-x", "name": "Xenon Aerospace", "status": "active"},
        ],
        "03_program.csv": [
            {
                "id": "prog-sentinel",
                "name": "Sentinel ISR Program",
                "sensitivity": "high",
                "status": "active",
            },
            {
                "id": "prog-harbor",
                "name": "Harbor Sustainment Program",
                "sensitivity": "medium",
                "status": "active",
            },
        ],
        "04_domain.csv": [
            {
                "fqdn": "micro-h.example",
                "host": "micro-h.example",
                "url": "https://micro-h.example",
                "asset_type": "domain",
                "criticality": "high",
                "access_surface": "employee_portal",
                "verified_at": now,
            },
            {
                "fqdn": "metals-f.example",
                "host": "metals-f.example",
                "url": "https://metals-f.example",
                "asset_type": "domain",
                "criticality": "medium",
                "access_surface": "employee_portal",
                "verified_at": now,
            },
            {
                "fqdn": "vpn.prime-x.example",
                "host": "vpn.prime-x.example",
                "url": "https://vpn.prime-x.example",
                "asset_type": "vpn",
                "criticality": "high",
                "access_surface": "remote_access",
                "verified_at": now,
            },
        ],
        "05_identity.csv": [
            {
                "id": "id:ops@micro-h.example",
                "email": "ops@micro-h.example",
                "username": "ops",
                "canonical_handle": "ops@micro-h.example",
                "account_type": "admin",
                "status": "active",
                "merged_into": "",
            },
        ],
        "06_credential_exposure.csv": [
            {
                "id": "exp:micro-h:active",
                "module": "cds",
                "secret_type": "cookie",
                "secret_present": "true",
                "masked_value": "SI***",
                "secret_fingerprint": "fp:micro-h:active",
                "first_seen": infected_at,
                "last_seen": now,
                "source_ref": "src:stealthmole:mock",
                "confidence": 0.9,
                "status": "active",
            },
        ],
        "07_infected_device.csv": [
            {
                "id": "dev:micro-h:laptop1",
                "device_fingerprint": "dfp:micro-h:laptop1",
                "malware": "RedLine",
                "infected_at": infected_at,
                "has_session_cookie": "true",
                "os": "Windows 10",
                "status": "active",
            },
        ],
        "08_threat_source.csv": [
            {
                "id": "src:stealthmole:mock",
                "kind": "osint_api",
                "name": "StealthMole mock",
                "collected_at": now,
                "reliability": 0.9,
                "status": "active",
            },
        ],
    }

    links: dict[str, list[dict[str, object]]] = {
        "20_link_subcontracts_to.csv": [
            {"from_supplier_id": "sup-h", "to_supplier_id": "sup-f"},
        ],
        "21_link_supplies.csv": [
            {"supplier_id": "sup-f", "prime_id": "prime-x"},
        ],
        "22_link_runs.csv": [
            {"prime_id": "prime-x", "program_id": "prog-sentinel"},
            {"prime_id": "prime-x", "program_id": "prog-harbor"},
        ],
        "23_link_owns.csv": [
            {"supplier_id": "sup-h", "domain_fqdn": "micro-h.example"},
            {"supplier_id": "sup-f", "domain_fqdn": "metals-f.example"},
        ],
        "24_link_prime_owns.csv": [
            {"prime_id": "prime-x", "domain_fqdn": "vpn.prime-x.example"},
        ],
        "25_link_belongs_to.csv": [
            {"identity_id": "id:ops@micro-h.example", "domain_fqdn": "micro-h.example"},
        ],
        "26_link_of.csv": [
            {"credential_exposure_id": "exp:micro-h:active", "identity_id": "id:ops@micro-h.example"},
        ],
        "27_link_targets.csv": [
            {"credential_exposure_id": "exp:micro-h:active", "domain_fqdn": "vpn.prime-x.example"},
        ],
        "28_link_sourced_from.csv": [
            {"credential_exposure_id": "exp:micro-h:active", "threat_source_id": "src:stealthmole:mock"},
        ],
        "29_link_leaked.csv": [
            {"infected_device_id": "dev:micro-h:laptop1", "credential_exposure_id": "exp:micro-h:active"},
        ],
        "30_link_compromises.csv": [
            {"infected_device_id": "dev:micro-h:laptop1", "identity_id": "id:ops@micro-h.example"},
        ],
    }

    for filename, rows in objects.items():
        write_csv(filename, rows)
    for filename, rows in links.items():
        write_csv(filename, rows)

    readme = OUT_DIR / "README.md"
    readme.write_text(
        "\n".join(
            [
                "# Foundry seed data",
                "",
                "Import object CSVs `01_*.csv` through `08_*.csv` first, then link CSVs `20_*.csv` through `30_*.csv`.",
                "",
                "This assumes `Domain` primary key is `fqdn`. If your Link Type UI names the endpoint differently, map `domain_fqdn` to the Domain primary key.",
                "If other Foundry API names differ, map columns during import. Keep the values unchanged.",
                "",
                "Primary Object Explorer paths to verify:",
                "",
                "1. `sup-h -> subcontractsTo -> sup-f -> supplies -> prime-x -> runs -> prog-sentinel`",
                "2. `exp:micro-h:active -> of -> id:ops@micro-h.example -> belongsTo -> micro-h.example -> owns(reverse) -> sup-h`",
                "3. `exp:micro-h:active -> targets -> vpn.prime-x.example -> primeOwns(reverse) -> prime-x -> runs -> prog-sentinel`",
                "",
                "This seed is synthetic. It contains no real secrets; `masked_value` is already redacted.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    print(f"Wrote Foundry seed CSVs to {OUT_DIR.relative_to(REPO_ROOT)}")
    for filename in sorted(os.listdir(OUT_DIR)):
        print(f" - {filename}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
