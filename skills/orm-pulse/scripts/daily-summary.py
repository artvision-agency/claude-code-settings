#!/usr/bin/env python3
"""daily-summary — короткая сводка ORM-клиента в TG команды.

Источники: /tmp/orm-pulse/<slug>/orders-state.json + reviews-tracker history.
Шлёт в группу команды через ~/.claude/scripts/tg-send.sh team.
БЕЗ rate-limit — это плановая сводка, не critical-алёрт.

Usage:
  daily-summary.py <slug> [--dry-run]
"""
from __future__ import annotations
import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timedelta

ROOT = Path("/Users/antonk/artvision-data")
TG_SEND = Path.home() / ".claude/scripts/tg-send.sh"
SPARK = "▁▂▃▄▅▆▇█"


def load_state(slug: str) -> dict:
    p = Path("/tmp/orm-pulse") / slug / "orders-state.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}


def daily_deltas(slug: str, days: int = 14) -> list[tuple[str, int, int]]:
    """Вернуть [(YYYY-MM-DD, delta_added, delta_removed)] за последние N дней.

    Берёт last_total на каждый день. Если total падает — это антифрод (removed).
    """
    history = ROOT / "clients" / slug / "orm" / "reviews-tracker" / "history.csv"
    if not history.exists():
        return []
    by_day: dict[str, int] = {}
    try:
        for row in csv.DictReader(open(history)):
            ts = row.get("timestamp", "")
            if len(ts) < 10:
                continue
            day = ts[:10]
            try:
                t = int(row.get("total") or 0)
            except (TypeError, ValueError):
                continue
            by_day[day] = t  # последняя строка дня перезатирает
    except Exception:
        return []
    if not by_day:
        return []
    sorted_days = sorted(by_day.keys())
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    sorted_days = [d for d in sorted_days if d >= cutoff]
    if len(sorted_days) < 2:
        return []
    out = []
    prev_total = by_day[sorted_days[0]]
    for day in sorted_days[1:]:
        cur = by_day[day]
        d = cur - prev_total
        added = max(d, 0)
        removed = max(-d, 0)
        out.append((day, added, removed))
        prev_total = cur
    return out


def sparkline(values: list[int]) -> str:
    if not values:
        return ""
    lo, hi = min(values), max(values)
    if hi == lo:
        return SPARK[0] * len(values) if hi == 0 else SPARK[3] * len(values)
    step = (hi - lo) / (len(SPARK) - 1)
    return "".join(SPARK[min(int((v - lo) / step), len(SPARK) - 1)] for v in values)


def compose_message(slug: str, st: dict) -> str:
    sc = st.get("state_counts", {})
    pace = st.get("pace", {})
    qc = st.get("qcomment", {})

    published = sc.get("published", 0)
    delta = pace.get("delta_total", 0)
    days = pace.get("period_days", 0)
    per_day = pace.get("per_day", 0)
    rating = pace.get("rating_now", "?")
    total = pace.get("to_total", "?")

    moderation = sc.get("moderation", 0)
    okpon = sc.get("given_to_okponrussia", 0)
    approved_not_given = sc.get("approved_not_given", 0)
    rejected = sc.get("rejected", 0)
    spent = sc.get("spent", 0)

    qc_pending = qc.get("pending_review", 0)
    qc_balance = qc.get("balance", "?")

    name_map = {"bluemart": "BluMart", "blumart": "BluMart"}
    name = name_map.get(slug, slug)
    now = datetime.now().strftime("%d.%m %H:%M МСК")

    deltas = daily_deltas(slug, days=14)
    spark_added = sparkline([a for _, a, _ in deltas])
    sum_added = sum(a for _, a, _ in deltas)
    sum_removed = sum(r for _, _, r in deltas)
    spark_line = ""
    if deltas:
        first_day = deltas[0][0][5:]   # MM-DD
        last_day = deltas[-1][0][5:]
        spark_line = f"📈 По дням ({first_day}→{last_day}): {spark_added}  +{sum_added}"
        if sum_removed:
            spark_line += f" · Я снёс: -{sum_removed}"

    lines = [
        f"🛒 {name} ORM — сводка {now}",
        "",
        f"✅ Опубликовано: {published} (+{delta} за {days} дн)",
        f"📈 Темп: {per_day:.2f}/день · цель 5",
        f"⭐ Rating: {rating} · Total: {total}",
    ]
    if spark_line:
        lines.append(spark_line)
    lines.extend([
        "",
        f"📤 На модерации Я: {moderation} · okponrussia: {okpon}",
        f"📝 Согласовано НЕ отдан: {approved_not_given}" + (" ⭐ можно раздать" if approved_not_given >= 5 else ""),
    ])
    if rejected or spent:
        lines.append(f"❌ Не прошли модерацию: {rejected} · 💸 Потрачен: {spent}")
    if qc_pending:
        lines.append("")
        lines.append(f"🚨 QComment: {qc_pending} проект(ов) на принятие")
        lines.append(f"   Балaнс: {qc_balance} ₽")
    lines.append("")
    lines.append(f"📊 https://artvision.pro/orm-command-center/{slug}.html")

    return "\n".join(lines)


def send_to_team(message: str, dry_run: bool = False) -> int:
    if dry_run:
        print("[dry-run] Would send to team:")
        print("---")
        print(message)
        print("---")
        return 0
    if not TG_SEND.exists():
        print(f"❌ tg-send.sh not found: {TG_SEND}", file=sys.stderr)
        return 2
    # tg-send.sh может вернуть exit 1 при ошибке парсинга msg_id, но всё равно отправляет.
    # Считаем успехом если в stdout есть "Sent" или "ok".
    proc = subprocess.run(
        [str(TG_SEND), "team", message],
        capture_output=True,
        text=True,
        timeout=30,
    )
    out = proc.stdout + proc.stderr
    if "Sent" in out or '"ok":true' in out:
        print("✅ Sent")
        return 0
    print(f"❌ Send failed (rc={proc.returncode}): {out[:300]}", file=sys.stderr)
    return proc.returncode or 3


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("slug", help="client slug, e.g. bluemart")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    st = load_state(args.slug)
    if not st:
        print(f"❌ orders-state.json not found for {args.slug}", file=sys.stderr)
        return 1
    msg = compose_message(args.slug, st)
    return send_to_team(msg, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
