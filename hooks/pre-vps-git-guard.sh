#!/usr/bin/env bash
# pre-vps-git-guard.sh — блокирует деструктивные git операции через ssh на VPS.
#
# Прецедент: 2026-04-23 потеря коммита 9973dc3 (filter qa_smoke от 19.04)
# в результате `git pull --rebase` через ssh без проверки локальных коммитов.
#
# Подключается в ~/.claude/settings.json как PreToolUse(Bash) хук.
#
# Exit codes:
#  0 = безопасно или не VPS-git операция (пропуск)
#  1 = заблокировано (Claude увидит stderr и попробует другой подход)
#
# Bypass: VPS_GIT_FORCE=1 ssh ... git ...

set -uo pipefail

CMD="${1:-${CLAUDE_BASH_COMMAND:-}}"
[ -z "$CMD" ] && exit 0

# Bypass
[ "${VPS_GIT_FORCE:-0}" = "1" ] && exit 0

# Должна быть ssh-команда с git внутри
echo "$CMD" | grep -qE '(^|[[:space:]]|&&|;|\|)[[:space:]]*ssh[[:space:]]' || exit 0
echo "$CMD" | grep -qE 'git[[:space:]]+(pull|reset|push|clean|checkout|rebase|merge)' || exit 0

block() {
  echo "" >&2
  echo "⛔ pre-vps-git-guard: ЗАБЛОКИРОВАНО — $1" >&2
  echo "" >&2
  echo "Прецедент: 23.04.2026 потеря коммита 9973dc3 (filter qa_smoke)" >&2
  echo "Причина блока: $2" >&2
  echo "" >&2
  echo "Безопасный путь:" >&2
  echo "  1) ssh <host> 'cd <repo> && git fetch && git status'" >&2
  echo "  2) ssh <host> 'cd <repo> && git log HEAD..origin/<br> --oneline'" >&2
  echo "  3) Если локальных коммитов нет → можно $3" >&2
  echo "  4) Если есть → cherry-pick/merge на dev машине, затем push, затем pull --ff-only на VPS" >&2
  echo "" >&2
  echo "Bypass (на свой риск): VPS_GIT_FORCE=1 <команда>" >&2
  exit 1
}

# 1. git pull --rebase / pull без --ff-only — самый прецедентный случай
if echo "$CMD" | grep -qE 'git[[:space:]]+pull[[:space:]]+--rebase'; then
  block "ssh + git pull --rebase" \
        "rebase молча перезаписывает историю VPS, локальные коммиты теряются" \
        "git pull --ff-only"
fi

if echo "$CMD" | grep -qE 'git[[:space:]]+pull([[:space:]]|$)' \
   && ! echo "$CMD" | grep -qE '\-\-ff-only'; then
  block "ssh + git pull без --ff-only" \
        "default merge-pull может создать merge-коммит на VPS или (с rebase.autoStash) потерять stash" \
        "git pull --ff-only"
fi

# 2. git reset --hard
if echo "$CMD" | grep -qE 'git[[:space:]]+reset[[:space:]]+--hard'; then
  block "ssh + git reset --hard" \
        "необратимо удаляет локальные коммиты и working tree" \
        "git stash + git fetch (без reset)"
fi

# 3. git push --force / -f
if echo "$CMD" | grep -qE 'git[[:space:]]+push[[:space:]]+(-f([[:space:]]|$)|--force([[:space:]]|$))'; then
  block "ssh + git push --force" \
        "перезаписывает remote, ломает работу других" \
        "git push --force-with-lease (с явной проверкой ref)"
fi

# 4. git clean -f / -fd / -fdx
if echo "$CMD" | grep -qE 'git[[:space:]]+clean[[:space:]]+-[a-z]*f'; then
  block "ssh + git clean -f" \
        "необратимо удаляет неотслеживаемые файлы (могут быть .env, логи, временные данные)" \
        "git clean -n (dry-run) сначала"
fi

# 5. git checkout -- . / git checkout HEAD .
if echo "$CMD" | grep -qE 'git[[:space:]]+checkout[[:space:]]+(--|HEAD)[[:space:]]+\.'; then
  block "ssh + git checkout -- ." \
        "необратимо отбрасывает все uncommitted changes" \
        "git stash сначала"
fi

exit 0
