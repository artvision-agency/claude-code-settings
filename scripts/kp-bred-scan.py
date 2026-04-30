#!/usr/bin/env python3
"""KP-bred-scan v2: нарушения в КП. Различает наши тарифы (от Xк/мес) и выручку клиента."""
import sys, re
from pathlib import Path

PATTERNS = {
    # === CRITICAL ===
    
    # 1. ВЫРУЧКА КЛИЕНТА в рублях (НЕ наши тарифы!)
    'CRITICAL_FIN_revenue_table': (
        r'(Выручка\s*/\s*мес|выручка/мес|ΔВыручк|выручк[аи][^.]{0,40}клиент|прогноз[^.]{0,15}выручк|маржинальн[^.]{0,15}\d{1,3}\s*%|\bbreak.?even\b|точк[аи].{0,5}окупаем|ROI\s+\d+[.,]?\d*\s*[xх×]|ROI\s*[+\-]\d+\s*%|маржа\s*[=:].{0,15}\d{1,3}\s*%|чистая\s+прибыль)',
        'Выручка/прибыль/ROI клиента в КП'
    ),
    'CRITICAL_FIN_delta_rub': (
        r'\+\d{2,3}\s*\d{3}\s*₽|\+\d{1,3}\s*тыс\.?\s*₽|\+\d{1,3}\s*млн\.?\s*₽',
        'ΔВыручка в плюс-рублях (прогноз клиента)'
    ),
    
    # 2. Внутренние маркеры
    'CRITICAL_INTERNAL_markers': (
        r'\bUNCONFIRMED\b|\bCONFIRMED\b|\bWRONG\b|\bWebFetch\b|Topvisor\s+API|Wordstat\s+API|view-source|`?curl\s+-',
        'Internal-маркеры (UNCONFIRMED/CONFIRMED/WebFetch/curl)'
    ),
    
    # 3. AI/Claude в публичных
    'CRITICAL_AI_claude': (
        r'\b(Claude|GPT-\d|нейросет[а-я]+\s+пиш|нейросет[а-я]+\s+генер|AI-генер[а-я]+|искусственн[а-я]+\s+интеллект\s+пиш)',
        'Claude/GPT/нейросеть как ИНСТРУМЕНТ (запрет)'
    ),
    
    # === WARN ===
    
    # 4. Бренды Artvision (запрещено только для AdvertMed-материалов)
    'WARN_artvision_products': (
        r'Artvision\s+(Flow|Watch|Radar|Scout|LinkForge|Insight|Leads|Content\s+Lab|Pulse|VoxRate|Lens|Funnel)\b',
        'Бренды Artvision Flow/Watch/Radar/etc'
    ),
    'WARN_artvision_pro': (
        r'\bartvision\.pro\b',
        'Упоминание artvision.pro'
    ),
    
    # 5. Клише
    'WARN_cliches': (
        r'(гарант[а-я]+\s+результат|качественн[а-я]+\s+услуг|индивидуальн[а-я]+\s+подход|команда\s+профессионал|лидер\s+рынка|более\s+\d+\s+лет\s+на\s+рынке)',
        'Маркетинговые клише'
    ),
    
    # 6. Специфические шаблонные leftover
    'WARN_template_leftover': (
        r'(6\s+филиал|Цветной\s+бульвар|Самотечная|ЛОР-нишу|открытый\s+МРТ\s+330|Староалексеевская|Лор-Альянс|loralliance)',
        'Шаблонные leftover от других клиентов'
    ),
}

# Ключевые слова которые ЛЕГИТИМНО соседствуют с большими суммами рублей
TARIFF_CONTEXT = re.compile(r'(тариф|пакет|стоимост|от\s+\d{1,3}\s*\d{3})', re.I)

def strip_html(html):
    s = re.sub(r'data:image/[^"\'\s]{200,}', '', html)
    s = re.sub(r'<script.*?</script>', ' ', s, flags=re.S|re.I)
    s = re.sub(r'<style.*?</style>', ' ', s, flags=re.S|re.I)
    s = re.sub(r'<!--.*?-->', ' ', s, flags=re.S)
    s = re.sub(r'<[^>]+>', ' ', s)
    s = re.sub(r'\s+', ' ', s)
    return s

def scan(path):
    try:
        html = open(path, encoding='utf-8', errors='ignore').read()
    except FileNotFoundError:
        return -1, [f"FILE NOT FOUND"]
    text = strip_html(html)
    findings = []
    for code, (pat, desc) in PATTERNS.items():
        hits = re.findall(pat, text, re.I)
        if hits:
            samples = list(set(str(h) if not isinstance(h,tuple) else ' '.join(h) for h in hits[:5]))[:3]
            sev = 'CRITICAL' if 'CRITICAL' in code else 'WARN'
            findings.append((sev, code, desc, len(hits), samples))
    return findings

def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    quiet = '--quiet' in sys.argv
    
    grand_crit = 0
    grand_warn = 0
    summary = []
    
    for f in args:
        finds = scan(f)
        if finds == -1: continue
        rel = str(Path(f).relative_to(Path.home())) if str(f).startswith(str(Path.home())) else f
        crit = sum(1 for x in finds if x[0]=='CRITICAL')
        warn = sum(1 for x in finds if x[0]=='WARN')
        if finds:
            print(f"\n{rel} — {crit}C/{warn}W")
            for sev, code, desc, n, samples in finds:
                print(f"  [{sev}] {desc} ({n}) → {samples}")
            grand_crit += crit
            grand_warn += warn
            summary.append((rel, crit, warn))
        elif not quiet:
            print(f"{rel}: ✅ clean")
    
    print(f"\n{'='*60}")
    print(f"TOTAL: {grand_crit}C / {grand_warn}W across {len(args)} files")
    if summary:
        print(f"\nSorted by CRITICAL count:")
        for rel, c, w in sorted(summary, key=lambda x: (-x[1], -x[2])):
            print(f"  {c}C/{w}W  {rel}")
    sys.exit(1 if grand_crit > 0 else 0)

if __name__ == '__main__':
    main()
