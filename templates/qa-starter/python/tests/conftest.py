"""Pytest fixtures skeleton.

Add shared fixtures here. pytest auto-discovers this file for all tests
in the same directory tree.
"""

from __future__ import annotations

import asyncio
from collections.abc import Generator, Iterator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest


# ---------- Scope: session ----------


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Absolute path to the project root."""
    return Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def event_loop() -> Iterator[asyncio.AbstractEventLoop]:
    """Single event loop for the whole session (pytest-asyncio)."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------- Scope: function ----------


@pytest.fixture
def tmp_workdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Switch cwd to an isolated tmp dir for the duration of the test."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def env_vars(monkeypatch: pytest.MonkeyPatch) -> Generator[dict[str, str], None, None]:
    """Collect env vars to set; applied lazily."""
    store: dict[str, str] = {}
    yield store
    for key, value in store.items():
        monkeypatch.setenv(key, value)


@pytest.fixture
def mock_http_client() -> MagicMock:
    """Stub HTTP client (requests.Session-like)."""
    client = MagicMock()
    client.get.return_value.status_code = 200
    client.get.return_value.json.return_value = {}
    client.post.return_value.status_code = 201
    return client


# ---------- Markers ----------


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line("markers", "slow: tests that take >1s")
    config.addinivalue_line("markers", "integration: requires external services")
    config.addinivalue_line("markers", "e2e: full end-to-end pipeline tests")


# ---------- Hooks ----------


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Skip integration tests unless --run-integration is passed."""
    if config.getoption("--run-integration", default=False):
        return
    skip_integration = pytest.mark.skip(reason="need --run-integration")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests (calls external services).",
    )


# ---------- Factories (example) ----------


@pytest.fixture
def make_user() -> Any:
    """Factory for user dicts — use to avoid repeating setup in tests."""

    def _factory(**overrides: Any) -> dict[str, Any]:
        defaults = {"id": 1, "name": "Alice", "email": "a@example.com", "active": True}
        defaults.update(overrides)
        return defaults

    return _factory
