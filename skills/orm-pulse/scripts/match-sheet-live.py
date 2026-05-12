#!/usr/bin/env python3
"""
orm-pulse: Match Sheet rows ↔ Live reviews (по тексту/автору).

Usage: match-sheet-live.py <client_slug>

Inputs:
  - clients/<slug>/orm/snapshots/latest/*.csv  (Sheet snapshots)
  - /tmp/orm-pulse/<slug>/reviews/in_range.json  (Playwright dump)

Output:
  - /tmp/orm-pulse/<slug>/match/matched.json     — Sheet rows that found live
  - /tmp/orm-pulse/<slug>/match/missing.json     — Sheet says published but not live
  - /tmp/orm-pulse/<slug>/match/organic.json     — Live reviews not in our Sheet
"""
import sys
import csv
import json
import argparse
from pathlib import Path
from difflib import SequenceMatcher

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from lib.config import ROOT  # noqa: E402


def load_registry(slug: str) -> dict:
    return yaml.safe_load((ROOT / "clients" / slug / "orm" / "registry.yaml").read_text())


def normalize(text: str) -> str:
    """Lowercase, strip punctuation, first 100 chars."""
    if not text:
        return ""
    text = text.lower().strip()
    for ch in ",.!?\"'`«»–—-()[]{}":
        text = text.replace(ch, " ")
    return " ".join(text.split())[:100]


def similarity(a: str, b: str) -> float:
    """Fuzzy similarity 0..1."""
    a, b = normalize(a), normalize(b)
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def load_sheet_rows(slug: str) -> list[dict]:
    """Load all Sheet rows from latest snapshot."""
    snapshots = ROOT / "clients" / slug / "orm" / "snapshots" / "latest"
    if not snapshots.exists():
        print(f"⚠️  No latest snapshot. Run sheet-snapshot.sh first.", file=sys.stderr)
        return []

    rows = []
    for csv_file in snapshots.glob("*.csv"):
        if csv_file.name.startswith("_"):
            continue
        try:
            with open(csv_file, encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for i, r in enumerate(reader, start=2):
                    text_col = r.get("Текст отзыва") or r.get("Текст") or ""
                    author_col = r.get("Автор отзыва") or r.get("Автор") or ""
                    status = r.get("Статус") or r.get("Статус размещения") or ""
                    date_заказа = r.get("Дата заказа", "").strip()
                    date_отзыва = r.get("Дата отзыва", "").strip()
                    if not text_col.strip():
                        continue
                    rows.append({
                        "src": csv_file.stem,
                        "row": i,
                        "text": text_col,
                        "author": author_col,
                        "status": status,
                        "date_заказа": date_заказа,
                        "date_отзыва": date_отзыва,
                    })
        except Exception as e:
            print(f"⚠️  Error reading {csv_file}: {e}", file=sys.stderr)
    return rows


def load_live_reviews(slug: str) -> list[dict]:
    """Load Playwright live dump."""
    p = Path("/tmp/orm-pulse") / slug / "reviews" / "in_range.json"
    if not p.exists():
        print(f"⚠️  No live dump. Run playwright-reviews.py first.", file=sys.stderr)
        return []
    return json.loads(p.read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("slug")
    parser.add_argument("--threshold", type=float, default=0.55)
    args = parser.parse_args()

    sheet_rows = load_sheet_rows(args.slug)
    live = load_live_reviews(args.slug)

    print(f"Sheet rows: {len(sheet_rows)}")
    print(f"Live reviews: {len(live)}")

    matched = []
    missing = []  # Sheet «Отзыв размещён» с датой, но не нашли live
    matched_live_ids = set()

    for sheet in sheet_rows:
        best = (0.0, None)
        for i, lv in enumerate(live):
            score = similarity(sheet["text"], lv.get("text", ""))
            # Бонус если автор совпадает
            if sheet.get("author") and lv.get("author"):
                if normalize(sheet["author"]) == normalize(lv["author"]):
                    score = min(1.0, score + 0.2)
            if score > best[0]:
                best = (score, i)

        if best[0] >= args.threshold:
            matched.append({
                "sheet": sheet,
                "live_idx": best[1],
                "live": live[best[1]],
                "score": round(best[0], 3),
            })
            matched_live_ids.add(best[1])
        else:
            # Если в Sheet статус «Отзыв размещён» — это missing-live
            if "размещ" in sheet["status"].lower() and sheet.get("date_отзыва"):
                missing.append({"sheet": sheet, "best_score": round(best[0], 3)})

    organic = [{"live_idx": i, "live": lv} for i, lv in enumerate(live) if i not in matched_live_ids]

    out_dir = Path("/tmp/orm-pulse") / args.slug / "match"
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "matched.json").write_text(json.dumps(matched, ensure_ascii=False, indent=2))
    (out_dir / "missing.json").write_text(json.dumps(missing, ensure_ascii=False, indent=2))
    (out_dir / "organic.json").write_text(json.dumps(organic, ensure_ascii=False, indent=2))

    print(f"\n✅ Matched (наши): {len(matched)}")
    print(f"⚠️  Missing-live (Sheet говорит размещён, live не найден): {len(missing)}")
    print(f"📰 Organic (live, не наши): {len(organic)}")
    print(f"\nSaved to: {out_dir}")


if __name__ == "__main__":
    main()
