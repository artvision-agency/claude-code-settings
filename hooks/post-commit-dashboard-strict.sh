#!/usr/bin/env bash
# post-commit-dashboard-strict.sh — auto-strict для клиентских dashboard файлов
#
# Срабатывает: PostToolUse Bash на `git commit` ИЛИ запуск из артвижн-data post-commit hook.
# Идея: после commit'а с большим diff (>50 строк) в dashboard/cabinet/КП — автоматически:
#   1. factcheck-fns-freshness.py → ФНС-числа без года/URL
#   2. dashboard-vs-pitch-classify.py → cabinet vs pitch
#   3. Если CRITICAL → TG-alert в team-chat (-4273200821)
#
# Прецедент 2026-05-20 (MIRBIR):
#   Strict-агент нашёл 4 CRITICAL только когда Антон сам попросил «strict factcheck».
#   Этот хук ловит CRITICAL автоматически в момент commit'а.
#
# Bypass: STRICT_AUTO_SKIP=1
#
# Зависит от: ~/.claude/scripts/factcheck-fns-freshness.py
#             ~/.claude/scripts/dashboard-vs-pitch-classify.py
#             ~/.claude/scripts/tg-send.sh (опционально для алерта)

set -euo pipefail

JSON_INPUT=$(cat 2>/dev/null || echo '')

# Достаём команду
COMMAND=$(echo "$JSON_INPUT" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('tool_input', {}).get('command', ''))" 2>/dev/null || echo "")

# Не наш git commit — выход
if [[ ! "$COMMAND" =~ git[[:space:]]+commit ]]; then
    exit 0
fi

# Bypass
if [[ "${STRICT_AUTO_SKIP:-}" == "1" ]]; then
    exit 0
fi

# Найти cwd (где репозиторий) — берём из tool_input или пропускаем
CWD=$(echo "$JSON_INPUT" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('tool_input', {}).get('cwd', ''))" 2>/dev/null || echo "")
[ -z "$CWD" ] && CWD="$(pwd)"

# Только artvision-data
if [[ "$CWD" != *"artvision-data"* ]]; then
    exit 0
fi

cd "$CWD" 2>/dev/null || exit 0

# Получить файлы из последнего коммита
LAST_COMMIT=$(git log -1 --pretty=%H 2>/dev/null || echo "")
[ -z "$LAST_COMMIT" ] && exit 0

# Список изменённых HTML файлов клиентов
CHANGED=$(git show --name-only --pretty=format: "$LAST_COMMIT" 2>/dev/null | grep -E '(clients|presales)/.*\.html$' || echo "")
[ -z "$CHANGED" ] && exit 0

FNS_SCRIPT="$HOME/.claude/scripts/factcheck-fns-freshness.py"
CLASS_SCRIPT="$HOME/.claude/scripts/dashboard-vs-pitch-classify.py"
LOG="/tmp/post-commit-strict-$(date +%Y%m%d).log"

CRITICAL_FOUND=0
WARN_TOTAL=0
REPORT=""

while IFS= read -r FILE; do
    [ -z "$FILE" ] && continue
    # Только dashboard / cabinet / kp / report — не любой HTML
    if [[ ! "$FILE" =~ (dashboard|cabinet|kp|report|mirbir-simple|director) ]]; then
        continue
    fi
    [ ! -f "$FILE" ] && continue

    # Размер diff
    DIFF_LINES=$(git show "$LAST_COMMIT" -- "$FILE" 2>/dev/null | wc -l | tr -d ' ')
    if [ "$DIFF_LINES" -lt 50 ]; then
        echo "[post-commit-strict] $FILE: skip (diff $DIFF_LINES < 50)" >> "$LOG"
        continue
    fi

    echo "[post-commit-strict] check $FILE (diff $DIFF_LINES)" >> "$LOG"

    # 1. fns-freshness
    if [ -x "$FNS_SCRIPT" ]; then
        FNS_OUT=$(python3 "$FNS_SCRIPT" "$FILE" --json 2>/dev/null || echo '{}')
        FNS_CRIT=$(echo "$FNS_OUT" | python3 -c "import sys, json; print(json.load(sys.stdin).get('summary', {}).get('CRITICAL', 0))" 2>/dev/null || echo "0")
        FNS_WARN=$(echo "$FNS_OUT" | python3 -c "import sys, json; print(json.load(sys.stdin).get('summary', {}).get('WARN', 0))" 2>/dev/null || echo "0")
        CRITICAL_FOUND=$((CRITICAL_FOUND + FNS_CRIT))
        WARN_TOTAL=$((WARN_TOTAL + FNS_WARN))
        REPORT="${REPORT}${FILE} fns-freshness: $FNS_CRIT CRIT / $FNS_WARN WARN\n"
    fi

    # 2. cabinet vs pitch — для информации (не блокер)
    if [ -x "$CLASS_SCRIPT" ]; then
        CLS_OUT=$(python3 "$CLASS_SCRIPT" "$FILE" --json 2>/dev/null || echo '{}')
        CLS_VERDICT=$(echo "$CLS_OUT" | python3 -c "import sys, json; print(json.load(sys.stdin).get('verdict', '?'))" 2>/dev/null || echo "?")
        REPORT="${REPORT}${FILE} classifier: $CLS_VERDICT\n"
    fi
done <<< "$CHANGED"

# Лог
echo "[$(date '+%H:%M:%S')] commit $LAST_COMMIT: $CRITICAL_FOUND CRIT / $WARN_TOTAL WARN" >> "$LOG"

# TG-alert если CRITICAL
if [ "$CRITICAL_FOUND" -gt 0 ]; then
    TG_SCRIPT="$HOME/.claude/scripts/tg-send.sh"
    if [ -x "$TG_SCRIPT" ]; then
        MSG="🔴 post-commit strict: $CRITICAL_FOUND CRITICAL after $LAST_COMMIT"$'\n\n'"$REPORT"$'\n'"Лог: $LOG"
        "$TG_SCRIPT" team "$MSG" >/dev/null 2>&1 || true
    fi
    # Также в stderr (видно Antону в Claude Code)
    echo "" >&2
    echo "🔴 post-commit-strict: $CRITICAL_FOUND CRITICAL findings в commit'е $LAST_COMMIT" >&2
    echo "$REPORT" >&2
    echo "Лог: $LOG" >&2
fi

exit 0
