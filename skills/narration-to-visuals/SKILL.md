---
name: narration-to-visuals
description: >-
  Лекция → видео, где автор читает сценарий, а экран заполняет авто-визуализация
  по речи (B: AI-картинки, C: слайды, D: схемы), автор в PiP справа-внизу.
  Триггеры: 'narration-to-visuals', 'визуализация лекции', 'озвучка → видеоряд',
  'сделай видео по лекции', 'narration to visuals'.
argument-hint: "<lecture> [--preset ai-course] [--force]"
user-invocable: true
allowed-tools: Read Write Edit Bash Glob Grep Agent
---

# Narration → Visuals

Полный замысел и решения: см. spec
`ai-course/docs/superpowers/specs/2026-05-16-narration-to-visuals-design.md`.

**Объём: полный пайплайн (Plan 1+2+3).** SCRIPT-GEN + REVIEW GATE 1 →
запись → STORYBOARD + REVIEW GATE 2 → RENDER → `visualized.mp4`.
Гейтов всего два; после утверждённого Гейта 2 рендер идёт до конца.

## Когда активировать

- Пользователь хочет сделать видео по лекции курса с авто-визуализацией.
- Триггеры: `/narration-to-visuals <lecture>` или фразы из `description`.

## Шаг 0: SCRIPT-GEN (детерминированно)

Окружение: в `skills/narration-to-visuals/` есть пакет `nv_engine` (Python).

```bash
cd <repo>/skills/narration-to-visuals
. .venv/bin/activate 2>/dev/null || (python3 -m venv .venv && . .venv/bin/activate && pip install -e . PyYAML)
python -m nv_engine <lecture> --project-root <ai-course-repo-root>
```

Скрипт детерминированно собирает **черновик** `narration_script.md`
(блоки из `summary.md`, текст из очищенного `transcript.json`,
эвристические `[B/C/D:]`-маркеры) и сохраняет brief в `.nv-work/<lecture>/`.

## Шаг 1: Доводка черновика (Claude)

Прочитай сгенерированный `narration_script.md` и `.nv-work/<lecture>/script_brief.json`,
а также исходные `summary.md`, `transcript.json`, `speaker_notes.md` (если есть).
Доведи черновик, СОХРАНЯЯ формат (frontmatter + `## Блок N — …` + `[B/C/D: …]` +
текст для чтения):

- Убери оставшийся ASR-шум, сделай текст связным для чтения вслух.
- Уточни `[B/C/D:]`-маркеры по смыслу блока (D — схемы/код/техника,
  C — определения/тезисы, B — иллюстрации/метафоры).
- Не выдумывай факты, которых нет в источниках курса.
- После правок прогони валидатор:
  `python -c "from nv_engine.script_doc import validate_script_md as v; import sys; v(open(sys.argv[1],encoding='utf-8').read())" <path>`

## === REVIEW GATE 1 ===

**STOP. Это жёсткий стоп-гейт.**

Покажи автору путь к `narration_script.md` и краткую сводку (число блоков,
распределение B/C/D, замеченные риски). Попроси прочитать и отредактировать
**текст блоков и `[B/C/D:]`-маркеры**.

**НЕ продолжай дальше** (запись, ALIGN, генерация) до явного подтверждения
автора. Запись видео делает автор вручную, читая утверждённый сценарий.
Дальнейшие стадии — Plan 2 / Plan 3 (не реализованы в этой вехе).

## Шаг 2: STORYBOARD (План 2, после записи, детерминированно)

Предусловие: автор записал `source/<lecture>/narration.mp4`, читая
утверждённый `narration_script.md`.

```bash
cd <repo>/skills/narration-to-visuals && . .venv/bin/activate
python -m nv_engine <lecture> --project-root <ai-course-root> --stage storyboard
```

Скрипт: ALIGN (stable-ts по тексту скрипта) → SEGMENT (тайминги блоков из
записи) → RECONCILE (флаги DEVIATION) → CLASSIFY (черновик контента под
авторский маркер) → `.nv-work/<lecture>/storyboard.json` (+ `.md`, `aligned.json`,
`reconcile.md`).

## Шаг 3: Доводка раскадровки (Claude)

Прочитай `storyboard.md`/`storyboard.json`. Уточни черновой контент
(`image_prompt`/`slide_lines`/`diagram_spec`) по смыслу, не меняя авторские
маркеры. Для блоков с `deviation: true` сверься с `reconcile.md` и записью.

## === REVIEW GATE 2 ===

**STOP. Жёсткий стоп-гейт.** Покажи автору `storyboard.md`: число блоков,
распределение B/C/D, блоки с DEVIATION. Попроси проверить/поправить.
**НЕ запускай генерацию ассетов** до явного подтверждения.

## Шаг 4: RENDER (после утверждённого Гейта 2, детерминированно)

Предусловие: автор утвердил/поправил `.nv-work/<lecture>/storyboard.json`.

```bash
cd <repo>/skills/narration-to-visuals && . .venv/bin/activate
python -m nv_engine <lecture> --project-root <ai-course-root> --stage render
```

Скрипт: GENERATE (B-картинки fal.ai, кэш по хешу, лимит `--max-cost`;
C/D пробрасываются) → COMPOSE (`remotion-props.json`: фон B/C/D по
таймлайну + PiP-вебка 24% справа-внизу + аудио, без субтитров) → RENDER
(`npx remotion render`) → `source/<lecture>/visualized.mp4` +
`nv-report.md`. **Это финал — стоп-гейтов больше нет. Pipeline complete.**

Реальные адаптеры: fal.ai требует `pip install fal-client` + `FAL_KEY`;
рендер требует Node ≥18 + Remotion (`npx`). Для прогона без них —
переменные окружения `NV_FAKE_ASSETS=1` / `NV_FAKE_RENDER=1`.

## Частые ошибки (НЕ повторять)

| Ошибка | Правильно |
|--------|-----------|
| Перезаписать отредактированный автором `narration_script.md` | Идемпотентность: без `--force` не перезаписывать |
| Пропустить REVIEW GATE 1 | Всегда СТОП до подтверждения автора |
| Читать вслух `[B/C/D:]`-строки | Это подсказки визуала, не текст диктора |
| Выполнять ALIGN/GENERATE | Это Plan 2/3, вне текущей вехи |

## Related Skills

- `video-learn` — паттерн «детерминированный скрипт + Claude + жёсткий СТОП».
- `video-editing`, `fal-ai-media` — будут задействованы в Plan 2/3.
