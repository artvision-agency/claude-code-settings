#!/usr/bin/env bash
# session-goals.sh — фиксация целей в начале сессии, сверка в конце (П/Ф)
# Использование:
#   session-goals.sh start "<цель1>" "<цель2>" ...   # вручную в начале
#   session-goals.sh add "<цель>"                    # добавить в текущую
#   session-goals.sh report                          # показать П/Ф (Stop hook)
#   session-goals.sh list                            # просто вывести
set -euo pipefail

STATE_DIR="$HOME/.claude/state/session-goals"
mkdir -p "$STATE_DIR"

# session_id из ENV (Claude Code прокидывает) или из cwd-хеша
SID="${CLAUDE_SESSION_ID:-$(echo -n "$PWD-$(date +%Y%m%d)" | shasum | cut -c1-8)}"
GOALS_FILE="$STATE_DIR/$SID.json"

cmd="${1:-list}"

case "$cmd" in
  start)
    shift
    python3 -c "
import json, sys, time
goals = [{'goal': g, 'done': False, 'ts': time.time()} for g in sys.argv[1:]]
json.dump({'session': '$SID', 'started': time.time(), 'goals': goals}, open('$GOALS_FILE','w'), ensure_ascii=False, indent=2)
print(f'[goals] {len(goals)} целей записано → $GOALS_FILE')
" "$@"
    ;;
  add)
    shift
    [ -f "$GOALS_FILE" ] || echo '{"goals":[]}' > "$GOALS_FILE"
    python3 -c "
import json, time
d = json.load(open('$GOALS_FILE'))
d.setdefault('goals',[]).append({'goal': '$1', 'done': False, 'ts': time.time()})
json.dump(d, open('$GOALS_FILE','w'), ensure_ascii=False, indent=2)
print(f'[goals] +1 цель ({len(d[\"goals\"])} всего)')
"
    ;;
  done)
    shift
    [ -f "$GOALS_FILE" ] || exit 0
    python3 -c "
import json, sys
d = json.load(open('$GOALS_FILE'))
needle = sys.argv[1].lower()
for g in d.get('goals',[]):
    if needle in g['goal'].lower():
        g['done'] = True
json.dump(d, open('$GOALS_FILE','w'), ensure_ascii=False, indent=2)
" "$1"
    ;;
  list|report)
    [ -f "$GOALS_FILE" ] || { [ "$cmd" = "report" ] && echo "[goals] нет целей этой сессии"; exit 0; }
    python3 << PYEOF
import json
d = json.load(open('$GOALS_FILE'))
goals = d.get('goals', [])
if not goals:
    print('[goals] пусто'); exit()
done = sum(1 for g in goals if g.get('done'))
print(f"═══ ПЛАН/ФАКТ — {done}/{len(goals)} ═══")
print(f"{'#':<3} {'Статус':<8} Цель")
for i, g in enumerate(goals, 1):
    s = '✅' if g.get('done') else '⏸'
    print(f"{i:<3} {s:<8} {g['goal']}")
print('═' * 40)
PYEOF
    ;;
  *)
    echo "Usage: $0 {start|add|done|list|report} [args]" >&2
    exit 1
    ;;
esac
