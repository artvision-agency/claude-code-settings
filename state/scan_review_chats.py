import asyncio, sys
from telethon import TelegramClient
from telethon.tl.types import MessageMediaDocument, DocumentAttributeFilename
API_ID=35195969; API_HASH='576ad787126be6f43f28df1a1279aa4a'
SESSION='/Users/antonk/.claude/state/telethon_session'
CHATS={'Blumart Отзывы':5113045924,'Отзывы/Группа':4854296455,'Отзывы от Smaylik_':5598821983,'Blumart (AVpro)':5169370651}
def fname(doc):
    for a in doc.attributes:
        if isinstance(a, DocumentAttributeFilename): return a.file_name
    return '(no-name)'
async def main():
    c=TelegramClient(SESSION,API_ID,API_HASH); await c.connect()
    if not await c.is_user_authorized(): print("not auth",file=sys.stderr); sys.exit(1)
    for label,cid in CHATS.items():
        print(f"\n===== {label} ({cid}) — documents =====")
        try: msgs=await c.get_messages(cid, limit=500)
        except Exception as e: print("  ERR",e); continue
        n=0
        for m in msgs:
            if not isinstance(m.media, MessageMediaDocument): continue
            fn=fname(m.media.document)
            if fn.endswith('.ogg'): continue
            who=''
            if m.sender: who=((getattr(m.sender,'first_name','') or '')+' '+(getattr(m.sender,'last_name','') or '')).strip()
            cap=(m.text or '').replace('\n',' ')[:90]
            print(f"  {m.date.strftime('%Y-%m-%d %H:%M')} | {who or m.sender_id} | {fn} | {m.media.document.size//1024}KB | id={m.id}  {cap}")
            n+=1
        print(f"  -- {n} non-voice docs --")
    await c.disconnect()
asyncio.run(main())
