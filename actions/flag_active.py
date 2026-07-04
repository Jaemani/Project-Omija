"""FlagActiveCompromise action (ontology.md §3, §4).

Active compromise is defined STRUCTURALLY, as the existence of a graph path — not
as a heuristic. For each InfectedDevice the action requires ALL of:

  1. `infected_at` within `window_days` of `now`  (recent stealer infection),
  2. `has_session_cookie` is true                  (a live session to replay),
  3. `account_type ∈ {vpn, admin}`                 (privileged account),
  4. a Device → Identity → Domain → Supplier path  (device is attributable), AND
  5. a Supplier → Prime → Program connection       (reaches a defense program).

Only when all five hold is a **CompromiseIncident** opened, carrying the full
traversed path (`Device → Identity → Domain → Supplier …→ Prime → Program`). The
Supplier→…→Prime→Program half is resolved by the VARIABLE-DEPTH recursive
traverse `store.propagation_paths` (ontology.md §2), so a tier-2 terminal
supplier that reaches a Prime only by subcontracting up through a tier-1 parent
STILL qualifies — the incident path then carries the intermediate Supplier hop(s)
and is longer than the classic 6-node shape. If a complete `traverses` path
cannot be assembled the incident is REFUSED (ontology.md §3: no derived object
without its path). Nothing is guessed — active status is exactly conditions 1–5.

The incident also records a `blast_radius` = every Prime/Program the compromised
supplier reaches (not only the one on the representative path), so the full
downstream reach of a single terminal-tier infection is retained.
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


def _build_path(dev: dict, prop_path: list[dict]) -> list[dict]:
    """Assemble the full traverses path node list. `prop_path` is the variable-
    length Supplier(start)…→Prime→Program node list from `propagation_paths`; the
    Device → Identity → Domain head is prepended. Raises if any hop is missing."""
    head = [
        {"type": "InfectedDevice", "ref": dev.get("device_id"),
         "detail": (f"{dev.get('malware') or 'stealer'} · session-cookie · "
                    f"infected_at={dev.get('infected_at')}")},
        {"type": "Identity", "ref": dev.get("identity_ref"),
         "detail": dev.get("email") or dev.get("username")},
        {"type": "Domain", "ref": dev.get("domain_ref"), "detail": dev.get("domain_ref")},
    ]
    tail = [
        {"type": n["type"], "ref": n.get("ref"),
         "detail": n.get("name") or n.get("ref")}
        for n in prop_path
    ]
    path = head + tail
    missing = [n["type"] for n in path if not n["ref"]]
    if missing:
        raise PathIncomplete(
            f"device {dev.get('device_id')}: incomplete traverses path, "
            f"missing hop(s): {', '.join(missing)}"
        )
    return path


def _blast_radius(paths: list[list[dict]]) -> dict:
    """Every distinct Prime/Program reachable from a supplier (across ALL its
    propagation paths) — the incident's downstream blast radius."""
    primes: dict[str, str] = {}
    programs: dict[str, str] = {}
    for path in paths:
        for n in path:
            if n.get("type") == "Prime" and n.get("ref"):
                primes[n["ref"]] = n.get("name")
            elif n.get("type") == "Program" and n.get("ref"):
                programs[n["ref"]] = n.get("name")
    return {
        "primes": [{"ref": k, "name": v} for k, v in sorted(primes.items())],
        "programs": [{"ref": k, "name": v} for k, v in sorted(programs.items())],
    }


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

        # condition 5: a Supplier …→ Prime → Program connection must exist —
        # resolved by the VARIABLE-DEPTH recursive traverse (pin #2), so a
        # subcontract-only tier-2 supplier reaching a Prime through a tier-1
        # parent qualifies (its path carries the intermediate Supplier hop).
        all_paths = store.propagation_paths(supplier_id)
        complete = [p for p in all_paths
                    if p[-1].get("type") == "Program" and p[-1].get("ref")]
        if not complete:
            result.skipped.append({
                "device_id": dev_id,
                "reasons": ["no Supplier→…→Prime→Program connection"],
            })
            continue

        # representative path (deterministic: shortest chain, then by refs).
        rep = min(complete, key=lambda p: (len(p), [n.get("ref") for n in p]))
        path = _build_path(dev, rep)       # raises PathIncomplete if a hop is missing

        # blast radius is aggregated at the DEVICE level (pin: cross-supplier
        # reach flows Device→compromises→Identity→Supplier, never through a
        # single Identity). Union every Prime/Program reachable from EVERY
        # supplier the device compromises (leaked∘of), not just this one.
        blast_suppliers = set(store.device_compromised_suppliers(dev_id)) or {supplier_id}
        blast_paths = [p for s in sorted(blast_suppliers)
                       for p in store.propagation_paths(s)]
        blast = _blast_radius(blast_paths)
        incident_id = f"incident:{supplier_id}"
        store.record_incident(
            id=incident_id, supplier_ref=supplier_id, opened_at=now,
            status="open", path=path, blast_radius=blast,
        )
        result.incidents.append({
            "id": incident_id, "supplier_ref": supplier_id, "device_id": dev_id,
            "opened_at": now, "status": "open", "path": path, "blast_radius": blast,
        })

    return result


def path_chain(path: list[dict]) -> str:
    """Render a traverses path as a `Device → … → Program` text chain."""
    return " → ".join(f"{n['type']}({n.get('detail') or n.get('ref')})" for n in path)
