#!/bin/bash
set -euo pipefail

# PostToolUse: Edit/Write — CRO-проверка при изменении UX-файлов (боты, лендинги, формы)
# Срабатывает на: handlers/, templates/, pages/, *.html с формами/кнопками

FILE_PATH="${CLAUDE_FILE_PATH:-}"

# Только для UX-файлов
case "$FILE_PATH" in
    */handlers/*.py|*/bot*.py|*/survey*.py|*/flow*.py|*/onboarding*|*/pages/*|*/templates/*)
        ;;
    *.html)
        # Только если есть кнопки/формы
        if ! grep -qiE 'button|form|onclick|callback|InlineKeyboard' "$FILE_PATH" 2>/dev/null; then
            exit 0
        fi
        ;;
    *)
        exit 0
        ;;
esac

# Проверка: лишние шаги в flow?
WARNINGS=""

# 1. Вопрос "хотите ли вы?" перед действием — антипаттерн
if grep -qiE 'хотите.*(оставить|написать|продолжить|начать)|do you want|would you like' "$FILE_PATH" 2>/dev/null; then
    WARNINGS="${WARNINGS}\n⚠️ CRO: Найден вопрос 'хотите ли?' — лучше сразу показать результат"
fi

# 2. Два подряд подтверждения
if grep -cE 'callback_data.*confirm|callback_data.*agree|callback_data.*yes' "$FILE_PATH" 2>/dev/null | grep -q '[2-9]'; then
    WARNINGS="${WARNINGS}\n⚠️ CRO: Несколько подтверждений подряд — каждый клик теряет 30-50% пользователей"
fi

if [ -n "$WARNINGS" ]; then
    echo -e "🎯 CRO-CHECK:${WARNINGS}"
    echo "Принцип: показывай готовый результат → предлагай разместить. Минимум кликов."
fi
