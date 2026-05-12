#!/usr/bin/env python3
"""alert-router — отправка ORM-алёртов в TG команде Артвишн.

Источники сигналов:
- qcomment snapshot: pending_review > 0
- reviews-tracker history: total падает (удалены отзывы) или темп <0.5/день
- orders-state: rejected увеличился, approved_not_given > 20
- executor-ledger: записей за 24ч нет (тишина в pipeline)

Куда: TG group команды (-4273200821) — НЕ заказчику.

Антиспам: state в /tmp/orm-pulse/<slug>/alerts-state.json,
  не повторять одинаковый алёрт чаще раза в 6 часов.

Usage:
  alert-router.py <client_slug> [--dry-run] [--force]
"""
from __future__ import annotations
import argparse
import asyncio
import csv
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent))
from lib.config import ROOT  # noqa: E402

TG_TEAM_CHAT = -4273200821  # группа команды Артвишн
RATE_LIMIT_HOURS = 6


def load_alert_state(slug: str) -> dict:
    p = Path(str(Path.home() / ".claude/state/orm-pulse")) / slug / "alerts-state.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}


def save_alert_state(slug: str, state: dict) -> None:
    p = Path(str(Path.home() / ".claude/state/orm-pulse")) / slug / "alerts-state.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, ensure_ascii=False, indent=2))


def can_send(state: dict, alert_id: str, force: bool) -> bool:
    if force:
        return True
    last = state.get(alert_id)
    if not last:
        return True
    try:
        ts = datetime.fromisoformat(last)
    except ValueError:
        return True
    return datetime.now() - ts >= timedelta(hours=RATE_LIMIT_HOURS)


def collect_alerts(slug: str) -> list[dict]:
    """Собрать список алёртов для отправки."""
    alerts: list[dict] = []

    # 1. QComment pending
    qc_dir = ROOT / "clients" / slug / "orm" / "qcomment"
    if qc_dir.exists():
        snaps = sorted(qc_dir.glob("snap-*.json"))
        if snaps:
            try:
                qc = json.loads(snaps[-1].read_text())
                pending = qc.get("pending_review", 0)
                if pending > 0:
                    pids = []
                    for projs in (qc.get("groups") or {}).values():
                        for p in projs:
                            if p.get("pending", 0) > 0:
                                pids.append(p["project_id"])
                    alerts.append({
                        "id": f"qc-pending-{slug}-{','.join(pids)}",
                        "severity": "critical",
                        "title": f"🚨 QComment: {pending} проект(ов) ждут принятия",
                        "body": (
                            f"⚠️ Auto-acceptance через 3 дня — иди принимать!\n"
                            f"Pending IDs: {', '.join(pids)}\n"
                            f"Балaнс: {qc.get('balance', '?')} ₽\n"
                            f"Open: https://artvision.pro/qcomment/"
                        ),
                    })
            except Exception:
                pass

    # 2. Reviews-tracker — total падает или темп низкий
    history = ROOT / "clients" / slug / "orm" / "reviews-tracker" / "history.csv"
    if history.exists():
        try:
            rows = list(csv.DictReader(open(history)))
            if len(rows) >= 2:
                first, last = rows[0], rows[-1]
                t_first = int(first.get("total", 0) or 0)
                t_last = int(last.get("total", 0) or 0)
                delta = t_last - t_first
                if delta < 0:
                    alerts.append({
                        "id": f"reviews-drop-{slug}",
                        "severity": "critical",
                        "title": f"📉 reviews.yandex.ru: total упал на {abs(delta)}",
                        "body": (
                            f"Возможное удаление отзывов (антифрод Я).\n"
                            f"Окно: {first.get('timestamp', '?')[:16]} → {last.get('timestamp', '?')[:16]}\n"
                            f"Было: {t_first} → стало: {t_last}"
                        ),
                    })
                # темп
                try:
                    ts_first = datetime.strptime(first["timestamp"][:16], "%Y-%m-%dT%H:%M")
                    ts_last = datetime.strptime(last["timestamp"][:16], "%Y-%m-%dT%H:%M")
                    days = max((ts_last - ts_first).total_seconds() / 86400, 0.1)
                    pace = delta / days
                    if days >= 1 and pace < 0.5 and delta >= 0:
                        alerts.append({
                            "id": f"low-pace-{slug}",
                            "severity": "warning",
                            "title": f"⚠️ Темп публикаций {pace:.2f}/день — ниже 0.5",
                            "body": (
                                f"Цель 5/день. Дельта {delta} за {days:.1f} дн.\n"
                                f"Возможно okponrussia не отдаёт или модерация режет."
                            ),
                        })
                except ValueError:
                    pass
        except Exception:
            pass

    # 3. Orders-state — approved_not_given > 20 или rejected увеличился
    state_path = Path(str(Path.home() / ".claude/state/orm-pulse")) / slug / "orders-state.json"
    if state_path.exists():
        try:
            st = json.loads(state_path.read_text())
            sc = st.get("state_counts", {})
            if sc.get("approved_not_given", 0) >= 20:
                n = sc["approved_not_given"]
                alerts.append({
                    "id": f"approved-stockpile-{slug}-{n}",
                    "severity": "warning",
                    "title": f"⭐ Sheet1: {n} текстов «Текст согласован» не отданы",
                    "body": (
                        f"Готовы к раздаче исполнителям. Передать в okponrussia / qcomment / kwork.\n"
                        f"Run: ./run.sh {slug} orders-state"
                    ),
                })
            rej = sc.get("rejected", 0)
            if rej >= 5:
                alerts.append({
                    "id": f"rejected-{slug}-{rej}",
                    "severity": "warning",
                    "title": f"❌ {rej} текстов не прошли модерацию",
                    "body": "Переписать через банк «переделать» или попросить @bitkey новые варианты.",
                })
        except Exception:
            pass

    # 4. Ledger — тишина (нет записей за 48ч)
    ledger = ROOT / "clients" / slug / "orm" / "executor-ledger.csv"
    if ledger.exists():
        try:
            rows = list(csv.DictReader(open(ledger)))
            if rows:
                last_ts = rows[-1]["timestamp"][:16]
                last_dt = datetime.strptime(last_ts, "%Y-%m-%dT%H:%M")
                if datetime.now() - last_dt > timedelta(hours=48):
                    hours = (datetime.now() - last_dt).total_seconds() / 3600
                    alerts.append({
                        "id": f"ledger-silence-{slug}",
                        "severity": "warning",
                        "title": f"📚 Executor-ledger тишина {hours:.0f}ч",
                        "body": "Нет передач исполнителям. Проверить что pipeline не остановился.",
                    })
        except Exception:
            pass

    return alerts


async def send_alerts(slug: str, alerts: list[dict], dry_run: bool, force: bool) -> int:
    if not alerts:
        print("(no alerts to send)")
        return 0

    if dry_run:
        print(f"DRY RUN — would send {len(alerts)} alerts:")
        for a in alerts:
            print(f"  [{a['severity']}] {a['title']}")
        return 0

    state = load_alert_state(slug)
    to_send = [a for a in alerts if can_send(state, a["id"], force)]
    skipped = len(alerts) - len(to_send)
    if skipped:
        print(f"⏸ Skipped {skipped} alerts (rate-limit {RATE_LIMIT_HOURS}h)")

    if not to_send:
        return 0

    # Импортируем Telethon с креды из tokens.json
    sys.path.insert(0, str(Path(__file__).parent))
    from telethon import TelegramClient  # type: ignore

    tokens = json.loads((ROOT / "tokens.json").read_text())
    api_id = int(tokens["telegram"]["api_id"])
    api_hash = tokens["telegram"]["api_hash"]

    orig_session = Path.home() / ".claude/state/telethon_session.session"
    clone_session = Path.home() / ".claude/skills/orm-pulse/state/telethon_session_alerts.session"
    clone_session.parent.mkdir(parents=True, exist_ok=True)
    if orig_session.exists() and not clone_session.exists():
        import shutil
        shutil.copy(orig_session, clone_session)

    client = TelegramClient(str(clone_session).replace(".session", ""), api_id, api_hash)
    await client.start()

    sent_at = datetime.now().isoformat(timespec="seconds")
    for a in to_send:
        msg = (
            f"**{a['title']}**\n\n"
            f"{a['body']}\n\n"
            f"_{slug} · {sent_at[:16]} · alert-router_"
        )
        try:
            await client.send_message(TG_TEAM_CHAT, msg, parse_mode="md")
            state[a["id"]] = sent_at
            print(f"✓ Sent: {a['title']}")
        except Exception as e:
            print(f"✗ Failed [{a['title']}]: {e}", file=sys.stderr)

    await client.disconnect()
    save_alert_state(slug, state)
    return len(to_send)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("client")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true",
                        help="игнор rate-limit, шлёт повторно")
    args = parser.parse_args()

    alerts = collect_alerts(args.client)
    print(f"# Collected {len(alerts)} alerts for {args.client}")
    asyncio.run(send_alerts(args.client, alerts, args.dry_run, args.force))


if __name__ == "__main__":
    main()
