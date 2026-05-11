"""Card-renderers для command-center.

Вынесено из command-center.py при refactoring 2026-05-10.
Каждая render_*_card функция возвращает HTML строку для одного виджета дашборда.
"""
from __future__ import annotations
import csv
import html
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from .charts import daily_deltas_for_chart, render_publications_svg
from .config import ROOT
from .loaders import last_contact_per_executor
from .inventory import STATUS_EMOJI, sheet_tab_stats, parse_batch_compose, docs_inventory  # noqa: F401
from .budget_guard import render_budget_alert_html


def render_alerts(qc, sheet_state, kwork_sum, client: str = "blumart") -> str:
    alerts = []
    # Q12 — budget-cap алёрт (приоритет CRITICAL → первым)
    budget_alert = render_budget_alert_html(client)
    if budget_alert:
        alerts.append(budget_alert)
    if qc and qc.get("pending_review", 0) > 0:
        n = qc["pending_review"]
        alerts.append(
            f'<div class="alert">🚨 QComment: {n} проект(ов) ждут принятия — '
            f'<a href="https://qcomment.com/manageprojects/" target="_blank">принять →</a> '
            f'(нужен login в qcomment.com · auto-accept на 3-й день!)</div>'
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


def render_reviews_card(pace, qc, client: str = "bluemart") -> str:
    if not pace:
        return '<div class="card"><h2><span><span class="icon">⭐</span>Yandex Reviews</span></h2><div class="empty">Нет history. LaunchAgent reviews-tracker должен прогнать 4×/день.</div></div>'

    rating = pace.get("rating_now", "?")
    total = pace.get("total_now", "?")
    delta = pace.get("delta_total", 0)
    delta_class = "good" if delta > 0 else ("danger" if delta < 0 else "")
    delta_str = f"+{delta}" if delta > 0 else str(delta)

    deltas = daily_deltas_for_chart(client, days=14)
    chart_svg = render_publications_svg(deltas)
    chart_block = (
        f'<div style="margin-top:10px;padding-top:10px;border-top:1px solid var(--border)">'
        f'<div style="font-size:11px;color:var(--muted);margin-bottom:2px">Динамика публикаций (14 дней)</div>'
        f'{chart_svg}</div>'
    ) if chart_svg else ""

    return f'''<div class="card">
  <h2><span><span class="icon">⭐</span>Yandex Reviews</span><span class="pill">{pace.get("snapshots", 0)} snapshots</span></h2>
  <div class="metric"><span class="label">Рейтинг сейчас</span><span class="value big">{rating}</span></div>
  <div class="metric"><span class="label">Всего отзывов</span><span class="value">{total}</span></div>
  <div class="metric"><span class="label">Δ за период</span><span class="value {delta_class}">{delta_str}</span></div>
  <div class="metric"><span class="label">Окно</span><span class="value" style="font-size:11px">{pace.get("first_ts", "?")} → {pace.get("last_ts", "?")}</span></div>
  {chart_block}
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
        return ('<div class="card"><h2><span><span class="icon">💰</span>Kupi-Otziv</span>'
                '<span class="pill">отложено</span></h2>'
                '<div class="empty">Прайс снят 27.04: <strong>870 ₽/отзыв</strong> на Я.Карты '
                '(×40 vs qcomment 20-37 ₽). Не используем для массового потока — только '
                '<strong>bucket C</strong> (отклонённые модерацией) + lift звёзд (66 ₽/звезда). '
                'Ждём пополнения баланса для теста.</div></div>')
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
        return ('<div class="card"><h2><span><span class="icon">🛠</span>Kwork</span>'
                '<span class="pill">пароль обновлён 09.05</span></h2>'
                '<div class="empty">Креды в <code>tokens.json/kwork</code>. '
                'Нужен один login-тест через браузер (kwork — JS-модалка, curl не пройдёт). '
                'После теста — статус <code>active</code>.</div></div>')
    snippet = html.escape(kw.get("snippet", "")[:300])
    return f'''<div class="card">
  <h2><span><span class="icon">🛠</span>Kwork</span></h2>
  <pre style="background:#f7f8fa;padding:8px;border-radius:4px;font-size:11px;white-space:pre-wrap">{snippet}</pre>
  <p style="margin:8px 0 0;font-size:11px"><a href="kwork.ru" target="_blank">kwork.ru →</a></p>
</div>'''


def render_attribution_card(client: str) -> str:
    """Карточка attribution: кого пинговать на дозамену + готовые тексты сообщений.

    Читает свежий attribution-report-*.csv. Если нет — показывает «нет данных».
    """
    out_dir = ROOT / "clients" / client / "orm"
    csvs = sorted(out_dir.glob("attribution-report-*.csv"))
    if not csvs:
        return ('<div class="card"><h2><span><span class="icon">🔁</span>Attribution / Дозамена</span></h2>'
                '<div class="empty">Нет attribution-report.csv. Запусти: '
                '<code>python3 ~/.claude/skills/orm-pulse/scripts/attribution-report.py ' + client + '</code></div></div>')
    latest = csvs[-1]
    import csv as _csv
    rows = list(_csv.DictReader(open(latest)))
    # Только те которым нужна замена
    need_replace = [r for r in rows if r.get("status_in_sheet") in ("Отзыв размещён", "Отзыв размещен")
                    and r.get("live_status", "").startswith("❌")]

    # Группировка по исполнителю
    from collections import defaultdict
    by_contractor: dict[str, list[dict]] = defaultdict(list)
    for r in need_replace:
        by_contractor[r["contractor"]].append(r)

    if not by_contractor:
        return ('<div class="card"><h2><span><span class="icon">🔁</span>Attribution / Дозамена</span></h2>'
                f'<div class="metric"><span class="label">Дата отчёта</span><span class="value">{latest.stem.split("-", 2)[-1]}</span></div>'
                '<div class="empty good">✅ Нечего дозаменять — все Sheet «размещён» найдены в live</div></div>')

    blocks = []
    total_certain = 0
    total_maybe = 0
    for contractor, items in sorted(by_contractor.items(), key=lambda x: -len(x[1])):
        # Сортируем по дате отзыва (старые первыми = точнее снос)
        certain = [r for r in items if r.get("date_review")]
        maybe = [r for r in items if not r.get("date_review")]
        total_certain += len(certain)
        total_maybe += len(maybe)
        # Текст сообщения для исполнителя — JS clipboard
        msg_lines = [
            f"Привет! Антифрод яндекса снёс {len(items)} наших отзывов на reviews.yandex.ru/shop. ",
            "Нужна дозамена. Список:",
            "",
        ]
        for i, r in enumerate(items[:30], 1):
            author = r.get("author_in_sheet") or "—"
            cat = r.get("category") or "—"
            date = r.get("date_review") or "(без даты)"
            preview = (r.get("text") or "")[:80].replace("\n", " ")
            msg_lines.append(f"{i}. {cat} · {author} · {date} · {preview}…")
        msg_lines.append("")
        msg_lines.append("Нужны новые тексты под те же товары/категории. Срок 3 дня. Спасибо!")
        msg_text = "\n".join(msg_lines)
        msg_escaped = html.escape(msg_text).replace("\n", "&#10;")
        # Список для preview
        preview_items = "".join(
            f'<li><strong>{html.escape(r.get("category","—"))}</strong> · '
            f'{html.escape(r.get("author_in_sheet") or "—")} · '
            f'{html.escape(r.get("date_review") or "(без даты)")} · '
            f'<em>{html.escape((r.get("text","") or "")[:80])}…</em></li>'
            for r in items[:20]
        )
        more = f'<li><em>…и ещё {len(items)-20}</em></li>' if len(items) > 20 else ''
        blocks.append(f"""
<details style="margin:8px 0;padding:10px;background:#fef2f2;border:1px solid #fecaca;border-radius:6px">
<summary style="cursor:pointer;font-weight:600;color:#991b1b">
🔁 {html.escape(contractor)} — {len(items)} требует дозамены
<span class="muted">(c датой: {len(certain)} · без даты: {len(maybe)})</span>
</summary>
<button onclick="navigator.clipboard.writeText(this.dataset.msg).then(()=>this.textContent='✅ Скопировано')" data-msg="{msg_escaped}" style="margin:8px 0;padding:6px 10px;background:#dc2626;color:white;border:none;border-radius:4px;cursor:pointer;font-size:12px">📋 Копировать текст для исполнителя</button>
<ul style="margin:8px 0 0;font-size:12px;max-height:300px;overflow-y:auto">{preview_items}{more}</ul>
</details>""")

    return f'''<div class="card">
  <h2><span><span class="icon">🔁</span>Attribution / Дозамена</span><span class="pill">{len(need_replace)} итого</span></h2>
  <div class="metric"><span class="label">Точно (с датой)</span><span class="value danger">{total_certain}</span></div>
  <div class="metric"><span class="label">Под вопросом (без даты)</span><span class="value warn">{total_maybe}</span></div>
  <div class="metric"><span class="label">Источник</span><span class="value" style="font-size:11px">{html.escape(latest.name)}</span></div>
  {''.join(blocks)}
  <p style="margin:8px 0 0;font-size:11px;color:var(--muted)">
    Регенерация: <code>attribution-report.py {client}</code> · CSV для Excel: <code>{html.escape(latest.name)}</code>
  </p>
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


def render_docs_card(client: str, registry: dict) -> str:
    inv = docs_inventory(client, registry)

    def doc_row(d: dict, extra: str = "") -> str:
        bits = [f'<span class="meta">{d["size_kb"]} KB · {d["mtime"]}']
        if d.get("rows") is not None:
            bits.append(f'· {d["rows"]} строк')
        bits.append("</span>")
        meta = "".join(bits)
        return (f'<a class="research-link" href="{html.escape(d["github"])}" target="_blank">'
                f'<span class="name">{html.escape(d["name"])}</span> {meta}{extra}</a>')

    def sheet_row(s: dict) -> str:
        st = s.get("stats")
        if st:
            statuses_html = " · ".join(
                f'<span style="white-space:nowrap">{html.escape(label)} {n}</span>'
                for label, n in st["by_status"]
            )
            stats_line = (
                f'<span class="meta">📈 <b>{st["total"]}</b> строк · '
                f'plan: {s["plan"] or "—"} · {html.escape(s["owner"])}</span>'
                f'<div style="font-size:11px;color:var(--muted);margin-top:4px;line-height:1.5">{statuses_html}</div>'
            )
        else:
            stats_line = (
                f'<span class="meta">{html.escape(s["owner"])} · '
                f'plan: {s["plan"] or "—"} · {s["period"] or "—"}</span>'
            )
        return (
            f'<a class="research-link" href="{html.escape(s["url"])}" target="_blank">'
            f'<span class="name">📊 {html.escape(s["label"])}</span>{stats_line}</a>'
        )

    sheets_rows = "".join(sheet_row(s) for s in inv["sheets"]) or '<div class="empty">нет</div>'

    def batch_row(d: dict) -> str:
        compose = d.get("data") or ""
        extra = (
            f'<div style="font-size:11px;color:var(--muted);margin-top:2px">📦 {html.escape(compose)}</div>'
            if compose else ""
        )
        return doc_row(d, extra=extra)

    dated_rows = "".join(doc_row(d) for d in inv["dated_docs"]) or '<div class="empty">нет</div>'
    key_rows = "".join(doc_row(d) for d in inv["key_docs"]) or '<div class="empty">нет</div>'
    batch_rows = "".join(batch_row(d) for d in inv["batches"]) or '<div class="empty">нет</div>'

    # External services
    ext_links = [
        ("📨 qcomment dashboard", "https://artvision.pro/qcomment/", "basic auth (см. tokens.json)"),
        ("⭐ reviews.yandex.ru/shop/blumart.ru", "https://reviews.yandex.ru/shop/blumart.ru", "публичная страница"),
        ("💬 kwork (ЛК)", "https://kwork.ru/manage_orders", "Андрей Киселев"),
    ]
    ext_rows = "".join(
        f'<a class="research-link" href="{html.escape(u)}" target="_blank">'
        f'<span class="name">{html.escape(label)}</span> '
        f'<span class="meta">{html.escape(note)} →</span></a>'
        for label, u, note in ext_links
    )

    total = len(inv["sheets"]) + len(inv["key_docs"]) + len(inv["dated_docs"]) + len(inv["batches"]) + len(ext_links)

    return f'''<div class="card">
  <h2><span><span class="icon">📚</span>Документы ORM</span><span class="pill">{total}</span></h2>

  <h3 style="font-size:13px;color:var(--muted);margin:12px 0 6px;text-transform:uppercase">Google Sheets</h3>
  {sheets_rows}

  <h3 style="font-size:13px;color:var(--muted);margin:12px 0 6px;text-transform:uppercase">Свежие отчёты ({len(inv["dated_docs"])})</h3>
  {dated_rows}

  <h3 style="font-size:13px;color:var(--muted);margin:12px 0 6px;text-transform:uppercase">Партии раздачи ({len(inv["batches"])})</h3>
  {batch_rows}

  <h3 style="font-size:13px;color:var(--muted);margin:12px 0 6px;text-transform:uppercase">Базовые доки ({len(inv["key_docs"])})</h3>
  {key_rows}

  <h3 style="font-size:13px;color:var(--muted);margin:12px 0 6px;text-transform:uppercase">Внешние сервисы</h3>
  {ext_rows}
</div>'''


def _status_classify(status: str) -> tuple[str, str]:
    """Возвращает (css_class, emoji) по статусу контрагента."""
    s = (status or "").lower()
    if s == "active":
        return ("ok", "✅")
    if "fail" in s or "block" in s or "decline" in s:
        return ("crit", "❌")
    if "unused" in s or "lead_only" in s:
        return ("neutral", "⏸")
    if "cold_pitch" in s or "pending" in s:
        return ("warn", "💬")
    if "documented_not_started" in s or "discovered_not_started" in s:
        return ("warn", "🆕")
    if s == "pending_password_retest":
        return ("warn", "🔑")
    if s == "postponed_by_us":
        return ("neutral", "⏸")
    if s == "dropped_no_response":
        return ("neutral", "📭")
    if s == "priced_out_postponed":
        return ("neutral", "💰")
    if "unknown" in s:
        return ("neutral", "❓")
    return ("neutral", "•")


def _next_action_for(status: str, ctype: str) -> str:
    """Возвращает короткую рекомендацию следующего шага."""
    s = (status or "").lower()
    if s == "active":
        return "выгружать партии"
    if s == "documented_not_started":
        if ctype == "text_writers_pool":
            return "регистрация + первый заказ"
        return "регистрация / API-ключ"
    if s == "discovered_not_started":
        return "разведка → cold pitch"
    if s == "registered_but_unused":
        return "первая партия 5-10 шт"
    if s == "login_fails":
        return "сброс пароля / новый аккаунт"
    if s == "pending_password_retest":
        return "login-тест через браузер"
    if s == "postponed_by_us":
        return "ждёт нашего решения о реактивации"
    if s == "dropped_no_response":
        return "повторный pitch (тишина >2 мес)"
    if s == "priced_out_postponed":
        return "только bucket C (отклонённые)"
    if s == "cold_pitch_pending":
        return "follow-up через 3 дня"
    if s == "cold_pitch_declined":
        return "архив / альтернатива"
    if s == "lead_only":
        return "созвон / детали"
    if s == "unknown_role":
        return "уточнить роль у заказчика"
    return "—"


def render_contractors_card(registry, client: str) -> str:
    contractors = registry.get("contractors", [])
    last_contacts = last_contact_per_executor(client)

    # Группировка: active → activate (documented/discovered/registered/cold_pitch_pending) → blocked/done
    GROUP_ORDER = [
        ("✅ Активные", lambda s: s == "active"),
        ("🆕 Готовы к запуску", lambda s: s in ("documented_not_started", "discovered_not_started",
                                                 "registered_but_unused", "cold_pitch_pending", "lead_only",
                                                 "pending_password_retest", "postponed_by_us")),
        ("❌ Заблокированные / отказы", lambda s: s in ("login_fails", "cold_pitch_declined")),
        ("❓ Прочее", lambda s: s in ("unknown_role",) or True),
    ]
    grouped: dict[str, list] = {g[0]: [] for g in GROUP_ORDER}
    for c in contractors:
        s = c.get("status", "")
        for label, pred in GROUP_ORDER:
            if pred(s):
                grouped[label].append(c)
                break

    body_parts = []
    for label, items in grouped.items():
        if not items:
            continue
        rows = []
        for c in items:
            name = c.get("name", "?")
            status = c.get("status", "?")
            ctype = c.get("type", "?")
            cls, emoji = _status_classify(status)
            next_act = _next_action_for(status, ctype)
            last = None
            for ex_key, info in last_contacts.items():
                if name.lower() in ex_key.lower() or ex_key.lower() in name.lower():
                    last = info
                    break
            last_html = (
                f'<small style="color:var(--muted)">{html.escape(last["last_ts"][:16])} · '
                f'{html.escape(last["last_channel"])}</small>'
                if last
                else '<small style="color:var(--muted)">—</small>'
            )
            rows.append(
                f'<tr>'
                f'<td>{emoji} <strong>{html.escape(name)}</strong><br>{last_html}</td>'
                f'<td><span class="tag {cls}">{html.escape(status)}</span><br>'
                f'<small style="color:var(--muted)">{html.escape(ctype)}</small></td>'
                f'<td><small>{html.escape(next_act)}</small></td>'
                f'</tr>'
            )
        body_parts.append(
            f'<tr><td colspan="3" style="background:#f8f9fa;font-weight:600;padding:8px 12px;'
            f'color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.5px">'
            f'{label} <span style="color:#999;font-weight:400">· {len(items)}</span></td></tr>'
        )
        body_parts.extend(rows)

    active_count = sum(1 for c in contractors if c.get("status") == "active")
    activate_count = sum(1 for c in contractors if c.get("status") in
                         ("documented_not_started", "discovered_not_started",
                          "registered_but_unused", "cold_pitch_pending", "lead_only",
                          "pending_password_retest", "postponed_by_us"))

    return f'''<div class="card">
  <h2><span><span class="icon">🤝</span>Подрядчики — статус общения</span>
      <span class="pill">{active_count}/{len(contractors)} active · {activate_count} готовы к запуску</span></h2>
  <p style="font-size:11px;color:var(--muted);margin:4px 0 8px">
    «Готовы к запуску» = зарегистрированы или прошёл cold pitch, нужно 1-2 действия (login-тест / API-key / пополнение баланса) для активации.
  </p>
  <table class="compact">
    <thead><tr><th style="width:42%">Кто / последний контакт</th><th style="width:28%">Статус / тип</th><th>Next action</th></tr></thead>
    <tbody>{"".join(body_parts)}</tbody>
  </table>
  <p style="font-size:11px;color:var(--muted);margin-top:8px">
    Source: <code>registry.yaml</code> + <code>executor-ledger.csv</code>. Группы: active · к активации (documented/discovered/registered/cold-pending) · заблокированные · прочее
  </p>
</div>'''
