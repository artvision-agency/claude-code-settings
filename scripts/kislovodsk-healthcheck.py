#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
kislovodsk-healthcheck.py — сторож «жив ли real-time монитор КМВ».

real-time alert (kislovodsk-realtime-alert.py) пишет строку в
~/.claude/logs/kislovodsk-alert.log на КАЖДОМ прогоне (cron */30). Если лог не
обновлялся дольше STALE (дефолт 90 мин = 3 пропуска при */30) — значит cron не
отрабатывал / скрипт молча падает → шлём Антону КОРОТКИЙ пинг.

Идемпотентность (anti-spam): повторный пинг не чаще REPING (дефолт 6 ч). Состояние
в ~/.claude/state/kislovodsk-healthcheck.json. При восстановлении (лог снова
свежий) состояние сбрасывается → следующий простой пингуется сразу.

Запуск из cron ОТДЕЛЬНЫМ job'ом (*/30), НЕ внутри alert-скрипта (иначе если
alert не запускается — некому проверять). Пороги — из kislovodsk-config.json.
Лог сторожа: ~/.claude/logs/kislovodsk-healthcheck.log

Секреты НЕ в коде (self-corrections #31) — TG-отправка через kislovodsk_common
(токены из tokens.json в рантайме).
"""

import os
import sys
import json
import time
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import kislovodsk_common as common
except ImportError:
    print("ERROR: kislovodsk_common.py not importable (нужен рядом)", file=sys.stderr)
    sys.exit(1)

MSK = common.MSK

# Лог real-time alert — его свежесть = пульс монитора.
ALERT_LOG = os.path.expanduser('~/.claude/logs/kislovodsk-alert.log')
STATE_FILE = os.path.expanduser('~/.claude/state/kislovodsk-healthcheck.json')
HC_LOG = os.path.expanduser('~/.claude/logs/kislovodsk-healthcheck.log')

# Пороги из конфига (фолбэк на дефолты — файла нет → не падаем).
STALE_MIN = common.cfg_num("thresholds.healthcheck.stale_minutes", 90)
REPING_HOURS = common.cfg_num("thresholds.healthcheck.reping_hours", 6)


def log(line):
    try:
        os.makedirs(os.path.dirname(HC_LOG), exist_ok=True)
        with open(HC_LOG, 'a', encoding='utf-8') as f:
            f.write(f"{datetime.now(MSK).strftime('%Y-%m-%d %H:%M:%S')} | {line}\n")
    except OSError:
        pass


def load_state():
    try:
        with open(STATE_FILE, encoding='utf-8') as f:
            st = json.load(f)
        return st if isinstance(st, dict) else {}
    except Exception:
        return {}


def save_state(st):
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        tmp = STATE_FILE + ".tmp"
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(st, f, ensure_ascii=False, indent=1)
        os.replace(tmp, STATE_FILE)
    except OSError as ex:
        log(f"STATE_SAVE_FAIL {type(ex).__name__}")


def log_age_minutes():
    """Возраст лога alert в минутах. None, если лог отсутствует (тоже = тревога)."""
    try:
        mtime = os.path.getmtime(ALERT_LOG)
    except OSError:
        return None
    return (time.time() - mtime) / 60.0


def main():
    now = time.time()
    age = log_age_minutes()                    # None = лога нет
    stale = (age is None) or (age > STALE_MIN)

    st = load_state()
    last_ping = st.get("last_ping_ts", 0) or 0

    if not stale:
        # монитор жив → сбросить состояние (следующий простой пингуется сразу)
        if last_ping:
            save_state({})
        log(f"OK alert-log age={age:.0f}m (порог {STALE_MIN}m)")
        print(f"OK (age={age:.0f}m <= {STALE_MIN}m)")
        return 0

    age_txt = "нет лога" if age is None else f"{int(age)} мин"
    # anti-spam: не пинговать чаще REPING_HOURS
    if last_ping and (now - last_ping) < REPING_HOURS * 3600:
        wait_h = (REPING_HOURS * 3600 - (now - last_ping)) / 3600
        log(f"STALE ({age_txt}) — пинг подавлен (anti-spam, ещё ~{wait_h:.1f}ч)")
        print(f"STALE ({age_txt}) — пинг подавлен (anti-spam)")
        return 0

    nowmsk = datetime.now(MSK).strftime('%d.%m %H:%M')
    msg = (f"⚠ Монитор КМВ молчит ({age_txt}, порог {STALE_MIN} мин) · {nowmsk}\n"
           f"real-time БПЛА-алерт не обновлял лог — проверь cron на VPS "
           f"(kislovodsk-realtime-alert.py).")
    rc, raw = common.send_tg(msg, notify=True)
    if rc == 0:
        save_state({"last_ping_ts": now,
                    "last_ping_at": datetime.now(MSK).isoformat(timespec='seconds')})
        log(f"PING SENT stale={age_txt} rc=0")
        print(f"PING SENT (stale {age_txt})")
    else:
        # не фиксируем last_ping → попробуем снова в следующий прогон
        log(f"PING FAIL stale={age_txt} {str(raw)[:120]}")
        print(f"PING FAIL (stale {age_txt})")
    return 0


if __name__ == '__main__':
    sys.exit(main())
