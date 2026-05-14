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

sys.path.insert(0, str(Path(__file__).parent))
from lib.config import ROOT  # noqa: E402


def load_registry(slug: str) -> dict:
    return yaml.safe_load((ROOT / "clients" / slug / "orm" / "registry.yaml").read_text())


def parse_date_ru(s: str) -> str | None:
    """'1 мая' / 'вчера' / '2 недели назад' → 'YYYY-MM-DD'."""
    if not s:
        return None
    s_low = s.lower().strip()
    today = datetime.now()
    from datetime import timedelta

    months = {
        "янв": "01", "фев": "02", "март": "03", "мар": "03", "апр": "04",
        "ма": "05", "май": "05",
        "июн": "06", "июл": "07", "авг": "08", "сен": "09", "окт": "10",
        "ноя": "11", "дек": "12",
    }
    parts = s_low.split()

    # "N <месяц>"
    if len(parts) >= 2 and parts[0].isdigit():
        day = parts[0].zfill(2)
        m_key = next((k for k in months if parts[1].startswith(k)), None)
        if m_key:
            year = today.year
            month = int(months[m_key])
            # если месяц больше текущего → отзыв за прошлый год
            if month > today.month:
                year -= 1
            return f"{year}-{months[m_key]}-{day}"

    if "вчера" in s_low:
        return (today - timedelta(days=1)).strftime("%Y-%m-%d")
    if "сегодня" in s_low:
        return today.strftime("%Y-%m-%d")
    if "позавчера" in s_low:
        return (today - timedelta(days=2)).strftime("%Y-%m-%d")

    # "N дн[яей] назад"
    import re
    m = re.match(r"(\d+)\s*(дн|сут)", s_low)
    if m:
        return (today - timedelta(days=int(m.group(1)))).strftime("%Y-%m-%d")
    # "N недел" — приблизительно
    m = re.match(r"(\d+)\s*недел", s_low)
    if m:
        return (today - timedelta(weeks=int(m.group(1)))).strftime("%Y-%m-%d")
    if s_low.startswith("неделю назад"):
        return (today - timedelta(weeks=1)).strftime("%Y-%m-%d")
    # "N месяц[ев] назад" — первый день N месяцев назад
    m = re.match(r"(\d+)\s*месяц", s_low)
    if m:
        n = int(m.group(1))
        y = today.year
        mo = today.month - n
        while mo <= 0:
            mo += 12
            y -= 1
        return f"{y}-{mo:02d}-01"

    return None


async def quit_chrome():
    """Кvit Chrome чтобы освободить персистент-профиль."""
    try:
        subprocess.run(["osascript", "-e", 'tell application "Google Chrome" to quit'],
                       check=False, capture_output=True, timeout=5)
        await asyncio.sleep(1)
    except Exception:
        pass


async def extract_reviews(page, max_iter=80):
    """Собирает все отзывы со страницы reviews.yandex.ru с прокруткой.

    DOM (2026-05): li.Review, .ReviewAuthor-Name, .Review-Rating[aria-label="оценка X из 5"],
                    .Review-Date, .Review-Text .TextCut, a.ReviewAuthor-Link[href=/user/<id>...]
    """
    seen = set()
    all_items: list[dict] = []
    last_count = 0
    stale_iter = 0

    for i in range(max_iter):
        items = await page.evaluate(r"""() => {
            const out = [];
            const cards = document.querySelectorAll('li.Review');
            cards.forEach(c => {
                // Автор
                const author = c.querySelector('.ReviewAuthor-Name')?.textContent?.trim() || '';

                // Рейтинг — из aria-label "оценка 5 из 5"
                const ratingEl = c.querySelector('.Review-Rating[aria-label]');
                const aria = ratingEl?.getAttribute('aria-label') || '';
                const m = aria.match(/(\d)\s*из\s*5/);
                const rating = m ? parseInt(m[1], 10) : null;

                // Дата
                const date = c.querySelector('.Review-Date')?.textContent?.trim() || '';

                // Текст
                const text = (c.querySelector('.Review-Text .TextCut, .Review-Text')?.textContent || '').trim();

                // user_id из href ReviewAuthor-Link
                const userHref = c.querySelector('a.ReviewAuthor-Link')?.getAttribute('href') || '';
                const uMatch = userHref.match(/\/user\/([a-z0-9]+)/i);
                const user_id = uMatch ? uMatch[1] : '';

                // log_node — для трекинга. Берём с любого data-log-node вложенного
                const logNodeEl = c.querySelector('[data-log-node]');
                const log_node = logNodeEl?.getAttribute('data-log-node') || '';

                if (author && rating !== null) {
                    out.push({
                        author, rating, date,
                        text: text.slice(0, 600),
                        user_id, log_node,
                    });
                }
            });
            return out;
        }""")

        for it in items:
            key = (it.get("author", ""), it.get("date", ""), it.get("text", "")[:80])
            if key in seen:
                continue
            seen.add(key)
            all_items.append(it)

        # Прокрутка вниз
        await page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
        await asyncio.sleep(1.5)

        if len(all_items) == last_count:
            stale_iter += 1
            if stale_iter >= 4:
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

        # Метаданные карточки магазина
        meta = await page.evaluate(r"""() => {
            // На странице есть блок с общей оценкой 3.0 + "3 264 оценки" + "3 088 отзывов"
            const txt = document.body.innerText || '';
            const ratingNum = (txt.match(/^(\d[.,]\d)\s*\n/m) || [])[1] || '';
            const ratingsCnt = (txt.match(/(\d[\d\s]*)\s*оцен/i) || [])[1]?.replace(/\s/g, '') || '';
            const reviewsCnt = (txt.match(/(\d[\d\s]*)\s*отзыв/i) || [])[1]?.replace(/\s/g, '') || '';
            return {
                rating: ratingNum,
                ratings_count: ratingsCnt,
                reviews_count: reviewsCnt,
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
