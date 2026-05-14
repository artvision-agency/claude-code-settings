#!/usr/bin/env bash
# run-action.sh — выполняет зарегистрированный action.
# Использование: run-action.sh <action_id>
#
# Поддержка двух типов action (поле action_type в YAML):
#   - bash             — прямое выполнение shell-команд (default для надёжности)
#   - claude_headless  — через `claude -p` (для задач требующих reasoning)
#
# Verification:
#   - exit code основной команды
#   - размер лога (если <300 bytes — warning, скорее всего ничего не сделалось)
#   - опциональное поле verify_command в YAML (bash, должен вернуть exit 0)
#
# История бага: 2026-05-13 — claude -p вернул exit 0 без реального выполнения
# destructive ssh-команд (видимо defensive mode без TTY). status=done был
# выставлен ложно. Теперь требуется verify-step.

set -euo pipefail

ACTION_ID="${1:?action_id required}"
ACTIONS_DIR="$HOME/artvision-data/actions"
YAML_PATH="$ACTIONS_DIR/${ACTION_ID}.yaml"
LOG_PATH="$ACTIONS_DIR/logs/${ACTION_ID}.log"

mkdir -p "$(dirname "$LOG_PATH")"

[[ ! -f "$YAML_PATH" ]] && { echo "ERROR: action $ACTION_ID не найден"; exit 1; }

STATUS=$(grep "^status:" "$YAML_PATH" | head -1 | awk '{print $2}')
if [[ "$STATUS" != "pending" ]]; then
    echo "ERROR: action $ACTION_ID имеет status=$STATUS (ожидался pending)"
    exit 1
fi

# Извлечь поля action_type, command_or_prompt, verify_command из YAML
read -r ACTION_TYPE PROMPT VERIFY < <(python3 << PYEOF
import yaml, json
with open('$YAML_PATH') as f:
    d = yaml.safe_load(f)
action_type = d.get('action_type', 'claude_headless')
prompt = (d.get('command_or_prompt') or '').strip()
verify = (d.get('verify_command') or '').strip()
# Передаём через base64 чтобы не сломать spaces/newlines
import base64
print(action_type,
      base64.b64encode(prompt.encode()).decode(),
      base64.b64encode(verify.encode()).decode())
PYEOF
)
PROMPT=$(echo "$PROMPT" | base64 -d)
VERIFY=$(echo "$VERIFY" | base64 -d)

if [[ -z "$PROMPT" ]]; then
    echo "ERROR: пустой command_or_prompt в $YAML_PATH"
    exit 1
fi

# Помечаем running
sed -i.bak 's/^status: pending$/status: running/' "$YAML_PATH"
rm -f "${YAML_PATH}.bak"
echo "started_at: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$YAML_PATH"
echo "action_type_used: $ACTION_TYPE" >> "$YAML_PATH"

# --- Выполнение ---
echo "[$(date '+%H:%M:%S')] === run-action.sh start ===" >> "$LOG_PATH"
echo "[$(date '+%H:%M:%S')] action_type=$ACTION_TYPE" >> "$LOG_PATH"
echo "[$(date '+%H:%M:%S')] prompt=${PROMPT:0:200}..." >> "$LOG_PATH"

LOG_SIZE_BEFORE=$(wc -c < "$LOG_PATH" | tr -d ' ')
EXEC_EXIT=0

case "$ACTION_TYPE" in
    bash)
        # Прямое выполнение bash (надёжно, deterministic)
        echo "[$(date '+%H:%M:%S')] === BASH START ===" >> "$LOG_PATH"
        bash -c "$PROMPT" >> "$LOG_PATH" 2>&1 || EXEC_EXIT=$?
        echo "[$(date '+%H:%M:%S')] === BASH END (exit=$EXEC_EXIT) ===" >> "$LOG_PATH"
        ;;
    claude_headless)
        # Через headless Claude (для reasoning задач)
        # Использую `command claude` чтобы обойти alias с --dangerously-skip-permissions
        # (alias может конфликтовать с headless mode)
        echo "[$(date '+%H:%M:%S')] === CLAUDE HEADLESS START ===" >> "$LOG_PATH"
        if ! command -v claude > /dev/null; then
            echo "ERROR: claude CLI not in PATH" >> "$LOG_PATH"
            EXEC_EXIT=127
        else
            # timeout 10 минут чтобы не висеть вечно
            (timeout 600 claude -p "$PROMPT" 2>&1 || EXEC_EXIT=$?) >> "$LOG_PATH"
        fi
        echo "[$(date '+%H:%M:%S')] === CLAUDE HEADLESS END (exit=$EXEC_EXIT) ===" >> "$LOG_PATH"
        ;;
    *)
        echo "ERROR: неизвестный action_type=$ACTION_TYPE (ожидалось bash или claude_headless)" >> "$LOG_PATH"
        EXEC_EXIT=2
        ;;
esac

LOG_SIZE_AFTER=$(wc -c < "$LOG_PATH" | tr -d ' ')
LOG_GROWTH=$((LOG_SIZE_AFTER - LOG_SIZE_BEFORE))
echo "[$(date '+%H:%M:%S')] log_growth=$LOG_GROWTH bytes" >> "$LOG_PATH"

# --- Verification ---
VERIFY_RESULT="skipped"
if [[ -n "$VERIFY" ]]; then
    echo "[$(date '+%H:%M:%S')] === VERIFY START ===" >> "$LOG_PATH"
    if bash -c "$VERIFY" >> "$LOG_PATH" 2>&1; then
        VERIFY_RESULT="passed"
    else
        VERIFY_RESULT="failed"
    fi
    echo "[$(date '+%H:%M:%S')] verify=$VERIFY_RESULT" >> "$LOG_PATH"
fi

# --- Решение о финальном статусе ---
# Считаем done только если:
#   - EXEC_EXIT == 0
#   - log вырос больше 300 байт (защита от headless-claude-no-op)
#   - verify прошёл (если был указан)
if [[ "$EXEC_EXIT" == "0" ]] && [[ "$LOG_GROWTH" -gt 300 ]] && [[ "$VERIFY_RESULT" != "failed" ]]; then
    FINAL_STATUS="done"
    ICON="✅"
elif [[ "$EXEC_EXIT" == "0" ]] && [[ "$LOG_GROWTH" -le 300 ]]; then
    # Headless вернул 0 но ничего не вывел = suspicious
    FINAL_STATUS="suspicious"
    ICON="⚠️"
else
    FINAL_STATUS="failed"
    ICON="❌"
fi

sed -i.bak "s/^status: running$/status: ${FINAL_STATUS}/" "$YAML_PATH"
rm -f "${YAML_PATH}.bak"
echo "finished_at: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$YAML_PATH"
echo "exec_exit: $EXEC_EXIT" >> "$YAML_PATH"
echo "log_growth_bytes: $LOG_GROWTH" >> "$YAML_PATH"
echo "verify_result: $VERIFY_RESULT" >> "$YAML_PATH"

# TG-нотификация (без markdown special chars в action_id чтоб не ломать parse)
SAFE_ID=$(echo "$ACTION_ID" | tr -d '`*_[]()~>#+=|{}.!')
RESULT_TAIL=$(tail -25 "$LOG_PATH" | head -c 2000 | tr -d '`*_~')

TG_TEXT="${ICON} Action ${SAFE_ID} — ${FINAL_STATUS}

exec_exit: ${EXEC_EXIT}
log_growth: ${LOG_GROWTH} bytes
verify: ${VERIFY_RESULT}

Хвост лога:
${RESULT_TAIL}

Полный лог: ${LOG_PATH}"

"$HOME/.claude/scripts/tg-send.sh" anton "$TG_TEXT" 2>&1 | tail -1 || echo "(tg-send failed)"

# Перемещаем в нужную папку
case "$FINAL_STATUS" in
    done) mv "$YAML_PATH" "$ACTIONS_DIR/completed/" 2>/dev/null || true ;;
    failed|suspicious) ;; # оставляем в actions/ для разбора
esac

echo "[$(date '+%H:%M:%S')] === FINAL: $FINAL_STATUS ===" >> "$LOG_PATH"

[[ "$FINAL_STATUS" == "done" ]] && exit 0 || exit 1
