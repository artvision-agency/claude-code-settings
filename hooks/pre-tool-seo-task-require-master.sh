#!/usr/bin/env bash
# pre-tool-seo-task-require-master.sh — блокирует SEO-операции пока не вызван /seo-master.
#
# Решает «adoption problem» (Codex GPT-5.4 review 09.05.2026):
# /seo-master вызван 4 раза из 83 КП за 3 мес = 4.8% adoption.
# Pipeline-enforcer бесполезен если entrypoint не используется.
#
# Триггеры блокировки (SEO-related операции):
#   - Bash команды: sf, lhci, hybrid-seo-audit, seo-toolkit, topvisor*, wordstat*, screaming
#   - Edit/Write/MultiEdit в путь содержащий /seo/ или /linkbuilding/
#   - Edit/Write с file_path matching *seo*audit*.md или *audit-*.html
#
# Self-disable:
#   - после первого Skill seo-master в transcript (touch /tmp/seo-master-invoked-{session_id})
#   - если в transcript уже есть "skill":"seo-master"
#
# Bypass: SEO_MASTER_FORCE=1
#
# Exit codes:
#   0 = не SEO-задача / Skill seo-master уже был / bypass / whitelist
#   2 = блок (Claude увидит и должен вызвать Skill seo-master первым)

set -uo pipefail

# 0. Bypass
[ "${SEO_MASTER_FORCE:-0}" = "1" ] && exit 0

# 1. Read JSON stdin
INPUT="$(cat 2>/dev/null || true)"
[ -z "$INPUT" ] && exit 0

# 1b. Inline bypass — env-префикс в ТЕКСТЕ команды (env-var хука не видит env суб-команды).
#     Делает документированный `SEO_MASTER_FORCE=1 <операция>` реально рабочим
#     для main-процесса И субагентов (seo-specialist сам несёт весь pipeline).
#     Approve Антона 2026-06-08 («bypass»).
printf '%s' "$INPUT" | grep -q 'SEO_MASTER_FORCE=1' && exit 0

# 2. Parse session_id, tool_name, bash_command, file_path
PARSED=$(printf '%s' "$INPUT" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get("session_id", ""))
    print(d.get("tool_name", ""))
    ti = d.get("tool_input", {}) or {}
    print(ti.get("command", "") if d.get("tool_name") == "Bash" else "")
    print(ti.get("file_path", "") if d.get("tool_name") in ("Edit", "Write", "MultiEdit") else "")
except Exception:
    print(""); print(""); print(""); print("")
' 2>/dev/null || printf '\n\n\n\n')

SESSION_ID=$(printf '%s\n' "$PARSED" | sed -n '1p')
TOOL_NAME=$(printf '%s\n' "$PARSED" | sed -n '2p')
CMD=$(printf '%s\n' "$PARSED" | sed -n '3p')
FILE_PATH=$(printf '%s\n' "$PARSED" | sed -n '4p')

[ -z "$TOOL_NAME" ] && exit 0

# 3. Whitelist tool names (Skill — whitelisted, чтобы можно было вызвать seo-master)
case "$TOOL_NAME" in
  TaskCreate|TaskList|TaskGet|TaskUpdate|TaskOutput|TaskStop|\
  Read|Grep|Glob|\
  ToolSearch|Skill|ScheduleWakeup|AskUserQuestion|\
  EnterPlanMode|ExitPlanMode|\
  ListMcpResourcesTool|ReadMcpResourceTool)
    exit 0
    ;;
esac

# 4. Self-disable если sentinel-файл существует (быстрый путь)
if [ -n "$SESSION_ID" ] && [ -f "/tmp/seo-master-invoked-$SESSION_ID" ]; then
  exit 0
fi

# 5. Определить SEO-task ли это
IS_SEO_TASK=0

if [ "$TOOL_NAME" = "Bash" ] && [ -n "$CMD" ]; then
  # Первая команда (до пайпов/&&/;)
  FIRST=$(printf '%s' "$CMD" | sed -e 's/^[[:space:]]*//' | awk -F'[[:space:]|;&]' '{print $1}')
  case "$FIRST" in
    sf|lhci|screamingfrog|hybrid-seo-audit*|seo-toolkit*)
      IS_SEO_TASK=1 ;;
  esac
  # Скрипты SEO в команде
  if printf '%s' "$CMD" | grep -qE '(hybrid-seo-audit|seo-toolkit|screaming|lighthouse|wordstat_or_fallback|yandex_serp_collector|seo_position_monitor|aggregator_audit)\.py'; then
    IS_SEO_TASK=1
  fi
  # Topvisor / Wordstat API вызовы (через python с импортом)
  if printf '%s' "$CMD" | grep -qE 'api\.topvisor\.com|wordstat\.yandex|yandex\.com/?wordstat'; then
    IS_SEO_TASK=1
  fi
fi

if [ -n "$FILE_PATH" ]; then
  # Путь в seo/ или linkbuilding/ клиента
  if printf '%s' "$FILE_PATH" | grep -qE '/clients/[^/]+/(seo|linkbuilding)/'; then
    IS_SEO_TASK=1
  fi
  # SEO-аудит/отчёт по имени файла
  if printf '%s' "$FILE_PATH" | grep -qiE '(seo[_-]?audit|seo[_-]?report|technical[_-]?seo|audit-[0-9]{4}-[0-9]{2}-[0-9]{2})'; then
    IS_SEO_TASK=1
  fi
fi

# Не SEO — пропуск
[ "$IS_SEO_TASK" -eq 0 ] && exit 0

# 6. Проверка transcript на наличие Skill seo-master
if [ -n "$SESSION_ID" ]; then
  TRANSCRIPT=$(find "$HOME/.claude/projects" -maxdepth 3 -name "${SESSION_ID}.jsonl" 2>/dev/null | head -1)
  if [ -n "$TRANSCRIPT" ] && [ -f "$TRANSCRIPT" ]; then
    # Ищем оба варианта: "skill":"seo-master" и "name":"Skill" + потом seo-master
    if grep -qE '"skill"[[:space:]]*:[[:space:]]*"seo-master"' "$TRANSCRIPT" 2>/dev/null; then
      touch "/tmp/seo-master-invoked-$SESSION_ID" 2>/dev/null || true
      exit 0
    fi
  fi
fi

# 7. BLOCK
{
  echo ""
  echo "⛔ pre-tool-seo-task-require-master: ЗАБЛОКИРОВАНО"
  echo ""
  echo "Обнаружена SEO-задача без вызова Skill /seo-master."
  echo "Запрошенный инструмент: $TOOL_NAME"
  if [ -n "$CMD" ]; then
    echo "Команда: $(printf '%s' "$CMD" | head -c 100)..."
  fi
  if [ -n "$FILE_PATH" ]; then
    echo "Файл: $FILE_PATH"
  fi
  echo ""
  echo "ПОЧЕМУ: за 3 мес /seo-master вызван 4 раза из 83 КП (4.8% adoption)."
  echo "        SEO-аудиты выходят неполными без обязательного pipeline."
  echo ""
  echo "ДЕЙСТВИЕ:"
  echo "  1) Сначала вызови Skill tool с name='seo-master'"
  echo "  2) Skill даст 8-шаговый pipeline (sf + lighthouse + wordstat + topvisor + ...)"
  echo "  3) После Skill — продолжай работу, hook самораспустится"
  echo ""
  echo "Bypass (на свой риск): SEO_MASTER_FORCE=1 <операция>"
  echo "Прецедент: Codex GPT-5.4 review 09.05.2026 — workflow adoption problem"
} >&2

exit 2
