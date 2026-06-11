---
name: factcheck
description: "Фактчекинг HTML-страниц, КП, отчётов клиентов перед деплоем. 7 слоёв проверки: структура, извлечение данных, кросс-ссылки с ТЗ, HTTP-проверка ассетов, консистентность, numeric facts (Layer 5), domain validators (Layer 6), strict adversarial (Layer 7). Для финансовых документов — авто-route в /finance-factcheck. Триггеры: фактчек, factcheck, проверь страницу, проверь перед деплоем, validate html, проверь факты"
---

# Factcheck — проверка контента перед отправкой

## Что делает

7 слоёв автоматической проверки:
1. **Структура** — HTML теги, мета, телефоны, email, дубли ID
2. **Извлечение** — все числа, утверждения, имена, даты из текста
3. **Кросс-ссылки** — сравнение HTML с ТЗ, config.yaml, corrections-log
4. **Ассеты** — HTTP HEAD на все img/audio/video (200? размер?)
5. **Консистентность** — placeholder текст, пустые src, alt
6. **Numeric facts** (НОВЫЙ, factcheck-numeric.py) — для каждого числа URL-источник + повторный WebFetch
7. **Domain validators** (НОВЫЙ) — финансовые/юридические/медицинские специфичные проверки
8. **Strict adversarial** (НОВЫЙ, Agent strict-factchecker) — презумпция лжи параллельно

## Авто-route

Документы со ставками/налогами/инвестиционными инструментами → автоматически на **/finance-factcheck** (использует те же слои + специализированные финансовые валидаторы).

## Как использовать

### Вариант 1: файл указан
```
/factcheck clients/esenina/kp/index-v9.html
```

### Вариант 2: проверить по URL (VPS)
```
/factcheck clients/esenina/kp/index-v9.html --base-url https://artvision.pro/esenina
```

### Вариант 3: без аргументов — спросить
Если файл не указан, спросить у пользователя какой файл проверять.

## Алгоритм

1. Определить файл для проверки (из аргументов или спросить)
2. Определить клиента из пути (`clients/[name]/`)
3. Автоматически найти source-файлы:
   - `clients/[name]/config.yaml`
   - `clients/[name]/patches/corrections-log-*.md`
   - `clients/[name]/context-log.md`
4. Определить base-url если файл уже на VPS:
   - `clients/esenina/` → `https://artvision.pro/esenina`
   - `clients/ant-partners/` → `https://artvision.pro/ant-test`
5. Запустить:
```bash
python3 ~/.claude/scripts/factcheck-v2.py <file> \
  --source <sources> \
  --base-url <url> \
  --report /tmp/factcheck-<client>-<date>.md \
  --standard
```
6. Показать результат пользователю таблицей
7. Если есть CRITICAL — предложить исправить
8. Если всё ОК — предложить задеплоить

## Режимы
- `--quick` — только структура + ассеты (10 сек)
- `--standard` — + кросс-ссылки (1 мин) **[по умолчанию для не-КП]**
- `--strict` — + спавн strict-factchecker агента (презумпция лжи, WebFetch источников) **[АВТО для КП]**

## Автоопределение strict-режима

Путь файла матчит `presales/*/kp/*.html` или `clients/*/kp/*.html` → **автоматически strict**:

1. Запустить `factcheck-strict.py` (Layer 1: factcheck-v2 --standard)
2. Спавнить `Agent(subagent_type=strict-factchecker)` для Layer 2
3. Агент проверяет каждое число по правилам strict (см. `~/.claude/agents/strict-factchecker.md`):
   - Презумпция лжи
   - 2+ источника через WebFetch
   - "Оценочно"/"~" без дисклеймера = CRITICAL
   - Прогнозы без методологии = CRITICAL
   - UNCONFIRMED из source-reports без бейджа в КП = CRITICAL
4. Verdict: BLOCK / CONDITIONAL / PASS
5. BLOCK → не деплоить. CONDITIONAL → добавить дисклеймеры → PASS.

Хук `pre-scp-factcheck.sh` блокирует scp для КП до прохождения обоих слоёв.

Bypass: `FACTCHECK_SKIP=1 scp ...` — на свой риск.

## Интерпретация результатов

| Статус | Значение | Действие |
|--------|---------|----------|
| ✅ PASS | Проверка пройдена | Ничего |
| ⚠️ WARN | Предупреждение | Показать, но не блокировать |
| ❌ CRITICAL | Критическая ошибка | БЛОКИРОВАТЬ деплой, предложить фикс |
| ℹ️ INFO | Информация | Показать для контекста |
