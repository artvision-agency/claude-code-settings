#!/usr/bin/env bash
# pre-scp-kp-diff.sh — PreToolUse Bash
#
# Блокирует scp/rsync клиентского КП на VPS если в config.yaml клиента
# указан reference_kp, а визуальный diff vs этот reference не прогонялся
# в текущей сессии (или вернул verdict=BLOCK).
#
# Триггеры:
#   scp .* clients/<name>/.*kp.*\.html .* root@80.90.181.152:/var/www/.*kp/
#   rsync .* clients/<name>/.*kp.*\.html .* root@80.90.181.152:.*
#
# Bypass:
#   KP_DIFF_SKIP=1            (env per command)
#   touch /tmp/kp-diff-done-<session_id>  (per-session snooze)
#
# Source: kp-visual-diff skill — https://artvision-data/.claude/skills/kp-visual-diff/SKILL.md

set -uo pipefail

[[ "${KP_DIFF_SKIP:-0}" == "1" ]] && exit 0

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
[[ "$TOOL_NAME" != "Bash" ]] && exit 0

CMD=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)
[[ -z "$CMD" ]] && exit 0
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty' 2>/dev/null)
[[ -z "$SESSION_ID" ]] && exit 0

# Snooze
[[ -f "/tmp/kp-diff-done-${SESSION_ID}" ]] && exit 0

# Match scp/rsync of client KP HTML
if ! echo "$CMD" | grep -qE '(scp|rsync).*clients/[^/]+/.*\.html.*root@80\.90\.181\.152'; then
  exit 0
fi

# Extract client slug from path: clients/<slug>/...
CLIENT_PATH=$(echo "$CMD" | grep -oE 'clients/[^/]+/[^ ]*\.html' | head -1)
[[ -z "$CLIENT_PATH" ]] && exit 0

CLIENT_SLUG=$(echo "$CLIENT_PATH" | cut -d/ -f2)
ARTVISION_DATA="${ARTVISION_DATA:-$HOME/artvision-data}"
CONFIG_PATH="$ARTVISION_DATA/clients/${CLIENT_SLUG}/config.yaml"

# If no config.yaml or no reference_kp — skip (no reference to compare against)
[[ ! -f "$CONFIG_PATH" ]] && exit 0
REFERENCE_KP=$(grep -E '^reference_kp:' "$CONFIG_PATH" 2>/dev/null | sed -E 's/^reference_kp:[[:space:]]*//; s/^["'\''](.*)["'\'']$/\1/')
[[ -z "$REFERENCE_KP" ]] && exit 0

# Resolve reference path (relative to artvision-data root)
REFERENCE_FULL="$ARTVISION_DATA/$REFERENCE_KP"
[[ ! -f "$REFERENCE_FULL" ]] && {
  cat <<EOF
⚠️ pre-scp-kp-diff: reference_kp указан в config.yaml, но файл не найден
   config: $CONFIG_PATH
   reference_kp: $REFERENCE_KP (resolved: $REFERENCE_FULL)
   → Проверь путь или удали reference_kp из config.yaml
EOF
  exit 2
}

# Check if visual diff was run in this session
TRANSCRIPT="$HOME/.claude/projects/-Users-antonk/${SESSION_ID}.jsonl"
DIFF_OK=0
if [[ -f "$TRANSCRIPT" ]]; then
  if grep -qE 'kp-visual-diff\.py|"skill":[[:space:]]*"kp-visual-diff"' "$TRANSCRIPT" 2>/dev/null; then
    DIFF_OK=1
  fi
fi

if [[ $DIFF_OK -eq 0 ]]; then
  TARGET_FULL="$ARTVISION_DATA/$CLIENT_PATH"
  cat <<EOF
🛑 pre-scp-kp-diff: ЗАБЛОКИРОВАНО

  Клиент: $CLIENT_SLUG
  Target: $TARGET_FULL
  Reference: $REFERENCE_FULL

  Перед deploy клиентского КП обязателен визуальный diff vs reference (skill kp-visual-diff).
  Это гарантирует что все элементы reference перенесены в target.

  Запусти:
    python3 $ARTVISION_DATA/scripts/kp-visual-diff.py \\
      --reference $REFERENCE_FULL \\
      --target $TARGET_FULL \\
      --output /tmp/kp-diff-${CLIENT_SLUG}

  После просмотра отчёта (и при verdict PASS/REVIEW) повторно запусти scp.

  Bypass (на свой риск): touch /tmp/kp-diff-done-${SESSION_ID} && <команда>
                          или: KP_DIFF_SKIP=1 <команда>

  Прецедент: АН-НУР 2026-05-05 — 3 итерации правок из-за пропущенных элементов starclinic.
EOF
  exit 2
fi

exit 0
