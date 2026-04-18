#!/usr/bin/env bash
# cc-session.sh — Named sessions manager for Claude Code
#
# Commands:
#   cc-session name <name>          — name the current/latest session
#   cc-session resume <name>        — resume session by name (fuzzy match)
#   cc-session list [--active]      — list all or recent (7d) named sessions
#
# Storage: ~/.claude/sessions.yaml
# Session IDs discovered from ~/.claude/projects/*/  JSONL files
#
# Requirements: bash 4.4+, python3, claude CLI
# Platform: macOS (BSD) + Linux

set -Eeuo pipefail
shopt -s inherit_errexit 2>/dev/null || true

# ─── Constants ───────────────────────────────────────────────────────────────

readonly SCRIPT_NAME="cc-session"
readonly SESSIONS_YAML="${HOME}/.claude/sessions.yaml"
readonly PROJECTS_DIR="${HOME}/.claude/projects"
readonly DATE_CMD_EPOCH="date +%s"

# ANSI colours — disabled automatically when stdout is not a terminal
if [[ -t 1 ]]; then
  C_RESET='\033[0m'
  C_BOLD='\033[1m'
  C_DIM='\033[2m'
  C_CYAN='\033[36m'
  C_GREEN='\033[32m'
  C_YELLOW='\033[33m'
  C_RED='\033[31m'
else
  C_RESET='' C_BOLD='' C_DIM='' C_CYAN='' C_GREEN='' C_YELLOW='' C_RED=''
fi

# ─── Helpers ─────────────────────────────────────────────────────────────────

log_err() { printf '%s[ERROR]%s %s\n' "${C_RED}" "${C_RESET}" "$*" >&2; }
log_info() { printf '%s[info]%s %s\n' "${C_DIM}" "${C_RESET}" "$*" >&2; }

usage() {
  cat >&2 <<EOF
${C_BOLD}${SCRIPT_NAME}${C_RESET} — named sessions for Claude Code

${C_BOLD}USAGE${C_RESET}
  ${SCRIPT_NAME} name   <name>          Name the latest session
  ${SCRIPT_NAME} resume <name|id>       Resume a named session (fuzzy match)
  ${SCRIPT_NAME} list   [--active]      List saved sessions (--active = last 7d)

${C_BOLD}EXAMPLES${C_RESET}
  cc-name bot-dev                       # alias for: cc-session name bot-dev
  cc-resume artvision                   # fuzzy-matches 'artvision-ops' etc.
  cc-sessions --active                  # alias for: cc-session list --active

${C_BOLD}STORAGE${C_RESET}
  ${SESSIONS_YAML}
EOF
}

# ─── YAML helpers via python3 ─────────────────────────────────────────────────
#
# We avoid a yq dependency and use python3 for all YAML read/write.
# The YAML is simple enough that we can also write it with plain shell
# for the "ensure file exists" bootstrap case.

yaml_read() {
  # yaml_read <key>  — prints value of sessions.<key>.id  or empty string
  local name="$1"
  python3 - "${SESSIONS_YAML}" "${name}" <<'PYEOF'
import sys, re

yaml_file = sys.argv[1]
target = sys.argv[2]

try:
    with open(yaml_file) as f:
        content = f.read()
except FileNotFoundError:
    sys.exit(0)

# Simple state-machine parser for our known schema
in_sessions = False
current_key = None
current_indent = 0

for line in content.splitlines():
    stripped = line.lstrip()
    indent = len(line) - len(stripped)

    if stripped == 'sessions:':
        in_sessions = True
        continue

    if not in_sessions:
        continue

    # Top-level session key (indent == 2)
    m = re.match(r'^(\w[\w\-]*):\s*$', stripped)
    if m and indent == 2:
        current_key = m.group(1)
        continue

    if current_key == target:
        m2 = re.match(r'^id:\s*["\']?([^"\']+)["\']?\s*$', stripped)
        if m2:
            print(m2.group(1))
            sys.exit(0)

sys.exit(0)
PYEOF
}

yaml_list() {
  # Prints lines: "name|id|created|cwd"
  python3 - "${SESSIONS_YAML}" <<'PYEOF'
import sys, re

yaml_file = sys.argv[1]

try:
    with open(yaml_file) as f:
        content = f.read()
except FileNotFoundError:
    sys.exit(0)

in_sessions = False
current_key = None
fields = {}

def flush(key, fields):
    if key:
        sid   = fields.get('id', '')
        cdate = fields.get('created', '')
        cwd   = fields.get('cwd', '')
        todo  = fields.get('todo', '')
        print(f"{key}|{sid}|{cdate}|{cwd}|{todo}")

for line in content.splitlines():
    stripped = line.lstrip()
    indent = len(line) - len(stripped)

    if stripped == 'sessions:':
        in_sessions = True
        continue

    if not in_sessions:
        continue

    m = re.match(r'^(\w[\w\-]*):\s*$', stripped)
    if m and indent == 2:
        flush(current_key, fields)
        current_key = m.group(1)
        fields = {}
        continue

    if current_key:
        for field in ('id', 'created', 'cwd', 'todo'):
            m2 = re.match(rf'^{field}:\s*["\']?([^"\']+)["\']?\s*$', stripped)
            if m2:
                fields[field] = m2.group(1)

flush(current_key, fields)
PYEOF
}

yaml_upsert() {
  # yaml_upsert <name> <id> <created> <cwd> <todo>
  local name="$1" sid="$2" created="$3" cwd="$4" todo="$5"
  python3 - "${SESSIONS_YAML}" "${name}" "${sid}" "${created}" "${cwd}" "${todo}" <<'PYEOF'
import sys, re, os

yaml_file = sys.argv[1]
name      = sys.argv[2]
sid       = sys.argv[3]
created   = sys.argv[4]
cwd       = sys.argv[5]
todo      = sys.argv[6]

entry = (
    f"  {name}:\n"
    f'    id: "{sid}"\n'
    f'    created: "{created}"\n'
    f'    cwd: "{cwd}"\n'
    f'    todo: "{todo}"\n'
)

try:
    with open(yaml_file) as f:
        content = f.read()
except FileNotFoundError:
    content = "sessions:\n"

# Replace existing block if present
pattern = rf'(?m)^  {re.escape(name)}:\n(?:    [^\n]*\n)*'
if re.search(pattern, content):
    content = re.sub(pattern, entry, content)
else:
    # Append before end (strip trailing newline first)
    content = content.rstrip('\n') + '\n' + entry

with open(yaml_file, 'w') as f:
    f.write(content)

print(f"Saved: {name} -> {sid}")
PYEOF
}

# ─── Session discovery ────────────────────────────────────────────────────────

# Find the ID of the most recently modified JSONL file under $PROJECTS_DIR.
# Returns the UUID stem (e.g. "abc123-def456-...").
find_latest_session_id() {
  python3 - "${PROJECTS_DIR}" <<'PYEOF'
import sys, os, glob

projects_dir = sys.argv[1]
pattern = os.path.join(projects_dir, '*', '*.jsonl')
files = glob.glob(pattern)

if not files:
    sys.exit(1)

# Sort by mtime descending
files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
stem = os.path.splitext(os.path.basename(files[0]))[0]
print(stem)
PYEOF
}

# Find session ID by scanning JSONL files in a given project dir.
# Looks for the cwd field to validate.
find_session_id_for_cwd() {
  local target_cwd="$1"
  python3 - "${PROJECTS_DIR}" "${target_cwd}" <<'PYEOF'
import sys, os, glob, json

projects_dir = sys.argv[1]
target_cwd   = sys.argv[2]

pattern = os.path.join(projects_dir, '*', '*.jsonl')
files = sorted(glob.glob(pattern), key=lambda p: os.path.getmtime(p), reverse=True)

for fpath in files[:50]:  # scan most recent 50 only
    try:
        with open(fpath, encoding='utf-8', errors='replace') as f:
            for line in f:
                try:
                    d = json.loads(line)
                    if d.get('cwd') == target_cwd:
                        stem = os.path.splitext(os.path.basename(fpath))[0]
                        print(stem)
                        sys.exit(0)
                except (json.JSONDecodeError, KeyError):
                    continue
    except OSError:
        continue
PYEOF
}

# Detect todo file for a given cwd path
detect_todo() {
  local cwd="$1"
  case "${cwd}" in
    */artvision-tg-bot*)   printf 'artvision-tg-bot/TODO.md' ;;
    */artvision-data*)     printf 'artvision-data/TODO.md' ;;
    */devops-agent*)       printf 'devops-agent/TODO.md' ;;
    *)                     printf '' ;;
  esac
}

# Get today's date as YYYY-MM-DD (portable macOS/Linux)
today() {
  date '+%Y-%m-%d'
}

# ─── Fuzzy name matching ──────────────────────────────────────────────────────

# Given a query string, find the best matching session name from sessions.yaml.
# Prints "name|id" on success, nothing on failure.
fuzzy_match() {
  local query="$1"
  python3 - "${SESSIONS_YAML}" "${query}" <<'PYEOF'
import sys, re

yaml_file = sys.argv[1]
query     = sys.argv[2].lower()

try:
    with open(yaml_file) as f:
        content = f.read()
except FileNotFoundError:
    sys.exit(0)

names = []
current_key = None
fields = {}
in_sessions = False

def flush(key, fields, names):
    if key:
        names.append((key, fields.get('id', '')))

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
        flush(current_key, fields, names)
        current_key = m.group(1)
        fields = {}
        continue

    if current_key:
        m2 = re.match(r'^id:\s*["\']?([^"\']+)["\']?\s*$', stripped)
        if m2:
            fields['id'] = m2.group(1)

flush(current_key, fields, names)

if not names:
    sys.exit(0)

# Exact match first
for name, sid in names:
    if name.lower() == query:
        print(f"{name}|{sid}")
        sys.exit(0)

# Prefix match
matches = [(n, s) for n, s in names if n.lower().startswith(query)]
if len(matches) == 1:
    print(f"{matches[0][0]}|{matches[0][1]}")
    sys.exit(0)

# Substring match
matches = [(n, s) for n, s in names if query in n.lower()]
if len(matches) == 1:
    print(f"{matches[0][0]}|{matches[0][1]}")
    sys.exit(0)

# Multiple matches — list them
if matches:
    print("MULTIPLE")
    for n, s in matches:
        print(f"  {n}|{s}")
    sys.exit(0)

# Token match (query words all appear in name)
q_tokens = query.split('-')
token_matches = [(n, s) for n, s in names
                 if all(t in n.lower() for t in q_tokens)]
if token_matches:
    if len(token_matches) == 1:
        print(f"{token_matches[0][0]}|{token_matches[0][1]}")
        sys.exit(0)
    print("MULTIPLE")
    for n, s in token_matches:
        print(f"  {n}|{s}")

sys.exit(0)
PYEOF
}

# ─── Commands ─────────────────────────────────────────────────────────────────

cmd_name() {
  local name="${1:-}"
  if [[ -z "${name}" ]]; then
    log_err "Usage: ${SCRIPT_NAME} name <name>"
    exit 1
  fi

  # Validate name: alphanumeric + hyphens only
  if [[ ! "${name}" =~ ^[a-zA-Z0-9][a-zA-Z0-9_-]*$ ]]; then
    log_err "Name must start with alphanumeric and contain only [a-zA-Z0-9_-]"
    exit 1
  fi

  # Try to detect current session from cwd
  local cwd
  cwd="$(pwd -P)"
  local sid
  sid="$(find_latest_session_id 2>/dev/null)" || {
    log_err "Could not find any JSONL session files in ${PROJECTS_DIR}"
    exit 1
  }

  local todo
  todo="$(detect_todo "${cwd}")"
  local created
  created="$(today)"

  # Ensure sessions.yaml exists
  if [[ ! -f "${SESSIONS_YAML}" ]]; then
    printf 'sessions:\n' > "${SESSIONS_YAML}"
    log_info "Created ${SESSIONS_YAML}"
  fi

  yaml_upsert "${name}" "${sid}" "${created}" "${cwd}" "${todo}"

  printf '%bSession named:%b %b%s%b -> %b%s%b\n' \
    "${C_GREEN}" "${C_RESET}" \
    "${C_BOLD}" "${name}" "${C_RESET}" \
    "${C_DIM}" "${sid}" "${C_RESET}"

  if [[ -n "${todo}" ]]; then
    printf '%bTODO context:%b %s\n' "${C_DIM}" "${C_RESET}" "${todo}"
  fi
}

cmd_resume() {
  local query="${1:-}"
  if [[ -z "${query}" ]]; then
    log_err "Usage: ${SCRIPT_NAME} resume <name|id>"
    exit 1
  fi

  if [[ ! -f "${SESSIONS_YAML}" ]]; then
    log_err "No sessions saved yet. Use: ${SCRIPT_NAME} name <name>"
    exit 1
  fi

  local sid=""

  # Check if query looks like a full UUID (contains hyphens at positions 8,13,18,23)
  if [[ "${query}" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]]; then
    sid="${query}"
  else
    # Exact YAML lookup first
    sid="$(yaml_read "${query}" 2>/dev/null)"

    # Fuzzy match if not found
    if [[ -z "${sid}" ]]; then
      local match_output
      match_output="$(fuzzy_match "${query}" 2>/dev/null)"

      if [[ -z "${match_output}" ]]; then
        log_err "No session named '${query}' found."
        printf '\nSaved sessions:\n'
        cmd_list
        exit 1
      fi

      local first_line
      first_line="$(printf '%s\n' "${match_output}" | head -1)"

      if [[ "${first_line}" == "MULTIPLE" ]]; then
        printf '%bMultiple matches for%b %s:\n' "${C_YELLOW}" "${C_RESET}" "${query}"
        printf '%s\n' "${match_output}" | tail -n +2 | while IFS='|' read -r n s; do
          printf '  %b%-30s%b %s\n' "${C_CYAN}" "${n}" "${C_RESET}" "${s}"
        done
        printf '\nBe more specific.\n'
        exit 1
      fi

      # Single match
      sid="$(printf '%s\n' "${first_line}" | cut -d'|' -f2)"
      local matched_name
      matched_name="$(printf '%s\n' "${first_line}" | cut -d'|' -f1)"
      if [[ "${matched_name}" != "${query}" ]]; then
        log_info "Fuzzy matched '${query}' -> '${matched_name}'"
      fi
    fi
  fi

  if [[ -z "${sid}" ]]; then
    log_err "Session ID is empty for '${query}'"
    exit 1
  fi

  printf '%bResuming session:%b %b%s%b -> %b%s%b\n' \
    "${C_CYAN}" "${C_RESET}" \
    "${C_BOLD}" "${query}" "${C_RESET}" \
    "${C_DIM}" "${sid}" "${C_RESET}"

  exec claude --resume "${sid}"
}

cmd_list() {
  local active_only=0
  local cutoff_epoch=0

  for arg in "$@"; do
    if [[ "${arg}" == "--active" ]]; then
      active_only=1
    fi
  done

  if [[ ! -f "${SESSIONS_YAML}" ]]; then
    printf 'No sessions saved yet.\n'
    printf 'Use: %bcc-name <name>%b to name the current session.\n' "${C_BOLD}" "${C_RESET}"
    return
  fi

  # Compute cutoff epoch for 7-day filter
  if [[ "${active_only}" -eq 1 ]]; then
    cutoff_epoch="$(python3 -c "import time; print(int(time.time()) - 7*86400)")"
  fi

  local rows
  rows="$(yaml_list 2>/dev/null)"

  if [[ -z "${rows}" ]]; then
    printf 'No sessions saved yet.\n'
    return
  fi

  # Header
  printf '\n%b%-25s  %-38s  %-10s  %s%b\n' \
    "${C_BOLD}" "NAME" "SESSION ID" "CREATED" "CWD" "${C_RESET}"
  printf '%s\n' "$(printf '─%.0s' {1..90})"

  local count=0
  while IFS='|' read -r name sid created cwd todo; do
    [[ -z "${name}" ]] && continue

    # Active filter: check created date >= cutoff
    if [[ "${active_only}" -eq 1 && -n "${created}" ]]; then
      local row_epoch
      row_epoch="$(python3 -c "
import time, sys
try:
    t = time.strptime('${created}', '%Y-%m-%d')
    print(int(time.mktime(t)))
except:
    print(0)
")"
      if [[ "${row_epoch}" -lt "${cutoff_epoch}" ]]; then
        continue
      fi
    fi

    # Truncate long values for display
    local short_sid="${sid:0:8}..."
    local short_cwd="${cwd/#${HOME}/~}"
    if [[ "${#short_cwd}" -gt 35 ]]; then
      short_cwd="...${short_cwd: -32}"
    fi

    printf '%b%-25s%b  %b%s%b  %-10s  %s\n' \
      "${C_CYAN}" "${name}" "${C_RESET}" \
      "${C_DIM}" "${short_sid}" "${C_RESET}" \
      "${created}" \
      "${short_cwd}"
    count=$((count + 1))
  done <<< "${rows}"

  if [[ "${count}" -eq 0 ]]; then
    if [[ "${active_only}" -eq 1 ]]; then
      printf 'No sessions from the last 7 days.\n'
    else
      printf 'No sessions saved.\n'
    fi
  fi

  printf '\n%bResuming:%b cc-resume <name>   %bNaming:%b cc-name <name>\n' \
    "${C_DIM}" "${C_RESET}" "${C_DIM}" "${C_RESET}"
  printf '\n'
}

# ─── Entry point ─────────────────────────────────────────────────────────────

main() {
  local cmd="${1:-}"
  shift || true

  case "${cmd}" in
    name)    cmd_name   "$@" ;;
    resume)  cmd_resume "$@" ;;
    list)    cmd_list   "$@" ;;
    -h|--help|help|"") usage; exit 0 ;;
    *)
      log_err "Unknown command: ${cmd}"
      usage
      exit 1
      ;;
  esac
}

main "$@"
