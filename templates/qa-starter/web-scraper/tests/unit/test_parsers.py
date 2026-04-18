"""Unit tests for pure parsers.

Принцип: парсер получает HTML/str и возвращает dict. Никакой сети.
HTML fixtures лежат в `tests/integration/fixtures/*.html` — те же
снапшоты, что используются в integration для регрессии.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from bs4 import BeautifulSoup

FIXTURES = Path(__file__).parents[1] / "integration" / "fixtures"


def parse_product(html: str) -> dict:
    """Example parser — replace with your extractor.

    Contract: returns dict with keys {name, price, url, telephone?}.
    Missing fields are OK (schema marks them optional).
    """
    soup = BeautifulSoup(html, "lxml")
    return {
        "name": (soup.select_one("[data-testid=product-name]") or soup.h1).get_text(strip=True),
        "price": int((soup.select_one("[data-testid=product-price]") or soup.select_one(".price")).get_text(strip=True).replace(" ", "").rstrip("₽")),
        "url": soup.find("link", rel="canonical")["href"],
    }


def test_parse_product_happy_path():
    html = """
    <html><head><link rel=canonical href=https://example.com/p/1></head>
    <body>
      <h1 data-testid=product-name>Стул венге</h1>
      <span data-testid=product-price>12 500₽</span>
    </body></html>
    """
    result = parse_product(html)
    assert result == {
        "name": "Стул венге",
        "price": 12500,
        "url": "https://example.com/p/1",
    }


def test_parse_product_fallback_to_h1_and_class():
    """Если data-testid отсутствует — fallback на h1/.price (resilient locator)."""
    html = """
    <html><head><link rel=canonical href=https://example.com/p/2></head>
    <body>
      <h1>Стол дубовый</h1>
      <span class=price>8500₽</span>
    </body></html>
    """
    result = parse_product(html)
    assert result["name"] == "Стол дубовый"
    assert result["price"] == 8500


@pytest.mark.parametrize("bad_html", ["", "<html></html>", "<html><body></body></html>"])
def test_parse_product_raises_on_missing(bad_html: str):
    with pytest.raises((AttributeError, TypeError, ValueError)):
        parse_product(bad_html)
