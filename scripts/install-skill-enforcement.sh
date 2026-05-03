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

step "1/5  Симлинки hooks"
HOOKS=(
  # skill-enforcement (orig 4)
  pre-tool-skill-required.sh
  prompt-skill-discovery.sh
  stop-skill-audit.sh
  stop-asana-skill-comment.sh
  # 7 anti-error hooks
  pre-scp-clients-factcheck.sh
  stop-recap-completeness.sh
  post-agent-cost-track.sh
  stop-cost-summary.sh
  pre-compact-context-save.sh
  prompt-compact-recovery.sh
)
for hook in "${HOOKS[@]}"; do
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

step "2/5  Симлинки scripts"
SCRIPTS=(
  audit-session-tools.py
  build-routing-table.py
  asana-skill-comment.py
  skill-discovery-tfidf.py
  multi-machine-drift-check.sh
  tg-bot-deploy-guard.sh
)
for script in "${SCRIPTS[@]}"; do
  src="$REPO/scripts/$script"
  dst="$CLAUDE/scripts/$script"
  if [[ -f "$src" ]]; then
    ln -sfn "$src" "$dst"
    chmod +x "$src"
    ok "$script → linked"
  fi
done

step "3/5  Симлинк commands/session-stats.md"
src="$REPO/commands/session-stats.md"
dst="$CLAUDE/commands/session-stats.md"
[[ -f "$src" ]] && ln -sfn "$src" "$dst" && ok "session-stats.md → linked"

step "4/5  Регистрация hooks в settings.json"
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

# PreToolUse — skill-блок + factcheck для scp клиентских HTML
add("PreToolUse", "$HOME/.claude/hooks/pre-tool-skill-required.sh")
add("PreToolUse", "$HOME/.claude/hooks/pre-scp-clients-factcheck.sh", matcher="Bash")
# PostToolUse — cost tracking для Agent tool (subagents)
add("PostToolUse", "$HOME/.claude/hooks/post-agent-cost-track.sh", matcher="Agent")
# UserPromptSubmit — skill discovery + post-compact recovery
add("UserPromptSubmit", "$HOME/.claude/hooks/prompt-skill-discovery.sh")
add("UserPromptSubmit", "$HOME/.claude/hooks/prompt-compact-recovery.sh")
# PreCompact — save context before compaction
add("PreCompact", "$HOME/.claude/hooks/pre-compact-context-save.sh")
# Stop — skill audit + recap completeness + cost summary + asana comment
add("Stop", "$HOME/.claude/hooks/stop-skill-audit.sh")
add("Stop", "$HOME/.claude/hooks/stop-recap-completeness.sh")
add("Stop", "$HOME/.claude/hooks/stop-cost-summary.sh")
add("Stop", "$HOME/.claude/hooks/stop-asana-skill-comment.sh")

p.write_text(json.dumps(data, indent=2, ensure_ascii=False))
print("settings.json patched")
PY

ok "hooks зарегистрированы в settings.json"

step "5/5  Cron jobs"
# 1) Auto-pull settings repo каждые 30 мин
CRON_PULL='*/30 * * * * cd $HOME/claude-code-settings && /usr/bin/git pull --quiet 2>>$HOME/claude-code-settings/.auto-pull.log'
if crontab -l 2>/dev/null | grep -qF "claude-code-settings && /usr/bin/git pull"; then
  ok "cron auto-pull уже установлен"
else
  ( crontab -l 2>/dev/null; echo "$CRON_PULL" ) | crontab -
  ok "cron auto-pull: каждые 30 мин"
fi

# 2) Multi-machine drift check каждый день 9:00
CRON_DRIFT='0 9 * * * /usr/bin/env bash $HOME/.claude/scripts/multi-machine-drift-check.sh 2>>$HOME/.claude/logs/drift-check.log'
if crontab -l 2>/dev/null | grep -qF "multi-machine-drift-check.sh"; then
  ok "cron drift-check уже установлен"
else
  ( crontab -l 2>/dev/null; echo "$CRON_DRIFT" ) | crontab -
  ok "cron drift-check: ежедневно 9:00"
fi

mkdir -p "$HOME/.claude/logs"

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  Skill-enforcement + 7 anti-error hooks установлены"
echo "═══════════════════════════════════════════════════════"
echo "  PreToolUse:"
echo "    • pre-tool-skill-required.sh (skill-блок)"
echo "    • pre-scp-clients-factcheck.sh (factcheck перед scp клиентских HTML)"
echo "  PostToolUse:"
echo "    • post-agent-cost-track.sh (cost tracking Agent tool)"
echo "  UserPromptSubmit:"
echo "    • prompt-skill-discovery.sh (TF-IDF top-5 релевантных)"
echo "    • prompt-compact-recovery.sh (восстановление после компакшена)"
echo "  PreCompact:"
echo "    • pre-compact-context-save.sh (сохранить goal+tasks+обещания)"
echo "  Stop:"
echo "    • stop-skill-audit.sh (аудит в recap)"
echo "    • stop-recap-completeness.sh (goal+deliverables+acceptance+status)"
echo "    • stop-cost-summary.sh (суммарные затраты, alert >\$10)"
echo "    • stop-asana-skill-comment.sh (комментарий в Asana задачи)"
echo "  Cron:"
echo "    • git pull каждые 30 мин"
echo "    • multi-machine-drift-check ежедневно 9:00"
echo ""
echo "  Тест: python3 ~/.claude/scripts/audit-session-tools.py"
echo "  Bypass skill: SKILL_OVERRIDE=1 SKILL_REASON='reason'"
echo "  Bypass factcheck: FACTCHECK_FORCE=1"
echo "  TG bot guard: bash ~/.claude/scripts/tg-bot-deploy-guard.sh <bot-name> <log-path>"
