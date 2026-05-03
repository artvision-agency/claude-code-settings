#!/usr/bin/env bash
# multi-machine-drift-check.sh — раз в день сравнивает SHA hooks/scripts на разных машинах
#
# Запускается через cron (на одной из машин — обычно VPS или Mac).
# Если SHA отличаются — TG-alert через tg-send.sh.
#
# Cron: 0 9 * * * /usr/bin/env bash $HOME/.claude/scripts/multi-machine-drift-check.sh

set -uo pipefail

MACHINES=(
  "local"
  "root@80.90.181.152"
)

# Compute SHA for hooks + scripts
local_sha() {
  find ~/.claude/hooks ~/.claude/scripts -maxdepth 1 -type f \( -name "*.sh" -o -name "*.py" \) 2>/dev/null \
    | sort | xargs cat 2>/dev/null | shasum -a 256 | cut -d' ' -f1
}

remote_sha() {
  local host="$1"
  ssh -o ConnectTimeout=10 -o BatchMode=yes "$host" \
    'find ~/.claude/hooks ~/.claude/scripts -maxdepth 1 -type f \( -name "*.sh" -o -name "*.py" \) 2>/dev/null | sort | xargs cat 2>/dev/null | sha256sum | cut -d" " -f1' \
    2>/dev/null
}

LOCAL=$(local_sha)
DRIFT=()

for m in "${MACHINES[@]}"; do
  [[ "$m" == "local" ]] && continue
  REMOTE=$(remote_sha "$m")
  if [[ -z "$REMOTE" ]]; then
    DRIFT+=("$m: UNREACHABLE")
  elif [[ "$REMOTE" != "$LOCAL" ]]; then
    DRIFT+=("$m: SHA mismatch (local=${LOCAL:0:8} remote=${REMOTE:0:8})")
  fi
done

if [[ ${#DRIFT[@]} -eq 0 ]]; then
  echo "[drift-check] OK — все машины синхронизированы (sha=${LOCAL:0:8})"
  exit 0
fi

echo "[drift-check] ⚠️ DRIFT detected:"
printf '%s\n' "${DRIFT[@]}"

# TG alert if available
if [[ -x "$HOME/.claude/scripts/tg-send.sh" ]]; then
  MSG="⚠️ Skill-enforcement drift между машинами:%0A$(printf '%s\\n' "${DRIFT[@]}")%0A%0AРешение: на отстающей машине: cd ~/claude-code-settings && git pull && bash scripts/install-skill-enforcement.sh"
  "$HOME/.claude/scripts/tg-send.sh" anton "$MSG" 2>/dev/null || true
fi

exit 1
