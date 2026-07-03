"""Adapter contract + normalization gateway (data-sources.md §2, §5).

`ExposureSource` is the Protocol both the real StealthMole adapter and the
mock implement, so the source is hot-swappable (day-1). `normalize()` is the
single boundary that maps raw StealthMole records to the `Exposure` ontology
object AND enforces secret masking: the raw secret is read only to compute a
masked value (first 2 chars + `***`) and is never stored on any field.

Active-compromise fields (`device.infected_at`, `has_session_cookie`,
`account_type`) are always preserved — they drive active-triage scoring.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import asdict, dataclass
from typing import Any, Protocol, runtime_checkable

# Module reliability → confidence (data-sources.md §5, decision 4).
CONFIDENCE: dict[str, float] = {"cds": 0.9, "ub": 0.9, "cl": 0.6, "cb": 0.3}

# ThreatSource.kind by module (provenance; ontology.md §1).
THREAT_KIND: dict[str, str] = {
    "cds": "darkweb",  # infostealer logs traded on darkweb
    "ub": "combo",     # ULP (URL:LOGIN:PASS) binder
    "cl": "breach",    # breached servers
    "cb": "combo",     # combo lists
}


@runtime_checkable
class ExposureSource(Protocol):
    """Common interface for real + mock StealthMole sources (hot-swap)."""

    def quotas(self) -> dict: ...

    def search(
        self,
        module: str,
        obs_type: str,
        value: str,
        start: int | None = None,
    ) -> list[dict]:
        """Return raw records for `query="{obs_type}:{value}"`. `start` = unix
        epoch lower bound for incremental polling."""
        ...


# ---- Exposure ontology object (data-sources.md §5) --------------------------


@dataclass
class Identity:
    email: str | None = None
    username: str | None = None


@dataclass
class Secret:
    type: str            # plaintext | hash | cookie | token
    masked_value: str | None
    present: bool


@dataclass
class Device:
    """Stealer-infection signal (cds). Active-compromise discriminators."""

    infected_at: int | None = None
    malware: str | None = None
    has_session_cookie: bool | None = None
    account_type: str | None = None  # vpn | admin | user ...
    os: str | None = None


@dataclass
class Exposure:
    id: str
    source: str          # "stealthmole"
    module: str          # cds | ub | cl | cb
    source_ref: str      # provenance handle → original record
    fetched_at: int
    identity: Identity
    secret: Secret
    host: str | None
    device: Device
    observed_at: int | None
    confidence: float
    threat_kind: str
    is_mock: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def is_active_signal(self) -> bool:
        """Path-precondition for FlagActiveCompromise: recent stealer device
        holding a session cookie on a vpn/admin account (recency judged later
        against a scoring clock; here we assert the structural signal)."""
        d = self.device
        return bool(
            d.has_session_cookie
            and d.account_type in {"vpn", "admin"}
            and d.infected_at is not None
        )


# ---- masking + normalization ------------------------------------------------


def mask_secret(value: str | None) -> str | None:
    """First 2 chars + `***`. Never returns the full secret. Short secrets are
    fully redacted to avoid leaking a small value."""
    if value is None:
        return None
    v = str(value)
    if len(v) <= 2:
        return "***"
    return v[:2] + "***"


def _pick_secret(module: str, raw: dict) -> tuple[str, str | None]:
    """Choose the primary stolen secret and its type. For active cds records
    the session cookie is the operative secret; otherwise the password."""
    cookie = raw.get("session_cookie") or raw.get("cookie")
    if module == "cds" and (raw.get("has_cookie") or cookie) and cookie:
        return "cookie", cookie
    password = raw.get("password")
    if password:
        return ("hash" if module == "cl" else "plaintext"), password
    if cookie:
        return "cookie", cookie
    return "plaintext", None


def _source_ref(module: str, raw: dict) -> str:
    ref = raw.get("id")
    if ref:
        return str(ref)
    basis = f"{module}|{raw.get('user')}|{raw.get('host')}"
    return f"{module}:{hashlib.sha1(basis.encode()).hexdigest()[:12]}"


def normalize(module: str, raw: dict, *, fetched_at: int | None = None) -> Exposure:
    """Map a raw StealthMole record → `Exposure`. Masking is enforced here:
    the raw secret is consumed only to produce `masked_value`."""
    module = module.lower()
    fetched_at = int(time.time()) if fetched_at is None else fetched_at

    user = raw.get("user")
    email = user if (user and "@" in user) else None
    username = None if email else user
    identity = Identity(email=email, username=username)

    stype, raw_value = _pick_secret(module, raw)
    secret = Secret(
        type=stype,
        masked_value=mask_secret(raw_value),
        present=raw_value is not None,
    )

    device = Device(
        infected_at=raw.get("infected_at"),
        malware=raw.get("malware"),
        has_session_cookie=bool(raw["has_cookie"]) if "has_cookie" in raw else None,
        account_type=raw.get("account_type"),
        os=raw.get("os"),
    )

    if module == "cds":
        observed_at = raw.get("infected_at") or raw.get("leak_date")
    else:
        observed_at = raw.get("leak_date")
    if observed_at is None:
        observed_at = fetched_at

    ref = _source_ref(module, raw)
    return Exposure(
        id=f"exp:{ref}",
        source="stealthmole",
        module=module,
        source_ref=ref,
        fetched_at=fetched_at,
        identity=identity,
        secret=secret,
        host=raw.get("host"),
        device=device,
        observed_at=observed_at,
        confidence=CONFIDENCE.get(module, 0.3),
        threat_kind=THREAT_KIND.get(module, "combo"),
        is_mock=bool(raw.get("_mock")),
    )
