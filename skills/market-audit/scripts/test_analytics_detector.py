"""Tests for analytics_detector.py — robust detection of Metrika/GA/GTM/Schema.

Run: pytest scripts/test_analytics_detector.py -v
"""
from __future__ import annotations

import base64
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from analytics_detector import (  # type: ignore[import-not-found]
    count_schema_types,
    detect_analytics_robust,
    detect_google_analytics,
    detect_gtm,
    detect_yandex_metrika,
)


# ---------------------------------------------------------------------------
# Yandex Metrika detection
# ---------------------------------------------------------------------------

def test_metrika_plain_js_detected():
    html = """<html><head><script>ym(22056523, 'init', {clickmap:true})</script></head></html>"""
    f = detect_yandex_metrika(html)
    assert f.detected is True
    assert f.tracker_id == "22056523"
    assert "plain_js" in f.sources
    assert f.confidence in ("low", "medium", "high")


def test_metrika_base64_encoded():
    """LiteSpeed Cache base64-encodes inline scripts — old grep would miss this."""
    inner_js = "ym(22056523, 'init', {accurateTrackBounce:true})"
    encoded = base64.b64encode(inner_js.encode()).decode()
    html = f'<html><head><script src="data:text/javascript;base64,{encoded}"></script></head></html>'
    f = detect_yandex_metrika(html)
    assert f.detected is True
    assert f.tracker_id == "22056523"
    assert "base64" in f.sources


def test_metrika_noscript_fallback():
    html = """<html><body>
    <noscript><div><img src="https://mc.yandex.ru/watch/22056523" alt=""/></div></noscript>
    </body></html>"""
    f = detect_yandex_metrika(html)
    assert f.detected is True
    assert f.tracker_id == "22056523"
    assert "noscript" in f.sources


def test_metrika_preconnect_only():
    """Just preconnect = low confidence (could be leftover from removed Metrika)."""
    html = '<link rel="preconnect" href="https://mc.yandex.ru">'
    f = detect_yandex_metrika(html)
    assert f.detected is True  # detected by preconnect alone
    assert f.confidence == "low"


def test_metrika_3_sources_high_confidence():
    """3+ sources = high confidence (real WP+LiteSpeed pattern)."""
    inner = "ym(22056523, 'init', {})"
    encoded = base64.b64encode(inner.encode()).decode()
    html = f"""<html><head>
    <link rel="preconnect" href="https://mc.yandex.ru">
    <script src="data:text/javascript;base64,{encoded}"></script>
    </head><body>
    <noscript><img src="https://mc.yandex.ru/watch/22056523"></noscript>
    </body></html>"""
    f = detect_yandex_metrika(html)
    assert f.detected is True
    assert f.confidence == "high"
    assert len(f.sources) >= 3


def test_metrika_not_present():
    html = "<html><body>Just a page, no analytics.</body></html>"
    f = detect_yandex_metrika(html)
    assert f.detected is False
    assert f.confidence == "none"


# ---------------------------------------------------------------------------
# Google Analytics detection
# ---------------------------------------------------------------------------

def test_ga_gtag_plain():
    html = """<script>gtag('config', 'G-XXXX123ABC')</script>"""
    f = detect_google_analytics(html)
    assert f.detected is True
    assert f.tracker_id == "G-XXXX123ABC"


def test_ga_universal_legacy():
    html = """<script>ga('create', 'UA-12345-1', 'auto')</script>"""
    f = detect_google_analytics(html)
    assert f.detected is True
    assert f.tracker_id == "UA-12345-1"


def test_ga_script_src():
    html = '<script async src="https://www.googletagmanager.com/gtag/js?id=G-ABC123"></script>'
    f = detect_google_analytics(html)
    assert f.detected is True
    assert "script_src" in f.sources


# ---------------------------------------------------------------------------
# GTM detection
# ---------------------------------------------------------------------------

def test_gtm_noscript_iframe():
    html = """<html><body>
    <noscript><iframe src="https://www.googletagmanager.com/ns.html?id=GTM-P2KLK9"></iframe></noscript>
    </body></html>"""
    f = detect_gtm(html)
    assert f.detected is True
    assert f.tracker_id == "GTM-P2KLK9"
    assert "noscript_iframe" in f.sources


# ---------------------------------------------------------------------------
# Schema detection
# ---------------------------------------------------------------------------

def test_schema_single_type():
    html = """<html><head>
    <script type="application/ld+json">
    {"@context": "https://schema.org", "@type": "Organization", "name": "Artvision"}
    </script>
    </head></html>"""
    result = count_schema_types(html)
    assert result["count"] == 1
    assert "Organization" in result["types"]
    assert result["json_ld_blocks"] == 1


def test_schema_graph_with_nested_types():
    """Real-world WP pattern — @graph with multiple types nested."""
    html = """<script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@graph": [
        {"@type": "Organization", "name": "Artvision"},
        {"@type": "WebSite", "url": "https://artvision.pro"},
        {"@type": "Service", "name": "SEO", "provider": {"@type": "Organization"}},
        {"@type": "FAQPage", "mainEntity": [
          {"@type": "Question", "name": "Q1"},
          {"@type": "Answer", "text": "A1"}
        ]}
      ]
    }
    </script>"""
    result = count_schema_types(html)
    assert result["count"] >= 5
    assert "Organization" in result["types"]
    assert "Service" in result["types"]
    assert "FAQPage" in result["types"]
    assert "Question" in result["types"]


def test_schema_multiple_blocks():
    html = """
    <script type="application/ld+json">{"@type": "Organization", "name": "x"}</script>
    <script type="application/ld+json">{"@type": "BreadcrumbList"}</script>
    """
    result = count_schema_types(html)
    assert result["json_ld_blocks"] == 2
    assert "Organization" in result["types"]
    assert "BreadcrumbList" in result["types"]


def test_schema_array_type():
    """@type can be a list — e.g. 'WebPage' + 'CollectionPage' simultaneously."""
    html = """<script type="application/ld+json">
    {"@type": ["WebPage", "CollectionPage"], "name": "Cases"}
    </script>"""
    result = count_schema_types(html)
    assert result["count"] == 2
    assert "WebPage" in result["types"]
    assert "CollectionPage" in result["types"]


def test_schema_parse_error_counted():
    html = """<script type="application/ld+json">{ malformed json}</script>"""
    result = count_schema_types(html)
    assert result["json_ld_blocks"] == 1
    assert result["parse_errors"] == 1
    assert result["count"] == 0


def test_schema_empty():
    html = "<html><body>No structured data here.</body></html>"
    result = count_schema_types(html)
    assert result["count"] == 0
    assert result["json_ld_blocks"] == 0


# ---------------------------------------------------------------------------
# Integration: detect_analytics_robust orchestrator
# ---------------------------------------------------------------------------

def test_robust_returns_all_three_tools():
    html = "<html></html>"
    result = detect_analytics_robust(html)
    assert "yandex_metrika" in result
    assert "google_analytics" in result
    assert "gtm" in result
    assert all(result[k]["detected"] is False for k in result)


def test_robust_high_confidence_metrika():
    inner = "ym(22056523, 'init', {})"
    encoded = base64.b64encode(inner.encode()).decode()
    html = f"""<html><head>
    <link rel="preconnect" href="https://mc.yandex.ru">
    <script src="data:text/javascript;base64,{encoded}"></script>
    </head><body>
    <noscript><img src="https://mc.yandex.ru/watch/22056523"></noscript>
    </body></html>"""
    result = detect_analytics_robust(html)
    assert result["yandex_metrika"]["detected"] is True
    assert result["yandex_metrika"]["confidence"] == "high"
    assert result["yandex_metrika"]["tracker_id"] == "22056523"


def test_robust_mixed_real_world_wp_litespeed():
    """Simulates real WP+LiteSpeed: Metrika base64, GTM noscript, GA via script src."""
    metrika_js = "ym(22056523, 'init', {clickmap:true})"
    metrika_b64 = base64.b64encode(metrika_js.encode()).decode()

    html = f"""<html><head>
    <link rel="dns-prefetch" href="//mc.yandex.ru">
    <link rel="preconnect" href="https://www.googletagmanager.com">
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-ABC123"></script>
    <script>gtag('config', 'G-ABC123')</script>
    <script src="data:text/javascript;base64,{metrika_b64}"></script>
    </head><body>
    <noscript><iframe src="https://www.googletagmanager.com/ns.html?id=GTM-P2KLK9"></iframe></noscript>
    </body></html>"""

    result = detect_analytics_robust(html)
    assert result["yandex_metrika"]["detected"] is True
    assert result["yandex_metrika"]["tracker_id"] == "22056523"
    assert result["google_analytics"]["detected"] is True
    assert result["google_analytics"]["tracker_id"] == "G-ABC123"
    assert result["gtm"]["detected"] is True
    assert result["gtm"]["tracker_id"] == "GTM-P2KLK9"
