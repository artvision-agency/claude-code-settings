"""orm-pulse loaders — read data from snapshots/CSV/JSON/YAML.

Вынесено из command-center.py при refactoring 2026-05-10.
Pure data-loading функции, без HTML-генерации.
"""
from __future__ import annotations
import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

import yaml

from .config import ROOT, TMP_ORM  # noqa: F401


def load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return yaml.safe_load(path.read_text()) or {}
    except Exception:
        return {}


def load_json(path: Path) -> dict | list | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def latest_qcomment(client: str) -> dict | None:
    d = ROOT / "clients" / client / "orm" / "qcomment"
    if not d.exists():
        return None
    snaps = sorted(d.glob("snap-*.json"))
    if not snaps:
        return None
    res = load_json(snaps[-1])
    return res if isinstance(res, dict) else None


def reviews_pace(client: str, days: int = 7) -> dict | None:
    history = ROOT / "clients" / client / "orm" / "reviews-tracker" / "history.csv"
    if not history.exists():
        return None
    try:
        rows = list(csv.DictReader(open(history)))
    except Exception:
        return None
    if len(rows) < 2:
        return None
    first = rows[0]
    last = rows[-1]
    try:
        delta_total = int(last.get("total", 0)) - int(first.get("total", 0))
    except (ValueError, TypeError):
        delta_total = 0
    return {
        "first_ts": first.get("timestamp"),
        "last_ts": last.get("timestamp"),
        "total_now": last.get("total"),
        "rating_now": last.get("rating"),
        "delta_total": delta_total,
        "snapshots": len(rows),
    }


def latest_orders_state(client: str) -> dict | None:
    p = TMP_ORM / client / "orders-state.json"
    res = load_json(p)
    return res if isinstance(res, dict) else None


def ledger_stats(client: str) -> dict:
    p = ROOT / "clients" / client / "orm" / "executor-ledger.csv"
    if not p.exists():
        return {"total": 0}
    try:
        rows = list(csv.DictReader(open(p)))
    except Exception:
        return {"total": 0}
    by_executor: Counter = Counter(r["executor"] for r in rows)
    by_channel: Counter = Counter(r["channel"] for r in rows)
    by_status: Counter = Counter(r["status"] for r in rows)
    return {
        "total": len(rows),
        "by_executor": dict(by_executor.most_common()),
        "by_channel": dict(by_channel.most_common()),
        "by_status": dict(by_status.most_common()),
        "first_ts": rows[0]["timestamp"][:16] if rows else None,
        "last_ts": rows[-1]["timestamp"][:16] if rows else None,
    }


def last_contact_per_executor(client: str) -> dict[str, dict]:
    """Возвращает {executor: {last_ts, last_text, last_channel}} — последний контакт."""
    p = ROOT / "clients" / client / "orm" / "executor-ledger.csv"
    if not p.exists():
        return {}
    try:
        rows = list(csv.DictReader(open(p)))
    except Exception:
        return {}
    last: dict[str, dict] = {}
    for r in rows:
        ex = r.get("executor", "")
        if not ex:
            continue
        ts = r.get("timestamp", "")
        if ex not in last or ts > last[ex]["last_ts"]:
            last[ex] = {
                "last_ts": ts,
                "last_text": (r.get("text", "") or "")[:80],
                "last_channel": r.get("channel", ""),
                "last_status": r.get("status", ""),
            }
    return last


def list_research(client: str) -> list[dict]:
    d = ROOT / "clients" / client / "orm" / "research"
    if not d.exists():
        return []
    out = []
    for f in sorted(d.glob("*.md")):
        out.append({
            "name": f.name,
            "size_kb": f.stat().st_size // 1024,
            "live_url": f"https://artvision.pro/orm-research/{client}-{f.name.replace('.md', '.html')}",
        })
    return out


def kupi_otziv_latest(client: str) -> dict | None:
    d = ROOT / "clients" / client / "orm" / "kupi-otziv"
    if not d.exists():
        return None
    snaps = sorted(d.glob("snap-*.json"))
    if not snaps:
        return None
    res = load_json(snaps[-1])
    return res if isinstance(res, dict) else None


def kwork_summary(client: str) -> dict | None:
    """Если background-агент сохранил kwork отчёт — подхватываем."""
    p = ROOT / "clients" / client / "orm" / "kwork" / f"SUMMARY-{datetime.now().strftime('%Y-%m-%d')}.md"
    if p.exists():
        return {"path": str(p), "snippet": p.read_text(encoding="utf-8")[:500]}
    return None
