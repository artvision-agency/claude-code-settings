#!/bin/bash
# pre-bash-resource-guard.sh
# Block heavy Bash commands when system is under memory/disk pressure.
# Triggered by repeated session crashes 26.04 (OOM kill suspected, free RAM ~42MB, disk 97%).
# Bypass: RESOURCE_FORCE=1
#
# Logs: ~/.claude/logs/resource-guard.log
set -euo pipefail

CMD="${1:-}"
LOG=~/.claude/logs/resource-guard.log
mkdir -p ~/.claude/logs

# Bypass
if [ "${RESOURCE_FORCE:-}" = "1" ]; then
  exit 0
fi

# Only guard heavy commands — let cheap stuff through (git status, ls, cat, echo, pwd, which)
case "$CMD" in
  git\ status*|git\ log*|git\ diff*|git\ branch*|git\ stash\ list*|\
  ls*|cat*|echo*|pwd*|which*|head*|tail*|wc*|grep*|find*|du*|df*|ps*|\
  stat*|file*|true|false|test*|\[*|date*|env*|uname*|whoami*|hostname*|\
  uptime|vm_stat*|sw_vers*|sysctl*)
    exit 0
    ;;
esac

# Get free memory in MB (page size 16K on Apple Silicon)
PAGE_SIZE=$(pagesize 2>/dev/null || echo 16384)
FREE_PAGES=$(vm_stat 2>/dev/null | awk '/Pages free/ {gsub(/\./,""); print $3}')
SPEC_PAGES=$(vm_stat 2>/dev/null | awk '/Pages speculative/ {gsub(/\./,""); print $3}')
if [ -z "${FREE_PAGES:-}" ]; then exit 0; fi
FREE_MB=$(( (FREE_PAGES + ${SPEC_PAGES:-0}) * PAGE_SIZE / 1048576 ))

# Get disk free GB on home volume
DISK_FREE_GB=$(df -g "$HOME" 2>/dev/null | awk 'NR==2 {print $4}')
DISK_USE_PCT=$(df "$HOME" 2>/dev/null | awk 'NR==2 {gsub(/%/,""); print $5}')

# Thresholds
MIN_MEM_MB=200
MIN_DISK_GB=5

ts="$(date '+%Y-%m-%d %H:%M:%S')"

if [ "$FREE_MB" -lt "$MIN_MEM_MB" ]; then
  echo "[$ts] BLOCKED low_mem free=${FREE_MB}MB cmd=${CMD:0:80}" >> "$LOG"
  cat <<EOF >&2
[pre-bash-resource-guard] BLOCKED — low free memory (${FREE_MB}MB < ${MIN_MEM_MB}MB).
Sessions могут упасть от OOM kill. Что сделать:
  1. Закрой лишние ttys с claude (\`pgrep -lf 'claude --dangerously'\`)
  2. Прибей жирные процессы: \`ps aux | sort -nrk 4,4 | head -10\`
  3. Если уверен — повтори с RESOURCE_FORCE=1 prefix.
Cmd: ${CMD:0:120}
EOF
  exit 1
fi

if [ -n "${DISK_FREE_GB:-}" ] && [ "$DISK_FREE_GB" -lt "$MIN_DISK_GB" ]; then
  echo "[$ts] BLOCKED low_disk free=${DISK_FREE_GB}GB cmd=${CMD:0:80}" >> "$LOG"
  cat <<EOF >&2
[pre-bash-resource-guard] BLOCKED — low disk (${DISK_FREE_GB}GB free, ${DISK_USE_PCT}% used).
Что почистить:
  rm ~/.claude/downloads/claude-*-darwin-arm64  # старые CLI бинарники
  find ~/.claude/projects/-Users-antonk/ -maxdepth 1 -name '*.jsonl' -mtime +14 -delete
  du -sh ~/.claude/* | sort -hr | head -10
Bypass: RESOURCE_FORCE=1
EOF
  exit 1
fi

# Soft warn only (logged, not blocked)
if [ "$FREE_MB" -lt 500 ] || { [ -n "${DISK_FREE_GB:-}" ] && [ "$DISK_FREE_GB" -lt 10 ]; }; then
  echo "[$ts] warn free_mem=${FREE_MB}MB free_disk=${DISK_FREE_GB:-?}GB cmd=${CMD:0:80}" >> "$LOG"
fi

exit 0
