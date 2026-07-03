"""Synthetic supplier registry (P1).

`registry/suppliers.yaml` is the seed for the supply-chain graph: Suppliers +
their Domains, Primes, Programs, and the `supplies` (Supplier→Prime) / `runs`
(Prime→Program) links that let risk propagate upward. Everything is synthetic
(*.example, made-up names). `loader.load_into_store` upserts it into an
`OntologyStore`.
"""

from .loader import DEFAULT_REGISTRY_PATH, load_into_store, load_registry

__all__ = ["DEFAULT_REGISTRY_PATH", "load_into_store", "load_registry"]
