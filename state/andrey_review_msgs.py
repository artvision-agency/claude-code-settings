import asyncio, sys
from telethon import TelegramClient
API_ID=35195969; API_HASH='576ad787126be6f43f28df1a1279aa4a'
SESSION='/Users/antonk/.claude/state/telethon_session'
ANDREY=1857522687
KW=['отзыв','выпущ','удал','снят','снял','модерац','опубликов','сравнен','release','review']
async def main():
    c=TelegramClient(SESSION,API_ID,API_HASH); await c.connect()
    if not await c.is_user_authorized(): print("not auth"); sys.exit(1)
    # Andrey's recent text messages in DM mentioning reviews
    print("===== Andrey DM text msgs (review-related, last 1500) =====")
    msgs=await c.get_messages(ANDREY, limit=1500)
    n=0
    for m in msgs:
        if m.sender_id!=ANDREY: continue
        t=(m.text or '')
        if not t: continue
        if any(k in t.lower() for k in KW):
            print(f"  {m.date.strftime('%Y-%m-%d %H:%M')} | {t[:200].replace(chr(10),' ')}")
            n+=1
    print(f"  -- {n} matches --")
    # Also: ALL Andrey docs in last 1500 (any type) with caption — most recent 15
    print("\n===== Andrey ALL docs in DM, most recent 15 =====")
    from telethon.tl.types import MessageMediaDocument, DocumentAttributeFilename
    def fn(d):
        for a in d.attributes:
            if isinstance(a,DocumentAttributeFilename): return a.file_name
        return '('+(d.mime_type or '?')+')'
    cnt=0
    for m in msgs:
        if m.sender_id!=ANDREY: continue
        if not isinstance(m.media, MessageMediaDocument): continue
        f=fn(m.media.document)
        if f.endswith('.ogg'): continue
        print(f"  {m.date.strftime('%Y-%m-%d %H:%M')} | {f} | id={m.id} | {(m.text or '')[:80]}")
        cnt+=1
        if cnt>=15: break
    await c.disconnect()
asyncio.run(main())
