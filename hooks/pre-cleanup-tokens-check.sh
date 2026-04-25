#!/usr/bin/env bash
# pre-cleanup-tokens-check.sh — блокирует rm -rf на cache-директориях,
# если внутри есть токены/credentials.
#
# Прецедент: 2026-04-17 при ENOSPC cleanup `rm -rf ~/.cache ~/.npm/_cacache`
# убил YouTube OAuth (youtube_token.json), invalid_grant, потребовалась
# ручная переавторизация.
#
# Подключается в ~/.claude/settings.json как PreToolUse(Bash) хук.
#
# Exit codes:
#  0 = безопасно (нет токенов в пути или не cleanup-операция)
#  1 = блок (Claude увидит список файлов и попробует другой подход)
#
# Bypass: CLEANUP_FORCE=1

set -uo pipefail

CMD="${1:-${CLAUDE_BASH_COMMAND:-}}"
[ -z "$CMD" ] && exit 0
[ "${CLEANUP_FORCE:-0}" = "1" ] && exit 0

# Триггер: rm -r* на cache-подобных путях
echo "$CMD" | grep -qE 'rm[[:space:]]+-[a-zA-Z]*[rR][a-zA-Z]*' || exit 0

# Извлечь пути после rm -r* (всё до конца строки или до &&/;/|)
TARGETS=$(echo "$CMD" | grep -oE 'rm[[:space:]]+-[a-zA-Z]+[[:space:]]+[^&;|]+' \
                     | sed -E 's/^rm[[:space:]]+-[a-zA-Z]+[[:space:]]+//')

# Список путей где могут лежать токены (расширенный, не только cache)
DANGER_PATHS=(
  "$HOME/.cache" "$HOME/.npm" "$HOME/.config" "$HOME/.local"
  "$HOME/.aws" "$HOME/.gcp" "$HOME/.azure"
  "$HOME/.gh" "$HOME/.config/gh"
  "$HOME/.gnupg" "$HOME/.ssh"
)

is_danger=0
matched_paths=""
for tgt in $TARGETS; do
  # Расширить ~ и $HOME
  expanded="${tgt/#\~/$HOME}"
  expanded="${expanded//\$HOME/$HOME}"
  for danger in "${DANGER_PATHS[@]}"; do
    case "$expanded" in
      "$danger"|"$danger"/*)
        is_danger=1
        matched_paths="$matched_paths $expanded"
        ;;
    esac
  done
done
[ "$is_danger" -eq 0 ] && exit 0

# Поиск токенов в matched_paths (timeout 4s)
TOKEN_PATTERNS='token|credential|secret|refresh_token|access_token|client_secret|\.pem$|\.key$|oauth'
found=$(timeout 4 bash -c "
  for p in $matched_paths; do
    [ -e \"\$p\" ] || continue
    find \"\$p\" -maxdepth 6 -type f 2>/dev/null \
      | grep -iE '$TOKEN_PATTERNS' \
      | grep -vE '\.(log|cache|tmp|lock|md|txt|sample)$' \
      | head -20
  done
" 2>/dev/null || true)

if [ -z "$found" ]; then
  exit 0
fi

echo "" >&2
echo "⛔ pre-cleanup-tokens-check: ЗАБЛОКИРОВАНО" >&2
echo "" >&2
echo "Команда:  $CMD" >&2
echo "Затронутые пути: $matched_paths" >&2
echo "" >&2
echo "Найдены файлы с признаками токена/credential:" >&2
echo "$found" | sed 's/^/  • /' >&2
echo "" >&2
echo "Прецедент: 17.04.2026 cleanup ~/.npm убил YouTube OAuth (invalid_grant)" >&2
echo "" >&2
echo "Безопасный путь:" >&2
echo "  1) Перенести токены в надёжное место:" >&2
echo "     mkdir -p ~/backup-tokens-\$(date +%Y%m%d) && cp <found-files> ~/backup-tokens-…/" >&2
echo "  2) Или удалить выборочно через find (исключив токены):" >&2
echo "     find <path> -type f \\! -name '*token*' \\! -name '*credential*' -delete" >&2
echo "  3) Или указать поддиректорию без токенов (например ~/.npm/_cacache, не ~/.npm целиком)" >&2
echo "" >&2
echo "Bypass (на свой риск): CLEANUP_FORCE=1 <команда>" >&2
exit 1
