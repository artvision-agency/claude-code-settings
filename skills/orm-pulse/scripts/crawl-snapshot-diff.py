#!/usr/bin/env python3
"""crawl-snapshot-diff — поштучный diff отзывов между запусками.

Запускается через LaunchAgent раз в час. Шаги:
  1. Прогоняет playwright-full-crawl.py (~600 свежих отзывов)
  2. Сохраняет snapshot в clients/<slug>/orm/live-reviews/<TS>.json
  3. Сравнивает с предыдущим snapshot:
     - removed = были в prev, нет в curr (с key=(user_id, text[:80]))
     - added   = в curr, не было в prev
  4. Если removed > 0 → алёрт в TG team с поимённой расшифровкой
  5. Сохраняет diff в clients/<slug>/orm/live-diffs/<TS>.json

Usage:
  crawl-snapshot-diff.py <slug> [--dry-run] [--no-crawl]
"""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path("/Users/antonk/artvision-data")
TG_SEND = Path.home() / ".claude/scripts/tg-send.sh"
CRAWLER = Path.home() / ".claude/skills/orm-pulse/scripts/playwright-full-crawl.py"

# Sanity floor: если crawl выдал < MIN_REVIEWS_FLOOR ИЛИ < SANITY_RATIO * len(prev),
# считаем crawl сломанным — НЕ архивируем, НЕ шлём removed-алёрт. Только TG-warn.
MIN_REVIEWS_FLOOR = 500
SANITY_RATIO = 0.7


def review_key(item: dict) -> str:
    """Стабильный hash-ключ. Не зависит от текста (устойчив к edit'ам автора).

    Состав: user_id + author (lower) + date + rating.
    Анонимные (user_id="") получают разные ключи если различается author/date/rating.
    """
    uid = (item.get("user_id") or "").strip()
    author = (item.get("author") or "").strip().lower()
    date = (item.get("date") or "").strip()
    rating = str(item.get("rating") or "").strip()
    base = f"{uid}|{author}|{date}|{rating}"
    return hashlib.sha1(base.encode("utf-8")).hexdigest()[:16]


def run_crawl(slug: str, max_pages: int = 80) -> Path | None:
    """Запустить playwright-full-crawl.py, вернуть путь к свежему snapshot."""
    cmd = ["python3", str(CRAWLER), slug, "--max-pages", str(max_pages)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        print(f"❌ crawler failed: {proc.stderr[:500]}", file=sys.stderr)
        return None
    # Берём самый свежий snapshot из стабильной директории
    stable = ROOT / "clients" / slug / "orm" / "live-reviews"
    today_file = stable / f"{datetime.now().strftime('%Y-%m-%d')}.json"
    if today_file.exists():
        return today_file
    candidates = sorted(stable.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def find_prev_snapshot_in_history(slug: str) -> Path | None:
    """Вернуть самый свежий архивный snapshot из history.

    КРИТИЧНО: вызывать ДО архивации текущего, иначе current и prev будут одинаковыми.
    """
    history_dir = ROOT / "clients" / slug / "orm" / "live-reviews-history"
    history_dir.mkdir(parents=True, exist_ok=True)
    candidates = sorted(history_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def compose_alert(slug: str, removed: list[dict], added: list[dict]) -> str:
    name_map = {"bluemart": "BluMart", "blumart": "BluMart"}
    name = name_map.get(slug, slug)
    now = datetime.now().strftime("%d.%m %H:%M МСК")
    lines = [f"🚨 {name} ORM — ИЗМЕНЕНИЯ В LIVE {now}", ""]
    if removed:
        lines.append(f"❌ ИСЧЕЗЛО ОТЗЫВОВ: {len(removed)}")
        for it in removed[:15]:
            author = it.get("author", "?")
            rating = it.get("rating", "?")
            date = it.get("date", "—")
            text = (it.get("text", "") or "")[:80].replace("\n", " ")
            lines.append(f"  • {author} ({rating}⭐, {date}) — {text}…")
        if len(removed) > 15:
            lines.append(f"  • _и ещё {len(removed)-15}_")
        lines.append("")
    if added:
        lines.append(f"✅ ПОЯВИЛОСЬ НОВЫХ: {len(added)}")
        for it in added[:5]:
            author = it.get("author", "?")
            rating = it.get("rating", "?")
            date = it.get("date", "—")
            lines.append(f"  • {author} ({rating}⭐, {date})")
        if len(added) > 5:
            lines.append(f"  • _и ещё {len(added)-5}_")
        lines.append("")
    lines.append(f"📊 https://artvision.pro/orm-command-center/{slug}.html")
    return "\n".join(lines)


def send_tg(message: str) -> bool:
    if not TG_SEND.exists():
        print(f"❌ {TG_SEND} not found", file=sys.stderr)
        return False
    proc = subprocess.run([str(TG_SEND), "team", message], capture_output=True, text=True, timeout=30)
    out = proc.stdout + proc.stderr
    if "Sent" in out or '"ok":true' in out:
        return True
    print(f"❌ TG send failed: {out[:200]}", file=sys.stderr)
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--dry-run", action="store_true", help="не слать TG, не запускать crawl, читать существующий snapshot")
    ap.add_argument("--no-crawl", action="store_true", help="использовать существующий snapshot, не делать новый")
    args = ap.parse_args()

    history_dir = ROOT / "clients" / args.slug / "orm" / "live-reviews-history"
    history_dir.mkdir(parents=True, exist_ok=True)
    diff_dir = ROOT / "clients" / args.slug / "orm" / "live-diffs"
    diff_dir.mkdir(parents=True, exist_ok=True)

    # Получить current snapshot
    if args.no_crawl or args.dry_run:
        stable = ROOT / "clients" / args.slug / "orm" / "live-reviews"
        candidates = sorted(stable.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        current_path = candidates[0] if candidates else None
        if not current_path:
            print("❌ No existing snapshot for --no-crawl mode", file=sys.stderr)
            return 1
    else:
        current_path = run_crawl(args.slug)
        if not current_path:
            print("❌ Crawl failed, abort", file=sys.stderr)
            return 1

    current_data = json.loads(current_path.read_text())
    current_items = current_data.get("items", [])
    print(f"📋 Current snapshot: {current_path.name} ({len(current_items)} items)")

    # 1. Найти prev snapshot ИЗ ИСТОРИИ — ДО архивации (баг B: иначе current==prev на след. запуске)
    prev_path = find_prev_snapshot_in_history(args.slug)

    # 2. SANITY FLOOR (A): прерываемся при подозрительно малом crawl
    abort_reason = None
    if len(current_items) < MIN_REVIEWS_FLOOR:
        abort_reason = f"crawl={len(current_items)} < MIN_FLOOR={MIN_REVIEWS_FLOOR}"
    elif prev_path:
        prev_size_check = len(json.loads(prev_path.read_text()).get("items", []))
        if prev_size_check >= MIN_REVIEWS_FLOOR and len(current_items) < SANITY_RATIO * prev_size_check:
            abort_reason = f"crawl={len(current_items)} < {SANITY_RATIO * 100:.0f}% × prev={prev_size_check}"

    if abort_reason:
        warn = (
            f"⚠️ {args.slug} crawl ABORTED: {abort_reason}\n"
            f"Возможные причины: yandex-captcha, селекторы сменились, network. "
            f"НЕ архивируем, НЕ шлём removed-алёрт. Ручная проверка."
        )
        print(warn, file=sys.stderr)
        if not args.dry_run:
            send_tg(warn)
        return 2

    # 3. Первый запуск — нет prev → архивируем current и выходим
    if not prev_path:
        ts = datetime.now().strftime("%Y-%m-%d-%H%M")
        archive_path = history_dir / f"{ts}.json"
        archive_path.write_text(current_path.read_text())
        print(f"ℹ️  Первый snapshot сохранён в историю: {archive_path}")
        print(f"  Diff будет на следующем запуске")
        return 0

    # 4. Diff
    current_keys = {review_key(it): it for it in current_items}
    prev_data = json.loads(prev_path.read_text())
    prev_items = prev_data.get("items", [])
    prev_keys = {review_key(it): it for it in prev_items}
    print(f"📦 Prev snapshot: {prev_path.name} ({len(prev_items)} items)")

    removed_keys = set(prev_keys) - set(current_keys)
    added_keys = set(current_keys) - set(prev_keys)
    removed = [prev_keys[k] for k in removed_keys]
    added = [current_keys[k] for k in added_keys]

    print(f"\n📊 DIFF:")
    print(f"  Removed: {len(removed)}")
    print(f"  Added:   {len(added)}")

    # 5. Архивируем current — ПОСЛЕ diff (фикс B)
    ts = datetime.now().strftime("%Y-%m-%d-%H%M")
    archive_path = history_dir / f"{ts}.json"
    archive_path.write_text(current_path.read_text())

    # Сохраняем diff
    diff_payload = {
        "generated": datetime.now().isoformat(),
        "current_snapshot": current_path.name,
        "prev_snapshot": prev_path.name,
        "current_size": len(current_items),
        "prev_size": len(prev_items),
        "removed_count": len(removed),
        "added_count": len(added),
        "removed": removed,
        "added": added,
    }
    diff_path = diff_dir / f"{ts}.json"
    diff_path.write_text(json.dumps(diff_payload, ensure_ascii=False, indent=2))
    print(f"💾 Diff: {diff_path}")

    if removed:
        print("\n❌ ИСЧЕЗЛИ ОТЗЫВЫ ПОИМЁННО:")
        for it in removed:
            print(f"  - {it.get('author','?')} ({it.get('rating','?')}⭐, {it.get('date','—')}) {(it.get('text','') or '')[:60]!r}")

    # TG алёрт если есть removed
    if removed and not args.dry_run:
        msg = compose_alert(args.slug, removed, added)
        if send_tg(msg):
            print("✅ TG alert sent")
        else:
            print("❌ TG alert failed", file=sys.stderr)
    elif removed and args.dry_run:
        print("\n[dry-run] Would send alert:")
        print(compose_alert(args.slug, removed, added))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
