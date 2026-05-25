#!/usr/bin/env python3
"""
match_local_pages.py — STUB.

Для каждого 404 URL конкурента найти страницу клиента с близкой темой.

Input: broken_urls.csv (url_to, anchor, status_code, ...)
Output: swap_suggestions.csv (broken_url, donor, anchor, local_url, similarity, method)

Methods:
    - tfidf      — TF-IDF similarity между анкором + path-slug 404 и title/h1 клиентских страниц (default)
    - embeddings — embeddings (через voyage-3 / Anthropic / OpenAI), точнее но платно
    - manual     — выгрузить кандидатов в interactive HTML для ручной разметки

TODO:
    1. Получить sitemap.xml клиента (--client-site)
    2. Crawl главных страниц (limit 500) → extract title, h1, meta description, body text
    3. Для каждого 404 url:
       a. Извлечь сигналы: anchor + slug + (опц.) text из Wayback Machine snapshot
       b. Compute similarity vs каждой клиентской страницы
       c. Top-1 если similarity >= 0.3, иначе skip
    4. Output CSV
    5. (опц.) HTML preview для ручной валидации

Acceptance:
    - На тесте с известным mapping (10 broken / 100 клиентских страниц) — precision >= 0.7
    - Запускается на пустом sitemap → graceful "no candidates"

Usage (когда реализовано):
    python3 match_local_pages.py \\
        --broken broken_urls.csv \\
        --client-site https://client-site.ru \\
        --method tfidf \\
        --min-similarity 0.3 \\
        --output swap_suggestions.csv

Связано:
    - SKILL.md шаг 4
    - sklearn (TfidfVectorizer + cosine_similarity)
    - Wayback Machine API (опционально, для извлечения тела старой страницы)
"""

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--broken", required=True)
    parser.add_argument("--client-site", required=True)
    parser.add_argument("--method", choices=["tfidf", "embeddings", "manual"], default="tfidf")
    parser.add_argument("--min-similarity", type=float, default=0.3)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    print(f"[STUB] match_local_pages: {args.broken} → {args.client_site} via {args.method}", file=sys.stderr)
    print("Реализация — следующая сессия. См. TODO в docstring.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
