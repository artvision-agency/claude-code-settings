#!/bin/bash
# SessionStart: тихо подтягивает свежие memory + rules из artvision-data
# Гарантирует что на любом аккаунте/машине Claude видит последние feedback_*/trend_*/reference_* файлы.
# Идемпотентно: rsync делает no-op если ничего не поменялось.
#
# Связан с ~/.claude/scripts/sync-memory.sh — там вся логика git pull + rsync.
# Логика: pull только если есть apvision-data репо и сеть.

REPO="$HOME/artvision-data"
SYNC_SCRIPT="$HOME/.claude/scripts/sync-memory.sh"

[ ! -d "$REPO/.git" ] && exit 0
[ ! -x "$SYNC_SCRIPT" ] && exit 0

# Тихий pull с таймаутом 10s — не блокировать SessionStart если сеть тормозит
( "$SYNC_SCRIPT" pull >/dev/null 2>&1 ) &
PID=$!

# wait с таймаутом
for i in $(seq 1 10); do
    kill -0 $PID 2>/dev/null || break
    sleep 1
done

# Если ещё работает — отпускаем (не блокируем SessionStart)
kill -0 $PID 2>/dev/null && exit 0

# Если завершился — проверим успех
wait $PID 2>/dev/null
RC=$?
[ $RC -eq 0 ] && exit 0 || exit 0  # ошибки молча — не ломать старт сессии
