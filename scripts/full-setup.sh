#!/bin/bash
# claude-code-settings / full-setup.sh
# Installer для 3-го аккаунта Claude Max 20x или друга
# one-liner: curl -sL https://raw.githubusercontent.com/artvision-agency/claude-code-settings/main/scripts/full-setup.sh | bash
#
# Снимки окружения см. в exports/ (Brewfile, pip-freeze.txt, bun-globals.txt) —
# генерируются на донорской машине через scripts/export-donor-env.sh

set -e

USERNAME="$(whoami)"
SETTINGS_REPO="artvision-agency/claude-code-settings"
EXT_DIR="$HOME/external-agents"
export PATH="$HOME/.local/bin:$HOME/.bun/bin:$PATH"

step() { printf "\n\033[1;34m▶ %s\033[0m\n" "$1"; }
ok()   { printf "  \033[0;32m✓\033[0m %s\n" "$1"; }
warn() { printf "  \033[0;33m⚠\033[0m %s\n" "$1"; }

# ──────────────────────────────────────────────────────────────
step "1/18  Homebrew"
if ! command -v brew &>/dev/null; then
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi
ok "brew $(brew --version | head -1)"

# ──────────────────────────────────────────────────────────────
step "2/18  GitHub CLI"
command -v gh &>/dev/null || brew install gh
if ! gh auth status &>/dev/null; then
    warn "GitHub не авторизован. Выполни: gh auth login (scopes: repo, read:org, workflow)"
    warn "После этого перезапусти установщик."
    exit 1
fi
ok "gh: $(gh api user -q .login)"

# ──────────────────────────────────────────────────────────────
step "3/18  Clone claude-code-settings → ~/.claude"
if [ ! -d "$HOME/.claude/.git" ]; then
    [ -d "$HOME/.claude" ] && mv "$HOME/.claude" "$HOME/.claude.backup-$(date +%s)"
    gh repo clone "$SETTINGS_REPO" "$HOME/.claude"
else
    (cd "$HOME/.claude" && git pull --ff-only) || warn ".claude: git pull failed, продолжаю"
fi
ok "~/.claude склонирован"

# ──────────────────────────────────────────────────────────────
step "4/18  Runtime: bun, node, python, uv"
command -v bun     &>/dev/null || curl -fsSL https://bun.sh/install | bash
command -v uv      &>/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
command -v node    &>/dev/null || brew install node
command -v python3 &>/dev/null || brew install python@3.12
ok "bun $(bun --version 2>/dev/null || echo '?') | node $(node -v 2>/dev/null || echo '?') | python3 $(python3 -V 2>&1 | awk '{print $2}') | uv $(uv --version 2>/dev/null | awk '{print $2}')"

# ──────────────────────────────────────────────────────────────
step "5/18  brew bundle (из exports/Brewfile донорской машины)"
if [ -f "$HOME/.claude/exports/Brewfile" ]; then
    brew bundle --file="$HOME/.claude/exports/Brewfile" || warn "часть пакетов не установилась"
else
    warn "exports/Brewfile нет — базовый набор"
    brew install jq gh cmake ffmpeg sox wireguard-tools tmux lazygit supabase go sqlite
fi

# ──────────────────────────────────────────────────────────────
step "6/18  Python-зависимости"
PIP_REQ="$HOME/.claude/exports/pip-freeze.txt"
if [ -f "$PIP_REQ" ]; then
    pip3 install -r "$PIP_REQ" --quiet || warn "часть pip-пакетов не установилась"
else
    pip3 install --quiet telethon aiogram python-telegram-bot openai anthropic asana playwright playwright-stealth openai-whisper requests aiohttp pyyaml jinja2
fi
# playwright browsers
python3 -m playwright install chromium firefox webkit 2>/dev/null || warn "playwright install пропущен"
ok "pip deps установлены"

# ──────────────────────────────────────────────────────────────
step "7/18  bun globals"
bun add -g \
    agent-browser playwright \
    @anthropic-ai/claude-code \
    @openai/codex \
    @levnikolaevich/hex-ssh-mcp \
    typescript vercel wrangler lighthouse pa11y broken-link-checker \
    pencil-mcp ai-factory 2>/dev/null || warn "часть bun-пакетов не установилась"
command -v agent-browser &>/dev/null && agent-browser install 2>/dev/null || true
ok "bun globals"

# ──────────────────────────────────────────────────────────────
step "8/18  Clone бизнес-репо (artvision-data, artvision-tg-bot, devops-agent)"
for r in artvision-data artvision-tg-bot devops-agent; do
    if [ -d "$HOME/$r/.git" ]; then
        (cd "$HOME/$r" && git pull --ff-only) || warn "$r: pull failed"
    else
        gh repo clone "artvision-agency/$r" "$HOME/$r"
    fi
    ok "~/$r"
done

# ──────────────────────────────────────────────────────────────
step "9/18  External-agents (voltagent × 2, alirezarezvani, wshobson)"
mkdir -p "$EXT_DIR"
clone_ext() {
    local url="$1" dir="$2"
    if [ ! -d "$EXT_DIR/$dir/.git" ]; then
        git clone --depth=1 "$url" "$EXT_DIR/$dir" || warn "$dir: clone failed"
    fi
}
clone_ext https://github.com/VoltAgent/awesome-claude-code-subagents voltagent-subagents
clone_ext https://github.com/VoltAgent/awesome-agent-skills           voltagent-skills
clone_ext https://github.com/alirezarezvani/claude-skills             alirezarezvani-skills
[ -d "$HOME/wshobson-agents/.git" ] || git clone --depth=1 https://github.com/wshobson/agents "$HOME/wshobson-agents"
mkdir -p "$HOME/.claude/plugins/marketplaces"
ln -sf "$HOME/wshobson-agents" "$HOME/.claude/plugins/marketplaces/wshobson-agents"
ok "external-agents + wshobson marketplace"

# ──────────────────────────────────────────────────────────────
step "10/18  Восстановление memory (156 файлов) + rules-global (31)"
MEM_DST="$HOME/.claude/projects/-Users-${USERNAME}/memory"
MEM_SRC="$HOME/artvision-data/.claude/memory-sync"
RULES_DST="$HOME/.claude/rules"
RULES_SRC="$HOME/artvision-data/.claude/rules-global"
mkdir -p "$MEM_DST" "$RULES_DST"
[ -d "$MEM_SRC" ]   && rsync -a "$MEM_SRC/"   "$MEM_DST/"   && ok "memory-файлов: $(ls -1 $MEM_DST/*.md 2>/dev/null | wc -l | tr -d ' ')"
[ -d "$RULES_SRC" ] && rsync -a "$RULES_SRC/" "$RULES_DST/" && ok "rules-файлов: $(ls -1 $RULES_DST/*.md 2>/dev/null | wc -l | tr -d ' ')"

# ──────────────────────────────────────────────────────────────
step "11/18  Симлинки external-agents → skills"
ln_ext() {
    local target="$1" link="$2"
    [ -e "$target" ] && [ ! -L "$link" ] && ln -sf "$target" "$link"
}
for s in ceo-advisor cmo-advisor executive-mentor board-deck-builder founder-coach scenario-war-room internal-narrative; do
    ln_ext "$EXT_DIR/alirezarezvani-skills/c-level-advisor/$s" "$HOME/.claude/skills/$s"
done
ok "c-level skills подключены"

# ──────────────────────────────────────────────────────────────
step "12/18  Local MCP: llm-consilium, medical-mcp, healthcare-mcp"
# llm-consilium уже есть в ~/.claude/mcp-servers/
[ -d "$HOME/medical-mcp/.git" ]         || git clone --depth=1 https://github.com/vitalogy-labs/medical-mcp "$HOME/medical-mcp" 2>/dev/null || true
[ -d "$HOME/healthcare-mcp-public/.git" ] || git clone --depth=1 https://github.com/Cicatriiz/healthcare-mcp-public "$HOME/healthcare-mcp-public" 2>/dev/null || true
if [ -d "$HOME/medical-mcp" ] && [ ! -f "$HOME/medical-mcp/build/index.js" ]; then
    (cd "$HOME/medical-mcp" && bun i && bun run build) 2>/dev/null || warn "medical-mcp build failed"
fi
ok "local MCP серверы"

# ──────────────────────────────────────────────────────────────
step "13/18  Permissions (+x) на hooks/scripts"
chmod +x "$HOME/.claude/hooks/"*.sh      2>/dev/null || true
chmod +x "$HOME/.claude/hooks/"*.py      2>/dev/null || true
chmod +x "$HOME/.claude/scripts/"*.sh    2>/dev/null || true
chmod +x "$HOME/.claude/scripts/"*.py    2>/dev/null || true
chmod +x "$HOME/.claude/statusline.sh"   2>/dev/null || true
ok "права выставлены"

# ──────────────────────────────────────────────────────────────
step "14/18  Screaming Frog wrapper (опционально)"
if [ -x "/Applications/Screaming Frog SEO Spider.app/Contents/MacOS/ScreamingFrogSEOSpiderLauncher" ]; then
    [ -f "$HOME/.local/bin/sf" ] || bash "$HOME/.claude/scripts/install-sf-wrapper.sh"
    ok "sf wrapper установлен"
else
    warn "Screaming Frog не найден — поставь приложение и повтори шаг"
fi

# ──────────────────────────────────────────────────────────────
step "15/18  cc-update / cc-share wrappers"
mkdir -p "$HOME/.local/bin"
SETTINGS_DIR="$HOME/claude-code-settings"
[ -d "$SETTINGS_DIR/.git" ] || gh repo clone "$SETTINGS_REPO" "$SETTINGS_DIR"
ln -sf "$SETTINGS_DIR/scripts/cc-update.sh" "$HOME/.local/bin/cc-update"
ln -sf "$SETTINGS_DIR/scripts/cc-share.sh"  "$HOME/.local/bin/cc-share"
chmod +x "$SETTINGS_DIR/scripts/cc-update.sh" "$SETTINGS_DIR/scripts/cc-share.sh" 2>/dev/null || true
ok "cc-update / cc-share"

# ──────────────────────────────────────────────────────────────
step "16/18  tokens.json — canal передачи с донорской машины"
if [ ! -f "$HOME/artvision-data/tokens.json" ]; then
    if [ -f "$HOME/.claude/templates/tokens.json.template" ]; then
        cp "$HOME/.claude/templates/tokens.json.template" "$HOME/artvision-data/tokens.json"
        chmod 600 "$HOME/artvision-data/tokens.json"
        warn "Создан tokens.json из template (пустые значения)."
        warn "Заполни: $EDITOR $HOME/artvision-data/tokens.json"
        warn "ИЛИ перекинь с донорской машины:"
        warn "  scp <1st-machine>:~/artvision-data/tokens.json $HOME/artvision-data/"
    fi
else
    ok "tokens.json уже есть ($(wc -l < $HOME/artvision-data/tokens.json) строк)"
fi

# ──────────────────────────────────────────────────────────────
step "17/18  Auto-bootstrap в .zshrc"
for rc in "$HOME/.zshrc" "$HOME/.bashrc"; do
    [ -f "$rc" ] || continue
    if ! grep -q "claude-code-settings auto-bootstrap" "$rc"; then
        cat >> "$rc" << 'RCEOF'

# claude-code-settings auto-bootstrap
[ -d "$HOME/.claude/.git" ] || {
  git clone --depth 1 https://github.com/artvision-agency/claude-code-settings.git "$HOME/.claude" 2>/dev/null
  chmod +x "$HOME/.claude/hooks/"*.sh "$HOME/.claude/scripts/"*.sh 2>/dev/null
}
export PATH="$HOME/.local/bin:$HOME/.bun/bin:$PATH"
RCEOF
    fi
done
ok "auto-bootstrap"

# ──────────────────────────────────────────────────────────────
step "18/18  Итоги"
cat << 'EOF'

Установлено:
  - 169 skills                (~/.claude/skills/)
  -  30 global rules          (~/.claude/rules/)
  -  61 hooks                 (SessionStart/PreTool/PostTool/Compact/Stop/UserPromptSubmit)
  - 199 agents + 24 archived  (~/.claude/agents/)
  - 107 scripts               (~/.claude/scripts/)
  -   7 commands              (~/.claude/commands/)
  - 156 memory files          (из artvision-data/.claude/memory-sync → projects/-Users-*/memory/)
  -   3 external-agents       (voltagent × 2, alirezarezvani)
  -   3 бизнес-репо           (artvision-data, artvision-tg-bot, devops-agent)

Следующие шаги:
  1. claude auth login              # залогинься этим 3-м аккаунтом
  2. Заполни/перекинь tokens.json    (см. шаг 16 выше)
  3. Запусти: claude
  4. (опц.) LaunchAgents              — см. SETUP_3RD_ACCOUNT.md §4

Документация:
  ~/.claude/SETUP_3RD_ACCOUNT.md     — пошагово
  ~/.claude/CLAUDE.md                — правила + memory-индекс
  ~/artvision-data/PROJECTS.md       — source of truth по проектам/клиентам

EOF
