"""Real StealthMole API v2 adapter (data-sources.md §1 — verified contract).

⚠️ Access opens day-1 (P0-B). This module implements the verified contract but
performs NO network call in P0-A. Wiring/live recon happens in P0-B; until then
the mock (`mock.py`) drives the pipe. Same `ExposureSource` interface → hot-swap
is a one-line source change.

[검증됨] = confirmed from StealthMole official integration code (Cisco XDR /
Netskope CRE v2 plugins). [확인필요] = to be measured on day-1.
"""

from __future__ import annotations

import datetime
import os
import uuid
from datetime import timezone

import jwt

from .base import ExposureSource

BASE_URL = "https://api.stealthmole.com/v2"

# Observable types accepted by /{module}/search [검증됨].
OBS_TYPES = ("email", "domain", "ip", "url")


def sm_headers(access_key: str, secret_key: str) -> dict:
    """JWT (HS256) auth header, fresh per request [검증됨].

    payload = access_key + nonce(uuid4) + iat(current UTC epoch), signed with
    secret_key → `Authorization: Bearer <jwt>`.
    """
    payload = {
        "access_key": access_key,
        "nonce": str(uuid.uuid4()),
        "iat": int(datetime.datetime.now(timezone.utc).timestamp()),
    }
    token = jwt.encode(payload, secret_key)  # HS256 default
    return {"Authorization": f"Bearer {token}"}


class StealthMoleSource:
    """Implements `ExposureSource` against the live API.

    Credentials come from env (`STEALTHMOLE_ACCESS_KEY` / `STEALTHMOLE_SECRET_KEY`).
    A `httpx.Client` can be injected for testing (network is mocked in tests).
    """

    def __init__(
        self,
        access_key: str | None = None,
        secret_key: str | None = None,
        client=None,  # httpx.Client | None — injected in tests
        base_url: str = BASE_URL,
        timeout: float = 30.0,
    ) -> None:
        self.access_key = access_key or os.environ.get("STEALTHMOLE_ACCESS_KEY", "")
        self.secret_key = secret_key or os.environ.get("STEALTHMOLE_SECRET_KEY", "")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = client

    # -- internals ---------------------------------------------------------

    def _headers(self) -> dict:
        if not self.access_key or not self.secret_key:
            raise RuntimeError(
                "StealthMole credentials missing. Set STEALTHMOLE_ACCESS_KEY / "
                "STEALTHMOLE_SECRET_KEY (day-1). P0-A uses the mock adapter."
            )
        return sm_headers(self.access_key, self.secret_key)

    def _get_client(self):
        if self._client is None:
            import httpx  # local import: P0-A never reaches here

            self._client = httpx.Client(timeout=self.timeout)
        return self._client

    def _get(self, path: str, params: dict) -> dict:
        resp = self._get_client().get(
            f"{self.base_url}{path}", params=params, headers=self._headers()
        )
        resp.raise_for_status()
        return resp.json()

    # -- ExposureSource contract ------------------------------------------

    def quotas(self) -> dict:
        """GET /v2/user/quotas → {"CDS":{"allowed":N}, ...}. Auth check + open
        modules. day-1: call this first, batch under available credits."""
        return self._get("/user/quotas", params={})

    def search(
        self,
        module: str,
        obs_type: str,
        value: str,
        start: int | None = None,
    ) -> list[dict]:
        """GET /v2/{module}/search?query={obs_type}:{value}&order=asc.

        `start` (unix epoch) → prefer /export for time-filtered incremental
        pulls. Returns the raw `data` list; `normalize()` maps to Exposure.
        """
        params: dict = {"query": f"{obs_type}:{value}", "order": "asc"}
        if start is not None:
            # /export supports start=<unix>, limit=0 (all), exportType=json.
            params.update({"start": start, "limit": 0, "exportType": "json"})
            data = self._get(f"/{module.lower()}/export", params=params)
        else:
            data = self._get(f"/{module.lower()}/search", params=params)
        return data.get("data", [])

    def export(
        self,
        module: str,
        obs_type: str,
        value: str,
        start: int | None = None,
        limit: int = 0,
    ) -> list[dict]:
        """GET /v2/{module}/export — bulk + time filter (incremental polling)."""
        params: dict = {
            "query": f"{obs_type}:{value}",
            "limit": limit,        # 0 = all
            "exportType": "json",
        }
        if start is not None:
            params["start"] = start
        return self._get(f"/{module.lower()}/export", params=params).get("data", [])


# [확인필요] day-1: cds record shape (device / malware / infected_at / cookie /
#   account_type). Mock assumes these fields; confirm and adjust normalize().
# [확인필요] day-1: which modules are enabled on the issued account beyond
#   cds/ub/cl/cb (dt/tt/rm/gm/lm) — check via quotas() before correlating.

# StealthMoleSource structurally implements ExposureSource (quotas/search).
_PROTOCOL_CHECK: type[ExposureSource] = StealthMoleSource
