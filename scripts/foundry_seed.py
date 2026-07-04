"""Generate minimal Foundry seed CSVs for Object Explorer path validation.

This generator follows ontology.md as written:

* Object CSVs contain only object properties from the ontology.
* Relationship data lives in separate join-table CSVs.
* Join-table column names mirror Foundry's generated default pattern, e.g.
  `left-Supplier-primary-key` / `right-Supplier-primary-key`.

Run:
    uv run python scripts/foundry_seed.py
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
        writer.writerows(rows)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for old in OUT_DIR.glob("*.csv"):
        old.unlink()

    now = "2026-07-03T00:00:00Z"
    infected_at = "2026-07-01T00:00:00Z"

    object_rows: dict[str, list[dict[str, object]]] = {
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
        "09_merge_proposal.csv": [
            {
                "id": "merge:micro-h:ops",
                "identity_a": "id:ops@micro-h.example",
                "identity_b": "id:ops@micro-h.example",
                "basis": "self-link smoke test; replace with real candidate pair later",
                "confidence": 1.0,
                "created_at": now,
                "reviewer": "demo-reviewer",
                "status": "proposed",
            },
        ],
        "10_risk_assessment.csv": [
            {
                "id": "risk:sup-h:2026-07-03",
                "supplier_ref": "sup-h",
                "risk_band": "A",
                "score": 95.76,
                "grade": "critical",
                "active_flag": "true",
                "computed_at": now,
                "components": '{"active_path":true,"session_cookie":true,"tier":2}',
                "scoring_version": "v0.2",
                "schema_version": "ontology-v0.2",
                "status": "active",
            },
        ],
        "11_compromise_incident.csv": [
            {
                "id": "incident:micro-h:active",
                "supplier_ref": "sup-h",
                "risk_band": "A",
                "opened_at": now,
                "path_snapshot": '["dev:micro-h:laptop1","exp:micro-h:active","id:ops@micro-h.example","sup-h","sup-f","prime-x","prog-sentinel"]',
                "path_hash": "pathhash:micro-h-active",
                "blast_radius": '{"suppliers":["sup-h","sup-f"],"primes":["prime-x"],"programs":["prog-sentinel","prog-harbor"]}',
                "path_confidence": 0.9,
                "status": "open",
            },
        ],
        "12_program_exposure.csv": [
            {
                "id": "progexp:prog-sentinel:2026-07-03",
                "program_ref": "prog-sentinel",
                "risk_band": "A",
                "score": 90.0,
                "grade": "critical",
                "active_flag": "true",
                "computed_at": now,
                "components": '{"active_incidents":1,"supplier_risk":"risk:sup-h:2026-07-03"}',
                "contributing_paths": '["pathhash:micro-h-active"]',
                "scoring_version": "v0.2",
                "status": "active",
            },
        ],
        "13_notification_draft.csv": [
            {
                "id": "draft:sup-h:2026-07-03",
                "recipient_ref": "sup-h",
                "body": "Synthetic demo draft: rotate exposed account, revoke sessions, enforce MFA, and review VPN access evidence.",
                "created_at": now,
                "created_by": "Project Omija",
                "reviewer": "demo-reviewer",
                "status": "draft",
            },
        ],
    }

    link_rows: dict[str, list[dict[str, object]]] = {
        "20_link_subcontracts_to.csv": [
            {
                "left-Supplier-primary-key": "sup-h",
                "right-Supplier-primary-key": "sup-f",
            },
        ],
        "21_link_supplies.csv": [
            {
                "left-Supplier-primary-key": "sup-f",
                "right-Prime-primary-key": "prime-x",
            },
        ],
        "22_link_runs.csv": [
            {
                "left-Prime-primary-key": "prime-x",
                "right-Program-primary-key": "prog-sentinel",
            },
            {
                "left-Prime-primary-key": "prime-x",
                "right-Program-primary-key": "prog-harbor",
            },
        ],
        "23_link_owns.csv": [
            {
                "left-Supplier-primary-key": "sup-h",
                "right-Domain-primary-key": "micro-h.example",
            },
            {
                "left-Supplier-primary-key": "sup-f",
                "right-Domain-primary-key": "metals-f.example",
            },
        ],
        "24_link_prime_owns.csv": [
            {
                "left-Prime-primary-key": "prime-x",
                "right-Domain-primary-key": "vpn.prime-x.example",
            },
        ],
        "25_link_belongs_to.csv": [
            {
                "left-Identity-primary-key": "id:ops@micro-h.example",
                "right-Domain-primary-key": "micro-h.example",
            },
        ],
        "26_link_of.csv": [
            {
                "left-CredentialExposure-primary-key": "exp:micro-h:active",
                "right-Identity-primary-key": "id:ops@micro-h.example",
            },
        ],
        "27_link_targets.csv": [
            {
                "left-CredentialExposure-primary-key": "exp:micro-h:active",
                "right-Domain-primary-key": "vpn.prime-x.example",
            },
        ],
        "28_link_sourced_from.csv": [
            {
                "left-CredentialExposure-primary-key": "exp:micro-h:active",
                "right-ThreatSource-primary-key": "src:stealthmole:mock",
            },
        ],
        "29_link_leaked.csv": [
            {
                "left-InfectedDevice-primary-key": "dev:micro-h:laptop1",
                "right-CredentialExposure-primary-key": "exp:micro-h:active",
            },
        ],
        "30_link_compromises.csv": [
            {
                "left-InfectedDevice-primary-key": "dev:micro-h:laptop1",
                "right-Identity-primary-key": "id:ops@micro-h.example",
            },
        ],
        "31_link_merge_candidates_identity.csv": [
            {
                "left-MergeProposal-primary-key": "merge:micro-h:ops",
                "right-Identity-primary-key": "id:ops@micro-h.example",
            },
        ],
        "32_link_risk_evidenced_by_exposure.csv": [
            {
                "left-RiskAssessment-primary-key": "risk:sup-h:2026-07-03",
                "right-CredentialExposure-primary-key": "exp:micro-h:active",
            },
        ],
        "33_link_risk_evidenced_by_device.csv": [
            {
                "left-RiskAssessment-primary-key": "risk:sup-h:2026-07-03",
                "right-InfectedDevice-primary-key": "dev:micro-h:laptop1",
            },
        ],
        "34_link_risk_evidenced_by_incident.csv": [
            {
                "left-RiskAssessment-primary-key": "risk:sup-h:2026-07-03",
                "right-CompromiseIncident-primary-key": "incident:micro-h:active",
            },
        ],
        "35_link_traverses_identity.csv": [
            {
                "left-CompromiseIncident-primary-key": "incident:micro-h:active",
                "right-Identity-primary-key": "id:ops@micro-h.example",
            },
        ],
        "36_link_traverses_asset.csv": [
            {
                "left-CompromiseIncident-primary-key": "incident:micro-h:active",
                "right-Domain-primary-key": "micro-h.example",
            },
            {
                "left-CompromiseIncident-primary-key": "incident:micro-h:active",
                "right-Domain-primary-key": "vpn.prime-x.example",
            },
        ],
        "37_link_traverses_supplier.csv": [
            {
                "left-CompromiseIncident-primary-key": "incident:micro-h:active",
                "right-Supplier-primary-key": "sup-h",
            },
            {
                "left-CompromiseIncident-primary-key": "incident:micro-h:active",
                "right-Supplier-primary-key": "sup-f",
            },
        ],
        "38_link_traverses_prime.csv": [
            {
                "left-CompromiseIncident-primary-key": "incident:micro-h:active",
                "right-Prime-primary-key": "prime-x",
            },
        ],
        "39_link_traverses_program.csv": [
            {
                "left-CompromiseIncident-primary-key": "incident:micro-h:active",
                "right-Program-primary-key": "prog-sentinel",
            },
            {
                "left-CompromiseIncident-primary-key": "incident:micro-h:active",
                "right-Program-primary-key": "prog-harbor",
            },
        ],
        "40_link_program_evidenced_by_risk.csv": [
            {
                "left-ProgramExposure-primary-key": "progexp:prog-sentinel:2026-07-03",
                "right-RiskAssessment-primary-key": "risk:sup-h:2026-07-03",
            },
        ],
        "41_link_program_evidenced_by_incident.csv": [
            {
                "left-ProgramExposure-primary-key": "progexp:prog-sentinel:2026-07-03",
                "right-CompromiseIncident-primary-key": "incident:micro-h:active",
            },
        ],
        "42_link_cites_exposure.csv": [
            {
                "left-NotificationDraft-primary-key": "draft:sup-h:2026-07-03",
                "right-CredentialExposure-primary-key": "exp:micro-h:active",
            },
        ],
        "43_link_cites_device.csv": [
            {
                "left-NotificationDraft-primary-key": "draft:sup-h:2026-07-03",
                "right-InfectedDevice-primary-key": "dev:micro-h:laptop1",
            },
        ],
        "44_link_cites_incident.csv": [
            {
                "left-NotificationDraft-primary-key": "draft:sup-h:2026-07-03",
                "right-CompromiseIncident-primary-key": "incident:micro-h:active",
            },
        ],
        "45_link_cites_risk.csv": [
            {
                "left-NotificationDraft-primary-key": "draft:sup-h:2026-07-03",
                "right-RiskAssessment-primary-key": "risk:sup-h:2026-07-03",
            },
        ],
    }

    for filename, rows in object_rows.items():
        write_csv(filename, rows)
    for filename, rows in link_rows.items():
        write_csv(filename, rows)

    (OUT_DIR / "README.md").write_text(
        "\n".join(
            [
                "# Foundry seed data",
                "",
                "This seed follows `ontology.md`: object properties stay on object CSVs, links use separate join-table CSVs.",
                "",
                "Import/replace object CSVs `01_*.csv` through `13_*.csv` first.",
                "Then use link CSVs `20_*.csv` through `45_*.csv` as join-table datasources for the matching Link Types.",
                "",
                "Important:",
                "- If a Link Type was recreated as foreign-key based, it will not use these link CSVs. Recreate it as join-table based or add the FK property to the Object Type.",
                "- If Foundry generated different join-table column names, keep the row values but rename the two CSV headers to exactly match the Link Type's expected columns.",
                "- Foundry Link Types are concrete pairs. Conceptual union links like `evidenced_by` and `cites` are split by target type in this seed.",
                "",
                "Primary Object Explorer paths to verify:",
                "1. `sup-h -> subcontractsTo -> sup-f -> supplies -> prime-x -> runs -> prog-sentinel`",
                "2. `exp:micro-h:active -> of -> id:ops@micro-h.example -> belongsTo -> micro-h.example -> owns(reverse) -> sup-h`",
                "3. `exp:micro-h:active -> targets -> vpn.prime-x.example -> primeOwns(reverse) -> prime-x -> runs -> prog-sentinel`",
                "4. `incident:micro-h:active -> traverses_* -> Identity/Domain/Supplier/Prime/Program`",
                "5. `draft:sup-h:2026-07-03 -> cites_* -> Exposure/Device/Incident/Risk`",
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
