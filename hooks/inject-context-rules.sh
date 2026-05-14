#!/usr/bin/env bash
# inject-context-rules.sh — SessionStart + PreToolUse(Edit|Write)
#
# Path-binding для rules: читает frontmatter conditional rules (`paths:`)
# и инжектит содержимое только когда текущий cwd / file_path матчит.
#
# Источник идеи: статья Хабр https://habr.com/ru/articles/1033416/ (CLAUDE COWORK)
# пункт 5 — «.claude/rules/ с YAML paths для активации только нужных».
#
# Поиск conditional rules в:
#   ~/.claude/rules-conditional/
#   ~/artvision-data/.claude/rules-conditional/
#
# Формат frontmatter в каждом rule:
#   ---
#   name: medical-kp
#   paths:
#     - 'clients/<med>/**'
#     - 'presales/<med>/**'
#   always: false       # если true — грузить всегда
#   size_tokens: 5000   # для бюджета (информационно)
#   ---
#
# Output: JSON с hookSpecificOutput.additionalContext (для SessionStart)
#         или просто stdout с текстом system-reminder (для PreToolUse).
#
# Bypass:
#   INJECT_CONTEXT_RULES_OFF=1 — полностью выключить
#   INJECT_CONTEXT_RULES_DEBUG=1 — записать debug в /tmp/inject-rules.log
#
# Self-dedup: для каждой сессии файл /tmp/injected-rules-<session_id>
# хранит уже-инжектированные rule names — не дублируем в одной сессии.

set -uo pipefail

[ "${INJECT_CONTEXT_RULES_OFF:-0}" = "1" ] && exit 0

LOG="/tmp/inject-rules.log"
debug() {
  [ "${INJECT_CONTEXT_RULES_DEBUG:-0}" = "1" ] && echo "[$(date '+%H:%M:%S')] $*" >> "$LOG"
}

INPUT="$(cat 2>/dev/null || true)"
[ -z "$INPUT" ] && exit 0

# Parse: session_id, hook_event_name, cwd, tool_name, file_path
PARSED=$(printf '%s' "$INPUT" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get("session_id", ""))
    print(d.get("hook_event_name", ""))
    print(d.get("cwd", ""))
    print(d.get("tool_name", ""))
    ti = d.get("tool_input", {}) or {}
    print(ti.get("file_path", "") if d.get("tool_name") in ("Edit","Write","MultiEdit","Read") else "")
except Exception as e:
    print(""); print(""); print(""); print(""); print("")
' 2>/dev/null || printf '\n\n\n\n\n')

SESSION_ID=$(printf '%s\n' "$PARSED" | sed -n '1p')
EVENT=$(printf '%s\n' "$PARSED" | sed -n '2p')
CWD=$(printf '%s\n' "$PARSED" | sed -n '3p')
TOOL=$(printf '%s\n' "$PARSED" | sed -n '4p')
FILE_PATH=$(printf '%s\n' "$PARSED" | sed -n '5p')

debug "EVENT=$EVENT TOOL=$TOOL CWD=$CWD FILE=$FILE_PATH SESSION=$SESSION_ID"

# Контекстная цель для матчинга — приоритет file_path, fallback cwd
TARGET="${FILE_PATH:-$CWD}"
[ -z "$TARGET" ] && exit 0

# Состояние инжекта — что уже было загружено в эту сессию
STATE_FILE=""
if [ -n "$SESSION_ID" ]; then
  STATE_FILE="/tmp/injected-rules-${SESSION_ID}"
  touch "$STATE_FILE" 2>/dev/null || STATE_FILE=""
fi

# Папки с conditional rules
DIRS=(
  "$HOME/.claude/rules-conditional"
  "$HOME/artvision-data/.claude/rules-conditional"
)

# Найти все rule-файлы
RULE_FILES=()
for d in "${DIRS[@]}"; do
  [ ! -d "$d" ] && continue
  while IFS= read -r f; do
    RULE_FILES+=("$f")
  done < <(find "$d" -maxdepth 1 -type f -name '*.md' 2>/dev/null)
done

[ ${#RULE_FILES[@]} -eq 0 ] && { debug "no conditional rules found"; exit 0; }
debug "found ${#RULE_FILES[@]} conditional rules"

# Для каждого rule — проверить match через python (yaml frontmatter + fnmatch)
MATCHED=$(printf '%s\n' "${RULE_FILES[@]}" | python3 -c "
import sys, fnmatch, os, re

target = '''$TARGET'''
state_file = '''$STATE_FILE'''
already = set()
if state_file and os.path.exists(state_file):
    with open(state_file) as f:
        already = set(l.strip() for l in f if l.strip())

def parse_frontmatter(text):
    if not text.startswith('---'):
        return None, text
    end = text.find('\n---', 4)
    if end == -1:
        return None, text
    fm_raw = text[4:end]
    body = text[end+5:].lstrip('\n')
    # naive YAML parse for paths: / always: / name: / size_tokens:
    data = {'paths': [], 'always': False, 'name': '', 'size_tokens': 0}
    in_paths = False
    for line in fm_raw.split('\n'):
        s = line.rstrip()
        if s.startswith('paths:'):
            in_paths = True
            continue
        if in_paths:
            # Пропустить комментарии и пустые строки внутри paths-блока
            stripped = s.lstrip()
            if not stripped or stripped.startswith('#'):
                continue
            m = re.match(r\"^\s+-\s+['\\\"]?([^'\\\"]+)['\\\"]?\s*$\", s)
            if m:
                data['paths'].append(m.group(1))
                continue
            # Если строка не начинается с отступа+'-' и не комментарий — выходим из paths
            if not s.startswith(' ') and not s.startswith('\t'):
                in_paths = False
        m = re.match(r'^name:\s*(.+)$', s)
        if m: data['name'] = m.group(1).strip()
        m = re.match(r'^always:\s*(true|false)$', s)
        if m: data['always'] = (m.group(1) == 'true')
        m = re.match(r'^size_tokens:\s*(\d+)$', s)
        if m: data['size_tokens'] = int(m.group(1))
    return data, body

def path_match(target, patterns):
    # match если target содержит pattern (glob)
    norm = target.replace(os.path.expanduser('~/artvision-data/'), '')
    norm = norm.replace(os.path.expanduser('~/'), '')
    for p in patterns:
        if fnmatch.fnmatch(norm, p) or fnmatch.fnmatch(target, p):
            return True
        # Дополнительно — substring match (если pattern базовая часть пути)
        clean = p.replace('**', '').rstrip('/').rstrip('*')
        if clean and clean in target:
            return True
    return False

matched_names = []
matched_files = []
for line in sys.stdin:
    fp = line.strip()
    if not fp: continue
    try:
        with open(fp) as f:
            text = f.read()
    except: continue
    fm, body = parse_frontmatter(text)
    if not fm: continue
    name = fm['name'] or os.path.basename(fp).replace('.md','')
    if name in already:
        continue
    if fm['always'] or path_match(target, fm['paths']):
        matched_names.append(name)
        matched_files.append(fp)

# Append to state file
if state_file:
    with open(state_file, 'a') as f:
        for n in matched_names:
            f.write(n + '\n')

# Output: names joined by space, then files joined by newlines, separated by ---
print(' '.join(matched_names))
print('---FILES---')
for fp in matched_files:
    print(fp)
" 2>>"$LOG")

NAMES=$(echo "$MATCHED" | sed -n '1p')
[ -z "$NAMES" ] && { debug "no matches for target=$TARGET"; exit 0; }

# Извлечь список файлов
FILES=$(echo "$MATCHED" | awk '/---FILES---/{flag=1; next} flag')

debug "matched: $NAMES"

# Собрать контент всех matched rules
CONTENT=""
while IFS= read -r fp; do
  [ -z "$fp" ] && continue
  CONTENT="${CONTENT}

## [conditional rule] $(basename "$fp" .md)
$(cat "$fp")
"
done <<< "$FILES"

# Wrap в system-reminder-like
ADDITIONAL=$(printf '[context-rules-loader] Загружены conditional rules по контексту: %s\n\nЦель: %s\n%s' "$NAMES" "$TARGET" "$CONTENT")

# Output format depends on event
case "$EVENT" in
  SessionStart)
    # JSON format: hookSpecificOutput.additionalContext
    printf '%s' "$ADDITIONAL" | jq -Rs --arg evt "SessionStart" '{hookSpecificOutput:{hookEventName:$evt,additionalContext:.}}'
    ;;
  PreToolUse)
    # JSON format for PreToolUse тоже поддерживает additionalContext
    printf '%s' "$ADDITIONAL" | jq -Rs --arg evt "PreToolUse" '{hookSpecificOutput:{hookEventName:$evt,additionalContext:.}}'
    ;;
  *)
    # Fallback — просто stdout как text (Claude увидит как system-reminder)
    printf '%s\n' "$ADDITIONAL"
    ;;
esac

exit 0
