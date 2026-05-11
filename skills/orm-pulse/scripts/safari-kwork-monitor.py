#!/usr/bin/env python3
"""safari-kwork-monitor — собирает данные kwork через Safari AppleScript.

Использует залогиненную сессию Safari (Антон уже залогинен в Safari).
Через AppleScript JS извлекает: уведомления + список заказов + ID активных треков.
Сохраняет JSON в clients/<slug>/orm/kwork-state-<date>.json.

Преимущество: без captcha, без login (Safari уже залогинен).

Зависит от: Safari + JavaScript from AppleEvents enabled
(см. ~/.claude/skills/youtube-history/SKILL.md prerequisites).

Usage: safari-kwork-monitor.py <slug>
"""
import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path("/Users/antonk/artvision-data")


def applescript(script):
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=60)
    return r.stdout.strip()


def js(url, code):
    """Open Safari URL + run JS, return result."""
    safe_code = code.replace("\\", "\\\\").replace('"', '\\"')
    apple = f"""
    tell application "Safari"
        if (count of windows) = 0 then make new document
        set URL of current tab of front window to "{url}"
        delay 7
        return (do JavaScript "{safe_code}" in current tab of front window)
    end tell
    """
    return applescript(apple)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug", default="blumart", nargs="?")
    args = ap.parse_args()

    out = {"fetched_at": datetime.now().isoformat(), "slug": args.slug}

    # 1) Notifications feed (последние события)
    notif_js = """
        const items = Array.from(document.querySelectorAll('a[href*=track]')).slice(0, 20).map(a => ({
            href: a.href,
            text: (a.textContent || '').replace(/\\s+/g, ' ').trim().slice(0, 200)
        }));
        const date_lines = (document.body.innerText.match(/(\\d{1,2}\\s+(?:мая|апр|июн|июл|мар|фев)\\s+\\d{4})/g) || []).slice(0, 10);
        JSON.stringify({notifications: items, date_lines});
    """
    notif_raw = js("https://kwork.ru/notifications", notif_js)
    try:
        out["notifications"] = json.loads(notif_raw)
    except Exception:
        out["notifications"] = {"_raw": notif_raw[:500]}

    # 2) Active orders как покупатель
    orders_js = """
        const all_a = Array.from(document.querySelectorAll('a'));
        const tracks = all_a.filter(a => a.href && /\\/track\\?/.test(a.href));
        const seen = new Set();
        const unique = [];
        for (const a of tracks) {
            if (seen.has(a.href)) continue;
            seen.add(a.href);
            unique.push({href: a.href, text: (a.textContent||'').replace(/\\s+/g,' ').trim().slice(0,200)});
        }
        // Header counters
        const header = document.body.innerText.slice(0, 1000);
        const orders_n = (header.match(/Заказы\\s*(\\d+)/) || [])[1] || '?';
        const chat_n = (header.match(/Чат\\s*(\\d+)/) || [])[1] || '?';
        const balance_n = (header.match(/(\\d[\\d\\s]*?)\\s*₽/) || [])[1] || '?';
        JSON.stringify({orders: unique, header_orders: orders_n, header_chat: chat_n, header_balance: balance_n});
    """
    orders_raw = js("https://kwork.ru/orders", orders_js)
    try:
        out["orders"] = json.loads(orders_raw)
    except Exception:
        out["orders"] = {"_raw": orders_raw[:500]}

    # 3) Active kworks как продавец
    kworks_js = """
        const counters = Array.from(document.querySelectorAll('span, b')).filter(el => /^\\d+$/.test((el.textContent||'').trim()) && parseInt(el.textContent) > 0).slice(0, 10).map(el => ({n: el.textContent.trim(), ctx: (el.parentElement?.textContent||'').replace(/\\s+/g,' ').trim().slice(0,80)}));
        JSON.stringify({counters});
    """
    out["my_kworks"] = js("https://kwork.ru/manage_kworks", kworks_js)
    try:
        out["my_kworks"] = json.loads(out["my_kworks"])
    except Exception:
        pass

    # Save
    out_dir = ROOT / "clients" / args.slug / "orm"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"kwork-state-{datetime.now().strftime('%Y-%m-%d-%H%M')}.json"
    out_file.write_text(json.dumps(out, ensure_ascii=False, indent=2))

    # Симлинк latest
    latest = out_dir / "kwork-state-latest.json"
    if latest.exists() or latest.is_symlink():
        latest.unlink()
    latest.symlink_to(out_file.name)

    notif = out.get("notifications", {})
    orders = out.get("orders", {})
    print(f"✓ {out_file.name}")
    print(f"  Header: Заказы={orders.get('header_orders','?')} Чат={orders.get('header_chat','?')} Баланс={orders.get('header_balance','?')}")
    print(f"  Notifications: {len(notif.get('notifications', []))}")
    print(f"  Active orders: {len(orders.get('orders', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
