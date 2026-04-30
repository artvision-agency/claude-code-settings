#!/usr/bin/env python3
"""KP-auto-fix: автоматические замены шаблонных проблем в КП."""
import sys, re
from pathlib import Path

# Замены: (regex, replacement, description)
FIXES = [
    # 1. UNCONFIRMED/CONFIRMED маркеры → нейтральные / удаление
    (r'\bUNCONFIRMED\b\s*[—–\-:]?\s*', 'требует уточнения после доступов: ', 'UNCONFIRMED → "требует уточнения"'),
    (r'\bCONFIRMED\s+\d{1,2}\.\d{2}[,.]?\s*', '', 'CONFIRMED-маркер с датой → удалить'),
    (r'\bCONFIRMED\b\s*[—–\-:]?\s*', '', 'CONFIRMED → удалить'),
    (r'\bWRONG\b', 'опровергнуто', 'WRONG → "опровергнуто"'),
    
    # 2. Технические маркеры
    (r'\bWebFetch\b', 'веб-проверка', 'WebFetch → "веб-проверка"'),
    (r'Topvisor\s+API', 'мониторинг позиций', 'Topvisor API → "мониторинг позиций"'),
    (r'Wordstat\s+API', 'данные Wordstat', 'Wordstat API → "данные Wordstat"'),
    (r'через\s+(curl|`curl)\s+[^.,)]{1,80}', '', 'curl упоминания → удалить'),
    (r'view-source\s+(главной|сайта)', 'разметка $1', 'view-source → "разметка"'),
    (r'\bview-source\b', 'разметка страницы', 'view-source → "разметка страницы"'),
    
    # 3. AI/Claude как инструмент
    (r'через\s+Groq/OpenRouter[^.,)]{0,40}', 'через независимый AI-аудит', 'Groq/OpenRouter → нейтрально'),
    (r'\b(Claude|GPT-\d)[^.,)]{0,30}', 'AI-аудит', 'Claude/GPT → AI-аудит'),
    (r'нейросет[а-я]+\s+(пиш|генер|создаёт)[^.,)]{0,40}', 'автоматическая генерация', 'нейросеть пишет → автогенерация'),
    
    # 4. artvision.pro в видимом тексте
    (r'\s*Совместно\s+с\s+командой\s+artvision\.pro\.?', '', 'artvision.pro упоминание'),
    (r'\s*совместно\s+с\s+командой\s+artvision\.pro', '', 'artvision.pro lower'),
    (r'\bartvision\.pro\b', 'технологический партнёр', 'artvision.pro → технологический партнёр'),
    
    # 5. Бренды Artvision продуктов
    (r'\bArtvision\s+Flow\b', 'SEO-мониторинг', 'Artvision Flow'),
    (r'\bArtvision\s+Watch\b', 'мониторинг репутации', 'Artvision Watch'),
    (r'\bArtvision\s+Radar\b', 'GEO-видимость', 'Artvision Radar'),
    (r'\bArtvision\s+Scout\b', 'конкурентный анализ', 'Artvision Scout'),
    (r'\bArtvision\s+LinkForge\b', 'линкбилдинг', 'Artvision LinkForge'),
    (r'\bArtvision\s+Content\s+Lab\b', 'контент-производство', 'Artvision Content Lab'),
    (r'\bArtvision\s+Insight\b', 'аналитика переговоров', 'Artvision Insight'),
    (r'\bArtvision\s+Leads\b', 'лидогенерация', 'Artvision Leads'),
    (r'\bArtvision\s+Pulse\b', 'мониторинг изменений', 'Artvision Pulse'),
    (r'\bArtvision\s+VoxRate\b', 'сбор отзывов', 'Artvision VoxRate'),
    (r'\bArtvision\s+Lens\b', 'A/B-тестирование', 'Artvision Lens'),
    (r'\bArtvision\s+Funnel\b', 'воронка лидов', 'Artvision Funnel'),
]

def fix_file(path, dry_run=False):
    try:
        text = open(path, encoding='utf-8').read()
    except:
        return None, 0
    original = text
    changes = []
    for pat, repl, desc in FIXES:
        new_text, n = re.subn(pat, repl, text, flags=re.I)
        if n > 0:
            changes.append(f"  {desc}: {n} замен")
            text = new_text
    if text != original and not dry_run:
        # Backup
        bak = path + '.bak.before-autofix'
        with open(bak, 'w') as fb: fb.write(original)
        with open(path, 'w') as f: f.write(text)
    return changes, len(changes)

def main():
    dry = '--dry-run' in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    total_changed = 0
    for f in args:
        changes, n = fix_file(f, dry_run=dry)
        if n > 0:
            print(f"\n{Path(f).name} ({n} типов изменений{', DRY' if dry else ''}):")
            for c in changes: print(c)
            total_changed += 1
    print(f"\n=== {total_changed}/{len(args)} files modified ===")

if __name__ == '__main__':
    main()

# === EXTRA FIXES (run as separate pass) ===
EXTRA_FIXES = [
    # Замена break-even в текстовых местах (не в таблицах с цифрами)
    (r'\bbreak.?even\s+через?\s+\d+[-–]?\d*\s*мес[а-я]*', 'срок выхода на ROI обсуждаем после доступов', 'break-even Х мес → нейтрально'),
    (r'\bBreak.?even\b\s*[—:\-]?\s*\d+[-–]?\d*\s*мес[а-я]*', 'срок выхода на ROI — после доступов', 'Break-even Х мес'),
    (r'\bBreak.?even\b(?!\s*\d)', 'срок выхода на ROI', 'Break-even (одиночное)'),
    (r'\bточк[аи]\s+окупаем\w+', 'срок выхода на ROI', 'точка окупаемости'),
    (r'\bТочк[аи]\s+окупаем\w+', 'Срок выхода на ROI', 'Точка окупаемости (cap)'),
    
    # ΔВыручка / +XXX 000 ₽ — пометить как «прирост заявок» (когда контекстуально безопасно)
    (r'ΔВыручк[ауи][а-я]*\s*[+\-]?\s*\d{1,3}\s*\d{3}\s*₽\s*/?\s*мес', 'прирост заявок (расчёт после данных)', 'ΔВыручка ±XXX ₽/мес'),
    (r'ΔВыручк[ауи][а-я]*', 'прирост заявок', 'ΔВыручка'),
    
    # Маржинальность 35% etc
    (r'маржинальн\w+\s*[—:]?\s*\d+\s*%', 'маржа — обсуждаем с клиентом', 'маржинальность Х%'),
    (r'Маржинальн\w+\s*[—:]?\s*\d+\s*%', 'Маржа — обсуждаем с клиентом', 'Маржинальность Х%'),
    
    # Чистая прибыль (только в видимом тексте, не в финреквизитах footer)
    (r'чистая\s+прибыль\s*[—:=]?\s*[+\-]?\s*\d+', 'дополнительный поток (расчёт после данных)', 'чистая прибыль ±X'),
    (r'Чистая\s+прибыль\s*[—:=]?\s*[+\-]?\s*\d+', 'Дополнительный поток (расчёт после данных)', 'Чистая прибыль ±X'),
    
    # Шаблонные leftover УГН в starclinic
    (r'\b6\s+филиал(ов|а|ам)?\b', '3 филиала', '6 филиалов → 3'),
    (r'\b5\s+филиал(ов|а|ам)?\s+(в\s+)?Москв[еы]', '3 филиала в Казани', '5 филиалов Москвы'),
    (r'Цветной\s+бульвар', 'К. Маркса 46 (флагман)', 'Цветной бульвар'),
    (r'Самотечная,?\s*5', 'К. Маркса, 46', 'Самотечная 5'),
    (r'Орехово-Зуево', 'Калининская 38', 'Орехово-Зуево'),
    (r'Преображенская\s+площадь', 'Чистопольская 38', 'Преображенская'),
    (r'Бульвар\s+Дмитрия\s+Донского', 'Чистопольская', 'БДД'),
    (r'Мичуринский\s+проспект', 'Калининская', 'Мичуринский'),
    
    # Гарантия результата (запрет)
    (r'гарант\w+\s+результат\w+', 'обсуждаем KPI на встрече', 'гарантия результата'),
    (r'Гарант\w+\s+результат\w+', 'Обсуждаем KPI на встрече', 'Гарантия результата'),
]

if '--extra' in sys.argv:
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    total = 0
    for f in args:
        try:
            text = open(f, encoding='utf-8').read()
        except:
            continue
        original = text
        changes = []
        for pat, repl, desc in EXTRA_FIXES:
            new_text, n = re.subn(pat, repl, text, flags=re.I)
            if n > 0:
                changes.append(f"  {desc}: {n}")
                text = new_text
        if text != original:
            bak = f + '.bak.before-extra'
            with open(bak, 'w') as fb: fb.write(original)
            with open(f, 'w') as fo: fo.write(text)
            print(f"\n{Path(f).name}:")
            for c in changes: print(c)
            total += 1
    print(f"\n=== {total}/{len(args)} files modified by EXTRA pass ===")

# === STRICT FIXES (полный запрет калькуляций выручки клиента) ===
STRICT_FIXES = [
    # Удаление delta-block «+514 500 ₽ / мес»
    (r'<div class="delta"[^>]*>\+[\d\s]+\s*₽[^<]*</div>\s*<div class="delta-label"[^>]*>[^<]*</div>', '', 'delta-block с ₽ удалён'),
    # Удаление строк «прирост заявок к мес 12 +XXX ₽»
    (r'<div class="metric"><span>прирост\s+заявок[^<]*</span><span[^>]*>\+[\d\s]+\s*₽[^<]*</span></div>', '', 'metric «прирост заявок +XXX₽»'),
    (r'<div class="metric"><span>ΔВыручка[^<]*</span><span[^>]*>\+[\d\s]+\s*₽[^<]*</span></div>', '', 'metric ΔВыручка +XXX₽'),
    # ROI 1.5× / 2× / 1.4×
    (r'ROI\s+\d[.,]?\d?[xх×][^.,)<]{0,30}', 'результат — обсуждаем после доступов', 'ROI 1.5×'),
    # «срок выхода на ROI X мес» (после первого прохода всё ещё может быть)
    (r'срок\s+выхода\s+на\s+ROI[^<]{0,15}\d+[-–]?\d*\s*мес[а-я]*', 'результат — после доступов', 'срок выхода на ROI Х мес'),
    # «С учётом LTV ... ×N»
    (r'С\s+учётом\s+LTV[^.<]{0,80}[×xх]\s*[\d.,\-]+', 'LTV учитываем при подведении итогов', 'LTV ×N'),
    # «средний чек 3 500 ₽» / «средний чек X тыс ₽»
    (r'средний\s+чек\s+\d{1,3}\s*\d{3}\s*₽', 'средний чек уточняем у клиента', 'средний чек в рублях'),
    (r'средний\s+чек\s+\d{1,3}\s*тыс\.?\s*₽', 'средний чек уточняем у клиента', 'средний чек в тыс'),
    # «Выручка/мес» столбец в th — заменить на «Заявки» (если уже посчитанные)
    (r'<th[^>]*>Выручка/мес</th>', '<th class="c">Качественных заявок</th>', 'th Выручка/мес'),
    (r'<th[^>]*>выручка/мес</th>', '<th class="c">Качественных заявок</th>', 'th выручка/мес'),
    # Прибыль клиента в text-блоках
    (r'(дополнительный\s+поток[^.<]{0,50})\(расчёт\s+после\s+данных\)', r'\1', 'cleanup от auto-fix предыдущего'),
]

if '--strict' in sys.argv:
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    total = 0
    for f in args:
        try:
            text = open(f, encoding='utf-8').read()
        except:
            continue
        original = text
        changes = []
        for pat, repl, desc in STRICT_FIXES:
            new_text, n = re.subn(pat, repl, text, flags=re.I)
            if n > 0:
                changes.append(f"  {desc}: {n}")
                text = new_text
        if text != original:
            bak = f + '.bak.before-strict'
            with open(bak, 'w') as fb: fb.write(original)
            with open(f, 'w') as fo: fo.write(text)
            print(f"\n{Path(f).name}:")
            for c in changes: print(c)
            total += 1
    print(f"\n=== {total}/{len(args)} files modified by STRICT pass ===")
