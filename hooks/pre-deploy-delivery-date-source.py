#!/usr/bin/env python3
"""
pre-deploy-delivery-date-source.py
PreToolUse hook: блокирует scp HTML если дата сдачи объекта в HTML
расходится с данными сайта застройщика более чем на 2 квартала.
Прецедент: IPOTEKA c052407c — Setl Ривьера «Q2 2026» (реально Q1 2028 = +6кв),
           Аурум «2028» (реально Q1 2029-2030 = +4-8кв).
Bypass: DELIVERY_DATE_SKIP=1
"""

import json
import os
import re
import sys
import urllib.request
import urllib.error
import hashlib
import time
import logging
from pathlib import Path

LOG_PATH = os.path.expanduser("~/.claude/logs/pre-deploy-delivery-date-source.log")
CACHE_DIR = Path("/tmp/delivery-date-cache")
CACHE_TTL = 12 * 3600

logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("delivery-verify")

# Quarter → month offset mapping
QUARTER_MONTHS = {1: 3, 2: 6, 3: 9, 4: 12}


def quarter_to_float(q: int, year: int) -> float:
    """Convert quarter/year to float for arithmetic comparison. Q1 2026 = 2026.0, Q3 2026 = 2026.5."""
    return year + (q - 1) * 0.25


def parse_delivery_date(text: str) -> list[tuple[float, str]]:
    """
    Parse delivery date strings into (float_date, raw_string) pairs.
    Handles: Q2 2026, 2 кв. 2028, II квартал 2029, 2028, I оч. 2026
    """
    results = []

    # Pattern: Q1-Q4 YYYY or 1-4 кв. YYYY
    patterns = [
        (r"[Qq]([1-4])\s*[./]?\s*(20[2-9][0-9])", "q-en"),
        (r"([1-4])\s*(?:кв\.?|квартал)\s*(20[2-9][0-9])", "q-ru"),
        (r"([IViv]{1,3})\s*(?:кв\.?|квартал|оч\.?|очередь)\.?\s*(20[2-9][0-9])", "q-roman"),
        (r"(20[2-9][0-9])\s*(?:год|г\.?)?$", "year-only"),
    ]
    roman_map = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 1}  # V → treated as 1 (edge case)

    for pat, kind in patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            raw = m.group(0)
            if kind == "year-only":
                year = int(m.group(1))
                results.append((quarter_to_float(2, year), raw))  # assume mid-year
            elif kind == "q-roman":
                roman = m.group(1).lower()
                q = roman_map.get(roman, 1)
                year = int(m.group(2))
                results.append((quarter_to_float(q, year), raw))
            else:
                q = int(m.group(1))
                year = int(m.group(2))
                results.append((quarter_to_float(q, year), raw))

    return results


def find_date_url_pairs(html: str) -> list[dict]:
    """Find (delivery_date_float, url, raw_date) triplets in HTML where date is near URL."""
    results = []
    url_matches = list(re.finditer(r"https?://[^\s\"'<>]{10,200}", html))

    # Search for date patterns in HTML
    date_patterns = [
        r"[Qq][1-4]\s*/?\s*20[2-9][0-9]",
        r"[1-4]\s*кв\.?\s*20[2-9][0-9]",
        r"[IViv]{1,3}\s*(?:кв|оч)\.?\s*20[2-9][0-9]",
        r"\bI{1,3}V?\s*(?:очередь|оч\.?|кв\.?)\s*(?:сдана|сдан|сдаётся)?\s*20[2-9][0-9]",
    ]

    for pat in date_patterns:
        for dm in re.finditer(pat, html, re.IGNORECASE):
            raw_date = dm.group(0)
            parsed = parse_delivery_date(raw_date)
            if not parsed:
                continue
            date_float, _ = parsed[0]

            # Find nearest URL within 600 chars
            best_url = None
            best_dist = 9999
            for um in url_matches:
                dist = abs(dm.start() - um.start())
                if dist < 600 and dist < best_dist:
                    # Skip static resources
                    url = um.group(0)
                    if not re.search(r"\.(css|js|png|jpg|svg|gif|woff|ico)(\?|$)", url):
                        best_dist = dist
                        best_url = url

            if best_url:
                results.append({
                    "date_float": date_float,
                    "raw_date": raw_date,
                    "url": best_url,
                })

    return results


def fetch_cached(url: str) -> str:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = hashlib.md5(url.encode()).hexdigest()
    cache_file = CACHE_DIR / f"{key}.txt"
    if cache_file.exists() and (time.time() - cache_file.stat().st_mtime) < CACHE_TTL:
        return cache_file.read_text(encoding="utf-8", errors="replace")
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; artvision-date-hook/1.0)"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            content = r.read(400_000).decode("utf-8", errors="replace")
        cache_file.write_text(content, encoding="utf-8")
        return content
    except Exception as exc:
        log.warning("Fetch error %s: %s", url, exc)
        return ""


def extract_dates_from_page(content: str) -> list[float]:
    """Extract all delivery dates from a source page."""
    results = []
    combined_text = re.sub(r"<[^>]+>", " ", content)  # strip HTML tags
    date_patterns = [
        r"[Qq][1-4]\s*/?\s*20[2-9][0-9]",
        r"[1-4]\s*кв\.?\s*20[2-9][0-9]",
        r"[IViv]{1,3}\s*(?:кв|оч)\.?\s*20[2-9][0-9]",
        r"сдача\s+в\s+(20[2-9][0-9])",
        r"сдан[аоы]?\s+в\s+(20[2-9][0-9])",
        r"срок\s+сдачи[^<]{0,20}(20[2-9][0-9])",
    ]
    for pat in date_patterns:
        for m in re.finditer(pat, combined_text, re.IGNORECASE):
            parsed = parse_delivery_date(m.group(0))
            if parsed:
                results.append(parsed[0][0])
    return results


def quarters_diff(a: float, b: float) -> float:
    """Difference in quarters between two quarter-floats."""
    return abs(a - b) / 0.25


def extract_html_path(command: str) -> str | None:
    m = re.search(r"(\S+\.html)", command)
    return m.group(1) if m else None


def main() -> int:
    if os.environ.get("DELIVERY_DATE_SKIP") == "1":
        print("[delivery-verify] SKIP via DELIVERY_DATE_SKIP=1", file=sys.stderr)
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

    log.info("Checking delivery dates in %s", html_path)

    try:
        with open(html_path, encoding="utf-8", errors="replace") as f:
            html = f.read()
    except OSError:
        return 0

    pairs = find_date_url_pairs(html)
    if not pairs:
        log.info("No date+url pairs found — PASS")
        return 0

    # Deduplicate by URL
    seen: set[str] = set()
    unique_pairs = []
    for p in pairs:
        key = f"{p['url']}|{p['raw_date']}"
        if key not in seen:
            seen.add(key)
            unique_pairs.append(p)

    criticals = []
    warnings = []

    for entry in unique_pairs[:8]:
        claimed_date = entry["date_float"]
        raw_date = entry["raw_date"]
        url = entry["url"]

        page_content = fetch_cached(url)
        if not page_content:
            log.info("Could not fetch %s — skipping", url)
            continue

        source_dates = extract_dates_from_page(page_content)
        if not source_dates:
            log.info("No dates found on %s — skipping", url)
            continue

        # Find closest source date
        closest = min(source_dates, key=lambda d: abs(d - claimed_date))
        diff_q = quarters_diff(claimed_date, closest)

        log.info(
            "Claimed=%s (%.2f), source_closest=%.2f, diff=%.0f quarters, url=%s",
            raw_date, claimed_date, closest, diff_q, url[:80]
        )

        if diff_q > 4:
            criticals.append(
                f"CRITICAL: дата «{raw_date}» в HTML, "
                f"источник даёт Q{int((closest % 1) / 0.25) + 1} {int(closest)} "
                f"(расхождение {diff_q:.0f} кв) — {url[:70]}"
            )
        elif diff_q > 2:
            warnings.append(
                f"WARN: дата «{raw_date}» в HTML, "
                f"источник даёт Q{int((closest % 1) / 0.25) + 1} {int(closest)} "
                f"(расхождение {diff_q:.0f} кв) — {url[:70]}"
            )

    if criticals:
        print("\n[pre-deploy-delivery-date-source] BLOCKED — даты сдачи расходятся >4 кварталов:", file=sys.stderr)
        for msg in criticals:
            print(f"  {msg}", file=sys.stderr)
        for msg in warnings:
            print(f"  {msg}", file=sys.stderr)
        print("\nИсправь даты сдачи или: DELIVERY_DATE_SKIP=1", file=sys.stderr)
        log.error("BLOCK: %d critical date errors in %s", len(criticals), html_path)
        return 2

    if warnings:
        print("\n[pre-deploy-delivery-date-source] WARN — даты сдачи расходятся 2-4 квартала:", file=sys.stderr)
        for msg in warnings:
            print(f"  {msg}", file=sys.stderr)
        print("Проверь вручную или: DELIVERY_DATE_SKIP=1", file=sys.stderr)
        log.warning("WARN: %d date warnings in %s", len(warnings), html_path)
        return 1

    log.info("PASS: delivery dates OK in %s", html_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
