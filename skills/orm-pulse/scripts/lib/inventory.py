"""orm-pulse inventory — парсинг docs/sheets для card-генератора.

Вынесено из cards.py (code review H1, 10.05.2026):
эти функции — pure data-loading, не render. Reused by render_docs_card,
а в будущем — daily-summary, alert-router и др.
"""
from __future__ import annotations
import csv
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

from .config import ROOT


# Маппинг статусов из Sheet — для подмешивания emoji в дашборд
STATUS_EMOJI = {
    "Отзыв размещён": "✅",
    "Согласовано, заказ размещён": "📤",
    "Ожидание модерации": "⏳",
    "Текст согласован": "📝",
    "Ожидает согласования": "⏸",
    "Неуникальный текст отзыва (повторящиеся шинглы)": "🚫",
    "Ждет размещения": "📦",
    "Не прошёл модерацию": "❌",
    "потрачен": "💸",
}


def sheet_tab_stats(client: str) -> dict:
    """Парсит snapshot CSV → {snapshot_filename: {total, by_status: [(emoji+status, count)]}}."""
    base = ROOT / "clients" / client / "orm" / "snapshots" / "latest"
    if not base.exists():
        return {}
    out: dict = {}
    for f in base.glob("sheet*.csv"):
        try:
            with open(f) as fh:
                rows = list(csv.reader(fh))
        except (OSError, csv.Error):
            continue
        statuses: Counter = Counter()
        for r in rows[1:]:
            if len(r) >= 3 and r[2].strip():
                statuses[r[2].strip()] += 1
        if not statuses:
            continue
        out[f.stem] = {
            "total": sum(statuses.values()),
            "by_status": [
                (f"{STATUS_EMOJI.get(s, '•')} {s[:24]}", n)
                for s, n in statuses.most_common(4)
            ],
        }
    return out


_BATCH_COMPOSE_RE = re.compile(r"\*\*Состав:\*\*\s*(.+?)$", re.MULTILINE)


def parse_batch_compose(p: Path) -> str:
    """Извлекает строку '5 шт. (Плитка ×3 + Аксессуары ×2)' из batch md."""
    try:
        text = p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""
    m = _BATCH_COMPOSE_RE.search(text)
    return m.group(1).strip() if m else ""


def docs_inventory(client: str, registry: dict) -> dict:
    """Собирает инвентарь всех ORM-документов клиента с фактическими цифрами."""
    base = ROOT / "clients" / client / "orm"
    repo_url = "https://github.com/artvision-agency/artvision-data/blob/feat/ops-crm-v1"
    sheet_stats = sheet_tab_stats(client)

    def file_meta(rel_path: str) -> dict | None:
        p = base / rel_path
        if not p.exists():
            return None
        st = p.stat()
        meta: dict = {
            "name": rel_path,
            "size_kb": st.st_size // 1024 or 1,
            "mtime": datetime.fromtimestamp(st.st_mtime).strftime("%d.%m %H:%M"),
            "github": f"{repo_url}/clients/{client}/orm/{rel_path}",
        }
        if rel_path.endswith(".csv"):
            try:
                with open(p) as f:
                    meta["rows"] = sum(1 for _ in f) - 1
            except OSError:
                pass
        if rel_path.startswith("batches/batch-"):
            meta["data"] = parse_batch_compose(p)
        return meta

    def latest_match(pattern: str) -> str | None:
        files = sorted(base.glob(pattern), reverse=True)
        return files[0].name if files else None

    sheet_snapshot_map = {
        ("sheet1_internal", 0): "sheet1_internal_0",
        ("sheet1_internal", 88304516): "sheet1_internal_88304516",
        ("sheet1_internal", 470319558): "sheet1_internal_470319558",
        ("sheet2_okponrussia", 0): "sheet2_okponrussia_0",
        ("sheet2_okponrussia", 666154064): "sheet2_okponrussia_666154064",
    }
    sheets = []
    for key, sh in (registry.get("sheets") or {}).items():
        sid = sh.get("id")
        if not sid:
            continue
        for tab in sh.get("tabs", []):
            snap_key = sheet_snapshot_map.get((key, tab.get("gid", 0)))
            stats = sheet_stats.get(snap_key) if snap_key else None
            sheets.append({
                "label": f"{sh.get('role', key)} — {tab.get('name', '?')}",
                "owner": sh.get("owner", "?"),
                "plan": tab.get("plan"),
                "period": tab.get("period"),
                "url": f"https://docs.google.com/spreadsheets/d/{sid}/edit#gid={tab.get('gid', 0)}",
                "stats": stats,
            })

    key_docs = []
    for rel in ["registry.yaml", "plan-may-2026.md", "batch-plan-2026-05-04.md",
                "contractors-master-table.md", "authoring-matrix-v1.md",
                "executor-ledger.csv", "order-template-for-executors.md"]:
        m = file_meta(rel)
        if m:
            key_docs.append(m)

    dated_docs = []
    for prefix in ["orders-state-", "STATUS-INTERNAL-", "STATUS-ALL-", "pending-"]:
        latest = latest_match(f"{prefix}*.md")
        if latest:
            m = file_meta(latest)
            if m:
                dated_docs.append(m)

    batches = []
    bdir = base / "batches"
    if bdir.exists():
        for f in sorted(bdir.glob("*.md")):
            m = file_meta(f"batches/{f.name}")
            if m:
                batches.append(m)

    return {
        "sheets": sheets,
        "key_docs": key_docs,
        "dated_docs": dated_docs,
        "batches": batches,
    }
