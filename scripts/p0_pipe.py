"""P0-A pipe demo: mock adapter → normalize → SQLite store → read-back.

Proves the round-trip that day-1 will run against live StealthMole + Foundry:
  mock records → normalize() (masking enforced) → OntologyStore.write_exposure
  → read-back → per-supplier exposure counts, active-signal counts, masking check.

Run: `uv run python scripts/p0_pipe.py` (no network, no secrets).
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

# Repo root on path (script may be run directly).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adapter.base import normalize                                   # noqa: E402
from adapter.mock import DAY, DEMO_NOW, MODULES, SEED_SUPPLIERS, MockExposureSource  # noqa: E402
from store.sqlite import SqliteOntologyStore                         # noqa: E402

# Active-compromise recency window (relative to the mock demo clock).
ACTIVE_WINDOW = 14 * DAY


def _is_active(row: dict, now: int) -> bool:
    """Path precondition for FlagActiveCompromise: recent stealer device with a
    live session cookie on a vpn/admin account."""
    return bool(
        row.get("has_session_cookie")
        and row.get("account_type") in {"vpn", "admin"}
        and row.get("infected_at") is not None
        and (now - int(row["infected_at"])) <= ACTIVE_WINDOW
    )


def run() -> int:
    source = MockExposureSource()
    store = SqliteOntologyStore(":memory:")

    # 1) Seed registry (Supplier + Domain).
    for fqdn, meta in SEED_SUPPLIERS.items():
        store.upsert_supplier(
            id=meta["id"], name=meta["name"], tier=meta["tier"],
            criticality=meta["criticality"],
        )
        store.upsert_domain(fqdn=fqdn, supplier_id=meta["id"])

    # 2) mock → normalize → write.
    written = 0
    for fqdn in source.domains():
        for module in MODULES:
            for raw in source.search(module, "domain", fqdn):
                exp = normalize(module, raw)
                store.write_exposure(exp, domain=fqdn)
                written += 1

    # 3) Read-back summary.
    print("=" * 68)
    print("P0-A pipe: mock → normalize → SQLite → read-back")
    print(f"anchor DEMO_NOW = {datetime.fromtimestamp(DEMO_NOW, timezone.utc):%Y-%m-%d} UTC")
    print("=" * 68)
    print(f"records written: {written}\n")

    print(f"{'supplier':<20} {'tier':<5} {'exposures':<10} {'active':<7} modules")
    print("-" * 68)
    total_active = 0
    for sup in store.suppliers():
        rows = store.exposures_for_supplier(sup["id"])
        active = [r for r in rows if _is_active(r, DEMO_NOW)]
        total_active += len(active)
        mods = ",".join(sorted({r["module"] for r in rows})) or "-"
        flag = "🔴" if active else ("·" if rows else "clean")
        print(f"{sup['name']:<20} T{sup['tier']:<4} {len(rows):<10} "
              f"{len(active):<7} {mods}   {flag}")

    # 4) Masking verification — no synthetic raw secret survives anywhere.
    dump = json.dumps(store.all_exposures())
    leaked = [s for s in source.raw_secrets() if s in dump]
    all_present = [r for r in store.all_exposures() if r["secret_present"]]
    bad_mask = [r for r in all_present
                if not (r["masked_value"] and r["masked_value"].endswith("***"))]

    print("\n" + "-" * 68)
    print("masking check:")
    print(f"  synthetic raw secrets generated : {len(source.raw_secrets())}")
    print(f"  raw secrets found in read-back   : {len(leaked)}  (must be 0)")
    print(f"  exposures with secret present    : {len(all_present)}")
    print(f"  improperly-masked rows           : {len(bad_mask)}  (must be 0)")
    print(f"\ntotal active-compromise signals    : {total_active}")
    print("=" * 68)

    ok = (written > 0 and leaked == [] and bad_mask == [] and total_active > 0)
    print("RESULT:", "OK ✅" if ok else "FAIL ❌")
    store.close()
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(run())
