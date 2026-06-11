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
#  1 = блок: найдены токены (Claude увидит список файлов и попробует другой подход)
#  2 = блок fail-CLOSED: проверка не смогла отработать (timeout find /
#      отсутствует зависимость / find упал) — НЕ пропускаем rm вслепую
#
# FAIL-CLOSED: если поиск токенов не довёл работу до конца (таймаут, ошибка
# find, нет бинаря timeout) — НЕЛЬЗЯ трактовать пустой результат как «токенов
# нет». Это блокировка (exit 2), а не разрешение. Иначе rm удалит credentials
# когда find просто не успел их перечислить.
#
# Bypass: CLEANUP_FORCE=1

set -uo pipefail

# Источник команды: $1 / env / stdin JSON (харнес обычно даёт tool_input через stdin).
# Если читать только из env — при stdin-payload CMD пуст -> exit 0 -> rm не проверяется
# (тот же класс fail-OPEN, что и в strip-guard). Поэтому добавлен stdin-fallback.
CMD="${1:-${CLAUDE_BASH_COMMAND:-${TOOL_INPUT_COMMAND:-}}}"
if [ -z "$CMD" ] && [ ! -t 0 ]; then
  STDIN_JSON="$(cat 2>/dev/null || true)"
  if [ -n "$STDIN_JSON" ] && command -v jq >/dev/null 2>&1; then
    CMD="$(printf '%s' "$STDIN_JSON" | jq -r '.tool_input.command // empty' 2>/dev/null || true)"
  fi
fi
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
# FAIL-CLOSED дизайн:
#   - explicit capture exit-кода timeout (НЕ '|| true' — иначе сбой → пустой
#     результат → ложное «токенов нет» → rm проходит при наличии токенов)
#   - sentinel-маркер '__SCAN_COMPLETE__' печатается ТОЛЬКО если цикл find
#     дошёл до конца. Его отсутствие = find не отработал (kill/ошибка).
TOKEN_PATTERNS='token|credential|secret|refresh_token|access_token|client_secret|\.pem$|\.key$|oauth'
SENTINEL='__SCAN_COMPLETE__'

# Зависимость: нужен бинарь timeout (или gtimeout на macOS). Нет → fail-CLOSED.
TIMEOUT_BIN=""
if command -v timeout >/dev/null 2>&1; then
  TIMEOUT_BIN="timeout"
elif command -v gtimeout >/dev/null 2>&1; then
  TIMEOUT_BIN="gtimeout"
fi

if [ -z "$TIMEOUT_BIN" ]; then
  echo "" >&2
  echo "⛔ pre-cleanup-tokens-check: ЗАБЛОКИРОВАНО (fail-closed)" >&2
  echo "" >&2
  echo "Команда:  $CMD" >&2
  echo "Причина: нет бинаря 'timeout'/'gtimeout' — проверка токенов невозможна." >&2
  echo "Затронутые пути: $matched_paths" >&2
  echo "" >&2
  echo "Не пропускаю rm вслепую на путях где могут лежать credentials." >&2
  echo "Установи coreutils (brew install coreutils) или используй CLEANUP_FORCE=1 осознанно." >&2
  exit 2
fi

# Запускаем поиск. stderr inner-скрипта НЕ глушим в /dev/null на уровне
# подстановки — только find'у разрешаем тихо падать на отдельных файлах.
scan_out=$("$TIMEOUT_BIN" 4 bash -c "
  for p in $matched_paths; do
    [ -e \"\$p\" ] || continue
    find \"\$p\" -maxdepth 6 -type f 2>/dev/null \
      | grep -iE '$TOKEN_PATTERNS' \
      | grep -vE '\.(log|cache|tmp|lock|md|txt|sample)\$'
  done
  # Маркер: достигается ТОЛЬКО если цикл завершился (не убит таймаутом)
  echo '$SENTINEL'
")
scan_rc=$?

# Разбор результата.
# scan_rc != 0 → timeout убил (124) либо bash/окружение упало (125/126/127/иное).
# Отсутствие sentinel → цикл не дошёл до конца (страховка от частичного вывода).
if [ "$scan_rc" -ne 0 ] || ! printf '%s\n' "$scan_out" | grep -qxF "$SENTINEL"; then
  echo "" >&2
  echo "⛔ pre-cleanup-tokens-check: ЗАБЛОКИРОВАНО (fail-closed)" >&2
  echo "" >&2
  echo "Команда:  $CMD" >&2
  echo "Затронутые пути: $matched_paths" >&2
  if [ "$scan_rc" -eq 124 ]; then
    echo "Причина: поиск токенов превысил таймаут (4с) — НЕ завершён." >&2
  else
    echo "Причина: поиск токенов не отработал (код $scan_rc, маркер завершения отсутствует)." >&2
  fi
  echo "" >&2
  echo "Пустой результат при незавершённом поиске НЕ значит «токенов нет»." >&2
  echo "Сужай область удаления (конкретная поддиректория без credentials)" >&2
  echo "или вручную убедись что токенов нет и используй CLEANUP_FORCE=1." >&2
  exit 2
fi

# Поиск ЗАВЕРШИЛСЯ корректно. Реальные находки = вывод без sentinel-строки,
# ограничиваем 20-ю для читаемости.
found=$(printf '%s\n' "$scan_out" | grep -vxF "$SENTINEL" | head -20)

if [ -z "$found" ]; then
  # find дошёл до конца И ничего не нашёл → действительно безопасно.
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
