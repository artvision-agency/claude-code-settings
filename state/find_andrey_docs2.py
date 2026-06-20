import asyncio, sys
from telethon import TelegramClient
from telethon.tl.types import MessageMediaDocument, DocumentAttributeFilename
API_ID=35195969; API_HASH='576ad787126be6f43f28df1a1279aa4a'
SESSION='/Users/antonk/.claude/state/telethon_session'
ANDREY_ID=1857522687
def fname(doc):
    for a in doc.attributes:
        if isinstance(a, DocumentAttributeFilename): return a.file_name
    return '(no-name)'
async def main():
    c=TelegramClient(SESSION,API_ID,API_HASH); await c.connect()
    if not await c.is_user_authorized(): print("not auth",file=sys.stderr); sys.exit(1)
    # 1) ALL docs from Andrey in DM, deep history
    print("===== Andrey docs in DM (deep, non-voice non-image) =====")
    msgs=await c.get_messages(1857522687, limit=2000)
    n=0
    for m in msgs:
        if not isinstance(m.media, MessageMediaDocument): continue
        if m.sender_id != ANDREY_ID: continue
        fn=fname(m.media.document); mt=m.media.document.mime_type or ''
        if fn.endswith('.ogg'): continue
        cap=(m.text or '').replace('\n',' ')[:100]
        print(f"  {m.date.strftime('%Y-%m-%d %H:%M')} | {fn} | {mt} | {m.media.document.size//1024}KB | id={m.id}  {cap}")
        n+=1
    print(f"  -- {n} Andrey non-voice docs --")
    # 2) list dialogs matching orm/blumart/отзыв/блюмарт
    print("\n===== Dialogs (orm/blumart/отзыв/review) =====")
    async for d in c.iter_dialogs(limit=300):
        nm=(d.name or '').lower()
        if any(k in nm for k in ['orm','blumart','блюмарт','отзыв','review','репутац']):
            print(f"  {d.entity.id} | {d.name}")
    await c.disconnect()
asyncio.run(main())
