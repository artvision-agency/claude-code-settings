#!/usr/bin/env python3
"""
orm-pulse: Reconciliation 3 источников (TG / Sheet / Live) + bucket-аудит.

Usage: reconcile.py <client_slug>

Output:
  - /tmp/orm-pulse/<slug>/reconcile/report.json
  - /tmp/orm-pulse/<slug>/reconcile/buckets.json   (draft/contractors/checking/public/rejected)
  - /tmp/orm-pulse/<slug>/reconcile/discrepancies.json
"""
import sys
import csv
import json
import argparse
import re
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter

import yaml


def load_registry(slug: str) -> dict:
    return yaml.safe_load((Path.home() / "artvision-data" / "clients" / slug / "orm" / "registry.yaml").read_text())


def parse_dmy(s: str):
    """Parse DD.MM.YYYY."""
    s = (s or "").strip()
    if not s:
        return None
    try:
        return datetime.strptime(s, "%d.%m.%Y")
    except ValueError:
        return None


def classify_buckets(slug: str) -> dict:
    """Classify Sheet rows into draft/contractors/checking/public/rejected/spent."""
    snapshots = Path.home() / "artvision-data" / "clients" / slug / "orm" / "snapshots" / "latest"
    today = datetime.now()

    buckets = {
        "draft": [],         # согласовано, не отдано (без даты заказа)
        "contractors": [],   # отдано в работу (с датой заказа, без даты публикации, ≤14 дней)
        "checking": [],      # на модерации Я (статус «На модерации» или 14+ дней без публикации)
        "public": [],        # «Отзыв размещён» с датой публикации
        "rejected": [],      # «Не прошёл модерацию»
        "spent": [],         # «потрачен»
        "rework": [],        # вкладка «переделать»
    }

    for csv_file in snapshots.glob("*.csv"):
        if csv_file.name.startswith("_"):
            continue
        sheet_key = csv_file.stem
        is_rework_sheet = "переделать" in sheet_key.lower() or "rework" in sheet_key.lower()

        with open(csv_file, encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for i, r in enumerate(reader, start=2):
                text = (r.get("Текст отзыва") or r.get("Текст") or "").strip()
                if not text:
                    continue
                row = {
                    "sheet": sheet_key,
                    "row": i,
                    "text": text,
                    "author": (r.get("Автор отзыва") or "").strip(),
                    "status": (r.get("Статус") or r.get("Статус размещения") or "").strip(),
                    "category": (r.get("Категория товара") or "").strip(),
                    "date_заказа": (r.get("Дата заказа") or "").strip(),
                    "date_отзыва": (r.get("Дата отзыва") or "").strip(),
                }
                status = row["status"].lower()

                if is_rework_sheet:
                    buckets["rework"].append(row)
                    continue

                if "размещ" in status and "не прош" not in status:
                    buckets["public"].append(row)
                elif "не прош" in status:
                    buckets["rejected"].append(row)
                elif "потрачен" in status:
                    buckets["spent"].append(row)
                elif "модерац" in status:
                    buckets["checking"].append(row)
                elif "ждет размещения" in status or "ждёт размещения" in status:
                    # Sheet2/okponrussia format — это всё «отдано в работу»
                    buckets["contractors"].append(row)
                elif "согласов" in status:
                    if not row["date_заказа"]:
                        buckets["draft"].append(row)
                    else:
                        # Дата заказа есть → contractors. Если >14 дней без публикации → checking
                        d_order = parse_dmy(row["date_заказа"])
                        if d_order and (today - d_order).days > 14:
                            buckets["checking"].append(row)
                        else:
                            buckets["contractors"].append(row)
                else:
                    # Unknown status — skip or log
                    pass

    return buckets


def parse_tg_signals(slug: str, registry: dict) -> dict:
    """Parse TG-чаты: пинги бирж, обещанные публикации."""
    tg_dir = Path("/tmp/orm-pulse") / slug / "tg"
    signals = {
        "bourse_pings": [],     # «дайте больше», «ждём новые»
        "bourse_publications": [],  # «+1», «+2», «залетело»
    }

    if not tg_dir.exists():
        return signals

    contractors = registry.get("contractors", [])
    contractor_chats = {c.get("tg_chat_id"): c for c in contractors if c.get("tg_chat_id")}

    for md_file in tg_dir.glob("*.md"):
        # chat_id из имени файла
        chat_id_match = re.match(r"(\d+)_", md_file.name)
        if not chat_id_match:
            continue
        chat_id = int(chat_id_match.group(1))
        contractor = contractor_chats.get(chat_id)

        content = md_file.read_text()
        for line in content.splitlines():
            if not line.startswith("| 2026"):
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 5:
                continue
            date, sender, reply_to, msg = parts[1], parts[2], parts[3], parts[4]
            msg_lower = msg.lower()

            # Биржа подтвердила публикацию
            if contractor and contractor.get("publication_signals"):
                for sig in contractor["publication_signals"]:
                    if sig.lower() in msg_lower:
                        signals["bourse_publications"].append({
                            "date": date, "chat_id": chat_id,
                            "contractor": contractor["name"],
                            "sender": sender, "msg": msg[:200],
                        })
                        break

            # Биржа просит ещё текстов
            if contractor and contractor.get("request_signals"):
                for sig in contractor["request_signals"]:
                    if sig.lower() in msg_lower:
                        signals["bourse_pings"].append({
                            "date": date, "chat_id": chat_id,
                            "contractor": contractor["name"],
                            "sender": sender, "msg": msg[:200],
                        })
                        break

    return signals


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("slug")
    args = parser.parse_args()

    registry = load_registry(args.slug)
    buckets = classify_buckets(args.slug)
    signals = parse_tg_signals(args.slug, registry)

    # Match data
    match_dir = Path("/tmp/orm-pulse") / args.slug / "match"
    matched = json.loads((match_dir / "matched.json").read_text()) if (match_dir / "matched.json").exists() else []
    missing = json.loads((match_dir / "missing.json").read_text()) if (match_dir / "missing.json").exists() else []
    organic = json.loads((match_dir / "organic.json").read_text()) if (match_dir / "organic.json").exists() else []

    # Summary cifry
    summary = {
        "buckets": {k: len(v) for k, v in buckets.items()},
        "live_confirmed_ours": len(matched),
        "missing_in_live": len(missing),
        "organic_on_platform": len(organic),
        "tg_publications_reported": len(signals["bourse_publications"]),
        "tg_pings_for_more": len(signals["bourse_pings"]),
    }

    # Recon discrepancies
    sheet_public = summary["buckets"]["public"]
    live_ours = summary["live_confirmed_ours"]
    bourse_reported = summary["tg_publications_reported"]

    discrepancies = []
    if abs(sheet_public - live_ours) > 0:
        discrepancies.append({
            "type": "sheet_vs_live",
            "sheet_public": sheet_public,
            "live_ours": live_ours,
            "delta": sheet_public - live_ours,
            "explanation": "Sheet говорит размещён → не найдено live (за пределами топ-1000 / удалены / ошибочный статус)" if sheet_public > live_ours else "Live больше Sheet — возможно tracking не успевает",
        })
    if abs(bourse_reported - live_ours) > 2:
        discrepancies.append({
            "type": "bourse_vs_live",
            "bourse_reported": bourse_reported,
            "live_ours": live_ours,
            "explanation": "Биржа отчиталась о публикациях → live не подтверждает / наоборот",
        })

    out_dir = Path("/tmp/orm-pulse") / args.slug / "reconcile"
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "buckets.json").write_text(json.dumps(buckets, ensure_ascii=False, indent=2))
    (out_dir / "signals.json").write_text(json.dumps(signals, ensure_ascii=False, indent=2))
    (out_dir / "discrepancies.json").write_text(json.dumps(discrepancies, ensure_ascii=False, indent=2))
    (out_dir / "report.json").write_text(json.dumps({
        "summary": summary,
        "discrepancies": discrepancies,
        "signals_count": {k: len(v) for k, v in signals.items()},
    }, ensure_ascii=False, indent=2))

    print(f"\n=== Reconcile {args.slug} ===")
    print(f"Buckets: {summary['buckets']}")
    print(f"Live confirmed (наши): {live_ours}")
    print(f"Missing in live: {summary['missing_in_live']}")
    print(f"Organic on platform: {summary['organic_on_platform']}")
    print(f"TG publications reported: {bourse_reported}")
    print(f"TG pings for more: {summary['tg_pings_for_more']}")
    print(f"\nDiscrepancies: {len(discrepancies)}")
    for d in discrepancies:
        print(f"  - {d['type']}: {d}")


if __name__ == "__main__":
    main()
