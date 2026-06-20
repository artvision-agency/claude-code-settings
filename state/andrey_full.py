import asyncio, sys
from telethon import TelegramClient
API_ID=35195969; API_HASH='576ad787126be6f43f28df1a1279aa4a'
SESSION='/Users/antonk/.claude/state/telethon_session'
ANDREY=1857522687
async def main():
    c=TelegramClient(SESSION,API_ID,API_HASH); await c.connect()
    msgs=await c.get_messages(ANDREY, limit=1500)
    # full text of Andrey msgs on 2026-06-16 about reviews
    for m in sorted([x for x in msgs if x.sender_id==ANDREY and x.text and x.date.strftime('%Y-%m-%d')=='2026-06-16'], key=lambda x:x.date):
        t=m.text
        if any(k in t.lower() for k in ['отзыв','размещ','опубликов','удал','жалоб','115','85','21','80','перепровер']):
            print(f"--- {m.date.strftime('%m-%d %H:%M')} id={m.id} ---")
            print(t)
            print()
    await c.disconnect()
asyncio.run(main())
