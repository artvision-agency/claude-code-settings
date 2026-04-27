#!/usr/bin/env bash
# session-menu.sh — единое меню перекрёстка для старта сессии Claude Code.
# Читает 5 TODO + Downloads + кэш Asana + /loop + последнюю локалку.
# Должен быть быстрым (<2s) — без сетевых вызовов кроме закэшированных.
#
# Output → stdout, отдаётся пользователю как часть SessionStart-контекста.

set -Eeuo pipefail

readonly HOME_DIR="${HOME}"
readonly OPS_TODO="${HOME_DIR}/artvision-data/TODO.md"
readonly BOT_TODO="${HOME_DIR}/artvision-tg-bot/TODO.md"
readonly INFRA_TODO="${HOME_DIR}/devops-agent/TODO.md"
readonly PRESALE_TODO="${HOME_DIR}/artvision-data/presale/TODO.md"
readonly PRODUCTS_TODO="${HOME_DIR}/artvision-data/products/TODO.md"
readonly DOWNLOADS="${HOME_DIR}/Downloads"
readonly LAST_SESSION_FILE="${HOME_DIR}/.claude/.last_local_session"
readonly OVERDUE_CACHE="${HOME_DIR}/.claude/state/asana-overdue.cache"
readonly LOOP_DIR="${HOME_DIR}/.claude/loops"
readonly SESSIONS_YAML="${HOME_DIR}/.claude/task-router/sessions.yaml"
readonly PROJECTS_MD="${HOME_DIR}/artvision-data/PROJECTS.md"
readonly CWD_NOW="$(pwd)"

# ─── Helpers ──────────────────────────────────────────────────────────────────

count_pending() {
  local f="$1"
  [[ -f "$f" ]] || { echo 0; return; }
  grep -c '^- \[ \]' "$f" 2>/dev/null | tr -d ' \n' || echo 0
}

count_high() {
  local f="$1"
  [[ -f "$f" ]] || { echo 0; return; }
  grep -c '^- \[ \].*priority:high' "$f" 2>/dev/null | tr -d ' \n' || echo 0
}

top_high() {
  # Выводит N задач: сперва priority:high, добивает обычными до N. Можно передать несколько файлов.
  local n="${1:-3}"; shift
  local files=("$@")
  {
    for f in "${files[@]}"; do
      [[ -f "$f" ]] || continue
      grep '^- \[ \].*priority:high' "$f" 2>/dev/null || true
    done
    for f in "${files[@]}"; do
      [[ -f "$f" ]] || continue
      grep '^- \[ \]' "$f" 2>/dev/null | grep -v 'priority:high' || true
    done
  } | head -n "$n" \
    | sed -E 's/^- \[ \] //; s/\*\*//g; s/\[[a-z-]+:[^]]+\]//g; s/  +/ /g; s/[[:space:]]+$//'
}

session_name_for_cwd() {
  [[ -f "$SESSIONS_YAML" ]] || { echo ""; return; }
  python3 - "$SESSIONS_YAML" "$CWD_NOW" <<'PY' 2>/dev/null || echo ""
import sys
try:
    import yaml
except ImportError:
    sys.exit(0)
cfg_path, cwd = sys.argv[1], sys.argv[2]
try:
    with open(cfg_path) as f:
        cfg = yaml.safe_load(f) or {}
except Exception:
    sys.exit(0)
for name, sess in (cfg.get("sessions") or {}).items():
    if (sess or {}).get("cwd", "") == cwd:
        print(name)
        break
PY
}

human_ago() {
  local ts="$1"
  [[ -z "$ts" ]] && { echo "?"; return; }
  local now last diff h m
  now=$(date +%s)
  last=$(date -j -f "%Y-%m-%dT%H:%M:%S" "$ts" "+%s" 2>/dev/null || echo "$now")
  diff=$((now - last))
  if   (( diff < 3600 )); then echo "$((diff/60))m назад"
  elif (( diff < 86400 )); then echo "$((diff/3600))ч назад"
  else echo "$((diff/86400))д назад"
  fi
}

# ─── Сбор данных ──────────────────────────────────────────────────────────────

OPS_N=$(count_pending "$OPS_TODO")
BOT_N=$(count_pending "$BOT_TODO")
INFRA_N=$(count_pending "$INFRA_TODO")
PRESALE_N=$(count_pending "$PRESALE_TODO")
PRODUCTS_N=$(count_pending "$PRODUCTS_TODO")
TOTAL_N=$((OPS_N + BOT_N + INFRA_N + PRESALE_N + PRODUCTS_N))

OPS_H=$(count_high "$OPS_TODO")
BOT_H=$(count_high "$BOT_TODO")
INFRA_H=$(count_high "$INFRA_TODO")
PRESALE_H=$(count_high "$PRESALE_TODO")
PRODUCTS_H=$(count_high "$PRODUCTS_TODO")
TOTAL_H=$((OPS_H + BOT_H + INFRA_H + PRESALE_H + PRODUCTS_H))

# Артефакты Downloads (HTML/MD <72ч, отсутствующие в clients/)
ARTIFACTS=()
if [[ -d "$DOWNLOADS" ]]; then
  while IFS= read -r f; do
    base=$(basename "$f")
    if ! find "$HOME_DIR/artvision-data/clients" -name "$base" -print -quit 2>/dev/null | grep -q .; then
      ARTIFACTS+=("$base")
    fi
  done < <(find "$DOWNLOADS" -maxdepth 1 \( -name "*.html" -o -name "*.md" \) -mtime -3 2>/dev/null)
fi
ARTIFACTS_N=${#ARTIFACTS[@]}

# Asana overdue (из кэша если есть, иначе 0)
OVERDUE_N=0
if [[ -f "$OVERDUE_CACHE" ]]; then
  OVERDUE_N=$(wc -l < "$OVERDUE_CACHE" 2>/dev/null | tr -d ' ')
fi

# Активные /loop (если есть директория)
LOOPS_N=0
if [[ -d "$LOOP_DIR" ]]; then
  LOOPS_N=$(find "$LOOP_DIR" -maxdepth 1 -name "*.json" 2>/dev/null | wc -l | tr -d ' ')
fi

# Последняя локальная сессия
LAST_TS=""
[[ -f "$LAST_SESSION_FILE" ]] && LAST_TS=$(cat "$LAST_SESSION_FILE")
LAST_AGO=$(human_ago "$LAST_TS")

# Контекст по cwd. Используем общую логику todo-route.sh (через case ниже),
# дополненную явными ветками presale/products. cwd=$HOME → CTX="—" (нейтральная
# сессия, без императивной фильтрации — Антон сам выберет через cc-name).
SESSION_NAME=$(session_name_for_cwd)
case "$CWD_NOW" in
  "$HOME_DIR/artvision-data/presale"|"$HOME_DIR/artvision-data/presale/"*)
    CTX="presale"; CTX_TODO="$PRESALE_TODO"; CTX_N=$PRESALE_N; CTX_H=$PRESALE_H ;;
  "$HOME_DIR/artvision-data/products"|"$HOME_DIR/artvision-data/products/"*)
    CTX="products"; CTX_TODO="$PRODUCTS_TODO"; CTX_N=$PRODUCTS_N; CTX_H=$PRODUCTS_H ;;
  "$HOME_DIR/artvision-data"|"$HOME_DIR/artvision-data/"*)
    CTX="ops"; CTX_TODO="$OPS_TODO"; CTX_N=$OPS_N; CTX_H=$OPS_H ;;
  "$HOME_DIR/artvision-tg-bot"|"$HOME_DIR/artvision-tg-bot/"*)
    CTX="bot"; CTX_TODO="$BOT_TODO"; CTX_N=$BOT_N; CTX_H=$BOT_H ;;
  "$HOME_DIR/devops-agent"|"$HOME_DIR/devops-agent/"*)
    CTX="infra"; CTX_TODO="$INFRA_TODO"; CTX_N=$INFRA_N; CTX_H=$INFRA_H ;;
  *)
    CTX="—"; CTX_TODO=""; CTX_N=0; CTX_H=0 ;;
esac

# ─── Вывод меню ───────────────────────────────────────────────────────────────

DATE=$(date "+%Y-%m-%d %H:%M")

echo ""
echo "═══════════════════════════════════════════"
if [[ -n "$SESSION_NAME" ]]; then
  echo "  ${SESSION_NAME} — ${DATE}"
else
  echo "  Сессия без имени — ${DATE}"
  echo "  → cc-name <bot-dev|artvision-ops|infra>"
fi
echo "  cwd: ${CWD_NOW/$HOME_DIR/~}  |  контекст: ${CTX}"
echo "  Последняя локалка: ${LAST_AGO}"
echo "═══════════════════════════════════════════"
echo ""
# Если контекст определён — показываем счётчик ТОЛЬКО его. Сводка 5 контекстов
# имеет смысл только в нейтральной сессии (cwd=$HOME).
if [[ "$CTX" != "—" ]]; then
  echo "  📊 Очередь (${CTX}): ${CTX_N} задач (${CTX_H} high)"
else
  echo "  📊 Очередь (все контексты): ${TOTAL_N} задач (${TOTAL_H} high)"
  printf "     ops:%s  bot:%s  infra:%s  presale:%s  products:%s\n" \
    "$OPS_N" "$BOT_N" "$INFRA_N" "$PRESALE_N" "$PRODUCTS_N"
fi
echo ""

if (( OVERDUE_N > 0 )); then
  echo "  ⚠️  Asana overdue: ${OVERDUE_N}"
fi
if (( ARTIFACTS_N > 0 )); then
  echo "  📥 Downloads (не в git): ${ARTIFACTS_N} → /save-from-chat"
  for a in "${ARTIFACTS[@]:0:3}"; do
    echo "     · $a"
  done
fi
if (( LOOPS_N > 0 )); then
  echo "  🔄 Активных /loop: ${LOOPS_N}"
fi

# Топ-3: high из текущего контекста, либо из всех 5 если cwd=~/
echo ""
if [[ -n "$CTX_TODO" ]]; then
  echo "  🎯 Top (${CTX}):"
  TOP=$(top_high 3 "$CTX_TODO")
else
  echo "  🎯 Top high (все контексты):"
  TOP=$(top_high 3 "$OPS_TODO" "$BOT_TODO" "$INFRA_TODO" "$PRESALE_TODO" "$PRODUCTS_TODO")
fi
if [[ -n "$TOP" ]]; then
  while IFS= read -r line; do
    [[ -n "$line" ]] && echo "     · ${line:0:80}"
  done <<< "$TOP"
else
  echo "     (пусто)"
fi

cat <<'MENU'

═══════════════════════════════════════════
  1. 🎯 КОМБАЙН    — выполнить очередь (top high первыми)
  2. 💬 ИНТЕРВЬЮ   — новая задача → разобью → в очередь
  3. 📋 ОБЗОР      — все TODO + Asana + статусы
  4. 🔄 СИНК       — git pull/push + memory + Asana
  5. ⚡ ФИКС       — одна мелочь сразу, мимо очереди
  6. ⏯  ПРОДОЛЖИТЬ — resume последней сессии этого контекста
═══════════════════════════════════════════
  Цифра, ключевое слово, или текст задачи
═══════════════════════════════════════════

MENU
