#!/usr/bin/env python3
"""kwork-session-init — открывает kwork в headed Chrome, ждёт ручного логина+captcha,
сохраняет cookies для последующих headless-сессий.

Запускать ОДИН РАЗ когда нужен kwork:
    python3 ~/.claude/skills/orm-pulse/scripts/kwork-session-init.py
"""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

PROFILE = Path.home() / ".claude/state/orm-pulse/kwork-profile"
PROFILE.mkdir(parents=True, exist_ok=True)
COOKIES = Path.home() / ".claude/state/orm-pulse/kwork-cookies.json"

async def main():
    print(f"Profile dir: {PROFILE}")
    print("→ Откроется браузер. Залогинься (dune87@yandex.ru / Sossos111) + пройди captcha.")
    print("  Когда увидишь свой кабинет — нажми Enter в этом терминале.")
    print()
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE),
            headless=False,
            viewport={"width": 1440, "height": 900},
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await page.goto("https://kwork.ru/login", timeout=30000)
        
        input("Нажми Enter когда залогинишься: ")
        
        # Сохранить cookies
        import json
        cookies = await ctx.cookies()
        COOKIES.write_text(json.dumps(cookies, ensure_ascii=False, indent=2))
        print(f"✓ {len(cookies)} cookies → {COOKIES}")
        
        # Тест: открыть manage_orders
        await page.goto("https://kwork.ru/manage_orders")
        await page.wait_for_timeout(3000)
        print(f"  Test URL: {page.url}")
        if "manage_orders" in page.url:
            print("✅ Session работает")
        else:
            print("⚠️ Что-то пошло не так — URL не /manage_orders")
        
        await ctx.close()

if __name__ == "__main__":
    asyncio.run(main())
