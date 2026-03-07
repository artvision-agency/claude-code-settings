#!/bin/bash
# Pre-read hook: проверка размера файла перед чтением
# Срабатывает автоматически перед каждым Read tool

FILE_PATH="$1"

# Проверяем что файл существует
if [ ! -f "$FILE_PATH" ]; then
  exit 0  # Пропускаем, файл не найден (будет обработано в Read)
fi

# Подсчитываем строки
LINE_COUNT=$(wc -l < "$FILE_PATH" 2>/dev/null || echo 0)

# Оценка токенов (примерно 1 токен = 4 символа, средняя строка ~80 символов)
ESTIMATED_TOKENS=$((LINE_COUNT * 20))

# Уровни предупреждения
if [ "$LINE_COUNT" -gt 10000 ]; then
  echo "🚨 КРИТИЧЕСКИЙ РАЗМЕР ФАЙЛА"
  echo "   Файл: $(basename "$FILE_PATH")"
  echo "   Строк: $LINE_COUNT"
  echo "   Токенов (оценка): ~$ESTIMATED_TOKENS"
  echo ""
  echo "💡 РЕКОМЕНДАЦИИ:"
  echo "   1. Используйте Grep для поиска конкретного содержимого"
  echo "   2. Используйте Read с offset/limit для чтения частями"
  echo "   3. Примеры:"
  echo "      Grep(pattern='искомый_текст', path='$FILE_PATH')"
  echo "      Read(file_path='$FILE_PATH', offset=0, limit=500)"
  echo ""
  echo "ЗАБЛОКИРОВАНО. Используйте Grep или Read с offset/limit."
  exit 2  # Блокируем операцию

elif [ "$LINE_COUNT" -gt 5000 ]; then
  echo "⚠️  БОЛЬШОЙ ФАЙЛ"
  echo "   Файл: $(basename "$FILE_PATH")"
  echo "   Строк: $LINE_COUNT"
  echo "   Токенов (оценка): ~$ESTIMATED_TOKENS"
  echo ""
  echo "Рекомендуется: Grep или Read с offset/limit"
  # exit 1 = предупреждение (Claude увидит и решит)

elif [ "$LINE_COUNT" -gt 2000 ]; then
  echo "ℹ️  Файл: $(basename "$FILE_PATH") ($LINE_COUNT строк, ~$ESTIMATED_TOKENS токенов)"
fi

# Продолжаем выполнение
exit 0
