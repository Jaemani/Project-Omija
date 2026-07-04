"""P0 pipe demo: mock adapter -> normalize -> OntologyStore -> read-back.

Default backend is SQLite because it is the offline validation store. Use
`--store foundry` to exercise the exact hot-swap point once the Foundry
ontology and OSDK package are published.

Run:
    uv run python scripts/p0_pipe.py
    uv run python scripts/p0_pipe.py --store foundry
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Literal

# Repo root on path (script may run directly).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adapter.base import normalize  # noqa: E402
from adapter.mock import DAY, DEMO_NOW, MODULES, SEED_SUPPLIERS, MockExposureSource  # noqa: E402
from store.sqlite import SqliteOntologyStore  # noqa: E402

ACTIVE_WINDOW = 14 * DAY
StoreKind = Literal["sqlite", "foundry"]


def _is_active(row: dict, now: int) -> bool:
    """FlagActiveCompromise precondition for the mock corpus."""
    return bool(
        row.get("has_session_cookie")
        and row.get("account_type") in {"vpn", "admin"}
        and row.get("infected_at") is not None
        and (now - int(row["infected_at"])) <= ACTIVE_WINDOW
    )


def _build_store(kind: StoreKind):
    if kind == "sqlite":
        return SqliteOntologyStore(":memory:")

    from store.foundry import FoundryOntologyStore  # noqa: PLC0415

    return FoundryOntologyStore()


def run(store_kind: StoreKind = "sqlite") -> int:
    source = MockExposureSource()
    store = _build_store(store_kind)
    store_label = store_kind.upper()

    try:
        for fqdn, meta in SEED_SUPPLIERS.items():
            store.upsert_supplier(
                id=meta["id"],
                name=meta["name"],
                tier=meta["tier"],
                criticality=meta["criticality"],
            )
            store.upsert_domain(fqdn=fqdn, supplier_id=meta["id"])

        written = 0
        for fqdn in source.domains():
            for module in MODULES:
                for raw in source.search(module, "domain", fqdn):
                    exp = normalize(module, raw)
                    store.write_exposure(exp, domain=fqdn)
                    written += 1
    except NotImplementedError as exc:
        print(
            "Foundry store selected, but the published OSDK calls are not wired yet.\n"
            "Keep using the default SQLite validation store until Ontology Manager "
            "publish + OSDK package install are complete.\n"
            f"detail: {exc}",
            file=sys.stderr,
        )
        return 2

    print("=" * 68)
    print(f"P0 pipe: mock -> normalize -> {store_label} -> read-back")
    print(f"anchor DEMO_NOW {datetime.fromtimestamp(DEMO_NOW, timezone.utc):%Y-%m-%d} UTC")
    print("=" * 68)
    print(f"records written: {written}\n")
    print(f"{'supplier':<20} {'tier':<5} {'exposures':<10} {'active':<7} modules")
    print("-" * 68)

    total_active = 0
    for sup in store.suppliers():
        rows = store.exposures_for_supplier(sup["id"])
        active = [row for row in rows if _is_active(row, DEMO_NOW)]
        total_active += len(active)
        modules = ",".join(sorted({row["module"] for row in rows})) or "-"
        flag = "ACTIVE" if active else ("seen" if rows else "clean")
        print(
            f"{sup['name']:<20} T{sup['tier']:<4} {len(rows):<10} "
            f"{len(active):<7} {modules} {flag}"
        )

    dump = json.dumps(store.all_exposures())
    leaked = [secret for secret in source.raw_secrets() if secret in dump]
    all_present = [row for row in store.all_exposures() if row["secret_present"]]
    bad_mask = [
        row
        for row in all_present
        if not (row["masked_value"] and row["masked_value"].endswith("***"))
    ]

    print("\n" + "-" * 68)
    print("masking check:")
    print(f" synthetic raw secrets generated : {len(source.raw_secrets())}")
    print(f" raw secrets found in read-back : {len(leaked)} (must be 0)")
    print(f" exposures secret present       : {len(all_present)}")
    print(f" improperly-masked rows         : {len(bad_mask)} (must be 0)")
    print(f"\ntotal active-compromise signals : {total_active}")
    print("=" * 68)

    ok = written > 0 and leaked == [] and bad_mask == [] and total_active > 0
    print("RESULT:", "OK" if ok else "FAIL")

    close = getattr(store, "close", None)
    if close:
        close()
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--store",
        choices=("sqlite", "foundry"),
        default="sqlite",
        help="OntologyStore backend. foundry requires a published OSDK package.",
    )
    args = parser.parse_args(argv)
    return run(args.store)


if __name__ == "__main__":
    raise SystemExit(main())
