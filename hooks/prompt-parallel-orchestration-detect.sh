#!/bin/bash
# UserPromptSubmit hook: детект многозадачного запроса → авто-напоминание о параллельной оркестрации.
# Антон 29.05: «я вообще не хочу ПРОСИТЬ про todo-лист» — параллель должна включаться сама.
# Правило: ~/.claude/rules/parallel-task-orchestration.md
# БЕЗОПАСНО: только инжект текста в stdout, exit 0 всегда, никогда не блокирует.

set +e
INPUT=$(cat 2>/dev/null)
PROMPT=$(echo "$INPUT" | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("prompt",""))
except: print("")' 2>/dev/null)

# bypass
[ "${PARALLEL_ORCH_OFF:-0}" = "1" ] && exit 0

# короткие/подтверждающие промпты — пропускаем (го/да/пуш/ок и т.п.)
words=$(echo "$PROMPT" | wc -w | tr -d ' ')
[ "$words" -lt 6 ] && exit 0

# self-disable на сессию: один раз за сессию (маркер по дате+часу)
MARK="/tmp/parallel-orch-nudged-$(date +%Y%m%d-%H)"
[ -f "$MARK" ] && exit 0

# детект многозадачности: нумерованный список ИЛИ 3+ глаголов действия ИЛИ «параллельно/рой/несколько»
multi=0
echo "$PROMPT" | grep -qE '(^|[^0-9])[1-3][.)],?\s' && multi=1
echo "$PROMPT" | grep -qiE 'параллел|рой|swarm|одновременно|несколько задач|и .* и .* и ' && multi=1
# 3+ командных глаголов через запятую/и
verbs=$(echo "$PROMPT" | grep -oiE 'сделай|создай|проверь|запусти|форкни|собери|напиши|найди|деплой|отправь|добавь|настрой|почини' | wc -l | tr -d ' ')
[ "$verbs" -ge 3 ] && multi=1

[ "$multi" = "0" ] && exit 0

touch "$MARK" 2>/dev/null
cat <<'EOF'
[PARALLEL-ORCHESTRATION] Запрос выглядит многозадачным. По правилу parallel-task-orchestration.md:
1. TaskCreate на каждую подзадачу (видимый трекер)
2. Анализ зависимостей — независимые vs цепочка (addBlockedBy)
3. Независимые → Agent(run_in_background:true) РОЕМ в одном сообщении, авто-подбор сеньора по agent-roster.md (макс 3-4, только Opus)
4. Зависимые → по готовности
НЕ выполнять последовательно если задачи независимы. Bypass: PARALLEL_ORCH_OFF=1
EOF
exit 0
