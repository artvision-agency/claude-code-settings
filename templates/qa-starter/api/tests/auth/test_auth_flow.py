"""Auth flow skeleton — JWT + OAuth 2.0 scenarios.

Replace TODOs with real calls (httpx / requests against your API).
Keep env-driven config so tests can target local / staging.

Env:
    API_BASE_URL
    TEST_USER_EMAIL, TEST_USER_PASSWORD     — for password grant
    OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET    — for client_credentials
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import pytest

httpx = pytest.importorskip("httpx")


BASE = os.environ.get("API_BASE_URL", "http://localhost:8000")


@dataclass
class Tokens:
    access: str
    refresh: str | None = None


# ---------- Login / refresh ----------


@pytest.mark.integration
def test_login_returns_valid_jwt() -> None:
    email = os.environ.get("TEST_USER_EMAIL")
    password = os.environ.get("TEST_USER_PASSWORD")
    if not (email and password):
        pytest.skip("TEST_USER_EMAIL / TEST_USER_PASSWORD not set")

    r = httpx.post(
        f"{BASE}/auth/login",
        json={"email": email, "password": password},
        timeout=10,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "access_token" in data
    # Basic JWT shape: three dot-separated base64 segments.
    assert data["access_token"].count(".") == 2


@pytest.mark.integration
def test_refresh_token_rotates() -> None:
    # 1. login -> get refresh
    # 2. POST /auth/refresh -> new access + new refresh
    # 3. old refresh should now be rejected (rotation)
    pytest.skip("Replace with real refresh rotation assertion.")


@pytest.mark.integration
def test_invalid_credentials_return_401() -> None:
    r = httpx.post(
        f"{BASE}/auth/login",
        json={"email": "nope@example.com", "password": "wrong"},
        timeout=10,
    )
    assert r.status_code in (400, 401), r.text


# ---------- Authorization ----------


@pytest.mark.integration
def test_protected_endpoint_requires_bearer() -> None:
    r = httpx.get(f"{BASE}/users/me", timeout=10)
    assert r.status_code == 401


@pytest.mark.integration
def test_protected_endpoint_accepts_valid_token() -> None:
    # Obtain access token (fixture in real suite)
    # r = httpx.get(f"{BASE}/users/me", headers={"Authorization": f"Bearer {tok}"})
    # assert r.status_code == 200
    pytest.skip("Replace with real token + GET /users/me assertion.")


# ---------- OAuth client credentials ----------


@pytest.mark.integration
def test_client_credentials_grant() -> None:
    client_id = os.environ.get("OAUTH_CLIENT_ID")
    client_secret = os.environ.get("OAUTH_CLIENT_SECRET")
    if not (client_id and client_secret):
        pytest.skip("OAUTH_CLIENT_ID / OAUTH_CLIENT_SECRET not set")

    r = httpx.post(
        f"{BASE}/oauth/token",
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=10,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("token_type", "").lower() == "bearer"
    assert "access_token" in data
    assert isinstance(data.get("expires_in"), int)
