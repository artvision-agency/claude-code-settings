#!/usr/bin/env python3
"""Реальная проверка Telethon-сессии (is_user_authorized) → кэш для SessionStart-хука.
Вызывается хуком session-tg-health.sh в фоне при устаревшем кэше.
Правило: self-corrections #20/#29 — НЕ mtime-эвристика, а реальный connect."""
import json, os, asyncio, time, inspect

CACHE = os.path.expanduser("~/.claude/state/tg-session-status.json")
SESSIONS = [
    "/Users/antonk/artvision-data/.claude_temp_scripts/tg_userbot",
    "/Users/antonk/artvision-data/telegram_session",
]

def write(data):
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    data["checked_at"] = int(time.time())
    data["checked_at_human"] = time.strftime("%Y-%m-%d %H:%M MSK")
    with open(CACHE, "w") as f:
        json.dump(data, f, ensure_ascii=False)

async def main():
    try:
        from telethon import TelegramClient
    except ImportError:
        write({"status": "error", "detail": "telethon not installed"})
        return
    try:
        t = json.load(open("/Users/antonk/artvision-data/tokens.json"))["telegram"]
    except Exception as e:
        write({"status": "error", "detail": f"tokens.json: {e}"})
        return
    if "api_id" not in t or "api_hash" not in t:
        # прецедент self-corrections #20: api-креды вычищены аудитом
        write({"status": "no-creds", "detail": "api_id/api_hash отсутствуют в tokens.json"})
        return
    results = []
    for s in SESSIONS:
        if not os.path.exists(s + ".session"):
            results.append({"session": s, "auth": None, "detail": "file missing"})
            continue
        c = TelegramClient(s, t["api_id"], t["api_hash"])
        try:
            await asyncio.wait_for(c.connect(), timeout=15)
            ok = await c.is_user_authorized()
            username = None
            if ok:
                me = await c.get_me()
                username = getattr(me, "username", None)
            results.append({"session": s, "auth": ok, "username": username})
        except Exception as e:
            results.append({"session": s, "auth": None, "detail": f"{type(e).__name__}: {e}"})
        finally:
            try:
                r = c.disconnect()
                if inspect.isawaitable(r):
                    await r
            except Exception:
                pass
    alive = [r for r in results if r.get("auth")]
    write({
        "status": "alive" if alive else "dead",
        "primary": alive[0] if alive else None,
        "results": results,
    })

if __name__ == "__main__":
    asyncio.run(main())
