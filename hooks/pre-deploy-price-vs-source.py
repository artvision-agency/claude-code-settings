#!/usr/bin/env python3
"""
pre-deploy-price-vs-source.py
PreToolUse hook: блокирует scp HTML если цены в HTML расходятся с источником >50%.
Прецедент: IPOTEKA c052407c — студия Парусная 1: HTML 6.1М, реальная цена 11.07М (+82%).
Bypass: PRICE_VERIFY_SKIP=1
"""

import json
import math
import os
import re
import sys
import urllib.request
import urllib.error
import hashlib
import time
import logging
from pathlib import Path

LOG_PATH = os.path.expanduser("~/.claude/logs/pre-deploy-price-vs-source.log")
CACHE_DIR = Path("/tmp/price-source-cache")
CACHE_TTL = 6 * 3600  # 6 hours

logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("price-verify")


def parse_price_mln(raw: str) -> float | None:
    """Parse price string like '6.1М', '6,1 млн', '11 000 000' → float millions."""
    raw = raw.strip().replace("\xa0", "").replace(" ", "")
    # Explicit М/млн/млрд suffix
    m = re.match(r"([0-9]+[.,][0-9]+|[0-9]+)\s*[Мм](?:лн)?$", raw)
    if m:
        return float(m.group(1).replace(",", "."))
    # Raw number (rubles): 10_000_000 → 10M
    m = re.match(r"^([0-9]{7,10})$", raw.replace("_", ""))
    if m:
        return float(m.group(1)) / 1_000_000
    return None


def fetch_cached(url: str) -> str:
    """Fetch URL content with 6-hour file cache."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = hashlib.md5(url.encode()).hexdigest()
    cache_file = CACHE_DIR / f"{key}.txt"

    if cache_file.exists():
        age = time.time() - cache_file.stat().st_mtime
        if age < CACHE_TTL:
            return cache_file.read_text(encoding="utf-8", errors="replace")

    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; artvision-hallucination-hook/1.0)",
                "Accept": "text/html,*/*",
            },
        )
        with urllib.request.urlopen(req, timeout=12) as r:
            content = r.read(500_000).decode("utf-8", errors="replace")
        cache_file.write_text(content, encoding="utf-8")
        return content
    except Exception as exc:
        log.warning("Fetch error for %s: %s", url, exc)
        return ""


def extract_prices_from_page(html: str) -> list[float]:
    """Extract all prices in millions from a web page."""
    results = []
    # М/млн variants
    for m in re.finditer(r"([0-9]+[.,][0-9]+|[0-9]+)\s*[Мм](?:лн)?\b", html):
        val = parse_price_mln(m.group(0))
        if val and 0.5 <= val <= 200:  # reasonable real estate range
            results.append(val)
    # Raw 7-10 digit numbers (rubles)
    for m in re.finditer(r"\b([0-9]{7,10})\b", html.replace("\xa0", "").replace(" ", "")):
        val = float(m.group(1)) / 1_000_000
        if 0.5 <= val <= 200:
            results.append(val)
    return results


def find_price_url_pairs(html: str) -> list[dict]:
    """
    Find (price, url) pairs in HTML where price and URL appear within 400 chars.
    Returns list of {price_mln, url, context}.
    """
    pairs = []

    # Pattern: price near URL in radius ~400 chars
    # Find all prices
    price_matches = list(re.finditer(
        r"([0-9]+[.,][0-9]+|[0-9]{4,10})\s*[Мм](?:лн)?",
        html
    ))
    # Find all http URLs
    url_matches = list(re.finditer(r"https?://[^\s\"'<>]{10,200}", html))

    for pm in price_matches:
        price_val = parse_price_mln(pm.group(0))
        if price_val is None or not (0.5 <= price_val <= 100):
            continue

        # Look for nearby URL within 400 chars
        for um in url_matches:
            dist = abs(pm.start() - um.start())
            if dist < 400:
                # Skip CDN/static URLs
                url = um.group(0)
                if re.search(r"\.(css|js|png|jpg|jpeg|svg|gif|woff|ico|ttf)(\?|$)", url):
                    continue
                if re.search(r"/(static|assets|media|cdn|upload|img|image)/", url):
                    continue
                context = html[max(0, min(pm.start(), um.start()) - 50):
                               min(len(html), max(pm.end(), um.end()) + 50)]
                pairs.append({
                    "price_mln": price_val,
                    "url": url,
                    "context": context,
                })
                break  # one URL per price is enough

    return pairs


def check_price_on_page(claimed_price: float, url: str) -> tuple[str, float | None]:
    """
    Fetch URL and check if claimed_price exists on page.
    Returns (status, closest_price_found).
    status: 'ok' | 'warn' | 'critical' | 'skip'
    """
    content = fetch_cached(url)
    if not content:
        return "skip", None

    # Check for "цена по запросу" / "уточняйте цену"
    if re.search(r"цена\s+по\s+запросу|уточн[яи]йте\s+цену|цену\s+уточн", content, re.IGNORECASE):
        return "warn", None

    page_prices = extract_prices_from_page(content)
    if not page_prices:
        return "skip", None

    # Find closest price to claimed
    closest = min(page_prices, key=lambda p: abs(p - claimed_price))
    ratio = abs(claimed_price - closest) / closest if closest else 1.0

    if ratio > 0.50:
        return "critical", closest
    elif ratio > 0.15:
        return "warn", closest
    return "ok", closest


def extract_html_path(command: str) -> str | None:
    m = re.search(r"(\S+\.html)", command)
    return m.group(1) if m else None


def main() -> int:
    if os.environ.get("PRICE_VERIFY_SKIP") == "1":
        print("[price-verify] SKIP via PRICE_VERIFY_SKIP=1", file=sys.stderr)
        return 0

    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return 0

    command = data.get("tool_input", {}).get("command", "")

    if not re.search(r"\bscp\b", command):
        return 0
    if ".html" not in command:
        return 0

    html_path = extract_html_path(command)
    if not html_path or not os.path.isfile(html_path):
        return 0

    log.info("Checking prices in %s", html_path)

    try:
        with open(html_path, encoding="utf-8", errors="replace") as f:
            html = f.read()
    except OSError:
        return 0

    pairs = find_price_url_pairs(html)
    if not pairs:
        log.info("No price+url pairs found — PASS")
        return 0

    # Deduplicate by URL
    seen_urls: set[str] = set()
    unique_pairs = []
    for p in pairs:
        if p["url"] not in seen_urls:
            seen_urls.add(p["url"])
            unique_pairs.append(p)

    criticals = []
    warnings = []

    for pair in unique_pairs[:10]:  # max 10 checks per deploy
        price = pair["price_mln"]
        url = pair["url"]
        status, found = check_price_on_page(price, url)
        log.info("price=%.2fM url=%s status=%s found=%s", price, url, status, found)

        if status == "critical":
            criticals.append(
                f"CRITICAL: цена {price:.1f}М в HTML, на странице {found:.1f}М ({url[:80]})"
            )
        elif status == "warn":
            if found:
                warnings.append(
                    f"WARN: цена {price:.1f}М в HTML, на странице {found:.1f}М ({url[:80]})"
                )
            else:
                warnings.append(
                    f"WARN: цена {price:.1f}М в HTML, источник говорит «цена по запросу» ({url[:80]})"
                )

    if criticals:
        print("\n[pre-deploy-price-vs-source] BLOCKED — расхождение цен >50%:", file=sys.stderr)
        for msg in criticals:
            print(f"  {msg}", file=sys.stderr)
        for msg in warnings:
            print(f"  {msg}", file=sys.stderr)
        print("\nИсправь цены или: PRICE_VERIFY_SKIP=1", file=sys.stderr)
        log.error("BLOCK: %d critical price errors", len(criticals))
        return 2

    if warnings:
        print("\n[pre-deploy-price-vs-source] WARN — подозрительные цены:", file=sys.stderr)
        for msg in warnings:
            print(f"  {msg}", file=sys.stderr)
        print("Проверь вручную или: PRICE_VERIFY_SKIP=1", file=sys.stderr)
        log.warning("WARN: %d price warnings", len(warnings))
        return 1

    log.info("PASS: prices OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
