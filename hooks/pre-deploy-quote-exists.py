#!/usr/bin/env python3
"""
pre-deploy-quote-exists.py
PreToolUse hook: блокирует Write/Edit HTML если цитаты в «кавычках» не найдены на источнике.
Прецедент: IPOTEKA c052407c — «средства заморозить на 3 года» приписано дольщикам Аурума,
           в отзывах spbguru.ru НЕ найдено — выдумано.
Bypass: QUOTE_VERIFY_SKIP=1
"""

import difflib
import json
import os
import re
import sys
import urllib.request
import urllib.error
import logging
from pathlib import Path
import hashlib
import time

LOG_PATH = os.path.expanduser("~/.claude/logs/pre-deploy-quote-exists.log")
CACHE_DIR = Path("/tmp/quote-source-cache")
CACHE_TTL = 4 * 3600

logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("quote-verify")

# Minimum quote length to bother checking (short phrases are too generic)
MIN_QUOTE_LEN = 15
# Fuzzy similarity threshold to consider quote "found"
FUZZY_THRESHOLD = 0.75
# Max WARN before blocking
MAX_WARNS_BEFORE_BLOCK = 3


def fetch_cached(url: str) -> str:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = hashlib.md5(url.encode()).hexdigest()
    cache_file = CACHE_DIR / f"{key}.txt"
    if cache_file.exists() and (time.time() - cache_file.stat().st_mtime) < CACHE_TTL:
        return cache_file.read_text(encoding="utf-8", errors="replace")
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; artvision-quote-hook/1.0)"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            content = r.read(300_000).decode("utf-8", errors="replace")
        cache_file.write_text(content, encoding="utf-8")
        return content
    except Exception as exc:
        log.warning("Fetch error %s: %s", url, exc)
        return ""


def strip_tags(html: str) -> str:
    """Strip HTML tags for text comparison."""
    return re.sub(r"<[^>]+>", " ", html)


def find_quotes_with_sources(html: str) -> list[dict]:
    """
    Find Russian curly-quote strings «...» or <i>...</i> / <blockquote>...</blockquote>
    near a URL source within ±300 chars.
    Returns list of {quote, url, source}.
    """
    results = []
    # Collect all URLs in document
    url_matches = list(re.finditer(r"https?://[^\s\"'<>]{10,200}", html))

    # Pattern 1: «кавычки»
    for m in re.finditer(r"«([^»]{15,300})»", html):
        quote = m.group(1).strip()
        if len(quote) < MIN_QUOTE_LEN:
            continue
        # Find nearest URL within 300 chars
        best_url = None
        best_dist = 9999
        for um in url_matches:
            dist = abs(m.start() - um.start())
            if dist < 300 and dist < best_dist:
                best_dist = dist
                best_url = um.group(0)
        if best_url:
            results.append({"quote": quote, "url": best_url, "source": "guillemets"})

    # Pattern 2: <i>текст</i> near URL
    for m in re.finditer(r"<i>([^<]{15,300})</i>", html, re.DOTALL):
        quote = m.group(1).strip()
        if len(quote) < MIN_QUOTE_LEN or re.search(r"<|>", quote):
            continue
        best_url = None
        best_dist = 9999
        for um in url_matches:
            dist = abs(m.start() - um.start())
            if dist < 300 and dist < best_dist:
                best_dist = dist
                best_url = um.group(0)
        if best_url:
            results.append({"quote": quote, "url": best_url, "source": "italic"})

    # Pattern 3: data-quote="..." attribute
    for m in re.finditer(r'data-quote=["\']([^"\']{15,300})["\']', html):
        quote = m.group(1).strip()
        best_url = None
        best_dist = 9999
        for um in url_matches:
            dist = abs(m.start() - um.start())
            if dist < 500 and dist < best_dist:
                best_dist = dist
                best_url = um.group(0)
        if best_url:
            results.append({"quote": quote, "url": best_url, "source": "data-quote"})

    return results


def quote_found_on_page(quote: str, page_content: str) -> bool:
    """Check if quote text appears on page (exact substring or fuzzy 75%+)."""
    clean_page = strip_tags(page_content).lower()
    clean_quote = quote.lower()

    # Exact substring
    if clean_quote in clean_page:
        return True

    # Fuzzy match using SequenceMatcher sliding window
    # Split page into chunks roughly quote-length
    chunk_size = len(clean_quote) + 50
    for i in range(0, len(clean_page) - chunk_size, chunk_size // 3):
        chunk = clean_page[i: i + chunk_size]
        ratio = difflib.SequenceMatcher(None, clean_quote, chunk).ratio()
        if ratio >= FUZZY_THRESHOLD:
            return True

    return False


def get_html_path_from_stdin(data: dict) -> str | None:
    """Extract file_path from Write/Edit tool input."""
    ti = data.get("tool_input", {})
    return ti.get("file_path") or ti.get("path")


def is_target_file(path: str) -> bool:
    """Only check HTML files under client/personal/presale/product folders."""
    if not path.endswith(".html"):
        return False
    return bool(re.search(r"/(clients|presales|personal|products)/", path))


def main() -> int:
    if os.environ.get("QUOTE_VERIFY_SKIP") == "1":
        print("[quote-verify] SKIP via QUOTE_VERIFY_SKIP=1", file=sys.stderr)
        return 0

    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return 0

    tool_name = data.get("tool_name", "")
    if tool_name not in ("Write", "Edit"):
        return 0

    file_path = get_html_path_from_stdin(data)
    if not file_path or not is_target_file(file_path):
        return 0

    # For Write: content is in tool_input.content
    # For Edit: file might already exist, check new_string
    ti = data.get("tool_input", {})
    html = ti.get("content") or ti.get("new_string") or ""
    if not html:
        # Try reading from disk if Edit
        if os.path.isfile(file_path):
            try:
                with open(file_path, encoding="utf-8", errors="replace") as f:
                    html = f.read()
            except OSError:
                return 0

    if not html:
        return 0

    log.info("Checking quotes in %s", file_path)
    quote_pairs = find_quotes_with_sources(html)

    if not quote_pairs:
        log.info("No quote+url pairs found — PASS")
        return 0

    warns = []
    for entry in quote_pairs[:15]:
        quote = entry["quote"]
        url = entry["url"]

        # Skip CDN/static URLs
        if re.search(r"\.(css|js|png|jpg|svg|gif|woff|ico)(\?|$)", url):
            continue

        page_content = fetch_cached(url)
        if not page_content:
            log.info("Could not fetch %s — skipping quote check", url)
            continue

        found = quote_found_on_page(quote, page_content)
        log.info("quote=%r url=%s found=%s", quote[:50], url[:80], found)

        if not found:
            warns.append(
                f"WARN: цитата «{quote[:80]}...» НЕ найдена на {url[:80]}"
            )

    if len(warns) >= MAX_WARNS_BEFORE_BLOCK:
        print(f"\n[pre-deploy-quote-exists] BLOCKED — {len(warns)} цитат не подтверждены:", file=sys.stderr)
        for msg in warns:
            print(f"  {msg}", file=sys.stderr)
        print(f"\nМинимум {MAX_WARNS_BEFORE_BLOCK} цитат выдуманы. Исправь или: QUOTE_VERIFY_SKIP=1", file=sys.stderr)
        log.error("BLOCK: %d unverified quotes in %s", len(warns), file_path)
        return 2

    if warns:
        print(f"\n[pre-deploy-quote-exists] WARN — {len(warns)} цитат не найдено на источниках:", file=sys.stderr)
        for msg in warns:
            print(f"  {msg}", file=sys.stderr)
        print("Проверь вручную или: QUOTE_VERIFY_SKIP=1", file=sys.stderr)
        log.warning("WARN: %d unverified quotes in %s", len(warns), file_path)
        return 1

    log.info("PASS: all quotes verified in %s", file_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
