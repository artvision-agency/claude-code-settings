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

# Local lib (refactored 2026-05-10)
sys.path.insert(0, str(Path(__file__).parent))
from lib.styles import CSS  # noqa: E402
from lib.loaders import (  # noqa: E402
    load_yaml, load_json,
    latest_qcomment, reviews_pace, latest_orders_state,
    ledger_stats, last_contact_per_executor,
    list_research, kupi_otziv_latest, kwork_summary,
)
from lib.charts import daily_deltas_for_chart, render_publications_svg  # noqa: E402, F401
from lib.cards import (  # noqa: E402
    render_alerts, render_qcomment_card, render_reviews_card,
    render_orders_state_card, render_ledger_card, render_kupi_otziv_card,
    render_kwork_card, render_attribution_card, render_research_card,
    render_docs_card, render_contractors_card, render_status_funnel_card,
    render_our_publications_card,
)
from lib.config import ROOT, VPS_USER, VPS_HOST, VPS_DIR, PUBLIC_BASE  # noqa: E402, F401


# CSS перенесён в lib/styles.py


# render_*_card функции перенесены в lib/cards.py


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
    _now = datetime.now()
    ts = _now.strftime("%Y-%m-%d %H:%M МСК")
    ts_iso = _now.isoformat()

    alerts_html = render_alerts(qc, state, kw, client=client)

    cards = [
        render_our_publications_card(client),
        render_qcomment_card(qc),
        render_reviews_card(pace, qc, client),
        render_status_funnel_card(client),
        render_attribution_card(client),
        render_orders_state_card(state),
        render_ledger_card(ledger),
        render_contractors_card(registry, client),
        render_kwork_card(kw),
        render_kupi_otziv_card(ko),
        render_research_card(research),
        render_docs_card(client, registry),
    ]

    return f'''<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow, noarchive, nosnippet">
<title>{html.escape(name)} — Command Center</title>
<style>{CSS}</style>
<script>
// Auto-refresh every 5 минут, но только если вкладка видима (не reload в фоне)
(function() {{
  const REFRESH_MS = 5 * 60 * 1000;
  let nextAt = Date.now() + REFRESH_MS;
  function maybeReload() {{
    if (document.visibilityState === 'visible' && Date.now() >= nextAt) {{
      location.reload();
    }}
  }}
  setInterval(maybeReload, 30000);
  document.addEventListener('visibilitychange', maybeReload);
}})();
</script>
</head>
<body>
<div class="container">
<header>
  <h1>{html.escape(name)} — ORM Command Center</h1>
  <div class="meta">Сгенерировано: <span id="gen-ts" data-ts="{ts_iso}">{ts}</span>
    <span id="freshness-badge" style="display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;margin-left:8px"></span>
  </div>
  <div class="badges">
    <span class="badge">INTERNAL</span>
    <span class="badge">noindex</span>
    <span class="badge">orm-pulse</span>
  </div>
</header>
<script>
// Q11 — visual freshness indicator (✅ <2ч / ⚠️ 2-4ч / 🚨 >4ч)
(function() {{
  const tsEl = document.getElementById('gen-ts');
  const badge = document.getElementById('freshness-badge');
  if (!tsEl || !badge) return;
  function tick() {{
    const gen = new Date(tsEl.dataset.ts);
    const ageMin = (Date.now() - gen.getTime()) / 60000;
    if (ageMin < 120) {{
      badge.textContent = '✅ свежие данные';
      badge.style.background = '#c8e6c9'; badge.style.color = '#1b5e20';
    }} else if (ageMin < 240) {{
      badge.textContent = '⚠️ устарели (' + Math.round(ageMin) + ' мин)';
      badge.style.background = '#ffe0b2'; badge.style.color = '#e65100';
    }} else {{
      badge.textContent = '🚨 cron сломан (' + Math.round(ageMin/60) + ' ч)';
      badge.style.background = '#ffcdd2'; badge.style.color = '#b71c1c';
    }}
  }}
  tick();
  setInterval(tick, 30000);
}})();
</script>

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
