"""Integration test example — uses mocks to isolate external systems.

Run with: pytest --run-integration  (marked with @pytest.mark.integration).
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


class UserService:
    """Example service that talks to an HTTP backend."""

    def __init__(self, http_client: MagicMock) -> None:
        self.http = http_client

    def get_user(self, user_id: int) -> dict[str, str]:
        resp = self.http.get(f"/users/{user_id}")
        resp.raise_for_status()
        data: dict[str, str] = resp.json()
        return data

    def create_user(self, name: str) -> int:
        resp = self.http.post("/users", json={"name": name})
        resp.raise_for_status()
        created: dict[str, int] = resp.json()
        return created["id"]


# ---------- With mock http_client fixture ----------


def test_get_user_happy_path(mock_http_client: MagicMock) -> None:
    mock_http_client.get.return_value.json.return_value = {"id": 42, "name": "Alice"}
    svc = UserService(mock_http_client)

    user = svc.get_user(42)

    assert user == {"id": 42, "name": "Alice"}
    mock_http_client.get.assert_called_once_with("/users/42")


def test_create_user_returns_id(mock_http_client: MagicMock) -> None:
    mock_http_client.post.return_value.json.return_value = {"id": 7}
    svc = UserService(mock_http_client)

    new_id = svc.create_user("Bob")

    assert new_id == 7
    mock_http_client.post.assert_called_once()


# ---------- Real integration (skipped unless --run-integration) ----------


@pytest.mark.integration
def test_real_api_call_skipped_by_default() -> None:
    """Only runs with --run-integration flag. Put real HTTP/DB calls here."""
    # import httpx
    # response = httpx.get("https://httpbin.org/status/200", timeout=5)
    # assert response.status_code == 200
    pytest.skip("Replace with actual integration test.")


# ---------- Async integration example ----------


@pytest.mark.asyncio
async def test_async_flow() -> None:
    import asyncio

    async def fake_io() -> str:
        await asyncio.sleep(0)
        return "ok"

    result = await fake_io()
    assert result == "ok"
