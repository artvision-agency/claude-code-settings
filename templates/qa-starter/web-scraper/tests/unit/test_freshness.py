"""Data-freshness guard: если последний scrape > 7 дней, тест падает.

Предполагаем наличие `data/last_run.json` с `{"completed_at": <iso>}`.
Подключить путь под свой проект. В CI — ежедневный запуск, fail = alert.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import json

import pytest

LAST_RUN_PATH = Path(__file__).parents[2] / "data" / "last_run.json"
MAX_AGE = timedelta(days=7)


@pytest.mark.unit
def test_last_run_is_fresh():
    if not LAST_RUN_PATH.exists():
        pytest.skip("No last_run.json yet — first deploy?")
    data = json.loads(LAST_RUN_PATH.read_text(encoding="utf-8"))
    completed = datetime.fromisoformat(data["completed_at"])
    age = datetime.now(timezone.utc) - completed
    assert age < MAX_AGE, f"Last scrape was {age} ago, >{MAX_AGE}"
