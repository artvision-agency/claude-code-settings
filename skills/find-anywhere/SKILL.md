---
name: find-anywhere
description: "Multi-source поиск перед выводом «не нашёл / нет нигде». Ищет доступ/токен/пароль/правило/факт сразу по всем источникам (tokens.json ×43, access.md ×9, memory, 301 jsonl, Keychain, git log -S, .env, config.yaml). Защита от false-negative. Триггеры: 'find-anywhere', 'найди везде', 'где лежит', 'есть ли доступ', 'где пароль', 'где токен', а также АВТО когда собираешься сказать «нет/не нашёл/не существует»."
---

# /find-anywhere — поиск по всем источникам до вывода «нет»

## Когда вызывать

**Автоматически** — перед ЛЮБЫМ негативным утверждением «нет доступа / не нашёл / не существует / нигде / только X / пробел». Прецеденты false-negative: avprocontext пароль, SEMrush правило, «п/ф не в словаре» (`self-corrections.md` #11/#16/#20).

**По команде:** «найди везде X», «где лежит X», «есть ли доступ к X», «где пароль/токен от X».

## Протокол

### Доступ / токен / пароль
```bash
~/.claude/scripts/cred-get.sh "<запрос>"
```
Скрипт обходит 6 источников: tokens.json, access.md, memory, jsonl, Keychain, git log -S.
Точечно:
- `cred-get.sh --json <ключ>` — значение из tokens.json
- `cred-get.sh --keychain <svc>` — из macOS Keychain

Карта где что лежит: `~/.claude/credentials-index.md`.

### Правило / инструкция (4 источника)
```bash
grep -ril "ТЕМА" ~/.claude/rules/ ~/artvision-data/.claude/rules/ \
  ~/.claude/projects/-Users-antonk/memory/ ~/.claude/skills/ 2>/dev/null
```

### Shorthand / сокращение (4 источника)
```bash
grep -ril "СОКРАЩЕНИЕ" ~/.claude/skills/shorthand/ \
  ~/.claude/projects/-Users-antonk/memory/ \
  ~/artvision-data/sync/recaps/ 2>/dev/null
find ~/.claude/projects/-Users-antonk -name "*.jsonl" -mtime -30 \
  -exec grep -il "СОКРАЩЕНИЕ" {} \; 2>/dev/null | head
```

### Клиент / проект / факт
```bash
grep -ril "ТЕМА" ~/artvision-data/clients/ ~/artvision-data/PROJECTS.md \
  ~/.claude/projects/-Users-antonk/memory/ 2>/dev/null
```

## Вывод

- **Найдено** → показать где (путь) + значение/факт.
- **Не найдено** → честный формат: «не найдено в: [перечислить ГДЕ искал]. Искал по: [паттерны]. Если есть — назови где.» НЕ «нет / не существует».

## Связано

- `~/.claude/credentials-index.md` — карта источников доступов
- `~/.claude/rules/no-false-negative.md` — правило
- `~/.claude/scripts/cred-get.sh` — helper
- `self-corrections.md` #11/#16/#20 — прецеденты false-negative
