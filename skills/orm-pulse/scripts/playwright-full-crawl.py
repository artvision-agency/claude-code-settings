#!/usr/bin/env python3
"""playwright-full-crawl — полный crawl reviews.yandex.ru/shop/<domain>.

Стратегия: Playwright (Chromium persistent context), скроллит до конца ленты
ИЛИ до даты cutoff (--since YYYY-MM-DD). Извлекает данные через DOM-инспекцию.

Селекторы:
  - reviews.yandex.ru рендерит SSR + hydrate. Карточки имеют data-* attributes.
  - Текст: ищем все <p>/<span> с длиной >40 в области ленты
  - Автор: рядом с avatar или в начале карточки
  - Дата: relative ('месяц назад', '2 мая') — парсим в abs

Output:
  /tmp/orm-pulse/<slug>/full-crawl/<YYYY-MM-DD-HHMM>.json
  clients/<slug>/orm/live-reviews/<YYYY-MM-DD>.json (last)

Usage:
  playwright-full-crawl.py <slug> [--since YYYY-MM-DD] [--max-pages 200]
"""
from __future__ import annotations
import argparse
import asyncio
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import yaml

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("❌ pip3 install playwright && playwright install chromium", file=sys.stderr)
    sys.exit(1)

ROOT = Path("/Users/antonk/artvision-data")

MONTHS = {
    "янв": 1, "фев": 2, "мар": 3, "апр": 4, "ма": 5, "мая": 5,
    "июн": 6, "июл": 7, "авг": 8, "сен": 9, "окт": 10, "ноя": 11, "дек": 12,
}


def parse_relative_date(s: str, now: datetime | None = None) -> str | None:
    """'2 мая' / 'месяц назад' / '5 дней назад' / 'вчера' → 'YYYY-MM-DD'."""
    if not s:
        return None
    s = s.lower().strip()
    now = now or datetime.now()

    if "вчера" in s:
        return (now - timedelta(days=1)).strftime("%Y-%m-%d")
    if "сегодня" in s:
        return now.strftime("%Y-%m-%d")

    # "5 дней назад", "2 недели назад", "месяц назад", "3 месяца назад", "год назад"
    m = re.match(r"(\d+)?\s*(день|дн|недел|месяц|мес|год|лет)", s)
    if m:
        n = int(m.group(1) or 1)
        unit = m.group(2)
        if unit.startswith(("день", "дн")):
            return (now - timedelta(days=n)).strftime("%Y-%m-%d")
        if unit.startswith("недел"):
            return (now - timedelta(weeks=n)).strftime("%Y-%m-%d")
        if unit.startswith(("месяц", "мес")):
            return (now - timedelta(days=n * 30)).strftime("%Y-%m-%d")
        if unit.startswith(("год", "лет")):
            return (now - timedelta(days=n * 365)).strftime("%Y-%m-%d")

    # "2 мая 2026" или "2 мая" (без года → текущий)
    m = re.match(r"(\d{1,2})\s+([а-я]+)(?:\s+(\d{4}))?", s)
    if m:
        day = int(m.group(1))
        m_key = next((k for k in MONTHS if m.group(2).startswith(k)), None)
        if m_key:
            mon = MONTHS[m_key]
            year = int(m.group(3)) if m.group(3) else now.year
            try:
                return f"{year:04d}-{mon:02d}-{day:02d}"
            except Exception:
                return None
    return None


async def quit_chrome():
    try:
        subprocess.run(
            ["osascript", "-e", 'tell application "Google Chrome" to quit'],
            check=False, capture_output=True, timeout=5,
        )
        await asyncio.sleep(1)
    except Exception:
        pass


async def extract_all(page) -> list[dict]:
    """Экстрактор для reviews.yandex.ru/shop/<domain>.

    Селекторы (актуальны на 2026-05-08):
      .Review[role="listitem"] — карточка
      .ReviewAuthor-Name — автор
      .Review-Rating[aria-label="оценка N из 5"] — рейтинг
      .Review-Date — дата (relative: '6 мая', '2 месяца назад')
      .Review-Text — тело отзыва
      data-log-node — уникальный ID карточки
      href="/user/<id>" — id профиля автора
    """
    data = await page.evaluate(r"""() => {
        const cards = document.querySelectorAll('.Review[role="listitem"]');
        return Array.from(cards).map(c => {
            const author = c.querySelector('.ReviewAuthor-Name')?.textContent?.trim() || '';
            const ratingEl = c.querySelector('.Review-Rating');
            const ratingLabel = ratingEl?.getAttribute('aria-label') || '';
            const ratingMatch = ratingLabel.match(/(\d+)\s*из\s*\d+/);
            const rating = ratingMatch ? parseInt(ratingMatch[1], 10) : null;
            const date = c.querySelector('.Review-Date')?.textContent?.trim() || '';
            const text = (c.querySelector('.Review-Text')?.textContent || '').trim();
            const userLink = c.querySelector('.ReviewAuthor-Link')?.getAttribute('href') || '';
            const m = userLink.match(/\/user\/([a-z0-9]+)/);
            const userId = m ? m[1] : '';
            const logNode = c.getAttribute('data-log-node') || '';
            return {author, rating, date, text, user_id: userId, log_node: logNode};
        });
    }""")
    return data


async def crawl(slug: str, since: str | None, max_pages: int) -> dict:
    reg = yaml.safe_load((ROOT / "clients" / slug / "orm" / "registry.yaml").read_text())
    url = reg["platform"]["url"]

    out_dir = Path("/tmp/orm-pulse") / slug / "full-crawl"
    out_dir.mkdir(parents=True, exist_ok=True)

    profile_dir = Path(f"/tmp/orm-pulse-pw-{slug}")

    await quit_chrome()

    collected: list[dict] = []
    seen_keys: set[tuple[str, str, str]] = set()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=True,
            viewport={"width": 1280, "height": 1800},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        )
        page = await browser.new_page()

        print(f"→ Open {url}", flush=True)
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)

        # Скриншот для аудита
        await page.screenshot(path=str(out_dir / "00_initial.png"), full_page=False)

        # Цикл скроллинга + сбора + клика «Показать ещё» если есть
        stale = 0
        for page_iter in range(max_pages):
            items = await extract_all(page)
            new_n = 0
            for it in items:
                key = (it.get("author", ""), it.get("date", ""), it.get("text", "")[:80])
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                it["date_iso"] = parse_relative_date(it.get("date", ""))
                collected.append(it)
                new_n += 1

            # Scroll
            await page.evaluate("window.scrollBy(0, document.body.scrollHeight * 0.9)")
            # Try clicking "Показать ещё" buttons if any
            try:
                btn = page.get_by_role("button", name=re.compile(r"показать.*ещ|следующ|загрузить", re.I))
                if await btn.count() > 0:
                    await btn.first.click(timeout=2000)
            except Exception:
                pass

            await asyncio.sleep(1.5)

            # Прогресс
            print(f"  iter {page_iter+1:>3} · collected {len(collected):>4} · new this iter {new_n:>3}", flush=True)

            if new_n == 0:
                stale += 1
                if stale >= 5:
                    print(f"  → 5 итераций без новых, завершаем", flush=True)
                    break
            else:
                stale = 0

            # Cutoff: stop when ALL of last 50 collected items older than since
            # (yandex выводит relevance, не date — поэтому смотрим хвост окна)
            if since and len(collected) > 50:
                tail = collected[-50:]
                tail_with_date = [t["date_iso"] for t in tail if t.get("date_iso")]
                if tail_with_date and max(tail_with_date) < since:
                    print(f"  → all of last 50 older than {since}, stop", flush=True)
                    break

        await page.screenshot(path=str(out_dir / "99_final.png"), full_page=False)
        await browser.close()

    return {"url": url, "items": collected, "fetched_at": datetime.now().isoformat()}


def main() -> int:
    import fcntl
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--since", default=None, help="cutoff YYYY-MM-DD (stop when older)")
    ap.add_argument("--max-pages", type=int, default=200)
    args = ap.parse_args()

    # flock на slug — НЕ давать 2 параллельным процессам биться за persistent context
    lock_path = Path(f"/tmp/orm-pulse-pw-{args.slug}.lock")
    lock_fd = open(lock_path, "w")
    try:
        fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print(f"⚠️ Another playwright-full-crawl уже работает для {args.slug} (lock {lock_path}). Skip.", file=sys.stderr)
        return 3

    try:
        result = asyncio.run(crawl(args.slug, args.since, args.max_pages))
    except Exception as e:
        # Не падаем тихо — выводим короткую причину чтобы daily-cron err.log был полезным
        import traceback
        print(f"❌ crawl failed: {type(e).__name__}: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr, limit=3)
        return 1
    finally:
        try:
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
            lock_fd.close()
        except Exception:
            pass

    out_dir = Path("/tmp/orm-pulse") / args.slug / "full-crawl"
    ts = datetime.now().strftime("%Y-%m-%d-%H%M")
    snap_path = out_dir / f"{ts}.json"
    snap_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))

    # Stable copy в clients
    stable_dir = ROOT / "clients" / args.slug / "orm" / "live-reviews"
    stable_dir.mkdir(parents=True, exist_ok=True)
    (stable_dir / f"{datetime.now().strftime('%Y-%m-%d')}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2)
    )

    items = result["items"]
    with_date = [i for i in items if i.get("date_iso")]
    print(f"\n✅ Total: {len(items)}")
    print(f"   With date: {len(with_date)}")
    if with_date:
        dates = sorted(d for d in (i.get("date_iso") for i in items) if d)
        print(f"   Range: {dates[0]} → {dates[-1]}")
    print(f"💾 {snap_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
