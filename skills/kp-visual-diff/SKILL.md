---
name: kp-visual-diff
description: Визуальный попарный диф двух КП клиентов через рендер слайдов в PNG + pixel-diff + side-by-side HTML отчёт. Используй когда новый КП собран по шаблону существующего и нужно проверить что все элементы перенесены. Триггеры — 'kp visual diff', 'визуальный диф кп', 'сравни кп с шаблоном', 'не пропустил ли слайд', 'проверь что все элементы перенесены', 'compare kp', 'kp template diff'.
---

# kp-visual-diff — попарный визуальный диф двух КП

## Когда использовать

- Новый КП собран по шаблону existing КП (например все 40-audits AdvertMed на основе starclinic) → перед отправкой клиенту
- Проверить что в новом КП НЕ потерялись элементы reference (бэйджи, плашки, разделы, доменный pill, brand strip)
- В конце сессии правки КП — финальный QA

## Когда НЕ использовать

- Один КП без reference — нечего сравнивать (используй `/factcheck`)
- Reference и target из разных шаблонов — diff будет 100%, бессмысленно
- Только текстовые правки (typo, числа) — используй `/factcheck`

## Запуск

```bash
python3 ~/artvision-data/scripts/kp-visual-diff.py \
    --reference clients/<refclient>/<path>/kp.html \
    --target clients/<targetclient>/<path>/kp.html \
    --output /tmp/kp-diff-<slug>
```

Опции:
- `--max-diff-pct` (default 40) — порог per-slide pixel diff для BLOCK
- `--max-blocks-missing` (default 2) — сколько слайдов из reference может отсутствовать в target

## Output

| Файл | Что |
|------|-----|
| `<output>/report.html` | Интерактивный отчёт side-by-side для каждой пары слайдов |
| `<output>/summary.json` | Машиночитаемый verdict (PASS / REVIEW / BLOCK) + per-slide diff_pct |
| `<output>/composite/comp-NN.png` | REFERENCE \| TARGET \| DIFF композит |
| `<output>/diff/diff-NN.png` | Pixel-diff подсветка (красное = отличается от ref) |
| `<output>/ref/`, `<output>/target/` | Исходные PNG обоих КП |

Exit codes:
- `0` — PASS / REVIEW (можно деплоить, но REVIEW = посмотри отчёт)
- `2` — BLOCK (per-slide diff > max или blocks_missing > max) → не деплоить

## Verdict logic

| Условие | Verdict |
|---------|---------|
| max_diff_pct > 40 ИЛИ blocks_missing > 2 | **BLOCK** |
| avg_diff_pct > 15 ИЛИ blocks_missing > 0 | REVIEW |
| иначе | PASS |

## Алгоритм

1. **Render**: оба HTML открываются в headless Chromium 1280×720@2x, для каждого `.slide` снимается PNG через активацию `.active` класса. JS-навигация и transitions отключены.
2. **Pixel diff**: попарное сравнение через Pillow `ImageChops.difference`, threshold > 30 per channel = «изменён». Считается % изменённых пикселей.
3. **Composite**: side-by-side `[ REFERENCE | TARGET | DIFF ]` с подписью diff% (зелёный <10, оранжевый 10-30, красный >30).
4. **Report**: HTML с таблицей слайдов, эмбедом композитов, KPI-блоком (avg/max diff, blocks missing).

## Прецедент

**АН-НУР сессия 2026-05-05** (3 итерации):
- Антон 3 раза возвращался: «не все элементы из starclinic перенесены»
- Изначально я делал grep по коду — пропустил domain-pill, бэйдж AdvertMed, плашки «Что даёт оценку», «Окно ROI», «Конкурентная гипотеза», «Формат AdvertMed», реквизиты клиники
- Решение: skill + script + hook → больше нельзя задеплоить КП с blocks_missing > 2

## Связь с другими правилами

- `quality.md` — расширяет «КП / HTML для клиента» обязательным визуальным diff если есть reference
- `factcheck.md` — дополняет (factcheck = текст/числа, kp-visual-diff = layout/elements)
- Hook `pre-scp-kp-diff.sh` — блокирует scp клиентского КП пока не пройдёт diff против reference (если в `clients/<name>/config.yaml` указан `reference_kp:`)
