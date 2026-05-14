#!/usr/bin/env python3
"""kwork-scrape — headless обход kwork с использованием сохранённых cookies.

Использовать после kwork-session-init.py.
Параметры: --orders | --inbox | --all
"""
import argparse, asyncio, json
from pathlib import Path
from playwright.async_api import async_playwright

COOKIES_PATH = Path.home() / ".claude/state/orm-pulse/kwork-cookies.json"
OUT_DIR = Path.home() / ".claude/state/orm-pulse/kwork-scrape"
OUT_DIR.mkdir(parents=True, exist_ok=True)


async def scrape(url: str, slug: str):
    if not COOKIES_PATH.exists():
        print(f"❌ Нет cookies. Сначала запусти: python3 ~/.claude/skills/orm-pulse/scripts/kwork-session-init.py")
        return False
    cookies = json.loads(COOKIES_PATH.read_text())
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 Chrome/124.0",
        )
        await ctx.add_cookies(cookies)
        page = await ctx.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(5000)
        html_path = OUT_DIR / f"{slug}.html"
        png_path = OUT_DIR / f"{slug}.png"
        html_path.write_text(await page.content(), encoding="utf-8")
        await page.screenshot(path=str(png_path), full_page=True)
        print(f"  {slug}: {html_path.stat().st_size} bytes → {url} → {page.url}")
        await browser.close()
        return True


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--orders", action="store_true")
    ap.add_argument("--inbox", action="store_true")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    targets = []
    if args.all or args.orders:
        targets.append(("https://kwork.ru/manage_orders", "orders"))
    if args.all or args.inbox:
        targets.append(("https://kwork.ru/inbox", "inbox"))
    if not targets:
        targets = [("https://kwork.ru/manage_orders", "orders"), ("https://kwork.ru/inbox", "inbox")]
    for url, slug in targets:
        await scrape(url, slug)

if __name__ == "__main__":
    asyncio.run(main())
