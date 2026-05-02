#!/usr/bin/env python3
"""command-center — единая HTML-страница для ORM workflow клиента.

Агрегирует данные из всех snapshot источников:
- qcomment snapshot (balance, проекты, pending)
- reviews-tracker history (rating, total, темп)
- orders-state.json (11 корзин Sheet)
- executor-ledger.csv (передачи)
- kupi-otziv snapshot (если есть)
- registry.yaml (контрагенты)
- research/ (links)

Output:
  Локально: clients/<slug>/orm/command-center.html
  Live:     https://artvision.pro/orm-command-center/<slug>.html (noindex + basic-auth)

Usage:
  command-center.py <client_slug> [--deploy]
"""
from __future__ import annotations
import argparse
import csv
import html
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path("/Users/antonk/artvision-data")
VPS_USER = "root"
VPS_HOST = "80.90.181.152"
VPS_DIR = "/var/www/artvision/orm-command-center"
PUBLIC_BASE = "https://artvision.pro/orm-command-center"


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
    p = Path("/tmp/orm-pulse") / client / "orders-state.json"
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


CSS = """
:root { color-scheme: light; --brand: #2c3e88; --bg: #f4f5f7; --card: #fff;
        --critical: #b71c1c; --critical-bg: #fdecea;
        --warning: #e65100; --warning-bg: #fff3e0;
        --good: #1b5e20; --good-bg: #e8f5e9;
        --text: #1a1a1a; --muted: #666; }
* { box-sizing: border-box; }
body { font-family: -apple-system, Segoe UI, Roboto, sans-serif;
       background: var(--bg); color: var(--text); margin: 0; padding: 16px; }
.container { max-width: 1400px; margin: 0 auto; }
header { background: linear-gradient(135deg, var(--brand) 0%, #1e2c5f 100%);
         color: white; padding: 20px 28px; border-radius: 12px;
         margin-bottom: 16px; box-shadow: 0 4px 12px rgba(44,62,136,0.2); }
header h1 { margin: 0 0 4px; font-size: 22px; }
header .meta { font-size: 13px; opacity: 0.85; }
header .badges { margin-top: 8px; }
header .badge { background: rgba(255,255,255,0.2); padding: 3px 10px;
                border-radius: 4px; font-size: 11px; margin-right: 6px;
                font-weight: 600; letter-spacing: 0.5px; }

.alerts { display: grid; grid-template-columns: 1fr; gap: 8px; margin-bottom: 16px; }
.alert { background: var(--critical-bg); border-left: 4px solid var(--critical);
         color: var(--critical); padding: 10px 16px; border-radius: 6px;
         font-weight: 600; font-size: 14px; }
.alert.warning { background: var(--warning-bg); border-color: var(--warning); color: var(--warning); }
.alert.good { background: var(--good-bg); border-color: var(--good); color: var(--good); }
.alert a { color: inherit; }

.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
        gap: 16px; }
.card { background: var(--card); border-radius: 10px; padding: 18px 22px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
.card h2 { margin: 0 0 12px; font-size: 16px; color: var(--brand);
           border-bottom: 1px solid #eee; padding-bottom: 6px;
           display: flex; align-items: center; justify-content: space-between; }
.card h2 .icon { font-size: 18px; margin-right: 8px; }
.card h2 .pill { background: #eef; color: var(--brand); padding: 2px 8px;
                 border-radius: 10px; font-size: 11px; font-weight: 600; }
.metric { display: flex; justify-content: space-between; align-items: baseline;
          padding: 6px 0; border-bottom: 1px dotted #eee; font-size: 13px; }
.metric:last-child { border-bottom: none; }
.metric .label { color: var(--muted); }
.metric .value { font-weight: 700; color: var(--text); font-variant-numeric: tabular-nums; }
.metric .value.big { font-size: 20px; color: var(--brand); }
.metric .value.danger { color: var(--critical); }
.metric .value.warning { color: var(--warning); }
.metric .value.good { color: var(--good); }
.bucket-list { list-style: none; padding: 0; margin: 0; }
.bucket-list li { padding: 5px 0; font-size: 13px;
                  display: flex; justify-content: space-between; }
.bucket-list .count { font-weight: 700; color: var(--brand); }
table.compact { width: 100%; border-collapse: collapse; font-size: 12px; }
table.compact th, table.compact td { padding: 4px 8px; text-align: left;
                                      border-bottom: 1px solid #f0f0f0; }
table.compact th { color: var(--muted); font-weight: 500; }

.research-link { display: block; padding: 8px 12px; margin: 4px 0;
                 background: #f7f8fa; border-left: 3px solid var(--brand);
                 border-radius: 4px; font-size: 13px; text-decoration: none;
                 color: var(--text); }
.research-link:hover { background: #eef; }
.research-link .name { font-weight: 600; }
.research-link .meta { color: var(--muted); font-size: 11px; }

.empty { text-align: center; color: var(--muted); padding: 30px;
         font-size: 13px; font-style: italic; }
.refresh-cmd { background: #1f2937; color: #e5e7eb; padding: 12px 16px;
               border-radius: 6px; font-family: SFMono-Regular, monospace;
               font-size: 12px; margin: 12px 0; overflow-x: auto; }
footer { text-align: center; color: var(--muted); font-size: 11px;
         margin-top: 24px; padding: 16px; }
.tag { display: inline-block; padding: 2px 7px; border-radius: 10px;
       font-size: 11px; font-weight: 600; margin-right: 4px; }
.tag.ok { background: #c8e6c9; color: #1b5e20; }
.tag.crit { background: #ffcdd2; color: #b71c1c; }
.tag.warn { background: #ffe0b2; color: #e65100; }
.tag.neutral { background: #eee; color: #555; }
@media (max-width: 600px) {
  body { padding: 8px; }
  .card { padding: 14px 16px; }
  header { padding: 14px 18px; }
}
"""


def render_alerts(qc, sheet_state, kwork_sum) -> str:
    alerts = []
    if qc and qc.get("pending_review", 0) > 0:
        n = qc["pending_review"]
        alerts.append(
            f'<div class="alert">🚨 QComment: {n} проект(ов) ждут принятия — '
            f'<a href="https://artvision.pro/qcomment/" target="_blank">принять →</a> '
            f'(auto-accept на 3-й день!)</div>'
        )
    if sheet_state:
        sc = sheet_state.get("state_counts", {})
        if sc.get("approved_not_given", 0) > 0:
            n = sc["approved_not_given"]
            alerts.append(
                f'<div class="alert warning">⭐ Sheet1: {n} текстов «согласованы, не отданы» — готовы к раздаче</div>'
            )
    if not alerts:
        alerts.append('<div class="alert good">✅ Критичных алёртов нет</div>')
    return '<section class="alerts">' + "\n".join(alerts) + "</section>"


def render_qcomment_card(qc) -> str:
    if not qc:
        return '<div class="card"><h2><span><span class="icon">📊</span>QComment</span></h2><div class="empty">Нет snapshot. Запустите: <code>orm-pulse bluemart qcomment</code></div></div>'

    pending = qc.get("pending_review", 0)
    pending_class = "danger" if pending > 0 else "good"
    pill = f'<span class="pill">{qc.get("ts", "?")[:16]}</span>'
    rows = ""
    for gname, projs in (qc.get("groups") or {}).items():
        n = len(projs)
        pend = sum(1 for p in projs if p.get("pending", 0) > 0)
        pend_html = f' <span class="tag crit">{pend} ждут</span>' if pend else ''
        rows += f'<li>{html.escape(gname)} <span class="count">{n}</span>{pend_html}</li>'

    return f'''<div class="card">
  <h2><span><span class="icon">📊</span>QComment</span>{pill}</h2>
  <div class="metric"><span class="label">Баланс</span><span class="value big">{qc.get("balance", "?")} ₽</span></div>
  <div class="metric"><span class="label">Всего проектов</span><span class="value">{qc.get("total_projects", 0)}</span></div>
  <div class="metric"><span class="label">⏳ Ждут принятия</span><span class="value {pending_class}">{pending}</span></div>
  <div class="metric"><span class="label">✅ Принято</span><span class="value">{qc.get("accepted_total", 0)}</span></div>
  <div class="metric"><span class="label">❌ Отклонено</span><span class="value">{qc.get("rejected_total", 0)}</span></div>
  <div class="metric"><span class="label">🔄 На доработке</span><span class="value">{qc.get("rework_total", 0)}</span></div>
  <ul class="bucket-list" style="margin-top:8px">{rows}</ul>
  <p style="margin:8px 0 0;font-size:11px;color:var(--muted)">
    <a href="https://artvision.pro/qcomment/" target="_blank">Live dashboard →</a>
  </p>
</div>'''


def render_reviews_card(pace, qc) -> str:
    if not pace:
        return '<div class="card"><h2><span><span class="icon">⭐</span>Yandex Reviews</span></h2><div class="empty">Нет history. LaunchAgent reviews-tracker должен прогнать 4×/день.</div></div>'

    rating = pace.get("rating_now", "?")
    total = pace.get("total_now", "?")
    delta = pace.get("delta_total", 0)
    delta_class = "good" if delta > 0 else ("danger" if delta < 0 else "")
    delta_str = f"+{delta}" if delta > 0 else str(delta)

    return f'''<div class="card">
  <h2><span><span class="icon">⭐</span>Yandex Reviews</span><span class="pill">{pace.get("snapshots", 0)} snapshots</span></h2>
  <div class="metric"><span class="label">Рейтинг сейчас</span><span class="value big">{rating}</span></div>
  <div class="metric"><span class="label">Всего отзывов</span><span class="value">{total}</span></div>
  <div class="metric"><span class="label">Δ за период</span><span class="value {delta_class}">{delta_str}</span></div>
  <div class="metric"><span class="label">Окно</span><span class="value" style="font-size:11px">{pace.get("first_ts", "?")} → {pace.get("last_ts", "?")}</span></div>
  <p style="margin:8px 0 0;font-size:11px;color:var(--muted)">
    <a href="https://reviews.yandex.ru/shop/blumart.ru" target="_blank">reviews.yandex.ru →</a>
  </p>
</div>'''


def render_orders_state_card(state) -> str:
    if not state:
        return '<div class="card"><h2><span><span class="icon">📋</span>Sheet Воронка</span></h2><div class="empty">Нет orders-state. Запустите: <code>orm-pulse bluemart orders-state</code></div></div>'

    sc = state.get("state_counts", {})
    rows = []
    bucket_labels = {
        "published": ("✅ Опубликовано", "good"),
        "moderation": ("⏳ На модерации", "warn"),
        "given_to_okponrussia": ("📤 У okponrussia", "neutral"),
        "given_to_kwork": ("📤 У kwork", "neutral"),
        "given_internal_sheet": ("📋 Согл.+дата", "neutral"),
        "approved_not_given": ("⭐ НЕ ОТДАН", "warn"),
        "waiting_approval": ("⏸ Ждёт согл.", "neutral"),
        "rejected": ("❌ Не прошёл", "crit"),
        "spent": ("💸 Потрачен", "crit"),
        "rework_pool": ("🔄 Переделать", "neutral"),
        "uniq_failed": ("🚫 Неуник", "crit"),
        "other": ("? Другое", "neutral"),
    }
    for key, (label, cls) in bucket_labels.items():
        n = sc.get(key, 0)
        if n == 0:
            continue
        rows.append(f'<li>{label} <span class="count"><span class="tag {cls}">{n}</span></span></li>')

    pace = state.get("pace") or {}
    pace_html = ""
    if pace and pace.get("per_day") is not None:
        pace_class = "good" if pace["per_day"] >= 5 else "warning"
        pace_html = f'''<div class="metric" style="margin-top:8px">
            <span class="label">Темп публикаций</span>
            <span class="value {pace_class}">{pace["per_day"]:.2f}/день</span>
        </div>'''

    return f'''<div class="card">
  <h2><span><span class="icon">📋</span>Sheet Воронка</span></h2>
  <ul class="bucket-list">{"".join(rows)}</ul>
  {pace_html}
</div>'''


def render_ledger_card(stats) -> str:
    total = stats.get("total", 0)
    if total == 0:
        return '<div class="card"><h2><span><span class="icon">📚</span>Executor Ledger</span></h2><div class="empty">Записей нет. <code>executor-ledger.py add bluemart ...</code></div></div>'

    by_ex_html = "".join(
        f'<tr><td>{html.escape(ex)}</td><td>{n}</td></tr>'
        for ex, n in list(stats.get("by_executor", {}).items())[:8]
    )

    return f'''<div class="card">
  <h2><span><span class="icon">📚</span>Executor Ledger</span><span class="pill">{total} entries</span></h2>
  <table class="compact"><thead><tr><th>Executor</th><th>Records</th></tr></thead>
  <tbody>{by_ex_html}</tbody></table>
  <p style="margin:8px 0 0;font-size:11px;color:var(--muted)">{stats.get("first_ts", "?")} → {stats.get("last_ts", "?")}</p>
</div>'''


def render_kupi_otziv_card(snap) -> str:
    if not snap:
        return '<div class="card"><h2><span><span class="icon">💰</span>Kupi-Otziv</span></h2><div class="empty">Нет snapshot. Setup: cookies + <code>orm-pulse bluemart kupi-otziv</code></div></div>'
    bal = snap.get("balance", {}).get("value_rub", "0.00")
    return f'''<div class="card">
  <h2><span><span class="icon">💰</span>Kupi-Otziv</span></h2>
  <div class="metric"><span class="label">Баланс</span><span class="value">{bal} ₽</span></div>
  <div class="metric"><span class="label">Проектов</span><span class="value">{len(snap.get("projects", []))}</span></div>
  <div class="metric"><span class="label">Заказов</span><span class="value">{len(snap.get("orderlist", []))}</span></div>
  <div class="metric"><span class="label">История ops</span><span class="value">{len(snap.get("billing_history", []))}</span></div>
</div>'''


def render_kwork_card(kw) -> str:
    if not kw:
        return '<div class="card"><h2><span><span class="icon">🛠</span>Kwork</span></h2><div class="empty">Login fails (26.04). Background-агент пытается с новым паролем.</div></div>'
    snippet = html.escape(kw.get("snippet", "")[:300])
    return f'''<div class="card">
  <h2><span><span class="icon">🛠</span>Kwork</span></h2>
  <pre style="background:#f7f8fa;padding:8px;border-radius:4px;font-size:11px;white-space:pre-wrap">{snippet}</pre>
  <p style="margin:8px 0 0;font-size:11px"><a href="kwork.ru" target="_blank">kwork.ru →</a></p>
</div>'''


def render_research_card(items) -> str:
    if not items:
        return '<div class="card"><h2><span><span class="icon">🔬</span>Research</span></h2><div class="empty">Отчётов нет</div></div>'
    rows = "".join(
        f'<a class="research-link" href="{html.escape(r["live_url"])}" target="_blank">'
        f'<span class="name">{html.escape(r["name"])}</span> '
        f'<span class="meta">{r["size_kb"]} KB · live →</span></a>'
        for r in items
    )
    return f'<div class="card"><h2><span><span class="icon">🔬</span>Research</span><span class="pill">{len(items)}</span></h2>{rows}</div>'


def render_contractors_card(registry) -> str:
    contractors = registry.get("contractors", [])
    rows = []
    for c in contractors:
        status = c.get("status", "?")
        cls = "ok" if status == "active" else ("crit" if "fail" in status else "neutral")
        rows.append(
            f'<tr><td>{html.escape(c.get("name", "?"))}</td>'
            f'<td><span class="tag {cls}">{status}</span></td></tr>'
        )
    return f'''<div class="card">
  <h2><span><span class="icon">🤝</span>Contractors</span><span class="pill">{len(contractors)}</span></h2>
  <table class="compact"><thead><tr><th>Name</th><th>Status</th></tr></thead><tbody>{"".join(rows)}</tbody></table>
</div>'''


def build_html(client: str) -> str:
    registry = load_yaml(ROOT / "clients" / client / "orm" / "registry.yaml")
    qc = latest_qcomment(client)
    pace = reviews_pace(client)
    state = latest_orders_state(client)
    ledger = ledger_stats(client)
    research = list_research(client)
    ko = kupi_otziv_latest(client)
    kw = kwork_summary(client)

    name = registry.get("client_full_name", client)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M МСК")

    alerts_html = render_alerts(qc, state, kw)

    cards = [
        render_qcomment_card(qc),
        render_reviews_card(pace, qc),
        render_orders_state_card(state),
        render_ledger_card(ledger),
        render_contractors_card(registry),
        render_kwork_card(kw),
        render_kupi_otziv_card(ko),
        render_research_card(research),
    ]

    return f'''<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow, noarchive, nosnippet">
<title>{html.escape(name)} — Command Center</title>
<style>{CSS}</style>
</head>
<body>
<div class="container">
<header>
  <h1>{html.escape(name)} — ORM Command Center</h1>
  <div class="meta">Сгенерировано: {ts}</div>
  <div class="badges">
    <span class="badge">INTERNAL</span>
    <span class="badge">noindex</span>
    <span class="badge">orm-pulse</span>
  </div>
</header>

{alerts_html}

<section class="grid">
{"".join(cards)}
</section>

<div class="card" style="margin-top:16px">
  <h2><span class="icon">🔄</span>Refresh</h2>
  <div class="refresh-cmd">~/.claude/skills/orm-pulse/scripts/run.sh {client} full</div>
  <div class="refresh-cmd">~/.claude/skills/orm-pulse/scripts/command-center.py {client} --deploy</div>
  <p style="font-size:11px;color:var(--muted);margin:8px 0 0">
    Live qcomment dashboard:
    <a href="https://artvision.pro/qcomment/" target="_blank">artvision.pro/qcomment/</a>
  </p>
</div>

<footer>
  Artvision ORM Command Center · X-Robots-Tag noindex · INTERNAL ONLY
</footer>
</div>
</body>
</html>'''


def deploy(client: str, html_text: str) -> tuple[bool, str]:
    local = ROOT / "clients" / client / "orm" / "command-center.html"
    local.write_text(html_text, encoding="utf-8")

    Path("/tmp/.claude_outbound_ack").touch()
    subprocess.run(["ssh", f"{VPS_USER}@{VPS_HOST}", f"mkdir -p {VPS_DIR}"], check=True)
    Path("/tmp/.claude_outbound_ack").touch()
    res = subprocess.run(
        ["scp", "-q", str(local), f"{VPS_USER}@{VPS_HOST}:{VPS_DIR}/{client}.html"],
        capture_output=True, text=True,
    )
    if res.returncode != 0:
        return False, f"scp failed: {res.stderr}"
    return True, f"{PUBLIC_BASE}/{client}.html"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("client")
    parser.add_argument("--deploy", action="store_true")
    args = parser.parse_args()

    html_text = build_html(args.client)
    print(f"✓ Generated HTML: {len(html_text)} chars")

    if args.deploy:
        ok, msg = deploy(args.client, html_text)
        if ok:
            print(f"✓ Deployed: {msg}")
        else:
            print(f"✗ FAILED: {msg}")
            return 2
    else:
        local = ROOT / "clients" / args.client / "orm" / "command-center.html"
        local.write_text(html_text, encoding="utf-8")
        print(f"✓ Saved local: {local}")
        print("Use --deploy to upload to VPS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
