"""Q12 budget-cap — алёрты при низком балансе бирж + daily spend-cap.

Decision: decisions/2026-05-10-orm-budget-cap.md
"""
from __future__ import annotations
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal

from .config import ROOT
from .loaders import latest_qcomment, load_yaml


def _registry_finance(client: str) -> dict:
    reg = load_yaml(ROOT / "clients" / client / "orm" / "registry.yaml")
    return reg.get("finance", {}) or {}


def _registry_thresholds(client: str) -> dict:
    fin = _registry_finance(client)
    th = fin.get("balance_thresholds") or {}
    return {
        "warn_rub": th.get("warn_rub", 1000),
        "critical_rub": th.get("critical_rub", 500),
        "daily_spend_cap_rub": fin.get("daily_spend_cap_rub", 5000),
        "rate_limit_hours": fin.get("alert_rate_limit_hours", 6),
    }


BalanceLevel = Literal["norm", "warn", "critical"]


def check_qcomment_balance(client: str) -> dict:
    """Возвращает {level, balance_rub, threshold_warn, threshold_critical}.

    level: 'norm' (>warn), 'warn' (warn≤balance≤?), 'critical' (<critical)
    """
    qc = latest_qcomment(client)
    if not qc:
        return {"level": "norm", "balance_rub": None, "reason": "no snapshot"}

    bal_raw = qc.get("balance", "0")
    try:
        balance = float(str(bal_raw).replace(" ", "").replace(",", ".").replace("₽", "").strip())
    except (TypeError, ValueError):
        balance = 0.0

    th = _registry_thresholds(client)
    if balance < th["critical_rub"]:
        level = "critical"
    elif balance < th["warn_rub"]:
        level = "warn"
    else:
        level = "norm"

    return {
        "level": level,
        "balance_rub": balance,
        "threshold_warn": th["warn_rub"],
        "threshold_critical": th["critical_rub"],
    }


def daily_spend_rub(client: str, window_hours: int = 24) -> float:
    """Сумма расходов за последние window_hours через audit-trail.jsonl (Q9).

    Если audit-trail.jsonl нет — возвращает 0.0 (нет данных = нет cap'а).
    """
    p = ROOT / "clients" / client / "orm" / "audit-trail.jsonl"
    if not p.exists():
        return 0.0

    cutoff = (datetime.now() - timedelta(hours=window_hours)).isoformat()
    total = 0.0
    try:
        with open(p) as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("ts", "") < cutoff:
                    continue
                if rec.get("type") not in ("placement", "payment"):
                    continue
                amount = rec.get("amount_rub", 0)
                if isinstance(amount, (int, float)):
                    total += amount
    except OSError:
        return 0.0
    return total


def is_placement_allowed(client: str) -> dict:
    """Можно ли отправлять новые заказы? Возвращает {allowed, reason, ...}.

    Блокируем если:
    - critical balance (< threshold_critical)
    - daily spend cap превышен
    """
    bal = check_qcomment_balance(client)
    if bal["level"] == "critical":
        return {
            "allowed": False,
            "reason": f"qcomment balance critical: {bal['balance_rub']} ₽ < {bal['threshold_critical']} ₽",
            "balance": bal,
        }

    spent = daily_spend_rub(client)
    th = _registry_thresholds(client)
    cap = th["daily_spend_cap_rub"]
    if spent >= cap:
        return {
            "allowed": False,
            "reason": f"daily spend cap exceeded: {spent} ₽ >= {cap} ₽",
            "spent_24h": spent,
            "cap": cap,
        }

    return {
        "allowed": True,
        "balance": bal,
        "spent_24h": spent,
        "cap": cap,
    }


def render_budget_alert_html(client: str) -> str | None:
    """HTML-алёрт для встраивания в render_alerts. Возвращает None если всё ок."""
    bal = check_qcomment_balance(client)
    if bal.get("balance_rub") is None:
        return None
    if bal["level"] == "norm":
        return None
    if bal["level"] == "critical":
        return (f'<div class="alert">💸 qcomment баланс CRITICAL: '
                f'{bal["balance_rub"]:.0f} ₽ < {bal["threshold_critical"]} ₽ — '
                f'<strong>пополнить срочно</strong>, новые заказы заблокированы</div>')
    if bal["level"] == "warn":
        return (f'<div class="alert warning">⚠️ qcomment баланс низкий: '
                f'{bal["balance_rub"]:.0f} ₽ < {bal["threshold_warn"]} ₽ — '
                f'<a href="https://qcomment.com/finance/" target="_blank">пополнить →</a></div>')
    return None


# Rate-limit: чтобы не спамить cron-алёрты
# P0-1 migration (2026-05-11): state в $HOME — persistent, переживает reboot Mac.
_LAST_ALERT_STATE = Path.home() / ".claude/state/orm-pulse/budget-last-alert.json"


def should_send_alert(level: str, rate_limit_hours: int = 6) -> bool:
    """True если последний алёрт этого level старше rate_limit_hours."""
    _LAST_ALERT_STATE.parent.mkdir(parents=True, exist_ok=True)
    state = {}
    if _LAST_ALERT_STATE.exists():
        try:
            state = json.loads(_LAST_ALERT_STATE.read_text())
        except (OSError, json.JSONDecodeError):
            state = {}
    last_ts = state.get(level)
    if not last_ts:
        return True
    try:
        last_dt = datetime.fromisoformat(last_ts)
    except ValueError:
        return True
    return (datetime.now() - last_dt).total_seconds() >= rate_limit_hours * 3600


def mark_alert_sent(level: str):
    _LAST_ALERT_STATE.parent.mkdir(parents=True, exist_ok=True)
    state = {}
    if _LAST_ALERT_STATE.exists():
        try:
            state = json.loads(_LAST_ALERT_STATE.read_text())
        except (OSError, json.JSONDecodeError):
            state = {}
    state[level] = datetime.now().isoformat()
    _LAST_ALERT_STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2))
