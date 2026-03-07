#!/bin/bash
# Диагностика конфигурации Claude Code
# Запуск: ~/.claude/scripts/claude-diag.sh или artvision-data/.claude/scripts/claude-diag.sh
# Выводит JSON-подобный отчёт для сравнения между аккаунтами

set -e

echo "========================================="
echo "  CLAUDE CODE — DIAGNOSTIC REPORT"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "  User: $(whoami)@$(hostname)"
echo "========================================="
echo ""

# 1. Version
echo "## Claude Code Version"
claude --version 2>/dev/null || echo "NOT INSTALLED"
echo ""

# 2. Account
echo "## Account"
if [ -f ~/.claude/.credentials.json ]; then
  python3 -c "import json; d=json.load(open('$HOME/.claude/.credentials.json')); print('Email:', d.get('claudeAiOauth',{}).get('email','?'))" 2>/dev/null || echo "credentials exist but unreadable"
else
  echo "No credentials file"
fi
echo ""

# 3. Global settings
echo "## Global Settings (~/.claude/settings.json)"
if [ -f ~/.claude/settings.json ]; then
  echo "  model: $(python3 -c "import json; print(json.load(open('$HOME/.claude/settings.json')).get('model','NOT SET'))" 2>/dev/null)"
  echo "  hooks: $(python3 -c "import json; d=json.load(open('$HOME/.claude/settings.json')); print(sum(len(v) for v in d.get('hooks',{}).values()))" 2>/dev/null) total"
  echo "  plugins enabled: $(python3 -c "import json; d=json.load(open('$HOME/.claude/settings.json')); print(sum(1 for v in d.get('enabledPlugins',{}).values() if v))" 2>/dev/null)"
  echo "  plugins disabled: $(python3 -c "import json; d=json.load(open('$HOME/.claude/settings.json')); print(sum(1 for v in d.get('enabledPlugins',{}).values() if not v))" 2>/dev/null)"
  echo "  permissions allow: $(python3 -c "import json; d=json.load(open('$HOME/.claude/settings.json')); print(len(d.get('permissions',{}).get('allow',[])))" 2>/dev/null)"
  echo "  permissions deny: $(python3 -c "import json; d=json.load(open('$HOME/.claude/settings.json')); print(len(d.get('permissions',{}).get('deny',[])))" 2>/dev/null)"
  echo "  skipDangerousMode: $(python3 -c "import json; print(json.load(open('$HOME/.claude/settings.json')).get('skipDangerousModePermissionPrompt','NOT SET'))" 2>/dev/null)"
  echo "  env vars: $(python3 -c "import json; d=json.load(open('$HOME/.claude/settings.json')); print(list(d.get('env',{}).keys()) or 'none')" 2>/dev/null)"
else
  echo "  MISSING!"
fi
echo ""

# 4. Project settings
echo "## Project Settings (artvision-data/.claude/settings.json)"
PROJ="$HOME/artvision-data/.claude/settings.json"
if [ -f "$PROJ" ]; then
  echo "  model: $(python3 -c "import json; print(json.load(open('$PROJ')).get('model','NOT SET'))" 2>/dev/null)"
  echo "  hooks: $(python3 -c "import json; d=json.load(open('$PROJ')); print(sum(len(v) for v in d.get('hooks',{}).values()))" 2>/dev/null) total"
  echo "  plugins enabled: $(python3 -c "import json; d=json.load(open('$PROJ')); print(sum(1 for v in d.get('enabledPlugins',{}).values() if v))" 2>/dev/null)"
  echo "  permissions allow: $(python3 -c "import json; d=json.load(open('$PROJ')); print(len(d.get('permissions',{}).get('allow',[])))" 2>/dev/null)"
else
  echo "  MISSING!"
fi
echo ""

# 5. Rules
echo "## Rules"
echo "  ~/.claude/rules/:"
ls ~/.claude/rules/ 2>/dev/null | sed 's/^/    /' || echo "    NONE"
echo "  artvision-data/.claude/rules/:"
ls ~/artvision-data/.claude/rules/ 2>/dev/null | sed 's/^/    /' || echo "    NONE"
echo ""

# 6. Hooks (scripts)
echo "## Hook Scripts (~/.claude/hooks/)"
ls ~/.claude/hooks/ 2>/dev/null | grep -v README | sed 's/^/    /' || echo "    NONE"
echo ""

# 7. Skills
echo "## Skills"
SKILL_COUNT=$(ls ~/.claude/skills/ 2>/dev/null | wc -l | tr -d ' ')
echo "  Total: $SKILL_COUNT"
echo "  List:"
ls ~/.claude/skills/ 2>/dev/null | sed 's/^/    /' || echo "    NONE"
echo ""

# 8. Memory
echo "## Memory Files"
for dir in ~/.claude/projects/*/memory/; do
  if [ -d "$dir" ]; then
    echo "  $dir:"
    ls "$dir" 2>/dev/null | sed 's/^/    /'
  fi
done
echo ""

# 9. CLAUDE.md
echo "## CLAUDE.md"
echo "  Global (~/.claude/CLAUDE.md): $(wc -l < ~/.claude/CLAUDE.md 2>/dev/null || echo 'MISSING') lines"
echo "  Project (artvision-data/.claude/CLAUDE.md): $(wc -l < ~/artvision-data/.claude/CLAUDE.md 2>/dev/null || echo 'MISSING') lines"
echo ""

# 10. MCP servers
echo "## MCP Servers (from settings)"
python3 -c "
import json, os
for f in [os.path.expanduser('~/.claude/settings.json'), os.path.expanduser('~/artvision-data/.claude/settings.json')]:
    try:
        d = json.load(open(f))
        mcps = d.get('mcpServers', {})
        if mcps:
            print(f'  {f}: {list(mcps.keys())}')
    except: pass
" 2>/dev/null
# Also check settings.local.json
if [ -f ~/artvision-data/.claude/settings.local.json ]; then
  echo "  settings.local.json MCP:"
  python3 -c "import json; d=json.load(open('$HOME/artvision-data/.claude/settings.local.json')); print('   ', list(d.get('mcpServers',{}).keys()))" 2>/dev/null
fi
echo ""

# 11. Agents
echo "## Agents"
AGENT_COUNT=$(ls ~/.claude/agents/ 2>/dev/null | wc -l | tr -d ' ')
echo "  Total: $AGENT_COUNT"
echo ""

# 12. Scripts
echo "## Scripts (~/.claude/scripts/)"
ls ~/.claude/scripts/ 2>/dev/null | sed 's/^/    /' || echo "    NONE"
echo ""

echo "========================================="
echo "  END OF DIAGNOSTIC REPORT"
echo "========================================="
