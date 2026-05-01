#!/usr/bin/env bash
# UserPromptSubmit hook — детект призыва к действию.
# Когда пользователь говорит «срочно надо делать / сделай / поставь задачу / в асану / залей / опубликуй»,
# инжектит напоминание Claude:
#   1) сначала проверить на сайте/в репо — не сделано ли уже (verify_on_real_site)
#   2) если задача реальна — создать в Asana по правилу asana-required-fields.md
#      (assignee + due_on + project_id; если не хватает — создать с тем что есть и попросить дозаполнить)
#
# Анти-триггеры: если в том же сообщении есть «не надо», «уже сделано», «отмени», «вопрос», «просто посмотри» —
# хук молчит.
#
# Self-disable: 1 раз в N=3 prompt'а, чтобы не спамить (lockfile с TTL).

set -uo pipefail

input="$(cat || true)"

prompt=$(printf '%s' "$input" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('prompt','') or d.get('user_message',''))" 2>/dev/null || echo "")
[ -z "$prompt" ] && exit 0

# Lowercase для русского и английского. Используем python — tr не справится с кириллицей.
p=$(printf '%s' "$prompt" | python3 -c "import sys; print(sys.stdin.read().lower())" 2>/dev/null || echo "")

# Анти-триггеры — в этом случае выходим тихо
if printf '%s' "$p" | grep -qE 'не[[:space:]]+надо|не[[:space:]]+делай|уже[[:space:]]+сделан|отмен[яи]|просто[[:space:]]+посмотри|вопрос:|просто[[:space:]]+узна'; then
    exit 0
fi

# Триггеры призыва к действию (русский + английский)
TRIGGERS='срочно[[:space:]]+(надо|нужно|сделай|делаем|делать)'
TRIGGERS+='|поставь[[:space:]]+задач'
TRIGGERS+='|задач[уа][[:space:]]+асан'
TRIGGERS+='|в[[:space:]]+асану|на[[:space:]]+асан'
TRIGGERS+='|сделай[[:space:]]+срочно'
TRIGGERS+='|зал[её]й|опубликуй|размести[[:space:]]+на'
TRIGGERS+='|приоритетн|надо[[:space:]]+делать|нужно[[:space:]]+сделать'
TRIGGERS+='|deploy[[:space:]]+(now|asap)|let.s[[:space:]]+(implement|build|deploy)|do[[:space:]]+it[[:space:]]+now'

if ! printf '%s' "$p" | grep -qE "$TRIGGERS"; then
    exit 0
fi

# Throttle: не больше 1 раза в 3 prompt'а на сессию
session_id=$(printf '%s' "$input" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('session_id',''))" 2>/dev/null || echo "")
[ -z "$session_id" ] && session_id="unknown"

flagdir="/tmp/asana-action-detect"
mkdir -p "$flagdir"
flag="${flagdir}/${session_id}.count"
count=0
if [ -f "$flag" ]; then
    count=$(cat "$flag" 2>/dev/null || echo 0)
fi
count=$((count + 1))
echo "$count" > "$flag"

# Срабатывает на 1, 4, 7... (раз в 3 turn'а)
remainder=$(( (count - 1) % 3 ))
if [ "$remainder" -ne 0 ]; then
    exit 0
fi

cat <<'EOF'
🔔 [action-call-detected] В запросе есть призыв к выполнению задачи (срочно/сделай/поставь/в асану/залей/опубликуй).

Протокол ДО исполнения:
1. **Иди на сайт/репо/живой проект** и проверь — не сделано ли уже.
   Правило: `feedback_verify_on_real_site.md`. Sitemap, ld+json, curl карточки — это факт. TODO/git — план.
   Если уже сделано → НЕ создавать задачу в Asana, сообщить факт + URL/доказательство.

2. **Если задача реальна** — создать в Asana по `asana-required-fields.md`:
   - assignee + due_on + project_id обязательны.
   - Если хватает контекста (упомянут клиент, дедлайн, исполнитель ЯВНО указан в тексте) — создать молча, отчёт одной строкой: «Asana: <name> → <assignee>, due <date>, GID <gid>».
   - **ЗАПРЕТ:** НЕ назначать assignee автоматически (из default'ов, по типу задачи, по клиенту). Только явное указание пользователем. Без assignee — создать задачу и спросить: «Кто исполнитель?»
   - Если не хватает — создать с тем что есть + ОТДЕЛЬНЫМ блоком запросить дозаполнить (1–3 коротких пункта).

3. **Никогда** не отправлять клиенту напрямую (`feedback_no_direct_client_communication.md`). Только драфт → файл/ответ → Антон/Андрей отправляет.

Этот hook напоминает 1 раз в 3 prompt'а с триггером, чтобы не спамить.
EOF

exit 0
