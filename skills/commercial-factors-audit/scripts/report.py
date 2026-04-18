#!/usr/bin/env python3
"""
Report generator — JSON от audit.py → HTML в стиле CAMEO.

CLI:
    python3 report.py audit.json --output=report.html --client-name="Example LLC"
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
TEMPLATES_DIR = SKILL_ROOT / "templates"

CATEGORY_LABELS: dict[str, str] = {
    "navigation_company": "Навигация и информация о компании",
    "trust": "Доверие и социальные доказательства",
    "ecommerce": "E-commerce: корзина, доставка, оплата",
    "engagement": "Взаимодействие с клиентом",
    "content_seo": "Контент и SEO",
    "sales_tools": "Инструменты продаж",
    "product_info": "Карточка товара и каталог",
}

CATEGORY_ORDER: list[str] = [
    "navigation_company",
    "trust",
    "ecommerce",
    "engagement",
    "content_seo",
    "sales_tools",
    "product_info",
]

STATUS_LABELS: dict[str, str] = {
    "pass": "Ок",
    "warn": "Внимание",
    "fail": "Разрыв",
    "manual": "Ручная",
    "na": "n/a",
}


def score_class(score: float) -> str:
    if score >= 70:
        return ""
    if score >= 40:
        return "mid"
    return "low"


def render_report(
    audit_data: dict[str, Any],
    output_path: str | Path,
    client_name: str,
) -> Path:
    """Генерирует HTML-отчёт из JSON-данных аудита."""
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(["html", "j2"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("report.html.j2")

    factors = audit_data.get("factors", [])
    summary = audit_data.get("meta", {}).get("summary", {})
    counts = summary.get("counts", {})
    by_category = summary.get("by_category", {})

    # Группировка по категориям в нужном порядке
    factors_by_category: dict[str, list[dict]] = {c: [] for c in CATEGORY_ORDER}
    for f in factors:
        factors_by_category.setdefault(f["category"], []).append(f)

    # Сортировка внутри категории: сначала FAIL critical/high, потом WARN, потом PASS, MANUAL в конце
    sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    status_order = {"fail": 0, "warn": 1, "pass": 2, "na": 3, "manual": 4}
    for cat in factors_by_category:
        factors_by_category[cat].sort(
            key=lambda x: (status_order.get(x["status"], 9), sev_order.get(x["severity"], 9), x["id"])
        )

    # Подсчёт total по категориям
    category_stats: dict[str, dict[str, int]] = {}
    for cat_id in CATEGORY_ORDER:
        stats = by_category.get(cat_id, {})
        category_stats[cat_id] = {
            "pass": stats.get("pass", 0),
            "fail": stats.get("fail", 0),
            "warn": stats.get("warn", 0),
            "manual": stats.get("manual", 0),
            "na": stats.get("na", 0),
            "total": sum(stats.values()) if stats else len(factors_by_category.get(cat_id, [])),
        }

    categories_ordered = [
        (cat_id, CATEGORY_LABELS[cat_id])
        for cat_id in CATEGORY_ORDER
        if factors_by_category.get(cat_id)
    ]

    # Дата в человеческом виде
    audited_at_raw = audit_data.get("audited_at", "")
    try:
        dt = datetime.fromisoformat(audited_at_raw.replace("Z", "+00:00"))
        audited_at_display = dt.strftime("%d.%m.%Y %H:%M")
    except (ValueError, AttributeError):
        audited_at_display = audited_at_raw or "—"

    total_count = audit_data.get("meta", {}).get("factors_total", len(factors))
    score = summary.get("score", 0)
    high_count = sum(1 for f in factors if f["status"] == "fail" and f["severity"] == "high")

    context = {
        "client_name": client_name,
        "target_url": audit_data.get("target_url", ""),
        "audited_at_display": audited_at_display,
        "pages_crawled": audit_data.get("pages_crawled", {}),
        "total_count": total_count,
        "pass_count": counts.get("pass", 0),
        "fail_count": counts.get("fail", 0),
        "warn_count": counts.get("warn", 0),
        "manual_count": counts.get("manual", 0),
        "na_count": counts.get("na", 0),
        "score": score,
        "score_class": score_class(score),
        "critical_fails": summary.get("critical_fails_top", []),
        "high_count": high_count,
        "categories_ordered": categories_ordered,
        "category_stats": category_stats,
        "factors_by_category": factors_by_category,
        "category_labels": CATEGORY_LABELS,
        "status_labels": STATUS_LABELS,
    }

    html = template.render(**context)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Генератор HTML-отчёта на основе audit.json"
    )
    parser.add_argument("input", help="Путь к JSON от audit.py")
    parser.add_argument("--output", "-o", required=True, help="Путь к выходному HTML")
    parser.add_argument("--client-name", default="Сайт клиента", help="Название клиента для заголовка")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"[ERROR] Файл не найден: {input_path}", file=sys.stderr)
        return 1

    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)

    output = render_report(
        audit_data=data,
        output_path=args.output,
        client_name=args.client_name,
    )
    print(f"[OK] Report saved: {output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
