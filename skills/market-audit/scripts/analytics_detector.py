"""Robust analytics & schema detection for /market-audit Technical subagent.

Fixes 33% false-positive rate from Week 1 pilot — single grep-based detection
falls down on WordPress + LiteSpeed Cache / Autoptimize / WP Rocket sites that
base64-encode inline scripts or lazy-load analytics after first paint.

Two main functions:
- detect_analytics_robust(html) → 3-source detection for Metrika/GA/GTM/etc.
- count_schema_types(html) → BeautifulSoup-based JSON-LD parser

Confidence levels per finding:
- high: 3+ sources confirm (or Playwright DOM)
- medium: 2 sources, OR 1 source + DNS preconnect hint
- low: only 1 source (grep on minified HTML)

Usage from market-audit Technical subagent:
    from analytics_detector import detect_analytics_robust, count_schema_types

    html = fetch(url)
    analytics = detect_analytics_robust(html)
    # → {"yandex_metrika": {"detected": True, "counter_id": "22056523",
    #                       "confidence": "high", "sources": ["base64", "noscript", "preconnect"]}}

    schema = count_schema_types(html)
    # → {"types": ["Organization", "Service", "FAQPage", ...],
    #    "count": 28, "json_ld_blocks": 4, "confidence": "high"}
"""
from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass, field
from typing import Any

try:
    from bs4 import BeautifulSoup  # type: ignore[import-not-found]
except ImportError:
    BeautifulSoup = None  # type: ignore[assignment,misc]


# ---------------------------------------------------------------------------
# Analytics detection — 3+ source pattern matching
# ---------------------------------------------------------------------------

@dataclass
class AnalyticsFinding:
    """Single tool detection result."""
    detected: bool = False
    tracker_id: str = ""
    sources: list[str] = field(default_factory=list)

    @property
    def confidence(self) -> str:
        n = len(self.sources)
        if n >= 3:
            return "high"
        if n == 2:
            return "medium"
        if n == 1:
            return "low"
        return "none"


def _decode_base64_scripts(html: str) -> str:
    """Find data:text/javascript;base64,... payloads and decode them.

    LiteSpeed Cache / Autoptimize / WP Rocket plugins inline scripts as
    base64 data URIs for performance. Standard grep misses these.

    Returns concatenated decoded JS for further pattern matching.
    """
    decoded_parts: list[str] = []
    pattern = re.compile(r"data:(?:text|application)/javascript;base64,([A-Za-z0-9+/=]+)")
    for match in pattern.finditer(html):
        b64 = match.group(1)
        try:
            padded = b64 + "=" * (-len(b64) % 4)
            decoded_parts.append(base64.b64decode(padded).decode("utf-8", errors="ignore"))
        except (ValueError, UnicodeDecodeError):
            continue
    return "\n".join(decoded_parts)


def detect_yandex_metrika(html: str) -> AnalyticsFinding:
    """3-source detection for Я.Метрика.

    Sources checked:
    1. plain JS — `ym(NNNN,` / `yaCounterNNNN`
    2. base64-decoded scripts — same patterns
    3. noscript fallback — `<noscript>...mc.yandex.ru/watch/NNNN`
    4. DNS preconnect/dns-prefetch hints for mc.yandex.ru
    """
    finding = AnalyticsFinding()
    counter_id = ""

    # 1. plain JS
    m = re.search(r"ym\((\d+)\s*,", html) or re.search(r"yaCounter(\d+)", html)
    if m:
        finding.sources.append("plain_js")
        counter_id = m.group(1)

    # 2. base64-encoded inline scripts
    decoded = _decode_base64_scripts(html)
    m = re.search(r"ym\((\d+)\s*,", decoded) or re.search(r"yaCounter(\d+)", decoded)
    if m:
        finding.sources.append("base64")
        counter_id = counter_id or m.group(1)

    # 3. noscript fallback (Я.Метрика всегда генерирует <img> в <noscript>)
    m = re.search(r"<noscript[^>]*>.*?mc\.yandex\.ru/watch/(\d+)", html, re.DOTALL)
    if m:
        finding.sources.append("noscript")
        counter_id = counter_id or m.group(1)

    # 4. DNS hints
    if re.search(r"<link[^>]+(?:preconnect|dns-prefetch)[^>]+mc\.yandex\.(?:ru|com)", html):
        finding.sources.append("preconnect")

    finding.detected = bool(finding.sources)
    finding.tracker_id = counter_id
    return finding


def detect_google_analytics(html: str) -> AnalyticsFinding:
    """3-source detection for GA4 / Universal Analytics.

    Sources: plain JS, base64, gtag.js script tag, dns preconnect.
    """
    finding = AnalyticsFinding()
    tracker_id = ""

    # 1. plain JS — gtag('config', 'G-XXX')  or  ga('create', 'UA-XXX')
    m = (re.search(r"gtag\(\s*['\"]config['\"]\s*,\s*['\"]([G][A-Z]?-[\w-]+)['\"]", html)
         or re.search(r"ga\(\s*['\"]create['\"]\s*,\s*['\"]((?:UA|G)-[\w-]+)['\"]", html))
    if m:
        finding.sources.append("plain_js")
        tracker_id = m.group(1)

    # 2. base64
    decoded = _decode_base64_scripts(html)
    m = (re.search(r"gtag\(\s*['\"]config['\"]\s*,\s*['\"]([G][A-Z]?-[\w-]+)['\"]", decoded)
         or re.search(r"((?:UA|G)-[A-Z0-9-]{6,})", decoded))
    if m:
        finding.sources.append("base64")
        tracker_id = tracker_id or m.group(1)

    # 3. gtag.js / analytics.js script src
    m = re.search(
        r"<script[^>]+src=['\"][^'\"]*google[^'\"]*(?:gtag/js|analytics\.js)[^'\"]*['\"]",
        html,
    )
    if m:
        finding.sources.append("script_src")

    # 4. DNS preconnect
    if re.search(r"<link[^>]+(?:preconnect|dns-prefetch)[^>]+google-analytics\.com", html):
        finding.sources.append("preconnect")

    finding.detected = bool(finding.sources)
    finding.tracker_id = tracker_id
    return finding


def detect_gtm(html: str) -> AnalyticsFinding:
    """Google Tag Manager — 3-source detection."""
    finding = AnalyticsFinding()
    tracker_id = ""

    # 1. plain JS — `'GTM-XXXX'`
    m = re.search(r"GTM-[A-Z0-9]{4,}", html)
    if m:
        finding.sources.append("plain_js")
        tracker_id = m.group(0)

    # 2. base64
    decoded = _decode_base64_scripts(html)
    m = re.search(r"GTM-[A-Z0-9]{4,}", decoded)
    if m:
        finding.sources.append("base64")
        tracker_id = tracker_id or m.group(0)

    # 3. noscript iframe fallback — GTM always has <noscript><iframe src=...gtm.js?id=GTM-...
    m = re.search(r"<noscript[^>]*>.*?googletagmanager\.com/ns\.html\?id=(GTM-[A-Z0-9]+)", html, re.DOTALL)
    if m:
        finding.sources.append("noscript_iframe")
        tracker_id = tracker_id or m.group(1)

    # 4. DNS preconnect
    if re.search(r"<link[^>]+(?:preconnect|dns-prefetch)[^>]+googletagmanager\.com", html):
        finding.sources.append("preconnect")

    finding.detected = bool(finding.sources)
    finding.tracker_id = tracker_id
    return finding


def detect_analytics_robust(html: str) -> dict[str, dict[str, Any]]:
    """Run all analytics detectors and return structured result.

    Returns:
        {
          "yandex_metrika": {"detected": bool, "tracker_id": str, "confidence": str, "sources": list[str]},
          "google_analytics": {...},
          "gtm": {...},
        }
    """
    return {
        "yandex_metrika": _finding_to_dict(detect_yandex_metrika(html)),
        "google_analytics": _finding_to_dict(detect_google_analytics(html)),
        "gtm": _finding_to_dict(detect_gtm(html)),
    }


def _finding_to_dict(f: AnalyticsFinding) -> dict[str, Any]:
    return {
        "detected": f.detected,
        "tracker_id": f.tracker_id,
        "confidence": f.confidence,
        "sources": f.sources,
    }


# ---------------------------------------------------------------------------
# Schema detection via BeautifulSoup
# ---------------------------------------------------------------------------

def count_schema_types(html: str) -> dict[str, Any]:
    """Parse JSON-LD blocks and count Schema.org types.

    Uses BeautifulSoup if available, falls back to regex.

    Recursively walks @type fields (including @graph nested structures).

    Returns:
        {
          "types": list[str] — unique sorted types found,
          "count": int — count of distinct types,
          "json_ld_blocks": int — number of <script type="application/ld+json"> tags,
          "parse_errors": int — blocks that failed to parse,
          "confidence": "high" if BS4 used, "medium" if regex fallback,
        }
    """
    types: set[str] = set()
    blocks = 0
    parse_errors = 0
    confidence = "high"

    if BeautifulSoup is not None:
        soup = BeautifulSoup(html, "html.parser")
        scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
        blocks = len(scripts)
        for script in scripts:
            payload = script.string or script.get_text() or ""
            try:
                data = json.loads(payload)
                _extract_types(data, types)
            except (json.JSONDecodeError, TypeError):
                parse_errors += 1
    else:
        confidence = "medium"
        pattern = re.compile(
            r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            re.DOTALL,
        )
        for match in pattern.finditer(html):
            blocks += 1
            try:
                data = json.loads(match.group(1).strip())
                _extract_types(data, types)
            except (json.JSONDecodeError, TypeError):
                parse_errors += 1

    return {
        "types": sorted(types),
        "count": len(types),
        "json_ld_blocks": blocks,
        "parse_errors": parse_errors,
        "confidence": confidence,
    }


def _extract_types(node: Any, accumulator: set[str]) -> None:
    """Recursively walk JSON-LD structure collecting all @type values."""
    if isinstance(node, dict):
        t = node.get("@type")
        if isinstance(t, str):
            accumulator.add(t)
        elif isinstance(t, list):
            for item in t:
                if isinstance(item, str):
                    accumulator.add(item)
        for value in node.values():
            _extract_types(value, accumulator)
    elif isinstance(node, list):
        for item in node:
            _extract_types(item, accumulator)


# ---------------------------------------------------------------------------
# CLI for ad-hoc testing
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys
    from urllib.request import Request, urlopen

    p = argparse.ArgumentParser(description="Test analytics + schema detection on a URL")
    p.add_argument("url", help="Target URL")
    p.add_argument("--json-output", action="store_true", help="Print as JSON")
    args = p.parse_args(argv)

    req = Request(args.url, headers={"User-Agent": "Mozilla/5.0 market-audit-detector/1.0"})
    with urlopen(req, timeout=30) as r:
        html = r.read().decode("utf-8", errors="ignore")

    result = {
        "url": args.url,
        "analytics": detect_analytics_robust(html),
        "schema": count_schema_types(html),
    }

    if args.json_output:
        json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
        print()
    else:
        print(f"\n=== Analytics detection — {args.url} ===\n")
        for tool, data in result["analytics"].items():
            mark = "✅" if data["detected"] else "❌"
            print(f"  {mark} {tool:<20} confidence={data['confidence']:<7} "
                  f"id={data['tracker_id'] or '—':<20} sources={data['sources']}")
        print(f"\n=== Schema.org types — {result['schema']['count']} ===\n")
        for t in result["schema"]["types"]:
            print(f"  - {t}")
        if result["schema"]["parse_errors"]:
            print(f"\n  ⚠️ {result['schema']['parse_errors']} JSON-LD blocks failed to parse")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
