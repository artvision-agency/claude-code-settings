#!/usr/bin/env python3
"""
orm-pulse: Playwright парс целевой площадки клиента.
Read-only. Прокручивает ленту до указанного периода, извлекает все отзывы.

Usage: playwright-reviews.py <client_slug> [--since YYYY-MM-DD] [--limit 1000]

Output: /tmp/orm-pulse/<slug>/reviews/
  - in_range.json    — все отзывы за период (date / author / rating / text / id)
  - raw_extract.json — все собранные отзывы (без фильтрации)
  - last_*.png       — скриншоты для аудита
"""
import sys
import json
import asyncio
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

import yaml

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("❌ pip3 install playwright && playwright install chromium", file=sys.stderr)
    sys.exit(1)


def load_registry(slug: str) -> dict:
    return yaml.safe_load((Path.home() / "artvision-data" / "clients" / slug / "orm" / "registry.yaml").read_text())


def parse_date_ru(s: str) -> str | None:
    """'1 мая' → 'YYYY-MM-DD' (год = текущий, поправка для 'месяцев назад')."""
    if not s:
        return None
    months = {
        "янв": "01", "фев": "02", "мар": "03", "апр": "04", "ма": "05",
        "июн": "06", "июл": "07", "авг": "08", "сен": "09", "окт": "10",
        "ноя": "11", "дек": "12",
    }
    parts = s.lower().strip().split()
    today = datetime.now()
    year = today.year

    if len(parts) >= 2 and parts[0].isdigit():
        day = parts[0].zfill(2)
        m_key = next((k for k in months if parts[1].startswith(k)), None)
        if not m_key:
            return None
        return f"{year}-{months[m_key]}-{day}"

    if "вчера" in s.lower():
        return (today.replace(day=today.day - 1)).strftime("%Y-%m-%d")
    if "сегодня" in s.lower():
        return today.strftime("%Y-%m-%d")

    return None


async def quit_chrome():
    """Кvit Chrome чтобы освободить персистент-профиль."""
    try:
        subprocess.run(["osascript", "-e", 'tell application "Google Chrome" to quit'],
                       check=False, capture_output=True, timeout=5)
        await asyncio.sleep(1)
    except Exception:
        pass


async def extract_reviews(page, max_iter=40):
    """Собирает все отзывы со страницы reviews.yandex.ru с прокруткой."""
    seen = set()
    all_items = []
    last_count = 0
    stale_iter = 0

    for i in range(max_iter):
        # JS-extract
        items = await page.evaluate("""() => {
            const reviews = [];
            const cards = document.querySelectorAll('[class*="review"], [data-zone-name*="review"]');
            cards.forEach(c => {
                const author = c.querySelector('[class*="author"], [class*="name"]')?.textContent?.trim() || '';
                const date = c.querySelector('[class*="date"]')?.textContent?.trim() || '';
                const text = c.querySelector('[class*="text"], [class*="body"]')?.textContent?.trim() || '';
                const ratingEl = c.querySelector('[class*="rating"], [class*="stars"]');
                const rating = ratingEl?.getAttribute('aria-label') || ratingEl?.textContent?.trim() || '';
                const id = c.getAttribute('data-review-id') || c.getAttribute('data-id') || c.id || '';
                if (author && (text || date)) {
                    reviews.push({author, date, text: text.slice(0, 500), rating, id});
                }
            });
            return reviews;
        }""")

        for it in items:
            key = (it.get("author", ""), it.get("date", ""), it.get("text", "")[:80])
            if key in seen:
                continue
            seen.add(key)
            all_items.append(it)

        # Прокрутка
        await page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
        await asyncio.sleep(1.5)

        if len(all_items) == last_count:
            stale_iter += 1
            if stale_iter >= 3:
                break
        else:
            stale_iter = 0
            last_count = len(all_items)

    return all_items


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("slug")
    parser.add_argument("--since", default=None, help="YYYY-MM-DD")
    parser.add_argument("--limit", type=int, default=1000)
    args = parser.parse_args()

    registry = load_registry(args.slug)
    url = registry["platform"]["url"]

    out_dir = Path("/tmp/orm-pulse") / args.slug / "reviews"
    out_dir.mkdir(parents=True, exist_ok=True)

    profile_dir = Path(f"/tmp/orm-pulse-pw-{args.slug}")

    await quit_chrome()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=True,
            viewport={"width": 1280, "height": 1600},
        )
        page = await browser.new_page()

        print(f"→ Open {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)

        # Скриншот для аудита
        await page.screenshot(path=str(out_dir / "00_initial.png"))

        # Извлечение
        all_items = await extract_reviews(page)

        # Метаданные
        meta = await page.evaluate("""() => {
            const ratingEl = document.querySelector('[class*="rating-value"], [class*="averageRating"]');
            const totalEl = document.querySelector('[class*="total"], [class*="count"]');
            return {
                rating: ratingEl?.textContent?.trim() || '',
                total_text: totalEl?.textContent?.trim() || '',
                title: document.title,
            };
        }""")

        await browser.close()

    # Парсинг дат + фильтр period
    for it in all_items:
        it["date_iso"] = parse_date_ru(it.get("date", ""))

    in_range = [it for it in all_items if it.get("date_iso")]
    if args.since:
        since = args.since
        in_range = [it for it in in_range if (it.get("date_iso") or "") >= since]

    # Save
    (out_dir / "raw_extract.json").write_text(json.dumps(all_items, ensure_ascii=False, indent=2))
    (out_dir / "in_range.json").write_text(json.dumps(in_range, ensure_ascii=False, indent=2))
    (out_dir / "_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))

    print(f"\n✅ Total extracted: {len(all_items)}")
    print(f"✅ With parsed date: {len([x for x in all_items if x.get('date_iso')])}")
    print(f"✅ In range (since {args.since or 'all'}): {len(in_range)}")
    print(f"\nMeta: {meta}")
    print(f"Saved to: {out_dir}")


if __name__ == "__main__":
    asyncio.run(main())
