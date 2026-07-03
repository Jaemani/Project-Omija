"""Deterministic mock StealthMole source (data-sources.md §3, §4).

Builds a fixed synthetic corpus (seeded RNG) so demos are reproducible and
tests are stable. Only synthetic `*.example` domains are used — no real
company data (CLAUDE.md guardrail). Every record carries `_mock: true`.

Coverage guarantees (asserted by tests):
- all four modules (cds/ub/cl/cb) produce records,
- at least one cds ACTIVE-compromise record: recent `infected_at`,
  `has_cookie=true`, `account_type ∈ {vpn,admin}`, malware (RedLine).

Passwords/cookies here are obviously synthetic strings; they exist so
`normalize()` can be shown to strip them (masking). They are NOT real leaked
secrets.
"""

from __future__ import annotations

import random
from datetime import datetime, timezone

from .base import ExposureSource

MODULES = ("cds", "ub", "cl", "cb")

# Fixed anchor for deterministic recency (CLAUDE.md currentDate 2026-07-03).
# Active records sit within a few days of this; stale ones are weeks back.
DEMO_NOW = int(datetime(2026, 7, 3, tzinfo=timezone.utc).timestamp())
DAY = 86400

# Synthetic supplier registry (5–7 domains, some clean). Full registry = P1.
# supplies→prime kept minimal here; propagation graph is built in P2.
SEED_SUPPLIERS: dict[str, dict] = {
    "supplier-a.example":  {"id": "sup-a", "name": "Alpha Precision",   "tier": 1, "criticality": "high",   "prime": "prime-x", "clean": False},
    "supplier-b.example":  {"id": "sup-b", "name": "Bravo Systems",     "tier": 1, "criticality": "high",   "prime": "prime-x", "clean": False},
    "supplier-c.example":  {"id": "sup-c", "name": "Charlie Components", "tier": 2, "criticality": "medium", "prime": "prime-y", "clean": False},
    "parts-d.example":     {"id": "sup-d", "name": "Delta Parts",       "tier": 2, "criticality": "medium", "prime": "prime-y", "clean": False},
    "avionics-g.example":  {"id": "sup-g", "name": "Golf Avionics",     "tier": 2, "criticality": "high",   "prime": "prime-x", "clean": False},
    "logistics-e.example": {"id": "sup-e", "name": "Echo Logistics",    "tier": 2, "criticality": "low",    "prime": "prime-y", "clean": True},
    "metals-f.example":    {"id": "sup-f", "name": "Foxtrot Metals",    "tier": 1, "criticality": "medium", "prime": "prime-x", "clean": True},
}

# Domains that carry a deliberate active-compromise case (recent stealer +
# session cookie on vpn/admin). Must be non-clean.
ACTIVE_DOMAINS = {"supplier-a.example", "avionics-g.example"}


class MockExposureSource:
    """Implements `ExposureSource`. Corpus built once at construction (seeded)."""

    def __init__(self, seed: int = 4703) -> None:
        self.seed = seed
        self._rng = random.Random(seed)
        # corpus[domain][module] -> list[raw record]
        self._corpus: dict[str, dict[str, list[dict]]] = {}
        self._raw_secrets: set[str] = set()
        self._build()

    # -- ExposureSource contract ------------------------------------------

    def quotas(self) -> dict:
        """Mirror /v2/user/quotas shape. Mock reports generous credits."""
        return {m.upper(): {"allowed": 1000, "_mock": True} for m in MODULES}

    def search(
        self,
        module: str,
        obs_type: str,
        value: str,
        start: int | None = None,
    ) -> list[dict]:
        """Return raw records for a domain (obs_type=='domain'). `start` filters
        by observed timestamp to mimic incremental polling."""
        module = module.lower()
        records = list(self._corpus.get(value, {}).get(module, []))
        if start is not None:
            records = [r for r in records if _record_time(r) >= start]
        return records

    # -- demo/test helpers -------------------------------------------------

    def domains(self) -> list[str]:
        return list(SEED_SUPPLIERS.keys())

    def all_records(self) -> list[tuple[str, str, dict]]:
        """(domain, module, raw) for the whole corpus."""
        out: list[tuple[str, str, dict]] = []
        for domain, by_mod in self._corpus.items():
            for module, recs in by_mod.items():
                for r in recs:
                    out.append((domain, module, r))
        return out

    def raw_secrets(self) -> set[str]:
        """Every synthetic secret string generated — for masking assertions
        (none of these must survive normalization into stored output)."""
        return set(self._raw_secrets)

    # -- corpus construction ----------------------------------------------

    def _build(self) -> None:
        for domain, meta in SEED_SUPPLIERS.items():
            self._corpus[domain] = {m: [] for m in MODULES}
            if meta["clean"]:
                continue
            self._gen_cds(domain)
            self._gen_ub(domain)
            self._gen_cl(domain)
            self._gen_cb(domain)

    def _pw(self, tag: str) -> str:
        # Obviously-synthetic password; long enough that a 2-char mask != full.
        pw = f"Synthetic-{tag}-{self._rng.randint(1000, 9999)}!"
        self._raw_secrets.add(pw)
        return pw

    def _cookie(self, tag: str) -> str:
        tok = "SID" + "".join(self._rng.choice("abcdef0123456789") for _ in range(28))
        self._raw_secrets.add(tok)
        return tok

    def _gen_cds(self, domain: str) -> None:
        recs = self._corpus[domain]["cds"]
        if domain in ACTIVE_DOMAINS:
            # ACTIVE: recent infection, live session cookie, vpn/admin account.
            acct = "vpn" if domain == "supplier-a.example" else "admin"
            recs.append({
                "id": f"cds-{domain}-active",
                "user": f"ops@{domain}",
                "password": self._pw("cds-active"),
                "session_cookie": self._cookie("cds-active"),
                "has_cookie": True,
                "malware": "RedLine",
                "infected_at": DEMO_NOW - 2 * DAY,   # recent
                "account_type": acct,
                "host": f"vpn.{domain}",
                "os": "Windows 10",
                "_mock": True,
            })
        # A stale, non-active stealer hit (older, no cookie, normal account).
        recs.append({
            "id": f"cds-{domain}-stale",
            "user": f"user1@{domain}",
            "password": self._pw("cds-stale"),
            "has_cookie": False,
            "malware": "Raccoon",
            "infected_at": DEMO_NOW - 40 * DAY,
            "account_type": "user",
            "host": f"portal.{domain}",
            "os": "Windows 11",
            "_mock": True,
        })

    def _gen_ub(self, domain: str) -> None:
        # ub = URL:LOGIN:PASS. Schema [검증됨]: {user, password, host}.
        # Reuses ops@ — same Identity as the cds stealer hit → entity resolution
        # merges stealer + ULP leak into one Identity (ontology.md §0).
        self._corpus[domain]["ub"].append({
            "id": f"ub-{domain}-0",
            "user": f"ops@{domain}",
            "password": self._pw("ub"),
            "host": f"https://mail.{domain}/login",
            "leak_date": DEMO_NOW - 12 * DAY,
            "_mock": True,
        })

    def _gen_cl(self, domain: str) -> None:
        # cl = breached servers (Medium). Stored hashed here.
        self._corpus[domain]["cl"].append({
            "id": f"cl-{domain}-0",
            "user": f"admin@{domain}",
            "password": self._pw("cl"),
            "host": f"hr.{domain}",
            "leak_date": DEMO_NOW - 90 * DAY,
            "_mock": True,
        })

    def _gen_cb(self, domain: str) -> None:
        # cb = recirculated combo list (Low confidence). Reuses admin@ (same
        # Identity as the cl breach) → a second entity-resolution merge.
        self._corpus[domain]["cb"].append({
            "id": f"cb-{domain}-0",
            "user": f"admin@{domain}",
            "password": self._pw("cb"),
            "host": domain,
            "leak_date": DEMO_NOW - 200 * DAY,
            "_mock": True,
        })


def _record_time(raw: dict) -> int:
    return int(raw.get("infected_at") or raw.get("leak_date") or 0)


# MockExposureSource structurally implements ExposureSource (quotas/search).
_PROTOCOL_CHECK: type[ExposureSource] = MockExposureSource
