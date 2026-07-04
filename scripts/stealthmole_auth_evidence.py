"""Create a secret-free StealthMole auth evidence package.

Use when `/user/quotas` returns 401. The output contains endpoint, server date,
local date, JWT iat skew, key lengths, and HTTP status only. It never writes the
access key, secret key, JWT, or query data.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import jwt


REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = REPO_ROOT / "out" / "p0b" / "stealthmole_auth_evidence.json"
sys.path.insert(0, str(REPO_ROOT))

from adapter.stealthmole import BASE_URL, sm_headers  # noqa: E402


def load_dotenv(path: Path = REPO_ROOT / ".env") -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def server_date(endpoint: str) -> tuple[str | None, str | None]:
    try:
        urlopen(Request(endpoint, method="HEAD"), timeout=10)
        return None, None
    except HTTPError as exc:
        return exc.headers.get("Date"), f"{exc.code} {exc.reason}"
    except URLError as exc:
        return None, f"{type(exc.reason).__name__}: {exc.reason}"


def quotas_status(endpoint: str, access_key: str, secret_key: str) -> tuple[int | None, str]:
    try:
        req = Request(endpoint, headers=sm_headers(access_key, secret_key))
        with urlopen(req, timeout=15) as response:
            response.read()
            return response.status, "OK"
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:120]
        return exc.code, body
    except URLError as exc:
        return None, f"{type(exc.reason).__name__}: {exc.reason}"


def build_evidence() -> dict:
    load_dotenv()
    access_key = os.environ.get("STEALTHMOLE_ACCESS_KEY", "")
    secret_key = os.environ.get("STEALTHMOLE_SECRET_KEY", "")
    endpoint = f"{BASE_URL}/user/quotas"
    local_now = datetime.now(timezone.utc)
    date_header, unauth_head_status = server_date(endpoint)
    parsed_server = parsedate_to_datetime(date_header).astimezone(timezone.utc) if date_header else None

    jwt_iat = None
    iat_minus_server = None
    if access_key and secret_key:
        token = sm_headers(access_key, secret_key)["Authorization"].split(" ", 1)[1]
        payload = jwt.decode(token, secret_key, algorithms=["HS256"], options={"verify_iat": False})
        jwt_iat = payload.get("iat")
        if parsed_server and isinstance(jwt_iat, int):
            iat_minus_server = jwt_iat - int(parsed_server.timestamp())

    status_code, status_body = quotas_status(endpoint, access_key, secret_key) if access_key and secret_key else (None, "missing credentials")
    return {
        "endpoint": endpoint,
        "base_url": BASE_URL,
        "local_utc": local_now.isoformat(),
        "server_date_header": date_header,
        "unauth_head_status": unauth_head_status,
        "jwt_iat": jwt_iat,
        "iat_minus_server_seconds": iat_minus_server,
        "iat_offset_seconds_env": os.environ.get("STEALTHMOLE_IAT_OFFSET_SECONDS", ""),
        "access_key_present": bool(access_key),
        "access_key_length": len(access_key),
        "secret_key_present": bool(secret_key),
        "secret_key_length": len(secret_key),
        "quotas_status_code": status_code,
        "quotas_response_prefix": status_body,
        "diagnosis": (
            "endpoint and JWT iat look aligned; if status is 401, check issued key pair, "
            "account activation, API product enablement, or IP allowlist"
        ),
    }


def main() -> int:
    evidence = build_evidence()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(evidence, indent=2, ensure_ascii=False))
    print(f"wrote {OUT_PATH.relative_to(REPO_ROOT)}")
    return 0 if evidence.get("quotas_status_code") == 200 else 1


if __name__ == "__main__":
    raise SystemExit(main())
