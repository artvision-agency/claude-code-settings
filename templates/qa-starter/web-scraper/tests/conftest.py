"""Shared fixtures for scraper tests.

Fixtures exposed:
- `browser`, `context`, `page` — provided by pytest-playwright (sync).
- `cassette_dir` — place for HTML snapshots (per-test isolated).
- `golden_dir` — place for last known-good serialised records.
- `schema_path` — JSONSchema file shared by all schema tests.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

HERE = Path(__file__).parent


@pytest.fixture(scope="session")
def schema_path() -> Path:
    return HERE / "schema" / "schema.json"


@pytest.fixture
def cassette_dir(tmp_path: Path) -> Path:
    """Per-test dir for HTML snapshots. Use for unit-tests on saved HTML."""
    d = tmp_path / "cassettes"
    d.mkdir()
    return d


@pytest.fixture(scope="session")
def golden_dir() -> Path:
    d = HERE / "regression" / "golden"
    d.mkdir(exist_ok=True)
    return d


@pytest.fixture(scope="session")
def golden_update() -> bool:
    """Set PYTEST_GOLDEN_UPDATE=1 to overwrite golden files."""
    return os.environ.get("PYTEST_GOLDEN_UPDATE") == "1"


@pytest.fixture
def anti_detect_targets() -> list[str]:
    """Known bot-detection labs. Keep short — these tests are expensive."""
    return [
        "https://bot.sannysoft.com/",
        "https://fingerprint.com/products/bot-detection/",
    ]
