#!/usr/bin/env python3
"""
SEO Factors Audit — Merge Report

Собирает результаты 4 модулей (ModuleResult) в единый dashboard HTML
в стиле CAMEO.

Обычно вызывается из run_all.py, но можно и отдельно:

    python3 merge_report.py --client avtoworld --date 2026-04-17 \
        --domain avto.world --output reports/avtoworld/dashboard.html
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
TEMPLATES_DIR = SKILL_ROOT / "templates"
REPORTS_DIR = SKILL_ROOT / "reports"


# ============================================================
# Цветовая кодировка
# ============================================================
def score_class(score: float) -> str:
    """Маппинг score → CSS-класс (red / yellow / green)."""
    if score >= 71:
        return "score-green"
    if score >= 41:
        return "score-yellow"
    return "score-red"


def score_label(score: float) -> str:
    if score >= 71:
        return "Норма"
    if score >= 41:
        return "Средний уровень"
    return "Критично"


# ============================================================
# Агрегация
# ============================================================
def aggregate_score(results: list, weights: dict[str, float]) -> float:
    """Взвешенное среднее score успешных модулей.

    Если модуль упал — его вес перераспределяется между остальными.
    """
    ok_results = [r for r in results if getattr(r, "ok", False)]
    if not ok_results:
        return 0.0
    total_w = sum(weights.get(r.module, 25) for r in ok_results)
    if total_w == 0:
        return 0.0
    weighted = sum(r.score * weights.get(r.module, 25) for r in ok_results)
    return round(weighted / total_w, 1)


def collect_critical_issues(results: list, limit: int = 20) -> list[dict[str, Any]]:
    """Топ критических проблем cross-group, отсортированные по severity + weight."""
    severity_rank = {"critical": 3, "high": 2, "medium": 1, "low": 0}
    pool: list[dict[str, Any]] = []

    for r in results:
        if not getattr(r, "ok", False):
            continue
        module = r.module
        module_label = r.label
        for issue in r.data.get("critical_issues", []) or []:
            pool.append({
                "module": module,
                "module_label": module_label,
                "factor_id": issue.get("factor_id", ""),
                "name": issue.get("name", ""),
                "severity": issue.get("severity", "medium"),
                "severity_rank": severity_rank.get(issue.get("severity", "medium"), 1),
                "impact": issue.get("impact", ""),
                "detail": issue.get("detail", ""),
            })

    pool.sort(key=lambda x: (-x["severity_rank"], x["module"]))
    return pool[:limit]


def collect_recommendations(results: list) -> dict[str, list[dict[str, Any]]]:
    """Группирует рекомендации по приоритетам: high / medium / low."""
    groups: dict[str, list[dict[str, Any]]] = {"high": [], "medium": [], "low": []}
    for r in results:
        if not getattr(r, "ok", False):
            continue
        for rec in r.data.get("recommendations", []) or []:
            prio = rec.get("priority", "medium").lower()
            if prio not in groups:
                prio = "medium"
            groups[prio].append({
                "module": r.module,
                "module_label": r.label,
                "action": rec.get("action", ""),
                "effort": rec.get("effort", ""),
                "impact": rec.get("impact", ""),
            })
    return groups


def module_summary(r, weights: dict[str, float]) -> dict[str, Any]:
    """Данные для секции модуля в dashboard."""
    if not getattr(r, "ok", False):
        return {
            "module": r.module,
            "label": r.label,
            "ok": False,
            "error": r.error or "модуль не выполнен",
            "score": 0,
            "score_class": "score-red",
            "score_label": "не выполнен",
            "weight": weights.get(r.module, 25),
            "html_link": None,
            "factors_passed": 0,
            "factors_total": 0,
            "top_factors": [],
        }

    factors = r.data.get("factors", []) or []
    passed = sum(1 for f in factors if f.get("passed") or f.get("status") == "pass")
    total = len(factors)

    # Топ-5 факторов (смесь pass/fail по весу, для чекмарк-списка)
    top = sorted(factors, key=lambda f: -float(f.get("weight", 0)))[:8]
    top_items = [
        {
            "name": f.get("name", f.get("id", "—")),
            "passed": f.get("passed") or f.get("status") == "pass",
            "detail": f.get("detail", ""),
        }
        for f in top
    ]

    html_link = None
    if r.html_path:
        html_link = Path(r.html_path).name  # относительно dashboard

    return {
        "module": r.module,
        "label": r.label,
        "ok": True,
        "error": None,
        "score": int(round(r.score)),
        "score_class": score_class(r.score),
        "score_label": score_label(r.score),
        "weight": weights.get(r.module, 25),
        "html_link": html_link,
        "factors_passed": passed,
        "factors_total": total,
        "top_factors": top_items,
    }


# ============================================================
# Рендер
# ============================================================
def build_dashboard(
    results: list,
    domain: str,
    client: str,
    date_str: str,
    weights: dict[str, float],
    competitors: list[str],
    output_path: Path,
    log: logging.Logger | None = None,
) -> Path:
    """Собирает 4 результата в единый HTML dashboard."""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "j2"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("dashboard.html.j2")

    overall_score = aggregate_score(results, weights)
    modules_summary = [module_summary(r, weights) for r in results]
    critical = collect_critical_issues(results, limit=20)
    recs = collect_recommendations(results)

    ok_count = sum(1 for r in results if getattr(r, "ok", False))
    total_count = len(results)

    context = {
        "client": client,
        "domain": domain,
        "date": date_str,
        "date_human": datetime.strptime(date_str, "%Y-%m-%d").strftime("%d.%m.%Y"),
        "overall_score": int(round(overall_score)),
        "overall_score_class": score_class(overall_score),
        "overall_score_label": score_label(overall_score),
        "ok_count": ok_count,
        "total_count": total_count,
        "modules": modules_summary,
        "critical_issues": critical,
        "recommendations": recs,
        "competitors": competitors,
        "weights": weights,
    }

    html = template.render(**context)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")

    if log:
        log.info("dashboard → %s (overall=%s, ok=%d/%d)",
                 output_path, overall_score, ok_count, total_count)
    return output_path


# ============================================================
# CLI (standalone)
# ============================================================
@dataclass
class _StubResult:
    """Для standalone-запуска: восстанавливаем ModuleResult из JSON на диске."""
    module: str
    label: str
    ok: bool
    html_path: Path | None
    score: float
    data: dict
    error: str | None = None


MODULE_LABELS = {
    "commercial": "Коммерческие факторы",
    "text": "Текстовые факторы",
    "link": "Ссылочные факторы",
    "behavioral": "Поведенческие факторы",
}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--client", required=True)
    p.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    p.add_argument("--domain", required=True)
    p.add_argument("--competitors", default="")
    p.add_argument("--output", default=None)
    args = p.parse_args()

    out_dir = REPORTS_DIR / args.client
    results: list = []
    for m, label in MODULE_LABELS.items():
        j = out_dir / f"{m}-{args.date}.json"
        h = out_dir / f"{m}-{args.date}.html"
        if j.exists():
            try:
                data = json.loads(j.read_text(encoding="utf-8"))
                score = float(data.get("score", 0))
                results.append(_StubResult(m, label, True,
                                           h if h.exists() else None, score, data))
            except Exception as e:  # noqa: BLE001
                results.append(_StubResult(m, label, False, None, 0, {},
                                           error=f"чтение JSON: {e}"))
        else:
            results.append(_StubResult(m, label, False, None, 0, {},
                                       error="JSON не найден"))

    weights: dict[str, float] = {"commercial": 25.0, "text": 25.0, "link": 25.0, "behavioral": 25.0}
    output_path = Path(args.output) if args.output else out_dir / f"seo-audit-{args.date}.html"

    build_dashboard(
        results=results,
        domain=args.domain,
        client=args.client,
        date_str=args.date,
        weights=weights,
        competitors=[c.strip() for c in args.competitors.split(",") if c.strip()],
        output_path=output_path,
    )
    print(f"dashboard → {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
