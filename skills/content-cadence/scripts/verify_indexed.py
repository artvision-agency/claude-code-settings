#!/usr/bin/env python3
"""
Verify публикация и индексация статей из schedule.json.

Что должен делать:
    1. Прочитать schedule.json
    2. Для каждого item.status=scheduled и time прошедшего:
       a. curl -sI URL → проверить HTTP 200 (опубликовано?)
       b. Google Search Console URL Inspection API → проверить isIndexed
       c. Если 7+ дней назад опубликовано И НЕ indexed → пометить как rollback
    3. Обновить status в schedule.json:
       - 'scheduled' → 'published' (если 200)
       - 'scheduled' → 'failed' (если 4xx/5xx или таймаут)
       - 'published' → 'indexed' (если GSC подтвердил)
       - 'published' → 'reopen' (если 7+ дней не indexed → переоткрытие в очередь с jitter)
    4. Вывести summary

TODO: реальная реализация через requests + GSC API.

ИНТЕГРАЦИЯ: переиспользовать seo-google skill для GSC URL Inspection.
НЕ дублировать GSC auth.

Usage (целевой):
    python3 verify_indexed.py --schedule schedule.json --gsc-property https://example.com/

Exit codes:
    0 — все OK или published
    1 — есть failed/reopen items (требует внимания)
"""
import sys

def main() -> int:
    sys.stderr.write(
        "TODO: verify_indexed.py — не реализован.\n"
        "Используй: skill /seo-google → GSC URL Inspection для каждого URL из schedule.json.\n"
        "Базовая проверка публикации:\n"
        "  jq -r '.items[] | select(.status==\"scheduled\") | .article' schedule.json | \\\n"
        "    xargs -I{} curl -sI -o /dev/null -w '%{http_code} {}\\n' {}\n"
    )
    return 0

if __name__ == "__main__":
    sys.exit(main())
