#!/usr/bin/env python3
"""tg-contractors-monitor — читает переписку всех TG-чатов исполнителей/бирж.

Источник: registry.yaml/contractors[].tg_chat_id + tg_dm_id.
Telethon userbot session: ~/artvision-data/.claude_temp_scripts/tg_userbot.session

Для каждого чата:
1. Читает последние N сообщений (default 50)
2. Извлекает: links reviews.yandex.ru, статус-маркеры ('размещ', 'снесли', '+1', etc)
3. Сохраняет в clients/<slug>/orm/tg-conversations/<contractor>-<date>.json

Запуск: tg-contractors-monitor.py <slug> [--limit 50]
Cron: каждые 30 мин (LaunchAgent)."""

from __future__ import annotations
import argparse, asyncio, json, re, sys
from datetime import datetime
from pathlib import Path
import yaml

ROOT = Path('/Users/antonk/artvision-data')
SESSION_SRC = Path.home() / '.claude/state/telethon_session.session'
# Используем копию session чтобы не конфликтовать с listener daemon (он держит .session).
import shutil
SESSION_COPY = Path('/tmp/tg-contractors-monitor.session')
if SESSION_SRC.exists():
    try:
        shutil.copy2(SESSION_SRC, SESSION_COPY)
    except Exception:
        pass
SESSION = Path(str(SESSION_COPY).rsplit('.session', 1)[0])  # без .session суффикса
TOKENS = ROOT / 'tokens.json'

PUB_MARKERS = ['размещ', 'опубл', '+1', '+2', '+3', 'залетело', 'залетел', 'есть!', 'готово']
REJ_MARKERS = ['снес', 'удал', 'отказ', 'не прошёл', 'не прошел', 'отклон', 'не пропустил']
REQ_MARKERS = ['дайте', 'нужны ещё', 'ждём', 'давай ещё', 'жду', 'ещё текст']


def has_marker(text, markers):
    t = (text or '').lower()
    return [m for m in markers if m in t]


async def fetch_chat(client, chat_id, label, limit):
    msgs = []
    try:
        async for msg in client.iter_messages(int(chat_id), limit=limit):
            text = (msg.text or '').replace(chr(10), ' ').strip()
            if not text:
                continue
            msgs.append({
                'id': msg.id,
                'date': msg.date.isoformat() if msg.date else '',
                'sender_id': msg.sender_id,
                'text': text[:500],
                'pub_markers': has_marker(text, PUB_MARKERS),
                'rej_markers': has_marker(text, REJ_MARKERS),
                'req_markers': has_marker(text, REQ_MARKERS),
                'has_yandex_link': 'reviews.yandex.ru' in text or 'yandex.ru/maps' in text,
            })
    except Exception as e:
        return {'chat_id': chat_id, 'label': label, 'error': str(e)[:200]}
    return {
        'chat_id': chat_id,
        'label': label,
        'fetched_at': datetime.now().isoformat(),
        'count': len(msgs),
        'messages': msgs,
        'summary': {
            'with_pub': sum(1 for m in msgs if m['pub_markers']),
            'with_rej': sum(1 for m in msgs if m['rej_markers']),
            'with_req': sum(1 for m in msgs if m['req_markers']),
            'with_link': sum(1 for m in msgs if m['has_yandex_link']),
        },
    }


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('slug')
    ap.add_argument('--limit', type=int, default=50)
    args = ap.parse_args()

    try:
        from telethon import TelegramClient
    except ImportError:
        sys.exit('pip3 install telethon')

    tok = json.load(open(TOKENS))
    tg = tok.get('telegram', {})
    api_id = tg.get('api_id') or tg.get('userbot_api_id')
    api_hash = tg.get('api_hash') or tg.get('userbot_api_hash')
    if not api_id or not api_hash:
        sys.exit('No telegram api_id/api_hash in tokens.json')

    reg = yaml.safe_load((ROOT / 'clients' / args.slug / 'orm' / 'registry.yaml').read_text())
    targets = []
    for c in reg.get('contractors', []):
        for k in ('tg_chat_id', 'tg_dm_id', 'tg_dialog_id'):
            cid = c.get(k)
            if cid:
                targets.append((cid, c.get('name', '?')))
                break
    print(f'Targets: {len(targets)}')

    client = TelegramClient(str(SESSION), int(api_id), api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        sys.exit('❌ Telethon session expired. Run ~/artvision-data/scripts/tg-reauth.sh')

    out_dir = ROOT / 'clients' / args.slug / 'orm' / 'tg-conversations'
    out_dir.mkdir(parents=True, exist_ok=True)
    date = datetime.now().strftime('%Y-%m-%d-%H%M')

    all_results = []
    for chat_id, label in targets:
        result = await fetch_chat(client, chat_id, label, args.limit)
        all_results.append(result)
        safe = re.sub(r'[^a-zA-Z0-9_-]', '_', label)[:30]
        out_file = out_dir / f'{safe}-{date}.json'
        out_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
        print(f'  {label[:30]:30} count={result.get("count",0)} pub={result.get("summary",{}).get("with_pub",0)} rej={result.get("summary",{}).get("with_rej",0)} req={result.get("summary",{}).get("with_req",0)}')

    # Summary
    index_file = out_dir / f'_index-{date}.json'
    index_file.write_text(json.dumps(all_results, ensure_ascii=False, indent=2))
    print(f'💾 {index_file}')
    await client.disconnect()


if __name__ == '__main__':
    asyncio.run(main())