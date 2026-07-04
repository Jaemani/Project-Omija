"""Registry loader — parse `suppliers.yaml` and seed an `OntologyStore`.

Builds the upper half of the supply-chain graph (Supplier·Domain·Prime·Program +
`supplies`/`runs` links) so that once exposures are correlated in, risk can
propagate Supplier → Prime → Program (ontology.md §2). All data is synthetic.
"""

from __future__ import annotations

import json
import os
from typing import Any

import yaml

DEFAULT_REGISTRY_PATH = os.path.join(os.path.dirname(__file__), "suppliers.yaml")


def load_registry(path: str = DEFAULT_REGISTRY_PATH) -> dict[str, Any]:
    """Parse the registry file (.yaml/.yml or .json) into a dict."""
    with open(path, encoding="utf-8") as fh:
        if path.endswith(".json"):
            data = json.load(fh)
        else:
            data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"registry {path!r} did not parse to a mapping")
    for key in ("suppliers", "primes", "programs"):
        data.setdefault(key, [])
    return data


def load_into_store(store: Any, registry: dict[str, Any] | None = None) -> dict[str, int]:
    """Upsert registry objects + links into `store`. Returns counts written.

    Order matters (FKs): Prime/Program first, then Supplier + owns(Domain),
    then the `supplies` / `runs` links.
    """
    if registry is None:
        registry = load_registry()

    counts = {k: 0 for k in (
        "suppliers", "domains", "primes", "programs", "supplies", "runs", "subcontracts"
    )}

    for prime in registry.get("primes", []):
        store.upsert_prime(id=prime["id"], name=prime.get("name", prime["id"]))
        counts["primes"] += 1

    for prog in registry.get("programs", []):
        store.upsert_program(
            id=prog["id"], name=prog.get("name", prog["id"]),
            sensitivity=prog.get("sensitivity"),
        )
        counts["programs"] += 1

    # Prime --runs--> Program (declared on the prime).
    for prime in registry.get("primes", []):
        for program_id in prime.get("runs", []) or []:
            store.link_runs(prime_id=prime["id"], program_id=program_id)
            counts["runs"] += 1

    for sup in registry.get("suppliers", []):
        store.upsert_supplier(
            id=sup["id"], name=sup.get("name", sup["id"]),
            tier=sup.get("tier"), criticality=sup.get("criticality"),
        )
        counts["suppliers"] += 1
        for fqdn in sup.get("domains", []) or []:
            store.upsert_domain(fqdn=fqdn, supplier_id=sup["id"])  # Supplier owns Domain
            counts["domains"] += 1
        # Supplier --supplies--> Prime (single or list).
        supplies = sup.get("supplies")
        for prime_id in ([] if supplies is None else _as_list(supplies)):
            store.link_supplies(supplier_id=sup["id"], prime_id=prime_id)
            counts["supplies"] += 1
        # Supplier --subcontracts_to--> Supplier (single or list). Declared on
        # the SUB (lower-tier) supplier: it delivers up to the parent(s). This is
        # the multi-tier edge; a subcontract-only supplier has NO direct supplies.
        subcontracts = sup.get("subcontracts")
        for parent_id in ([] if subcontracts is None else _as_list(subcontracts)):
            store.link_subcontract(sub_supplier_id=sup["id"], parent_supplier_id=parent_id)
            counts["subcontracts"] += 1

    return counts


def _as_list(value: Any) -> list:
    return value if isinstance(value, list) else [value]
