#!/bin/bash
# pre-finance-no-period-split.sh
# WARN если в финансовом HTML/MD есть выражения типа "3M × 15%" без разбивки welcome+базовая ставка.
# Соответствует правилу welcome-vs-base-math.md
# Bypass: FINANCE_SPLIT_OK=1

set -uo pipefail

INPUT="$(cat 2>/dev/null || echo '{}')"

# Берём path из Write/Edit
FILE_PATH=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    ti = d.get('tool_input', {})
    print(ti.get('file_path', ''))
except Exception:
    print('')
" 2>/dev/null)

# Проверка что это финансовый файл
if [ -z "$FILE_PATH" ]; then exit 0; fi
if ! echo "$FILE_PATH" | grep -qE '(finance|savings|ipoteka|deposit|вклад|кредит)'; then
    exit 0
fi
if ! echo "$FILE_PATH" | grep -qE '\.(html|md)$'; then exit 0; fi

# Bypass
if [ "${FINANCE_SPLIT_OK:-}" = "1" ]; then
    echo "[pre-finance-split] bypass: FINANCE_SPLIT_OK=1" >&2
    exit 0
fi

# Извлекаем content из tool_input
CONTENT=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    ti = d.get('tool_input', {})
    print(ti.get('content', '') or ti.get('new_string', ''))
except Exception:
    print('')
" 2>/dev/null)

if [ -z "$CONTENT" ]; then exit 0; fi

# Поиск: «3M × 15%» или «3 000 000 × 14.5%» без рядом «welcome» / «базов» / «период»
RESULT=$(python3 << PYEOF
import re

content = """$CONTENT"""

# Pattern: число × процент
finance_re = re.compile(
    r'\d[\d\s.,]*[MKмМкКmKтТ]?\s*(?:млн|тыс|mln)?\s*[*xх×]\s*\d{1,2}(?:[.,]\d+)?\s*%',
    re.IGNORECASE
)

split_markers = re.compile(
    r'welcome|приветств|базов|базис|базис.\s*ставк|после.\s*welcome|на.\s*остат',
    re.IGNORECASE
)

unsplit = []
for m in finance_re.finditer(content):
    start = max(0, m.start() - 300)
    end = min(len(content), m.end() + 300)
    window = content[start:end]
    if not split_markers.search(window):
        unsplit.append(m.group(0))

unsplit = unsplit[:3]
if unsplit:
    print("FOUND:" + "|".join(unsplit))
else:
    print("OK")
PYEOF
)

if echo "$RESULT" | grep -q '^FOUND:'; then
    EXPR=$(echo "$RESULT" | sed 's/^FOUND://')
    cat >&2 <<EOF
⚠️  pre-finance-no-period-split: WARN (не блок)

В $FILE_PATH найдены финансовые выражения без разбивки welcome+базовая:
  $EXPR

Правило welcome-vs-base-math.md требует: разбивать срок на welcome-период + базовый.
Иначе ошибка до 50-100% (прецедент session 9f7e1adc — 54% занижение).

Пример правильного:
  3M × 15.5% × 2/12 + 3M × 12% × 4/12 (welcome 2 мес + базовая 4 мес)

Bypass: FINANCE_SPLIT_OK=1
EOF
fi

exit 0
