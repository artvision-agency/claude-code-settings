#!/usr/bin/env python3
"""
draft_response.py — генерация драфта экспертного ответа на журналистский запрос
================================================================================

Логика:
1. Берёт один match (client + query) из /tmp/press-matches.json
2. Читает context environment клиента:
   - clients/<slug>/CLAUDE.md
   - clients/<slug>/config.yaml
   - clients/<slug>/brand-voice/profile.md (если есть)
   - clients/<slug>/cases/*.md (выбирает 1-2 релевантных)
3. Выбирает template из ../templates/ по niche
4. Заполняет: цитата эксперта 2-3 абзаца + bio + 1 dofollow ссылка
5. Сохраняет в clients/<slug>/linkbuilding/press-drafts/<query-id>.md

STUB / TODO — нужна доработка после ручного теста MVP.

TODO:
- [ ] Load match + client context (CLAUDE.md + config.yaml + cases)
- [ ] Select template by client niche (medical/seo/business/realestate/education)
- [ ] Render Jinja-like placeholders {{client_name}}, {{expert_name}}, {{case_stats}}
- [ ] Anti-pattern filter: запретить AI/нейросети упоминания (security.md)
- [ ] Anti-pattern filter: убрать «магические» проценты без источника (challenge-self)
- [ ] Validate: dofollow link 1 раз (не 2+), без UTM-параметров
- [ ] Длина: 150-350 слов основной цитаты + 30-50 слов bio
- [ ] Save draft + meta-JSON (для tracking)

Usage:
    python3 draft_response.py \\
      --match /tmp/press-matches.json \\
      --client <slug> \\
      --query-id <id> \\
      -o ~/artvision-data/clients/<slug>/linkbuilding/press-drafts/<id>.md
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = SKILL_DIR / "templates"

NICHE_TO_TEMPLATE = {
    "медицина": "response-medical.md",
    "стоматология": "response-medical.md",
    "seo": "response-seo.md",
    "маркетинг": "response-seo.md",
    "недвижимость": "response-realestate.md",
    "образование": "response-education.md",
    "b2b": "response-business.md",
}


def pick_template(niches: list[str]) -> Path:
    """Подобрать шаблон по нишам клиента / тегам запроса."""
    for n in niches:
        if n in NICHE_TO_TEMPLATE:
            return TEMPLATES_DIR / NICHE_TO_TEMPLATE[n]
    return TEMPLATES_DIR / "response-business.md"


def main() -> int:
    ap = argparse.ArgumentParser(description="Draft press response (STUB)")
    ap.add_argument("--match", required=True, help="press-matches.json")
    ap.add_argument("--client", required=True, help="client slug")
    ap.add_argument("--query-id", help="specific query id (else first match)")
    ap.add_argument("-o", "--output", help="output draft path")
    args = ap.parse_args()

    with open(args.match) as f:
        matches = json.load(f)

    # Filter to this client
    client_matches = [m for m in matches if m.get("client") == args.client]
    if args.query_id:
        client_matches = [m for m in client_matches if str(m.get("query_id")) == str(args.query_id)]
    if not client_matches:
        print(f"[draft] No matches for client={args.client} query={args.query_id}", file=sys.stderr)
        return 1

    m = client_matches[0]
    # TODO: реально load client context + cases + brand-voice
    # TODO: рендерить шаблон
    # TODO: factcheck integration (числа из cases)

    template_path = pick_template([])  # TODO: pass real niches
    if not template_path.exists():
        print(f"[draft] Template missing: {template_path}", file=sys.stderr)
        return 2

    draft_body = template_path.read_text(encoding="utf-8")
    draft_body = (
        f"# DRAFT (STUB) — {m.get('query_title', '')}\n\n"
        f"**Query URL:** {m.get('query_url', '')}\n"
        f"**Score:** {m.get('score')} ({', '.join(m.get('signals', []))})\n"
        f"**Client:** {args.client}\n"
        f"**Source:** {m.get('query_source')}\n\n"
        f"---\n\n"
        f"## Template ({template_path.name})\n\n"
        f"{draft_body}\n\n"
        f"---\n"
        f"TODO: реальная генерация на основе clients/{args.client}/cases/*.md + brand-voice profile.\n"
    )

    out_path = Path(args.output) if args.output else (
        Path.home() / "artvision-data" / "clients" / args.client / "linkbuilding"
        / "press-drafts" / f"{m.get('query_id')}.md"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(draft_body, encoding="utf-8")
    print(f"RESULT: {json.dumps({'client': args.client, 'query_id': m.get('query_id'), 'draft': str(out_path), 'status': 'stub'}, ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
