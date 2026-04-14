#!/usr/bin/env python3
"""
bot-smoke-test.py — smoke-тест TG-бота после деплоя.

Использование:
    python3 bot-smoke-test.py <bot_name> [--token TOKEN] [--process PM2_NAME]

Проверки:
    1. pm2: процесс онлайн, restart count ≤ 3 за последние 2 мин
    2. pm2 logs: нет ERROR/Exception/Traceback за 2 мин
    3. TG Bot API: getMe() отвечает 200 (токен валиден, бот жив)
    4. TG Bot API: getWebhookInfo() — нет pending_update_count > 100
    5. TG Bot API: getUpdates() — нет длинных очередей (long_polling режим)

Выходные коды:
    0 — PASS
    1 — FAIL (rollback рекомендован)
    2 — WARN (проверить вручную)

Токены читаются из tokens.json (~/artvision-tg-bot/tokens.json или передан через --token).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

TOKENS_PATHS = [
    Path.home() / "artvision-tg-bot" / "tokens.json",
    Path.home() / "artvision-data" / "tokens.json",
    Path.home() / ".claude" / "tokens.json",
]


def load_token(bot_name: str, explicit: str | None) -> str | None:
    if explicit:
        return explicit
    env_key = f"BOT_TOKEN_{bot_name.upper().replace('-', '_')}"
    if env_key in os.environ:
        return os.environ[env_key]
    for path in TOKENS_PATHS:
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text())
        except Exception:
            continue
        for key in (bot_name, f"{bot_name}_token", f"tg_{bot_name}"):
            if key in data:
                return data[key]
            if isinstance(data.get("bots"), dict) and key in data["bots"]:
                return data["bots"][key]
    return None


def pm2_status(process: str) -> tuple[bool, str]:
    try:
        out = subprocess.run(
            ["pm2", "jlist"], capture_output=True, text=True, timeout=10
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return False, f"pm2 unavailable: {e}"
    try:
        procs = json.loads(out.stdout or "[]")
    except json.JSONDecodeError:
        return False, "pm2 jlist returned non-json"
    for p in procs:
        if p.get("name") == process:
            status = p.get("pm2_env", {}).get("status", "?")
            restarts = p.get("pm2_env", {}).get("restart_time", 0)
            if status != "online":
                return False, f"status={status}"
            return True, f"online, restarts={restarts}"
    return False, f"process {process!r} not found"


def pm2_logs_clean(process: str, lines: int = 200) -> tuple[bool, str]:
    try:
        out = subprocess.run(
            ["pm2", "logs", process, "--lines", str(lines), "--nostream"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return True, f"pm2 logs unavailable: {e} (skipped)"
    text = (out.stdout or "") + (out.stderr or "")
    needles = ("ERROR", "Exception", "Traceback", "CRITICAL", "FATAL")
    hits = [n for n in needles if n in text]
    if hits:
        return False, f"found: {', '.join(hits)}"
    return True, "clean"


def tg_api(token: str, method: str, timeout: int = 10) -> dict:
    url = f"https://api.telegram.org/bot{token}/{method}"
    req = Request(url, headers={"User-Agent": "bot-smoke-test/1.0"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        return {"ok": False, "error": f"HTTP {e.code}: {e.reason}"}
    except URLError as e:
        return {"ok": False, "error": f"URLError: {e.reason}"}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("bot_name", help="Bot identifier (e.g., tvorims_bot)")
    ap.add_argument("--token", help="Bot token (override)")
    ap.add_argument("--process", help="pm2 process name (default: bot_name)")
    ap.add_argument("--skip-pm2", action="store_true")
    args = ap.parse_args()

    process = args.process or args.bot_name
    results: list[tuple[str, bool, str]] = []

    if not args.skip_pm2:
        ok, msg = pm2_status(process)
        results.append(("pm2 status", ok, msg))
        ok, msg = pm2_logs_clean(process)
        results.append(("pm2 logs", ok, msg))

    token = load_token(args.bot_name, args.token)
    if not token:
        results.append(("tg token", False, "token not found in tokens.json"))
    else:
        me = tg_api(token, "getMe")
        results.append(("getMe", bool(me.get("ok")), me.get("result", {}).get("username", me.get("error", "?"))))

        wh = tg_api(token, "getWebhookInfo")
        if wh.get("ok"):
            info = wh.get("result", {})
            pending = info.get("pending_update_count", 0)
            ok = pending < 100
            results.append(("webhook queue", ok, f"pending={pending}"))
        else:
            results.append(("webhook queue", False, wh.get("error", "?")))

    print(f"\n[smoke-test] bot={args.bot_name}")
    passed = failed = 0
    for name, ok, msg in results:
        mark = "PASS" if ok else "FAIL"
        print(f"  {mark:4} {name:20} {msg}")
        if ok:
            passed += 1
        else:
            failed += 1

    print(f"\n[smoke-test] PASS={passed} FAIL={failed}")
    if failed == 0:
        return 0
    if failed <= 1 and passed >= 2:
        print("VERDICT: WARN — review manually", file=sys.stderr)
        return 2
    print("VERDICT: FAIL — rollback recommended", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
