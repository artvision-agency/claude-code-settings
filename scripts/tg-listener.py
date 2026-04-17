#!/usr/bin/env python3
"""
tg-listener.py — Telethon daemon слушает Artvision общий чат, матчит ответы
на активные status_requests и пишет в tg_responses.jsonl.

Запуск:
  python3 tg-listener.py --daemon         # live режим (LaunchAgent)
  python3 tg-listener.py --backfill 2h    # разовый пробег за последние N часов
  python3 tg-listener.py --backfill-msg 6287  # с конкретного msg_id

Output: ~/artvision-data/sync/tg-tracking/tg_responses.jsonl (append-only)
"""
import asyncio
import argparse
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    from telethon import TelegramClient, events
except ImportError:
    print("ERROR: pip3 install telethon", file=sys.stderr); sys.exit(1)

API_ID = 35195969
API_HASH = '576ad787126be6f43f28df1a1279aa4a'
SESSION = '/Users/antonk/.claude/state/telethon_session'

TRACK_DIR = Path.home() / "artvision-data" / "sync" / "tg-tracking"
REQUESTS_FILE = TRACK_DIR / "status_requests.jsonl"
RESPONSES_FILE = TRACK_DIR / "tg_responses.jsonl"
LOG_FILE = TRACK_DIR / "listener.log"

# Основной чат команды Artvision
WATCHED_CHATS = [-4273200821]

# Маппинг TG user_id → recipient name (для матчинга по sender)
SENDER_MAP = {
    1857522687: "andrey",   # @PandaCaffe
    326925698:  "anton",
    356640470:  "stas",
}

# Окно, в котором сообщения от recipient считаются ответом на запрос (минут)
RESPONSE_WINDOW_MIN = 60


def log(msg):
    ts = datetime.now(timezone.utc).isoformat()
    line = f"{ts} {msg}"
    print(line, flush=True)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def load_active_requests():
    """Возвращает awaiting-запросы из status_requests.jsonl."""
    if not REQUESTS_FILE.exists():
        return []
    active = []
    with open(REQUESTS_FILE) as f:
        for line in f:
            try:
                r = json.loads(line)
                if r.get("status") == "awaiting":
                    active.append(r)
            except Exception:
                continue
    return active


def append_response(rec):
    RESPONSES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(RESPONSES_FILE, "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def match_message_to_request(msg, requests):
    """
    Возвращает список (request, matched_question_n_or_None) для данного сообщения.
    Стратегии матчинга:
      1. reply_to_message_id == request.msg_id → прямой матч
      2. sender в SENDER_MAP совпадает с request.recipient И сообщение в окне
         → кандидат, line-number парсинг определит вопрос
    """
    matches = []
    sender_id = msg.sender_id if msg.sender_id else None
    sender_name = SENDER_MAP.get(sender_id)
    reply_to = msg.reply_to_msg_id if msg.reply_to else None
    msg_time = msg.date.replace(tzinfo=timezone.utc) if msg.date.tzinfo is None else msg.date

    for req in requests:
        # Стратегия 1: прямой reply
        if reply_to and reply_to == req["msg_id"]:
            n = extract_question_number(msg.text or "")
            matches.append((req, n))
            continue

        # Стратегия 2: sender + window
        if sender_name and sender_name == req["recipient"]:
            sent_at = datetime.fromisoformat(req["sent_at"].replace("Z", "+00:00"))
            delta = (msg_time - sent_at).total_seconds() / 60
            if 0 <= delta <= RESPONSE_WINDOW_MIN:
                n = extract_question_number(msg.text or "")
                matches.append((req, n))

    return matches


def extract_question_number(text):
    """Ищет префикс '1 ...', '2. ...', '3) ...' — возвращает int или None."""
    if not text:
        return None
    m = re.match(r"^\s*(\d+)\s*[.,)\-:]?\s+", text)
    if m:
        return int(m.group(1))
    return None


async def process_message(client, msg, source="live"):
    """Обрабатывает одно сообщение: матчит к активным запросам → пишет response."""
    requests = load_active_requests()
    if not requests:
        return

    matches = match_message_to_request(msg, requests)
    if not matches:
        return

    sender = await msg.get_sender()
    sender_name = SENDER_MAP.get(msg.sender_id, getattr(sender, "first_name", "unknown"))

    for req, qn in matches:
        response = {
            "response_id": f"resp_{msg.id}_{req['id']}",
            "request_id": req["id"],
            "msg_id": msg.id,
            "chat_id": msg.chat_id,
            "sender_id": msg.sender_id,
            "sender_name": sender_name,
            "text": msg.text or "",
            "matched_question_n": qn,
            "match_reason": "reply_to" if (msg.reply_to and msg.reply_to.reply_to_msg_id == req["msg_id"]) else "sender_window",
            "received_at": (msg.date.isoformat() if msg.date else datetime.now(timezone.utc).isoformat()),
            "source": source,
            "processed": False,
        }
        append_response(response)
        log(f"✅ matched msg {msg.id} → {req['id']} (q={qn}) text={(msg.text or '')[:80]!r}")


async def run_daemon(client):
    log(f"🚀 listener started, watching chats: {WATCHED_CHATS}")

    @client.on(events.NewMessage(chats=WATCHED_CHATS))
    async def handler(event):
        try:
            await process_message(client, event.message, source="live")
        except Exception as e:
            log(f"ERROR handling msg {event.message.id}: {e}")

    log("listener ready, entering run_until_disconnected")
    await client.run_until_disconnected()


async def run_backfill(client, since_str=None, since_msg_id=None):
    """Backfill: читает историю чата и матчит."""
    log(f"🔄 backfill start: since={since_str} msg_id={since_msg_id}")
    requests = load_active_requests()
    if not requests:
        log("no active requests, nothing to backfill")
        return

    # Найти самый ранний msg_id среди активных
    earliest_msg_id = min(r["msg_id"] for r in requests)

    for chat_id in WATCHED_CHATS:
        async for msg in client.iter_messages(chat_id, min_id=earliest_msg_id, limit=500):
            if since_msg_id and msg.id <= since_msg_id:
                continue
            await process_message(client, msg, source="backfill")
    log("🔄 backfill done")


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--daemon", action="store_true", help="live mode (LaunchAgent)")
    ap.add_argument("--backfill", help="e.g. '2h' — backfill last N hours")
    ap.add_argument("--backfill-msg", type=int, help="backfill messages with id > N")
    args = ap.parse_args()

    client = TelegramClient(SESSION, API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        log("ERROR: not authorized, run telethon-auth.py first")
        return

    try:
        if args.daemon:
            await run_daemon(client)
        elif args.backfill or args.backfill_msg:
            await run_backfill(client, since_str=args.backfill, since_msg_id=args.backfill_msg)
        else:
            ap.print_help()
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
