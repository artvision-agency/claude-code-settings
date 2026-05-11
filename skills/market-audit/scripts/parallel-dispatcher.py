"""Parallel dispatcher для /market-audit skill — справочная утилита.

Этот файл — НЕ основной диспатч. Внутри skill сам Claude
запускает 5 параллельных Task tool calls в одном assistant message —
это и есть «параллельный режим» (подобно /swarm).

Для случая когда нужен внешний CLI (например cron / npm script /
интеграция в pipeline без Claude Code в loop) — используется
этот скрипт через Anthropic SDK + asyncio.

Стек: anthropic SDK, asyncio, jsonschema (опц.) для валидации
JSON outputs от subagents.

Usage (без Claude Code):
    python3 parallel-dispatcher.py --url https://artvision.pro \\
                                   --brand Artvision \\
                                   --region msk \\
                                   --output _pilot/market-audit-artvision.html

Functions:
    load_rubric_section: вытащить нужную секцию из scoring-rubric.md
    build_subagent_prompt: собрать prompt для одного subagent типа
    dispatch_parallel: запустить N subagents через asyncio.gather
    parse_subagent_json: безопасный парсинг JSON output от subagent
    compute_marketing_score: взвешенное среднее
    render_html_report: финальный HTML rendering

Внутри Claude Code skill — этот файл не вызывается. Skill сам
оркестрирует через Task tool. Этот файл оставлен:
1. Для тестов scoring логики (compute_marketing_score)
2. Для будущей CI/cron-интеграции (без человека в loop)
3. Для документирования архитектуры
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Iterable


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SUBAGENT_SECTIONS = ("content", "conversion", "technical", "competitive", "strategy")

WEIGHTS = {
    "content": 0.25,
    "conversion": 0.20,
    "technical": 0.20,
    "competitive": 0.15,
    "strategy": 0.20,
}

GRADE_BANDS = (
    (85, "A", "Excellent"),
    (70, "B", "Good"),
    (55, "C", "Average"),
    (40, "D", "Below average"),
    (0, "F", "Critical"),
)


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------


@dataclass
class SubagentResult:
    """Один subagent output после parse."""

    section: str
    score: int
    findings: list[dict] = field(default_factory=list)
    recommendations: list[dict] = field(default_factory=list)
    evidence_urls: list[str] = field(default_factory=list)
    partial: bool = False
    notes: str = ""
    raw_output: str = ""

    @property
    def band(self) -> str:
        for threshold, _grade, name in GRADE_BANDS:
            if self.score >= threshold:
                return name
        return "Critical"


@dataclass
class AuditReport:
    """Финальный собранный отчёт всех 5 subagents."""

    url: str
    brand: str
    region: str
    industry: str
    date: str
    subagents: list[SubagentResult]
    wall_clock_seconds: float = 0.0

    @property
    def composite_score(self) -> float:
        return compute_marketing_score({s.section: s.score for s in self.subagents})

    @property
    def grade(self) -> str:
        for threshold, letter, _ in GRADE_BANDS:
            if self.composite_score >= threshold:
                return letter
        return "F"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_rubric_section(rubric_path: Path, section: str) -> str:
    """Извлечь секцию scoring rubric для конкретного subagent.

    Каждая секция в scoring-rubric.md начинается с ``## N. Section``.
    Возвращает текст от заголовка до следующего ``## N+1. ...``.
    """
    if section not in SUBAGENT_SECTIONS:
        raise ValueError(f"Unknown section: {section!r}")

    text = rubric_path.read_text()
    # Match section header case-insensitively
    pattern = re.compile(
        rf"^## \d+\. {section}\b.*?(?=^## \d+\.|^---\s*$|\Z)",
        re.IGNORECASE | re.MULTILINE | re.DOTALL,
    )
    m = pattern.search(text)
    return m.group(0).strip() if m else ""


def build_subagent_prompt(
    section: str,
    url: str,
    brand: str,
    industry: str,
    region: str,
    rubric_section: str,
) -> str:
    """Собрать prompt для одного subagent.

    Каждый subagent получает: свою специализацию + URL + brand +
    industry + region + СВОЮ секцию rubric (не весь файл) + строгий
    JSON output schema.
    """
    return f"""Ты — {section} auditor для маркетингового аудита сайта.

URL: {url}
Brand: {brand}
Industry: {industry}
Region (РФ): {region}

=== ТВОЯ СЕКЦИЯ SCORING RUBRIC ===
{rubric_section}
=== /КОНЕЦ RUBRIC ===

Задача: проанализируй сайт по секции "{section}", выстави score 0-100
согласно rubric выше, собери findings и recommendations.

ОБЯЗАТЕЛЬНО:
1. Используй WebFetch чтобы получить реальный HTML главной + 2-3
   ключевые страницы. НЕ выдумывай — все findings должны иметь URL
   evidence.
2. Проверяй найденное через `curl -sI <url>` где применимо.
3. Учитывай РФ-специфику: Я.Метрика (mc.yandex.ru/metrika),
   Я.Вебмастер (yandex-verification meta), 2GIS, ВК, Дзен,
   Топвизор-like позиции. НЕ выдумывай данные GA/SEMrush.
4. Если данных недостаточно — пиши `"partial": true` и `notes:`,
   а не выдумывай.

ФОРМАТ OUTPUT (строгий JSON, ничего кроме JSON в финальном
сообщении):

```json
{{
  "section": "{section}",
  "score": 0-100,
  "findings": [
    {{"severity": "critical|high|medium|low",
      "what": "...",
      "where": "https://...",
      "evidence": "..." }}
  ],
  "recommendations": [
    {{"effort": "quick_win|strategic|long_term",
      "what": "...",
      "impact": "high|medium|low",
      "timeline": "1 week|1 month|1 quarter"}}
  ],
  "evidence_urls": ["https://..."],
  "partial": false,
  "notes": ""
}}
```
"""


def parse_subagent_json(raw: str, section: str) -> SubagentResult:
    """Безопасный парсинг output от subagent.

    Subagent должен вернуть строгий JSON, но на практике может
    обернуть в markdown code fence или дописать пояснения.
    Этот парсер вытаскивает первый ``{...}`` блок и парсит.
    """
    # Try to find JSON block (with or without markdown fence)
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if fence_match:
        candidate = fence_match.group(1)
    else:
        # Find first {...} structure
        brace_match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", raw, re.DOTALL)
        candidate = brace_match.group(0) if brace_match else "{}"

    try:
        data = json.loads(candidate)
    except json.JSONDecodeError:
        return SubagentResult(
            section=section,
            score=0,
            partial=True,
            notes=f"JSON parse failed; raw output len={len(raw)}",
            raw_output=raw[:1000],
        )

    return SubagentResult(
        section=data.get("section", section),
        score=int(data.get("score", 0)),
        findings=list(data.get("findings", [])),
        recommendations=list(data.get("recommendations", [])),
        evidence_urls=list(data.get("evidence_urls", [])),
        partial=bool(data.get("partial", False)),
        notes=str(data.get("notes", "")),
        raw_output=raw[:500],
    )


def compute_marketing_score(scores: dict[str, int]) -> float:
    """Compute weighted composite score 0-100.

    Missing sections contribute 0 (signal that subagent failed).
    """
    total = 0.0
    for section, weight in WEIGHTS.items():
        total += scores.get(section, 0) * weight
    return round(total, 1)


def classify_recommendation_buckets(
    subagents: Iterable[SubagentResult],
) -> dict[str, list[dict]]:
    """Распределить все recommendations по 3 корзинам."""
    buckets: dict[str, list[dict]] = {
        "quick_win": [],
        "strategic": [],
        "long_term": [],
    }
    for sa in subagents:
        for rec in sa.recommendations:
            effort = rec.get("effort", "strategic")
            if effort not in buckets:
                effort = "strategic"
            enriched = {**rec, "_source_section": sa.section}
            buckets[effort].append(enriched)
    return buckets


# ---------------------------------------------------------------------------
# HTML rendering
# ---------------------------------------------------------------------------


def _bar_svg(score: int, width: int = 200) -> str:
    """SVG-like inline bar (no SVG, just div for HTML email compat)."""
    pct = max(0, min(100, score))
    bar_w = int(width * pct / 100)
    return (
        f'<span style="display:inline-block;background:#e5e7eb;width:{width}px;'
        f'height:8px;border-radius:2px;vertical-align:middle;">'
        f'<span style="display:inline-block;background:#2c3e88;width:{bar_w}px;'
        f'height:8px;border-radius:2px;"></span></span>'
    )


def _grade_class(grade: str) -> str:
    return f"score-{grade}"


def _render_findings_list(findings: list[dict]) -> str:
    if not findings:
        return "<p><em>Findings not provided.</em></p>"
    items = []
    for f in findings:
        sev = escape(str(f.get("severity", "")))
        what = escape(str(f.get("what", "")))
        where = escape(str(f.get("where", "")))
        where_link = f' <a href="{where}">link</a>' if where.startswith("http") else ""
        items.append(f"<li><strong>[{sev}]</strong> {what}{where_link}</li>")
    return "<ul>" + "".join(items) + "</ul>"


def _render_recs_list(recs: list[dict]) -> str:
    if not recs:
        return "<p><em>No recommendations.</em></p>"
    items = []
    for r in recs:
        effort = escape(str(r.get("effort", "")))
        impact = escape(str(r.get("impact", "")))
        what = escape(str(r.get("what", "")))
        timeline = escape(str(r.get("timeline", "")))
        items.append(
            f"<li><strong>[{effort}, {impact} impact, {timeline}]</strong> {what}</li>"
        )
    return "<ul>" + "".join(items) + "</ul>"


def render_html_report(report: AuditReport) -> str:
    """Финальный HTML report. Standalone (не КП-template)."""
    score = report.composite_score
    grade = report.grade
    grade_class = _grade_class(grade)
    buckets = classify_recommendation_buckets(report.subagents)

    rows = []
    for sa in report.subagents:
        weight = WEIGHTS.get(sa.section, 0.0)
        weighted = round(sa.score * weight, 1)
        top_finding = sa.findings[0]["what"] if sa.findings else "—"
        rows.append(
            f"<tr>"
            f"<td>{escape(sa.section.title())}</td>"
            f'<td><span class="{_grade_class(_letter_for_score(sa.score))}">'
            f"{sa.score}/100</span> {_bar_svg(sa.score)}</td>"
            f"<td>{int(weight*100)}%</td>"
            f"<td>{weighted}</td>"
            f"<td>{escape(top_finding)}{'  (partial)' if sa.partial else ''}</td>"
            f"</tr>"
        )

    sections_html = []
    for sa in report.subagents:
        sections_html.append(
            f'<div class="section">'
            f"<h3>{escape(sa.section.title())} "
            f'<span class="{_grade_class(_letter_for_score(sa.score))}">'
            f"{sa.score}/100</span> ({escape(sa.band)})</h3>"
            f"{'<p><em>Partial result: ' + escape(sa.notes) + '</em></p>' if sa.partial else ''}"
            f"<h4>Findings ({len(sa.findings)})</h4>"
            f"{_render_findings_list(sa.findings)}"
            f"<h4>Recommendations ({len(sa.recommendations)})</h4>"
            f"{_render_recs_list(sa.recommendations)}"
            f"</div>"
        )

    def render_bucket(name: str, items: list[dict]) -> str:
        if not items:
            return f"<p><em>No {name} items.</em></p>"
        return _render_recs_list(items)

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>Market Audit — {escape(report.brand)} — {escape(report.date)}</title>
<style>
  body {{ font-family: -apple-system, system-ui, sans-serif; max-width: 1200px;
         margin: 2em auto; padding: 0 1em; color: #222; line-height: 1.5; }}
  h1 {{ border-bottom: 3px solid #2c3e88; padding-bottom: 0.3em; }}
  h2 {{ margin-top: 2em; color: #2c3e88; }}
  h3 {{ color: #2c3e88; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1em 0; }}
  th, td {{ border: 1px solid #ddd; padding: 0.5em 0.8em; text-align: left;
            vertical-align: top; }}
  th {{ background: #f5f6fa; }}
  .score-A {{ color: #15803d; font-weight: 700; }}
  .score-B {{ color: #84cc16; font-weight: 600; }}
  .score-C {{ color: #d97706; }}
  .score-D {{ color: #ea580c; }}
  .score-F {{ color: #dc2626; font-weight: 700; }}
  .section {{ background: #fafbfc; padding: 1em 1.2em; border-left: 4px solid #2c3e88;
              margin: 1.2em 0; border-radius: 4px; }}
  code {{ background: #f0f2f5; padding: 0.1em 0.4em; border-radius: 3px;
          font-family: ui-monospace, monospace; font-size: 0.9em; }}
  .meta {{ background: #f0f6fa; padding: 0.8em 1em; border-left: 4px solid #2c3e88;
           margin: 1em 0; }}
  .footer {{ margin-top: 3em; color: #6b7280; font-size: 0.85em; }}
</style>
</head>
<body>
  <h1>Market Audit — {escape(report.brand)}</h1>
  <div class="meta">
    <p><strong>URL:</strong> <a href="{escape(report.url)}">{escape(report.url)}</a><br>
       <strong>Дата:</strong> {escape(report.date)}<br>
       <strong>Тип бизнеса:</strong> {escape(report.industry)}<br>
       <strong>Регион:</strong> {escape(report.region)}<br>
       <strong>Wall-clock:</strong> {report.wall_clock_seconds:.1f}s</p>
  </div>

  <h2>Итоговая оценка: <span class="{grade_class}">{score}/100 ({grade})</span></h2>

  <h2>Score Breakdown</h2>
  <table>
    <thead>
      <tr><th>Категория</th><th>Score</th><th>Вес</th><th>Взвешено</th>
          <th>Ключевая находка</th></tr>
    </thead>
    <tbody>{''.join(rows)}</tbody>
  </table>

  <h2>Quick Wins (на этой неделе)</h2>
  {render_bucket("quick win", buckets["quick_win"])}

  <h2>Strategic Recommendations (этот месяц)</h2>
  {render_bucket("strategic", buckets["strategic"])}

  <h2>Long-Term Initiatives (этот квартал)</h2>
  {render_bucket("long-term", buckets["long_term"])}

  <h2>Detailed Findings by Category</h2>
  {''.join(sections_html)}

  <p class="footer">Generated by <code>/market-audit</code> · Artvision
  orchestrator week1 · {escape(report.date)}</p>
</body>
</html>
"""


def _letter_for_score(score: int) -> str:
    for threshold, letter, _ in GRADE_BANDS:
        if score >= threshold:
            return letter
    return "F"


# ---------------------------------------------------------------------------
# CLI entry (для off-Claude-Code использования)
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Parallel dispatcher for /market-audit (reference utility). "
        "Inside Claude Code, the skill orchestrates via Task tool directly."
    )
    parser.add_argument("--url", required=True, help="Target URL")
    parser.add_argument("--brand", default="", help="Brand name (default: parsed from <title>)")
    parser.add_argument("--region", default="msk", help="Region code (msk|spb|...)")
    parser.add_argument("--industry", default="auto", help="Industry hint")
    parser.add_argument("--output", required=True, help="Path to write HTML report")
    parser.add_argument(
        "--from-json",
        help="Path to JSON file with pre-computed 5 subagent results "
        "(skip live dispatch, just render HTML)",
    )
    args = parser.parse_args()

    if not args.from_json:
        # Live dispatch requires anthropic SDK + asyncio + WebFetch.
        # Not implemented here — see skill SKILL.md "Phase 2" for the
        # in-Claude-Code path. This CLI is a reference for the rendering
        # half of the pipeline; live dispatch is delegated to skill.
        print(
            "Live dispatch from this CLI is not implemented. "
            "Either: (a) use /market-audit skill inside Claude Code, or "
            "(b) pre-compute subagent JSONs and pass --from-json."
        )
        return 1

    raw_data = json.loads(Path(args.from_json).read_text())
    subagents = [
        SubagentResult(
            section=item["section"],
            score=int(item.get("score", 0)),
            findings=list(item.get("findings", [])),
            recommendations=list(item.get("recommendations", [])),
            evidence_urls=list(item.get("evidence_urls", [])),
            partial=bool(item.get("partial", False)),
            notes=str(item.get("notes", "")),
        )
        for item in raw_data["subagents"]
    ]
    report = AuditReport(
        url=args.url,
        brand=args.brand or raw_data.get("brand", ""),
        region=args.region,
        industry=args.industry,
        date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        subagents=subagents,
        wall_clock_seconds=float(raw_data.get("wall_clock_seconds", 0.0)),
    )
    Path(args.output).write_text(render_html_report(report))
    print(f"Report written: {args.output}")
    print(
        f"Composite score: {report.composite_score}/100 (Grade {report.grade})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
