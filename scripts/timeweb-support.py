#!/usr/bin/env python3
"""
Timeweb Cloud Support — отправка тикета через Telegram @twcsupport.

Использование:
  python3 ~/.claude/scripts/timeweb-support.py --message "текст проблемы"
  python3 ~/.claude/scripts/timeweb-support.py --message-file /tmp/ticket.txt
  python3 ~/.claude/scripts/timeweb-support.py --auto   # собрать логи с VPS и отправить
  python3 ~/.claude/scripts/timeweb-support.py --check   # проверить ответ

Панель Timeweb защищена reCAPTCHA — используем Telethon MTProto.
"""

import asyncio
import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    from telethon import TelegramClient
except ImportError:
    print("ERROR: pip install telethon", file=sys.stderr)
    sys.exit(1)

# Конфигурация
API_ID = 35195969
API_HASH = "576ad787126be6f43f28df1a1279aa4a"
SESSION = "/Users/antonk/.telegram_session"
RECIPIENT = "twcsupport"
TOKENS_PATH = "/Users/antonk/artvision-data/tokens.json"
SUPPORT_DIR = Path("/Users/antonk/artvision-data/docs/support")
VPS_IP = "80.90.181.152"


def load_vps_info():
    """Загрузить данные VPS из tokens.json."""
    try:
        data = json.loads(Path(TOKENS_PATH).read_text())
        tw = data["timeweb_cloud"]
        vps = tw["vps"]
        return {
            "id": vps["id"],
            "name": vps["name"],
            "ip": vps["ip"],
            "specs": vps["specs"],
            "login": tw["login"],
            "owner": tw["owner"],
        }
    except Exception as e:
        print(f"[WARN] Не удалось прочитать tokens.json: {e}")
        return {
            "id": "6670871",
            "name": "artvision-main-nl",
            "ip": "80.90.181.152",
            "specs": "4 CPU / 8 GB RAM / 80 GB NVMe",
            "login": "sr951557",
            "owner": "Камеристый Антон",
        }


def collect_vps_diagnostics():
    """Собрать диагностику с VPS через SSH."""
    diag = {}
    commands = {
        "uptime": "uptime",
        "load": "cat /proc/loadavg",
        "memory": "free -h | head -3",
        "disk": "df -h / | tail -1",
        "reboots": "last reboot --time-format iso | head -5",
        "dmesg_errors": "dmesg --time-format iso 2>/dev/null | tail -10 || journalctl -k --no-pager -n 10",
    }
    for key, cmd in commands.items():
        try:
            result = subprocess.run(
                ["ssh", "-o", "ConnectTimeout=5", f"root@{VPS_IP}", cmd],
                capture_output=True, text=True, timeout=15
            )
            diag[key] = result.stdout.strip() if result.returncode == 0 else f"ERROR: {result.stderr.strip()}"
        except Exception as e:
            diag[key] = f"TIMEOUT: {e}"
    return diag


def format_message(description, vps_info, diagnostics=None):
    """Сформировать текст тикета."""
    msg = f"""Тема: {description.split(chr(10))[0][:80]}

Добрый день,

Аккаунт: {vps_info['login']}
Сервер: {vps_info['id']} / {vps_info['name']} ({vps_info['ip']})
Тариф: {vps_info['specs']}

{description}"""

    if diagnostics:
        msg += "\n\nДиагностика с сервера:"
        for key, val in diagnostics.items():
            msg += f"\n\n{key}:\n{val}"

    msg += """

С уважением,
Антон Камеристый
Artvision Agency"""

    return msg


async def send_ticket(message):
    """Отправить тикет в @twcsupport."""
    client = TelegramClient(SESSION, API_ID, API_HASH)
    await client.start()

    try:
        entity = await client.get_entity(RECIPIENT)
        result = await client.send_message(entity, message)
        print(f"[OK] Отправлено: message_id={result.id}, date={result.date}")
        return result
    finally:
        await client.disconnect()


async def check_reply():
    """Проверить ответ от поддержки."""
    client = TelegramClient(SESSION, API_ID, API_HASH)
    await client.start()

    try:
        entity = await client.get_entity(RECIPIENT)
        messages = await client.get_messages(entity, limit=10)
        print(f"\n=== Последние сообщения от @{RECIPIENT} ===\n")
        for msg in reversed(messages):
            sender = "Мы" if msg.out else "Поддержка"
            date = msg.date.strftime("%Y-%m-%d %H:%M")
            text = msg.text or "(без текста)"
            print(f"[{date}] {sender}:\n{text[:500]}\n")
    finally:
        await client.disconnect()


def save_ticket_copy(message, msg_id=None):
    """Сохранить копию тикета."""
    SUPPORT_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    path = SUPPORT_DIR / f"timeweb-ticket-{date_str}.md"

    # Суффикс если файл уже есть
    counter = 2
    while path.exists():
        path = SUPPORT_DIR / f"timeweb-ticket-{date_str}-{counter}.md"
        counter += 1

    vps = load_vps_info()
    content = f"""# Запрос в техподдержку Timeweb Cloud

**Дата:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Сервер:** {vps['id']} / {vps['name']} ({vps['ip']})
**Тариф:** {vps['specs']}
**TG message_id:** {msg_id or 'N/A'}
**Статус:** отправлено

---

## Текст обращения

{message}
"""
    path.write_text(content)
    print(f"[OK] Копия: {path}")
    return path


async def main():
    parser = argparse.ArgumentParser(description="Timeweb Cloud Support via Telegram")
    parser.add_argument("--message", "-m", help="Текст проблемы")
    parser.add_argument("--message-file", "-f", help="Файл с текстом")
    parser.add_argument("--auto", "-a", action="store_true",
                       help="Собрать диагностику с VPS и включить в тикет")
    parser.add_argument("--check", "-c", action="store_true",
                       help="Проверить ответ от поддержки")
    parser.add_argument("--no-diag", action="store_true",
                       help="Не собирать диагностику (при --auto)")
    args = parser.parse_args()

    if args.check:
        await check_reply()
        return

    # Получить текст
    if args.message:
        description = args.message
    elif args.message_file:
        description = Path(args.message_file).read_text().strip()
    elif args.auto:
        description = "Проблема с VPS — требуется диагностика (описание ниже)"
    else:
        parser.print_help()
        sys.exit(1)

    # VPS info
    vps = load_vps_info()

    # Диагностика
    diagnostics = None
    if args.auto and not args.no_diag:
        print("[...] Собираю диагностику с VPS...")
        diagnostics = collect_vps_diagnostics()
        for k, v in diagnostics.items():
            print(f"  {k}: {v[:80]}")

    # Формируем сообщение
    message = format_message(description, vps, diagnostics)

    # Показываем
    print(f"\n{'='*60}")
    print(message)
    print(f"{'='*60}\n")

    # Отправляем
    result = await send_ticket(message)

    # Сохраняем копию
    msg_id = result.id if result else None
    save_ticket_copy(message, msg_id)

    print(f"\nТикет отправлен в @{RECIPIENT}")
    if msg_id:
        print(f"Message ID: {msg_id}")
    print(f"Проверка ответа: python3 {__file__} --check")


if __name__ == "__main__":
    asyncio.run(main())
