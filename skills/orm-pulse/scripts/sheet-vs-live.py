#!/usr/bin/env python3
"""sheet-vs-live — match нашего Sheet с тем что реально на reviews.yandex.ru.

Источники:
  - Sheet snapshot: clients/<slug>/orm/snapshots/latest/*.csv
  - Live: JSON-LD из https://reviews.yandex.ru/shop/<domain> (топ-25 свежих)

Match: нечёткий по reviewBody (нормализация → SequenceMatcher 0.85+).

Output:
  /tmp/orm-pulse/<slug>/sheet-vs-live.json
  clients/<slug>/orm/sheet-vs-live-{date}.md  (отчёт)

Usage:
  sheet-vs-live.py <slug>
"""
from __future__ import annotations
import argparse
import csv
import json
import re
import sys
import urllib.request
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from lib.config import ROOT  # noqa: E402

PUBLISHED_STATUSES = {"Отзыв размещён", "Отзыв размещен"}


def load_registry(slug: str) -> dict:
    return yaml.safe_load((ROOT / "clients" / slug / "orm" / "registry.yaml").read_text())


def normalize(s: str) -> str:
    s = s.lower().replace("ё", "е")
    s = re.sub(r"[^\wа-я0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def load_sheet_published(slug: str) -> list[dict]:
    """Из всех CSV в snapshots/latest/ — взять строки со статусом 'Отзыв размещён'."""
    snap_dir = ROOT / "clients" / slug / "orm" / "snapshots" / "latest"
    if not snap_dir.exists():
        return []
    out = []
    for csv_file in sorted(snap_dir.glob("*.csv")):
        with open(csv_file) as f:
            rows = list(csv.DictReader(f))
        if not rows:
            continue
        status_col = next((c for c in rows[0].keys() if c.startswith("Статус")), None)
        text_col = next((c for c in rows[0].keys() if "Текст" in c), None)
        date_col = next((c for c in rows[0].keys() if "Дата отзыва" in c), None)
        author_col = next((c for c in rows[0].keys() if "Автор отзыва" in c or c == "Автор"), None)
        if not (status_col and text_col):
            continue
        for r in rows:
            status = (r.get(status_col) or "").strip()
            text = (r.get(text_col) or "").strip()
            if status in PUBLISHED_STATUSES and text:
                out.append({
                    "sheet": csv_file.name,
                    "status": status,
                    "text": text,
                    "text_norm": normalize(text),
                    "author": (r.get(author_col) or "").strip() if author_col else "",
                    "date_review": (r.get(date_col) or "").strip() if date_col else "",
                    "category": (r.get("Категория товара") or "").strip(),
                })
    return out


def fetch_live_jsonld(url: str) -> list[dict]:
    """Тянет страницу reviews.yandex.ru/shop/<domain>, парсит JSON-LD (топ-25)."""
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        html = resp.read().decode("utf-8", errors="replace")
    m = re.search(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL)
    if not m:
        return []
    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError:
        return []
    out = []
    for r in data.get("review", []) or []:
        body = r.get("reviewBody", "") or ""
        out.append({
            "author": (r.get("author") or {}).get("name", ""),
            "rating": (r.get("reviewRating") or {}).get("ratingValue", ""),
            "text": body,
            "text_norm": normalize(body),
            "source": "json-ld",
            "date_iso": "",
        })
    return out


def load_live_crawl(slug: str) -> list[dict]:
    """Берёт самый большой/свежий crawl из /tmp/orm-pulse/<slug>/full-crawl/."""
    crawl_dir = Path("/tmp/orm-pulse") / slug / "full-crawl"
    if not crawl_dir.exists():
        return []
    candidates = sorted(crawl_dir.glob("*.json"), key=lambda p: p.stat().st_size, reverse=True)
    if not candidates:
        return []
    largest = candidates[0]
    try:
        data = json.loads(largest.read_text())
    except Exception:
        return []
    out = []
    for it in data.get("items", []):
        text = it.get("text", "") or ""
        out.append({
            "author": it.get("author", ""),
            "rating": it.get("rating", ""),
            "text": text,
            "text_norm": normalize(text),
            "date_iso": it.get("date_iso", ""),
            "source": f"crawl:{largest.name}",
        })
    return out


def best_match(needle_norm: str, hay: list[dict], threshold: float = 0.75) -> tuple[dict | None, float]:
    if not needle_norm or not hay:
        return None, 0.0
    best, best_score = None, 0.0
    for h in hay:
        s = SequenceMatcher(None, needle_norm, h["text_norm"]).ratio()
        if s > best_score:
            best, best_score = h, s
    if best_score >= threshold:
        return best, best_score
    return None, best_score


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    args = ap.parse_args()

    reg = load_registry(args.slug)
    url = reg["platform"]["url"]

    sheet_pub = load_sheet_published(args.slug)
    print(f"📋 Sheet 'Отзыв размещён': {len(sheet_pub)} записей")

    # Приоритет — full-crawl (если есть). Fallback на JSON-LD.
    live = load_live_crawl(args.slug)
    if live:
        print(f"🌐 Live full-crawl: {len(live)} отзывов (источник: {live[0].get('source','?')})")
    else:
        live = fetch_live_jsonld(url)
        print(f"🌐 Live JSON-LD на {url}: {len(live)} отзывов")

    if not live:
        print("❌ Не удалось получить live данные", file=sys.stderr)
        return 1

    # Match каждой записи Sheet с live
    confirmed = []
    not_confirmed = []
    for s in sheet_pub:
        m, score = best_match(s["text_norm"], live, threshold=0.75)
        if m:
            confirmed.append({**s, "live_author": m["author"], "live_rating": m["rating"], "match_score": round(score, 2)})
        else:
            not_confirmed.append({**s, "best_score": round(score, 2)})

    # Live отзывы которые НЕ найдены в Sheet — органика или чужие
    organic = []
    for liv in live:
        m, score = best_match(liv["text_norm"], sheet_pub, threshold=0.75)
        if not m:
            organic.append({**liv, "best_score": round(score, 2)})

    # Группировка по месяцам (по date_review из Sheet)
    by_month: dict[str, dict[str, int]] = {}
    for s in sheet_pub:
        d = s.get("date_review", "")
        m_match = re.match(r"(\d{2})\.(\d{2})\.(\d{4})", d)
        if m_match:
            month = f"{m_match.group(3)}-{m_match.group(2)}"
        else:
            month = "—"
        if month not in by_month:
            by_month[month] = {"sheet_published": 0, "live_confirmed": 0}
        by_month[month]["sheet_published"] += 1
    for c in confirmed:
        d = c.get("date_review", "")
        m_match = re.match(r"(\d{2})\.(\d{2})\.(\d{4})", d)
        if m_match:
            month = f"{m_match.group(3)}-{m_match.group(2)}"
        else:
            month = "—"
        if month in by_month:
            by_month[month]["live_confirmed"] += 1

    # Save artifacts
    out_dir = ROOT / "clients" / args.slug / "orm"
    today = datetime.now().strftime("%Y-%m-%d")
    md_path = out_dir / f"sheet-vs-live-{today}.md"
    json_path = Path("/tmp/orm-pulse") / args.slug / "sheet-vs-live.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps({
        "generated": datetime.now().isoformat(),
        "url": url,
        "sheet_published_total": len(sheet_pub),
        "live_jsonld_total": len(live),
        "confirmed": confirmed,
        "not_confirmed": not_confirmed,
        "organic_or_unknown_in_live": organic,
        "by_month": by_month,
    }, ensure_ascii=False, indent=2))

    # Markdown report
    lines = [
        f"# BluMart — Sheet vs Live ({today})",
        "",
        f"**Источник Sheet:** snapshots/latest (4 табов)",
        f"**Источник Live:** {url} (JSON-LD топ-25 свежих, ВНИМАНИЕ: не покрывает все 3079 отзывов)",
        "",
        "## Цифры",
        "",
        f"- 📋 Sheet «Отзыв размещён»: **{len(sheet_pub)}**",
        f"- 🌐 Live JSON-LD (топ-25 свежих): **{len(live)}**",
        f"- ✅ Подтверждено матчем (Sheet→Live): **{len(confirmed)}**",
        f"- ❌ Sheet говорит «размещён», но в live (топ-25) НЕ найдено: **{len(not_confirmed)}** (могут быть глубже первой страницы или сняты антифродом)",
        f"- 🌱 В live (топ-25) НЕТ соответствия в Sheet: **{len(organic)}** (органика или чужой источник)",
        "",
        "## По месяцам (даты из Sheet)",
        "",
        "| Месяц | Sheet «размещён» | Подтверждено в live |",
        "|-------|-----------------:|--------------------:|",
    ]
    for month in sorted(by_month.keys()):
        m = by_month[month]
        lines.append(f"| {month} | {m['sheet_published']} | {m['live_confirmed']} |")
    lines.extend([
        "",
        "## ⚠️ Ограничение этого отчёта",
        "",
        "Live JSON-LD у reviews.yandex.ru = только топ-25 свежих отзывов.",
        f"Из {len(sheet_pub)} «Отзыв размещён» в Sheet проверены лишь те, чей текст попал в топ-25.",
        "Для полного покрытия (~3079 отзывов) нужен Playwright-crawl всех страниц или Yandex Maps API fetchReviews.",
        "",
        "## ✅ Подтверждённые матчи (Sheet → Live)",
        "",
    ])
    for c in confirmed[:50]:
        lines.append(f"- **{c.get('author','?')}** ({c['date_review'] or '—'}, score={c['match_score']}) — {c['text'][:80]}…")
    if len(confirmed) > 50:
        lines.append(f"- _и ещё {len(confirmed)-50}_")

    lines.extend(["", "## 🌱 Органика или чужой источник (в live, не в нашем Sheet)", ""])
    for o in organic[:30]:
        lines.append(f"- **{o.get('author','?')}** (rating={o['rating']}, best match score={o['best_score']}) — {o['text'][:80]}…")

    md_path.write_text("\n".join(lines))
    print(f"\n💾 JSON: {json_path}")
    print(f"💾 MD:   {md_path}")

    # Сводка в stdout
    print(f"\n========== СВОДКА ==========")
    print(f"Sheet «Отзыв размещён»:   {len(sheet_pub)}")
    print(f"Live JSON-LD (топ-25):    {len(live)}")
    print(f"Подтверждено матчем:      {len(confirmed)}")
    print(f"Sheet→Live not found:     {len(not_confirmed)}")
    print(f"Органика в live:          {len(organic)}")
    print(f"\nПо месяцам:")
    for month in sorted(by_month.keys()):
        m = by_month[month]
        print(f"  {month}: Sheet={m['sheet_published']:>3} · live confirmed={m['live_confirmed']:>3}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
