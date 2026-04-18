#!/usr/bin/env python3
"""
Session Data Audit — сканирует ВСЕ сессии за 6 месяцев,
находит паттерны где Claude генерировал данные которые должны быть из проверенных источников.

Категории:
1. Рыночные цифры (доли рынка, обороты, рост)
2. Конкуренты (названия, позиции, сравнения)
3. Цены/стоимость услуг
4. URL/ссылки на источники
5. Статистика (посещаемость, конверсия, CTR)
6. Юридические данные (ИНН, ОГРН, обороты по СБИС)
7. Отраслевые факты (тренды, прогнозы)
8. География/демография
"""

import json
import os
import re
import sys
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime

PROJECTS_DIR = Path.home() / ".claude" / "projects"

# Паттерны для обнаружения данных требующих верификации
PATTERNS = {
    "market_numbers": {
        "label": "Рыночные цифры",
        "patterns": [
            r'\d+[,.]?\d*\s*(?:млрд|млн|тыс|%|процент)',
            r'(?:рынок|объём|оборот|выручка|доход)\s+(?:составля|оценива|равн|достиг)',
            r'(?:рост|падение|снижение|увеличение)\s+(?:на|до)\s+\d+',
            r'(?:доля\s+рынка|market\s+share)',
        ],
    },
    "competitors": {
        "label": "Конкуренты",
        "patterns": [
            r'(?:конкурент|competitor|лидер\s+рынка|топ-?\d+)',
            r'(?:занимает|позиция|место)\s+(?:в|на)\s+(?:рынке|выдаче|нише)',
            r'(?:обгоняет|опережает|уступает|проигрывает)',
        ],
    },
    "prices": {
        "label": "Цены и стоимость",
        "patterns": [
            r'(?:стоимость|цена|тариф|бюджет|прайс)\s+(?:от|до|составля|начина)',
            r'\d+[\s,.]?\d*\s*(?:руб|₽|\$|USD|EUR|тыс\.?\s*руб)',
            r'(?:средний\s+чек|ARPU|LTV|CAC|CPA|CPL|CPC)',
        ],
    },
    "urls_sources": {
        "label": "URL и источники",
        "patterns": [
            r'(?:по\s+данным|источник|согласно|исследовани)',
            r'(?:Яндекс\.?Вордстат|SimilarWeb|SEMrush|Ahrefs|Serpstat)',
            r'(?:Росстат|СПАРК|СБИС|rusprofile|checko)',
        ],
    },
    "traffic_stats": {
        "label": "Статистика трафика",
        "patterns": [
            r'(?:посещаемость|трафик|визиты|сессии)\s+\d+',
            r'(?:конверсия|CTR|CR|bounce\s*rate)\s+\d+',
            r'(?:позиция|ранжирован|топ-?\d+)\s+(?:по|в)\s+(?:запрос|ключ)',
        ],
    },
    "legal_financial": {
        "label": "Юридические/финансовые данные",
        "patterns": [
            r'(?:ИНН|ОГРН|КПП|ОКПО)\s*:?\s*\d+',
            r'(?:уставный\s+капитал|учредител|директор|генеральный)',
            r'(?:годовая|годовой|квартальн)\s+(?:выручка|оборот|прибыль)',
        ],
    },
    "industry_facts": {
        "label": "Отраслевые факты и тренды",
        "patterns": [
            r'(?:тренд|прогноз|forecast|trend)\s+(?:на|до|в)\s+20\d\d',
            r'(?:по\s+прогнозам|ожидается|к\s+20\d\d)',
            r'(?:отрасл|индустри|сектор|сегмент)\s+(?:рост|развива|трансформ)',
        ],
    },
    "geo_demo": {
        "label": "География и демография",
        "patterns": [
            r'(?:население|жителей|численность)\s+\d+',
            r'(?:регион|город|район)\s+с\s+(?:населением|численностью)',
            r'(?:целевая\s+аудитория|ЦА|портрет\s+клиента)',
        ],
    },
}


def scan_session(session_file: Path) -> list[dict]:
    """Сканирует одну сессию, возвращает найденные паттерны."""
    findings = []

    try:
        with open(session_file) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if obj.get("type") != "assistant":
                    continue
                if obj.get("isSidechain"):
                    continue

                # Извлекаем текст
                msg = obj.get("message", {})
                content = msg.get("content", "")
                text = ""

                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            text += block.get("text", "")
                elif isinstance(content, str):
                    text = content

                if len(text) < 50:
                    continue

                # Проверяем каждую категорию
                for cat_id, cat_info in PATTERNS.items():
                    for pattern in cat_info["patterns"]:
                        matches = re.findall(pattern, text, re.IGNORECASE)
                        if matches:
                            # Извлекаем контекст (±100 символов вокруг матча)
                            for match in matches[:3]:  # макс 3 матча на паттерн
                                if isinstance(match, str):
                                    idx = text.lower().find(match.lower())
                                    if idx >= 0:
                                        start = max(0, idx - 80)
                                        end = min(len(text), idx + len(match) + 80)
                                        context = text[start:end].replace('\n', ' ').strip()
                                    else:
                                        context = match
                                else:
                                    context = str(match)

                                findings.append({
                                    "category": cat_id,
                                    "label": cat_info["label"],
                                    "context": context[:300],
                                    "session": session_file.stem[:8],
                                    "timestamp": obj.get("timestamp", ""),
                                })
                            break  # один паттерн сработал — достаточно для категории
    except Exception as e:
        pass  # пропускаем битые файлы

    return findings


def main():
    print("🔍 Сканирую сессии...", file=sys.stderr)

    # Собираем все JSONL файлы
    all_sessions = sorted(PROJECTS_DIR.glob("*/*.jsonl"), key=os.path.getmtime, reverse=True)

    # Фильтр: только за последние 6 месяцев (по mtime)
    cutoff = datetime.now().timestamp() - (180 * 86400)
    sessions = [s for s in all_sessions if os.path.getmtime(s) > cutoff]

    print(f"📁 Найдено {len(sessions)} сессий за 6 месяцев (из {len(all_sessions)} всего)", file=sys.stderr)

    # Счётчики
    category_counts = Counter()
    category_examples = defaultdict(list)
    sessions_with_data = set()
    total_findings = 0

    for i, session in enumerate(sessions):
        if i % 100 == 0:
            print(f"  [{i}/{len(sessions)}] обработано...", file=sys.stderr)

        findings = scan_session(session)
        if findings:
            sessions_with_data.add(session.stem[:8])

        for f in findings:
            category_counts[f["category"]] += 1
            total_findings += 1
            # Сохраняем макс 10 примеров на категорию
            if len(category_examples[f["category"]]) < 10:
                category_examples[f["category"]].append(f)

    # Отчёт
    print(f"\n{'='*70}")
    print(f"DATA AUDIT REPORT — {len(sessions)} сессий, {len(sessions_with_data)} с данными")
    print(f"Всего найдено паттернов: {total_findings}")
    print(f"{'='*70}\n")

    # Сортируем по частоте
    for cat_id, count in category_counts.most_common():
        label = PATTERNS[cat_id]["label"]
        print(f"\n## {label} — {count} случаев")
        print(f"{'─'*50}")
        for ex in category_examples[cat_id][:5]:
            print(f"  [{ex['session']}] ...{ex['context']}...")

    # Рекомендации
    print(f"\n{'='*70}")
    print("РЕКОМЕНДАЦИИ: какие данные заменить на API/скрипты")
    print(f"{'='*70}\n")

    recommendations = {
        "market_numbers": "→ СКРИПТ: парсинг Росстат, СПАРК, отраслевых отчётов (РБК, Коммерсантъ)",
        "competitors": "→ СКРИПТ: SimilarWeb API / Serpstat API / парсинг выдачи Яндекс",
        "prices": "→ СКРИПТ: парсинг прайс-листов конкурентов, Яндекс.Маркет API",
        "urls_sources": "→ СКРИПТ: HTTP HEAD валидация всех URL + автоподстановка из кэша",
        "traffic_stats": "→ СКРИПТ: Яндекс.Метрика API, Google Analytics API, Serpstat/Keys.so",
        "legal_financial": "→ СКРИПТ: rusprofile.ru парсинг, СБИС API, checko.ru",
        "industry_facts": "→ СКРИПТ: RSS парсинг отраслевых изданий + верификация через 2 источника",
        "geo_demo": "→ СКРИПТ: Росстат API, data.gov.ru, Яндекс.Карты API",
    }

    for cat_id, count in category_counts.most_common():
        label = PATTERNS[cat_id]["label"]
        rec = recommendations.get(cat_id, "→ требует ручной верификации")
        print(f"  {label} ({count}x): {rec}")

    # Сохраняем полный отчёт
    report_path = Path.home() / ".claude" / "data-audit-report.md"
    with open(report_path, "w") as f:
        f.write(f"# Data Audit Report\n\n")
        f.write(f"**Дата:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"**Сессий:** {len(sessions)} | **С данными:** {len(sessions_with_data)} | **Паттернов:** {total_findings}\n\n")

        f.write("## Категории по частоте\n\n")
        f.write("| # | Категория | Случаев | Рекомендация |\n")
        f.write("|---|-----------|---------|-------------|\n")
        for i, (cat_id, count) in enumerate(category_counts.most_common(), 1):
            label = PATTERNS[cat_id]["label"]
            rec = recommendations.get(cat_id, "ручная верификация")
            f.write(f"| {i} | {label} | {count} | {rec} |\n")

        f.write("\n## Примеры по категориям\n\n")
        for cat_id, count in category_counts.most_common():
            label = PATTERNS[cat_id]["label"]
            f.write(f"\n### {label} ({count})\n\n")
            for ex in category_examples[cat_id][:5]:
                f.write(f"- `[{ex['session']}]` ...{ex['context']}...\n")

        f.write(f"\n## Рекомендуемый Data Pipeline\n\n")
        f.write("```\n")
        f.write("ЗАПРОС НА ДАННЫЕ\n")
        f.write("     │\n")
        f.write("     ▼\n")
        f.write("┌─────────────────┐\n")
        f.write("│  DATA ROUTER    │ — определяет категорию данных\n")
        f.write("└────────┬────────┘\n")
        f.write("         │\n")
        f.write("    ┌────┴────┬──────────┬──────────┐\n")
        f.write("    ▼         ▼          ▼          ▼\n")
        f.write("┌───────┐ ┌───────┐ ┌────────┐ ┌────────┐\n")
        f.write("│Росстат│ │СБИС/  │ │Serpstat│ │Отрасл. │\n")
        f.write("│data.  │ │Ruspr. │ │SWeb   │ │RSS/    │\n")
        f.write("│gov.ru │ │Checko │ │Keys.so│ │издания │\n")
        f.write("└───┬───┘ └───┬───┘ └───┬────┘ └───┬────┘\n")
        f.write("    │         │         │          │\n")
        f.write("    ▼         ▼         ▼          ▼\n")
        f.write("┌─────────────────────────────────────┐\n")
        f.write("│        VERIFIED DATA CACHE           │\n")
        f.write("│  JSON + дата + источник + URL        │\n")
        f.write("└────────────────┬────────────────────┘\n")
        f.write("                 │\n")
        f.write("                 ▼\n")
        f.write("┌─────────────────────────────────────┐\n")
        f.write("│     КП / ОТЧЁТ / ДАШБОРД            │\n")
        f.write("│  Каждое число = источник + дата      │\n")
        f.write("└─────────────────────────────────────┘\n")
        f.write("```\n")

    print(f"\n📄 Полный отчёт: {report_path}")


if __name__ == "__main__":
    main()
