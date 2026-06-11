#!/usr/bin/env python3
"""
parse_tg_journalist.py — парсер TG-канала @jouroffer (Журналист Запрос)
================================================================================

Использует ту же Telethon-инфру что и skill tg-chat-export:
    ~/.claude/scripts/tg-chat-export.py (Telethon session, phone +79110861888)

STUB / TODO — требует доработки.

TODO:
- [ ] Импортировать Telethon session из ~/.claude/state/telethon_session
- [ ] Resolve @jouroffer chat_id (через client.get_entity('jouroffer'))
- [ ] Iterate messages с --since фильтром
- [ ] Parse каждое сообщение в формат query (как pressfeed)
- [ ] @jouroffer формат: обычно "СМИ: <название>\nТема: ...\nДедлайн: ...\nКонтакт: @username"
- [ ] Извлечь outlet, topic, deadline, contact из структуры
- [ ] Idempotency через state-file (key 'jouroffer')
- [ ] Alternative: использовать t.me/s/jouroffer (TG preview, без auth) — если канал public

Альтернатива для MVP (БЕЗ Telethon):
- Использовать t.me/s/jouroffer как parse_pressfeed.py — public preview если канал public
- Проверить доступность: curl -I https://t.me/s/jouroffer

Usage (когда будет готов):
    python3 parse_tg_journalist.py --since 24h -o /tmp/press-queries-jouroffer.json
"""

from __future__ import annotations

import argparse
import json
import sys


def main() -> int:
    ap = argparse.ArgumentParser(description="Parse @jouroffer TG channel (STUB)")
    ap.add_argument("--since", default="24h")
    ap.add_argument("-o", "--output", default="/tmp/press-queries-jouroffer.json")
    args = ap.parse_args()

    # TODO: реализовать через Telethon ИЛИ t.me/s/jouroffer preview
    out: list[dict] = []
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"RESULT: {json.dumps({'source': 'jouroffer', 'count': 0, 'output': args.output, 'status': 'stub'}, ensure_ascii=False)}")
    print("[jouroffer] STUB — реализация через Telethon (см. tg-chat-export.py) или t.me/s/jouroffer preview", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
