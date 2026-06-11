#!/usr/bin/env bash
# bootstrap-mac-login.sh — оркестратор автозапуска при ЛОГИНЕ Mac.
# Вызывается LaunchAgent pro.artvision.bootstrap (RunAtLoad=true).
# Поток: net-failover (приоритет телефону) → resume 6 сессий + combine-окно.
# Терминал: Ghostty (через sessions-resume-launcher.sh).
# Старое поведение (одно окно claude /combine) заменено на оркестратор.
# Бэкап старой версии: bootstrap-mac-login.sh.bak-2026-05-30

set -uo pipefail
LOG="$HOME/Library/Logs/artvision-bootstrap.log"
exec >> "$LOG" 2>&1
echo "=== bootstrap LOGIN $(date '+%F %T') ==="

# 1) Сеть: приоритет хотспоту телефона / failover при captive
"$HOME/.claude/scripts/net-failover-phone.sh" || echo "net-failover: non-fatal error"

# 2) Дать сети устаканиться
sleep 8

# 3) ТОЛЬКО окно combine (asana+очередь). 6 resume-окон по mtime убраны 2026-06-08
#    (тормозящий несвязанный мусор — аудит 01-login-chain.md CRITICAL #1).
"$HOME/.claude/scripts/sessions-resume-launcher.sh" 0 || echo "sessions-resume: non-fatal error"

echo "bootstrap done $(date '+%H:%M:%S')"
