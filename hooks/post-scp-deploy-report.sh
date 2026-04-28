#!/bin/bash
# PostToolUse (Bash): триггерит deploy-report-template после scp клиентского документа
# Правило: ~/.claude/rules/deploy-report-template.md

COMMAND="${CLAUDE_BASH_COMMAND:-$1}"

# 1) Триггер: scp на artvision VPS ИЛИ ssh+deploy ИЛИ прямой curl upload
IS_DEPLOY=false
echo "$COMMAND" | grep -qE "scp.*(80\.90\.181\.152|artvision\.pro|root@)" && IS_DEPLOY=true
echo "$COMMAND" | grep -qE "rsync.*(80\.90\.181\.152|artvision\.pro)" && IS_DEPLOY=true

if [ "$IS_DEPLOY" != "true" ]; then exit 0; fi

# 2) Проверка что деплой КЛИЕНТСКИЙ (КП, лендинг, отчёт)
IS_CLIENT=false
echo "$COMMAND" | grep -qE "clients/|presale/|presales/|/kp/|kp_|_kp\.html|landing" && IS_CLIENT=true
# HTML без client-маркера — не триггерим (могут быть внутренние тесты)
[ "$IS_CLIENT" != "true" ] && exit 0

# 3) Проверка что это документ, не просто ассет (картинка/стиль без HTML)
IS_DOC=false
echo "$COMMAND" | grep -qE "\.html|\.pdf|index\.html|/$ |/\s" && IS_DOC=true
echo "$COMMAND" | grep -qE "^\s*scp\s+-r" && IS_DOC=true   # рекурсивный scp тоже считаем документом
[ "$IS_DOC" != "true" ] && exit 0

# 4) Извлечь имя клиента
CLIENT=$(echo "$COMMAND" | grep -oE "(clients|presale|presales)/[a-z0-9-]+" | head -1 | cut -d/ -f2)
[ -z "$CLIENT" ] && CLIENT=$(echo "$COMMAND" | grep -oE "/kp/[a-z0-9-]+" | head -1 | cut -d/ -f3)
[ -z "$CLIENT" ] && CLIENT="<unknown>"

# 5) Инжект напоминания в контекст (stdout попадает в транскрипт)
cat <<EOF
═══════════════════════════════════════════
📋 [DEPLOY-REPORT REQUIRED] Клиент: $CLIENT
═══════════════════════════════════════════
ОБЯЗАТЕЛЬНО после этого ответа — вывести Deploy Report по шаблону
~/.claude/rules/deploy-report-template.md:

  1. Шапка: документ, live URL, размер, версия
  2. Таблица из 15 пунктов (скилл /presale-kp, агенты, скрипты, хуки) ✅/❌/➖
  3. Блок «Что НЕ применялось и почему»
  4. Блок «Что стоит добавить перед отправкой клиенту»

Если /presale-kp НЕ вызывался — первой строкой в таблице
подсказка: «Для нового документа с нуля → /presale-kp <url>».

Флаг: /tmp/claude-deploy-report-needed-$CLIENT
═══════════════════════════════════════════
EOF

# 6) Создать флаг-файл для следующего UserPromptSubmit хука
echo "{\"client\":\"$CLIENT\",\"ts\":$(date +%s),\"cmd\":\"${COMMAND:0:200}\"}" > "/tmp/claude-deploy-report-needed-$CLIENT.json"

exit 0
