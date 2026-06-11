#!/usr/bin/env python3
"""
Publish to WordPress with scheduled date via WP REST API.

TODO: реализация. Базовый паттерн:
    POST /wp-json/wp/v2/posts
    {
      "title": "...",
      "content": "...",
      "status": "future",       # scheduled, not 'publish'
      "date": "2026-05-26T09:23:00",
      "slug": "..."
    }

Auth: Application Password или JWT (зависит от установки клиента).

ПРОВЕРЕННАЯ АЛЬТЕРНАТИВА (proven-tools-first):
    wp post create file.html \\
      --post_type=post \\
      --post_status=future \\
      --post_date='2026-05-26 09:23:00' \\
      --post_title='...' \\
      --post_category=123

WP-CLI требует SSH-доступа к серверу клиента, но это «proven» — официальный инструмент.
В большинстве случаев предпочитаем page-publish skill (он уже умеет WP REST).

ИНТЕГРАЦИЯ: этот скрипт — обёртка которая читает schedule.json и для каждого
item.status=scheduled вызывает page-publish или wp-cli. НЕ дублировать REST-логику.

Usage (целевой):
    python3 publish_wp.py --schedule schedule.json --wp-url https://example.com --auth-file ~/.creds/wp.json

Exit codes:
    0 — все scheduled item опубликованы как 'future'
    1 — частичный успех (см. лог)
    2 — конфиг/auth ошибка
"""
import sys

def main() -> int:
    sys.stderr.write(
        "TODO: publish_wp.py — не реализован.\n"
        "Используй: skill /page-publish с input=schedule.json (он уже умеет WP REST).\n"
        "Или WP-CLI: wp post create --post_status=future --post_date='YYYY-MM-DD HH:MM:SS'\n"
    )
    return 0

if __name__ == "__main__":
    sys.exit(main())
