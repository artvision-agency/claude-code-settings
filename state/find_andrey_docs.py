#!/usr/bin/env python3
"""Find document attachments from Andrey (@PandaCaffe, id 1857522687) in DM + team chat."""
import asyncio, sys
from telethon import TelegramClient
from telethon.tl.types import MessageMediaDocument, DocumentAttributeFilename

API_ID = 35195969
API_HASH = '576ad787126be6f43f28df1a1279aa4a'
SESSION = '/Users/antonk/.claude/state/telethon_session'

ANDREY_ID = 1857522687
CHATS = {
    'DM-Andrey(@PandaCaffe)': 1857522687,
    'Team-chat': -4273200821,
}

def fname(doc):
    for a in doc.attributes:
        if isinstance(a, DocumentAttributeFilename):
            return a.file_name
    return f"(no-name).{(doc.mime_type or '').split('/')[-1]}"

async def main():
    client = TelegramClient(SESSION, API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        print("ERROR: not authorized", file=sys.stderr); sys.exit(1)
    for label, cid in CHATS.items():
        print(f"\n===== {label} ({cid}) =====")
        try:
            msgs = await client.get_messages(cid, limit=400)
        except Exception as e:
            print(f"  ERROR: {e}"); continue
        found = 0
        for m in msgs:
            if not isinstance(m.media, MessageMediaDocument):
                continue
            sender = m.sender_id
            # only Andrey's docs (in team chat filter by sender)
            who = ''
            if m.sender:
                who = (getattr(m.sender,'first_name','') or '') + ' ' + (getattr(m.sender,'last_name','') or '')
            mark = ' <<ANDREY' if sender == ANDREY_ID else ''
            fn = fname(m.media.document)
            size = m.media.document.size
            cap = (m.text or '').replace('\n',' ')[:120]
            print(f"  {m.date.strftime('%Y-%m-%d %H:%M')} | {who.strip() or sender} | {fn} | {size//1024}KB | id={m.id}{mark}  {cap}")
            found += 1
        print(f"  -- {found} documents in last 400 msgs --")
    await client.disconnect()

asyncio.run(main())
