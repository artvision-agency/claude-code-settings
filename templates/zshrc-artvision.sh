
# Claude Code Templates - Global Agents
export PATH="/Users/antonk/.claude-code-templates/bin:$PATH"
eval "$(ssh-agent -s)" > /dev/null 2>&1 && ssh-add ~/.ssh/vps_artvision > /dev/null 2>&1
export PATH="$HOME/bin:$PATH"
devops() { mkdir -p ~/devops-agent && curl -sL "https://raw.githubusercontent.com/artvision-agency/artvision-data/main/agents/devops-agent.md" > ~/devops-agent/CLAUDE.md && cd ~/devops-agent && command claude --dangerously-skip-permissions; }

# DevOps Agent
devops() {
  mkdir -p ~/devops-agent
  curl -sL "https://raw.githubusercontent.com/artvision-agency/artvision-data/main/agents/devops-agent.md" > ~/devops-agent/CLAUDE.md
  cd ~/devops-agent
  command claude --dangerously-skip-permissions
}

export PATH=$HOME/bin:$PATH

# Claude Sync - быстрая синхронизация с claude.ai
alias claude-sync="/Users/antonk/artvision-data/scripts/claude-sync.sh"
alias cs="/Users/antonk/artvision-data/scripts/claude-sync.sh"

export OPENAI_API_KEY="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"
alias v="~/scripts/whisper-voice.sh"

# Claude Code Sessions Manager
alias claude-sessions="~/.claude/scripts/claude-sessions.py"
alias cs="~/.claude/scripts/claude-sessions.py"  # короткий alias
alias ss="~/.claude/scripts/session-search.py"   # поиск по сессиям
# Открыть сессии в новых окнах: cr 2 3 4
cr() { for n in "$@"; do open -na Ghostty.app --args -e "$HOME/.claude/scripts/claude-sessions.py --resume $n"; done; }

# Asana CLI (Free plan wrapper)
alias asana="python3 ~/artvision-data/scripts/asana_cli.py"
export PATH="$HOME/.local/bin:$PATH"

# bun completions
[ -s "/Users/antonk/.bun/_bun" ] && source "/Users/antonk/.bun/_bun"

# bun
export BUN_INSTALL="$HOME/.bun"
export PATH="$BUN_INSTALL/bin:$PATH"
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1

# Claude Code — skip permissions встроен в claude() функцию ниже (строка 57+)

# Переключение аккаунтов Claude Max
alias sw="~/.claude/scripts/switch-account.sh"
export PATH=$PATH:$HOME/.maestro/bin

# Maestro Cloud
export MAESTRO_CLOUD_API_KEY="rb_LybSv3ahNRn7i3Wiab0cCgxHTQWLhGWNTau6yTuxPBJYHXjQ6s2BubhIXP6fbqxmufHJbBAeR3wrZWdOeWqedJJBTQ37cnzpGty"
export PATH="$HOME/.maestro/bin:$PATH"

# Claude — прямой запуск без меню (можно открывать 10+ окон)
# VPS: ssh root@80.90.181.152 'cd /root/artvision-data && claude'

# Claude Code — auto-bootstrap (новая машина = автонастройка)
[ -d "$HOME/.claude/.git" ] || {
  git clone --depth 1 https://github.com/artvision-agency/claude-code-settings.git "$HOME/.claude" 2>/dev/null
  chmod +x "$HOME/.claude/hooks/"*.sh "$HOME/.claude/scripts/"*.sh 2>/dev/null
  echo "✅ Claude Code settings installed from git"
}

# Claude Code named sessions
source ~/.claude/task-router/session-aliases.sh
