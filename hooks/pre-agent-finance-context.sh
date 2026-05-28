#!/usr/bin/env bash
# pre-agent-finance-context.sh
# Hook: PreToolUse(Agent) для finance/research задач.
# Объединяет 2 правила:
#   1) proven-tools-first.md — напоминать про GitHub-tools перед research-агентом
#   2) поиск .claude_temp_scripts/credit-* и personal/finance/* перед запуском нового research
#
# Прецедент 22.05.2026 — Антон запустил 5 research-агентов на банки/кредитки/ипотеки,
# не зная что прошлая сессия 28-29.04.2026 уже сделала аналогичный research
# (39 файлов в .claude_temp_scripts/credit-reels-2026-04-28/).
# Через 30 мин Антон скорректировал. Теряем ~1 час работы.
#
# Bypass: FINANCE_HISTORY_OK=1 <операция>

set -u

# Stdin = JSON от Claude Code (см. claude.ai/docs/claude-code/hooks)
INPUT=$(cat)

# Защита от non-Agent tool calls — пропускаем
TOOL_NAME=$(printf '%s' "$INPUT" | /usr/bin/python3 -c "import json,sys; d=json.loads(sys.stdin.read()); print(d.get('tool_name',''))" 2>/dev/null || echo "")
if [[ "$TOOL_NAME" != "Agent" ]]; then
  exit 0
fi

# Bypass
if [[ "${FINANCE_HISTORY_OK:-}" == "1" ]]; then
  exit 0
fi

# Парсим prompt субагента
PROMPT=$(printf '%s' "$INPUT" | /usr/bin/python3 -c "
import json, sys
try:
    d = json.loads(sys.stdin.read())
    p = d.get('tool_input', {}).get('prompt', '')
    print(p[:3000])  # первые 3K символов
except Exception:
    pass
" 2>/dev/null || echo "")

if [[ -z "$PROMPT" ]]; then
  exit 0
fi

# Триггеры финансовых задач
FINANCE_KEYWORDS='кредит|банк|альфа|тинькофф|сбер|втб|газпром|совком|маркетплейс|ozon|wildberries|wb|халва|долями|подели|сплит|накопит|вклад|депозит|ипотек|рефинанс|кредитка|арбитраж|БТ|перевод баланса|БКИ|ПДН|МПЛ|АСВ|НДФЛ|cashflow|финанс|finance|loan|credit|mortgage|bank|deposit|saving'

if ! echo "$PROMPT" | /usr/bin/grep -qiE "$FINANCE_KEYWORDS"; then
  exit 0
fi

# Это финансовая задача — проверяем историю
FOUND_FILES=""

# 1. .claude_temp_scripts/credit-*, finance-*, money-*, refi-* за последние 90 дней
SCRIPTS_DIR="$HOME/artvision-data/.claude_temp_scripts"
if [[ -d "$SCRIPTS_DIR" ]]; then
  for d in "$SCRIPTS_DIR"/credit-* "$SCRIPTS_DIR"/finance-* "$SCRIPTS_DIR"/money-* "$SCRIPTS_DIR"/refi-* "$SCRIPTS_DIR"/bank-*; do
    [[ -d "$d" ]] || continue
    # Только за последние 90 дней
    if /usr/bin/find "$d" -maxdepth 0 -mtime -90 2>/dev/null | /usr/bin/grep -q .; then
      FOUND_FILES="$FOUND_FILES\n  - $d/ (см. FINAL_synthesis.md если есть)"
    fi
  done
fi

# 2. personal/finance/* за 90 дней
FINANCE_DIR="$HOME/artvision-data/personal/finance"
if [[ -d "$FINANCE_DIR" ]]; then
  while IFS= read -r d; do
    [[ -d "$d" ]] || continue
    FOUND_FILES="$FOUND_FILES\n  - $d/"
  done < <(/usr/bin/find "$FINANCE_DIR" -mindepth 1 -maxdepth 1 -type d -mtime -90 2>/dev/null)
fi

# Если ничего не нашли — напомнить про proven-tools-first
if [[ -z "$FOUND_FILES" ]]; then
  /bin/cat <<EOF >&2
ℹ️  PROVEN-TOOLS-FIRST напоминание: задача похожа на финансовый research.
Перед запуском Agent — 3-минутный поиск готовых GitHub-tools:
  - WebSearch "<task> github stars 2026"
  - Если есть >1K⭐ репо в нужной нише → adopt вместо write
  - См. правило ~/.claude/rules/proven-tools-first.md
  - См. каталог Wave 4 (financial): beancount, fava, numpy-financial, wealthfolio, actual
Bypass: FINANCE_HISTORY_OK=1
EOF
  exit 0
fi

# Есть локальный контекст — предупреждаем чтобы не дублировать
/bin/cat <<EOF >&2
🚨 FINANCE-HISTORY DETECTED: задача похожа на финансовый research, но УЖЕ ЕСТЬ локальный контекст:
$(printf '%b' "$FOUND_FILES")

ПРОЧИТАЙ существующие файлы (особенно FINAL_synthesis.md / final-strategy-*.md / analysis/) ПЕРЕД
запуском нового research-агента. Прецедент 22.05.2026 — потеряли ~1 час дублируя апрельскую сессию.

Также проверь external-tools-catalog.md Wave 4 — может уже форкнут нужный инструмент.

Bypass: FINANCE_HISTORY_OK=1
EOF

# Это soft warning, не блокируем (exit 0)
exit 0
