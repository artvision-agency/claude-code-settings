#!/usr/bin/env python3
"""
avportal-spam-watchdog.py — лёгкий сторож против спама @avportal_bot.

Запускается по cron (LaunchAgent pro.artvision.avportal-spam-watchdog, раз в 20 мин).
Стоимость: 1 запрос getMe + grep лога. Алерт максимум 1 раз на событие (дедуп).

Ловит ДВА сигнала:
  1. PRIVACY FLIP — can_read_all_group_messages False→True
     = бота сделали админом группы / отключили privacy mode
     = первопричина инцидента (бот начинает видеть все сообщения).
  2. RATE SPIKE — >TASK_RATE_THRESHOLD обработок/час в логе локального моста
     = фактический всплеск активности (похоже на спам).

Алерт уходит Антону в личку через tg-send.sh (отдельный бот, не @avportal_bot).

Прецедент: session 85fca7e8 (2026-05-25) — @avportal_bot спамил "Task queued"
на каждое сообщение ~2 месяца после получения прав админа в группе.
"""

import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ============ КОНФИГ ============

HOME = Path.home()
TOKENS_PATHS = [
    HOME / "artvision-data" / "tokens.json",
    Path("/root/artvision-data/tokens.json"),
]
STATE_FILE = HOME / ".claude" / "logs" / "avportal-spam-watchdog.state.json"
LOG_FILE = HOME / ".claude" / "logs" / "avportal-spam-watchdog.log"
BRIDGE_LOG = Path("/tmp/tg-to-claude-bridge.log")  # лог локального моста
TG_SEND = HOME / ".claude" / "scripts" / "tg-send.sh"

TASK_RATE_THRESHOLD = 25       # обработок/час в логе моста → подозрение на спам
RATE_WINDOW_SEC = 3600         # окно для подсчёта rate
ALERT_COOLDOWN_SEC = 6 * 3600  # не повторять однотипный алерт чаще раза в 6ч
HTTP_TIMEOUT = 15


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def log(msg: str) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    line = f"{now_utc().isoformat()} {msg}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)


def load_token() -> str:
    for p in TOKENS_PATHS:
        if p.exists():
            t = json.load(open(p))["telegram"]["portal_bot"]["token"]
            return t
    raise FileNotFoundError("tokens.json not found")


def read_state() -> dict:
    try:
        if STATE_FILE.exists():
            return json.load(open(STATE_FILE))
    except (json.JSONDecodeError, IOError):
        pass
    return {}


def write_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    json.dump(state, open(tmp, "w"), indent=2)
    tmp.rename(STATE_FILE)


def send_alert(text: str) -> None:
    """Алерт Антону в личку через tg-send.sh (отдельный бот, не @avportal_bot)."""
    try:
        subprocess.run(
            ["bash", str(TG_SEND), "anton", text],
            timeout=30,
            check=False,
            capture_output=True,
        )
        log(f"ALERT SENT: {text[:80]}")
    except Exception as e:  # noqa: BLE001
        log(f"ALERT FAILED: {e}")


def can_alert(state: dict, key: str) -> bool:
    """Дедуп: не повторять однотипный алерт чаще ALERT_COOLDOWN_SEC."""
    last = state.get("last_alert", {}).get(key, 0)
    return (time.time() - last) >= ALERT_COOLDOWN_SEC


def mark_alert(state: dict, key: str) -> None:
    state.setdefault("last_alert", {})[key] = time.time()


# ============ ПРОВЕРКИ ============


def check_privacy(token: str, state: dict) -> None:
    """Сигнал 1: privacy mode (can_read_all_group_messages)."""
    try:
        import urllib.request

        url = f"https://api.telegram.org/bot{token}/getMe"
        with urllib.request.urlopen(url, timeout=HTTP_TIMEOUT) as r:
            data = json.loads(r.read().decode())
    except Exception as e:  # noqa: BLE001
        log(f"getMe failed: {e}")
        return

    if not data.get("ok"):
        log(f"getMe not ok: {data.get('description')}")
        return

    privacy_off = bool(data["result"].get("can_read_all_group_messages"))
    prev = state.get("privacy_off")
    state["privacy_off"] = privacy_off
    log(f"privacy_off={privacy_off} (prev={prev})")

    # Первый запуск — только фиксируем baseline, без алерта
    if prev is None:
        return

    # Переход False→True = бота сделали админом группы / отключили privacy
    if privacy_off and not prev and can_alert(state, "privacy"):
        send_alert(
            "⚠️ @avportal_bot: privacy mode ОТКЛЮЧЁН "
            "(can_read_all_group_messages=True).\n"
            "Вероятно бота сделали админом в группе — он теперь видит ВСЕ сообщения. "
            "Это первопричина спама 'Task queued'. Проверь права бота в группах."
        )
        mark_alert(state, "privacy")
    # Восстановление True→False
    elif prev and not privacy_off:
        send_alert("✅ @avportal_bot: privacy mode снова включён. Риск спама снят.")


def check_rate(state: dict) -> None:
    """Сигнал 2: всплеск активности в логе локального моста."""
    if not BRIDGE_LOG.exists():
        return  # мост не запущен/нет лога — спамить нечему

    cutoff = time.time() - RATE_WINDOW_SEC
    count = 0
    try:
        with open(BRIDGE_LOG, encoding="utf-8", errors="ignore") as f:
            for line in f:
                if "Task added" not in line:
                    continue
                # формат: "2026-05-25 11:57:38,624 [INFO] Task added: ..."
                ts_str = line[:19]
                try:
                    dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                    # лог в локальном времени; сравниваем по epoch грубо
                    if dt.timestamp() >= cutoff:
                        count += 1
                except ValueError:
                    continue
    except IOError as e:
        log(f"bridge log read failed: {e}")
        return

    log(f"bridge rate last {RATE_WINDOW_SEC//60}min = {count} (threshold {TASK_RATE_THRESHOLD})")

    if count > TASK_RATE_THRESHOLD and can_alert(state, "rate"):
        send_alert(
            f"⚠️ @avportal_bot (локальный мост): всплеск активности — "
            f"{count} обработок за час (порог {TASK_RATE_THRESHOLD}).\n"
            "Похоже на спам/реакцию на каждое сообщение. Проверь tg-to-claude-bridge.py."
        )
        mark_alert(state, "rate")


def main() -> int:
    try:
        token = load_token()
    except Exception as e:  # noqa: BLE001
        log(f"FATAL load_token: {e}")
        return 0  # exit 0 чтобы launchd не перезапускал в цикле

    state = read_state()
    check_privacy(token, state)
    check_rate(state)
    write_state(state)
    return 0


if __name__ == "__main__":
    sys.exit(main())
