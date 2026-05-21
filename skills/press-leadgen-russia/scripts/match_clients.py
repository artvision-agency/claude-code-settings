#!/usr/bin/env python3
"""
match_clients.py — матчинг журналистских запросов под клиентов Artvision
================================================================================

Читает:
1. /tmp/press-queries-*.json (output из parse_*.py)
2. ~/artvision-data/clients/*/config.yaml — каждого активного клиента

Для каждого (query, client):
- Считает relevance score по пересечению keywords
- Применяет бонусы (DR outlet, регион, дедлайн)
- Возвращает только matches с score >= 5

Output: /tmp/press-matches.json — array объектов:
    {client: <slug>, query: <full query obj>, score: <int>, signals: [<list>]}

STUB / TODO — требует доработки.

TODO:
- [ ] Read clients/*/config.yaml (YAML) — нужен PyYAML или ручной парсер
- [ ] Extract fields: name, niche, segment, region, expertise, target_keywords
- [ ] Build keyword set per client (включая synonyms)
- [ ] Keyword match: simple intersection + jaccard
- [ ] DR-bonus: проверка outlet против списка DR70+ медиа
- [ ] Region-bonus: spb_keywords/msk_keywords совпадают с client.region
- [ ] Deadline filter: < 6h = skip, > 24h = +2 бонус
- [ ] Blacklist filter (templates/blacklist-outlets.txt)
- [ ] Output sorted by score desc

Usage:
    python3 match_clients.py \\
      --queries /tmp/press-queries-pressfeed.json /tmp/press-queries-deadline.json \\
      --clients-dir ~/artvision-data/clients/ \\
      -o /tmp/press-matches.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


DR70_OUTLETS = {
    # outlet name patterns → DR score bonus weight
    "forbes": 3, "rbc": 3, "rbk": 3, "коммерсант": 3, "kommersant": 3, "vedomosti": 3,
    "ведомости": 3, "vc.ru": 3, "habr": 3, "хабр": 3, "sostav": 2, "cossa": 2,
    "rusbase": 2, "rb.ru": 2, "vademec": 2, "medvestnik": 2, "seonews": 2,
    "searchengines": 2, "интернетурок": 1,  # niche-relevant ones
}


def load_queries(paths: list[str]) -> list[dict]:
    all_q = []
    for p in paths:
        path = Path(p)
        if not path.exists():
            print(f"[match] WARN: {p} not found, skipping", file=sys.stderr)
            continue
        with open(path) as f:
            all_q.extend(json.load(f))
    return all_q


def load_clients(clients_dir: Path) -> list[dict]:
    """TODO: parse clients/*/config.yaml.
    Минимум нужны поля: slug (from dir name), niche, segment, region, keywords."""
    clients = []
    if not clients_dir.exists():
        print(f"[match] ERROR: {clients_dir} not found", file=sys.stderr)
        return clients
    # TODO: YAML parser. Пока что заглушка-шаблон
    for sub in sorted(clients_dir.iterdir()):
        if not sub.is_dir():
            continue
        cfg = sub / "config.yaml"
        if not cfg.exists():
            continue
        # STUB: возвращаем minimal client object для каркаса
        clients.append({
            "slug": sub.name,
            "config_path": str(cfg),
            # TODO: распарсить yaml
            "niche": [],
            "region": None,
            "keywords": [],
        })
    return clients


def score_match(query: dict, client: dict) -> tuple[int, list[str]]:
    """TODO: реальная логика скоринга.
    Возвращает (score, signals_used)."""
    score = 0
    signals = []

    # Базовый скор: пересечение topic_tags запроса с niche клиента
    q_tags = set(query.get("topic_tags", []))
    c_niche = set(client.get("niche", []))
    overlap = q_tags & c_niche
    if overlap:
        score += len(overlap) * 2
        signals.append(f"niche_overlap={list(overlap)}")

    # Бонус за DR outlet
    outlet_lower = (query.get("outlet") or "").lower()
    for pattern, bonus in DR70_OUTLETS.items():
        if pattern in outlet_lower:
            score += bonus
            signals.append(f"dr_outlet={pattern}+{bonus}")
            break

    # TODO: region match, deadline check, blacklist, brand-voice keyword overlap
    return score, signals


def main() -> int:
    ap = argparse.ArgumentParser(description="Match queries to clients (STUB)")
    ap.add_argument("--queries", nargs="+", required=True, help="JSON files from parse_*.py")
    ap.add_argument("--clients-dir", default=str(Path.home() / "artvision-data" / "clients"))
    ap.add_argument("-o", "--output", default="/tmp/press-matches.json")
    ap.add_argument("--min-score", type=int, default=5)
    args = ap.parse_args()

    queries = load_queries(args.queries)
    clients = load_clients(Path(args.clients_dir).expanduser())
    print(f"[match] Loaded {len(queries)} queries × {len(clients)} clients", file=sys.stderr)

    matches = []
    for q in queries:
        for c in clients:
            score, signals = score_match(q, c)
            if score >= args.min_score:
                matches.append({
                    "client": c["slug"],
                    "score": score,
                    "signals": signals,
                    "query_id": q.get("id"),
                    "query_source": q.get("source"),
                    "query_title": q.get("title"),
                    "query_url": q.get("url"),
                })
    matches.sort(key=lambda m: m["score"], reverse=True)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(matches, f, ensure_ascii=False, indent=2)
    print(f"RESULT: {json.dumps({'matches': len(matches), 'output': args.output, 'status': 'stub'}, ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
