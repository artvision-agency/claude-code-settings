#!/usr/bin/env bash
# pre-tool-codex-lifecycle-guard.sh — enforcer codex-dev-lifecycle для кода (warn-only)
#
# Правило: ~/.claude/rules/codex-dev-lifecycle.md (DEFAULT-обязательный для кода во всех сессиях).
# Прецедент: OPS runner собран 14.06 без Codex-ревью (правило opt-in → пропустили).
# Этот хук — деттерминированный enforcer: при Write/Edit КОДА в scripts/.claude
# напоминает прогнать codex-dev-lifecycle (план→Codex-ревью→build→Codex-ревью).
#
# ПОВЕДЕНИЕ: WARN-ONLY (exit 0 всегда). НЕ блокирует — печатает напоминание в stderr.
#   Block на 3 аккаунта = риск сломать сессии (self-corrections #31). Только warn.
# DEDUP: один раз за сессию (маркер /tmp).
# BYPASS: CODEX_LIFECYCLE_OK=1
#
# Тест: pre-tool-codex-lifecycle-guard.test.sh
set -uo pipefail

[ -n "${CODEX_LIFECYCLE_OK:-}" ] && exit 0

# stdin = JSON tool-call. Достаём file_path и session_id без jq (могут не быть).
INPUT="$(cat 2>/dev/null || true)"
FP="$(printf '%s' "$INPUT" | grep -oE '"file_path"[[:space:]]*:[[:space:]]*"[^"]+"' | head -1 | sed -E 's/.*"file_path"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/')"
SID="$(printf '%s' "$INPUT" | grep -oE '"session_id"[[:space:]]*:[[:space:]]*"[^"]+"' | head -1 | sed -E 's/.*:[[:space:]]*"([^"]+)".*/\1/')"

# Нет пути — не наше дело.
[ -z "$FP" ] && exit 0

# Триггер: код-файл (.py/.js/.sh) в код-локациях (scripts/ | .claude/workflows | .claude/hooks).
case "$FP" in
  *.py|*.js|*.sh|*.mjs|*.cjs) : ;;
  *) exit 0 ;;
esac
case "$FP" in
  */scripts/*|*/.claude/workflows/*|*/.claude/hooks/*) : ;;
  *) exit 0 ;;
esac

# Исключения: тесты/конфиги/тривиальное — не дёргаем (.test., conftest, __init__).
case "$FP" in
  *.test.sh|*.test.py|*.test.js|*_test.py|*test_*.py|*/conftest.py|*/__init__.py) exit 0 ;;
esac

# Dedup за сессию.
MARK="/tmp/codex-lifecycle-warned-${SID:-nosession}"
[ -f "$MARK" ] && exit 0
touch "$MARK" 2>/dev/null || true

cat >&2 <<'EOF'
[CODEX-LIFECYCLE] Правка КОДА (scripts/.claude). По правилу codex-dev-lifecycle.md
этот класс ОБЯЗАН идти через цикл: план(Claude)→ПЕРЕГОВОРЫ+Codex-ревью плана→
build→Codex-ревью кода→рефактор, луп до «ожидание==результат».
  → Workflow({name:'codex-dev-lifecycle', args:{task, context, attackSurface, buildScope}})
  → ИЛИ Agent(subagent_type:'codex:codex-rescue') на ревью + переговоры (факты Claude бьют Codex).
При 403 Codex — codex CLI / round_table / задокументированное main-ревью (не пропустить ревью).
Тривиально/опечатка/не security → bypass: CODEX_LIFECYCLE_OK=1
EOF
exit 0
