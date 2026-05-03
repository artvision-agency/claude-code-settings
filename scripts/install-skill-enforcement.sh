#!/usr/bin/env bash
# install-skill-enforcement.sh — установить инфру гарантии использования скиллов
#
# Что делает:
#   1. Симлинки ~/.claude/hooks/{pre-tool-skill-required,prompt-skill-discovery,stop-skill-audit}.sh
#      → ~/claude-code-settings/hooks/*
#   2. Симлинки ~/.claude/scripts/{audit-session-tools,build-routing-table}.py
#   3. Симлинк ~/.claude/commands/session-stats.md
#   4. Регистрирует hooks в ~/.claude/settings.json
#   5. Crontab: */30 * * * * cd ~/claude-code-settings && git pull --quiet
#
# Idempotent — запускать повторно безопасно.

set -euo pipefail

REPO="$HOME/claude-code-settings"
CLAUDE="$HOME/.claude"

step() { printf "\n\033[1;34m▶ %s\033[0m\n" "$1"; }
ok()   { printf "  \033[0;32m✓\033[0m %s\n" "$1"; }
warn() { printf "  \033[0;33m⚠\033[0m %s\n" "$1"; }

if [[ ! -d "$REPO" ]]; then
  echo "ERR: $REPO not found. Run: git clone git@github.com:artvision-agency/claude-code-settings.git ~/claude-code-settings"
  exit 1
fi

mkdir -p "$CLAUDE/hooks" "$CLAUDE/scripts" "$CLAUDE/commands"

step "1/4  Симлинки hooks"
for hook in pre-tool-skill-required.sh prompt-skill-discovery.sh stop-skill-audit.sh stop-asana-skill-comment.sh; do
  src="$REPO/hooks/$hook"
  dst="$CLAUDE/hooks/$hook"
  if [[ -f "$src" ]]; then
    ln -sfn "$src" "$dst"
    chmod +x "$src"
    ok "$hook → linked"
  else
    warn "$hook not in repo, skip"
  fi
done

step "2/4  Симлинки scripts"
for script in audit-session-tools.py build-routing-table.py asana-skill-comment.py; do
  src="$REPO/scripts/$script"
  dst="$CLAUDE/scripts/$script"
  if [[ -f "$src" ]]; then
    ln -sfn "$src" "$dst"
    chmod +x "$src"
    ok "$script → linked"
  fi
done

step "3/4  Симлинк commands/session-stats.md"
src="$REPO/commands/session-stats.md"
dst="$CLAUDE/commands/session-stats.md"
[[ -f "$src" ]] && ln -sfn "$src" "$dst" && ok "session-stats.md → linked"

step "4/4  Регистрация hooks в settings.json"
SETTINGS="$CLAUDE/settings.json"
if [[ ! -f "$SETTINGS" ]]; then
  echo '{"hooks":{}}' > "$SETTINGS"
fi

# Patch settings.json через Python (jq может не быть на новой машине, но python есть всегда)
python3 - "$SETTINGS" <<'PY'
import json, sys
from pathlib import Path

p = Path(sys.argv[1])
data = json.loads(p.read_text() or '{}')
hooks = data.setdefault("hooks", {})

def add(event, command, matcher=""):
    arr = hooks.setdefault(event, [])
    # check duplicate by command tail
    cmd_tail = command.rsplit("/", 1)[-1]
    for entry in arr:
        for h in entry.get("hooks", []):
            if cmd_tail in h.get("command", ""):
                return  # already registered
    new = {"hooks": [{"type": "command", "command": command}]}
    if matcher:
        new["matcher"] = matcher
    arr.append(new)

# PreToolUse — скилл-блок (matcher для всех инструментов кроме whitelist делается внутри скрипта)
add("PreToolUse", "$HOME/.claude/hooks/pre-tool-skill-required.sh")
# UserPromptSubmit — discovery
add("UserPromptSubmit", "$HOME/.claude/hooks/prompt-skill-discovery.sh")
# Stop — audit в recap + Asana comment
add("Stop", "$HOME/.claude/hooks/stop-skill-audit.sh")
add("Stop", "$HOME/.claude/hooks/stop-asana-skill-comment.sh")

p.write_text(json.dumps(data, indent=2, ensure_ascii=False))
print("settings.json patched")
PY

ok "hooks зарегистрированы в settings.json"

step "+ Cron auto-pull (каждые 30 мин)"
CRON_LINE='*/30 * * * * cd $HOME/claude-code-settings && /usr/bin/git pull --quiet 2>>$HOME/claude-code-settings/.auto-pull.log'
if crontab -l 2>/dev/null | grep -qF "claude-code-settings && /usr/bin/git pull"; then
  ok "cron уже установлен"
else
  ( crontab -l 2>/dev/null; echo "$CRON_LINE" ) | crontab -
  ok "cron записан: каждые 30 мин"
fi

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  Skill-enforcement установлен"
echo "═══════════════════════════════════════════════════════"
echo "  • PreToolUse: pre-tool-skill-required.sh (блок если skill пропущен)"
echo "  • UserPromptSubmit: prompt-skill-discovery.sh (подсказка релевантных)"
echo "  • Stop: stop-skill-audit.sh (аудит в recap)"
echo "  • Cron: git pull каждые 30 мин"
echo ""
echo "  Тест: python3 ~/.claude/scripts/audit-session-tools.py"
echo "  Bypass блокировки: SKILL_OVERRIDE=1 SKILL_REASON='reason'"
