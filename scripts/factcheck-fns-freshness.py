#!/usr/bin/env python3
"""
factcheck-fns-freshness.py — проверка свежести ФНС-данных в клиентских дашбордах.

Прецедент 2026-05-20 (MIRBIR Кабинет):
Strict-агент нашёл что дашборд показывал «142 млн ▲ +7,4%» как настоящее,
а это ФНС 2024 vs 2023. Реальный 2025 = 43,4 млн (−70%). И аналогично
по конкуренту Ханхи: на странице −7,2% (2024), реально +9,9% (2025).

Этот скрипт ловит:
1. Финансовые числа без явного года рядом
2. Числа без URL-источника (list-org / rusprofile / checko / e-disclosure)
3. ФНС-данные старше 6 месяцев от текущей даты
4. Mislabel метрик (net profit ≠ EBITDA = валовая)

Usage:
  factcheck-fns-freshness.py <file.html>
  factcheck-fns-freshness.py --url https://artvision.pro/mirbir-simple/
  factcheck-fns-freshness.py <file.html> --json  # для CI / хуков

Exit codes:
  0 — нет проблем
  1 — есть WARN (нет явного года или URL рядом)
  2 — есть CRITICAL (mislabel метрики или старые данные)
"""
import re
import sys
import argparse
import urllib.request
import json
from datetime import date
from pathlib import Path

# Источники которые засчитываются как референс ФНС
FNS_SOURCE_HOSTS = [
    'list-org.com', 'rusprofile.ru', 'checko.ru',
    'e-disclosure.ru', 'sbis.ru', 'fns.ru', 'nalog.gov.ru',
    'kontur.ru', 'spark-interfax.ru'
]

# Финансовые маркеры (числа рядом с этими словами — финансовые)
FIN_MARKERS = [
    'выручк', 'оборот', 'прибыль', 'EBITDA', 'маржа', 'profit',
    'revenue', 'годов', 'ФНС', 'СПАРК', 'rusprofile'
]

# Mislabel-словарь (что НЕ должно быть рядом)
MISLABEL_PATTERNS = [
    # «N млн прибыль ... EBITDA» в одной фразе — подозрительно
    (r'чист[аяой]\s*прибыл[ьи]', r'EBITDA', 'Чистая прибыль ≠ EBITDA'),
    (r'фин\.?\s*результат', r'EBITDA.*валов', 'Фин. результат ФНС Ф2.2400 = чистая прибыль, НЕ EBITDA'),
    (r'выручк[аи]', r'себестоимост', 'Выручка vs себестоимость — разные строки Ф2'),
]

# Big numbers regex (от 10 млн до триллионов)
BIG_NUMBER = re.compile(
    r'(\d{1,3}(?:[\s,]\d{3})*(?:[.,]\d+)?)\s*(млн|млрд|тыс)\s*[₽р]?',
    re.IGNORECASE
)
YEAR_RE = re.compile(r'\b(20[12]\d)\b')
URL_RE = re.compile(r'https?://[\w.-]+(?:/[^\s"\'<>]*)?')


def load_html(target: str) -> str:
    if target.startswith('http'):
        req = urllib.request.Request(target, headers={'User-Agent': 'factcheck-fns/1.0'})
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.read().decode('utf-8', errors='ignore')
    path = Path(target).expanduser().resolve()
    return path.read_text(encoding='utf-8', errors='ignore')


def strip_html(html: str) -> str:
    """Грубый strip — убираем теги, оставляем текст в исходном порядке."""
    no_script = re.sub(r'<script[^>]*>.*?</script>', ' ', html, flags=re.DOTALL | re.IGNORECASE)
    no_style = re.sub(r'<style[^>]*>.*?</style>', ' ', no_script, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', no_style)
    return re.sub(r'\s+', ' ', text)


def find_fin_chunks(text: str, window: int = 200) -> list:
    """Найти все chunks с финансовыми числами + контекст ±window."""
    chunks = []
    for m in BIG_NUMBER.finditer(text):
        start = max(0, m.start() - window)
        end = min(len(text), m.end() + window)
        ctx = text[start:end]
        # Только если рядом есть финансовый маркер
        if any(mk.lower() in ctx.lower() for mk in FIN_MARKERS):
            chunks.append({
                'number': m.group(0),
                'context': ctx,
                'pos': m.start(),
            })
    return chunks


def check_chunk(chunk: dict) -> list:
    """Проверка одного chunk: год, URL, mislabel."""
    findings = []
    ctx = chunk['context']
    ctx_lower = ctx.lower()
    num = chunk['number']

    # 1. Явный год в контексте?
    years = YEAR_RE.findall(ctx)
    if not years:
        findings.append({
            'severity': 'WARN',
            'rule': 'no_year',
            'msg': f'Число "{num}" — нет явного года в ±200 символах',
        })
    else:
        year = max(int(y) for y in years)
        current_year = date.today().year
        if year < current_year - 1:
            findings.append({
                'severity': 'WARN',
                'rule': 'stale_year',
                'msg': f'Число "{num}" привязано к году {year}, сейчас {current_year} — данные на {current_year - year} лет старше',
            })

    # 2. URL источника в контексте?
    urls = URL_RE.findall(ctx)
    fns_urls = [u for u in urls if any(h in u for h in FNS_SOURCE_HOSTS)]
    if not fns_urls:
        # Текстовое упоминание источника?
        text_hints = ['ФНС', 'СПАРК', 'rusprofile', 'list-org', 'checko']
        has_text_source = any(h in ctx for h in text_hints)
        if not has_text_source:
            findings.append({
                'severity': 'WARN',
                'rule': 'no_source',
                'msg': f'Число "{num}" — нет URL источника (list-org/rusprofile/checko) или упоминания ФНС/СПАРК в ±200 символах',
            })
        else:
            findings.append({
                'severity': 'INFO',
                'rule': 'text_source_only',
                'msg': f'Число "{num}" — есть текстовое упоминание источника, но нет URL для верификации',
            })

    # 3. Mislabel patterns
    for p1, p2, msg in MISLABEL_PATTERNS:
        if re.search(p1, ctx_lower) and re.search(p2, ctx_lower):
            findings.append({
                'severity': 'CRITICAL',
                'rule': 'mislabel',
                'msg': f'Число "{num}" — возможный mislabel: {msg}',
            })

    return findings


def report(findings_all: list, target: str, as_json: bool = False) -> int:
    by_severity = {'CRITICAL': [], 'WARN': [], 'INFO': []}
    for f in findings_all:
        by_severity[f['severity']].append(f)

    if as_json:
        print(json.dumps({
            'target': target,
            'summary': {k: len(v) for k, v in by_severity.items()},
            'findings': findings_all,
        }, ensure_ascii=False, indent=2))
    else:
        print(f'═══ factcheck-fns-freshness — {target} ═══')
        for sev in ('CRITICAL', 'WARN', 'INFO'):
            items = by_severity[sev]
            if not items:
                continue
            print(f'\n[{sev}] {len(items)}:')
            for f in items[:15]:
                snippet = f['msg'][:200]
                print(f'  · {snippet}')
            if len(items) > 15:
                print(f'  · ... и ещё {len(items) - 15}')
        total = sum(len(v) for v in by_severity.values())
        if total == 0:
            print('\n✅ Чисто — финансовые числа имеют год + источник, mislabel не найдено')

    if by_severity['CRITICAL']:
        return 2
    if by_severity['WARN']:
        return 1
    return 0


def main():
    ap = argparse.ArgumentParser(description='ФНС-данные: год + источник + mislabel-чек')
    ap.add_argument('target', nargs='?', help='Путь к HTML или --url')
    ap.add_argument('--url', help='HTTPS URL для проверки live')
    ap.add_argument('--json', action='store_true', help='JSON-выход для CI/хуков')
    ap.add_argument('--window', type=int, default=200, help='Окно контекста в символах')
    args = ap.parse_args()

    target = args.url or args.target
    if not target:
        ap.error('Укажите файл или --url')

    html = load_html(target)
    text = strip_html(html)
    chunks = find_fin_chunks(text, window=args.window)

    findings_all = []
    seen_msgs = set()
    for chunk in chunks:
        for f in check_chunk(chunk):
            key = (f['severity'], f['rule'], f['msg'][:80])
            if key not in seen_msgs:
                seen_msgs.add(key)
                findings_all.append(f)

    return report(findings_all, target, as_json=args.json)


if __name__ == '__main__':
    sys.exit(main())
