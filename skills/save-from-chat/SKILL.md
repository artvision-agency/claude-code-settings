---
name: save-from-chat
description: "Сохранить артефакты из claude.ai в git. Использовать когда есть результаты работы на claude.ai (HTML, тексты, КП, решения) которые нужно зафиксировать в репозитории."
disable-model-invocation: false
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - AskUserQuestion
---

# Save from Chat — Сохранение артефактов из claude.ai в git

Когда работа ведётся на claude.ai, результаты (HTML, тексты, КП, решения) не попадают в git автоматически. Этот скилл помогает зафиксировать их.

## Режимы использования

### 1. Пользователь указал клиента: `/save-from-chat [клиент]`

1. Определить slug клиента
2. Проверить существование `clients/[slug]/` в artvision-data
3. Если нет — создать по шаблону из `clients/_template/`
4. Спросить что сохранить (AskUserQuestion):
   - HTML файлы (из Downloads или вставленные)
   - Текстовый контент (статьи, описания)
   - КП / презентации
   - Решения / контекст (→ `/context`)
   - config.yaml (дизайн-система)

### 2. Пользователь вставил контент: `/save-from-chat` + текст

1. Определить тип контента (HTML, markdown, YAML, текст)
2. Спросить к какому клиенту относится
3. Определить куда сохранить:
   - HTML → `clients/[slug]/output_v6/`
   - КП → `clients/[slug]/kp/`
   - Текст/статья → `clients/[slug]/content/`
   - Решение → вызвать `/context`
   - config.yaml → `clients/[slug]/config.yaml`

### 3. Автосканирование Downloads: `/save-from-chat --scan`

1. Найти в `~/Downloads/` свежие файлы (последние 24ч):
   ```bash
   find ~/Downloads -maxdepth 1 -name "*.html" -mtime -1 -o -name "*.md" -mtime -1 | sort
   ```
2. Показать список найденных файлов
3. Для каждого спросить: к какому клиенту? куда сохранить?
4. Скопировать и закоммитить

## Порядок действий

```
1. ОПРЕДЕЛИТЬ — что за артефакт и какой клиент
2. ПРОВЕРИТЬ — есть ли папка клиента (создать если нет)
3. СОХРАНИТЬ — в правильную подпапку
4. КОММИТ — git add + commit + push
5. ASANA — создать задачу если есть follow-up действия
```

## Формат коммита

```
feat(clients): save [тип] for [клиент] from claude.ai

Артефакт перенесён из claude.ai сессии.
Тип: [HTML/КП/контент/config]

Co-Authored-By: Claude <noreply@anthropic.com>
```

## Проверка после сохранения

- HTML: проверить отсутствие внешних URL (`grep -oE 'https?://[^"'"'"'> ]+' file.html`)
- config.yaml: проверить синтаксис (`python3 -c "import yaml; yaml.safe_load(open('file'))"`)
- Размер: предупредить если HTML > 500KB

## Важно

- НЕ публиковать на сайт/CMS — только в git
- Если артефакт — КП с дизайн-системой, сохранить также config.yaml
- Если есть промежуточные версии (v1, v2, v3) — сохранить все
- Если есть промпт генерации — сохранить в `kp/` как `*_prompt.md`
