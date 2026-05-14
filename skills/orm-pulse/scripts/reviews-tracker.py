#!/usr/bin/env python3
"""
orm-pulse: Reviews Yandex.ru tracker — снимает периодические снапшоты
страницы отзывов магазина и фиксирует delta (новые/удалённые/вернувшиеся).

Usage: reviews-tracker.py <client_slug>

Запускать через cron/LaunchAgent N раз в день.

Output:
  ~/artvision-data/clients/<slug>/orm/reviews-tracker/
    snap-{YYYY-MM-DD-HHMM}.json   — всё что найдено в момент запуска (rating + review_ids + meta)
    delta-{YYYY-MM-DD-HHMM}.json  — diff vs предыдущий snapshot
    history.csv                    — append: timestamp, total, rating, new_count, removed_count
"""
import sys
import json
import re
import argparse
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime
import yaml

sys.path.insert(0, str(Path(__file__).parent))
from lib.config import ROOT  # noqa: E402


def load_registry(slug: str) -> dict:
    return yaml.safe_load((ROOT / "clients" / slug / "orm" / "registry.yaml").read_text())


def fetch_html(url: str) -> str:
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def extract_data(html: str) -> dict:
    """Reviews.yandex.ru хранит данные в встроенном JSON.
    Patterns: "rating":2.9... / "reviewsCount":3075 / "ratingCount":3250 / "id":"<UUID>" / "publishTime":"2026-05-01..."
    """
    out = {"reviews": [], "rating": None, "total": None, "rating_count": None}

    # Rating
    m = re.search(r'"rating":\s*([0-9.]+)', html)
    if m:
        try:
            out["rating"] = round(float(m.group(1)), 1)
        except ValueError:
            pass

    # Total reviews
    m = re.search(r'"reviewsCount":\s*(\d+)', html)
    if m:
        out["total"] = int(m.group(1))

    # Rating count (отдельно от reviews count)
    m = re.search(r'"ratingCount":\s*(\d+)', html)
    if m:
        out["rating_count"] = int(m.group(1))

    # Review IDs (UUIDs)
    # Паттерн "id":"<UUID>" встречается не только у отзывов, поэтому фильтруем —
    # берём только те, у которых рядом есть "publishTime" или "rating" (это отзыв, а не сущность shop)
    review_blocks = re.findall(r'"id":"([A-Za-z0-9_-]{20,})"[^}]*?"publishTime"', html)
    out["reviews"] = sorted(set(review_blocks))

    return out


def diff(prev: dict, curr: dict) -> dict:
    prev_ids = set(prev.get("reviews", []) or [])
    curr_ids = set(curr.get("reviews", []) or [])
    return {
        "new_review_ids": sorted(curr_ids - prev_ids),
        "removed_review_ids": sorted(prev_ids - curr_ids),
        "rating_change": (curr.get("rating") or 0) - (prev.get("rating") or 0),
        "total_change": (curr.get("total") or 0) - (prev.get("total") or 0),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("slug")
    args = parser.parse_args()

    registry = load_registry(args.slug)
    url = registry["platform"]["url"]

    out_dir = ROOT / "clients" / args.slug / "orm" / "reviews-tracker"
    out_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M")

    print(f"→ Fetch {url}")
    try:
        html = fetch_html(url)
    except urllib.error.URLError as e:
        print(f"❌ HTTP error: {e}")
        sys.exit(1)

    data = extract_data(html)
    data["fetched_at"] = datetime.now().isoformat()
    data["url"] = url

    snap_path = out_dir / f"snap-{timestamp}.json"
    snap_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"✓ Snapshot: {snap_path}")
    print(f"  rating={data.get('rating')}, total={data.get('total')}, review_ids extracted={len(data.get('reviews', []))}")

    # Найти предыдущий snapshot
    prev_snaps = sorted(out_dir.glob("snap-*.json"))
    d = {"new_review_ids": [], "removed_review_ids": [], "rating_change": 0, "total_change": 0}
    if len(prev_snaps) >= 2:
        prev_data = json.loads(prev_snaps[-2].read_text())
        d = diff(prev_data, data)
        delta_path = out_dir / f"delta-{timestamp}.json"
        delta_path.write_text(json.dumps({
            "from": prev_snaps[-2].stem,
            "to": snap_path.stem,
            **d,
        }, ensure_ascii=False, indent=2))
        print(f"\n📊 Delta vs {prev_snaps[-2].stem}:")
        print(f"  new IDs:     {len(d['new_review_ids'])}")
        print(f"  removed IDs: {len(d['removed_review_ids'])} ⚠️" if d['removed_review_ids'] else f"  removed IDs: 0")
        print(f"  rating Δ:    {d['rating_change']:+.2f}")
        print(f"  total Δ:     {d['total_change']:+d}")

        # Алёрт если удаления
        if d['removed_review_ids']:
            print(f"\n🚨 УДАЛЕНИЕ ОТЗЫВОВ ОБНАРУЖЕНО ({len(d['removed_review_ids'])} шт.):")
            for rid in d['removed_review_ids']:
                print(f"   - {rid}")

    # History CSV
    history_path = out_dir / "history.csv"
    new_count = len(d["new_review_ids"])
    removed_count = len(d["removed_review_ids"])
    if not history_path.exists():
        history_path.write_text("timestamp,total,rating,new_count,removed_count\n")
    with open(history_path, "a") as f:
        f.write(f"{timestamp},{data.get('total','')},{data.get('rating','')},{new_count},{removed_count}\n")

    print(f"\n📈 History: {history_path}")


if __name__ == "__main__":
    main()
