---
name: figma-export
description: Экспорт фреймов Figma через REST API. Скачивает PNG/SVG/PDF любых frames в репо клиента, опционально коммитит и деплоит на VPS. Использовать когда Антон даёт ссылку figma.com/design/... или просит «вытащи макет из фигмы», «скачай фрейм», «экспорт figma», «достань пнг из фигмы», «figma export», «фигма экспорт», «скачай макет», «возьми фрейм из figma».
---

# /figma-export — экспорт Figma через REST API

## Что делает

Универсальная обёртка над Figma REST API. Скрипт `~/artvision-data/scripts/figma-export.py` забирает токен из `tokens.json → figma.personal_access_token`, парсит URL Figma и скачивает PNG/SVG/PDF любых frames.

## Требования

- Токен в `tokens.json → figma` (создаётся на figma.com/settings → Security → Personal access tokens → Generate)
- Антон даёт URL Figma либо file_key
- Если нужен `--commit` или `--deploy` — указать `--client <slug>`

## Алгоритм работы

### Шаг 1: Определить вход

Получи от Антона ОДНО из:
- **URL Figma** (`https://www.figma.com/design/<KEY>/<title>?node-id=104-12`)
- **file_key** (`Ez5HuaA8JS0JlLOQbBwmBC` — 15-30 alphanumeric)
- Опционально **client** (имя папки в `clients/<name>/`)

Если URL не дан — спроси.

### Шаг 2: Метаданные (обязательно сначала)

Покажи список всех frames в файле (узнать какой именно нужен):

```bash
python3 ~/artvision-data/scripts/figma-export.py <URL_ИЛИ_KEY> --metadata-only
```

Возвращает дерево страниц с frames + размеры. Покажи Антону, спроси какой именно фрейм нужен (если он не сказал в URL).

### Шаг 3: Экспорт

Один конкретный фрейм:

```bash
python3 ~/artvision-data/scripts/figma-export.py <URL> \
    --client <client_slug> \
    --node-id <id> \
    --scale 2
```

Все frames файла:

```bash
python3 ~/artvision-data/scripts/figma-export.py <URL> \
    --client <client_slug> \
    --all --scale 1
```

### Шаг 4: Опции автоматизации

- `--commit` — после экспорта `git add` + `git commit` + `git push`
- `--deploy` — `scp` на `artvision.pro/preview/<client>/figma/`
- `--format svg` или `--format pdf` — вместо PNG
- `--scale 2` — retina (×2)

Сочетай для одношагового workflow:

```bash
python3 ~/artvision-data/scripts/figma-export.py <URL> \
    --client aleksandra-dental --scale 2 --commit --deploy
```

→ Файл скачан → положен в `clients/aleksandra-dental/figma/` → закоммичен → залит на VPS → доступен на `artvision.pro/preview/aleksandra-dental/figma/`.

## Выходные файлы

В `clients/<client>/figma/`:

- `<frame-name>-<page-name>-<id>@2x.png` — экспортированные изображения
- `figma-metadata.json` — список всех frames файла + параметры экспорта

## Примеры использования

### Простой — посмотреть что в файле
> Антон: «глянь что в фигме https://www.figma.com/design/Ez5HuaA8.../DENTIX»

```bash
python3 ~/artvision-data/scripts/figma-export.py 'https://www.figma.com/design/Ez5HuaA8JS0JlLOQbBwmBC/DENTIX' --metadata-only
```

### Скачать конкретный фрейм
> Антон: «достань главную страницу клиента»

```bash
python3 ~/artvision-data/scripts/figma-export.py \
    'https://figma.com/design/<key>/file?node-id=104-12' \
    --client <slug> --scale 2 --commit
```

### Скачать ВСЕ фреймы и задеплоить
> Антон: «забери все экраны из фигмы и положи на превью»

```bash
python3 ~/artvision-data/scripts/figma-export.py <URL> \
    --client <slug> --all --scale 1 --commit --deploy
```

## Когда вызывать /figma-export

- Антон присылает URL `figma.com/design/...` или `figma.com/file/...`
- Слова «фигма», «figma», «макет», «фрейм», «вытащи из фигмы», «достань пнг»
- Перед redline-аннотациями нужен реальный PNG макета
- Подготовка к page-review клиентского сайта (макет → ТЗ → HTML)

## Когда НЕ вызывать

- Если у Антона нет токена в `tokens.json` — попросить создать его сначала
- Если просто нужны общие правила работы с дизайном (это `frontend-design` skill)
- Если нужен Figma MCP интерактивно (это другая задача — `claude mcp add figma`)

## Связь

- `figma.personal_access_token` в `tokens.json` (gitignored)
- Скрипт `~/artvision-data/scripts/figma-export.py`
- Папка `clients/<name>/figma/` — стандарт хранения макетов клиента
- VPS deploy путь — `/var/www/artvision/preview/<client>/figma/` → `artvision.pro/preview/<client>/figma/`
- Применяется в pipeline `/page-review` и при работе с blueprint `dental-clinic-pages-blueprint.md`

## История

- **2026-05-13** — создан после сессии DENTIX (85419c66) когда Антон прислал токен и реальный экспорт PNG разблокировал главный блок. Универсализировано для всех клиентов.
