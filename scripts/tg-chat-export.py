#!/usr/bin/env python3
"""
TG Chat Export via Telethon — universal chat history exporter.

Usage:
  python3 tg-chat-export.py --search "Екатерина"          # find chats by name
  python3 tg-chat-export.py --chat-id 954855520            # export by ID
  python3 tg-chat-export.py --chat-id 954855520 --limit 50 # last 50 messages
  python3 tg-chat-export.py --chat-id 954855520 --since 2026-03-01
  python3 tg-chat-export.py --list                         # list all dialogs

Output: markdown table to stdout, or --output file.md
"""

import asyncio
import argparse
import sys
from datetime import datetime, timezone

try:
    from telethon import TelegramClient
    from telethon.tl.types import User, Chat, Channel
except ImportError:
    print("ERROR: pip install telethon", file=sys.stderr)
    sys.exit(1)

API_ID = 35195969
API_HASH = '576ad787126be6f43f28df1a1279aa4a'
SESSION = '/Users/antonk/.claude/state/telethon_session'


async def list_dialogs(client, search=None):
    """List all dialogs, optionally filtered by name."""
    dialogs = await client.get_dialogs(limit=200)
    results = []
    for d in dialogs:
        name = d.name or '(no name)'
        entity = d.entity
        dtype = 'User' if isinstance(entity, User) else 'Group' if isinstance(entity, Chat) else 'Channel' if isinstance(entity, Channel) else 'Unknown'
        eid = d.entity.id

        if search and search.lower() not in name.lower():
            continue

        results.append({'id': eid, 'name': name, 'type': dtype, 'unread': d.unread_count})

    print(f"| ID | Name | Type | Unread |")
    print(f"|----|------|------|--------|")
    for r in results:
        print(f"| {r['id']} | {r['name']} | {r['type']} | {r['unread']} |")
    print(f"\nTotal: {len(results)} dialogs")


async def export_chat(client, chat_id, limit=500, since=None, output=None):
    """Export chat messages as markdown table."""
    kwargs = {'limit': limit}
    if since:
        kwargs['offset_date'] = since

    messages = await client.get_messages(chat_id, **kwargs)

    rows = []
    for m in messages:
        if not m.text and not m.media:
            continue

        sender_name = ""
        if m.sender:
            sender_name = getattr(m.sender, 'first_name', '') or ''
            last = getattr(m.sender, 'last_name', '') or ''
            if last:
                sender_name += ' ' + last

        text = (m.text or '').replace('\n', ' ').replace('|', '\\|').strip()
        if not text and m.media:
            media_type = type(m.media).__name__
            text = f"[{media_type}]"

        if text:
            rows.append({
                'date': m.date.strftime('%Y-%m-%d %H:%M'),
                'sender': sender_name,
                'text': text[:300]
            })

    rows.sort(key=lambda x: x['date'])

    lines = []
    lines.append(f"# TG Chat Export: {chat_id}")
    lines.append(f"**Exported:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**Messages:** {len(rows)}")
    lines.append("")
    lines.append("| Date | Sender | Message |")
    lines.append("|------|--------|---------|")
    for r in rows:
        lines.append(f"| {r['date']} | {r['sender']} | {r['text']} |")

    result = '\n'.join(lines)

    if output:
        with open(output, 'w', encoding='utf-8') as f:
            f.write(result)
        print(f"Saved {len(rows)} messages to {output}", file=sys.stderr)
    else:
        print(result)


async def main():
    parser = argparse.ArgumentParser(description='TG Chat Export via Telethon')
    parser.add_argument('--list', action='store_true', help='List all dialogs')
    parser.add_argument('--search', type=str, help='Search dialogs by name')
    parser.add_argument('--chat-id', type=int, help='Chat ID to export')
    parser.add_argument('--limit', type=int, default=500, help='Max messages (default 500)')
    parser.add_argument('--since', type=str, help='Export since date (YYYY-MM-DD)')
    parser.add_argument('--output', '-o', type=str, help='Output file path')
    args = parser.parse_args()

    client = TelegramClient(SESSION, API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        print("ERROR: Telethon not authorized. Run manual auth first.", file=sys.stderr)
        sys.exit(1)

    try:
        if args.list or args.search:
            await list_dialogs(client, search=args.search)
        elif args.chat_id:
            since = None
            if args.since:
                since = datetime.strptime(args.since, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            await export_chat(client, args.chat_id, limit=args.limit, since=since, output=args.output)
        else:
            parser.print_help()
    finally:
        await client.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
