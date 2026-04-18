#!/usr/bin/env python3
"""
Bank Form Automation — отправка заявлений в банки через Playwright.

Использование:
  python3 ~/.claude/scripts/bank-form.py --bank alfa --action mortgage-holidays --message "текст"
  python3 ~/.claude/scripts/bank-form.py --bank alfa --action complaint --message-file /tmp/complaint.txt
  python3 ~/.claude/scripts/bank-form.py --bank sber --action support --message "текст"
  python3 ~/.claude/scripts/bank-form.py --list   # список банков и действий

Поддерживаемые банки: Альфа-Банк, Сбер, Т-Банк (Тинькофф).
"""

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

SCREENSHOT_DIR = Path("/tmp")
SUPPORT_DIR = Path("/Users/antonk/artvision-data/docs/support")

# Конфигурация банков
BANKS = {
    "alfa": {
        "name": "Альфа-Банк",
        "support_url": "https://alfabank.ru/feedback/",
        "chat_url": "https://click.alfabank.ru/",
        "phone": "8-800-200-00-00",
        "actions": {
            "mortgage-holidays": {
                "name": "Ипотечные каникулы",
                "path": "Ипотека → Каникулы / Реструктуризация",
                "url": "https://alfabank.ru/feedback/",
            },
            "complaint": {
                "name": "Жалоба",
                "url": "https://alfabank.ru/feedback/",
            },
            "support": {
                "name": "Обращение в поддержку",
                "url": "https://alfabank.ru/feedback/",
            },
        },
    },
    "sber": {
        "name": "Сбербанк",
        "support_url": "https://www.sberbank.com/ru/feedback",
        "phone": "900",
        "actions": {
            "support": {
                "name": "Обращение в поддержку",
                "url": "https://www.sberbank.com/ru/feedback",
            },
            "complaint": {
                "name": "Жалоба",
                "url": "https://www.sberbank.com/ru/feedback",
            },
        },
    },
    "tbank": {
        "name": "Т-Банк (Тинькофф)",
        "support_url": "https://www.tbank.ru/feedback/",
        "phone": "8-800-555-22-44",
        "actions": {
            "support": {
                "name": "Обращение в поддержку",
                "url": "https://www.tbank.ru/feedback/",
            },
        },
    },
}


async def submit_bank_form(bank_key, action, message):
    """Отправить форму в банк через Playwright."""
    from playwright.async_api import async_playwright

    bank = BANKS[bank_key]
    action_config = bank["actions"][action]
    url = action_config["url"]
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()
        page.set_default_timeout(15000)

        try:
            print(f"[...] Открываю {url}...")
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            await page.screenshot(
                path=str(SCREENSHOT_DIR / f"bank-{bank_key}-{ts}-1-page.jpg"),
                type="jpeg", quality=70
            )

            # Ищем форму обратной связи
            # Общий подход: найти textarea или input[type=text], заполнить
            print("[...] Ищу форму...")

            # Попробовать заполнить поля
            fields_filled = 0

            # Имя
            for sel in ["input[name*='name' i]", "input[placeholder*='имя' i]", "input[placeholder*='ФИО' i]"]:
                inp = page.locator(sel)
                if await inp.count() > 0 and await inp.first.is_visible():
                    await inp.first.fill("Камеристый Антон Алексеевич")
                    fields_filled += 1
                    break

            # Email
            for sel in ["input[name*='email' i]", "input[type='email']", "input[placeholder*='mail' i]"]:
                inp = page.locator(sel)
                if await inp.count() > 0 and await inp.first.is_visible():
                    await inp.first.fill("justtrance@gmail.com")
                    fields_filled += 1
                    break

            # Телефон
            for sel in ["input[name*='phone' i]", "input[type='tel']", "input[placeholder*='телефон' i]"]:
                inp = page.locator(sel)
                if await inp.count() > 0 and await inp.first.is_visible():
                    await inp.first.fill("+79219990770")
                    fields_filled += 1
                    break

            # Текст обращения
            for sel in ["textarea", "div[contenteditable='true']", "input[name*='message' i]"]:
                ta = page.locator(sel)
                if await ta.count() > 0 and await ta.first.is_visible():
                    await ta.first.click()
                    await ta.first.fill(message)
                    fields_filled += 1
                    print(f"[OK] Текст введён ({len(message)} символов)")
                    break

            print(f"[OK] Заполнено {fields_filled} полей")

            await page.screenshot(
                path=str(SCREENSHOT_DIR / f"bank-{bank_key}-{ts}-2-filled.jpg"),
                type="jpeg", quality=70
            )

            # НЕ отправляем автоматически — CONFIRM уровень
            print(f"\n[CONFIRM] Форма заполнена, НЕ отправлена.")
            print(f"Скриншот: /tmp/bank-{bank_key}-{ts}-2-filled.jpg")
            print(f"Для отправки нужно подтверждение Антона.")

            # Ждём чтобы можно было проверить
            await asyncio.sleep(5)

            return True

        except Exception as e:
            print(f"[ERR] {e}")
            try:
                await page.screenshot(
                    path=str(SCREENSHOT_DIR / f"bank-{bank_key}-{ts}-error.jpg"),
                    type="jpeg", quality=70
                )
            except:
                pass
            return False

        finally:
            await context.close()
            await browser.close()


def save_copy(bank_key, action, message):
    """Сохранить копию обращения."""
    SUPPORT_DIR.mkdir(parents=True, exist_ok=True)
    bank = BANKS[bank_key]
    date_str = datetime.now().strftime("%Y-%m-%d")
    path = SUPPORT_DIR / f"{bank_key}-{action}-{date_str}.md"

    content = f"""# Обращение в {bank['name']}

**Дата:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Действие:** {bank['actions'][action]['name']}
**Статус:** форма заполнена, ожидает подтверждения

---

## Текст обращения

{message}

---

Камеристый Антон Алексеевич
+7 921 999 07 70
justtrance@gmail.com
"""
    path.write_text(content)
    print(f"[OK] Копия: {path}")


def list_banks():
    """Показать список банков и действий."""
    print("\nПоддерживаемые банки:\n")
    for key, bank in BANKS.items():
        print(f"  {key}: {bank['name']} ({bank['phone']})")
        for akey, action in bank["actions"].items():
            print(f"    --action {akey}: {action['name']}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Bank Form Automation")
    parser.add_argument("--bank", "-b", choices=list(BANKS.keys()), help="Банк")
    parser.add_argument("--action", "-a", help="Действие (mortgage-holidays, complaint, support)")
    parser.add_argument("--message", "-m", help="Текст обращения")
    parser.add_argument("--message-file", "-f", help="Файл с текстом")
    parser.add_argument("--list", "-l", action="store_true", help="Список банков")
    args = parser.parse_args()

    if args.list:
        list_banks()
        return

    if not args.bank:
        parser.print_help()
        return

    if args.action not in BANKS[args.bank]["actions"]:
        print(f"[ERR] Неизвестное действие '{args.action}' для {BANKS[args.bank]['name']}")
        print(f"Доступные: {', '.join(BANKS[args.bank]['actions'].keys())}")
        return

    if args.message:
        message = args.message
    elif args.message_file:
        message = Path(args.message_file).read_text().strip()
    else:
        print("[ERR] Укажите --message или --message-file")
        return

    save_copy(args.bank, args.action, message)
    asyncio.run(submit_bank_form(args.bank, args.action, message))


if __name__ == "__main__":
    main()
