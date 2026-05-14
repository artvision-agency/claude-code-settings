#!/usr/bin/env python3
"""tg-discover-serm — поиск SERM/ORM каналов и групп через Telethon.

Что делает:
1. Через Telethon ищет публичные каналы по SERM/ORM-keywords
2. Опционально: join + scan пары последних сообщений для классификации
3. Сохраняет результаты в clients/<slug>/orm/tg-discover/

Usage:
  tg-discover-serm.py <client_slug> [--keywords ...] [--join] [--days N]

Defaults:
  --keywords  serm,отзыв,накрутк,модерац,reputation,рейтинг,карт,репутац
  --join      false (только search, без join — безопасный режим)
  --days      30  (если --join — сколько дней истории забирать)

Output:
  clients/<slug>/orm/tg-discover/discovered-<date>.json — найденные каналы
  clients/<slug>/orm/tg-discover/<channel>_<id>.md — content (если --join)
"""
from __future__ import annotations
import argparse
import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).parent))
from lib.config import ROOT  # noqa: E402

SKILLS_ROOT = Path.home() / ".claude" / "skills" / "orm-pulse"
ORIG_SESSION = Path.home() / ".claude/state/telethon_session.session"
CLONE_SESSION = SKILLS_ROOT / "state" / "telethon_session_discover.session"

DEFAULT_KEYWORDS = [
    "serm", "сёрм", "серм",
    "отзыв",
    "накрутк", "накрут",
    "модерац",
    "reputation", "репутац",
    "рейтинг",
    "карт яндекс", "yandex map",
    "orm",
    "biржа отзыв",
]


def load_telethon():
    try:
        from telethon import TelegramClient
        from telethon.tl.functions.contacts import SearchRequest
        from telethon.tl.functions.channels import GetFullChannelRequest, JoinChannelRequest
        from telethon.tl.functions.messages import SearchGlobalRequest
        from telethon.tl.types import InputMessagesFilterEmpty
        return {
            "TelegramClient": TelegramClient,
            "SearchRequest": SearchRequest,
            "GetFullChannelRequest": GetFullChannelRequest,
            "JoinChannelRequest": JoinChannelRequest,
            "SearchGlobalRequest": SearchGlobalRequest,
            "InputMessagesFilterEmpty": InputMessagesFilterEmpty,
        }
    except ImportError:
        sys.exit("ERROR: telethon not installed. pip install telethon")


def load_telegram_creds() -> tuple[int, str]:
    tokens = json.loads((ROOT / "tokens.json").read_text())
    tg = tokens.get("telegram", {})
    api_id = tg.get("api_id") or tg.get("API_ID")
    api_hash = tg.get("api_hash") or tg.get("API_HASH")
    if not api_id or not api_hash:
        sys.exit("ERROR: tokens.json missing telegram.api_id/api_hash")
    return int(api_id), api_hash


async def discover(slug: str, keywords: list[str], do_join: bool, days: int,
                   global_search: bool, scan_subs: bool):
    tl = load_telethon()
    TelegramClient = tl["TelegramClient"]
    SearchRequest = tl["SearchRequest"]
    SearchGlobalRequest = tl["SearchGlobalRequest"]
    InputMessagesFilterEmpty = tl["InputMessagesFilterEmpty"]
    api_id, api_hash = load_telegram_creds()

    out_dir = ROOT / "clients" / slug / "orm" / "tg-discover"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Клон-сессия чтобы не блокировать listener
    CLONE_SESSION.parent.mkdir(parents=True, exist_ok=True)
    if ORIG_SESSION.exists() and not CLONE_SESSION.exists():
        import shutil as _sh
        _sh.copy(ORIG_SESSION, CLONE_SESSION)
    client = TelegramClient(str(CLONE_SESSION).replace(".session", ""), api_id, api_hash)
    await client.start()

    discovered: dict[str, dict] = {}
    for kw in keywords:
        try:
            res = await client(SearchRequest(q=kw, limit=20))
        except Exception as e:
            print(f"  ⚠️  search '{kw}' failed: {e}", file=sys.stderr)
            continue
        for chat in res.chats:
            cid = getattr(chat, "id", None)
            if not cid:
                continue
            key = str(cid)
            if key in discovered:
                discovered[key]["matched_keywords"].append(kw)
                continue
            discovered[key] = {
                "id": cid,
                "title": getattr(chat, "title", None),
                "username": getattr(chat, "username", None),
                "type": type(chat).__name__,
                "verified": getattr(chat, "verified", False),
                "scam": getattr(chat, "scam", False),
                "fake": getattr(chat, "fake", False),
                "participants_count": getattr(chat, "participants_count", None),
                "matched_keywords": [kw],
            }
        # also users (могут быть индив. SERM-консультанты)
        for user in res.users:
            uid = getattr(user, "id", None)
            if not uid:
                continue
            uname = getattr(user, "username", None)
            if not uname:
                continue
            key = f"user:{uid}"
            if key in discovered:
                discovered[key]["matched_keywords"].append(kw)
                continue
            discovered[key] = {
                "id": uid,
                "type": "User",
                "username": uname,
                "first_name": getattr(user, "first_name", None),
                "last_name": getattr(user, "last_name", None),
                "verified": getattr(user, "verified", False),
                "matched_keywords": [kw],
            }

    print(f"\n✓ Stage 1 (channel search): {len(discovered)} entities across {len(keywords)} keywords")

    # Stage 2: Global message search — найти сообщения по keyword в любых чатах
    global_msgs: list[dict] = []
    if global_search:
        for kw in keywords[:5]:  # cap 5 keywords для скорости
            try:
                res = await client(SearchGlobalRequest(
                    q=kw,
                    filter=InputMessagesFilterEmpty(),
                    min_date=None, max_date=None,
                    offset_rate=0, offset_peer="me", offset_id=0, limit=20,
                ))
                for msg in res.messages:
                    if not getattr(msg, "message", None):
                        continue
                    global_msgs.append({
                        "kw": kw,
                        "msg_id": msg.id,
                        "chat_id": getattr(msg.peer_id, "channel_id", None) or
                                   getattr(msg.peer_id, "user_id", None) or
                                   getattr(msg.peer_id, "chat_id", None),
                        "date": msg.date.isoformat() if msg.date else None,
                        "text": msg.message[:300],
                    })
            except Exception as e:
                print(f"  ⚠️  global search '{kw}' failed: {e}", file=sys.stderr)
        print(f"✓ Stage 2 (global message search): {len(global_msgs)} messages")

    # Stage 3: Scan собственных подписок — найти SERM-каналы где уже подписан
    sub_matches: list[dict] = []
    if scan_subs:
        kw_lower = [k.lower() for k in keywords]
        try:
            async for dialog in client.iter_dialogs(limit=500):
                title = (dialog.title or "").lower()
                hits = [k for k in kw_lower if k in title]
                if hits:
                    sub_matches.append({
                        "id": dialog.id,
                        "title": dialog.title,
                        "username": getattr(dialog.entity, "username", None),
                        "type": type(dialog.entity).__name__,
                        "unread_count": dialog.unread_count,
                        "matched_keywords": hits,
                    })
            print(f"✓ Stage 3 (subscriptions scan): {len(sub_matches)} matches in user dialogs")
        except Exception as e:
            print(f"  ⚠️  scan subs failed: {e}", file=sys.stderr)

    # Save
    stamp = datetime.now().strftime("%Y-%m-%d-%H%M")
    discover_path = out_dir / f"discovered-{stamp}.json"
    with open(discover_path, "w", encoding="utf-8") as f:
        json.dump({
            "ts": datetime.now().isoformat(),
            "stage1_channel_search": list(discovered.values()),
            "stage2_global_msg_search": global_msgs,
            "stage3_subscription_matches": sub_matches,
        }, f, ensure_ascii=False, indent=2)
    print(f"💾 {discover_path}")

    # Optional: join + scan
    if do_join:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        for entity in list(discovered.values())[:30]:  # cap 30
            if entity.get("type") == "User":
                continue  # users не joinим
            uname = entity.get("username") or entity.get("id")
            try:
                msgs = []
                async for msg in client.iter_messages(uname, limit=200):
                    if msg.date < cutoff:
                        break
                    if msg.text:
                        msgs.append({
                            "date": msg.date.isoformat(),
                            "sender": str(getattr(msg.sender, "first_name", "") or msg.sender_id),
                            "text": msg.text[:500],
                        })
                if msgs:
                    safe_name = str(uname).replace("/", "_")
                    out_path = out_dir / f"{safe_name}.md"
                    out_path.write_text(
                        f"# {entity.get('title', uname)} (id={entity['id']})\n"
                        f"**Username**: @{entity.get('username', '?')}\n"
                        f"**Matched keywords**: {entity['matched_keywords']}\n"
                        f"**Messages last {days}d**: {len(msgs)}\n\n"
                        + "\n".join(f"## {m['date']} ({m['sender']})\n{m['text']}\n" for m in msgs)
                    )
                    print(f"  ✓ {safe_name} ({len(msgs)} msgs)")
            except Exception as e:
                print(f"  ⚠️  join {uname} failed: {e}", file=sys.stderr)

    await client.disconnect()
    return discovered


def main():
    parser = argparse.ArgumentParser(description="Discover SERM/ORM channels via Telethon")
    parser.add_argument("client")
    parser.add_argument("--keywords", help="comma-separated", default=",".join(DEFAULT_KEYWORDS))
    parser.add_argument("--join", action="store_true", help="join+scan top channels")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--global-search", action="store_true",
                        help="искать сообщения по keyword глобально (не только заголовки каналов)")
    parser.add_argument("--scan-subs", action="store_true",
                        help="сканировать свои подписки на match keywords")
    args = parser.parse_args()

    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    asyncio.run(discover(args.client, keywords, args.join, args.days,
                         args.global_search, args.scan_subs))


if __name__ == "__main__":
    main()
