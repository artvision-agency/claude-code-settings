#!/usr/bin/env python3
"""
orm-pulse: Compose STATUS-ALL.md из всех собранных данных.

Usage: compose-status.py <client_slug> [--public]
"""
import sys
import json
import argparse
import csv
from pathlib import Path
from datetime import datetime
from collections import Counter

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from lib.config import ROOT  # noqa: E402


def load_registry(slug: str) -> dict:
    return yaml.safe_load((ROOT / "clients" / slug / "orm" / "registry.yaml").read_text())


def load_json(path: Path, default=None):
    if not path.exists():
        return default if default is not None else []
    return json.loads(path.read_text())


def render_status(slug: str, public: bool = False) -> str:
    registry = load_registry(slug)
    base = Path("/tmp/orm-pulse") / slug

    # Reconcile data
    report = load_json(base / "reconcile" / "report.json", {})
    buckets = load_json(base / "reconcile" / "buckets.json", {})
    signals = load_json(base / "reconcile" / "signals.json", {})
    discrepancies = load_json(base / "reconcile" / "discrepancies.json", [])
    matched = load_json(base / "match" / "matched.json", [])

    # Distribution by month for matched live
    by_month = Counter()
    for m in matched:
        date = m.get("live", {}).get("date", "")
        if date.startswith("2026-03"):
            by_month["март"] += 1
        elif date.startswith("2026-04"):
            by_month["апрель"] += 1
        elif date.startswith("2026-05"):
            by_month["май"] += 1

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M МСК")
    title = f"# {registry.get('client_full_name', slug)} ORM — Статус"

    lines = [title, ""]
    if public:
        lines.append("> **Публичная версия для отчёта** (без исполнителей и цен)")
    else:
        lines.append("> **INTERNAL** — содержит исполнителей и цены")
    lines.append(f"> Сгенерировано: {timestamp}")
    lines.append(f"> Скилл: `/orm-pulse {slug}`")
    lines.append("")

    # 1. Площадка
    pl = registry.get("platform", {})
    lines.append("## Площадка")
    lines.append("")
    lines.append("| Параметр | Значение |")
    lines.append("|----------|----------|")
    lines.append(f"| URL | {pl.get('url', '—')} |")
    lines.append(f"| KPI рейтинг | {pl.get('rating_kpi', '—')} → {pl.get('rating_target', 'выше')} |")
    lines.append(f"| Лимит без auth | {pl.get('publication_limit_top', '—')} (топ-N отзывов) |")
    lines.append("")

    # 2. Воронка по статусам
    summary = report.get("summary", {})
    bk = summary.get("buckets", {})
    lines.append("## Воронка отзывов")
    lines.append("")
    lines.append("| Статус | Кол-во | Что это |")
    lines.append("|--------|:------:|---------|")
    lines.append(f"| **public** (Sheet)        | {bk.get('public', 0)} | «Отзыв размещён» в Sheet |")
    lines.append(f"| **public** (live confirmed) | {summary.get('live_confirmed_ours', 0)} | подтверждено на платформе |")
    lines.append(f"| **checking**              | {bk.get('checking', 0)} | на модерации Я |")
    lines.append(f"| **contractors**           | {bk.get('contractors', 0)} | у исполнителя |")
    lines.append(f"| **draft**                 | {bk.get('draft', 0)} | согласовано, не отдано |")
    lines.append(f"| **rejected**              | {bk.get('rejected', 0)} | не прошёл модерацию |")
    lines.append(f"| **spent**                 | {bk.get('spent', 0)} | потрачен (деньги ушли) |")
    lines.append(f"| **rework**                | {bk.get('rework', 0)} | банк на доработку |")
    lines.append("")

    # 3. По месяцам live
    plans = registry.get("plans", {})
    lines.append("## По месяцам (live confirmed)")
    lines.append("")
    lines.append("| Месяц | План | Live | %  |")
    lines.append("|-------|:----:|:----:|:---:|")
    for month, plan_def in plans.items():
        target = plan_def.get("target") or plan_def.get("target_proposed") or 0
        if month == "2026-03":
            actual = by_month.get("март", 0)
        elif month == "2026-04":
            actual = by_month.get("апрель", 0)
        elif month == "2026-05":
            actual = by_month.get("май", 0)
        else:
            actual = 0
        pct = round(100 * actual / target) if target else 0
        lines.append(f"| {month} | {target} | {actual} | {pct}% |")
    lines.append("")

    # 4. Контрагенты (skip if public)
    if not public:
        lines.append("## Исполнители / каналы")
        lines.append("")
        lines.append("| Контрагент | Тип | Статус | Платформа |")
        lines.append("|-----------|-----|--------|-----------|")
        for c in registry.get("contractors", []):
            lines.append(f"| {c.get('name')} | {c.get('type', '—')} | {c.get('status', '—')} | {c.get('platform', '—')} |")
        lines.append("")

    # 5. Расхождения
    if discrepancies:
        lines.append("## Расхождения")
        lines.append("")
        for d in discrepancies:
            lines.append(f"- **{d.get('type')}:** {d.get('explanation', '')}")
            for k, v in d.items():
                if k not in ("type", "explanation"):
                    lines.append(f"  - {k}: {v}")
        lines.append("")

    # 6. TG-сигналы (не для публичной)
    if not public:
        bourse_pubs = signals.get("bourse_publications", [])
        bourse_pings = signals.get("bourse_pings", [])
        lines.append("## TG-сигналы (последние)")
        lines.append("")
        lines.append(f"- Биржа отчиталась о публикациях: **{len(bourse_pubs)}**")
        if bourse_pubs:
            for s in bourse_pubs[-3:]:
                lines.append(f"  - {s.get('date')} {s.get('contractor')}: «{s.get('msg', '')[:80]}»")
        lines.append(f"- Биржа просит ещё текстов: **{len(bourse_pings)}**")
        if bourse_pings:
            for s in bourse_pings[-3:]:
                lines.append(f"  - {s.get('date')} {s.get('contractor')}: «{s.get('msg', '')[:80]}»")
        lines.append("")

    # 7. Артефакты (не для публичной)
    if not public:
        lines.append("## Артефакты")
        lines.append("")
        lines.append(f"- Snapshots: `clients/{slug}/orm/snapshots/latest/`")
        lines.append(f"- TG-экспорт: `/tmp/orm-pulse/{slug}/tg/`")
        lines.append(f"- Match: `/tmp/orm-pulse/{slug}/match/`")
        lines.append(f"- Reconcile: `/tmp/orm-pulse/{slug}/reconcile/`")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("slug")
    parser.add_argument("--public", action="store_true")
    parser.add_argument("--out")
    args = parser.parse_args()

    md = render_status(args.slug, public=args.public)

    if args.out:
        out_path = Path(args.out)
    else:
        suffix = "PUBLIC" if args.public else "INTERNAL"
        date = datetime.now().strftime("%Y-%m-%d")
        out_path = ROOT / "clients" / args.slug / "orm" / f"STATUS-{suffix}-{date}.md"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md)
    print(f"✅ {out_path}")
    print()
    print(md)


if __name__ == "__main__":
    main()
