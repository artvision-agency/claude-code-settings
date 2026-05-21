#!/usr/bin/env python3
"""
Publish to MODX via Playwright (как в page-publish skill).

TODO: реализация. Базовый паттерн:
    1. Playwright login в /manager/
    2. Создать ресурс (resource/create)
    3. Заполнить TV (template variables) для template статьи блога
    4. Выставить pub_date = scheduled time (MODX поддерживает отложенную публикацию через pub_date)
    5. published=0, pub_date=future → MODX опубликует автоматически

Альтернатива через MODX REST API (если ContentBlocks/REST extra установлен):
    POST /rest/resource
    {"pagetitle": "...", "content": "...", "pub_date": "2026-05-26 09:23:00", "published": 0}

ИНТЕГРАЦИЯ: переиспользовать page-publish skill (раздел MODX).
НЕ дублировать Playwright-логику логина.

Usage (целевой):
    python3 publish_modx.py --schedule schedule.json --modx-url https://example.com/manager/

Exit codes как в publish_wp.py
"""
import sys

def main() -> int:
    sys.stderr.write(
        "TODO: publish_modx.py — не реализован.\n"
        "Используй: skill /page-publish с input=schedule.json и cms=modx.\n"
        "MODX поддерживает pub_date в будущем + published=0 → автопубликация.\n"
    )
    return 0

if __name__ == "__main__":
    sys.exit(main())
