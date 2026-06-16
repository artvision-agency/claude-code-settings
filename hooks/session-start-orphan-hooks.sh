#!/usr/bin/env bash
# session-start-orphan-hooks.sh — SessionStart хук (warn-only)
#
# Детектит «orphan-хуки»: hooks/*.sh, которые НЕ зарегистрированы в settings.json
# и НЕ входят в allowlist by-design-исключений. Прецедент: self-corrections #18 —
# post-kp-deploy-factcheck.sh лежал месяц незарегистрированным → ложная защита.
#
# warn-only: НИКОГДА не блокирует старт сессии (только stdout-нудж).
# Bypass: ORPHAN_SCAN_OFF=1
#
# By-design НЕ settings.json-хуки (исключаются из «orphan»):
#   *.test.sh            — тест-файлы хуков
#   _disabled_*          — намеренно отключены
#   pre-commit-secret-guard.sh — git-хук (.git/hooks/pre-commit, self-corr #31)
#   post-deploy-qa-smoke.sh    — вызывается из deploy-скриптов, не событие
#   hook-interaction-lint.sh   — ручной статик-анализатор
#   lib-*.sh / *-lib.sh        — библиотеки, source'ятся другими хуками

set -uo pipefail

[[ "${ORPHAN_SCAN_OFF:-0}" == "1" ]] && exit 0

HOOKS_DIR="$HOME/.claude/hooks"
SETTINGS="$HOME/.claude/settings.json"
[[ -d "$HOOKS_DIR" && -f "$SETTINGS" ]] || exit 0

# Allowlist (basename) — by-design не в settings.json
is_excluded() {
  case "$1" in
    *.test.sh|_disabled_*) return 0;;
    pre-commit-secret-guard.sh|post-deploy-qa-smoke.sh|hook-interaction-lint.sh) return 0;;
    lib-*.sh|*-lib.sh) return 0;;
  esac
  return 1
}

ORPHANS=()
for f in "$HOOKS_DIR"/*.sh; do
  [[ -f "$f" ]] || continue
  b="$(basename "$f")"
  is_excluded "$b" && continue
  # зарегистрирован в settings.json?
  grep -q "$b" "$SETTINGS" 2>/dev/null && continue
  # source'ится другим хуком? (библиотека/хелпер) → не orphan
  refs="$(grep -rl --include='*.sh' "$b" "$HOOKS_DIR" 2>/dev/null | grep -v "^${f}$" | wc -l | tr -d ' ')"
  [[ "${refs:-0}" -gt 0 ]] && continue
  ORPHANS+=("$b")
done

[[ ${#ORPHANS[@]} -eq 0 ]] && exit 0

echo "═══════════════════════════════════════════"
echo "⚠️  ORPHAN-ХУКИ: ${#ORPHANS[@]} файл(ов) есть, но НЕ зарегистрированы в settings.json"
echo "   (ложная защита — прецедент self-corrections #18)"
for o in "${ORPHANS[@]}"; do echo "   • $o"; done
echo "   → register в settings.json ЛИБО понизить правило до knowledge-only."
echo "   Bypass: ORPHAN_SCAN_OFF=1"
echo "═══════════════════════════════════════════"
exit 0
