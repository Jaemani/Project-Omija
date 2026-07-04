"""(c) StealthMole JWT header shape + request contract — network is mocked.

NO real API call is made (access opens day-1). We assert the verified auth
contract and that search() builds the right URL/params against an injected
fake client.
"""

import jwt

from adapter.stealthmole import BASE_URL, USER_AGENT, StealthMoleSource, sm_headers


def test_jwt_header_shape():
    headers = sm_headers("AK_test", "SK_test")
    assert set(headers) == {"Authorization", "User-Agent"}
    assert headers["User-Agent"] == USER_AGENT
    scheme, token = headers["Authorization"].split(" ", 1)
    assert scheme == "Bearer"

    payload = jwt.decode(token, "SK_test", algorithms=["HS256"])
    assert payload["access_key"] == "AK_test"
    assert "nonce" in payload and len(payload["nonce"]) >= 8
    assert isinstance(payload["iat"], int)


def test_nonce_is_fresh_per_call():
    a = jwt.decode(
        sm_headers("AK", "SK")["Authorization"].split(" ", 1)[1],
        "SK", algorithms=["HS256"],
    )
    b = jwt.decode(
        sm_headers("AK", "SK")["Authorization"].split(" ", 1)[1],
        "SK", algorithms=["HS256"],
    )
    assert a["nonce"] != b["nonce"]


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _FakeClient:
    """Captures the outbound request instead of hitting the network."""

    def __init__(self, payload):
        self._payload = payload
        self.calls = []

    def get(self, url, params=None, headers=None):
        self.calls.append({"url": url, "params": params, "headers": headers})
        return _FakeResponse(self._payload)


def test_search_builds_verified_contract_no_network():
    fake = _FakeClient({"data": [{"user": "a@x.example", "password": "***", "host": "h"}]})
    src = StealthMoleSource(access_key="AK", secret_key="SK", client=fake)

    out = src.search("cds", "domain", "supplier-a.example")
    assert out and out[0]["host"] == "h"

    call = fake.calls[-1]
    assert call["url"] == f"{BASE_URL}/cds/search"
    assert call["params"]["query"] == "domain:supplier-a.example"
    assert call["params"]["order"] == "asc"
    assert call["headers"]["Authorization"].startswith("Bearer ")


def test_incremental_search_uses_export_with_start():
    fake = _FakeClient({"data": []})
    src = StealthMoleSource(access_key="AK", secret_key="SK", client=fake)
    src.search("ub", "domain", "supplier-a.example", start=1783000000)

    call = fake.calls[-1]
    assert call["url"] == f"{BASE_URL}/ub/export"
    assert call["params"]["start"] == 1783000000
    assert call["params"]["exportType"] == "json"


def test_quotas_requires_credentials():
    src = StealthMoleSource(access_key="", secret_key="")
    try:
        src.quotas()
    except RuntimeError as e:
        assert "credentials missing" in str(e).lower()
    else:  # pragma: no cover
        raise AssertionError("expected RuntimeError for missing credentials")
