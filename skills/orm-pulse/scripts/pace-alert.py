#!/usr/bin/env python3
"""Q10 pace-alert — TG-алёрт если темп публикаций отзывов упал ниже порога.

Источник данных: clients/<slug>/orm/live-reviews-history/*.json (снапшоты).
Считает: сколько НОВЫХ отзывов появилось за последние window_hours.
Если темп < min_pace_per_day → TG team alert (rate-limited).

Connect к Q5 (auto-stop): если crawler unhealthy (3+ partials),
pace alert НЕ срабатывает — нет смысла спорить (нет валидных данных).

Usage:
    pace-alert.py <slug> [--dry-run]

decisions/2026-05-10-orm-pace-alert.md
"""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import yaml

ROOT = Path("/Users/antonk/artvision-data")
TG_SEND = Path.home() / ".claude/scripts/tg-send.sh"


def load_registry(slug: str) -> dict:
    p = ROOT / "clients" / slug / "orm" / "registry.yaml"
    return yaml.safe_load(p.read_text()) if p.exists() else {}


def crawler_unhealthy(slug: str) -> tuple[bool, int]:
    """Q5 связь: если crawler unhealthy — не врем о темпе."""
    p = ROOT / "clients" / slug / "orm" / ".crawl-health.json"
    if not p.exists():
        return False, 0
    try:
        h = json.loads(p.read_text())
        cp = int(h.get("consecutive_partials", 0))
        return cp >= 3, cp
    except Exception:
        return False, 0


def find_history_snapshots(slug: str, window_hours: int) -> tuple[Path | None, Path | None]:
    """Найти 2 снапшота: самый свежий и тот что ~window_hours назад."""
    hist_dir = ROOT / "clients" / slug / "orm" / "live-reviews-history"
    if not hist_dir.exists():
        return None, None
    files = sorted(hist_dir.glob("*.json"))
    if len(files) < 2:
        return files[-1] if files else None, None

    newest = files[-1]
    # Имена формата YYYY-MM-DD-HHMM.json — парсим
    target_ts = datetime.now() - timedelta(hours=window_hours)
    older = None
    best_delta = timedelta.max
    for f in files[:-1]:
        try:
            ts = datetime.strptime(f.stem, "%Y-%m-%d-%H%M")
        except ValueError:
            continue
        delta = abs(ts - target_ts)
        if delta < best_delta:
            best_delta = delta
            older = f
    return newest, older


def count_items_diff(newest: Path, older: Path | None) -> tuple[int, int, int]:
    """Возвращает (new_count, old_count, new_added)."""
    new_data = json.loads(newest.read_text())
    new_items = new_data.get("items", [])
    new_keys = {(i.get("author", ""), (i.get("text") or "")[:80]) for i in new_items}

    if not older:
        return len(new_items), 0, 0

    old_data = json.loads(older.read_text())
    old_items = old_data.get("items", [])
    old_keys = {(i.get("author", ""), (i.get("text") or "")[:80]) for i in old_items}

    added = len(new_keys - old_keys)
    return len(new_items), len(old_items), added


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    reg = load_registry(args.slug)
    pace_cfg = reg.get("pace_alert", {})
    min_pace = float(pace_cfg.get("min_pace_per_day", 0.5))
    window_h = int(pace_cfg.get("window_hours", 24))
    rate_limit_h = int(pace_cfg.get("rate_limit_hours", 24))

    # Q5: если crawler нездоров — пропускаем (false-pace неинформативен)
    unhealthy, cp = crawler_unhealthy(args.slug)
    if unhealthy:
        print(f"⏸ Pace check skipped: crawler unhealthy (consecutive_partials={cp})")
        return 0

    newest, older = find_history_snapshots(args.slug, window_h)
    if not newest:
        print(f"❌ Нет history snapshots в {args.slug}/orm/live-reviews-history/", file=sys.stderr)
        return 1
    if not older:
        print(f"ℹ️ Только 1 snapshot, нечего сравнивать с window {window_h}h")
        return 0

    new_count, old_count, added = count_items_diff(newest, older)

    # Темп = добавилось за окно / (окно в днях)
    days = window_h / 24.0
    pace = added / days if days > 0 else 0.0

    print(f"📊 Pace report for {args.slug}:")
    print(f"   newest snapshot: {newest.name} ({new_count} items)")
    print(f"   older snapshot:  {older.name} ({old_count} items)")
    print(f"   added in window {window_h}h: {added}")
    print(f"   pace: {pace:.2f}/day (min {min_pace}/day)")

    if pace >= min_pace:
        print(f"✅ темп в норме — алёрт не нужен")
        return 0

    # Rate-limit
    rate_path = Path(f"{Path.home()}/.claude/state/orm-pulse/{args.slug}-pace-alert-last")
    rate_path.parent.mkdir(parents=True, exist_ok=True)
    now = int(time.time())
    if rate_path.exists():
        try:
            last = int(rate_path.read_text().strip())
            if now - last < rate_limit_h * 3600:
                print(f"⏸ Алёрт rate-limited ({now - last}s < {rate_limit_h*3600}s)")
                return 0
        except Exception:
            pass

    msg = (
        f"⚠️ {args.slug}: темп публикаций упал\n"
        f"За {window_h}ч добавлено {added} отзывов = {pace:.2f}/день (норма ≥{min_pace}/день)\n"
        f"Snapshot: {newest.stem} vs {older.stem}\n"
        f"Проверь: replacement-pinger логи, статус подрядчиков, qcomment баланс."
    )
    if args.dry_run:
        print(f"[DRY-RUN] would send:\n{msg}")
    elif TG_SEND.exists():
        subprocess.run([str(TG_SEND), "team", msg], timeout=15)
        print(f"🚨 Алёрт отправлен в TG team")
    rate_path.write_text(str(now))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
