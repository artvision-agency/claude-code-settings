---
name: video-learn
description: >-
  Анализ видео → транскрипт → план применения → сравнение с текущим workflow → тест конфликтов → реализация → тесты → отчёт.
  URL видео → yt-dlp субтитры → actionable план. Поддержка YouTube, VK, Rutube и др.
  Триггеры: 'video-learn', 'видео учёба', 'разбери видео', 'выжимка из видео',
  'что полезного в видео', 'законспектируй видео', 'learn from video',
  'транскрипт видео', 'видео → правила', 'видео → скилл'.
argument-hint: "<video-url> [focus: workflow|tools|marketing|seo|dev|all]"
user-invocable: true
allowed-tools: Read Write Edit Bash Glob Grep Agent WebSearch WebFetch
---

# Video Learn — Извлечение знаний из видео в workflow Artvision

Полный pipeline: от URL видео до обновлённых правил, скиллов и скриптов.

## КРИТИЧЕСКИЕ ПРАВИЛА

### 1. Источник транскрипта — каскадный fallback

```
YouTube URL → youtube-transcript-api (PRIMARY, не блокируется consent-редиректом)
            → yt-dlp (FALLBACK для не-YouTube или при отказе API)
            → @BukvitsaAI_bot (LAST RESORT, ручной)

Не-YouTube URL → yt-dlp → @BukvitsaAI_bot
```

Зависимости (проверять перед стартом):
```bash
python3 -c "import youtube_transcript_api" 2>/dev/null || pip3 install youtube-transcript-api
which yt-dlp || brew install yt-dlp
```

**Почему `youtube-transcript-api` сначала:** YouTube редиректит на `consent.youtube.com` (EU/UK), что ломает WebFetch и часть запросов yt-dlp без cookies. API-эндпоинт `timedtext` отдаёт авто-субтитры напрямую, без consent. Подтверждено 2026-05-03 на видео Игоря Тимо (YXXKbilyWCQ).

### 2. Язык субтитров — сначала русский, потом английский
Приоритет: ручные ru → авто ru → ручные en → авто en. Применять одинаково для обоих способов.

### 3. Не модифицировать файлы без явного одобрения пользователя
Шаги 1-7 (анализ) — автоматически. Шаг 8 (реализация) — ТОЛЬКО после подтверждения.

---

## WORKFLOW

### Step 0: Подготовка

- Получить URL видео из `$ARGUMENTS` (первый аргумент)
- Получить фокус из `$ARGUMENTS` (второй аргумент, по умолчанию `all`)
- Проверить yt-dlp: `which yt-dlp || echo "INSTALL: brew install yt-dlp"`
- Создать рабочую директорию:
```bash
WORK_DIR="/tmp/video-learn-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$WORK_DIR"
```

### Step 1: Скачать транскрипт

**1.1 (PRIMARY для YouTube): `youtube-transcript-api`**

Срабатывает если URL содержит `youtube.com` или `youtu.be`. Не зависит от consent-редиректа, не требует cookies.

```bash
VIDEO_URL="$1"
WORK_DIR="/tmp/video-learn-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$WORK_DIR"

# Извлечь video_id (поддерживает youtube.com/watch?v=, youtu.be/, shorts/)
VIDEO_ID=$(python3 -c "
import re, sys
url = '$VIDEO_URL'
m = re.search(r'(?:v=|/shorts/|youtu\.be/|/embed/)([A-Za-z0-9_-]{11})', url)
print(m.group(1) if m else '')
")

if [ -n "$VIDEO_ID" ]; then
  python3 << PYEOF > "$WORK_DIR/transcript_raw.txt" 2> "$WORK_DIR/transcript_err.log"
from youtube_transcript_api import YouTubeTranscriptApi
api = YouTubeTranscriptApi()
listing = api.list("$VIDEO_ID")
# Приоритет: ручные ru → авто ru → ручные en → авто en
preferred_order = []
for is_generated in [False, True]:
    for lang in ["ru", "en"]:
        for t in listing:
            if t.language_code == lang and t.is_generated == is_generated:
                preferred_order.append(t)
if preferred_order:
    tr = preferred_order[0].fetch()
    for s in tr.snippets:
        m, sec = divmod(int(s.start), 60)
        print(f"[{m:02d}:{sec:02d}] {s.text}")
PYEOF
fi

# Метаданные через oEmbed (без yt-dlp)
python3 -c "
import urllib.request, json
url = 'https://www.youtube.com/oembed?url=$VIDEO_URL&format=json'
try:
    data = json.loads(urllib.request.urlopen(url, timeout=10).read())
    print(f\"{data.get('title','')}|||{data.get('author_name','')}|||unknown|||unknown\")
except: pass
" > "$WORK_DIR/metadata.txt"
```

Если `transcript_raw.txt` пустой — переход к 1.2.

**1.2 (FALLBACK): yt-dlp** — для не-YouTube платформ или если API не отдал транскрипт

```bash
yt-dlp --list-subs "$VIDEO_URL" 2>/dev/null | head -20

yt-dlp --write-sub --write-auto-sub --sub-lang "ru,en" --sub-format "srt/vtt/best" \
  --skip-download --output "$WORK_DIR/%(title)s.%(ext)s" "$VIDEO_URL"

yt-dlp --print "%(title)s|||%(uploader)s|||%(duration_string)s|||%(upload_date)s" \
  "$VIDEO_URL" 2>/dev/null > "$WORK_DIR/metadata.txt"
```

**1.3 (LAST RESORT): Если транскрипта нет нигде**

1. Сообщить пользователю: "Субтитры недоступны для этого видео."
2. Предложить: "Отправьте видео в @BukvitsaAI_bot (Telegram) — он вернёт текстовый транскрипт."
3. Попросить вставить транскрипт в чат или указать путь к файлу.
4. **НЕ продолжать pipeline без транскрипта.**

### Step 2: Очистка → plain text

**2a (если использовался путь 1.1 — youtube-transcript-api):** `transcript_raw.txt` уже без HTML-тегов и формат `[MM:SS] текст`. Для шага 3 достаточно скопировать его в `transcript_clean.txt` (опционально срезать таймкоды для длинных текстовых блоков):

```bash
if [ -s "$WORK_DIR/transcript_raw.txt" ]; then
  # Убрать таймкоды и склеить дубли подряд
  sed 's/^\[[0-9:]*\] //' "$WORK_DIR/transcript_raw.txt" | awk '!seen[$0]++' > "$WORK_DIR/transcript_clean.txt"
fi
```

**2b (если использовался путь 1.2 — yt-dlp):** очистка SRT/VTT:

```bash
# Найти скачанный файл субтитров
SUB_FILE=$(find "$WORK_DIR" -name "*.srt" -o -name "*.vtt" | head -1)

if [ -n "$SUB_FILE" ] && [ ! -s "$WORK_DIR/transcript_clean.txt" ]; then
  # Очистить SRT: убрать таймкоды, номера строк, дубли, HTML-теги
  python3 -c "
import re, sys

with open('$SUB_FILE', 'r', encoding='utf-8') as f:
    text = f.read()

# Убрать VTT заголовок
text = re.sub(r'^WEBVTT.*?\n\n', '', text, flags=re.DOTALL)

# Убрать номера строк SRT
text = re.sub(r'^\d+\s*$', '', text, flags=re.MULTILINE)

# Убрать таймкоды (SRT и VTT форматы)
text = re.sub(r'\d{2}:\d{2}:\d{2}[.,]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[.,]\d{3}.*', '', text)

# Убрать HTML-теги
text = re.sub(r'<[^>]+>', '', text)

# Убрать пустые строки, объединить
lines = [l.strip() for l in text.split('\n') if l.strip()]

# Убрать дубли подряд идущих строк (авто-субтитры часто дублируют)
deduped = []
for line in lines:
    if not deduped or line != deduped[-1]:
        deduped.append(line)

# Объединить в абзацы (каждые 5-7 предложений)
result = ' '.join(deduped)
# Разбить на абзацы по ~500 символов на границе предложений
paragraphs = []
current = ''
for sentence in re.split(r'(?<=[.!?])\s+', result):
    current += sentence + ' '
    if len(current) > 500:
        paragraphs.append(current.strip())
        current = ''
if current.strip():
    paragraphs.append(current.strip())

print('\n\n'.join(paragraphs))
" > "$WORK_DIR/transcript_clean.txt"
fi
```

Результат: `$WORK_DIR/transcript_clean.txt` — чистый текст без таймкодов.

### Step 3: Анализ транскрипта — извлечение actionable знаний

Прочитать `$WORK_DIR/transcript_clean.txt` и извлечь:

**Категории извлечения:**

| Категория | Что искать | Пример |
|-----------|-----------|--------|
| **Инструменты** | Названия софта, сервисов, CLI-утилит | "используйте Cursor для..." |
| **Методы/Фреймворки** | Подходы, алгоритмы, процессы | "метод AIDA для текстов" |
| **Правила/Принципы** | Жёсткие правила, "всегда/никогда" | "никогда не деплойте в пятницу" |
| **Workflow-паттерны** | Последовательности действий | "сначала MVP, потом тесты" |
| **Метрики/Пороги** | Конкретные числа, KPI | "CTR ниже 2% = проблема" |
| **Антипаттерны** | Чего НЕ делать | "не используйте !important" |
| **Кейсы/Примеры** | Конкретные истории успеха/провала | "мы увеличили конверсию на 40%" |

Формат вывода:
```markdown
## Извлечённые знания из: [название видео]
**Автор:** [uploader] | **Длительность:** [duration] | **Дата:** [date]

### Инструменты (N шт.)
1. [Инструмент] — [для чего] — [как применить у нас]

### Методы и фреймворки (N шт.)
1. [Метод] — [суть] — [где применить]

### Правила и принципы (N шт.)
1. [Правило] — [обоснование]

### Workflow-паттерны (N шт.)
1. [Паттерн] — [шаги] — [когда использовать]

### Метрики и пороги (N шт.)
1. [Метрика]: [значение] — [контекст]

### Антипаттерны (N шт.)
1. [Что НЕ делать] — [почему]

### Кейсы (N шт.)
1. [Кейс] — [результат] — [что взять]
```

Сохранить в `$WORK_DIR/extracted_knowledge.md`.

### Step 4: План применения

На основе извлечённых знаний составить план — что конкретно можно внедрить:

```markdown
## План применения

### Немедленно (quick wins)
- [ ] [Действие] → [какой файл/правило затрагивает]

### На этой неделе
- [ ] [Действие] → [файл/правило]

### Требует обсуждения
- [ ] [Действие] — [почему нужно обсудить]

### Отклонено (неприменимо)
- [Знание] — [почему не подходит для нашего workflow]
```

Сохранить в `$WORK_DIR/application_plan.md`.

### Step 5: Сравнение с текущим workflow

Проверить пересечения с существующей базой знаний:

```bash
# Прочитать текущие правила и скиллы
~/.claude/CLAUDE.md
~/.claude/rules/*.md
~/.claude/skills/*/SKILL.md   # только SKILL.md, не вложенные файлы
~/artvision-data/CLAUDE.md    # если есть
```

Для каждого извлечённого знания определить статус:

| Статус | Значение |
|--------|---------|
| **УЖЕ ЕСТЬ** | Правило/метод уже реализовано в наших файлах |
| **ЧАСТИЧНО** | Есть похожее, но видео даёт улучшение/расширение |
| **НОВОЕ** | Этого у нас нет, стоит добавить |
| **ПРОТИВОРЕЧИТ** | Конфликтует с существующим правилом |

Формат:
```markdown
## Сравнение с текущим workflow

| # | Знание | Статус | Где у нас | Комментарий |
|---|--------|--------|-----------|-------------|
| 1 | [знание] | УЖЕ ЕСТЬ | rules/workflow.md:15 | Полностью покрыто |
| 2 | [знание] | НОВОЕ | — | Добавить в rules/X.md |
| 3 | [знание] | ПРОТИВОРЕЧИТ | skills/Y/SKILL.md:42 | Наше правило лучше |
```

### Step 6: Тест на конфликты

Для каждого знания со статусом НОВОЕ или ЧАСТИЧНО:

1. **Проверить совместимость** с существующими правилами:
   - Не противоречит ли правилам в `~/.claude/rules/*.md`?
   - Не ломает ли существующие скиллы?
   - Не конфликтует ли с workflow команды?

2. **Проверить техническую реализуемость:**
   - Нужны ли новые зависимости (brew, pip, npm)?
   - Работает ли на macOS (наша платформа)?
   - Не требует ли платных API, которых у нас нет?

3. **Оценить риск:**
   - LOW — изменение изолировано, легко откатить
   - MEDIUM — затрагивает несколько файлов, но обратимо
   - HIGH — меняет core workflow, нужно обсуждение

Формат:
```markdown
## Тест конфликтов

### Безопасные (LOW risk)
- [Знание] → [файл для изменения] — нет конфликтов

### Требуют внимания (MEDIUM risk)
- [Знание] → затрагивает [файлы] — [описание потенциального конфликта]

### Требуют обсуждения (HIGH risk)
- [Знание] → конфликт с [правило] — [детали]
```

### Step 7: Показать результат пользователю

Вывести сводку ПЕРЕД реализацией:

```
## Video Learn: Результат анализа

**Видео:** [название]
**Извлечено:** X знаний (Y инструментов, Z методов, W правил)

### К внедрению (N шт.)
1. [Знание] → [куда добавить] — risk: LOW
2. ...

### Требуют обсуждения (N шт.)
1. [Знание] — [почему]

### Отклонено (N шт.)
1. [Знание] — [причина]

Применить безопасные изменения (LOW risk)?
```

**СТОП. Ждать подтверждения пользователя.**

### Step 8: Реализация

После подтверждения — применить изменения:

**8.1: Обновить существующие файлы**
- `Edit` для добавления новых правил в `~/.claude/rules/*.md`
- `Edit` для обновления скиллов в `~/.claude/skills/*/SKILL.md`
- Минимальные изменения — добавлять, не переписывать

**8.2: Создать новые файлы (если нужно)**
- Новые скриптыs в `~/.claude/scripts/`
- Новые скиллы через `/skill-generator` (НЕ вручную)

**8.3: Сохранить источник**
```bash
# Сохранить лог что откуда взято
cat >> ~/artvision-data/docs/video-learn-log.md << EOF

## $(date +%Y-%m-%d) — [название видео]
- **URL:** $VIDEO_URL
- **Внедрено:** [список изменений]
- **Отклонено:** [список с причинами]
- **Файлы изменены:** [список путей]
EOF
```

### Step 9: Рой тестов

Запустить параллельных агентов для проверки изменений:

**Agent 1: Синтаксис и целостность**
```
Проверить все изменённые файлы:
- YAML frontmatter валиден (skills)
- Markdown корректен
- Нет битых ссылок на файлы
- JSON файлы валидны (если менялись)
```

**Agent 2: Конфликты правил**
```
Прочитать ВСЕ файлы ~/.claude/rules/*.md.
Найти противоречия между правилами.
Проверить что новые правила не конфликтуют со старыми.
Формат: список конфликтов или "Конфликтов не найдено".
```

**Agent 3: Функциональность скриптов**
```
Если были созданы/изменены скрипты:
- Проверить синтаксис: bash -n script.sh / python3 -c "compile(open('x').read(), 'x', 'exec')"
- Проверить зависимости: все импорты/утилиты доступны
- Dry-run если возможно
```

Если все 3 агента ОК — изменения приняты. Если нет — откатить проблемные.

### Step 10: Отчёт

Финальный отчёт пользователю:

```markdown
## Video Learn: Отчёт

**Видео:** [название] ([duration])
**Дата обработки:** YYYY-MM-DD

### Внедрено (N шт.)
| # | Знание | Файл | Изменение |
|---|--------|------|-----------|
| 1 | [что] | [путь] | Добавлено правило X |

### Отложено (N шт.)
| # | Знание | Причина | Когда вернуться |
|---|--------|---------|-----------------|
| 1 | [что] | [почему] | [дата/условие] |

### Отклонено (N шт.)
| # | Знание | Причина |
|---|--------|---------|
| 1 | [что] | Не применимо / конфликт / уже есть |

### Тесты
- Синтаксис: OK/FAIL
- Конфликты: OK/FAIL
- Скрипты: OK/FAIL/N/A

**Транскрипт сохранён:** $WORK_DIR/transcript_clean.txt
**Извлечённые знания:** $WORK_DIR/extracted_knowledge.md
```

### Step 11: Напоминание — проверка через неделю

Создать напоминание для проверки эффективности внедрённых изменений:

```
CronCreate: через 7 дней напомнить:
"Video Learn: проверить эффективность изменений из видео [название].
Внедрено N правил/скриптов. Проверить:
- Использовались ли новые правила?
- Были ли проблемы?
- Нужно ли откатить/скорректировать?"
```

Также добавить TODO в соответствующий TODO.md:
```markdown
- [ ] Video Learn review: [название видео] — проверить внедрённые изменения (YYYY-MM-DD + 7 дней)
```

---

## Поддерживаемые платформы

| Платформа | PRIMARY | FALLBACK | LAST RESORT |
|-----------|---------|----------|-------------|
| YouTube | `youtube-transcript-api` (Python) | `yt-dlp` | @BukvitsaAI_bot |
| VK Video | `yt-dlp` | — | @BukvitsaAI_bot |
| Rutube | `yt-dlp` | — | @BukvitsaAI_bot |
| Vimeo | `yt-dlp` (ручные если есть) | — | @BukvitsaAI_bot |
| Twitch VOD | `yt-dlp` (авто если есть) | — | @BukvitsaAI_bot |
| Yandex.Zen | — | — | @BukvitsaAI_bot |

## Частые ошибки (НЕ ПОВТОРЯТЬ)

| Ошибка | Последствие | Правильно |
|--------|-------------|-----------|
| Применять ВСЕ советы из видео | Конфликты, перегрузка | Фильтровать через Steps 5-6 |
| Не проверять конфликты | Сломанный workflow | Обязательный Step 6 |
| Менять core rules без подтверждения | Откат, потеря времени | СТОП на Step 7 |
| Доверять метрикам из видео без проверки | Устаревшие данные | Перепроверить WebSearch |
| Игнорировать контекст Artvision | Generic советы | Всегда сравнивать с нашим workflow |

## Related Skills

- **ai-evolve** — self-improvement на основе patches (похожий подход, другой источник данных)
- **continuous-learning** — обновление memory-файлов
- **skill-generator** — создание новых скиллов (если видео даёт идею для нового скилла)
- **agent-prompt-evolve** — улучшение промптов агентов
