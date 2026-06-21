#!/usr/bin/env bash
# pre-bash-ppc-api-write-gate.sh
# PreToolUse(Bash): БЛОК API-write в кабинет Я.Директа без подтверждения Антона.
# Правило: ppc-excel-first-then-api.md (CONFIRM-гейт, как finance-gate). Антон 2026-06-21.
# Подтверждение Антона = запуск с PPC_API_OK=1 (как finance bypass).
# Блокирует ПИШУЩИЕ/создающие/включающие методы. НЕ трогает read (.get/AuctionBids) и suspend (выключение безопасно).
set -uo pipefail

# Антон подтвердил → bypass
[ "${PPC_API_OK:-0}" = "1" ] && exit 0

input=$(cat 2>/dev/null || true)
cmd=$(printf '%s' "$input" | python3 -c "import sys,json
try: print(json.load(sys.stdin).get('tool_input',{}).get('command',''))
except: print('')" 2>/dev/null || true)

[ -z "$cmd" ] && exit 0

# Пропустить текстовые/git утилиты (слова ads.add/keywordbids в тексте коммита/grep ≠ реальный API-вызов).
# Реальный API-write идёт через python/node/curl/скрипт, не через git/grep/echo.
firstword=$(printf '%s' "$cmd" | sed -E 's/^([[:space:]]*[A-Za-z_][A-Za-z0-9_]*=[^[:space:]]*[[:space:]]+)*//' | awk '{print $1}')
firstbase=$(basename "$firstword" 2>/dev/null || echo "$firstword")
case "$firstbase" in
  git|grep|rg|ack|egrep|fgrep|echo|printf|cat|ls|find|sed|awk|head|tail|wc|less|more|diff|jq|cp|mv|rm|chmod|mkdir|touch|tee) exit 0;;
esac

# API-write паттерны Я.Директа (создают/меняют/включают/тратят) + скрипты заливки
WRITE='ads\.(add|update|moderate)|campaigns\.(add|update|resume|unarchive)|adgroups\.(add|update)|keywordbids\.set|keywords\.add|bids\.set|adimages\.add|sitelinkssets\.add|vcards\.add|dynamictextadtargets\.add|upload[_-]?camp|uploadcamp|залив[кч]'

if printf '%s' "$cmd" | grep -qiE "$WRITE"; then
  # исключение: только-suspend/get (безопасно) — если в команде НЕТ пишущих, а есть suspend/get, пропустить
  cat >&2 <<'EOF'
⛔ pre-ppc-api-write-gate: ЗАБЛОКИРОВАНО

Обнаружено API-write действие в кабинет Я.Директа (создание/правка/включение кампаний/объявлений/ставок/баннеров).

Это финансовое/кабинетное действие (правило ppc-excel-first-then-api — CONFIRM-гейт, как с финансами):
  1. СНАЧАЛА запроси у Антона подтверждение: «собираюсь сделать X (что/куда/сколько) — подтверди».
  2. После явного «да» — повтори команду с маркером: PPC_API_OK=1 <команда>

Безопасные операции (НЕ требуют подтверждения, обходи если ложно сработало):
  • .get / keywordbids.get / AuctionBids (чтение)
  • campaigns.suspend (ВЫКЛЮЧЕНИЕ — не тратит)

Bypass (= подтверждение Антона): PPC_API_OK=1 <команда>
Правило: ~/.claude/rules-conditional/ppc-excel-first-then-api.md
EOF
  exit 2
fi

exit 0
