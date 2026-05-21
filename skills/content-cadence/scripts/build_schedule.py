#!/usr/bin/env python3
"""
Content Cadence — Ramp-up schedule builder.

Алгоритм: day(n) = min(target_daily_max, ceil(n/3))
Натуральное нарастание публикаций, имитация роста активного блога.

Usage:
    python3 build_schedule.py --count 50 --start 2026-05-26 --output schedule.json
    python3 build_schedule.py --articles articles.txt --start 2026-05-26 --output schedule.json
    python3 build_schedule.py --count 100 --target-daily-max 7 --no-weekdays-only

Output: schedule.json
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path


# Праздники РФ 2026 (упрощённо: основные нерабочие дни)
RU_HOLIDAYS_2026 = {
    "2026-01-01", "2026-01-02", "2026-01-05", "2026-01-06", "2026-01-07", "2026-01-08",
    "2026-02-23", "2026-03-09", "2026-05-01", "2026-05-04", "2026-05-11",
    "2026-06-12", "2026-11-04",
}
RU_HOLIDAYS_2027 = {
    "2027-01-01", "2027-01-04", "2027-01-05", "2027-01-06", "2027-01-07", "2027-01-08",
    "2027-02-23", "2027-03-08", "2027-05-03", "2027-05-10",
    "2027-06-14", "2027-11-04",
}
ALL_HOLIDAYS = RU_HOLIDAYS_2026 | RU_HOLIDAYS_2027


def is_working_day(d: date, weekdays_only: bool, skip_holidays: bool) -> bool:
    """Является ли день рабочим (с учётом weekend/holidays)."""
    if weekdays_only and d.weekday() >= 5:  # Sat=5, Sun=6
        return False
    if skip_holidays and d.isoformat() in ALL_HOLIDAYS:
        return False
    return True


def ramp_up_posts(day_n: int, target_daily_max: int, start_offset: int = 0) -> int:
    """
    Кол-во постов в день N.

    day(n) = min(target_max, ceil((n + start_offset) / 3))

    start_offset > 0 = mode='resume', блог уже активен, начинаем с day=offset+1
    """
    effective_n = day_n + start_offset
    return min(target_daily_max, math.ceil(effective_n / 3))


def jittered_time(window_start: time, window_end: time, jitter_minutes: int = 30) -> time:
    """
    Случайное время в окне ± jitter, не выходя за границы.
    """
    start_min = window_start.hour * 60 + window_start.minute
    end_min = window_end.hour * 60 + window_end.minute

    # Распределяем равномерно в окне
    pick_min = random.randint(start_min, end_min)
    # Добавляем jitter, потом клампим обратно в окно
    pick_min += random.randint(-jitter_minutes, jitter_minutes)
    pick_min = max(start_min, min(end_min, pick_min))

    return time(hour=pick_min // 60, minute=pick_min % 60)


def parse_hour_window(spec: str) -> tuple[time, time]:
    """'09:00-11:00' → (time(9,0), time(11,0))"""
    a, b = spec.split("-")
    ah, am = map(int, a.split(":"))
    bh, bm = map(int, b.split(":"))
    return time(ah, am), time(bh, bm)


def build_schedule(
    article_count: int,
    start_date: date,
    target_daily_max: int = 5,
    weekdays_only: bool = True,
    skip_holidays: bool = True,
    hour_window: tuple[time, time] = (time(9, 0), time(11, 0)),
    jitter_minutes: int = 30,
    articles: list[str] | None = None,
    start_offset: int = 0,
    client: str = "unknown",
    seed: int | None = None,
) -> dict:
    """
    Построить расписание ramp-up.

    Returns dict с метаданными + items[] для записи в JSON.
    """
    if seed is not None:
        random.seed(seed)

    if articles is None:
        articles = [f"article-{i + 1}" for i in range(article_count)]
    else:
        article_count = len(articles)

    items: list[dict] = []
    article_idx = 0
    day_n = 0
    current_date = start_date
    max_days_safety = article_count * 5 + 60  # защита от бесконечного цикла
    iter_count = 0

    while article_idx < article_count and iter_count < max_days_safety:
        iter_count += 1
        if not is_working_day(current_date, weekdays_only, skip_holidays):
            items.append({
                "day": None,
                "date": current_date.isoformat(),
                "time": None,
                "article_idx": None,
                "article": None,
                "status": "skipped_non_working",
            })
            current_date += timedelta(days=1)
            continue

        day_n += 1
        posts_today = ramp_up_posts(day_n, target_daily_max, start_offset)
        posts_today = min(posts_today, article_count - article_idx)

        # Распределить N постов по часовому окну (внутри одного дня)
        times_today: list[time] = sorted({
            jittered_time(hour_window[0], hour_window[1], jitter_minutes)
            for _ in range(posts_today * 2)  # genereruem с запасом для dedup
        })[:posts_today]
        # Если из-за dedup получилось меньше — добиваем последовательно
        while len(times_today) < posts_today:
            times_today.append(jittered_time(hour_window[0], hour_window[1], jitter_minutes))
        times_today = sorted(times_today)

        for t in times_today:
            items.append({
                "day": day_n,
                "date": current_date.isoformat(),
                "time": t.strftime("%H:%M"),
                "article_idx": article_idx,
                "article": articles[article_idx],
                "status": "scheduled",
            })
            article_idx += 1

        current_date += timedelta(days=1)

    if article_idx < article_count:
        sys.stderr.write(
            f"WARN: safety cap hit, scheduled {article_idx}/{article_count} articles. "
            f"Increase target_daily_max or check holidays config.\n"
        )

    return {
        "client": client,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "start_date": start_date.isoformat(),
        "target_daily_max": target_daily_max,
        "weekdays_only": weekdays_only,
        "skip_holidays": skip_holidays,
        "hour_window": [hour_window[0].strftime("%H:%M"), hour_window[1].strftime("%H:%M")],
        "jitter_minutes": jitter_minutes,
        "start_offset": start_offset,
        "total_articles": article_count,
        "total_scheduled": sum(1 for it in items if it["status"] == "scheduled"),
        "total_days_with_posts": len({it["date"] for it in items if it["status"] == "scheduled"}),
        "items": items,
    }


def print_summary(schedule: dict) -> None:
    """Краткая таблица в stderr для UX."""
    from collections import Counter
    per_day = Counter(
        (it["date"], it["day"]) for it in schedule["items"] if it["status"] == "scheduled"
    )
    sys.stderr.write(f"\n=== Schedule for {schedule['client']} ===\n")
    sys.stderr.write(f"Total articles: {schedule['total_articles']}\n")
    sys.stderr.write(f"Working days used: {schedule['total_days_with_posts']}\n")
    sys.stderr.write(f"Target daily max: {schedule['target_daily_max']}\n\n")
    sys.stderr.write(f"{'Day':>4}  {'Date':<12}  Posts\n")
    sys.stderr.write("-" * 30 + "\n")
    for (d, day_n), n in sorted(per_day.items(), key=lambda x: x[0][0]):
        sys.stderr.write(f"{day_n:>4}  {d:<12}  {n}\n")
    sys.stderr.write("\n")


def main() -> int:
    p = argparse.ArgumentParser(description="Content Cadence ramp-up schedule builder")
    p.add_argument("--count", type=int, help="Кол-во статей (если без --articles)")
    p.add_argument("--articles", type=Path, help="Файл со списком URL/paths статей (one per line)")
    p.add_argument("--start", required=True, help="Дата старта YYYY-MM-DD")
    p.add_argument("--target-daily-max", type=int, default=5, help="Максимум постов в день (default: 5)")
    p.add_argument("--weekdays-only", action="store_true", default=True, help="Только Пн-Пт (default: true)")
    p.add_argument("--no-weekdays-only", dest="weekdays_only", action="store_false", help="Включить выходные")
    p.add_argument("--skip-holidays", action="store_true", default=True, help="Пропускать праздники РФ (default: true)")
    p.add_argument("--no-skip-holidays", dest="skip_holidays", action="store_false")
    p.add_argument("--hour-window", default="09:00-11:00", help="Окно публикаций HH:MM-HH:MM (default: 09:00-11:00)")
    p.add_argument("--jitter", type=int, default=30, help="Рандомизация ± N минут (default: 30)")
    p.add_argument("--mode", choices=["fresh", "resume"], default="fresh",
                   help="fresh = ramp с day=1; resume = блог уже активен, старт с day=5")
    p.add_argument("--client", default="unknown", help="Slug клиента для лога")
    p.add_argument("--output", type=Path, help="Куда писать schedule.json (default: stdout)")
    p.add_argument("--seed", type=int, help="Сид рандома (для воспроизводимости тестов)")
    args = p.parse_args()

    # Источник статей
    if args.articles:
        if not args.articles.exists():
            sys.stderr.write(f"ERROR: --articles file not found: {args.articles}\n")
            return 2
        articles = [
            line.strip() for line in args.articles.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        count = len(articles)
        if count == 0:
            sys.stderr.write("ERROR: --articles file is empty\n")
            return 2
    elif args.count:
        articles = None
        count = args.count
    else:
        sys.stderr.write("ERROR: provide either --count N or --articles FILE\n")
        return 2

    try:
        start_date = datetime.strptime(args.start, "%Y-%m-%d").date()
    except ValueError as e:
        sys.stderr.write(f"ERROR: bad --start date ({e}); expected YYYY-MM-DD\n")
        return 2

    try:
        hour_window = parse_hour_window(args.hour_window)
    except (ValueError, IndexError):
        sys.stderr.write(f"ERROR: bad --hour-window '{args.hour_window}'; expected HH:MM-HH:MM\n")
        return 2

    start_offset = 0 if args.mode == "fresh" else 12  # resume → day_effective стартует с ~5/день (ceil(13/3)=5)

    schedule = build_schedule(
        article_count=count,
        start_date=start_date,
        target_daily_max=args.target_daily_max,
        weekdays_only=args.weekdays_only,
        skip_holidays=args.skip_holidays,
        hour_window=hour_window,
        jitter_minutes=args.jitter,
        articles=articles,
        start_offset=start_offset,
        client=args.client,
        seed=args.seed,
    )

    print_summary(schedule)

    out_json = json.dumps(schedule, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(out_json, encoding="utf-8")
        sys.stderr.write(f"Wrote: {args.output}\n")
    else:
        sys.stdout.write(out_json)
        sys.stdout.write("\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
