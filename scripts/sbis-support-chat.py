#!/usr/bin/env python3
"""
СБИС (Saby) Support Chat — отправка обращения в техподдержку.

Использование:
  python3 ~/.claude/scripts/sbis-support-chat.py --message "текст" [--category "ЭДО и EDI"]
  python3 ~/.claude/scripts/sbis-support-chat.py --message-file /tmp/msg.txt
  python3 ~/.claude/scripts/sbis-support-chat.py --status  # проверить ответ

Требования:
  - Yandex Browser (/Applications/Yandex.app)
  - ЭЦП (КриптоПро) — USB-токен вставлен
  - playwright (pip install playwright)

Путь бота:
  ? → Поддержка Saby → [категория] → подкатегория → "Нет, позови оператора" → текст
"""

import asyncio
import argparse
import sys
from datetime import datetime

# Конфигурация
YANDEX_PATH = "/Applications/Yandex.app/Contents/MacOS/Yandex"
PROFILE_DIR = "/tmp/yandex-sbis-profile"
SBIS_URL = "https://online.sbis.ru/"
SCREENSHOT_DIR = "/tmp"
CERT_NAME = "Камеристый"

# Категории бота (верхний уровень)
BOT_CATEGORIES = [
    "Отчетность",
    "ЭДО и EDI",
    "Бухгалтерия и зарплата",
    "Электронная подпись",
    "Кассы, Розница, Presto, Hotel",
    "Маркировка, ЕГАИС, Меркурий",
    "Складской учет",
    "МЧД и другие вопросы",
]


async def login_ecp(page):
    """Логин через ЭЦП. Возвращает True если успешно."""
    url = page.url
    if "online.sbis.ru" in url and "sso" not in url and "auth" not in url:
        print("[OK] Уже залогинены")
        return True

    print("[...] Логин через ЭЦП...")
    try:
        await page.locator("text=По электронной подписи").click(timeout=10000)
        await asyncio.sleep(3)

        cert = page.locator(f"text=/{CERT_NAME}/")
        if await cert.count() > 0:
            await cert.first.click()
            print(f"[OK] Сертификат {CERT_NAME} выбран, ждём авторизацию...")
            try:
                await page.wait_for_url("**/online.sbis.ru/**", timeout=25000)
            except:
                await asyncio.sleep(10)

            if "sso" not in page.url:
                print("[OK] Залогинены!")
                return True
        else:
            print("[ERR] Сертификат не найден. ЭЦП вставлена?")
    except Exception as e:
        print(f"[ERR] Ошибка логина: {e}")

    return False


async def open_support_chat(page):
    """Открыть чат Поддержка Saby. Возвращает True если открылся."""
    print("[...] Открываю чат поддержки...")

    # Кнопка ?
    help_btn = page.locator(".sabyPage-HelpButton")
    if await help_btn.count() > 0:
        await help_btn.first.click()
        await asyncio.sleep(2)
    else:
        print("[ERR] Кнопка помощи не найдена")
        return False

    # Поддержка Saby
    support = page.locator("text='Поддержка Saby'")
    if await support.count() > 0:
        await support.first.click()
        await asyncio.sleep(4)
        print("[OK] Чат поддержки открыт")
        return True

    print("[ERR] 'Поддержка Saby' не найдена в меню помощи")
    return False


async def click_bot_button(page, text, min_y=300):
    """Кликнуть кнопку бота по тексту. Возвращает True если нашёл и кликнул."""
    btn = page.locator(f"text='{text}'")
    cnt = await btn.count()
    for i in range(cnt):
        if await btn.nth(i).is_visible():
            box = await btn.nth(i).bounding_box()
            if box and box['y'] > min_y:
                await btn.nth(i).click()
                await asyncio.sleep(4)
                return True
    return False


async def navigate_to_operator(page, category="ЭДО и EDI"):
    """Пройти бота до вызова оператора."""
    print(f"[...] Навигация: {category} → оператор...")

    # 1. Категория
    if await click_bot_button(page, category):
        print(f"[OK] Категория: {category}")
    else:
        print(f"[WARN] Категория '{category}' не найдена")

    # 2. Подкатегория — пробуем релевантные
    subcategories = [
        "Работа с документами",
        "Приглашения к ЭДО или роумингу",
    ]
    for sub in subcategories:
        if await click_bot_button(page, sub):
            print(f"[OK] Подкатегория: {sub}")
            break

    # 3. Ещё уровень
    detail_options = [
        "Подписать или отклонить документ",
        "Нет права подписи по организации",
    ]
    for opt in detail_options:
        if await click_bot_button(page, opt):
            print(f"[OK] Детализация: {opt}")
            break

    # 4. "Нет, позови оператора"
    operator_phrases = [
        "Нет, позови оператора",
        "Позови оператора",
        "Не помогло",
    ]
    for phrase in operator_phrases:
        btn = page.locator(f"text=/{phrase}/i")
        cnt = await btn.count()
        for i in range(cnt):
            if await btn.nth(i).is_visible():
                box = await btn.nth(i).bounding_box()
                if box and box['y'] > 300:
                    await btn.nth(i).click()
                    await asyncio.sleep(5)
                    print(f"[OK] Оператор вызван: {phrase}")
                    return True

    print("[WARN] Кнопка вызова оператора не найдена, отправляю текстом")
    return False


async def send_message(page, message):
    """Отправить сообщение в чат."""
    ta = page.locator("textarea")
    if await ta.count() > 0 and await ta.first.is_visible():
        await ta.first.click()
        await asyncio.sleep(0.3)
        await page.keyboard.type(message, delay=2)
        await asyncio.sleep(1)

        # Кнопка отправки
        send_btns = await page.locator("[class*='send' i], button[title*='Отправить']").all()
        for s in send_btns:
            if await s.is_visible():
                await s.click()
                print("[OK] Сообщение отправлено (кнопка)")
                return True

        # Fallback: Ctrl+Enter
        await page.keyboard.press("Control+Enter")
        print("[OK] Сообщение отправлено (Ctrl+Enter)")
        return True

    print("[ERR] Поле ввода не найдено")
    return False


async def main_send(message, category="ЭДО и EDI"):
    """Основной flow: логин → чат → бот → оператор → сообщение."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            executable_path=YANDEX_PATH,
            headless=False,
            args=["--no-first-run", "--disable-blink-features=AutomationControlled"],
            viewport={"width": 1440, "height": 900},
            ignore_default_args=["--enable-automation"],
            timeout=90000,
        )

        page = context.pages[0] if context.pages else await context.new_page()
        page.set_default_timeout(15000)

        try:
            # 1. Navigate
            await page.goto(SBIS_URL, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(5)

            # 2. Login
            if not await login_ecp(page):
                print("[FATAL] Не удалось залогиниться")
                await page.screenshot(path=f"{SCREENSHOT_DIR}/sbis-login-fail.jpg", type="jpeg", quality=70)
                return False

            await asyncio.sleep(2)

            # 3. Open support chat
            if not await open_support_chat(page):
                return False

            # 4. Navigate bot to operator
            await navigate_to_operator(page, category)

            # 5. Send message
            await asyncio.sleep(2)
            result = await send_message(page, message)

            # 6. Screenshot
            ts = datetime.now().strftime("%Y%m%d-%H%M%S")
            screenshot_path = f"{SCREENSHOT_DIR}/sbis-support-{ts}.jpg"
            await page.screenshot(path=screenshot_path, type="jpeg", quality=70, timeout=15000)
            print(f"[OK] Скриншот: {screenshot_path}")

            return result

        except Exception as e:
            print(f"[ERR] {e}")
            try:
                await page.screenshot(path=f"{SCREENSHOT_DIR}/sbis-error.jpg", type="jpeg", quality=70)
            except:
                pass
            return False

        finally:
            await asyncio.sleep(2)
            await context.close()


async def main_status():
    """Проверить ответ в чате поддержки."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            executable_path=YANDEX_PATH,
            headless=False,
            args=["--no-first-run", "--disable-blink-features=AutomationControlled"],
            viewport={"width": 1440, "height": 900},
            ignore_default_args=["--enable-automation"],
            timeout=90000,
        )

        page = context.pages[0] if context.pages else await context.new_page()
        page.set_default_timeout(15000)

        try:
            await page.goto(SBIS_URL, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(5)

            if not await login_ecp(page):
                return

            await asyncio.sleep(2)
            if not await open_support_chat(page):
                return

            await asyncio.sleep(3)
            ts = datetime.now().strftime("%Y%m%d-%H%M%S")
            await page.screenshot(path=f"{SCREENSHOT_DIR}/sbis-status-{ts}.jpg", type="jpeg", quality=70)

            chat_text = await page.evaluate("() => document.body?.innerText?.slice(-1500)")
            print(f"\n=== ЧАТ ПОДДЕРЖКИ ===\n{chat_text[-1000:]}")

        finally:
            await asyncio.sleep(2)
            await context.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="СБИС Support Chat")
    parser.add_argument("--message", "-m", help="Текст обращения")
    parser.add_argument("--message-file", "-f", help="Файл с текстом обращения")
    parser.add_argument("--category", "-c", default="ЭДО и EDI",
                       help="Категория бота (default: ЭДО и EDI)")
    parser.add_argument("--status", "-s", action="store_true",
                       help="Проверить ответ в чате")
    args = parser.parse_args()

    if args.status:
        asyncio.run(main_status())
    elif args.message:
        asyncio.run(main_send(args.message, args.category))
    elif args.message_file:
        with open(args.message_file) as f:
            msg = f.read().strip()
        asyncio.run(main_send(msg, args.category))
    else:
        parser.print_help()
        sys.exit(1)
