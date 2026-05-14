#!/usr/bin/env python3
"""
orm-pulse: Telethon export релевантных чатов клиента через клон-сессию.
Не блокирует listener.

Usage: tg-export-clone.py <client_slug> [--days N]
"""
import sys
import shutil
import asyncio
import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta

import yaml
from telethon import TelegramClient
from telethon.tl.types import User, Chat, Channel

sys.path.insert(0, str(Path(__file__).parent))
from lib.config import ROOT  # noqa: E402

API_ID = 35195969
API_HASH = '576ad787126be6f43f28df1a1279aa4a'
ORIG_SESSION = Path.home() / ".claude/state/telethon_session.session"


def load_registry(slug: str) -> dict:
    path = ROOT / "clients" / slug / "orm" / "registry.yaml"
    if not path.exists():
        print(f"❌ Registry not found: {path}", file=sys.stderr)
        sys.exit(1)
    return yaml.safe_load(path.read_text())


async def export_chat(client: TelegramClient, chat_id: int, label: str, since: datetime, out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# TG Chat Export: {chat_id} ({label})", f"**Period:** since {since.isoformat()}", "", "| Date | Sender | Reply-to | Message |", "|------|--------|----------|---------|"]

    count = 0
    try:
        async for msg in client.iter_messages(chat_id, offset_date=None, reverse=False):
            if msg.date < since:
                break
            sender = ""
            if msg.sender:
                if isinstance(msg.sender, User):
                    sender = msg.sender.first_name or ""
                    if msg.sender.username:
                        sender = f"{sender} (@{msg.sender.username})"
                else:
                    sender = getattr(msg.sender, 'title', '') or ''
            text = (msg.message or "[Media]").replace("|", "/").replace("\n", " / ")
            if len(text) > 500:
                text = text[:500] + "…"
            reply_to = msg.reply_to_msg_id or ""
            lines.append(f"| {msg.date.strftime('%Y-%m-%d %H:%M')} | {sender} | {reply_to} | {text} |")
            count += 1
    except Exception as e:
        lines.append(f"| ERROR | — | — | {e} |")

    out_path.write_text("\n".join(lines) + "\n")
    return count


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("slug", help="Client slug (e.g. bluemart)")
    parser.add_argument("--days", type=int, default=14, help="Days back to export (default 14)")
    args = parser.parse_args()

    registry = load_registry(args.slug)
    chats = registry.get("tg_chats", {})
    if not chats:
        print("⚠️  No tg_chats in registry", file=sys.stderr)
        sys.exit(0)

    # Клонируем сессию чтобы не блокировать listener
    clone_session = Path(f"/tmp/tl-orm-{args.slug}.session")
    if not clone_session.exists() or clone_session.stat().st_mtime < ORIG_SESSION.stat().st_mtime:
        shutil.copy2(ORIG_SESSION, clone_session)

    out_dir = Path("/tmp/orm-pulse") / args.slug / "tg"
    out_dir.mkdir(parents=True, exist_ok=True)

    since = datetime.now(timezone.utc) - timedelta(days=args.days)

    client = TelegramClient(str(clone_session.with_suffix("")), API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        print("❌ Telethon clone not authorized", file=sys.stderr)
        sys.exit(2)

    summary = []
    for key, chat_def in chats.items():
        chat_id = chat_def.get("chat_id")
        label = chat_def.get("label", key)
        out_path = out_dir / f"{chat_id}_{key}.md"
        print(f"→ {key} ({chat_id}) {label}")
        n = await export_chat(client, chat_id, label, since, out_path)
        summary.append((key, chat_id, n, out_path))

    await client.disconnect()

    # Summary
    print(f"\n✅ Exported {len(summary)} chats to {out_dir}")
    print(f"\n| Chat | id | Messages | File |")
    print(f"|------|-----|---------:|------|")
    for key, cid, n, p in summary:
        print(f"| {key} | {cid} | {n} | {p.name} |")


if __name__ == "__main__":
    asyncio.run(main())
