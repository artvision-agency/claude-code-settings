#!/bin/bash
# pre-deploy-numbers-have-sources.sh
# WARN (не блок) перед scp клиентского HTML если в файле есть числа >= 100 без URL/даты в окне 200 символов.
# Соответствует правилу calculations-need-sources.md
# Bypass: NUMBERS_OK=1

set -uo pipefail

INPUT="$(cat 2>/dev/null || echo '{}')"

CMD=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get('tool_input', {}).get('command', ''))
except Exception:
    print('')
" 2>/dev/null)

# Проверяем что это scp .html на клиентский путь
if ! echo "$CMD" | grep -qE 'scp\s+.*\.html.*artvision\.pro|scp\s+.*\.html.*var/www'; then
    exit 0
fi

# Bypass
if [ "${NUMBERS_OK:-}" = "1" ]; then
    echo "[pre-deploy-numbers] bypass: NUMBERS_OK=1" >&2
    exit 0
fi

# Извлекаем локальный путь .html
LOCAL_FILE=$(echo "$CMD" | grep -oE '/[^ ]+\.html' | head -1)
if [ -z "$LOCAL_FILE" ] || [ ! -f "$LOCAL_FILE" ]; then
    exit 0  # Не нашли файл — пропускаем
fi

# Python проверка чисел без источника
RESULT=$(python3 << PYEOF
import re

path = "$LOCAL_FILE"
with open(path, encoding='utf-8') as f:
    text = f.read()

# Найти все числа >= 100 (например рубли, проценты, частотности)
# Включая форматы: 1234, 1 234, 1,234, 1.234 (млн), 12%, 1234₽
number_re = re.compile(r'(?<![\d.,])\b(\d{3,}(?:[\s,.]?\d{3})*(?:[.,]\d+)?)\b(?![\d.])')

# Маркеры источника
source_markers = re.compile(
    r'https?://|wordstat|webmaster|метрика|metrika|topvisor|backlinko|sistrix|'
    r'\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4}|\d{4}-\d{2}-\d{2}|'
    r'оценочно|целевой|бенчмарк|обновлено|проверено|источник|по данным',
    re.IGNORECASE
)

unsourced = []
for m in number_re.finditer(text):
    start = max(0, m.start() - 200)
    end = min(len(text), m.end() + 200)
    window = text[start:end]
    if not source_markers.search(window):
        # Проверяем что не внутри стиля/скрипта/HTML-атрибута
        # Простая heuristic: если рядом '<' или 'style=' — скип
        context_start = max(0, m.start() - 30)
        context = text[context_start:m.start()]
        if re.search(r'(style=|class=|width=|height=|<style|<script)', context):
            continue
        unsourced.append(m.group(1))

# Лимит — выводим первые 5
unsourced = unsourced[:5]

if unsourced:
    print("FOUND:" + ",".join(unsourced))
else:
    print("OK")
PYEOF
)

if echo "$RESULT" | grep -q '^FOUND:'; then
    NUMS=$(echo "$RESULT" | sed 's/^FOUND://')
    cat >&2 <<EOF
⚠️  pre-deploy-numbers-have-sources: WARN (не блок)

В файле $LOCAL_FILE найдены числа без источника в окне 200 символов:
  $NUMS

Правило calculations-need-sources.md требует: каждое число в документе клиенту = URL + дата + автор.

Если числа реально UNCONFIRMED → пометить «оценочно/целевой/бенчмарк».
Если есть источник но дальше 200 символов → переместить ближе.
Bypass: NUMBERS_OK=1 scp ...
EOF
fi

# Это WARN, не блок
exit 0
