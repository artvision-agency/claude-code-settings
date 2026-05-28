#!/bin/bash
# pre-fork-without-roundtable.sh
# Блокирует `gh repo fork` если в transcript текущей сессии нет следов round_table проверки.
# Соответствует правилу tool-adoption-proof.md — adopt внешнего инструмента только после round_table.
# Bypass: ROUNDTABLE_OK=1

set -uo pipefail

# Hook читает JSON input через stdin
INPUT="$(cat 2>/dev/null || echo '{}')"

# Извлекаем команду из tool_input
CMD=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get('tool_input', {}).get('command', ''))
except Exception:
    print('')
" 2>/dev/null)

# Проверяем что это gh repo fork
if ! echo "$CMD" | grep -qE 'gh\s+repo\s+fork\b'; then
    exit 0  # Не fork — пропускаем
fi

# Bypass
if [ "${ROUNDTABLE_OK:-}" = "1" ]; then
    echo "[pre-fork] bypass: ROUNDTABLE_OK=1" >&2
    exit 0
fi

# Извлекаем transcript_path
TRANSCRIPT=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get('transcript_path', ''))
except Exception:
    print('')
" 2>/dev/null)

if [ -z "$TRANSCRIPT" ] || [ ! -f "$TRANSCRIPT" ]; then
    # Без transcript — пропускаем (не блокировать на edge case)
    exit 0
fi

# Ищем round_table или mcp__llm-consilium в transcript
if grep -qE 'round_table|mcp__llm-consilium|ext-tool-bench|tool-adoption-proof' "$TRANSCRIPT" 2>/dev/null; then
    exit 0  # Round_table был — пропускаем
fi

# Блокируем
cat >&2 <<'BLOCKED'
🛑 pre-fork-without-roundtable: ЗАБЛОКИРОВАНО

Команда `gh repo fork` детектирована без следов round_table в текущей сессии.

Правило `~/.claude/rules/tool-adoption-proof.md` требует:
  1. Round_table через mcp__llm-consilium с 2-3 внешними моделями
  2. Запись гипотезы в knowledge/<domain>/hypotheses.md
  3. 3 подтверждения до промоушена в rules

ДЕЙСТВИЕ:
  • Вызови mcp__llm-consilium__round_table перед adopt инструмента
  • ИЛИ ROUNDTABLE_OK=1 gh repo fork ... (если бы round_table уже был раньше)

Прецедент: 2026-04-20 (Obsidian — НЕ внедрять после round_table)
BLOCKED

exit 2
