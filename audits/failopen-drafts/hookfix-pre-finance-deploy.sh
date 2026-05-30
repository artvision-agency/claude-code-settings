#!/usr/bin/env bash
# pre-finance-deploy.sh
# PreToolUse hook — независимая проверка финансовых документов перед scp/Edit deploy
#
# Триггер: scp/Edit/Write на HTML/MD файл в personal/finance/ или personal/ipoteka/ или /preview/savings-*
# Действие: запустить factcheck-numeric.py (Layer 5) для проверки числовых ставок vs офсайт банка
#
# Exit codes:
#   0 = proceed (все обязательные проверки прошли)
#   2 = BLOCK — fail-CLOSED:
#         * числовые расхождения >0.5 п.п. (Layer 5) ИЛИ domain-fail (Layer 6), ИЛИ
#         * обязательный factcheck-скрипт отсутствует/нечитаем/упал (зависимость недоступна).
#       Финансовый/банк-документ НЕ деплоится без подтверждённой проверки.
#
# Bypass: FINANCE_DEPLOY_SKIP=1 (осознанный обход; не ослабляет fail-closed по умолчанию)

set -uo pipefail

readonly FACTCHECK_NUMERIC="/Users/antonk/artvision-data/.claude-shared/scripts/factcheck-numeric.py"
readonly FACTCHECK_DOMAIN="/Users/antonk/artvision-data/.claude-shared/scripts/factcheck-finance-domain.py"
readonly FINANCE_PATTERN='(personal/finance|personal/ipoteka|personal/savings|/preview/savings-|/preview/finance-|/preview/calculator-)'

log_info()  { printf '[pre-finance-deploy] %s\n' "$*" >&2; }
log_warn()  { printf '[pre-finance-deploy] WARN: %s\n' "$*" >&2; }
log_block() { printf '[pre-finance-deploy] BLOCK: %s\n' "$*" >&2; }

COMMAND="${CLAUDE_BASH_COMMAND:-${1:-}}"
TOOL_NAME="${CLAUDE_TOOL_NAME:-Bash}"

# Bypass
if [[ "${FINANCE_DEPLOY_SKIP:-}" == "1" ]]; then
    log_warn "FINANCE_DEPLOY_SKIP=1 — bypass"
    exit 0
fi

# Only trigger on scp commands (Edit/Write handled separately)
if [[ "$TOOL_NAME" == "Bash" ]]; then
    if ! printf '%s' "$COMMAND" | grep -qE '^\s*scp\b'; then
        exit 0
    fi
    if ! printf '%s' "$COMMAND" | grep -qE "$FINANCE_PATTERN"; then
        exit 0
    fi

    # Extract HTML file
    HTML_FILE=$(printf '%s' "$COMMAND" | grep -oE '[^ ]+\.html' | head -1)
    if [[ -z "$HTML_FILE" ]]; then
        exit 0
    fi

    HTML_FILE="${HTML_FILE/#\~/$HOME}"
    if [[ ! -f "$HTML_FILE" ]]; then
        ALT="/Users/antonk/artvision-data/$HTML_FILE"
        if [[ -f "$ALT" ]]; then
            HTML_FILE="$ALT"
        else
            log_warn "Файл не найден: $HTML_FILE — пропуск"
            exit 0
        fi
    fi

    log_info "Финансовый документ обнаружен: $(basename "$HTML_FILE")"

    # FAIL-CLOSED: обязательный скрипт Layer 5. Отсутствие/нечитаемость зависимости =
    # БЛОК, а не тихий пропуск проверки банк-документа.
    if [[ ! -f "$FACTCHECK_NUMERIC" || ! -r "$FACTCHECK_NUMERIC" ]]; then
        log_block "Обязательный скрипт factcheck-numeric.py НЕ НАЙДЕН/НЕЧИТАЕМ: $FACTCHECK_NUMERIC"
        log_block "Финансовый документ НЕ может быть проверен (Layer 5) — деплой ЗАБЛОКИРОВАН (fail-closed)"
        printf '{"decision":"block","reason":"FAIL-CLOSED: обязательный factcheck-numeric.py отсутствует или нечитаем (%s). Финансовый документ не проверен (Layer 5). Восстановите скрипт. Осознанный обход только: FINANCE_DEPLOY_SKIP=1"}\n' "$FACTCHECK_NUMERIC"
        exit 2
    fi

    REPORT="/tmp/factcheck-numeric-$(date +%Y%m%d-%H%M%S).md"
    printf '\n═══════════════════════════════════════════\n' >&2
    printf '  PRE-FINANCE-DEPLOY: numeric factcheck\n' >&2
    printf '  Файл: %s\n' "$(basename "$HTML_FILE")" >&2
    printf '═══════════════════════════════════════════\n' >&2

    # Layer 5 — numeric factcheck
    NUMERIC_OK=0
    if python3 "$FACTCHECK_NUMERIC" "$HTML_FILE" --no-fetch --report "$REPORT" 2>&1; then
        NUMERIC_OK=1
        printf '  Layer 5 (numeric): ✅ PASS\n' >&2
    else
        printf '  Layer 5 (numeric): ❌ MISMATCH\n' >&2
        printf '  Report: %s\n' "$REPORT" >&2
    fi

    # Layer 6 — domain validators
    # FAIL-CLOSED: обязательный скрипт Layer 6. Отсутствие/нечитаемость = БЛОК,
    # а не тихий пропуск с DOMAIN_OK=1.
    DOMAIN_REPORT="${REPORT%.md}-domain.md"
    DOMAIN_OK=0
    if [[ ! -f "$FACTCHECK_DOMAIN" || ! -r "$FACTCHECK_DOMAIN" ]]; then
        log_block "Обязательный скрипт factcheck-finance-domain.py НЕ НАЙДЕН/НЕЧИТАЕМ: $FACTCHECK_DOMAIN"
        log_block "Финансовый документ НЕ может быть проверен (Layer 6) — деплой ЗАБЛОКИРОВАН (fail-closed)"
        printf '{"decision":"block","reason":"FAIL-CLOSED: обязательный factcheck-finance-domain.py отсутствует или нечитаем (%s). Финансовый документ не проверен (Layer 6). Восстановите скрипт. Осознанный обход только: FINANCE_DEPLOY_SKIP=1"}\n' "$FACTCHECK_DOMAIN"
        exit 2
    fi
    # PIPESTATUS используется чтобы поймать exit-код python3, а не tail (иначе
    # сбой/парс-ошибка factcheck маскируется успешным tail = fail-OPEN).
    python3 "$FACTCHECK_DOMAIN" "$HTML_FILE" --report "$DOMAIN_REPORT" 2>&1 | tail -3 >&2
    if [[ "${PIPESTATUS[0]}" -eq 0 ]]; then
        DOMAIN_OK=1
        printf '  Layer 6 (domain): ✅ PASS\n' >&2
    else
        printf '  Layer 6 (domain): ❌ FAIL\n' >&2
        printf '  Domain report: %s\n' "$DOMAIN_REPORT" >&2
    fi

    if [[ $NUMERIC_OK -eq 1 && $DOMAIN_OK -eq 1 ]]; then
        printf '═══════════════════════════════════════════\n\n' >&2
        exit 0
    fi

    printf '\n  Bypass: FINANCE_DEPLOY_SKIP=1 %s\n' "$COMMAND" >&2
    printf '═══════════════════════════════════════════\n\n' >&2
    printf '{"decision":"block","reason":"Финансовый документ: Layer 5 OK=%s, Layer 6 OK=%s. Reports: %s + %s. Bypass: FINANCE_DEPLOY_SKIP=1"}\n' "$NUMERIC_OK" "$DOMAIN_OK" "$REPORT" "$DOMAIN_REPORT"
    exit 2
fi

exit 0
