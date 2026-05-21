#!/usr/bin/env python3
"""
parse_deadline.py — парсер журналистских запросов Deadline.media
================================================================================

Deadline.media — российская HARO-платформа на WordPress, открыт WP REST API:
    https://deadline.media/wp-json/wp/v2/posts?per_page=50&_embed=1

Каждый "пост" = журналистский запрос. Поля API:
    id, title.rendered, content.rendered, excerpt.rendered, date, link,
    categories, tags, _embedded (для автора и медиа)

ВНИМАНИЕ: STUB / TODO — нужна доработка после ручного теста.

TODO:
- [ ] Mapped WP categories → topic_tags (наш формат)
- [ ] Извлечь дедлайн из content.rendered (HTML парсинг)
- [ ] Получить email журналиста (часто в excerpt или последних абзацах)
- [ ] Filter only posts with category-id указывающим на journalist_request
- [ ] Idempotency через ~/.claude/state/press-leadgen-seen.json (key 'deadline')

Usage (когда будет готов):
    python3 parse_deadline.py --since 24h -o /tmp/press-queries-deadline.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from urllib.request import Request, urlopen

API_URL = "https://deadline.media/wp-json/wp/v2/posts"
DEFAULT_UA = "Mozilla/5.0 press-leadgen-russia/1.0"


def fetch_posts(per_page: int = 50) -> list[dict]:
    """Fetch последние посты через WP REST API."""
    url = f"{API_URL}?per_page={per_page}&_embed=1"
    req = Request(url, headers={"User-Agent": DEFAULT_UA})
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Parse Deadline.media journalist requests (STUB)")
    ap.add_argument("--since", default="24h")
    ap.add_argument("-o", "--output", default="/tmp/press-queries-deadline.json")
    ap.add_argument("--smoke", action="store_true", help="Just fetch and dump raw")
    args = ap.parse_args()

    posts = fetch_posts()
    print(f"[deadline] Fetched {len(posts)} raw posts (smoke)", file=sys.stderr)

    # TODO: реальная фильтрация по category + парсинг дедлайна + email-извлечение
    # Сейчас просто сохраняем минимум для проверки доступности API
    out = []
    for p in posts:
        out.append({
            "source": "deadline",
            "id": str(p["id"]),
            "url": p.get("link"),
            "title": p.get("title", {}).get("rendered", "")[:300],
            "outlet": "deadline.media",  # TODO: extract real outlet from content
            "deadline": None,  # TODO: parse from content.rendered
            "topic_tags": [],  # TODO: map p['categories'] via /wp-json/wp/v2/categories
            "body": p.get("content", {}).get("rendered", "")[:5000],
            "posted_at": p.get("date"),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "hash": f"deadline-{p['id']}",
        })

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"RESULT: {json.dumps({'source': 'deadline', 'count': len(out), 'output': args.output, 'status': 'stub'}, ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
