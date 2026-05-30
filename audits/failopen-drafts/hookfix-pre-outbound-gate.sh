#!/bin/bash
# PreToolUse(Bash): блокирует отправку наружу клиенту без ACK Антона.
# Триггеры: curl к клиентским доменам, scp на клиентские VPS, mailx/sendmail,
#           telegram bot send_message к клиентским chat_id.
# ACK: файл /tmp/.claude_outbound_ack (создаётся Антоном) или ключевое слово --ack-anton в команде.
#
# FAIL-CLOSED (фикс 2026-05-30): ошибка парса stdin / отсутствие python3 / любая
# невозможность достоверно определить команду => БЛОКИРОВАТЬ (exit 2), НЕ пропускать.
# Раньше сбой парса делал CMD пустым и хук тихо выходил exit 0 (fail-OPEN),
# пропуская scp/email/telegram на чужой хост.

set -uo pipefail

# ── Чтение stdin ───────────────────────────────────────────────────────────
INPUT=$(cat)

# Пустой stdin = харнес не передал payload. Без payload мы не можем удостовериться
# что это безопасная команда => fail-CLOSED.
if [ -z "${INPUT}" ]; then
  cat <<'EOF'
🛑 OUTBOUND-GATE (fail-closed): пустой ввод от харнеса — невозможно проверить команду.
Хук не может удостовериться что отправки наружу нет, поэтому БЛОКИРУЕТ.
Если это ложное срабатывание — проверь почему PreToolUse получил пустой stdin.
EOF
  exit 2
fi

# ── Обязательная зависимость: python3 ───────────────────────────────────────
# Без парсера JSON мы не можем извлечь команду => fail-CLOSED (а не доверять пустоте).
if ! command -v python3 >/dev/null 2>&1; then
  cat <<'EOF'
🛑 OUTBOUND-GATE (fail-closed): python3 недоступен — невозможно распарсить tool_input.
Хук не может определить команду, поэтому БЛОКИРУЕТ отправку наружу.
Установи python3 либо проверь PATH harness-окружения.
EOF
  exit 2
fi

# ── Парс команды с явным статусом ───────────────────────────────────────────
# Важно: НЕ глотаем ошибку молча. Питон печатает сам command в stdout и
# выходит с кодом 0 ТОЛЬКО при валидном JSON-объекте с корректной структурой.
# Любой сбой (malformed JSON, исключение, неверный тип) => код 3 => fail-CLOSED.
PARSE_OUT=$(printf '%s' "${INPUT}" | python3 -c '
import sys, json
try:
    data = json.load(sys.stdin)
except Exception as e:
    sys.stderr.write("parse-error: %s\n" % e)
    sys.exit(3)
if not isinstance(data, dict):
    sys.stderr.write("parse-error: top-level JSON is not an object\n")
    sys.exit(3)
ti = data.get("tool_input", {})
if not isinstance(ti, dict):
    sys.stderr.write("parse-error: tool_input is not an object\n")
    sys.exit(3)
cmd = ti.get("command", "")
if cmd is None:
    cmd = ""
sys.stdout.write(str(cmd))
sys.exit(0)
')
PARSE_RC=$?

# Сбой парса (malformed JSON / неверная структура / исключение / python crash)
# => БЛОКИРОВАТЬ. Это и есть исправляемая дыра: раньше тут было тихое exit 0.
if [ "${PARSE_RC}" -ne 0 ]; then
  cat <<EOF
🛑 OUTBOUND-GATE (fail-closed): не удалось распарсить tool_input (код ${PARSE_RC}).
Хук не может достоверно определить команду => БЛОКИРУЕТ отправку наружу.
Это защита: при сбое парса раньше команда проходила без проверки.
EOF
  exit 2
fi

CMD="${PARSE_OUT}"

# ── Команда успешно распарсена ──────────────────────────────────────────────
# Достоверно пустая команда (валидный JSON, command == "") = нет исходящего
# действия => безопасно пропустить. Это НЕ то же самое что сбой парса выше.
if [ -z "${CMD}" ]; then
  exit 0
fi

# ── ACK-байпас (легитимный, сохранён как есть) ──────────────────────────────
if echo "${CMD}" | grep -q -- '--ack-anton'; then
  exit 0
fi
if [ -f /tmp/.claude_outbound_ack ]; then
  # one-shot: потребить файл
  rm -f /tmp/.claude_outbound_ack
  exit 0
fi

# ── Паттерны исходящих действий к клиентам ──────────────────────────────────
OUTBOUND=0
REASON=""

# scp/rsync на клиентские VPS (кроме наших)
if echo "${CMD}" | grep -qE '\b(scp|rsync)\b'; then
  if echo "${CMD}" | grep -qvE '80\.90\.181\.152|147\.45\.232\.226|localhost|127\.0\.0\.1'; then
    if echo "${CMD}" | grep -qE '@[a-zA-Z0-9.-]+:'; then
      OUTBOUND=1
      REASON="scp/rsync к внешнему хосту"
    fi
  fi
fi

# Email отправка
if echo "${CMD}" | grep -qE '\b(mail|mailx|sendmail|msmtp)\b.*@'; then
  OUTBOUND=1
  REASON="email отправка"
fi

# TG bot sendMessage / WebFetch POST к api.telegram.org с клиентским chat_id
# (группа команды — не блокируем)
TEAM_CHAT_IDS="-1001234567890"  # заглушка — реальные team chat_id можно добавить
if echo "${CMD}" | grep -qE 'api\.telegram\.org/bot[^/]+/sendMessage'; then
  # Если не указан team chat — считаем outbound
  OUTBOUND=1
  REASON="Telegram sendMessage"
fi

# gh pr create / gh issue create к публичным репо клиента — не трогаем пока

if [ "${OUTBOUND}" -eq 1 ]; then
  cat <<EOF
🛑 OUTBOUND-GATE: обнаружена попытка отправки наружу клиенту.
Причина: ${REASON}
Команда: $(echo "${CMD}" | head -c 200)

Перед отправкой:
  1. Покажи Антону контент (deploy на ревью-URL ОК).
  2. Получи ACK → одно из:
     • touch /tmp/.claude_outbound_ack  (one-shot байпас)
     • добавь --ack-anton в команду
EOF
  exit 2
fi

exit 0
