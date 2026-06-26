---
name: ant-deploy
disable-model-invocation: true
description: "Деплой страниц ANT Partners на тестовый сервер. Полный pipeline: preflight → generate → upload → verify. Триггеры: 'ant deploy', 'залей ant', 'деплой ant', 'загрузи ant страницы'"
---

# ANT Partners Deploy

Единый pipeline деплоя страниц ANT Partners на `ant-dev.artvision.pro`.

## ОБЯЗАТЕЛЬНО ПЕРЕД ДЕПЛОЕМ

1. Прочитать `clients/ant-partners/CLAUDE.md`
2. Прочитать все `clients/ant-partners/patches/*.md`

## Pipeline

```bash
cd /Users/antonk/artvision-data/clients/ant-partners/templates/

# 1. Preflight (JSON valid, images exist, hubs intact, sections stable)
bash ant-preflight.sh

# 2. Generate + validate
python3 generate_page.py --template master-template.html --content pages/ --output output_v7/for_client/
python3 validate_pages.py

# 3. Deploy (preflight + generate + upload + verify)
bash ant-deploy.sh              # полный деплой
bash ant-deploy.sh --skip-images  # без картинок
bash ant-deploy.sh --pages-only   # только HTML
bash ant-deploy.sh --dry-run      # предпросмотр
```

## Или одной командой:

```bash
bash ant-deploy.sh
```

Скрипт автоматически выполняет:
1. **Preflight** — 6 проверок (JSON, images, hubs, HTML, sections, validate)
2. **Generate** — 29 страниц через Jinja2
3. **Upload images** — scp 29 директорий → `/files/images/`
4. **Upload HTML** — scp 29 HTML + 4 hub index.html
5. **Verify** — HTTP 200 для 5 sample pages

## Серверы

| Сервер | Назначение | IP |
|--------|-----------|-----|
| ant-dev.artvision.pro | ✅ ТЕСТ | 80.90.181.152 |
| ant.partners | ❌ БОЕВОЙ | 77.222.56.111 |

**ЗАПРЕЩЕНО** загружать тестовые файлы на 77.222.56.111.

## После деплоя

Запустить визуальную проверку:
```bash
python3 ant-visual-check.py
```
