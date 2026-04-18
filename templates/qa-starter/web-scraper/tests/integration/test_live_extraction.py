"""Smoke: проверяем что боевой URL отдаёт extractable HTML.

НЕ скрейпим массово в тестах. 1-2 URL достаточно — это canary, а не
production run. Для массовых прогонов — отдельный CLI, не pytest.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.unit.test_parsers import parse_product  # reuse extractor

FIXTURES = Path(__file__).parent / "fixtures"

SMOKE_URLS = [
    # Заменить на реальные URL проекта. Держать 1-2 штуки.
    "https://example.com/p/1",
]


@pytest.mark.integration
@pytest.mark.parametrize("url", SMOKE_URLS)
def test_live_page_extracts_minimum_fields(page, url: str):
    page.goto(url, wait_until="domcontentloaded", timeout=15_000)
    html = page.content()

    # Save snapshot for regression/unit re-use
    snapshot = FIXTURES / f"{url.rsplit('/', 1)[-1]}.html"
    snapshot.parent.mkdir(exist_ok=True)
    snapshot.write_text(html, encoding="utf-8")

    record = parse_product(html)
    assert record["name"]
    assert record["price"] > 0
    assert record["url"].startswith("http")


@pytest.mark.integration
def test_page_does_not_serve_captcha(page):
    page.goto(SMOKE_URLS[0], wait_until="domcontentloaded", timeout=15_000)
    body = page.locator("body").inner_text().lower()
    forbidden = ["captcha", "access denied", "cloudflare", "доступ ограничен"]
    hits = [w for w in forbidden if w in body]
    assert not hits, f"Possible anti-bot block: {hits}"
