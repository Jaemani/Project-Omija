"""Real StealthMole hackathon API adapter (data-sources.md §1).

⚠️ Live recon can run whenever valid credentials are present. This module implements the verified contract; the mock (`mock.py`) drives the pipe. Same `ExposureSource` interface → hot-swap
is a one-line source change.

[검증됨] = confirmed from StealthMole official integration code (Cisco XDR /
Netskope CRE v2 plugins). [확인필요] = to be measured during live recon.
"""

from __future__ import annotations

import datetime
import json
import os
import uuid
from datetime import timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import jwt

from .base import ExposureSource

BASE_URL = "https://hackathon.stealthmole.com"
USER_AGENT = "netskope-ce-5.1.1-cre-stealthmole-v1.0.0"

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
    return {"Authorization": f"Bearer {token}", "User-Agent": USER_AGENT}


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
        self.last_response_meta: dict = {}

    # -- internals ---------------------------------------------------------

    def _headers(self) -> dict:
        if not self.access_key or not self.secret_key:
            raise RuntimeError(
                "StealthMole credentials missing. Set STEALTHMOLE_ACCESS_KEY / "
                "STEALTHMOLE_SECRET_KEY. Use the mock adapter for offline validation."
            )
        return sm_headers(self.access_key, self.secret_key)

    def _get_client(self):
        return self._client

    def _get(self, path: str, params: dict) -> dict:
        if self._client is not None:
            resp = self._client.get(
                f"{self.base_url}{path}", params=params, headers=self._headers()
            )
            resp.raise_for_status()
            return resp.json()

        query = urlencode(params)
        url = f"{self.base_url}{path}" + (f"?{query}" if query else "")
        request = Request(url, headers=self._headers())
        with urlopen(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    # -- ExposureSource contract ------------------------------------------

    def quotas(self) -> dict:
        """GET /user/quotas → {"CDS":{"allowed":N,"used":N}, ...}.
        Auth check + open
        modules. live recon: call this first, batch under available credits."""
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
        self.last_response_meta = {
            key: data.get(key)
            for key in ("totalCount", "cursor", "limit", "queryCost")
            if key in data
        }
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


# [확인필요] live recon: cds record shape (device / malware / infected_at / cookie /
#   account_type). Mock assumes these fields; confirm and adjust normalize().
# Hackathon scope: DT and UB are unavailable even if a quota key is present.
# Query only explicitly selected, documented modules.

# StealthMoleSource structurally implements ExposureSource (quotas/search).
_PROTOCOL_CHECK: type[ExposureSource] = StealthMoleSource
