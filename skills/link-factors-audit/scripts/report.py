#!/usr/bin/env python3
"""
Report generator — JSON от audit.py → HTML в стиле CAMEO + графики matplotlib.

CLI:
    python3 report.py link-audit.json --output=report.html --client-name="Example LLC"
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

import matplotlib
matplotlib.use("Agg")  # без GUI
import matplotlib.pyplot as plt
from jinja2 import Environment, FileSystemLoader, select_autoescape

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
TEMPLATES_DIR = SKILL_ROOT / "templates"

GROUP_LABELS: dict[str, str] = {
    "external_profile": "Внешний ссылочный профиль",
    "anchor_toxicity": "Анкор-лист и токсичность",
    "dynamics_age": "Динамика и возраст массы",
    "internal_linking": "Внутренняя перелинковка",
    "competitor_gap": "Конкурентный разрыв",
}

GROUP_ORDER: list[str] = [
    "external_profile",
    "anchor_toxicity",
    "dynamics_age",
    "internal_linking",
    "competitor_gap",
]

STATUS_LABELS: dict[str, str] = {
    "pass": "Ок",
    "warn": "Внимание",
    "fail": "Разрыв",
    "manual": "Ручная",
    "na": "n/a",
}

# CAMEO palette
COLOR_GREEN = "#059856"
COLOR_ORANGE = "#e07c1d"
COLOR_RED = "#c33648"
COLOR_PINK = "#d82b63"
COLOR_GRAY = "#636663"
COLOR_LIGHT = "#f3f3f3"


# ============================================================
# Графики → base64 PNG
# ============================================================
def _fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=110)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def chart_anchor_distribution(data: dict[str, int]) -> str | None:
    if not data or sum(data.values()) == 0:
        return None
    labels_map = {
        "brand": "Брендовые",
        "exact": "Точное вхождение",
        "partial": "Разбавленные",
        "naked_url": "Naked URL",
        "generic": "Generic",
        "empty": "Пустой анкор",
    }
    colors = {
        "brand": COLOR_GREEN,
        "exact": COLOR_RED,
        "partial": COLOR_ORANGE,
        "naked_url": COLOR_GRAY,
        "generic": "#b0b0b0",
        "empty": "#dadada",
    }
    items = [(k, v) for k, v in data.items() if v > 0]
    if not items:
        return None
    labels = [labels_map.get(k, k) for k, _ in items]
    values = [v for _, v in items]
    colors_list = [colors.get(k, COLOR_GRAY) for k, _ in items]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.barh(labels, values, color=colors_list)
    ax.set_xlabel("Кол-во ссылок", fontsize=10)
    ax.set_title("Распределение анкоров", fontsize=13, fontweight="bold", loc="left")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(labelsize=9)
    for i, v in enumerate(values):
        ax.text(v, i, f"  {v}", va="center", fontsize=9)
    fig.tight_layout()
    return _fig_to_base64(fig)


def chart_follow_breakdown(data: dict[str, int]) -> str | None:
    if not data or sum(data.values()) == 0:
        return None
    labels = ["dofollow", "nofollow"]
    values = [data.get("dofollow", 0), data.get("nofollow", 0)]
    colors_list = [COLOR_GREEN, COLOR_GRAY]
    fig, ax = plt.subplots(figsize=(4.5, 4.5))
    ax.pie(values, labels=labels, colors=colors_list, autopct="%1.0f%%",
           startangle=90, wedgeprops={"edgecolor": "white", "linewidth": 2})
    ax.set_title("Типы ссылок", fontsize=13, fontweight="bold", loc="left")
    fig.tight_layout()
    return _fig_to_base64(fig)


def chart_velocity_12m(monthly: list[int]) -> str | None:
    if not monthly or sum(monthly) == 0:
        return None
    months = list(range(1, len(monthly) + 1))
    fig, ax = plt.subplots(figsize=(8, 3.5))
    ax.plot(months, monthly, marker="o", color=COLOR_GREEN, linewidth=2)
    ax.fill_between(months, monthly, alpha=0.2, color=COLOR_GREEN)
    ax.set_title("Прирост ссылок по месяцам (12 мес)", fontsize=13, fontweight="bold", loc="left")
    ax.set_xlabel("Месяц", fontsize=10)
    ax.set_ylabel("Новых ссылок", fontsize=10)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", linestyle="--", alpha=0.3)
    fig.tight_layout()
    return _fig_to_base64(fig)


def chart_competitor_comparison(data: dict[str, list]) -> str | None:
    if not data or not data.get("labels"):
        return None
    labels = data["labels"]
    values = data["values"]
    colors_list = [COLOR_GREEN] + [COLOR_GRAY] * (len(labels) - 1)
    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.bar(labels, values, color=colors_list)
    ax.set_title("Ссылающиеся домены: мы vs конкуренты", fontsize=13, fontweight="bold", loc="left")
    ax.set_ylabel("Ref domains", fontsize=10)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(axis="x", labelsize=9, rotation=20)
    for bar, v in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, v, f" {v}",
                ha="center", va="bottom", fontsize=9)
    fig.tight_layout()
    return _fig_to_base64(fig)


def chart_dr_histogram(data: dict[str, int]) -> str | None:
    if not data or sum(data.values()) == 0:
        return None
    labels = list(data.keys())
    values = list(data.values())
    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.bar(labels, values, color=COLOR_GREEN)
    ax.set_title("Распределение DR донаров", fontsize=13, fontweight="bold", loc="left")
    ax.set_ylabel("Доноров", fontsize=10)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return _fig_to_base64(fig)


def build_charts(audit_data: dict[str, Any]) -> dict[str, str]:
    charts = audit_data.get("charts", {})
    out: dict[str, str] = {}
    if "anchor_distribution" in charts:
        img = chart_anchor_distribution(charts["anchor_distribution"])
        if img:
            out["anchor_distribution"] = img
    if "follow_breakdown" in charts:
        img = chart_follow_breakdown(charts["follow_breakdown"])
        if img:
            out["follow_breakdown"] = img
    if "velocity_12m" in charts:
        img = chart_velocity_12m(charts["velocity_12m"])
        if img:
            out["velocity_12m"] = img
    if "competitor_comparison" in charts:
        img = chart_competitor_comparison(charts["competitor_comparison"])
        if img:
            out["competitor_comparison"] = img
    if "dr_histogram" in charts:
        img = chart_dr_histogram(charts["dr_histogram"])
        if img:
            out["dr_histogram"] = img
    return out


# ============================================================
# Render
# ============================================================
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
    by_group = summary.get("by_group", {})

    factors_by_group: dict[str, list[dict]] = {g: [] for g in GROUP_ORDER}
    for f in factors:
        factors_by_group.setdefault(f["group"], []).append(f)

    sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    status_order = {"fail": 0, "warn": 1, "pass": 2, "na": 3, "manual": 4}
    for g in factors_by_group:
        factors_by_group[g].sort(
            key=lambda x: (status_order.get(x["status"], 9), sev_order.get(x["severity"], 9), x["id"])
        )

    group_stats: dict[str, dict[str, int]] = {}
    for gid in GROUP_ORDER:
        stats = by_group.get(gid, {})
        group_stats[gid] = {
            "pass": stats.get("pass", 0),
            "fail": stats.get("fail", 0),
            "warn": stats.get("warn", 0),
            "manual": stats.get("manual", 0),
            "na": stats.get("na", 0),
            "total": sum(stats.values()) if stats else len(factors_by_group.get(gid, [])),
        }

    groups_ordered = [
        (gid, GROUP_LABELS[gid])
        for gid in GROUP_ORDER
        if factors_by_group.get(gid)
    ]

    audited_at_raw = audit_data.get("audited_at", "")
    try:
        dt = datetime.fromisoformat(audited_at_raw.replace("Z", "+00:00"))
        audited_at_display = dt.strftime("%d.%m.%Y %H:%M")
    except (ValueError, AttributeError):
        audited_at_display = audited_at_raw or "—"

    total_count = audit_data.get("meta", {}).get("factors_total", len(factors))
    automated = summary.get("automated_factors", 0)
    score = summary.get("score", 0)
    high_count = sum(1 for f in factors if f["status"] == "fail" and f["severity"] == "high")

    charts = build_charts(audit_data)

    providers = audit_data.get("providers_available", {})
    providers_display = {
        "Checktrust": providers.get("checktrust", False),
        "Serpstat": providers.get("serpstat", False),
        "Ahrefs": providers.get("ahrefs", False),
        "Majestic": providers.get("majestic", False),
        "Яндекс.Вебмастер": providers.get("yandex_webmaster", False),
    }

    context = {
        "client_name": client_name,
        "target_domain": audit_data.get("target_domain", ""),
        "audited_at_display": audited_at_display,
        "competitors": audit_data.get("competitors", []),
        "total_count": total_count,
        "automated_count": automated,
        "pass_count": counts.get("pass", 0),
        "fail_count": counts.get("fail", 0),
        "warn_count": counts.get("warn", 0),
        "manual_count": counts.get("manual", 0),
        "na_count": counts.get("na", 0),
        "score": score,
        "score_class": score_class(score),
        "critical_fails": summary.get("critical_fails_top", []),
        "high_count": high_count,
        "groups_ordered": groups_ordered,
        "group_stats": group_stats,
        "factors_by_group": factors_by_group,
        "group_labels": GROUP_LABELS,
        "status_labels": STATUS_LABELS,
        "charts": charts,
        "providers_display": providers_display,
        "crawl_meta": audit_data.get("meta", {}).get("crawl", {}),
    }

    html = template.render(**context)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="HTML-отчёт ссылочного аудита")
    parser.add_argument("input", help="JSON от audit.py")
    parser.add_argument("--output", "-o", required=True)
    parser.add_argument("--client-name", default="Сайт клиента")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"[ERROR] Файл не найден: {input_path}", file=sys.stderr)
        return 1

    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)

    output = render_report(data, args.output, args.client_name)
    print(f"[OK] Report: {output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
