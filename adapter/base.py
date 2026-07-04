"""Adapter contract + normalization gateway (data-sources.md §2, §5).

`ExposureSource` is the Protocol for synthetic and future approved
candidate sources. `normalize()` is the
single boundary that maps raw candidate records to the `Exposure` ontology
object AND enforces secret masking: the raw secret is read only to compute a
masked value (first 2 chars + `***`) and is never stored on any field.

Active-compromise fields (`device.infected_at`, `has_session_cookie`,
`account_type`) are always preserved — they drive active-triage scoring.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
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
    """Common interface for synthetic or approved non-sensitive sources."""

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
    source: str          # neutral candidate-source id
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


def _first(raw: dict, *names: str) -> Any:
    """Return the first non-empty top-level field from a candidate record.

    Candidate-source response names can vary by module/plan. This keeps the mapping
    conservative and explicit; it never guesses privilege or active status.
    """
    for name in names:
        value = raw.get(name)
        if value is not None and value != "":
            return value
    return None


def _timestamp(value: Any) -> int | None:
    """Normalize epoch seconds/milliseconds or an ISO-8601 string."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        ts = int(value)
        return ts // 1000 if ts > 10_000_000_000 else ts
    text = str(value).strip()
    if text.isdigit():
        ts = int(text)
        return ts // 1000 if ts > 10_000_000_000 else ts
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return int(parsed.timestamp())
    except ValueError:
        return None


def _boolish(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"true", "yes", "y", "1"}:
        return True
    if text in {"false", "no", "n", "0"}:
        return False
    return None


def _pick_secret(module: str, raw: dict) -> tuple[str, str | None]:
    """Choose the primary stolen secret and its type. For active cds records
    the session cookie is the operative secret; otherwise the password."""
    cookie = _first(raw, "session_cookie", "cookie", "session")
    has_cookie = _first(raw, "has_cookie", "has_session_cookie")
    if module == "cds" and (has_cookie or cookie) and cookie:
        return "cookie", cookie
    password = _first(raw, "password", "passwd", "pwd")
    if password:
        return ("hash" if module == "cl" else "plaintext"), password
    if cookie:
        return "cookie", cookie
    return "plaintext", None


def _source_ref(module: str, raw: dict) -> str:
    ref = _first(raw, "id", "_id", "record_id", "uuid")
    if ref:
        return str(ref)
    user = _first(raw, "user", "email", "login", "username", "account")
    host = _first(raw, "host", "url", "domain", "site")
    basis = f"{module}|{user}|{host}"
    return f"{module}:{hashlib.sha1(basis.encode()).hexdigest()[:12]}"


def normalize(module: str, raw: dict, *, fetched_at: int | None = None) -> Exposure:
    """Map a raw candidate record to `Exposure`. Masking is enforced here:
    the raw secret is consumed only to produce `masked_value`."""
    module = module.lower()
    fetched_at = int(time.time()) if fetched_at is None else fetched_at

    user = _first(raw, "user", "email", "login", "username", "account")
    email = user if (user and "@" in user) else None
    username = None if email else user
    identity = Identity(email=email, username=username)

    stype, raw_value = _pick_secret(module, raw)
    secret = Secret(
        type=stype,
        masked_value=mask_secret(raw_value),
        present=raw_value is not None,
    )

    cookie = _first(raw, "session_cookie", "cookie", "session")
    explicit_cookie = _first(raw, "has_cookie", "has_session_cookie")
    device = Device(
        infected_at=_timestamp(_first(
            raw, "infected_at", "infection_date", "compromised_at", "log_date"
        )),
        malware=_first(raw, "malware", "stealer", "family", "malware_name"),
        has_session_cookie=(
            _boolish(explicit_cookie) if explicit_cookie is not None
            else (True if cookie else None)
        ),
        # Never infer privilege from a URL/username. Active status requires an
        # explicit API field or a later reviewed asset mapping.
        account_type=_first(raw, "account_type", "privilege_type"),
        os=_first(raw, "os", "operating_system"),
    )

    if module == "cds":
        observed_at = device.infected_at or _timestamp(_first(
            raw, "leak_date", "breach_date", "observed_at", "date"
        ))
    else:
        observed_at = _timestamp(_first(
            raw, "leak_date", "breach_date", "observed_at", "date"
        ))
    if observed_at is None:
        observed_at = fetched_at

    ref = _source_ref(module, raw)
    return Exposure(
        id=f"exp:{ref}",
        source="candidate",
        module=module,
        source_ref=ref,
        fetched_at=fetched_at,
        identity=identity,
        secret=secret,
        host=_first(raw, "host", "url", "domain", "site"),
        device=device,
        observed_at=observed_at,
        confidence=CONFIDENCE.get(module, 0.3),
        threat_kind=THREAT_KIND.get(module, "combo"),
        is_mock=bool(raw.get("_mock")),
    )
