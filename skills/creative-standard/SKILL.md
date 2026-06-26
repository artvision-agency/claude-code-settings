---
name: creative-standard
description: Каталог стандартов рекламных креативов (ракурс/линза, тип баннера, gen-промпт) как ДАННЫЕ — 0 токенов на «вспомнить». Перед генерацией дентал/мед-креатива брать стандарт отсюда, не из памяти. Триггеры — 'creative standard', 'стандарт креатива', 'каталог референсов', 'добавь в стандарты', 'применить стандарт креатива', 'ракурс как у конкурента', 'баннер по стандарту'.
---
# creative-standard — каталог стандартов креативов (0 токенов)
```bash
python3 ~/.claude/scripts/creative_standard.py list [--type lens|banner]
python3 ~/.claude/scripts/creative_standard.py get <id>          # gen_prompt для генерации
python3 ~/.claude/scripts/creative_standard.py add --id X --name "..." --type lens --image <path> --when "a;b" --gen "..."
```
Каталог: artvision-data/knowledge/marketing/ad-creative-standards/catalog.yaml (+ refs/).
Применять: ПЕРЕД генерацией рекламного креатива (ad-creative/figma) → `get <id>` → взять gen_prompt + ref. Антон присылает реф «запиши в стандарт» → `add`.
Стандарты v1: wideangle-face-forward (широкий ракурс лицо-вперёд), phone-mockup-consult (баннер консультации с телефоном).
