#!/usr/bin/env python3
"""
dashboard-vs-pitch-classify.py — классифицирует HTML клиента как CABINET / PITCH / HYBRID

Прецедент 2026-05-20 (MIRBIR SCOPE-DRIFT):
Goal-файл говорил «CRM для торговой ниши» = CABINET (operational dashboard).
Claude 7 дней правил director-cabinet.html — это PITCH (slide-deck 17 слайдов с CTA «Обсудить»).
Этот скрипт автоматически отличает дашборд от презентации, чтобы не повторить.

Сигнатуры:
  PITCH (presentation/pitch-deck):
    - <div class="slide">, <div class="slide-num">, <div class="slide-footer">
    - "01 / 17", slide numbering pattern
    - CTA: "Обсудить стратегию", "Получить план", "Связаться"
    - Mentions "Наша работа", "Чеклист действий", "Что мы сделаем"
    - Artvision-product mentions (LinkForge/Scout/Radar/Flow) >3
    - Self-promotional: "наша компания", "мы предлагаем", "наш кейс"

  CABINET (operational dashboard):
    - <aside class="sidebar"> + <main class="content">
    - .topbar + .period-tabs (Сегодня/7д/90д)
    - KPI grid, sparklines, alerts
    - Operational sigs: "stock turn", "sell-through", "LFL", "AOV", "GMROI"
    - filter/view-switch UI
    - data-fresh markers (live URL, last-updated)

  HYBRID — смесь, неоднозначный

Usage:
  dashboard-vs-pitch-classify.py <file.html>
  dashboard-vs-pitch-classify.py --url https://artvision.pro/mirbir-simple/
  dashboard-vs-pitch-classify.py <file> --json
  dashboard-vs-pitch-classify.py <file> --expect cabinet  # fails if это pitch
"""
import re
import sys
import argparse
import urllib.request
import json
from pathlib import Path

PITCH_SIGNATURES = {
    'slide_num_pattern': (r'\d{1,2}\s*[/из]\s*\d{1,2}', 3),
    'slide_div': (r'class="slide(?!\-num|\-footer|\-header|\-body)[\s"]', 5),
    'slide_footer': (r'class="slide-footer"', 3),
    'slide_num_class': (r'class="slide-num"', 3),
    'cta_phrases': (r'(?:Обсудить (?:стратегию|план)|Получить (?:план|КП|консультацию)|Записаться на|Связаться с нами)', 4),
    'our_work_section': (r'Наша работа|Что мы сделаем|Чеклист действий', 4),
    'agency_products': (r'Artvision\s+(?:LinkForge|Scout|Radar|Flow|Lens|Insight|Content Lab)', 1),
    'pitch_phrasing': (r'мы предлагаем|наш кейс|наша компания|свяжитесь с нами', 3),
}

CABINET_SIGNATURES = {
    'sidebar_nav': (r'<aside[^>]+class="[^"]*sidebar', 5),
    'topbar': (r'class="topbar"', 4),
    'period_tabs': (r'period-tabs', 3),
    'view_switch': (r'view-switch', 2),
    'kpi_grid': (r'kpi-grid|kpi-card', 3),
    'data_chapter': (r'data-chapter=', 2),
    'operational_kpi': (r'(?:stock\s*turn|sell.through|GMROI|LFL\s*Sales|AOV|repeat\s*rate|sales per FTE)', 3),
    'live_data_marker': (r'обновлено|Я\.Метрика|last.updated|updated', 2),
    'sparkline_alerts': (r'sparkline|алерт|🔔|alert', 2),
}


def load(target: str) -> str:
    if target.startswith('http'):
        req = urllib.request.Request(target, headers={'User-Agent': 'dashboard-classify/1.0'})
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.read().decode('utf-8', errors='ignore')
    return Path(target).expanduser().resolve().read_text(encoding='utf-8', errors='ignore')


def score(html: str, sigs: dict) -> tuple:
    """Return (total_score, hits_dict)."""
    hits = {}
    total = 0
    for name, (pattern, weight) in sigs.items():
        n = len(re.findall(pattern, html, re.IGNORECASE))
        if n > 0:
            hits[name] = {'matches': n, 'weight': weight, 'score': n * weight}
            total += n * weight
    return total, hits


def classify(html: str) -> dict:
    pitch_score, pitch_hits = score(html, PITCH_SIGNATURES)
    cab_score, cab_hits = score(html, CABINET_SIGNATURES)
    if pitch_score >= 10 and cab_score < pitch_score * 0.4:
        verdict = 'PITCH'
    elif cab_score >= 10 and pitch_score < cab_score * 0.4:
        verdict = 'CABINET'
    elif pitch_score < 5 and cab_score < 5:
        verdict = 'UNKNOWN'
    else:
        verdict = 'HYBRID'
    return {
        'verdict': verdict,
        'pitch_score': pitch_score,
        'cabinet_score': cab_score,
        'pitch_hits': pitch_hits,
        'cabinet_hits': cab_hits,
    }


def main():
    ap = argparse.ArgumentParser(description='Cabinet vs Pitch detector')
    ap.add_argument('target', nargs='?')
    ap.add_argument('--url', help='URL для проверки live')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--expect', choices=['cabinet', 'pitch', 'hybrid'], help='Expected type, fails если другой')
    args = ap.parse_args()

    target = args.url or args.target
    if not target:
        ap.error('Укажите файл или --url')

    html = load(target)
    result = classify(html)

    if args.json:
        print(json.dumps({'target': target, **result}, ensure_ascii=False, indent=2))
    else:
        print(f'═══ {target} ═══')
        print(f'Verdict: **{result["verdict"]}**')
        print(f'  Pitch score: {result["pitch_score"]}')
        print(f'  Cabinet score: {result["cabinet_score"]}')
        print('\nPitch signatures:')
        for k, v in result['pitch_hits'].items():
            print(f'  {k}: {v["matches"]}× (вес {v["weight"]}) = {v["score"]}')
        print('\nCabinet signatures:')
        for k, v in result['cabinet_hits'].items():
            print(f'  {k}: {v["matches"]}× (вес {v["weight"]}) = {v["score"]}')

    if args.expect:
        if result['verdict'].lower() != args.expect:
            print(f'\n❌ ОЖИДАЛИ {args.expect.upper()}, ПОЛУЧИЛИ {result["verdict"]}', file=sys.stderr)
            return 2
        print(f'\n✅ {result["verdict"]} — соответствует expected')
    return 0


if __name__ == '__main__':
    sys.exit(main())
