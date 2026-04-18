#!/usr/bin/env python3
"""Telethon re-authorization script. Run interactively in terminal."""
import asyncio, json

from telethon import TelegramClient

with open('/Users/antonk/artvision-data/tokens.json') as f:
    tokens = json.load(f)

api_id = tokens['telegram']['api_id']
api_hash = tokens['telegram']['api_hash']
SESSION = '/Users/antonk/.claude/state/telethon_session'

async def main():
    client = TelegramClient(SESSION, api_id, api_hash)
    await client.start()
    me = await client.get_me()
    print(f"\n✅ Авторизован как: {me.first_name} ({me.phone})")
    print(f"Session saved: {SESSION}.session")
    
    # Quick test
    msg = await client.get_messages('seo_uravnitel', ids=233)
    if msg:
        print(f"\n--- TEST: seo_uravnitel/233 ---")
        print(msg.text[:500] if msg.text else "No text")
    
    await client.disconnect()

asyncio.run(main())
