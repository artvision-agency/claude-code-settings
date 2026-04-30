#!/usr/bin/env bash
# pre-bash-topvisor-guard.sh — PreToolUse(Bash) блокирует broadcast-триггеры Topvisor
# checker/go которые запускают съём по ВСЕМ проектам аккаунта.
#
# Прецедент: 2026-04-29 — ДВАЖДЫ за одну сессию случайно сжёг 100 RUB баланса
#   Антона, использовав фильтр `NOT_IN [0]` вместо `EQUALS [project_id]`.
#   Триггер прошёл по 9 чужим проектам (vlpco, dsk-home, stomatiko, otido и т.д.),
#   529 ключей × 1 регион ≈ 100 RUB сожжено вместо 6.6 RUB на наш проект.
#
# Bypass: TOPVISOR_BROADCAST_FORCE=1
#
# Exit codes: 0 = пропуск, 2 = блок

set -uo pipefail

# 0. Bypass
[ "${TOPVISOR_BROADCAST_FORCE:-0}" = "1" ] && exit 0

# 1. Read JSON stdin into variable
INPUT="$(cat 2>/dev/null || true)"
[ -z "$INPUT" ] && exit 0

# 2. Parse + validate в одном python вызове, передаём INPUT через переменную окружения
RESULT=$(INPUT="$INPUT" python3 - << 'PYEOF' 2>/dev/null
import os, sys, json, re

raw = os.environ.get("INPUT", "")
try:
    d = json.loads(raw)
except Exception:
    print("OK_NOT_JSON")
    sys.exit(0)

if d.get("tool_name") != "Bash":
    print("OK_NOT_BASH")
    sys.exit(0)

cmd = (d.get("tool_input") or {}).get("command", "") or ""
if not cmd:
    print("OK_EMPTY")
    sys.exit(0)

# Skip git operations (commit messages могут содержать 'checker/go' без вызова API)
cmd_first = cmd.lstrip().split(None, 1)[0] if cmd.strip() else ""
if cmd_first in ("git", "gh"):
    print("OK_GIT")
    sys.exit(0)
if cmd_first == "cd" and "git" in cmd:
    # cd <dir> && git commit ... — тоже git
    print("OK_GIT_CD")
    sys.exit(0)

# Только если касается checker/go (фактический API call: curl/python с http)
# и команда содержит api.topvisor.com (чтобы избежать false-positive на текстовые упоминания)
if "checker/go" not in cmd:
    print("OK_NO_CHECKER")
    sys.exit(0)
if "api.topvisor.com" not in cmd and "topvisor.com/v2" not in cmd:
    print("OK_NO_API_URL")
    sys.exit(0)

# 1. NOT_IN везде — broadcast
if re.search(r'"operator"\s*:\s*"NOT_IN"', cmd):
    print("DANGER:NOT_IN operator (broadcast по всем проектам аккаунта кроме списка)")
    sys.exit(0)

# 2. MATCH с % — regex match-all
if re.search(r'"operator"\s*:\s*"MATCH"', cmd) and "%" in cmd:
    print("DANGER:MATCH с '%' (regex match-all)")
    sys.exit(0)

# 3. EXISTS
if re.search(r'"operator"\s*:\s*"EXISTS"', cmd):
    print("DANGER:EXISTS operator (matches all)")
    sys.exit(0)

# 4. GREATER/LESS — range
if re.search(r'"operator"\s*:\s*"(GREATER|LESS|GREATER_OR_EQUAL|LESS_OR_EQUAL)"', cmd):
    print("DANGER:range operator GREATER/LESS (matches multiple projects)")
    sys.exit(0)

# 5. checker/go без EQUALS-фильтра вообще
if not re.search(r'"operator"\s*:\s*"EQUALS"', cmd):
    print("DANGER:checker/go без EQUALS-фильтра — запустит по всем проектам")
    sys.exit(0)

# 6. EQUALS [0] или EQUALS []
m = re.search(r'"operator"\s*:\s*"EQUALS"\s*,\s*"values"\s*:\s*\[([^\]]*)\]', cmd)
if m:
    raw_vals = m.group(1).strip()
    if not raw_vals:
        print("DANGER:EQUALS values=[] (пустой список)")
        sys.exit(0)
    try:
        vals = json.loads("[" + raw_vals + "]")
        if 0 in vals:
            print("DANGER:EQUALS [..0..] — id=0 не существует, потенциально match всё")
            sys.exit(0)
    except Exception:
        pass

print("OK")
PYEOF
)

case "$RESULT" in
  DANGER:*)
    REASON="${RESULT#DANGER:}"
    {
      echo ""
      echo "🚫 BLOCKED: Опасный trigger Topvisor checker/go."
      echo ""
      echo "   $REASON"
      echo ""
      echo "   Прецедент: 2026-04-29 — ДВАЖДЫ сжёг 100 RUB баланса Антона:"
      echo "   фильтр NOT_IN [0] запустил съём по 9 чужим проектам аккаунта"
      echo "   (vlpco, dsk-home, stomatiko, otido и т.д.), 529 ключей × ~0.19 RUB."
      echo ""
      echo "   БЕЗОПАСНЫЙ паттерн:"
      echo "     filters=[{\"name\":\"id\",\"operator\":\"EQUALS\",\"values\":[<один_PID>]}]"
      echo ""
      echo "   ОПАСНО (блокируется хуком):"
      echo "     - NOT_IN [<маленький список>]   (всё кроме списка)"
      echo "     - MATCH с '%'                    (regex match-all)"
      echo "     - EXISTS                         (любой)"
      echo "     - GREATER/LESS                   (диапазон)"
      echo "     - checker/go без EQUALS          (всё)"
      echo "     - EQUALS []                      (пустой)"
      echo "     - EQUALS [0, ...]                (id=0 не существует)"
      echo ""
      echo "   Bypass: TOPVISOR_BROADCAST_FORCE=1"
      echo ""
    } >&2
    exit 2
    ;;
  *)
    exit 0
    ;;
esac
