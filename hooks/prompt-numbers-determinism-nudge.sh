#!/usr/bin/env bash
# prompt-numbers-determinism-nudge.sh — UserPromptSubmit hook (INJECT-ONLY, не блокирует)
#
# Детектит задачи где смешаны ТОЧНЫЕ ДАННЫЕ (числа/цены/коды) и СМЫСЛ (перевод/скрейп/расчёт)
# → инжектит напоминание правила numbers-deterministic-meaning-llm.md:
#   числа — детерминированным кодом (regex/CSS/парсер/арифметика + gate),
#   смыслы — нейросетью. Число «прошло через LLM» = UNCONFIRMED пока не сверено кодом.
#
# Источник: Fable 5 win (mask-numbers перевод + CSS-extract цен + pofilter-gate), 2026-06-12.
# Правило: ~/.claude/rules/numbers-deterministic-meaning-llm.md
# Bypass: NUMBERS_DET_OFF=1
# Anti-spam: один раз за сессию (/tmp/numbers-det-done-<session_id>)

set -uo pipefail
[[ "${NUMBERS_DET_OFF:-0}" == "1" ]] && exit 0

INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty' 2>/dev/null)
PROMPT=$(echo "$INPUT" | jq -r '.prompt // empty' 2>/dev/null)

[[ -z "$PROMPT" || -z "$SESSION_ID" ]] && exit 0

FLAG="/tmp/numbers-det-done-${SESSION_ID}"
[[ -f "$FLAG" ]] && exit 0

[[ ${#PROMPT} -lt 15 ]] && exit 0

# НЕ использовать tr [:upper:][:lower:] — byte-oriented, корраптит UTF-8 кириллицу.
# bash [[ == *kw* ]] + nocasematch — byte-substring, без grep/locale-проблем (self-corrections #31).
shopt -s nocasematch 2>/dev/null || true
HIT=0
for kw in перевед переве даташ datasheet 'перевод pdf' 'перевод докум' 'перевод специф' 'перевод техдок' 'перевод прайс' 'translate pdf' 'translate doc' симметрон simmetron спарс распарс скрейп scrape 'собери цены' 'вытащи цены' 'цены с сайта' 'цены конкурент' характеристик 'extract price' 'extract number' посчитай рассчитай доходност окупаем доходность вклад ипотек кредит ставк; do
  if [[ "$PROMPT" == *"$kw"* ]]; then HIT=1; break; fi
done
if [[ "$HIT" == "1" ]]; then
  touch "$FLAG" 2>/dev/null || true
  cat << 'EOF'
[ЧИСЛА ДЕТЕРМИНИРОВАННО — правило numbers-deterministic-meaning-llm.md]
В этой задаче смешаны ТОЧНЫЕ ДАННЫЕ (числа/цены/коды/координаты/даты) и СМЫСЛ (перевод/извлечение/расчёт).
Разделить обработку:
 • Числа/цены/коды → ДЕТЕРМИНИРОВАННО кодом (regex / CSS-селектор / парсер / арифметика), НЕ выводом LLM.
 • Смыслы → нейросеть (перевод, переформулировка, классификация).
 • Если данные «проходят через» LLM (перевод/суммаризация) — обязателен КОД-ГЕЙТ сверки что все числа целы (mask-numbers → перевод → вернуть числа → pofilter-gate).
 • Скрейп цен — CSS-селектор/regex без LLM; каждое число = source_url + checked_at.
 • Расчёт (ROI/проценты/доходность) — арифметика кодом, 2+ источника на число (calculations-need-sources).
Число, выведенное/переведённое LLM без код-сверки = по умолчанию UNCONFIRMED.
Bypass: NUMBERS_DET_OFF=1
EOF
fi

exit 0
