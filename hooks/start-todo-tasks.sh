#!/usr/bin/env bash
# start-todo-tasks.sh — SessionStart hook.
# Читает все активные TODO.md по контекстам и инжектит pending задачи
# + ЖЁСТКУЮ инструкцию "создай TaskCreate для каждой" в system-reminder модели.
#
# Цель: убрать "Я забыл создать TaskCreate" из повторяющихся ошибок.
# Enforcement через hookSpecificOutput.additionalContext — модель ВИДИТ это
# в первом system-reminder'е сессии, не опираясь на память/преференсы.

set -uo pipefail

# TODO файлы по приоритету
TODO_FILES=(
  "$HOME/artvision-data/TODO.md"
  "$HOME/artvision-data/presale/TODO.md"
  "$HOME/artvision-data/products/TODO.md"
  "$HOME/artvision-tg-bot/TODO.md"
  "$HOME/devops-agent/TODO.md"
)

# Собираем все pending ( `- [ ]` строки, макс 30 на файл — анти-флуд)
ALL_PENDING=""
COUNT=0
TOTAL=0
for f in "${TODO_FILES[@]}"; do
  [ -f "$f" ] || continue
  # Всего pending в файле (для счётчика)
  FILE_TOTAL=$(grep -c '^- \[ \]' "$f" 2>/dev/null || echo 0)
  TOTAL=$((TOTAL + FILE_TOTAL))
  # Priority:high — max 5 per file
  HIGH=$(grep '^- \[ \].*priority:high' "$f" 2>/dev/null | head -5)
  # Остальные без priority:high — max 3 per file
  OTHER=$(grep '^- \[ \]' "$f" 2>/dev/null | grep -v 'priority:high' | head -3)
  PENDING=""
  [ -n "$HIGH" ] && PENDING+="$HIGH"$'\n'
  [ -n "$OTHER" ] && PENDING+="$OTHER"
  if [ -n "$PENDING" ]; then
    FILE_LABEL=$(echo "$f" | sed "s|$HOME/||")
    ALL_PENDING+=$'\n\n── '"$FILE_LABEL"' ('"$FILE_TOTAL"$' pending) ──\n'"$PENDING"
    N=$(echo "$PENDING" | grep -c '^- \[' || echo 0)
    COUNT=$((COUNT + N))
  fi
done

if [ "$COUNT" -eq 0 ]; then
  # Нет pending — тихо выйти
  echo '{}'
  exit 0
fi

# Генерим JSON с additionalContext (escape-safe через jq)
jq -n --arg pending "$ALL_PENDING" --arg count "$COUNT" --arg total "$TOTAL" '
{
  hookSpecificOutput: {
    hookEventName: "SessionStart",
    additionalContext: (
      "📋 **АКТИВНЫЕ TODO — top " + $count + " из " + $total + " pending (full list в TODO.md файлах):**\n" +
      $pending +
      "\n\n**ОБЯЗАТЕЛЬНЫЕ ШАГИ (enforced через SessionStart hook — НЕ полагаться на память):**\n" +
      "1. Для ВСЕХ задач с `[priority:high]` выше — СРАЗУ вызови TaskCreate (subject + description + relevant context).\n" +
      "2. Покажи пользователю меню перекрёстка (session-crossroads.md): 1 Комбайн / 2 Интервью / 3 Обзор / 4 Синк / 5 Фикс.\n" +
      "3. Жди выбор пользователя.\n\n" +
      "Полный список pending: `cat ~/artvision-data/TODO.md` и связанные файлы."
    )
  }
}
'
