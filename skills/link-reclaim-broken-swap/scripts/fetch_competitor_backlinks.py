#!/usr/bin/env python3
"""
fetch_competitor_backlinks.py — STUB.

Получить список backlinks конкурента через API (DataForSEO/keys.so/Ahrefs/SEMrush/Common Crawl).

Output CSV: url_from, url_to, anchor, dr, traffic, last_seen

TODO:
    1. Реализовать fetch через DataForSEO MCP (см. skill `seo-dataforseo`):
       - Endpoint: backlinks/backlinks/live
       - target: competitor.com
       - filters: dofollow=true, broken=False (на этом этапе берём ВСЕ, фильтр позже)
    2. Fallback keys.so (для рунета):
       - Endpoint: https://api.keys.so/backlinks
       - Токен: tokens.json → keys_so.api_key (TBD проверить наличие)
    3. Fallback Common Crawl:
       - URL: http://index.commoncrawl.org/CC-MAIN-XXXX-XX-index?url=*.competitor.com
       - Парсить index, экстрактить inbound links (медленно, но бесплатно)
    4. Normalize output формат (CSV с 6 колонками выше)
    5. Дедуп по (url_from, url_to)

Usage (когда реализовано):
    python3 fetch_competitor_backlinks.py \\
        --competitor competitor.com \\
        --source dataforseo \\
        --output backlinks.csv \\
        --limit 1000

Связано:
    - SKILL.md шаг 1
    - skill seo-dataforseo
    - tokens.json (keys_so, dataforseo если есть)
"""

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--competitor", required=True)
    parser.add_argument("--source", choices=["dataforseo", "keys-so", "ahrefs", "semrush", "commoncrawl"],
                        default="dataforseo")
    parser.add_argument("--output", required=True)
    parser.add_argument("--limit", type=int, default=1000)
    args = parser.parse_args()

    print(f"[STUB] fetch_competitor_backlinks for {args.competitor} via {args.source}", file=sys.stderr)
    print("Реализация — следующая сессия. См. TODO в docstring.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
