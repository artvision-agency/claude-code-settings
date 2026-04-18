#!/usr/bin/env python3
"""
Report generator — JSON от audit.py → HTML в стиле CAMEO.

CLI:
    python3 report.py audit.json --output=report.html --client-name="Example LLC"

Опционально создаёт графики через matplotlib (если есть raw_data/по_категориям).
"""
from __future__ import annotations

import argparse
import base64
import io
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
    "engagement": "Вовлечённость на сайте",
    "serp": "Поведение в выдаче Яндекса",
    "interaction": "Взаимодействие с элементами",
    "segmentation": "Сегменты аудитории",
    "conversions": "Цели и конверсии",
    "technical": "Скорость и техническое здоровье",
}

CATEGORY_ORDER: list[str] = [
    "engagement",
    "serp",
    "interaction",
    "segmentation",
    "conversions",
    "technical",
]

STATUS_LABELS: dict[str, str] = {
    "pass": "Ок",
    "warn": "Внимание",
    "fail": "Разрыв",
    "manual": "Ручная",
    "na": "Нет данных",
}


def score_class(score: float) -> str:
    if score >= 70:
        return ""
    if score >= 40:
        return "mid"
    return "low"


def build_sources_chart(raw_metrika: dict) -> str | None:
    """Столбчатая диаграмма источников трафика (base64 PNG)."""
    sources = raw_metrika.get("by_source") or {}
    if not sources:
        return None
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None

    # Топ-7 источников
    top = sorted(sources.items(), key=lambda x: -x[1].get("visits", 0))[:7]
    names = [t[0][:20] for t in top]
    visits = [t[1]["visits"] for t in top]

    fig, ax = plt.subplots(figsize=(9, 4), dpi=120)
    bars = ax.barh(names[::-1], visits[::-1], color="#059856")
    ax.set_xlabel("Визиты")
    ax.set_title("Источники трафика (топ-7)")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    for bar, v in zip(bars, visits[::-1]):
        ax.text(bar.get_width(), bar.get_y() + bar.get_height() / 2, f" {v:,}".replace(",", " "), va="center", fontsize=9)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def build_device_chart(raw_metrika: dict) -> str | None:
    devices = raw_metrika.get("by_device") or {}
    if not devices:
        return None
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None

    labels = list(devices.keys())
    bounce = [devices[l]["bounceRate"] for l in labels]

    fig, ax = plt.subplots(figsize=(7, 3.5), dpi=120)
    colors = ["#059856" if b <= 25 else "#e07c1d" if b <= 40 else "#c33648" for b in bounce]
    bars = ax.bar(labels, bounce, color=colors)
    ax.set_ylabel("Отказы, %")
    ax.set_title("Отказы по типу устройства")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    for bar, v in zip(bars, bounce):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{v:.1f}%",
            ha="center",
            va="bottom",
            fontsize=10,
        )
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def render_report(
    audit_data: dict[str, Any],
    output_path: str | Path,
    client_name: str,
) -> Path:
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
    raw = audit_data.get("raw_data", {})

    # Группировка по категориям
    factors_by_category: dict[str, list[dict]] = {c: [] for c in CATEGORY_ORDER}
    for f in factors:
        factors_by_category.setdefault(f["category"], []).append(f)

    sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    status_order = {"fail": 0, "warn": 1, "pass": 2, "manual": 3, "na": 4}
    for cat in factors_by_category:
        factors_by_category[cat].sort(
            key=lambda x: (status_order.get(x["status"], 9), sev_order.get(x["severity"], 9), x["id"])
        )

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

    audited_at_raw = audit_data.get("audited_at", "")
    try:
        dt = datetime.fromisoformat(audited_at_raw.replace("Z", "+00:00"))
        audited_at_display = dt.strftime("%d.%m.%Y %H:%M")
    except (ValueError, AttributeError):
        audited_at_display = audited_at_raw or "—"

    total_count = audit_data.get("meta", {}).get("factors_total", len(factors))
    score = summary.get("score", 0)
    high_count = sum(1 for f in factors if f["status"] == "fail" and f["severity"] == "high")
    critical_count = sum(1 for f in factors if f["status"] == "fail" and f["severity"] == "critical")

    # Графики (если есть данные Метрики)
    metrika_raw = raw.get("metrika") or {}
    sources_chart = build_sources_chart(metrika_raw) if metrika_raw else None
    device_chart = build_device_chart(metrika_raw) if metrika_raw else None

    # Основные KPI для executive summary
    kpi_cards: list[dict[str, str]] = []
    if metrika_raw:
        if "visits" in metrika_raw:
            kpi_cards.append({"label": "Визиты за период", "value": f"{int(metrika_raw['visits']):,}".replace(",", " ")})
        if "bounceRate" in metrika_raw:
            kpi_cards.append({"label": "Отказы", "value": f"{metrika_raw['bounceRate']:.1f}%"})
        if "pageDepth" in metrika_raw:
            kpi_cards.append({"label": "Глубина", "value": f"{metrika_raw['pageDepth']:.2f}"})
        if "avgVisitDurationSeconds" in metrika_raw:
            dur = metrika_raw["avgVisitDurationSeconds"]
            kpi_cards.append({"label": "Среднее время", "value": f"{int(dur // 60)}м {int(dur % 60)}с"})

    webmaster_raw = raw.get("webmaster") or {}
    if webmaster_raw and not webmaster_raw.get("_error"):
        if "overall_ctr" in webmaster_raw:
            kpi_cards.append({"label": "CTR в Яндексе", "value": f"{webmaster_raw['overall_ctr']:.2f}%"})
        if "avg_position" in webmaster_raw and webmaster_raw.get("avg_position"):
            kpi_cards.append({"label": "Средняя позиция", "value": f"{webmaster_raw['avg_position']:.1f}"})

    pagespeed_raw = raw.get("pagespeed") or {}
    if pagespeed_raw and not pagespeed_raw.get("_error"):
        if "performance_score" in pagespeed_raw:
            kpi_cards.append({"label": "Performance (mobile)", "value": f"{pagespeed_raw['performance_score']}/100"})
        if "lcp_sec" in pagespeed_raw:
            kpi_cards.append({"label": "LCP", "value": f"{pagespeed_raw['lcp_sec']:.1f} сек"})

    # Data availability
    has_metrika = bool(metrika_raw) and "visits" in metrika_raw
    has_webmaster = bool(webmaster_raw) and not webmaster_raw.get("_error")
    has_pagespeed = bool(pagespeed_raw) and not pagespeed_raw.get("_error")

    context = {
        "client_name": client_name,
        "target_url": audit_data.get("target_url", ""),
        "counter_id": audit_data.get("counter_id"),
        "period_days": audit_data.get("period_days", 30),
        "audited_at_display": audited_at_display,
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
        "critical_count": critical_count,
        "categories_ordered": categories_ordered,
        "category_stats": category_stats,
        "factors_by_category": factors_by_category,
        "category_labels": CATEGORY_LABELS,
        "status_labels": STATUS_LABELS,
        "kpi_cards": kpi_cards,
        "sources_chart": sources_chart,
        "device_chart": device_chart,
        "has_metrika": has_metrika,
        "has_webmaster": has_webmaster,
        "has_pagespeed": has_pagespeed,
        "meta": audit_data.get("meta", {}),
    }

    html = template.render(**context)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Генератор HTML-отчёта на основе audit.json (behavioral-factors-audit)"
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
