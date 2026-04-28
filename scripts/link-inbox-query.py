#!/usr/bin/env python3
"""
link-inbox-query.py — Supabase helper для skill process-link.

Команды:
  --pending --limit N        Вернуть N pending строк в JSON
  --mark-processing <id>     status='processing' (резерв строки)
  --update <id> --json <str> UPDATE полями из JSON
  --send-card <id>           Собрать карточку из БД + editMessageText в TG
  --asana-pending --limit N  Вернуть строки с priority='asana-pending'
"""
import argparse
import json
import os
import sys
import ssl
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# === Env ===
TOKENS = json.load(open(Path.home() / "artvision-data/tokens.json"))
SB_URL = TOKENS["supabase"]["url"]
SB_KEY = TOKENS["supabase"]["anon_key"]

# Bot token — читаем из artvision-tg-bot/.env.local
def _load_bot_token():
    env_file = Path.home() / "artvision-tg-bot/.env.local"
    if not env_file.exists():
        return os.environ.get("TELEGRAM_BOT_TOKEN", "")
    for line in env_file.read_text().splitlines():
        if line.startswith("TELEGRAM_BOT_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"')
    return ""

BOT_TOKEN = _load_bot_token()
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

HEADERS = {
    "apikey": SB_KEY,
    "Authorization": f"Bearer {SB_KEY}",
    "Content-Type": "application/json",
}

# === SSL context (Python 3.14 + OpenSSL 3.x fix) ===
_SSL_CTX = ssl.create_default_context()

# === Supabase helpers ===
def sb_get(path: str, params: dict | None = None):
    url = f"{SB_URL}/rest/v1/{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15, context=_SSL_CTX) as r:
        return json.loads(r.read())

def sb_patch(path: str, params: dict, data: dict):
    url = f"{SB_URL}/rest/v1/{path}?" + urllib.parse.urlencode(params)
    body = json.dumps(data).encode()
    h = dict(HEADERS)
    h["Prefer"] = "return=representation"
    req = urllib.request.Request(url, method="PATCH", headers=h, data=body)
    with urllib.request.urlopen(req, timeout=15, context=_SSL_CTX) as r:
        return json.loads(r.read())

# === TG helpers ===
def tg_call(method: str, payload: dict):
    req = urllib.request.Request(
        f"{TG_API}/{method}",
        method="POST",
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload).encode(),
    )
    try:
        with urllib.request.urlopen(req, timeout=15, context=_SSL_CTX) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"ok": False, "error": e.read().decode()[:300]}

# === Commands ===
def cmd_pending(limit: int):
    rows = sb_get("link_inbox", {
        "status": "eq.pending",
        "order": "created_at.asc",
        "limit": str(limit),
        "select": "id,user_id,chat_id,message_id,temp_message_id,url,url_normalized,platform,created_at,tags,priority",
    })
    print(json.dumps(rows, ensure_ascii=False, indent=2))

def cmd_asana_pending(limit: int):
    rows = sb_get("link_inbox", {
        "priority": "eq.asana-pending",
        "order": "processed_at.desc",
        "limit": str(limit),
        "select": "id,url,title,summary,applicability,tags",
    })
    print(json.dumps(rows, ensure_ascii=False, indent=2))

def cmd_mark_processing(link_id: str):
    sb_patch("link_inbox", {"id": f"eq.{link_id}"}, {"status": "processing"})
    print(f"OK processing: {link_id}")

def cmd_update(link_id: str, data_json: str):
    try:
        data = json.loads(data_json)
    except json.JSONDecodeError as e:
        print(f"ERROR: invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)
    sb_patch("link_inbox", {"id": f"eq.{link_id}"}, data)
    print(f"OK updated: {link_id}")

def _build_card_text(row: dict) -> str:
    """HTML для editMessageText. Макс ~4000 символов."""
    def esc(s):
        return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    title = esc(row.get("title") or "Без заголовка")
    author = esc(row.get("author") or "—")
    platform = esc(row.get("platform") or "—")
    summary = esc(row.get("summary") or "—")
    how = esc(row.get("how_it_works") or "—")
    url = row.get("url", "")

    lines = [
        f"📚 <b>{title}</b>",
        f"by {author} · {platform}",
        "",
        f"🎯 <b>Суть:</b> {summary}",
        "",
        f"🔍 <b>Как работает:</b>",
        how,
    ]

    # Applicability
    app = row.get("applicability") or {}
    if app:
        lines.append("")
        lines.append("💡 <b>Для нас:</b>")
        for k, v in app.items():
            lines.append(f"→ {esc(str(k))}: {esc(str(v))}")

    # Factcheck counters
    cs = row.get("confirmed_sources") or []
    if isinstance(cs, list) and cs:
        n_conf = sum(1 for c in cs if c.get("status") == "CONFIRMED")
        n_unc = sum(1 for c in cs if c.get("status") == "UNCONFIRMED")
        n_wrong = sum(1 for c in cs if c.get("status") == "WRONG")
        parts = []
        if n_conf: parts.append(f"✅ {n_conf}")
        if n_unc: parts.append(f"⚠️ {n_unc}")
        if n_wrong: parts.append(f"❌ {n_wrong}")
        if parts:
            lines.append("")
            lines.append(" · ".join(parts))

    lines.append("")
    lines.append(f"🔗 {esc(url)}")
    text = "\n".join(lines)
    # Trim if too long
    if len(text) > 4000:
        text = text[:3950] + "\n…"
    return text

def _build_keyboard(link_id: str, url: str) -> dict:
    return {
        "inline_keyboard": [
            [
                {"text": "📌 В задачу", "callback_data": f"lnk_task_{link_id}"},
                {"text": "🧠 В memory", "callback_data": f"lnk_mem_{link_id}"},
            ],
            [
                {"text": "🏷 Тег", "callback_data": f"lnk_tag_{link_id}"},
                {"text": "🗑 Скип", "callback_data": f"lnk_skip_{link_id}"},
            ],
            [
                {"text": "🔗 Открыть", "url": url},
            ],
        ]
    }

def cmd_send_card(link_id: str):
    rows = sb_get("link_inbox", {"id": f"eq.{link_id}", "limit": "1"})
    if not rows:
        print(f"ERROR: no row {link_id}", file=sys.stderr)
        sys.exit(1)
    row = rows[0]

    text = _build_card_text(row)
    kb = _build_keyboard(link_id, row["url"])
    chat_id = row["chat_id"]
    temp_id = row.get("temp_message_id")

    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
        "reply_markup": kb,
    }

    if temp_id:
        payload["message_id"] = temp_id
        result = tg_call("editMessageText", payload)
        # Если edit провалился (temp удалили / уже отредактировали) — шлём новое
        if not result.get("ok"):
            payload.pop("message_id", None)
            payload["reply_to_message_id"] = row.get("message_id")
            result = tg_call("sendMessage", payload)
    else:
        payload["reply_to_message_id"] = row.get("message_id")
        result = tg_call("sendMessage", payload)

    print(json.dumps(result, ensure_ascii=False))

def cmd_finalize():
    """
    Дожим после claude -p: находит processed строки без learning_file/memory_file
    и дозаписывает:
      1) Карточку в TG (editMessageText) если temp_message_id есть
      2) learning/links/YYYY-MM.md — append
      3) memory/trend_<slug>.md — если priority='high' или есть тег 'force-memory' или confirmed_sources >= 2
      4) UPDATE строки с путями к файлам + processed_at
    """
    import os
    import re
    from datetime import datetime, timezone

    # Строки со status='processed' но без learning_file
    rows = sb_get("link_inbox", {
        "status": "eq.processed",
        "learning_file": "is.null",
        "order": "processed_at.desc.nullsfirst,created_at.asc",
        "limit": "10",
        "select": "*",
    })

    if not rows:
        print("finalize: nothing to do")
        return

    ARTVISION_ROOT = os.path.expanduser("~/artvision-data")
    MEMORY_ROOT = os.path.expanduser("~/.claude/projects/-Users-antonk/memory")
    month = datetime.now().strftime("%Y-%m")
    learning_path = f"{ARTVISION_ROOT}/learning/links/{month}.md"
    os.makedirs(os.path.dirname(learning_path), exist_ok=True)

    def slugify(s: str) -> str:
        s = (s or "").lower()
        # Транслит базовый
        tr = {
            'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'yo','ж':'zh','з':'z','и':'i','й':'y','к':'k',
            'л':'l','м':'m','н':'n','о':'o','п':'p','р':'r','с':'s','т':'t','у':'u','ф':'f','х':'h','ц':'ts',
            'ч':'ch','ш':'sh','щ':'sch','ъ':'','ы':'y','ь':'','э':'e','ю':'yu','я':'ya',
        }
        s = ''.join(tr.get(c, c) for c in s)
        s = re.sub(r'[^a-z0-9]+', '_', s).strip('_')
        return s[:60] or 'untitled'

    now_iso = datetime.now(timezone.utc).isoformat()

    for row in rows:
        link_id = row["id"]
        title = row.get("title") or "—"
        print(f"\n=== finalize {link_id}: {title[:60]} ===")

        # 1) Карточка в TG
        try:
            cmd_send_card(link_id)
            print("  ✅ card sent")
        except Exception as e:
            print(f"  ⚠️ card send: {e}")

        # 2) Learning markdown — append
        url = row.get("url", "")
        author = row.get("author") or "—"
        platform = row.get("platform") or "—"
        summary = row.get("summary") or "—"
        how = row.get("how_it_works") or ""
        applicability = row.get("applicability") or {}
        tags = row.get("tags") or []
        confirmed = row.get("confirmed_sources") or []

        dt = (row.get("created_at") or "")[:16].replace("T", " ")
        app_lines = []
        if isinstance(applicability, dict):
            for k, v in applicability.items():
                app_lines.append(f"- **{k}**: {v}")
        elif isinstance(applicability, list):
            for v in applicability:
                app_lines.append(f"- {v}")
        app_block = "\n".join(app_lines) or "—"

        fact_lines = []
        for c in confirmed if isinstance(confirmed, list) else []:
            status = c.get("status", "?")
            claim = c.get("claim", "")
            srcs = c.get("sources", [])
            fact_lines.append(f"- **{status}:** {claim}" + (f" [src: {', '.join(srcs[:3])}]" if srcs else ""))
        fact_block = "\n".join(fact_lines) or "—"

        section = f"""## {dt} · {title}
**Source:** {url}  |  **Author:** {author}  |  **Platform:** {platform}

### Суть
{summary}

### Как работает
{how or '—'}

### Применимость
{app_block}

### Факты
{fact_block}

### Теги
{', '.join(tags) if tags else '—'}

---

"""
        # Создать файл с заголовком месяца если пусто
        if not os.path.exists(learning_path):
            with open(learning_path, 'w', encoding='utf-8') as f:
                f.write(f"# Learning Links — {month}\n\n")
        # Идемпотентность: не дублировать если уже записано
        with open(learning_path, 'r', encoding='utf-8') as f:
            existing = f.read()
        marker = f"## {dt} · {title}"
        if marker in existing:
            print(f"  ℹ️ learning: already appended")
        else:
            with open(learning_path, 'a', encoding='utf-8') as f:
                f.write(section)
            print(f"  ✅ learning appended: {learning_path}")

        # 3) Memory trend — если durable
        priority = row.get("priority") or ""
        is_durable = (
            priority == "high"
            or "force-memory" in tags
            or (isinstance(confirmed, list) and sum(1 for c in confirmed if c.get("status") == "CONFIRMED") >= 2)
        )

        memory_path = None
        if is_durable:
            slug = slugify(title)
            memory_path = f"{MEMORY_ROOT}/trend_{slug}.md"
            if not os.path.exists(memory_path):
                conf_sources = [c for c in confirmed if isinstance(c, dict) and c.get("sources")] if isinstance(confirmed, list) else []
                conf_urls = []
                for c in conf_sources[:3]:
                    conf_urls.extend(c.get("sources", [])[:2])
                conf_block = "\n".join(f"  - {u}" for u in conf_urls[:5]) or f"  - (no additional sources)"

                memory_content = f"""---
name: trend_{slug}
description: {summary[:140]}
type: reference
source: {url}
fetched: {now_iso}
fetched_via: link-processor finalize
author: {author}
confirmed_by:
{conf_block}
---

## Факт
{summary}

## Как работает
{how or '—'}

## Применимость
{app_block}

## Проверено
{datetime.now().strftime('%Y-%m-%d')}, {len([c for c in confirmed if c.get('status') == 'CONFIRMED']) if isinstance(confirmed, list) else 0} подтверждённых источников
"""
                with open(memory_path, 'w', encoding='utf-8') as f:
                    f.write(memory_content)
                print(f"  ✅ memory created: {memory_path}")

                # Добавим в MEMORY.md индекс
                memory_index = f"{MEMORY_ROOT}/MEMORY.md"
                if os.path.exists(memory_index):
                    with open(memory_index, 'r', encoding='utf-8') as f:
                        idx_content = f.read()
                    if f"trend_{slug}" not in idx_content:
                        with open(memory_index, 'a', encoding='utf-8') as f:
                            f.write(f"| `trend_{slug}.md` | {summary[:120]} |\n")
            else:
                print(f"  ℹ️ memory: already exists")

        # 4) UPDATE row
        update_data = {
            "learning_file": learning_path,
            "processed_at": now_iso,
        }
        if memory_path:
            update_data["memory_file"] = memory_path
        sb_patch("link_inbox", {"id": f"eq.{link_id}"}, update_data)
        print(f"  ✅ row updated")

    print(f"\nfinalize complete: {len(rows)} rows")

def cmd_send_error(link_id: str, error_msg: str):
    rows = sb_get("link_inbox", {"id": f"eq.{link_id}", "limit": "1"})
    if not rows:
        sys.exit(1)
    row = rows[0]
    text = f"⚠️ Не смог обработать {row['url']}\n\n{error_msg[:500]}\n\nСкинь краткое описание — добавлю в memory."
    payload = {"chat_id": row["chat_id"], "text": text}
    temp_id = row.get("temp_message_id")
    if temp_id:
        payload["message_id"] = temp_id
        tg_call("editMessageText", payload)
    else:
        payload["reply_to_message_id"] = row.get("message_id")
        tg_call("sendMessage", payload)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pending", action="store_true")
    ap.add_argument("--asana-pending", action="store_true")
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--mark-processing", metavar="ID")
    ap.add_argument("--update", metavar="ID")
    ap.add_argument("--json", metavar="JSON")
    ap.add_argument("--send-card", metavar="ID")
    ap.add_argument("--send-error", metavar="ID")
    ap.add_argument("--error-msg", default="")
    ap.add_argument("--finalize", action="store_true", help="Дожим processed-строк: карточка + learning + memory")
    args = ap.parse_args()

    if args.pending:
        cmd_pending(args.limit)
    elif args.asana_pending:
        cmd_asana_pending(args.limit)
    elif args.mark_processing:
        cmd_mark_processing(args.mark_processing)
    elif args.update:
        if not args.json:
            print("ERROR: --update requires --json", file=sys.stderr)
            sys.exit(1)
        cmd_update(args.update, args.json)
    elif args.send_card:
        cmd_send_card(args.send_card)
    elif args.send_error:
        cmd_send_error(args.send_error, args.error_msg)
    elif args.finalize:
        cmd_finalize()
    else:
        ap.print_help()
        sys.exit(2)

if __name__ == "__main__":
    main()
