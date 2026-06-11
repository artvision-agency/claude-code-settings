#!/usr/bin/env python3
"""attribution-report — единая прозрачная таблица для ORM-клиента.

Связывает: текст из Sheet → исполнитель/биржа (по registry.contractors[].sheet_link)
          → дата заказа/отзыва → найден ли в live crawl → текущий статус на yandex.

Output:
  clients/<slug>/orm/attribution-report-{date}.csv  (для Excel)
  clients/<slug>/orm/attribution-report-{date}.html (для браузера)

Usage:
  attribution-report.py <slug>
"""
from __future__ import annotations
import argparse
import csv
import html
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from lib.config import ROOT  # noqa: E402


def normalize(s: str) -> str:
    s = (s or "").lower().replace("ё", "е")
    s = re.sub(r"[^\wа-я0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def load_registry(slug: str) -> dict:
    return yaml.safe_load((ROOT / "clients" / slug / "orm" / "registry.yaml").read_text())


def sheet_to_contractor(reg: dict) -> dict[str, str]:
    """Map sheet_key → contractor_name через registry.contractors[].sheet_link."""
    out: dict[str, str] = {}
    for c in reg.get("contractors", []):
        sl = c.get("sheet_link")
        if sl:
            out[sl] = c["name"]
    return out


def load_sheet_rows(slug: str, contractor_map: dict[str, str]) -> list[dict]:
    """Все строки из всех CSV snapshots/latest/, с executor."""
    snap = ROOT / "clients" / slug / "orm" / "snapshots" / "latest"
    if not snap.exists():
        return []
    out = []
    for csv_file in sorted(snap.glob("*.csv")):
        # sheet1_internal_88304516.csv → sheet_key = "sheet1_internal", tab_gid = "88304516"
        m = re.match(r"(.+?)_(\d+)\.csv", csv_file.name)
        if not m:
            continue
        sheet_key, tab_gid = m.group(1), m.group(2)
        contractor = contractor_map.get(sheet_key, "—")
        # sheet1_internal: внутренний — это "Иришка/Андрей К." (через registry.contractors role)
        if sheet_key == "sheet1_internal":
            contractor = "internal (Иришка/Андрей К.)"
        try:
            with open(csv_file) as fh:
                rows = list(csv.DictReader(fh))
        except Exception:
            continue
        if not rows:
            continue
        text_col = next((k for k in rows[0].keys() if "Текст" in k), None)
        status_col = next((k for k in rows[0].keys() if k.startswith("Статус")), None)
        date_order_col = next((k for k in rows[0].keys() if "Дата заказа" in k), None)
        date_review_col = next((k for k in rows[0].keys() if "Дата отзыва" in k), None)
        author_col = next((k for k in rows[0].keys() if "Автор отзыва" in k), None)
        category_col = next((k for k in rows[0].keys() if "Категория" in k), None)
        if not (text_col and status_col):
            continue
        for r in rows:
            text = (r.get(text_col) or "").strip()
            if not text or len(text) < 20:
                continue
            out.append({
                "sheet": csv_file.stem,
                "tab_gid": tab_gid,
                "contractor": contractor,
                "category": (r.get(category_col) or "").strip() if category_col else "",
                "status_in_sheet": (r.get(status_col) or "").strip(),
                "date_order": (r.get(date_order_col) or "").strip() if date_order_col else "",
                "date_review": (r.get(date_review_col) or "").strip() if date_review_col else "",
                "author_in_sheet": (r.get(author_col) or "").strip() if author_col else "",
                "text": text,
                "text_norm": normalize(text),
            })
    return out


def load_tg_signals(slug: str) -> dict:
    """Читает свежий _index из tg-conversations/. Возвращает агрегаты по контрактору."""
    tg_dir = ROOT / "clients" / slug / "orm" / "tg-conversations"
    if not tg_dir.exists():
        return {}
    indices = sorted(tg_dir.glob("_index-*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not indices:
        return {}
    try:
        data = json.loads(indices[0].read_text())
    except Exception:
        return {}
    out = {}
    for chat in data:
        if "error" in chat:
            continue
        s = chat.get("summary", {})
        msgs = chat.get("messages", [])
        # Последняя дата с pub-маркером
        last_pub = None
        for m in msgs:
            if m.get("pub_markers"):
                d = m.get("date", "")[:10]
                if not last_pub or d > last_pub:
                    last_pub = d
        out[chat["label"]] = {
            "chat_id": chat["chat_id"],
            "count": chat.get("count", 0),
            "pub": s.get("with_pub", 0),
            "rej": s.get("with_rej", 0),
            "req": s.get("with_req", 0),
            "link": s.get("with_link", 0),
            "last_pub": last_pub or "—",
        }
    out["_source"] = str(indices[0].name)
    out["_pulled_at"] = data[0].get("fetched_at", "") if data else ""
    return out


def load_live(slug: str, window_days: int = 10) -> list[dict]:
    """Union всех crawl-dump за последние window_days дней (dedup по _live_key).

    BUG-fix (2026-05-29): раньше брался ТОЛЬКО freshest-by-mtime dump → недосчёт.
    Yandex показывает «окно» отзывов (~300-1000), наши отзывы дрейфуют в/из окна
    при каждом crawl (сортировка по релевантности, не дате). Отзыв, мелькнувший
    в ЛЮБОМ свежем crawl = был опубликован. Union недели crawl'ов даёт реальное
    число (~24-27 против 3 от одного партиального 300-dump).
    Validated: strict-publications-count-2026-05-23.md (best-estimate 22-25).

    Старая логика (freshest-only, BUG-4 2026-05-11) занижала: партиальный 300-dump
    вытеснял глубокий 894-1000 по mtime → matching против узкого окна.
    """
    import time
    cutoff = time.time() - window_days * 86400
    files: list[Path] = []
    for d in ("live-reviews", "live-reviews-history"):
        p = ROOT / "clients" / slug / "orm" / d
        if p.exists():
            files.extend(f for f in p.glob("*.json") if f.stat().st_mtime >= cutoff)
    if not files:
        # fallback: freshest single (если за окно ничего нет)
        allf: list[Path] = []
        for d in ("live-reviews", "live-reviews-history"):
            p = ROOT / "clients" / slug / "orm" / d
            if p.exists():
                allf.extend(p.glob("*.json"))
        if not allf:
            return []
        files = [max(allf, key=lambda p: p.stat().st_mtime)]
    merged: dict[str, dict] = {}
    for f in sorted(files, key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(f.read_text())
        except Exception:
            continue
        for it in data.get("items", []):
            text = (it.get("text") or "").strip()
            key = (it.get("log_node") or it.get("user_id")
                   or f"{it.get('author', '')}|{text[:80]}")
            if key in merged:
                continue
            merged[key] = {
                "author": it.get("author", ""),
                "rating": it.get("rating", ""),
                "date": it.get("date", ""),
                "user_id": it.get("user_id", ""),
                "log_node": it.get("log_node", ""),
                "text": text,
                "text_norm": normalize(text),
            }
    return list(merged.values())


def best_match(needle_norm: str, hay: list[dict], threshold: float = 0.75,
               used_keys: set | None = None) -> tuple[dict | None, float]:
    """BUG-2 fix (2026-05-11): greedy assignment — each live review consumed only once.

    used_keys: set of live-item identifiers already matched. Excludes them.
    """
    if not needle_norm or not hay:
        return None, 0.0
    best, best_score = None, 0.0
    for h in hay:
        # Skip уже потреблённые
        if used_keys and _live_key(h) in used_keys:
            continue
        # Pre-filter по длине ±30%
        if not h.get("text_norm"):
            continue
        if abs(len(h["text_norm"]) - len(needle_norm)) / max(len(needle_norm), 1) > 0.3:
            continue
        s = SequenceMatcher(None, needle_norm, h["text_norm"]).ratio()
        if s > best_score:
            best, best_score = h, s
    if best_score >= threshold:
        return best, best_score
    return None, best_score


def _live_key(item: dict) -> str:
    """Уникальный идентификатор live-отзыва для greedy-assignment."""
    return (
        item.get("log_node")
        or item.get("user_id")
        or f"{item.get('author','')}|{(item.get('text') or '')[:80]}"
    )


def render_replacement_block(rows: list[dict]) -> str:
    """Блок 'кого пинговать' — группировка по исполнителю."""
    by_contractor: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        if r.get("replacement_required") in ("yes", "maybe"):
            by_contractor[r["contractor"]].append(r)
    if not by_contractor:
        return "<p class='muted'>Нет кандидатов на дозамену.</p>"
    blocks = []
    for c, items in sorted(by_contractor.items(), key=lambda x: -len(x[1])):
        yes = [r for r in items if r["replacement_required"] == "yes"]
        maybe = [r for r in items if r["replacement_required"] == "maybe"]
        text_lines = [
            f"<details style='margin:8px 0;padding:10px;background:white;border:1px solid #fee2e2;border-radius:6px'>",
            f"<summary style='cursor:pointer;font-weight:600;color:#991b1b'>",
            f"🔁 {html.escape(c)} — {len(items)} требует дозамены ",
            f"<span class='muted'>(точно: {len(yes)} · под вопросом: {len(maybe)})</span>",
            f"</summary>",
            f"<ul style='margin:8px 0 0;font-size:12px'>",
        ]
        for r in sorted(items, key=lambda x: -(x.get("age_days") or 0))[:25]:
            age = r.get("age_days", "?")
            age_str = f"{age}дн" if isinstance(age, int) else "без даты"
            text_lines.append(
                f"<li>"
                f"<strong>{html.escape(r['category'])}</strong> · "
                f"{age_str} · "
                f"автор: {html.escape(r.get('author_in_sheet') or '—')} · "
                f"<em>{html.escape(r['text'][:120])}…</em>"
                f"</li>"
            )
        if len(items) > 25:
            text_lines.append(f"<li><em>…и ещё {len(items)-25}</em></li>")
        text_lines.append("</ul></details>")
        blocks.append("".join(text_lines))
    return "".join(blocks)


def render_tg_block(tg: dict) -> str:
    if not tg:
        return ''
    src = tg.pop('_source', '')
    pulled = tg.pop('_pulled_at', '')[:16]
    rows_html = []
    for label, s in tg.items():
        rows_html.append(
            f"<tr><td>{html.escape(label)}</td>"
            f"<td style='text-align:right'>{s['count']}</td>"
            f"<td style='text-align:right;color:#16a34a'>{s['pub']}</td>"
            f"<td style='text-align:right;color:#dc2626'>{s['rej']}</td>"
            f"<td style='text-align:right'>{s['req']}</td>"
            f"<td style='text-align:right'>{s['link']}</td>"
            f"<td>{html.escape(s['last_pub'])}</td></tr>"
        )
    return (
        '<h2 style="margin-top:24px">💬 TG-сигналы исполнителей за 30 дней</h2>'
        f'<div class="muted">Источник: {html.escape(src)} · pulled: {html.escape(pulled)}</div>'
        '<table><thead><tr>'
        '<th>Чат</th><th>Msg всего</th><th>Pub-марк</th><th>Rej-марк</th><th>Req-марк</th><th>URLs</th><th>Последний pub</th>'
        '</tr></thead><tbody>' + ''.join(rows_html) + '</tbody></table>'
    )


def render_html(slug: str, rows: list[dict], stats: dict, tg: dict | None = None) -> str:
    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    bg = {
        "Отзыв размещён": ("#dcfce7", "✅"),
        "Согласовано, заказ размещён": ("#fef3c7", "⏳"),
        "Ожидание модерации": ("#fef3c7", "⏳"),
        "Не прошёл модерацию": ("#fecaca", "❌"),
        "потрачен": ("#fecaca", "💸"),
        "Текст согласован": ("#dbeafe", "📝"),
        "Ждет размещения": ("#dbeafe", "📤"),
    }
    live_bg = {
        "✅ найден в live": "#dcfce7",
        "❌ удалён или вне crawl": "#fecaca",
        "— не публиковался": "#f1f5f9",
    }
    body = []
    for r in rows:
        sheet_color, sheet_icon = bg.get(r["status_in_sheet"], ("#f1f5f9", "·"))
        live_color = live_bg.get(r["live_status"], "#f1f5f9")
        text_short = html.escape(r["text"][:120]) + ("…" if len(r["text"]) > 120 else "")
        replace_icon = {"yes": "🔁 да", "maybe": "❓ ?", "no": ""}.get(r.get("replacement_required", "no"), "")
        replace_color = {"yes": "#fee2e2", "maybe": "#fef3c7", "no": ""}.get(r.get("replacement_required", "no"), "")
        body.append(f"""
        <tr>
          <td>{html.escape(r["contractor"])}</td>
          <td>{html.escape(r["category"])}</td>
          <td style="background:{sheet_color}">{sheet_icon} {html.escape(r["status_in_sheet"])}</td>
          <td>{html.escape(r["date_order"] or "—")}</td>
          <td>{html.escape(r["date_review"] or "—")}</td>
          <td>{html.escape(r["author_in_sheet"] or "—")}</td>
          <td style="background:{live_color}">{html.escape(r["live_status"])}{(' (' + str(r['live_match_score']) + ')') if r.get('live_match_score') else ''}</td>
          <td>{html.escape(r.get("live_author", "") or "—")}</td>
          <td style="background:{replace_color};text-align:center;font-weight:600">{replace_icon}</td>
          <td title="{html.escape(r['text'])}">{text_short}</td>
        </tr>""")
    replacement_html = render_replacement_block(rows)

    return f"""<!DOCTYPE html>
<html lang="ru"><head>
<meta charset="utf-8"><title>BluMart ORM — Attribution {today}</title>
<style>
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;font-size:13px;padding:16px;background:#f8fafc;color:#0f172a}}
h1{{font-size:20px;margin:0 0 4px}}
.muted{{color:#64748b;font-size:12px}}
.metrics{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:8px;margin:16px 0;padding:12px;background:white;border:1px solid #e2e8f0;border-radius:8px}}
.metric{{display:flex;flex-direction:column}}
.metric .label{{font-size:11px;color:#64748b}}
.metric .value{{font-size:20px;font-weight:600}}
table{{width:100%;border-collapse:collapse;background:white;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden}}
th{{background:#f1f5f9;padding:8px 6px;text-align:left;font-size:11px;text-transform:uppercase;color:#475569;position:sticky;top:0}}
td{{padding:6px;border-bottom:1px solid #f1f5f9;vertical-align:top}}
tr:hover{{background:#f8fafc}}
.filter{{margin:8px 0}}input{{padding:6px;border:1px solid #cbd5e1;border-radius:4px;width:280px}}
</style></head>
<body>
<h1>BluMart ORM — Attribution Table</h1>
<div class="muted">Сгенерировано: {today} · slug: {slug} · INTERNAL (не показывать заказчику)</div>

<div class="metrics">
  <div class="metric"><span class="label">Всего строк в Sheet</span><span class="value">{stats['total']}</span></div>
  <div class="metric"><span class="label">«Отзыв размещён»</span><span class="value">{stats['published']}</span></div>
  <div class="metric"><span class="label">→ Найдено в live</span><span class="value">{stats['confirmed']}</span></div>
  <div class="metric"><span class="label">→ НЕ найдено (удалён/глубже)</span><span class="value" style="color:#dc2626">{stats['not_found']}</span></div>
  <div class="metric"><span class="label">В работе у бирж</span><span class="value">{stats['in_progress']}</span></div>
  <div class="metric"><span class="label">Не прошли / потрачены</span><span class="value" style="color:#dc2626">{stats['rejected']}</span></div>
  <div class="metric"><span class="label">🔁 Нужна дозамена (точно)</span><span class="value" style="color:#dc2626">{stats['replacement_yes']}</span></div>
  <div class="metric"><span class="label">❓ Дозамена под вопросом</span><span class="value" style="color:#d97706">{stats['replacement_maybe']}</span></div>
</div>

{render_tg_block(tg) if tg else ''}

<h2 style="margin-top:24px">🔁 Кого пинговать на дозамену</h2>
{replacement_html}

<h2 style="margin-top:24px">📋 Полная таблица attribution</h2>
<div class="filter"><input type="text" id="filter" placeholder="Фильтр по тексту/исполнителю/категории..." oninput="filterRows()"></div>

<table id="t">
<thead><tr>
<th>Исполнитель</th><th>Категория</th><th>Статус Sheet</th>
<th>Дата заказа</th><th>Дата отзыва</th><th>Автор Sheet</th>
<th>Статус Live</th><th>Автор Live</th><th>Replace</th><th>Текст</th>
</tr></thead>
<tbody>{''.join(body)}</tbody></table>

<script>
function filterRows(){{
  const q=document.getElementById('filter').value.toLowerCase();
  document.querySelectorAll('#t tbody tr').forEach(r=>{{
    r.style.display = r.textContent.toLowerCase().includes(q)?'':'none';
  }});
}}
</script>
</body></html>"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    args = ap.parse_args()

    reg = load_registry(args.slug)
    contractor_map = sheet_to_contractor(reg)

    sheet_rows = load_sheet_rows(args.slug, contractor_map)
    print(f"📋 Sheet rows: {len(sheet_rows)}")

    live = load_live(args.slug)
    print(f"🌐 Live items: {len(live)}")

    # Match каждой строки Sheet с live + флаг "нужна дозамена у исполнителя"
    # BUG-2 fix: greedy assignment (live-review consumed only once).
    # Сортируем: сначала строки с явной date_review (точные), потом без даты.
    today = datetime.now()
    used_live_keys: set = set()

    def sort_key(row: dict) -> tuple[int, str]:
        # 0 = с датой (приоритет), 1 = без → matched первыми с датой
        has_date = 0 if row.get("date_review") else 1
        return (has_date, row.get("date_review") or "")

    for r in sorted(sheet_rows, key=sort_key):
        r["replacement_required"] = "no"
        r["age_days"] = ""
        if r["status_in_sheet"] in ("Отзыв размещён", "Отзыв размещен"):
            m, score = best_match(r["text_norm"], live, threshold=0.75, used_keys=used_live_keys)
            if m:
                used_live_keys.add(_live_key(m))
            # Возраст отзыва (для оценки шанса что он на page 1000+ vs точно удалён)
            try:
                d = datetime.strptime(r["date_review"], "%d.%m.%Y") if r["date_review"] else None
                if d:
                    r["age_days"] = (today - d).days
            except ValueError:
                pass
            if m:
                r["live_status"] = "✅ найден в live"
                r["live_author"] = m.get("author", "")
                r["live_match_score"] = round(score, 2)
            else:
                r["live_status"] = "❌ нет в live (вероятно удалён)"
                r["live_author"] = ""
                r["live_match_score"] = round(score, 2)
                # Логика "вернуться к исполнителю":
                # - публиковался ≥7 дней назад (не свежий что мог не попасть в crawl)
                # - И не найден в live-1000
                # → высокая вероятность что снёс антифрод
                if isinstance(r.get("age_days"), int) and r["age_days"] >= 7:
                    r["replacement_required"] = "yes"
                elif r["age_days"] == "":
                    # Без даты — тоже кандидат (нет инфо когда публиковался)
                    r["replacement_required"] = "maybe"
        else:
            r["live_status"] = "— не публиковался"
            r["live_author"] = ""
            r["live_match_score"] = 0

    # Stats
    stats = {
        "total": len(sheet_rows),
        "published": sum(1 for r in sheet_rows if r["status_in_sheet"] in ("Отзыв размещён", "Отзыв размещен")),
        "confirmed": sum(1 for r in sheet_rows if r["live_status"] == "✅ найден в live"),
        "not_found": sum(1 for r in sheet_rows if r["live_status"].startswith("❌")),
        "in_progress": sum(1 for r in sheet_rows if r["status_in_sheet"] in ("Согласовано, заказ размещён", "Ожидание модерации", "Текст согласован", "Ждет размещения")),
        "rejected": sum(1 for r in sheet_rows if r["status_in_sheet"] in ("Не прошёл модерацию", "Не прошел", "потрачен")),
        "replacement_yes": sum(1 for r in sheet_rows if r["replacement_required"] == "yes"),
        "replacement_maybe": sum(1 for r in sheet_rows if r["replacement_required"] == "maybe"),
    }

    # Группировка "что вернуть какому исполнителю"
    replacement_by_contractor: dict[str, list[dict]] = defaultdict(list)
    for r in sheet_rows:
        if r["replacement_required"] in ("yes", "maybe"):
            replacement_by_contractor[r["contractor"]].append(r)
    print("\n🔁 ВЕРНУТЬ ИСПОЛНИТЕЛЯМ (нужна дозамена):")
    for c, items in sorted(replacement_by_contractor.items(), key=lambda x: -len(x[1])):
        yes_n = sum(1 for r in items if r["replacement_required"] == "yes")
        maybe_n = sum(1 for r in items if r["replacement_required"] == "maybe")
        print(f"  {c}: {len(items)} строк (точно: {yes_n}, под вопросом без даты: {maybe_n})")
    print(f"\n📊 Stats: {stats}")

    # Распределение по исполнителям
    from collections import Counter
    by_contractor = Counter(r["contractor"] for r in sheet_rows)
    print("\nПо исполнителям:")
    for c, n in by_contractor.most_common():
        print(f"  {c}: {n}")

    # Save
    out_dir = ROOT / "clients" / args.slug / "orm"
    today = datetime.now().strftime("%Y-%m-%d")
    csv_path = out_dir / f"attribution-report-{today}.csv"
    html_path = out_dir / f"attribution-report-{today}.html"

    with open(csv_path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=[
            "contractor", "category", "status_in_sheet", "date_order", "date_review",
            "author_in_sheet", "live_status", "live_author", "live_match_score",
            "sheet", "text",
        ])
        writer.writeheader()
        for r in sheet_rows:
            writer.writerow({k: r.get(k, "") for k in writer.fieldnames})

    tg = load_tg_signals(args.slug)
    html_path.write_text(render_html(args.slug, sheet_rows, stats, tg))

    print(f"\n💾 CSV:  {csv_path}")
    print(f"💾 HTML: {html_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
