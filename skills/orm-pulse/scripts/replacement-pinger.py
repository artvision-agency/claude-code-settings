#!/usr/bin/env python3
"""replacement-pinger — daily diff attribution-report → TG-алёрт о НОВЫХ удалениях.

Сравнивает свежий attribution-report-{today}.csv с прошлым (вчерашним).
Для каждого исполнителя считает: появились ли НОВЫЕ строки со status="❌ нет в live"
которых не было вчера.

Если новые есть → формирует текст-сообщение для пинга исполнителя
и отправляет в TG team (-4273200821).

Usage:
  replacement-pinger.py <slug>
"""
from __future__ import annotations
import argparse
import csv
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path("/Users/antonk/artvision-data")
TG_SEND = Path.home() / ".claude/scripts/tg-send.sh"
ATTRIBUTION = Path.home() / ".claude/skills/orm-pulse/scripts/attribution-report.py"


def run_attribution(slug: str) -> Path | None:
    """Запустить свежий attribution-report.py → вернуть путь к свежему CSV."""
    proc = subprocess.run(
        ["python3", str(ATTRIBUTION), slug],
        capture_output=True, text=True, timeout=300,
    )
    if proc.returncode != 0:
        print(f"❌ attribution failed: {proc.stderr[:300]}", file=sys.stderr)
        return None
    today = datetime.now().strftime("%Y-%m-%d")
    csv_path = ROOT / "clients" / slug / "orm" / f"attribution-report-{today}.csv"
    return csv_path if csv_path.exists() else None


def load_attribution(csv_path: Path) -> list[dict]:
    return list(csv.DictReader(open(csv_path)))


def find_prev(slug: str, exclude: Path) -> Path | None:
    """Найти прошлый attribution-report (любой из директории)."""
    out_dir = ROOT / "clients" / slug / "orm"
    candidates = sorted(out_dir.glob("attribution-report-*.csv"), key=lambda p: p.stat().st_mtime)
    for c in reversed(candidates):
        if c.resolve() != exclude.resolve():
            return c
    return None


def row_key(r: dict) -> str:
    """Стабильный ключ строки — по тексту (text[:80] нормализованный)."""
    text = (r.get("text") or "")[:80].lower().strip()
    return text


def compose_msg_internal(slug: str, contractor: str, items: list[dict]) -> str:
    """Сообщение в TG team — для Иришки/Андрея К. (внутренние). Полные детали."""
    name_map = {"blumart": "BluMart", "bluemart": "BluMart"}
    client_name = name_map.get(slug, slug)
    now = datetime.now().strftime("%d.%m %H:%M МСК")
    lines = [
        f"🔁 {client_name} — НОВЫЕ удаления антифродом яндекса {now}",
        "",
        f"Исполнитель: {contractor}",
        f"Снеслось за период: {len(items)} отзывов",
        "",
        "Список (нужна замена тех же текстов):",
    ]
    for i, r in enumerate(items[:25], 1):
        author = r.get("author_in_sheet") or "—"
        cat = r.get("category") or "—"
        date = r.get("date_review") or "(без даты)"
        preview = (r.get("text") or "")[:80].replace("\n", " ")
        lines.append(f"{i}. {cat} · {author} · {date}")
        lines.append(f"   «{preview}…»")
    if len(items) > 25:
        lines.append(f"… и ещё {len(items)-25}")
    lines.append("")
    lines.append("📋 Полный список — карточка «Attribution / Дозамена»:")
    lines.append(f"https://artvision.pro/orm-command-center/{slug}.html")
    return "\n".join(lines)


def compose_msg_external(contractor: str, items: list[dict]) -> str:
    """Текст для отправки ВНЕШНЕМУ исполнителю (биржа okponrussia / kwork / etc.).

    БЕЗ упоминания: имени клиента, площадки (reviews.yandex.ru),
    авторов (имена приватные). Только: категории + количество + срок.
    Антон/Андрей копируют и отправляют вручную.
    """
    from collections import Counter
    cats = Counter(r.get("category") or "—" for r in items)
    cat_lines = "\n".join(f"  • {cat}: {n}" for cat, n in cats.most_common())
    lines = [
        f"Привет!",
        "",
        f"По нашей партии {len(items)} отзывов слетели с площадки (модерация удалила).",
        "Просим заменить на новые тексты в тех же категориях:",
        "",
        cat_lines,
        "",
        "Требования к новым текстам:",
        "  • Объём 200-400 знаков",
        "  • Естественная речь покупателя (без шаблонных фраз и клише)",
        "  • Конкретные детали о товаре (цвет, размер, ситуация использования)",
        "  • НЕ повторять прошлые тексты (по которым уже снесли)",
        "",
        "Срок: 3 рабочих дня.",
        "Спасибо!",
    ]
    return "\n".join(lines)


def save_request_file(slug: str, contractor: str, items: list[dict],
                       internal: bool, date_str: str) -> Path:
    """Сохранить готовый текст запроса в файл — для ручной отправки."""
    out_dir = ROOT / "clients" / slug / "orm" / "replacement-requests"
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_contractor = contractor.replace(" ", "_").replace("/", "_").replace("(", "").replace(")", "")[:40]
    suffix = "internal" if internal else "external"
    fname = f"{date_str}_{safe_contractor}_{suffix}.md"
    fpath = out_dir / fname
    if internal:
        body = compose_msg_internal(slug, contractor, items)
    else:
        body = compose_msg_external(contractor, items)
    header = (f"# Replacement request — {contractor} — {date_str}\n\n"
              f"> {'INTERNAL (Иришка/Андрей К.)' if internal else 'EXTERNAL (отправить копирайтерам/бирже вручную)'}\n"
              f"> {len(items)} удалённых текстов · сгенерировано replacement-pinger.py\n\n"
              f"---\n\n")
    fpath.write_text(header + body)
    return fpath


def _safe_for_markdown(s: str) -> str:
    """Убрать символы которые ломают Telegram Markdown parse."""
    return (s.replace("(", "")
             .replace(")", "")
             .replace("/", " ")
             .replace("_", " "))


def compose_summary_for_team(slug: str, all_groups: dict[str, dict]) -> str:
    """Краткая сводка для TG team — что сгенерировано, ссылки на файлы."""
    name_map = {"blumart": "BluMart", "bluemart": "BluMart"}
    client_name = name_map.get(slug, slug)
    now = datetime.now().strftime("%d.%m %H:%M МСК")
    lines = [
        f"BluMart ORM — replacement requests готовы {now}",
        "",
    ]
    total = 0
    for contractor, info in sorted(all_groups.items(), key=lambda x: -x[1]["count"]):
        total += info["count"]
        safe_c = _safe_for_markdown(contractor)
        lines.append(f"  · {safe_c}: {info['count']} строк")
    lines.append("")
    lines.append(f"Всего новых удалений за период: {total}")
    lines.append("")
    lines.append(f"Файлы готовых сообщений: clients {slug} orm replacement-requests")
    lines.append("")
    lines.append(f"Дашборд: https://artvision.pro/orm-command-center/{slug}.html")
    return "\n".join(lines)


def send_tg(message: str) -> bool:
    if not TG_SEND.exists():
        return False
    proc = subprocess.run([str(TG_SEND), "team", message], capture_output=True, text=True, timeout=30)
    out = proc.stdout + proc.stderr
    return "Sent" in out or '"ok":true' in out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-attribution", action="store_true",
                    help="не запускать attribution-report, использовать существующий")
    args = ap.parse_args()

    if args.no_attribution:
        out_dir = ROOT / "clients" / args.slug / "orm"
        candidates = sorted(out_dir.glob("attribution-report-*.csv"), key=lambda p: p.stat().st_mtime)
        if not candidates:
            print("❌ нет existing attribution-report.csv", file=sys.stderr)
            return 1
        current_path = candidates[-1]
    else:
        current_path = run_attribution(args.slug)
        if not current_path:
            return 1

    print(f"📋 Current: {current_path.name}")
    current = load_attribution(current_path)

    prev_path = find_prev(args.slug, current_path)
    if not prev_path:
        print("ℹ️ нет prev attribution → первый запуск, всё в текущем считается «новым»")
        prev_keys: set = set()
    else:
        print(f"📦 Prev: {prev_path.name}")
        prev = load_attribution(prev_path)
        prev_keys = {row_key(r) for r in prev
                     if r.get("status_in_sheet") in ("Отзыв размещён", "Отзыв размещен")
                     and r.get("live_status", "").startswith("❌")}

    # Текущие removed
    current_removed = [r for r in current
                       if r.get("status_in_sheet") in ("Отзыв размещён", "Отзыв размещен")
                       and r.get("live_status", "").startswith("❌")]

    # Новые = те которых не было вчера
    new_removed = [r for r in current_removed if row_key(r) not in prev_keys]

    print(f"\n📊 Removed currently: {len(current_removed)} (новых vs prev: {len(new_removed)})")

    if not new_removed:
        print("✅ нет новых удалений — TG-алёрт не нужен")
        return 0

    # Группировка по исполнителю
    by_contractor: dict[str, list[dict]] = defaultdict(list)
    for r in new_removed:
        by_contractor[r["contractor"]].append(r)

    print(f"\n🔁 Новые удаления по исполнителям:")
    for c, items in sorted(by_contractor.items(), key=lambda x: -len(x[1])):
        print(f"  {c}: {len(items)}")

    # Сохранить файлы запросов + собрать сводку
    date_str = datetime.now().strftime("%Y-%m-%d")
    all_groups: dict[str, dict] = {}
    for contractor, items in by_contractor.items():
        is_internal = contractor.startswith("internal")
        fpath = save_request_file(args.slug, contractor, items, internal=is_internal, date_str=date_str)
        rel_path = f"replacement-requests/{fpath.name}"
        all_groups[contractor] = {"count": len(items), "file_name": rel_path, "internal": is_internal}
        print(f"💾 {contractor}: {fpath}")

    # Summary в TG team
    summary = compose_summary_for_team(args.slug, all_groups)
    if args.dry_run:
        print("\n[dry-run] Would send summary to TG team:")
        print(summary)
    else:
        if send_tg(summary):
            print("\n✅ TG summary sent to team")
        else:
            print("\n❌ TG summary failed", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
