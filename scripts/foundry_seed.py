"""Generate minimal Foundry seed CSVs for Object Explorer path validation.

The output is deliberately small: one multi-tier supplier path, one active
credential exposure, one infected device, and one cross-target VPN asset.
It is optimized for Foundry foreign-key link types: import object CSVs only,
then configure each 1:N/N:1 link from the FK column on the "many" side.

Run:
    uv run python scripts/foundry_seed.py

Then replace/import object backing datasources in the order listed in
out/foundry_seed/README.md, or use the rows as values for Foundry's
auto-generated Create/Edit actions.
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
        writer = csv.DictWriter(
            fh,
            fieldnames=list(rows[0].keys()),
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for old in OUT_DIR.glob("*.csv"):
        old.unlink()

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
                "parent_supplier_id": "sup-f",
                "prime_id": "",
            },
            {
                "id": "sup-f",
                "name": "Foxtrot Metals",
                "tier": 1,
                "criticality": "medium",
                "status": "active",
                "is_prime_candidate": "false",
                "parent_supplier_id": "",
                "prime_id": "prime-x",
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
                "prime_id": "prime-x",
            },
            {
                "id": "prog-harbor",
                "name": "Harbor Sustainment Program",
                "sensitivity": "medium",
                "status": "active",
                "prime_id": "prime-x",
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
                "supplier_id": "sup-h",
                "prime_id": "",
            },
            {
                "fqdn": "metals-f.example",
                "host": "metals-f.example",
                "url": "https://metals-f.example",
                "asset_type": "domain",
                "criticality": "medium",
                "access_surface": "employee_portal",
                "verified_at": now,
                "supplier_id": "sup-f",
                "prime_id": "",
            },
            {
                "fqdn": "vpn.prime-x.example",
                "host": "vpn.prime-x.example",
                "url": "https://vpn.prime-x.example",
                "asset_type": "vpn",
                "criticality": "high",
                "access_surface": "remote_access",
                "verified_at": now,
                "supplier_id": "",
                "prime_id": "prime-x",
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
                "domain_fqdn": "micro-h.example",
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
                "identity_id": "id:ops@micro-h.example",
                "target_domain_fqdn": "vpn.prime-x.example",
                "threat_source_id": "src:stealthmole:mock",
                "infected_device_id": "dev:micro-h:laptop1",
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
                "identity_id": "id:ops@micro-h.example",
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

    for filename, rows in objects.items():
        write_csv(filename, rows)

    readme = OUT_DIR / "README.md"
    readme.write_text(
        "\n".join(
            [
                "# Foundry seed data",
                "",
                "Import/replace object CSVs `01_*.csv` through `08_*.csv`. This folder is FK-link mode: there are no separate link CSVs.",
                "",
                "This assumes `Domain` primary key is `fqdn`.",
                "If other Foundry API names differ, map columns during import. Keep the values unchanged.",
                "",
                "Configure links as foreign-key links using these columns:",
                "",
                "- `subcontracts_to`: Supplier.parent_supplier_id -> Supplier.id",
                "- `supplies`: Supplier.prime_id -> Prime.id",
                "- `runs`: Program.prime_id -> Prime.id",
                "- `owns`: Domain.supplier_id -> Supplier.id",
                "- `prime_owns`: Domain.prime_id -> Prime.id",
                "- `belongs_to`: Identity.domain_fqdn -> Domain.fqdn",
                "- `of`: CredentialExposure.identity_id -> Identity.id",
                "- `targets`: CredentialExposure.target_domain_fqdn -> Domain.fqdn",
                "- `sourced_from`: CredentialExposure.threat_source_id -> ThreatSource.id",
                "- `leaked`: CredentialExposure.infected_device_id -> InfectedDevice.id",
                "- `compromises`: InfectedDevice.identity_id -> Identity.id",
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
