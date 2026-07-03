"""FlagActiveCompromise action (ontology.md §3, §4).

Active compromise is defined STRUCTURALLY, as the existence of a graph path — not
as a heuristic. For each InfectedDevice the action requires ALL of:

  1. `infected_at` within `window_days` of `now`  (recent stealer infection),
  2. `has_session_cookie` is true                  (a live session to replay),
  3. `account_type ∈ {vpn, admin}`                 (privileged account),
  4. a Device → Identity → Domain → Supplier path  (device is attributable), AND
  5. a Supplier → Prime → Program connection       (reaches a defense program).

Only when all five hold is a **CompromiseIncident** opened, carrying the full
traversed path (`Device → Identity → Domain → Supplier → Prime → Program`). If a
complete `traverses` path cannot be assembled the incident is REFUSED
(ontology.md §3: no derived object without its path). Nothing is guessed — active
status is exactly conditions 1–5, evaluated on the defined fields.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

ACTIVE_WINDOW_DAYS = 14
_ACTIVE_ACCOUNTS = {"vpn", "admin"}
_DAY = 86400


class PathIncomplete(Exception):
    """Raised if an otherwise-active device cannot yield a complete traverses
    path — the incident is refused rather than opened without provenance."""


@dataclass
class FlagResult:
    incidents: list[dict] = field(default_factory=list)   # opened CompromiseIncidents
    skipped: list[dict] = field(default_factory=list)     # (device_id, reasons)

    def summary(self) -> str:
        return (f"{len(self.incidents)} active-compromise incident(s) opened; "
                f"{len(self.skipped)} device(s) did not meet the path conditions")


def _recent(infected_at: Any, now: int, window_days: int) -> bool:
    if infected_at is None:
        return False
    return 0 <= (now - int(infected_at)) <= window_days * _DAY


def _build_path(dev: dict, prop_row: dict) -> list[dict]:
    """Assemble the traverses path node list; raise if any hop is missing."""
    nodes = [
        ("InfectedDevice", dev.get("device_id"),
         f"{dev.get('malware') or 'stealer'} · session-cookie · "
         f"infected_at={dev.get('infected_at')}"),
        ("Identity", dev.get("identity_ref"), dev.get("email") or dev.get("username")),
        ("Domain", dev.get("domain_ref"), dev.get("domain_ref")),
        ("Supplier", dev.get("supplier_id"), dev.get("supplier_name")),
        ("Prime", prop_row.get("prime_id"), prop_row.get("prime_name")),
        ("Program", prop_row.get("program_id"), prop_row.get("program_name")),
    ]
    path = [{"type": t, "ref": ref, "detail": detail} for (t, ref, detail) in nodes]
    missing = [n["type"] for n in path if not n["ref"]]
    if missing:
        raise PathIncomplete(
            f"device {dev.get('device_id')}: incomplete traverses path, "
            f"missing hop(s): {', '.join(missing)}"
        )
    return path


def flag_active_compromises(
    store: Any, *, now: int | None = None, window_days: int = ACTIVE_WINDOW_DAYS,
) -> FlagResult:
    """Run FlagActiveCompromise over every InfectedDevice. Opens one
    CompromiseIncident per supplier that has a qualifying device AND a full
    Device→…→Program path. Devices failing any condition are skipped with a
    reason (never dropped silently)."""
    now = int(time.time()) if now is None else now
    result = FlagResult()

    for dev in store.infected_device_paths():
        dev_id = dev.get("device_id")
        reasons: list[str] = []
        if not _recent(dev.get("infected_at"), now, window_days):
            reasons.append(f"stealer infection not within {window_days}d")
        if not dev.get("has_session_cookie"):
            reasons.append("no live session cookie")
        if dev.get("account_type") not in _ACTIVE_ACCOUNTS:
            reasons.append(f"account_type={dev.get('account_type')!r} not vpn/admin")
        supplier_id = dev.get("supplier_id")
        if not supplier_id:
            reasons.append("no Device→Identity→Domain→Supplier path")
        if reasons:
            result.skipped.append({"device_id": dev_id, "reasons": reasons})
            continue

        # condition 5: Supplier → Prime → Program connection must exist
        prop = [r for r in store.propagation_for_supplier(supplier_id)
                if r.get("prime_id") and r.get("program_id")]
        if not prop:
            result.skipped.append({
                "device_id": dev_id,
                "reasons": ["no Supplier→Prime→Program connection"],
            })
            continue

        path = _build_path(dev, prop[0])   # raises PathIncomplete if a hop is missing
        incident_id = f"incident:{supplier_id}"
        store.record_incident(
            id=incident_id, supplier_ref=supplier_id, opened_at=now,
            status="open", path=path,
        )
        result.incidents.append({
            "id": incident_id, "supplier_ref": supplier_id, "device_id": dev_id,
            "opened_at": now, "status": "open", "path": path,
        })

    return result


def path_chain(path: list[dict]) -> str:
    """Render a traverses path as a `Device → … → Program` text chain."""
    return " → ".join(f"{n['type']}({n.get('detail') or n.get('ref')})" for n in path)
