#!/usr/bin/env bash
# gemini-rescue.sh — handoff wrapper для Gemini CLI с pre-flight checks.
# Аналог codex-companion.mjs, использует официальный @google/gemini-cli.
#
# Usage:
#   gemini-rescue.sh task "опиши задачу"                       # foreground, default model
#   gemini-rescue.sh task --model gemini-2.5-pro "..."         # выбор модели
#   gemini-rescue.sh task --plan "..."                         # read-only (approval-mode plan)
#   gemini-rescue.sh task --write "..."                        # auto-edit (approval-mode auto_edit)
#   gemini-rescue.sh task --yolo "..."                         # авто-всё (approval-mode yolo)
#   gemini-rescue.sh task --resume-last "..."                  # продолжить прошлую сессию
#   gemini-rescue.sh task --image /path/to/file.png "..."      # с картинкой (frontend handoff)
#
# Pre-flight checks:
#   1) gemini установлен
#   2) IP — не РФ (geo-блок Google Generative AI)
#   3) Auth настроен (OAuth Code Assist ИЛИ GEMINI_API_KEY env)
#
# Output: stdout от gemini -p, stderr — preflight ошибки

set -euo pipefail

# === pre-flight ===

if ! command -v gemini >/dev/null 2>&1; then
  echo "[gemini-rescue] FATAL: gemini CLI not found. Install: npm i -g @google/gemini-cli" >&2
  exit 127
fi

# Проверка geo (Google API блокирует РФ)
COUNTRY=$(curl -s --max-time 5 https://ifconfig.co/country-iso 2>/dev/null || echo "UNKNOWN")
if [ "$COUNTRY" = "RU" ]; then
  echo "[gemini-rescue] FATAL: IP в РФ ($COUNTRY). Google Generative AI geo-блок." >&2
  echo "[gemini-rescue]        Включи VPN (Mullvad/AmneziaVPN/Wireguard) или используй OpenRouter route." >&2
  echo "[gemini-rescue]        Setup: ~/.claude/docs/gemini-vpn-setup.md" >&2
  exit 2
fi

# Auth check: либо OAuth (~/.gemini/oauth_creds.json), либо GEMINI_API_KEY env, либо ключ в tokens.json
if [ -z "${GEMINI_API_KEY:-}" ] && [ ! -f "$HOME/.gemini/oauth_creds.json" ]; then
  # Попробовать подгрузить из tokens.json
  TOKEN=$(python3 -c "import json; print(json.load(open('/Users/antonk/artvision-data/tokens.json'))['gemini']['api_key'])" 2>/dev/null || true)
  if [ -n "$TOKEN" ]; then
    export GEMINI_API_KEY="$TOKEN"
  else
    echo "[gemini-rescue] FATAL: No auth. Run 'gemini' interactively → OAuth flow." >&2
    echo "[gemini-rescue]        OR set GEMINI_API_KEY env / add 'gemini.api_key' to tokens.json" >&2
    exit 3
  fi
fi

# === argv parsing ===

if [ "${1:-}" != "task" ]; then
  echo "[gemini-rescue] Usage: $0 task [--model X] [--plan|--write|--yolo] [--resume-last] [--image PATH] \"prompt\"" >&2
  exit 64
fi
shift

MODEL=""
APPROVAL="default"
RESUME=""
IMAGES=()
PROMPT=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --model)        MODEL="$2"; shift 2 ;;
    --plan)         APPROVAL="plan"; shift ;;
    --write)        APPROVAL="auto_edit"; shift ;;
    --yolo)         APPROVAL="yolo"; shift ;;
    --resume-last)  RESUME="--resume latest"; shift ;;
    --image)        IMAGES+=("$2"); shift 2 ;;
    --)             shift; PROMPT="$*"; break ;;
    *)              PROMPT="$1"; shift ;;
  esac
done

if [ -z "$PROMPT" ]; then
  echo "[gemini-rescue] FATAL: empty prompt." >&2
  exit 64
fi

# === build gemini args ===

ARGS=("--skip-trust" "--approval-mode" "$APPROVAL" "-p" "$PROMPT")
[ -n "$MODEL" ] && ARGS+=("-m" "$MODEL")
[ -n "$RESUME" ] && ARGS+=($RESUME)

# Картинки добавляются через @file syntax в prompt (Gemini CLI понимает @path)
if [ "${#IMAGES[@]}" -gt 0 ]; then
  for img in "${IMAGES[@]}"; do
    PROMPT="$PROMPT @$img"
  done
  # Пересобрать args с обновлённым промптом
  ARGS=("--skip-trust" "--approval-mode" "$APPROVAL" "-p" "$PROMPT")
  [ -n "$MODEL" ] && ARGS+=("-m" "$MODEL")
  [ -n "$RESUME" ] && ARGS+=($RESUME)
fi

# === logging ===

LOG_DIR="$HOME/.claude/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/gemini-rescue.log"
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] model=${MODEL:-default} approval=$APPROVAL prompt_len=${#PROMPT}" >> "$LOG_FILE"

# === execute ===

exec gemini "${ARGS[@]}"
