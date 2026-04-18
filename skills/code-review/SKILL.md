---
name: code-review
description: "Code review изменений в сессии. Лёгкий (1 проход) — для коммитов. Для глубокого аудита используй /code-audit."
---

# /code-review — Code Review

## Когда вызывать
- Перед коммитом (автотриггер: `post-edit-skill-trigger.sh` при 5+ файлах)
- По запросу "ревью", "посмотри код", "review"
- После superpowers:requesting-code-review (дополняет его)

## Шаги

### 1. Собрать diff

```bash
git diff --stat
git diff --cached --stat
git diff HEAD
```

### 2. Проверить по чеклисту

| Категория | Что искать |
|-----------|-----------|
| **Баги** | Необработанные exceptions, race conditions, пустые catch |
| **Security** | Hardcoded tokens, SQL injection, XSS, open redirects |
| **Логика** | Off-by-one, неправильные условия, забытый else |
| **Стиль** | Мёртвый код, console.log/print, TODO без issue |
| **Контракт** | Изменился API? Обновлены ли вызывающие? |
| **Тесты** | Есть тесты для изменённого кода? Нужны новые? |

### 3. Python-специфика (artvision стек)

- `import` — нет ли shadowing (п.7 self-corrections: `from config import` vs stdlib)
- `async/await` — нет ли забытого await
- aiogram: handler без `@router.` декоратора = мёртвый код
- bot.py: проверить что FSM states корректно переключаются

### 4. HTML-специфика (клиентские страницы)

- Внешние CDN (tailwind CDN = не работает на iOS Safari)
- viewport, lang, canonical
- Inline CSS > external CSS для автономности
- Фото: реальные или placeholder?

### 5. Формат вывода

```
CODE REVIEW: [файлы]
═══════════════════

🔴 CRITICAL (блокирует коммит):
  1. [файл:строка] — описание

🟡 IMPORTANT (исправить до деплоя):
  1. [файл:строка] — описание

🟢 SUGGESTIONS (можно позже):
  1. [файл:строка] — описание

Тесты: [есть/нет/нужны новые]
Вердикт: [OK / ИСПРАВИТЬ / ПЕРЕПИСАТЬ]
```

## Связь с другими скиллами

- **superpowers:requesting-code-review** → процесс ("что ревьюить, зачем") → потом этот скилл
- **superpowers:receiving-code-review** → когда ПОЛУЧИЛ фидбек на своё ревью
- **/code-audit** → глубокий аудит (4 параллельных агента) — для рефакторинга, не для коммитов
- **/verification-loop** → техническая проверка (build, lint, test) — дополняет, не заменяет
