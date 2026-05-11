#!/usr/bin/env python3
"""qcomment-monitor — снапшот биржи qcomment.com через прямой API.

Что делает:
1. POST /api/projects + /api/balance + /api/comments на каждый проект
2. Сохраняет snapshot в clients/<slug>/orm/qcomment/snap-<date>.json
3. Diff с предыдущим — алёрт если pending_review растёт или баланс падает
4. История CSV: date, balance, total, pending, accepted, rejected, rework

Usage: qcomment-monitor.py <client_slug>
Запуск через cron/LaunchAgent N раз в день.
"""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from collections import defaultdict

ROOT = Path("/Users/antonk/artvision-data")
TOKENS_PATH = ROOT / "tokens.json"
TG_SEND = Path.home() / ".claude/scripts/tg-send.sh"

# Q12 budget-cap (decisions/2026-05-10-orm-budget-cap.md)
sys.path.insert(0, str(Path(__file__).parent))
try:
    from lib.budget_guard import check_qcomment_balance, should_send_alert, mark_alert_sent  # noqa: E402
except ImportError:
    check_qcomment_balance = None  # type: ignore
    should_send_alert = None  # type: ignore
    mark_alert_sent = None  # type: ignore


def _send_budget_alert(client: str) -> None:
    """Q12: TG-алёрт при низком балансе qcomment (rate-limited)."""
    if check_qcomment_balance is None:
        return
    try:
        bal = check_qcomment_balance(client)
    except Exception as e:
        print(f"⚠️ budget check failed: {e}", file=sys.stderr)
        return
    if bal.get("level") == "norm" or bal.get("balance_rub") is None:
        return
    level = bal["level"]
    if not should_send_alert(level, rate_limit_hours=6):
        print(f"⏸ Budget alert rate-limited ({level})", file=sys.stderr)
        return

    if level == "critical":
        msg = (
            f"🚨 {client}: qcomment баланс CRITICAL — "
            f"{bal['balance_rub']:.0f} ₽ < {bal['threshold_critical']} ₽\n"
            f"Новые placement-заказы автоматически блокируются (Q12 budget-cap).\n"
            f"Пополни: https://qcomment.com/finance/"
        )
    else:  # warn
        msg = (
            f"⚠️ {client}: qcomment баланс низкий — "
            f"{bal['balance_rub']:.0f} ₽ < {bal['threshold_warn']} ₽\n"
            f"Рекомендую пополнить: https://qcomment.com/finance/"
        )

    if TG_SEND.exists():
        try:
            subprocess.run([str(TG_SEND), "team", msg], timeout=15)
            mark_alert_sent(level)
            print(f"🚨 Q12 budget alert sent ({level})", file=sys.stderr)
        except Exception as e:
            print(f"❌ TG send failed: {e}", file=sys.stderr)


def load_qcomment_config() -> dict:
    with open(TOKENS_PATH, encoding="utf-8") as f:
        tokens = json.load(f)
    cfg = tokens.get("qcomment")
    if not cfg or not cfg.get("api_code"):
        sys.exit("ERROR: tokens.json missing qcomment.api_code")
    return cfg


def post_qcomment(api_base: str, api_code: str, endpoint: str, **params) -> dict | list:
    params["apicode"] = api_code
    params["result"] = "json"
    data = urlencode(params).encode()
    req = Request(f"{api_base}/{endpoint}", data=data, method="POST")
    with urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_comments(api_base: str, api_code: str, project_id: str) -> list:
    try:
        r = post_qcomment(api_base, api_code, "comments", project_id=project_id)
    except Exception as e:
        return [{"_error": str(e)}]
    if isinstance(r, dict) and r.get("error_code"):
        return []
    if isinstance(r, dict):
        return list(r.values())
    return []


def classify_status(p: dict, pending: int, accepted: int, rejected: int, rework: int) -> tuple[str, str, int]:
    s = p.get("status_short", "0")
    pay = int(p.get("pay", 0))
    if s == "4":
        return "На модерации QComment", "moder", 50
    if s == "2":
        return "Пауза (юзер)", "pause", 70
    if s == "3":
        return "Пауза (админ)", "pause", 60
    if s == "0":
        return "Без оплаты", "neutral", 80
    if pending > 0:
        return f"Принять работу ({pending})", "review", 1
    if rework > 0:
        return f"На доработке ({rework})", "rework", 30
    if accepted >= pay > 0:
        return "Завершён", "done", 90
    if rejected > 0:
        return f"Отклонено ({rejected}) — ждём исполнителя", "wait", 35
    return "Ждёт исполнителя", "wait", 40


def build_snapshot(cfg: dict) -> dict:
    api_base = cfg["api_base"]
    api_code = cfg["api_code"]
    group_names = cfg.get("groups", {})

    projects_resp = post_qcomment(api_base, api_code, "projects")
    balance_resp = post_qcomment(api_base, api_code, "balance")
    projects = list(projects_resp.values()) if isinstance(projects_resp, dict) else []
    balance_value = balance_resp.get("balance", "?") if isinstance(balance_resp, dict) else "?"

    grouped = defaultdict(list)
    pending_total = accepted_total = rejected_total = rework_total = 0

    for p in projects:
        gid = str(p.get("group_id", "0"))
        gname = group_names.get(gid, f"Группа {gid}")
        comments = fetch_comments(api_base, api_code, p["id"])
        pending = sum(1 for c in comments if str(c.get("status")) == "0")
        accepted = sum(1 for c in comments if str(c.get("status")) == "1")
        rejected = sum(1 for c in comments if str(c.get("status")) == "2")
        rework = sum(1 for c in comments if str(c.get("status")) == "3")

        st_text, st_class, st_prio = classify_status(p, pending, accepted, rejected, rework)
        rec = {
            "project_id": p["id"],
            "title": p.get("title", ""),
            "url": p.get("url", ""),
            "pay": int(p.get("pay", 0)),
            "pending": pending,
            "accepted": accepted,
            "rejected": rejected,
            "rework": rework,
            "all_comments": int(p.get("all_comments", 0)),
            "raw_status": p.get("status", "?"),
            "status_short": p.get("status_short", "?"),
            "human_status": st_text,
            "status_class": st_class,
            "priority": st_prio,
            "group_id": gid,
            "tarif_id": p.get("tarif_id"),
            "manage_url": f"https://qcomment.com/manageprojects/showproject/{p['id']}",
        }
        grouped[gname].append(rec)
        pending_total += pending
        accepted_total += accepted
        rejected_total += rejected
        rework_total += rework

    for k in grouped:
        grouped[k].sort(key=lambda x: (x["priority"], x["project_id"]))

    return {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "balance": balance_value,
        "total_projects": len(projects),
        "pending_review": pending_total,
        "accepted_total": accepted_total,
        "rejected_total": rejected_total,
        "rework_total": rework_total,
        "groups": dict(grouped),
        "_raw_projects_count": len(projects),
    }


def diff_snapshots(prev: dict, curr: dict) -> dict:
    return {
        "balance_change": float(curr.get("balance", 0)) - float(prev.get("balance", 0)),
        "pending_change": curr["pending_review"] - prev["pending_review"],
        "accepted_change": curr["accepted_total"] - prev["accepted_total"],
        "rejected_change": curr["rejected_total"] - prev["rejected_total"],
        "rework_change": curr["rework_total"] - prev["rework_total"],
        "new_pending_projects": _diff_pending_projects(prev, curr),
    }


def _diff_pending_projects(prev: dict, curr: dict) -> list[str]:
    prev_pending = set()
    for projs in prev.get("groups", {}).values():
        for p in projs:
            if p.get("pending", 0) > 0:
                prev_pending.add(p["project_id"])
    curr_pending = set()
    for projs in curr.get("groups", {}).values():
        for p in projs:
            if p.get("pending", 0) > 0:
                curr_pending.add(p["project_id"])
    return sorted(curr_pending - prev_pending)


VALID_SLUG = __import__("re").compile(r"^[a-z0-9][a-z0-9_-]*$")

def main():
    if len(sys.argv) < 2:
        sys.exit("Usage: qcomment-monitor.py <client_slug>")
    client = sys.argv[1]

    if not VALID_SLUG.match(client):
        sys.exit(f"❌ Invalid client_slug: {client!r} — must be [a-z0-9][a-z0-9_-]*")

    client_dir = ROOT / "clients" / client
    if not client_dir.exists():
        sys.exit(f"❌ Client folder not found: {client_dir}")

    cfg = load_qcomment_config()
    out_dir = client_dir / "orm" / "qcomment"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"→ Pulling qcomment API for {client}")
    snap = build_snapshot(cfg)

    stamp = datetime.now().strftime("%Y-%m-%d-%H%M")
    snap_path = out_dir / f"snap-{stamp}.json"
    with open(snap_path, "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=2)
    print(f"✓ Snapshot: {snap_path}")

    # Diff vs previous
    prev_snaps = sorted(out_dir.glob("snap-*.json"))
    diff: dict = {"balance_change": 0, "pending_change": 0, "accepted_change": 0,
                  "rejected_change": 0, "rework_change": 0, "new_pending_projects": []}
    if len(prev_snaps) >= 2:
        with open(prev_snaps[-2], encoding="utf-8") as f:
            prev = json.load(f)
        diff = diff_snapshots(prev, snap)

    # History CSV
    history_path = out_dir / "history.csv"
    if not history_path.exists():
        with open(history_path, "w", encoding="utf-8") as f:
            f.write("timestamp,balance,total_projects,pending,accepted,rejected,rework,new_pending_count\n")
    with open(history_path, "a", encoding="utf-8") as f:
        f.write(
            f"{snap['ts']},{snap['balance']},{snap['total_projects']},"
            f"{snap['pending_review']},{snap['accepted_total']},"
            f"{snap['rejected_total']},{snap['rework_total']},"
            f"{len(diff['new_pending_projects'])}\n"
        )

    # Console output
    print(f"\n{'='*60}")
    print(f"BALANCE: {snap['balance']} ₽")
    print(f"PROJECTS: {snap['total_projects']}")
    print(f"⏳ pending review: {snap['pending_review']} (Δ {diff['pending_change']:+d})")
    print(f"✅ accepted:       {snap['accepted_total']} (Δ {diff['accepted_change']:+d})")
    print(f"❌ rejected:       {snap['rejected_total']} (Δ {diff['rejected_change']:+d})")
    print(f"🔄 rework:         {snap['rework_total']} (Δ {diff['rework_change']:+d})")
    if diff["new_pending_projects"]:
        print(f"\n🚨 НОВЫЕ ПРОЕКТЫ ЖДУТ ПРИНЯТИЯ:")
        for pid in diff["new_pending_projects"]:
            print(f"   → https://qcomment.com/manageprojects/showproject/{pid}")
    if snap["pending_review"] > 0:
        print(f"\n⚠️  ВСЕГО {snap['pending_review']} pending — иди принимать")
    print("="*60)

    # Q12 budget-cap: алёрт если баланс упал ниже threshold
    _send_budget_alert(client)

    return 0 if snap["pending_review"] == 0 else 2  # exit 2 → есть что принимать


if __name__ == "__main__":
    sys.exit(main())
