#!/usr/bin/env bash
# stop-deploy-url-check.sh — проверяет что deploy-ответ начинается с URL.
# Правило: ~/.claude/projects/-Users-antonk/memory/feedback_deploy_url_first.md
# Триггеры в последнем assistant message: "Live URL:", "scp ... :/var/www/",
# "Опубликовано", "https://artvision.pro/(kp|preview)/"
# Если URL найден но НЕ в первых 3 строках → exit 2 с напоминанием.
# Bypass: DEPLOY_URL_OK=1
#
# FAIL-CLOSED (правка 2026-05-30): сбой парса JSON / отсутствие python3 /
# отсутствие транскрипта при наличии session_id / краш парсера транскрипта =
# НЕ тихий exit 0, а видимый warn + exit 2 (enforcement сохраняется).
# Тихий exit 0 остаётся ТОЛЬКО для легитимного "нет деплоя" (валидно
# распарсили транскрипт, но deploy-маркеров нет — не каждый Stop это деплой).

[[ "${DEPLOY_URL_OK:-}" == "1" ]] && exit 0

# fail_closed <reason> — видимый warn, enforcement сохранён (exit 2).
# Используется когда мы НЕ СМОГЛИ проверить ответ (парс/зависимость/файл),
# а не когда проверка прошла и деплоя нет.
fail_closed() {
    cat >&2 <<EOF
⛔ deploy-url-check: проверка не выполнена (fail-closed)

Причина: $1

Хук НЕ смог проверить последний ответ на правило "URL первой строкой"
(feedback_deploy_url_first.md). Чтобы парс-сбой не пропускал enforcement
молча — стоп заблокирован. Проверь вручную что deploy-URL стоит первой
строкой ответа.

Bypass (если осознанно): DEPLOY_URL_OK=1
EOF
    exit 2
}

# Зависимость python3 обязательна для парса payload и транскрипта.
if ! command -v python3 >/dev/null 2>&1; then
    fail_closed "не найден python3 (обязательная зависимость для парса JSON/транскрипта)"
fi

# Stop hook input — JSON со stdin: {session_id, stop_hook_active, ...}
INPUT=$(cat 2>/dev/null || true)

# Пустой stdin — харнес всегда шлёт JSON; пусто = аномалия ввода → fail-closed.
if [[ -z "${INPUT//[[:space:]]/}" ]]; then
    fail_closed "пустой stdin (ожидался JSON payload от харнеса)"
fi

# Извлечь session_id. Различаем 3 исхода:
#   PARSE_FAIL   — JSON не распарсился (rc=2) → fail-closed
#   NO_SESSION   — валидный JSON, но session_id пуст/отсутствует (rc=3) → fail-closed (аномалия)
#   <id>         — успех (rc=0)
SESSION_ID=$(printf '%s' "$INPUT" | python3 -c '
import sys, json
try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(2)              # parse failure
sid = data.get("session_id", "")
if not isinstance(sid, str) or not sid.strip():
    sys.exit(3)              # valid JSON but no usable session_id
sys.stdout.write(sid.strip())
sys.exit(0)
')
RC=$?

if [[ $RC -eq 2 ]]; then
    fail_closed "не удалось распарсить JSON payload (malformed stdin)"
elif [[ $RC -eq 3 ]]; then
    fail_closed "в payload отсутствует session_id (валидный JSON, но нет id сессии)"
elif [[ $RC -ne 0 || -z "$SESSION_ID" ]]; then
    fail_closed "сбой извлечения session_id (python3 rc=$RC)"
fi

# Защита от path traversal в session_id (на всякий случай — id из payload).
case "$SESSION_ID" in
    */*|*..*) fail_closed "подозрительный session_id (содержит '/' или '..'): $SESSION_ID" ;;
esac

JSONL="$HOME/.claude/projects/-Users-antonk/$SESSION_ID.jsonl"

# Транскрипта нет, хотя session_id получен → не можем проверить → fail-closed.
# (Раньше тут был тихий exit 0 — парс-сбой проходил незаметно.)
if [[ ! -f "$JSONL" ]]; then
    fail_closed "не найден транскрипт сессии: $JSONL"
fi

# Парс транскрипта. Различаем:
#   PARSER_CRASH — сам парсер упал (rc!=0) → fail-closed
#   успех        — печатает последний assistant-text (может быть пустым, это ОК)
LAST_TEXT=$(python3 - "$JSONL" <<'PY'
import json, sys
path = sys.argv[1]
last = ""
try:
    with open(path, encoding='utf-8') as f:
        for line in f:
            try:
                ev = json.loads(line)
            except Exception:
                # битая строка транскрипта — пропускаем, это не крах парсера
                continue
            if ev.get("type") != "assistant":
                continue
            msg = ev.get("message", {})
            content = msg.get("content", [])
            if isinstance(content, list):
                for c in content:
                    if isinstance(c, dict) and c.get("type") == "text":
                        last = c.get("text", "")
            elif isinstance(content, str):
                last = content
except Exception as e:
    sys.stderr.write("transcript-parse-error: %s\n" % e)
    sys.exit(4)   # парсер не смог даже открыть/прочитать файл
sys.stdout.write(last)
sys.exit(0)
PY
)
PRC=$?

if [[ $PRC -ne 0 ]]; then
    fail_closed "сбой парсера транскрипта (python3 rc=$PRC): $JSONL"
fi

# С этого момента транскрипт распарсен УСПЕШНО.
# Пустой текст / отсутствие deploy-маркеров = легитимно "нет деплоя" → тихий exit 0.
[[ -z "$LAST_TEXT" ]] && exit 0

# Deploy маркеры
if ! printf '%s' "$LAST_TEXT" | grep -qE "(Live URL:|scp .* :/var/www/|Опубликовано|https://artvision\.pro/(kp|preview|orm))"; then
    exit 0
fi

# Извлечь URL artvision.pro
URL=$(printf '%s' "$LAST_TEXT" | grep -oE "https://artvision\.pro/[a-zA-Z0-9/_.-]+" | head -1)
[[ -z "$URL" ]] && exit 0

# Проверить присутствует ли URL в первых 3 строках
FIRST3=$(printf '%s' "$LAST_TEXT" | head -3)
if printf '%s' "$FIRST3" | grep -qF "$URL"; then
    exit 0
fi

cat >&2 <<EOF
⛔ deploy-url-check: URL не в первых 3 строках ответа

Правило: feedback_deploy_url_first.md
Антон смотрит только URL — он должен быть первой строкой.

Найденный URL: $URL

Перепиши ответ начиная с URL.

Bypass: DEPLOY_URL_OK=1 (если осознанно)
EOF
exit 2
