#!/usr/bin/env python3
"""Скачать фото media из 4 контракторских чатов + OCR через Apple Vision
+ match с текстами sheets (174 уник)."""
import asyncio
import re
import json
import subprocess
import unicodedata
import csv
from datetime import datetime, timezone, timedelta
from difflib import SequenceMatcher
from pathlib import Path
from telethon import TelegramClient
from telethon.tl.types import MessageMediaPhoto

API_ID = 35195969
API_HASH = '576ad787126be6f43f28df1a1279aa4a'
SESSION = '/tmp/telethon_contractors'

CHATS = [
    ('okponrussia', 4854296455, 'Отзывы (биржа)'),
    ('blumart-otzyvy', 5113045924, 'Blumart Отзывы'),
    ('kiselev', 1857522687, 'Андрей Киселев DM'),
]

SHEET_BASE = Path.home() / 'artvision-data/clients/blumart/orm/snapshots/latest'
OUT_DIR = Path('/tmp/screens-ocr')
OUT_DIR.mkdir(exist_ok=True)
OCR_SWIFT = str(Path.home() / '.claude/skills/orm-pulse/scripts/macos-ocr.swift')


def norm(s):
    s = unicodedata.normalize('NFKC', (s or '').lower()).replace('ё', 'е')
    return re.sub(r'\s+', ' ', re.sub(r'[^\wа-я0-9 ]+', ' ', s)).strip()


def load_sheet_texts():
    texts = []
    for f in ['sheet1_internal_88304516', 'sheet1_internal_0',
              'sheet2_okponrussia_0', 'sheet2_okponrussia_666154064']:
        p = SHEET_BASE / f'{f}.csv'
        if not p.exists():
            continue
        for r in csv.DictReader(open(p, encoding='utf-8')):
            t = r.get('Текст отзыва', '').strip()
            if t:
                texts.append({'text': t, 'file': f, 'norm': norm(t)})
    seen = set()
    uniq = []
    for t in texts:
        k = t['norm'][:100]
        if k in seen:
            continue
        seen.add(k)
        uniq.append(t)
    return uniq


def ocr_image(path: Path) -> str:
    try:
        r = subprocess.run(['swift', OCR_SWIFT, str(path)],
                           capture_output=True, text=True, timeout=30)
        return r.stdout
    except Exception as e:
        return f'[OCR FAIL: {e}]'


async def pull():
    sheet_texts = load_sheet_texts()
    print(f'📋 Sheet текстов (уник): {len(sheet_texts)}')

    since = datetime.now(timezone.utc) - timedelta(days=30)

    client = TelegramClient(SESSION, API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        print('❌ session expired')
        return

    all_screens = []
    for slug, chat_id, label in CHATS:
        chat_dir = OUT_DIR / slug
        chat_dir.mkdir(exist_ok=True)
        print(f'\n=== {label} (chat {chat_id}) ===')
        photos_count = 0
        async for msg in client.iter_messages(chat_id, limit=2000):
            if msg.date and msg.date < since:
                break
            if not isinstance(msg.media, MessageMediaPhoto):
                continue
            fname = chat_dir / f'{msg.id}.jpg'
            if not fname.exists():
                try:
                    await client.download_media(msg, file=str(fname))
                except Exception as e:
                    print(f'  ⚠️  msg {msg.id}: dl fail {e}')
                    continue
            sender = ''
            if msg.sender:
                sender = (getattr(msg.sender, 'first_name', '') or '')
                last = getattr(msg.sender, 'last_name', '') or ''
                sender = (sender + ' ' + last).strip()
                un = getattr(msg.sender, 'username', '')
                if un:
                    sender += f' (@{un})'
            all_screens.append({
                'chat': slug,
                'chat_id': chat_id,
                'msg_id': msg.id,
                'date': msg.date.isoformat(),
                'sender': sender,
                'caption': (msg.text or '')[:200],
                'path': str(fname),
            })
            photos_count += 1
        print(f'  📷 фото за 30 дней: {photos_count}')

    await client.disconnect()
    print(f'\n📦 Всего скринов: {len(all_screens)}')

    # OCR all
    print('\n🔍 OCR через Apple Vision...')
    for i, sc in enumerate(all_screens, 1):
        if i % 20 == 0:
            print(f'  {i}/{len(all_screens)}')
        ocr_text = ocr_image(Path(sc['path']))
        sc['ocr'] = ocr_text
        sc['ocr_norm'] = norm(ocr_text)

    # Match каждый скрин с sheet текстами
    print('\n🔗 Match скринов с sheet текстами...')
    matched = []
    for sc in all_screens:
        ocr_n = sc['ocr_norm']
        if len(ocr_n) < 50:
            continue
        best_score = 0
        best_st = None
        for st in sheet_texts:
            sn = st['norm']
            # быстрый skip — должны иметь хотя бы 30-symbol overlap
            if not sn:
                continue
            s = SequenceMatcher(None, sn[:200], ocr_n[:500]).ratio()
            if s > best_score:
                best_score = s
                best_st = st
        if best_score >= 0.55:
            matched.append({
                'chat': sc['chat'],
                'msg_id': sc['msg_id'],
                'date': sc['date'][:16],
                'sender': sc['sender'],
                'caption': sc['caption'][:80],
                'sheet_file': best_st['file'] if best_st else '',
                'sheet_text': best_st['text'][:120] if best_st else '',
                'sim': round(best_score, 2),
                'screen_path': sc['path'],
            })

    # Сохранить
    (OUT_DIR / 'screens-index.json').write_text(json.dumps(all_screens, ensure_ascii=False, indent=2))
    (OUT_DIR / 'sheet-matches.json').write_text(json.dumps(matched, ensure_ascii=False, indent=2))

    print(f'\n🎯 СОВПАДЕНИЙ скрин ↔ sheet (sim>=0.55): {len(matched)}')
    for m in matched[:20]:
        print(f'  [{m["chat"]:18s} {m["date"]}] sim={m["sim"]:.2f}  {m["sender"][:25]}')
        print(f'    sheet: {m["sheet_text"][:120]}')

    print(f'\n💾 /tmp/screens-ocr/screens-index.json — все скрины с OCR')
    print(f'💾 /tmp/screens-ocr/sheet-matches.json — совпадения')


asyncio.run(pull())
