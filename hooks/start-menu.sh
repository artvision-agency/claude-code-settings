#!/usr/bin/env bash
# start-menu.sh — SessionStart hook: единое меню перекрёстка.
# Тонкая обёртка над session-menu.sh, чтобы хук можно было отключать независимо.
#
# Регистрация: ~/.claude/settings.json → hooks.SessionStart (последним).
# Output идёт пользователю как часть SessionStart-контекста.

set -Eeuo pipefail
exec "${HOME}/.claude/scripts/session-menu.sh"
