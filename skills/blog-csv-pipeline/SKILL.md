---
name: blog-csv-pipeline
description: "Batch генерация статей в блог из CSV списка ключей. Glue-skill: CSV → for каждой keyword → serp-format-extractor + content-writer + personality-files-bundle → MD-файл. Resume support, parallel max 3-4. Triggers: 'csv → статьи', 'batch контент', 'массовая генерация статей', 'csv blog pipeline', 'батч статей', 'из csv в блог', 'blog csv', 'статьи из csv'."
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep, Task]
---

# blog-csv-pipeline — CSV ключей → batch статей

Glue-скилл: принимает CSV с ключевыми словами, для каждой строки оркестрирует `serp-format-extractor` (если есть) + `content-writer` + опц. `personality-files-bundle`, сохраняет MD-черновики в `clients/<slug>/blog/drafts/`. Resume support, parallel max 3-4.

**Не дублирует логику writer/extractor** — только orchestration. Падение одной статьи не валит batch.

## Когда вызывать

| Триггер | Действие |
|---|---|
| «у меня csv ключей, нужно статьи в блог» | §1 Запуск |
| «batch контент 50 статей» | §1 Запуск |
| «продолжи генерацию» (после прерывания) | §2 Resume |
| «покажи отчёт по blog-csv» | §3 Report |
| «csv формат правильный?» | §4 Validate only |

## §1 Запуск

```bash
python3 ~/.claude/skills/blog-csv-pipeline/scripts/pipeline.py \
  --csv <path-to-csv> \
  --client <slug> \
  --mode sequential        # sequential | parallel (parallel TBD)
  [--concurrency 3]        # max 3-4
  [--resume]               # продолжить с прерванной точки
  [--dry-run]              # только валидация + план, без вызовов
```

**Параметры:**
- `--csv` — путь к CSV (формат см. §4)
- `--client` — slug клиента (`creates clients/<slug>/blog/drafts/`)
- `--mode sequential` — по одной (стабильно, дефолт)
- `--mode parallel` — concurrent.futures ThreadPoolExecutor (TBD, см. scripts/pipeline.py:run_parallel)
- `--resume` — читает `state.json`, пропускает status=done

**Outputs:**
- `clients/<client>/blog/drafts/<slug-of-keyword>.md` — статья
- `clients/<client>/blog/state.json` — прогресс (resume)
- `~/.claude/logs/blog-csv-pipeline-<client>.log` — лог запусков

## §2 Resume

Прерванный pipeline (Ctrl+C, network error, content-writer fail) — продолжается с того же CSV:

```bash
python3 ~/.claude/skills/blog-csv-pipeline/scripts/pipeline.py \
  --csv <path> --client <slug> --resume
```

`state.json` хранит: `{keyword: {status: done|failed|pending, file_path, word_count, error, ts}}`. При `--resume` пропускает все `done`, повторяет `failed` и `pending`.

## §3 Финальный отчёт

После завершения (или вручную):

```bash
python3 ~/.claude/skills/blog-csv-pipeline/scripts/pipeline.py \
  --client <slug> --report-only
```

Печатает таблицу:

| keyword | status | file_path | word_count | error |
|---------|--------|-----------|------------|-------|
| seo для стоматологии | done | clients/.../seo-dlya-stomatologii.md | 1832 | — |
| продвижение в Яндексе | failed | — | — | content-writer timeout |

И summary: `done=N, failed=M, skipped=K, total_words=X`.

## §4 CSV формат

```csv
keyword,priority,target_url_slug,word_count
seo для стоматологии,1,seo-dlya-stomatologii,1800
продвижение в Яндексе,2,,2000
SEO ошибки 2026,3,seo-oshibki-2026,
```

| Колонка | Обязат. | Описание |
|---|:---:|---|
| `keyword` | ✅ | Главный ключ (он же тема статьи) |
| `priority` | — | 1-5, дефолт 3 (сортировка очереди) |
| `target_url_slug` | — | если пусто — генерируется транслитом из keyword |
| `word_count` | — | желаемый объём; дефолт 1500 |

**Валидация перед стартом:**

```bash
python3 ~/.claude/skills/blog-csv-pipeline/scripts/csv_validator.py <path-to-csv>
```

Проверяет: заголовок, обязательные колонки, дубли keyword, валидный priority, slug без кириллицы (если задан).

## §5 Pipeline шаги (что происходит per keyword)

1. **SERP анализ** — если установлен skill `serp-format-extractor` → Task tool с промптом `«SERP top-3 для '<keyword>' → каркас H2/H3»`. Если не установлен — пропускаем, content-writer получит только keyword.
2. **Personality injection** — если в `clients/<client>/blog/personality.md` есть файл → читаем и передаём в prompt content-writer'a.
3. **content-writer call** — через Task tool, `subagent_type: general-purpose`, prompt:
   ```
   GLOBAL OVERRIDE: Write full article to <absolute_path>.
   Используй skill content-writer §1. Тема: <keyword>. Объём: <word_count>.
   Каркас SERP (top-3): <skeleton or "—">.
   Personality: <bundle or "—">.
   Tone of Voice — Artvision (умный друг). После записи верни краткий summary (<200 слов).
   ```
4. **Verify** — после Task завершения: `os.path.exists(file_path)` + `word_count >= 0.8 × target`. Иначе status=failed.
5. **State update** — `state.json` пишется атомарно (tmp + rename) после каждой статьи.

## §6 Связанные скиллы

- `content-writer` — основной writer (вызывается на шаге 3)
- `serp-format-extractor` — каркас top-3 (опц., шаг 1)
- `personality-files-bundle` — голос автора (опц., шаг 2)
- `factcheck` — после генерации batch, прогнать `python3 ~/artvision-data/scripts/factcheck-v2.py` на drafts/
- `page-publish` — потом публикация в WordPress (отдельный шаг, не часть pipeline)
- `programmatic-seo` — для шаблонных страниц (services × cities), НЕ статей

## §7 Антипаттерны

- ❌ Пускать parallel >4 — Claude API rate-limit, content-writer субагенты упадут
- ❌ Запускать без `--dry-run` на >20 ключей в первый раз — потеря денег при ошибке в CSV
- ❌ Доверять статусу `done` без verify файла — `state.json` может разойтись с FS
- ❌ Дублировать логику content-writer в этом скилле — он glue, не writer
- ❌ Хардкодить `clients/<slug>` — путь через `--client` параметр

## §8 Прецеденты

- (TBD: первый клиент-кейс после реального запуска)

## §9 TODO (не блокеры запуска)

- Parallel mode (concurrent.futures) — заглушка в `pipeline.py:run_parallel()` с TODO
- Cost tracking — оценка $ per article через Anthropic API usage endpoint
- Retry policy — exponential backoff для failed (сейчас фиксируется один раз)
- WordPress publish hook — после `done` всех опционально вызвать `page-publish`
