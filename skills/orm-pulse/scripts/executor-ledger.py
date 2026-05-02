#!/usr/bin/env python3
"""executor-ledger — append-only журнал передач текстов исполнителям.

Что это: CSV-лог «кто/что/когда/куда отдал» — закрывает пробел между
Sheet (внутренний учёт) и реальностью (kwork-личка, qcomment, TG-биржа).

Формат: clients/<slug>/orm/executor-ledger.csv
Поля:
  timestamp, text_id, text_preview, executor, channel, batch_id,
  status, source, notes

Usage:
  # ручная запись (типичный кейс — после kwork-личной передачи)
  executor-ledger.py <client> add \\
      --executor social_boost --channel kwork \\
      --text-id "apr26-r79" --text "Заказ через kwork ЛК 02.05" \\
      --status sent --notes "4 текста, тариф ?"

  # автоматический backfill из qcomment snapshot (создаёт record за каждый comment)
  executor-ledger.py <client> backfill --source qcomment

  # запрос истории
  executor-ledger.py <client> query --executor okponrussia
  executor-ledger.py <client> query --channel kwork
  executor-ledger.py <client> stats
"""
from __future__ import annotations
import argparse
import csv
import json
import sys
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict

ROOT = Path("/Users/antonk/artvision-data")

LEDGER_FIELDS = [
    "timestamp", "text_id", "text_preview", "executor", "channel",
    "batch_id", "status", "source", "notes",
]

VALID_STATUSES = {"sent", "accepted", "rejected", "rework", "published", "withdrawn", "spent"}
VALID_CHANNELS = {"tg", "kwork", "qcomment", "kupi-otziv", "sheet", "advego", "manual", "other"}
VALID_SOURCES = {"manual", "sheet-diff", "tg-extract", "qcomment-api", "kupi-otziv-api", "kwork-snapshot", "backfill"}


def ledger_path(slug: str) -> Path:
    p = ROOT / "clients" / slug / "orm" / "executor-ledger.csv"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def ensure_header(path: Path) -> None:
    if path.exists() and path.stat().st_size > 0:
        return
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LEDGER_FIELDS)
        writer.writeheader()


def append_row(path: Path, row: dict) -> None:
    ensure_header(path)
    with open(path, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LEDGER_FIELDS)
        writer.writerow({k: row.get(k, "") for k in LEDGER_FIELDS})


def load_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def cmd_add(args) -> int:
    if args.status not in VALID_STATUSES:
        sys.exit(f"ERROR: status must be one of {sorted(VALID_STATUSES)}")
    if args.channel not in VALID_CHANNELS:
        sys.exit(f"ERROR: channel must be one of {sorted(VALID_CHANNELS)}")

    path = ledger_path(args.client)
    text_preview = (args.text or "")[:80]
    row = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "text_id": args.text_id or "",
        "text_preview": text_preview,
        "executor": args.executor,
        "channel": args.channel,
        "batch_id": args.batch_id or "",
        "status": args.status,
        "source": args.source or "manual",
        "notes": args.notes or "",
    }
    append_row(path, row)
    print(f"✓ Added: {row['executor']} via {row['channel']} · status={row['status']} · {text_preview[:40]}")
    return 0


def cmd_backfill_qcomment(args) -> int:
    """Backfill из qcomment snapshot: за каждый комментарий — record."""
    qc_dir = ROOT / "clients" / args.client / "orm" / "qcomment"
    snaps = sorted(qc_dir.glob("snap-*.json")) if qc_dir.exists() else []
    if not snaps:
        sys.exit("ERROR: no qcomment snapshots found")
    snap = json.loads(snaps[-1].read_text())

    path = ledger_path(args.client)
    existing = {(r["text_id"], r["executor"], r["channel"]) for r in load_rows(path)}

    added = 0
    for gname, projs in snap.get("groups", {}).items():
        for p in projs:
            text_id = f"qcomment:{p['project_id']}"
            key = (text_id, "qcomment", "qcomment")
            if key in existing:
                continue
            # Determine status from counters
            if p.get("accepted", 0) > 0 and p.get("accepted", 0) >= p.get("pay", 1):
                status = "accepted"
            elif p.get("pending", 0) > 0:
                status = "sent"  # waiting for our acceptance
            elif p.get("rework", 0) > 0:
                status = "rework"
            elif p.get("rejected", 0) > 0:
                status = "rejected"
            else:
                status = "sent"  # waiting for executor pickup
            row = {
                "timestamp": snap.get("ts", datetime.now().isoformat()),
                "text_id": text_id,
                "text_preview": (p.get("title", ""))[:80],
                "executor": "qcomment",
                "channel": "qcomment",
                "batch_id": gname,
                "status": status,
                "source": "qcomment-api",
                "notes": f"project_id={p['project_id']} pay={p.get('pay')} pending={p.get('pending')} accepted={p.get('accepted')}",
            }
            append_row(path, row)
            added += 1
    print(f"✓ Backfilled {added} qcomment records (total snapshots: {len(snaps)})")
    return 0


def cmd_query(args) -> int:
    rows = load_rows(ledger_path(args.client))
    filtered = rows
    if args.executor:
        filtered = [r for r in filtered if r["executor"] == args.executor]
    if args.channel:
        filtered = [r for r in filtered if r["channel"] == args.channel]
    if args.status:
        filtered = [r for r in filtered if r["status"] == args.status]
    if args.since:
        filtered = [r for r in filtered if r["timestamp"] >= args.since]

    if not filtered:
        print("(no records)")
        return 0
    print(f"# Found {len(filtered)} records (of {len(rows)} total)\n")
    for r in filtered[-50:]:
        ts = r["timestamp"][:16]
        print(f"{ts} · {r['executor']:18} · {r['channel']:10} · {r['status']:10} · {r['text_id'][:30]:30} · {r['text_preview'][:50]}")
    return 0


def cmd_stats(args) -> int:
    rows = load_rows(ledger_path(args.client))
    if not rows:
        print("(no records)")
        return 0

    by_executor = Counter(r["executor"] for r in rows)
    by_channel = Counter(r["channel"] for r in rows)
    by_status = Counter(r["status"] for r in rows)
    by_executor_status: dict = defaultdict(Counter)
    for r in rows:
        by_executor_status[r["executor"]][r["status"]] += 1

    print(f"# Executor Ledger Stats — {args.client}")
    print(f"Total records: {len(rows)}")
    print(f"Date range: {rows[0]['timestamp'][:10]} → {rows[-1]['timestamp'][:10]}\n")

    print("## By executor")
    for ex, n in by_executor.most_common():
        statuses = " · ".join(f"{s}={c}" for s, c in by_executor_status[ex].most_common())
        print(f"  {ex:25} {n:5}  ({statuses})")

    print("\n## By channel")
    for ch, n in by_channel.most_common():
        print(f"  {ch:15} {n}")

    print("\n## By status")
    for st, n in by_status.most_common():
        print(f"  {st:15} {n}")
    return 0


def main():
    parser = argparse.ArgumentParser(description="executor-ledger — append-only журнал передач")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_add = sub.add_parser("add", help="добавить запись")
    p_add.add_argument("client")
    p_add.add_argument("--executor", required=True)
    p_add.add_argument("--channel", required=True, choices=sorted(VALID_CHANNELS))
    p_add.add_argument("--status", required=True, choices=sorted(VALID_STATUSES))
    p_add.add_argument("--text-id", default="")
    p_add.add_argument("--text", default="")
    p_add.add_argument("--batch-id", default="")
    p_add.add_argument("--source", default="manual", choices=sorted(VALID_SOURCES))
    p_add.add_argument("--notes", default="")
    p_add.set_defaults(func=cmd_add)

    p_bf = sub.add_parser("backfill", help="ретроспектива из источников")
    p_bf.add_argument("client")
    p_bf.add_argument("--source", required=True, choices=["qcomment"])
    p_bf.set_defaults(func=lambda a: cmd_backfill_qcomment(a) if a.source == "qcomment" else 1)

    p_q = sub.add_parser("query", help="запросить историю")
    p_q.add_argument("client")
    p_q.add_argument("--executor")
    p_q.add_argument("--channel")
    p_q.add_argument("--status")
    p_q.add_argument("--since", help="ISO date YYYY-MM-DD")
    p_q.set_defaults(func=cmd_query)

    p_s = sub.add_parser("stats", help="статистика")
    p_s.add_argument("client")
    p_s.set_defaults(func=cmd_stats)

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
