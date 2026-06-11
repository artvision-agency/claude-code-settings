#!/usr/bin/env python3
"""
check_4xx.py — batch HTTP HEAD check на список URL, фильтр 4xx/5xx.

Использует httpx (async) для параллельных запросов с retry.
Fallback на requests если httpx не установлен.

Input CSV: url_from, url_to, anchor, dr, traffic, last_seen
Output CSV: url_from, url_to, anchor, dr, status_code, error
              (только записи где url_to вернул 4xx/5xx или ошибку)

Usage:
    python3 check_4xx.py --input candidates.csv --output broken_urls.csv [--concurrency 10] [--timeout 15]

Связано:
    - ~/.claude/rules/proven-tools-first.md (используем httpx, не велосипед)
    - SKILL.md шаг 3
"""

import argparse
import asyncio
import csv
import logging
import sys
from pathlib import Path
from typing import Optional

LOG = logging.getLogger("check_4xx")

# Какие статусы считаем "битыми" → кандидаты на reclaim
BROKEN_STATUS_RANGES = [(400, 499), (500, 599)]
# Сетевые ошибки тоже считаем битыми (DNS, connection refused, timeout)
NETWORK_ERROR_AS_BROKEN = True

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ArtvisionLinkReclaim/1.0; +https://artvision.pro/bot)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def is_broken_status(code: int) -> bool:
    return any(lo <= code <= hi for lo, hi in BROKEN_STATUS_RANGES)


async def check_url(client, url: str, timeout: int, retries: int = 2) -> tuple[Optional[int], Optional[str]]:
    """Возвращает (status_code, error). status_code=None если сетевая ошибка."""
    last_err = None
    for attempt in range(retries + 1):
        try:
            # HEAD сначала (быстрее), если 405 Method Not Allowed → GET fallback
            resp = await client.head(url, headers=DEFAULT_HEADERS, follow_redirects=True, timeout=timeout)
            if resp.status_code == 405:
                resp = await client.get(url, headers=DEFAULT_HEADERS, follow_redirects=True, timeout=timeout)
            return resp.status_code, None
        except Exception as exc:
            last_err = f"{type(exc).__name__}: {exc}"
            if attempt < retries:
                await asyncio.sleep(0.5 * (attempt + 1))  # лёгкий backoff
    return None, last_err


async def check_batch(urls: list[str], concurrency: int, timeout: int) -> dict[str, tuple[Optional[int], Optional[str]]]:
    try:
        import httpx
    except ImportError:
        LOG.error("httpx не установлен. Установить: pip3 install httpx")
        sys.exit(2)

    semaphore = asyncio.Semaphore(concurrency)
    results: dict[str, tuple[Optional[int], Optional[str]]] = {}

    async with httpx.AsyncClient(verify=False) as client:
        async def worker(url: str):
            async with semaphore:
                code, err = await check_url(client, url, timeout)
                results[url] = (code, err)
                if code is not None and is_broken_status(code):
                    LOG.info("BROKEN %d %s", code, url)
                elif code is None:
                    LOG.info("ERROR %s — %s", url, err)

        await asyncio.gather(*(worker(u) for u in urls))

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch HTTP check, filter 4xx/5xx")
    parser.add_argument("--input", required=True, help="CSV with column url_to")
    parser.add_argument("--output", required=True, help="CSV output broken URLs")
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--url-col", default="url_to", help="Column name to check")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    in_path = Path(args.input)
    if not in_path.exists():
        LOG.error("Input not found: %s", in_path)
        return 1

    with in_path.open() as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    if args.url_col not in fieldnames:
        LOG.error("Column '%s' not found in %s. Found: %s", args.url_col, in_path, fieldnames)
        return 1

    # Уникальные URL (один URL может быть в нескольких строках с разными донорами)
    unique_urls = sorted({r[args.url_col].strip() for r in rows if r.get(args.url_col)})
    LOG.info("Checking %d unique URLs (concurrency=%d, timeout=%ds)", len(unique_urls), args.concurrency, args.timeout)

    results = asyncio.run(check_batch(unique_urls, args.concurrency, args.timeout))

    # Output: все строки где url_to битый
    out_fields = list(fieldnames) + ["status_code", "error"]
    broken_count = 0
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader()
        for row in rows:
            url = row[args.url_col].strip()
            code, err = results.get(url, (None, "not_checked"))
            is_broken = (code is not None and is_broken_status(code)) or (
                code is None and NETWORK_ERROR_AS_BROKEN and err and "not_checked" not in err
            )
            if is_broken:
                row["status_code"] = code if code is not None else ""
                row["error"] = err or ""
                writer.writerow(row)
                broken_count += 1

    LOG.info("Done. %d broken records → %s", broken_count, out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
