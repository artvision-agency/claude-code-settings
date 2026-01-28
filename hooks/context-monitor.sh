#!/bin/bash
# Context Monitor: отслеживает размер контекста и предупреждает о переполнении
# Срабатывает периодически во время сессии

# Получаем текущее использование токенов из переменных окружения (если доступны)
CURRENT_TOKENS="${CLAUDE_CONTEXT_TOKENS:-0}"
MAX_TOKENS=200000
WARNING_THRESHOLD=150000  # 75%
CRITICAL_THRESHOLD=180000 # 90%

# Если информация недоступна, пытаемся получить из последней сессии
if [ "$CURRENT_TOKENS" -eq 0 ]; then
  # Проверяем последний лог сессии
  LATEST_LOG=$(ls -t ~/.claude/debug/*.txt 2>/dev/null | head -1)
  if [ -f "$LATEST_LOG" ]; then
    # Ищем упоминания токенов в логе
    LAST_TOKEN_COUNT=$(grep -o "prompt is too long: [0-9]* tokens" "$LATEST_LOG" 2>/dev/null | tail -1 | grep -o "[0-9]*" || echo 0)
    if [ "$LAST_TOKEN_COUNT" -gt 0 ]; then
      CURRENT_TOKENS=$LAST_TOKEN_COUNT
    fi
  fi
fi

# Вычисляем процент использования
if [ "$CURRENT_TOKENS" -gt 0 ]; then
  PERCENT=$((CURRENT_TOKENS * 100 / MAX_TOKENS))

  if [ "$CURRENT_TOKENS" -ge "$CRITICAL_THRESHOLD" ]; then
    echo "🔴 КРИТИЧЕСКИЙ УРОВЕНЬ КОНТЕКСТА: $CURRENT_TOKENS / $MAX_TOKENS токенов ($PERCENT%)"
    echo ""
    echo "⚠️  ДЕЙСТВИЯ:"
    echo "   1. Завершите текущую задачу"
    echo "   2. Начните НОВУЮ сессию (очистит контекст)"
    echo "   3. Или используйте Task tool для изоляции"
    echo ""

  elif [ "$CURRENT_TOKENS" -ge "$WARNING_THRESHOLD" ]; then
    echo "🟡 Предупреждение: контекст $CURRENT_TOKENS / $MAX_TOKENS токенов ($PERCENT%)"
    echo "💡 Рекомендуется завершить сессию после текущей задачи"
    echo ""
  fi
fi

exit 0
