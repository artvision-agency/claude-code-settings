#!/bin/bash
# Bootstrap для НОВОЙ машины: подключиться к синку Artvision Claude Code.
# Запуск ОДИН раз на новой машине после установки Claude Code и git/ssh.
#
# Что делает:
#   1. Проверяет prerequisites (git, ssh, brew)
#   2. Клонирует ~/.claude/ из github.com/artvision-agency/claude-code-settings
#   3. Клонирует ~/artvision-data/
#   4. Проверяет SSH-доступ к VPS (для sync-tokens.sh)
#   5. Тянет первый pull всего (sync-all.sh pull)
#
# Ничего не делает destructive — на каждом шаге проверяет существующее состояние.

set -u
RED='\033[0;31m'; GRN='\033[0;32m'; YLW='\033[1;33m'; BLU='\033[0;34m'; NC='\033[0m'
ok()   { echo -e "${GRN}✅${NC} $*"; }
warn() { echo -e "${YLW}⚠️${NC}  $*"; }
err()  { echo -e "${RED}❌${NC} $*"; }
step() { echo -e "\n${BLU}━━━ $* ━━━${NC}"; }

step "1/5 Prerequisites"
for cmd in git ssh rsync python3; do
    if command -v "$cmd" >/dev/null 2>&1; then
        ok "$cmd: $(command -v "$cmd")"
    else
        err "$cmd не найден — установи через brew/apt"
        exit 1
    fi
done

step "2/5 ~/.claude/ (settings + hooks + skills)"
if [ -d "$HOME/.claude/.git" ]; then
    ok "~/.claude/ уже git repo"
else
    if [ -d "$HOME/.claude" ] && [ "$(ls -A "$HOME/.claude" 2>/dev/null | head -1)" ]; then
        warn "~/.claude/ существует но не git — переименуй в ~/.claude.bak и запусти ещё раз"
        echo "      mv ~/.claude ~/.claude.bak.\$(date +%s)"
        exit 1
    fi
    git clone git@github.com:artvision-agency/claude-code-settings.git "$HOME/.claude"
    ok "~/.claude/ клонирован"
fi

step "3/5 ~/artvision-data/ (memory + rules + recaps)"
if [ -d "$HOME/artvision-data/.git" ]; then
    ok "~/artvision-data/ уже git repo"
else
    git clone git@github.com:artvision-agency/artvision-data.git "$HOME/artvision-data"
    ok "~/artvision-data/ клонирован"
fi

step "4/5 SSH к VPS (для sync-tokens.sh)"
if ssh -o ConnectTimeout=5 -o BatchMode=yes -o StrictHostKeyChecking=accept-new \
       root@80.90.181.152 'echo OK' >/dev/null 2>&1; then
    ok "SSH к VPS работает"
else
    warn "SSH к VPS не работает. Скопируй приватный ключ с основной машины:"
    echo "      scp ~/.ssh/id_ed25519* user@main-mac:/Users/antonk/.ssh/"
    echo "      или сгенерируй новый и добавь публичный в /root/.ssh/authorized_keys на VPS"
    echo "      Без этого tokens.json синкаться не будет (но остальное — да)"
fi

step "5/5 Первый pull"
if [ -x "$HOME/.claude/scripts/sync-all.sh" ]; then
    "$HOME/.claude/scripts/sync-all.sh" pull
else
    warn "sync-all.sh не найден — после ручного pull ~/.claude должен появиться"
fi

step "Готово"
ok "Подключи Claude Max аккаунт: claude auth login"
ok "После старта первой сессии хуки автоматически тянут свежее перед каждой сессией"
echo ""
echo "Что синкается автоматически:"
echo "  • ~/.claude/             — git push/pull (settings, hooks, skills, agents)"
echo "  • memory + rules         — через artvision-data git (sync-memory.sh)"
echo "  • tokens.json            — через VPS scp (sync-tokens.sh)"
echo "  • recaps сессий          — через artvision-data git"
