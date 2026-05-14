"""Pytest для domain-intel.

Запуск:
  cd ~/.claude/skills/domain-intel
  .venv/bin/python -m pytest tests/ -v

Сетевые тесты помечены @pytest.mark.network — пропускаются по умолчанию.
Запуск всех тестов: pytest tests/ -v --run-network
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import domain_intel as di  # noqa: E402


def pytest_addoption(parser):  # type: ignore[no-redef]
    parser.addoption("--run-network", action="store_true", default=False,
                     help="Запустить тесты с реальными сетевыми вызовами")


def pytest_collection_modifyitems(config, items):  # type: ignore[no-redef]
    if config.getoption("--run-network"):
        return
    skip_network = pytest.mark.skip(reason="нужен --run-network")
    for item in items:
        if "network" in item.keywords:
            item.add_marker(skip_network)


# ─────────────────────────────────────────────────────────────────────────────
# Unit tests (без сети)

class TestSnapshot:
    def test_date_format(self):
        s = di.Snapshot(timestamp="20240315120000", original_url="https://x.ru/", status_code="200")
        assert s.date == "2024-03-15"

    def test_archive_url(self):
        s = di.Snapshot(timestamp="20240101000000", original_url="https://x.ru/page", status_code="200")
        assert s.archive_url == "https://web.archive.org/web/20240101000000/https://x.ru/page"

    def test_invalid_timestamp_falls_back(self):
        s = di.Snapshot(timestamp="bogus", original_url="https://x.ru/", status_code="200")
        # date property должно вернуть префикс без падения
        assert isinstance(s.date, str)


class TestExtractSeoFields:
    def test_basic(self):
        html = """
        <html lang="ru">
        <head>
            <title>Главная — Стоматология</title>
            <meta name="description" content="Лечение зубов в СПб">
            <meta name="keywords" content="стоматология, зубы">
            <meta property="og:title" content="OG Title">
            <link rel="canonical" href="https://x.ru/">
        </head>
        <body><h1>Стоматология «Улыбка»</h1></body>
        </html>
        """
        f = di.extract_seo_fields(html)
        assert f["title"] == "Главная — Стоматология"
        assert f["h1"] == "Стоматология «Улыбка»"
        assert f["meta_description"] == "Лечение зубов в СПб"
        assert f["meta_keywords"] == "стоматология, зубы"
        assert f["og_title"] == "OG Title"
        assert f["canonical"] == "https://x.ru/"
        assert f["lang"] == "ru"

    def test_empty_html(self):
        assert di.extract_seo_fields("") == {}

    def test_no_meta(self):
        f = di.extract_seo_fields("<html><body><p>no meta</p></body></html>")
        assert f["title"] == ""
        assert f["meta_description"] == ""
        assert f["h1"] == ""

    def test_multiple_h1(self):
        f = di.extract_seo_fields("<html><body><h1>One</h1><h1>Two</h1></body></html>")
        assert "One" in f["h1"] and "Two" in f["h1"]


class TestCdxQuery:
    def test_empty_response(self):
        with patch.object(di, "http_get") as mock_get:
            mock_get.return_value = MagicMock(status_code=200, text="", json=lambda: [])
            result = di.cdx_query("example.com")
            assert result == []

    def test_normal_response(self):
        cdx_payload = [
            ["timestamp", "original", "statuscode", "mimetype", "digest", "length"],
            ["20200101120000", "https://x.ru/", "200", "text/html", "ABC123", "1024"],
            ["20210315090000", "https://x.ru/", "200", "text/html", "DEF456", "1100"],
        ]
        with patch.object(di, "http_get") as mock_get:
            mock_get.return_value = MagicMock(status_code=200, text="data",
                                              json=lambda: cdx_payload)
            result = di.cdx_query("x.ru")
            assert len(result) == 2
            assert result[0].timestamp == "20200101120000"
            assert result[0].original_url == "https://x.ru/"
            assert result[1].date == "2021-03-15"

    def test_passes_filters(self):
        with patch.object(di, "http_get") as mock_get:
            mock_get.return_value = MagicMock(status_code=200, text="x",
                                              json=lambda: [])
            di.cdx_query("x.ru", limit=50, date_from="2020", date_to="2024", match_type="exact")
            args, kwargs = mock_get.call_args
            params = kwargs.get("params") or args[1]
            assert params["limit"] == "50"
            assert params["from"] == "2020"
            assert params["to"] == "2024"
            assert params["matchType"] == "exact"


class TestAgeYears:
    def test_iso_string(self):
        # фиксируем относительную проверку — возраст положительный и в разумных пределах
        age = di._age_years("2020-01-01")
        assert age is not None and age > 0

    def test_iso_with_t(self):
        age = di._age_years("2020-01-01T12:00:00")
        assert age is not None

    def test_none(self):
        assert di._age_years(None) is None

    def test_list(self):
        age = di._age_years(["2020-01-01", "2020-02-01"])
        assert age is not None

    def test_garbage(self):
        assert di._age_years("not a date") is None


class TestParseRdap:
    def test_basic_parse(self):
        rdap = {
            "events": [
                {"eventAction": "registration", "eventDate": "2018-05-01T00:00:00Z"},
                {"eventAction": "expiration", "eventDate": "2027-05-01T00:00:00Z"},
                {"eventAction": "last changed", "eventDate": "2026-01-15T00:00:00Z"},
            ],
            "nameservers": [{"ldhName": "ns1.reg.ru"}, {"ldhName": "ns2.reg.ru"}],
            "status": ["client transfer prohibited"],
            "entities": [],
        }
        out = di._parse_rdap(rdap, "example.ru")
        assert out["domain"] == "example.ru"
        assert out["creation_date"] == "2018-05-01T00:00:00Z"
        assert out["expiration_date"] == "2027-05-01T00:00:00Z"
        assert "ns1.reg.ru" in out["name_servers"]
        assert out["source"] == "RDAP"


# ─────────────────────────────────────────────────────────────────────────────
# Network tests (только с --run-network)

@pytest.mark.network
def test_real_history_example_com():
    snaps = di.cdx_query("example.com", limit=5)
    assert len(snaps) > 0
    assert all(s.timestamp for s in snaps)


@pytest.mark.network
def test_real_whois_example_com():
    info = di.whois_lookup("example.com")
    assert info, "whois вернул пусто для example.com"
    assert "registrar" in info or "creation_date" in info


@pytest.mark.network
def test_real_intel_artvision_pro():
    """Полная проверка intel-команды на нашем домене."""
    info = di.whois_lookup("artvision.pro")
    snaps = di.cdx_query("artvision.pro", collapse="digest", limit=10)
    assert info
    assert len(snaps) > 0
