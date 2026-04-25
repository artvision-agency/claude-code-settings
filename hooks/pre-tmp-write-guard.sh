#!/usr/bin/env bash
# pre-tmp-write-guard.sh — блокирует Write/Edit скриптовых файлов в /tmp.
#
# Прецедент: 2026-04-23 потеря /tmp/gen_dental_reports.py при reboot,
# ~30 мин на пересоздание. /tmp очищается при перезагрузке macOS.
#
# Подключается в ~/.claude/settings.json как PreToolUse(Write|Edit) хук.
#
# Exit codes:
#  0 = безопасно (не /tmp или не скриптовое расширение)
#  1 = блок (Claude увидит stderr и попробует другой путь)
#
# Bypass: TMP_WRITE_FORCE=1

set -uo pipefail

PATH_ARG="${1:-${CLAUDE_FILE_PATH:-}}"
[ -z "$PATH_ARG" ] && exit 0

# Bypass
[ "${TMP_WRITE_FORCE:-0}" = "1" ] && exit 0

# Только /tmp/* или /var/tmp/* или /private/tmp/* (macOS)
case "$PATH_ARG" in
  /tmp/*|/var/tmp/*|/private/tmp/*) ;;
  *) exit 0 ;;
esac

# Только скриптовые/код-файлы (не текстовые fixtures, логи)
case "$PATH_ARG" in
  *.py|*.sh|*.js|*.ts|*.tsx|*.jsx|*.rb|*.go|*.rs|*.php|*.java|*.kt|*.swift|*.c|*.cpp|*.h) ;;
  *) exit 0 ;;
esac

echo "" >&2
echo "⛔ pre-tmp-write-guard: $PATH_ARG" >&2
echo "" >&2
echo "Прецедент: 23.04.2026 потеря /tmp/gen_dental_reports.py при reboot (~30 мин работы)" >&2
echo "/tmp очищается при перезагрузке macOS — скриптовые файлы там терять нельзя." >&2
echo "" >&2
echo "Куда писать вместо /tmp:" >&2
echo "  • Разовый скрипт   → ~/.claude_temp_scripts/" >&2
echo "  • Часть проекта    → <repo>/scripts/" >&2
echo "  • Эксперимент      → ~/scratch/  (создать если нет)" >&2
echo "" >&2
echo "Bypass (если правда нужно в /tmp): TMP_WRITE_FORCE=1" >&2
exit 1
