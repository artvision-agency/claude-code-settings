#!/usr/bin/env bash
# session-namer.sh — SessionStart hook: remind to name unnamed sessions
#
# Registered in ~/.claude/settings.json under hooks.SessionStart.
# Reads the current session ID from the CLAUDE_SESSION_ID environment variable
# (injected by Claude Code when running hooks) or falls back to the latest
# JSONL file mtime heuristic.
#
# Output is shown to the user at session start.

set -Eeuo pipefail
shopt -s inherit_errexit 2>/dev/null || true

readonly SESSIONS_YAML="${HOME}/.claude/sessions.yaml"
readonly PROJECTS_DIR="${HOME}/.claude/projects"

# ─── Find current session ID ──────────────────────────────────────────────────

get_current_session_id() {
  # Claude Code injects CLAUDE_SESSION_ID when running hooks
  if [[ -n "${CLAUDE_SESSION_ID:-}" ]]; then
    printf '%s' "${CLAUDE_SESSION_ID}"
    return
  fi

  # Fallback: the most recently modified JSONL file
  python3 - "${PROJECTS_DIR}" <<'PYEOF'
import sys, os, glob

projects_dir = sys.argv[1]
pattern = os.path.join(projects_dir, '*', '*.jsonl')
files = glob.glob(pattern)
if not files:
    sys.exit(1)
files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
print(os.path.splitext(os.path.basename(files[0]))[0])
PYEOF
}

# ─── Check if session ID is already named ─────────────────────────────────────

session_is_named() {
  local sid="$1"
  [[ ! -f "${SESSIONS_YAML}" ]] && return 1

  python3 - "${SESSIONS_YAML}" "${sid}" <<'PYEOF'
import sys, re

yaml_file = sys.argv[1]
target_id = sys.argv[2]

try:
    with open(yaml_file) as f:
        content = f.read()
except FileNotFoundError:
    sys.exit(1)

in_sessions = False
current_key = None
fields = {}

def check_and_print(key, fields, target_id):
    if key and fields.get('id', '') == target_id:
        print(key)
        return True
    return False

for line in content.splitlines():
    stripped = line.lstrip()
    indent   = len(line) - len(stripped)

    if stripped == 'sessions:':
        in_sessions = True
        continue
    if not in_sessions:
        continue

    m = re.match(r'^(\w[\w\-]*):\s*$', stripped)
    if m and indent == 2:
        if check_and_print(current_key, fields, target_id):
            sys.exit(0)
        current_key = m.group(1)
        fields = {}
        continue

    if current_key:
        m2 = re.match(r'^id:\s*["\']?([^"\']+)["\']?\s*$', stripped)
        if m2:
            fields['id'] = m2.group(1)

if check_and_print(current_key, fields, target_id):
    sys.exit(0)

sys.exit(1)
PYEOF
}

# ─── List recent named sessions for context ───────────────────────────────────

list_recent_sessions() {
  [[ ! -f "${SESSIONS_YAML}" ]] && return

  python3 - "${SESSIONS_YAML}" <<'PYEOF'
import sys, re, time

yaml_file = sys.argv[1]
cutoff = time.time() - 7 * 86400

try:
    with open(yaml_file) as f:
        content = f.read()
except FileNotFoundError:
    sys.exit(0)

in_sessions = False
current_key = None
fields = {}
rows = []

def flush(key, fields, rows):
    if key:
        rows.append((key, fields.get('created', ''), fields.get('cwd', '')))

for line in content.splitlines():
    stripped = line.lstrip()
    indent   = len(line) - len(stripped)

    if stripped == 'sessions:':
        in_sessions = True
        continue
    if not in_sessions:
        continue

    m = re.match(r'^(\w[\w\-]*):\s*$', stripped)
    if m and indent == 2:
        flush(current_key, fields, rows)
        current_key = m.group(1)
        fields = {}
        continue

    if current_key:
        for field in ('id', 'created', 'cwd'):
            m2 = re.match(rf'^{field}:\s*["\']?([^"\']+)["\']?\s*$', stripped)
            if m2:
                fields[field] = m2.group(1)

flush(current_key, fields, rows)

# Filter recent
recent = []
for name, created, cwd in rows:
    try:
        t = time.mktime(time.strptime(created, '%Y-%m-%d'))
        if t >= cutoff:
            short_cwd = cwd.replace('/Users/', '~/', 1) if '/Users/' in cwd else cwd
            recent.append((name, short_cwd))
    except ValueError:
        recent.append((name, cwd))

if recent:
    print("Недавние сессии:")
    for name, cwd in recent[-5:]:
        print(f"  cc-resume {name:<22}  # {cwd}")
PYEOF
}

# ─── Main ─────────────────────────────────────────────────────────────────────

main() {
  local sid
  sid="$(get_current_session_id 2>/dev/null)" || {
    # Cannot determine session ID — skip silently
    exit 0
  }

  local existing_name
  existing_name="$(session_is_named "${sid}" 2>/dev/null)" || existing_name=""

  if [[ -n "${existing_name}" ]]; then
    printf '\033[2m[session] %s (%s...)\033[0m\n' "${existing_name}" "${sid:0:8}"
    return
  fi

  # Session is unnamed — prompt the user
  printf '\n\033[33m[session]\033[0m Сессия без имени (%s...)\n' "${sid:0:8}"
  printf '  Назови: \033[1mcc-name <имя>\033[0m\n'
  printf '  Пример: cc-name bot-dev | cc-name artvision-ops | cc-name infra\n'

  local recent
  recent="$(list_recent_sessions 2>/dev/null)"
  if [[ -n "${recent}" ]]; then
    printf '\n%s\n' "${recent}"
  fi

  printf '\n'
}

main "$@"
