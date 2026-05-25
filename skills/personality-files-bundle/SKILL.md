---
name: personality-files-bundle
description: "5-file scaffold для personal-brand клиентов: voice/humor/stats/stories/opinions.md. Дополнение к brand-voice. Автоинжект в content-writer/outreach-emails/smm-strategist по роли. Triggers: 'personality files', 'персональный бренд', 'личный голос', 'humor opinions stats', 'писать от лица клиента', 'storytelling профиль', 'эксперт колонка'."
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep]
---

# Personality Files Bundle

Раскладывает «персональный голос» клиента на 5 отдельных файлов вместо одного `VOICE PROFILE`. Каждый файл — отдельная грань (стиль речи / юмор / цифры / истории / мнения). Скиллы вниз по стеку (content-writer, outreach, smm) подгружают только те файлы, которые нужны под роль текста.

## Когда вызывать

- Personal-brand клиент (физлицо-эксперт, основатель, публичная персона) — НЕ корпоративный голос
- Артикулы Артвижн: Андрей Бурение, Я.Канер, Vladislav (Blumart как личность), Антон Артвижн как личность
- Нужны разные «модусы» в зависимости от типа контента (storytelling vs аналитика vs провокация)
- Уже есть `brand-voice` профиль и хочется разложить его на роли

Если клиент — корпоратив с одним голосом, использовать `brand-voice`, не этот скилл.

## Когда НЕ вызывать

- Разовый текст без переиспользования (просто напиши через `copywriting`)
- Клиент B2B-агентство без personal-brand
- Нет ни одного источника реальных текстов клиента (сначала собери, потом scaffold)

## 5 файлов

| Файл | Что внутри | Когда инжектится |
|------|------------|------------------|
| `voice.md` | Базовый стиль: ритм, длина предложений, словарь, капитализация, что автор НИКОГДА не делает | Всегда (база) |
| `humor.md` | Где уместен юмор, типы шуток автора, табу-темы, регистр иронии | Соцсети, посты, лёгкий outreach |
| `stats.md` | Конкретные цифры/кейсы/проценты которые можно цитировать, источники, год | Аналитические посты, статьи, КП |
| `stories.md` | Личные истории, анекдоты, поворотные моменты карьеры | Storytelling-посты, длинные эссе |
| `opinions.md` | Позиции по острым темам индустрии, что автор открыто критикует, где идёт против мейнстрима | Авторские колонки, провокационные посты, дебаты |

## Workflow

### 1. Scaffold (создать 5 файлов)

```bash
python3 ~/.claude/skills/personality-files-bundle/scripts/scaffold.py <client-slug>
```

Создаёт `clients/<slug>/personality/{voice,humor,stats,stories,opinions}.md` из templates с placeholder-секциями.

Если есть `clients/<slug>/brand-voice.md` от скилла `brand-voice` — стартует с него: voice.md забирает базовый профиль, остальные 4 файла получают placeholders для интервью.

### 2. Interview (заполнить через CLI)

```bash
python3 ~/.claude/skills/personality-files-bundle/scripts/interview.py <client-slug> [--file voice|humor|stats|stories|opinions|all]
```

Серия вопросов по каждому файлу. Можно прогнать только один файл (`--file humor`) или весь bundle.

### 3. Source-derived заполнение (опц.)

Если есть 5+ реальных постов/видео клиента — переиспользовать `brand-voice` чтобы извлечь базу, затем `scaffold.py --from-brand-voice` раскладывает на 5 файлов автоматически:

- voice.md — берёт всё про ритм/стиль/словарь
- humor.md — ищет места где автор шутил, какие приёмы (сарказм, самоирония, абсурд)
- stats.md — экстрактит все числа из источников с разметкой «дата + источник»
- stories.md — личные истории (маркеры «когда я», «у меня был случай», «помню»)
- opinions.md — оценочные суждения, «не согласен», «считаю что», провокационные тезисы

### 4. Auto-inject в downstream скиллы

`inject.py` читает `clients/<slug>/personality/` и формирует context-block по роли. Подключающиеся скиллы:

| Скилл | Что инжектит |
|-------|--------------|
| `content-writer` | voice + (humor если соцсети) + (stats если аналитика) + (stories если эссе) |
| `copywriting` | voice + humor (короткие тексты) |
| `outreach-emails` | voice + (humor по уместности) + (stats для proof) |
| `smm-strategist` | voice + humor + opinions (соцсети любят острое) |
| `article-writing` | voice + stats + stories + opinions (длинная форма = все грани) |

Использование в downstream:
```python
# в content-writer / любой скилл
from personality_files_bundle.inject import build_context

ctx = build_context(client_slug="andrey-burenie", role="article")
# возвращает markdown-блок с релевантными разделами
```

## Source priority (для interview/extract)

1. Реальные посты автора (TG, VK, LinkedIn, X) — последние 6 мес
2. Видео-транскрипты (YouTube, подкасты)
3. Личная переписка с командой/клиентами (если разрешено)
4. Публичные выступления, интервью
5. Старые тексты — только если автор скажет «это мой канон»

НЕ использовать: generic platform examples, AI-generated копии, тексты ghostwriter'ов без подтверждения.

## Output контракт

Каждый файл — markdown с фиксированными секциями (см. templates/). Структурно одинаков для всех клиентов чтобы inject.py знал куда смотреть.

Например, `humor.md` всегда содержит секции:
- `## Регистр` (сарказм / самоирония / абсурд / dry / ...)
- `## Где уместен` (соцсети / outreach / статьи / ...)
- `## Табу` (что НЕ шутить — религия, политика, конкретные люди)
- `## Примеры` (3-5 реальных шуток автора с контекстом)

## Жёсткие запреты

- НЕ создавать `personality/` для корпоративов (Blumart как бренд, Artvision как агентство) — для них brand-voice
- НЕ выдумывать содержимое файлов — пустые секции лучше выдуманных
- НЕ коммитить `personality/` в публичные репо клиента — это внутренний кухонный артефакт
- НЕ цитировать `opinions.md` дословно в КП клиенту без проверки (там острое)
- НЕ путать `voice.md` (как пишет) с `brand-voice` корпоративным (как пишет бренд)

## Связь с brand-voice

| Аспект | brand-voice | personality-files-bundle |
|--------|-------------|--------------------------|
| Сколько файлов | 1 (`VOICE PROFILE`) | 5 (роли отдельно) |
| Для кого | Корпоративный бренд | Личность (founder, эксперт) |
| Извлечение | Source-derived из реальных постов | Source-derived + interview по граням |
| Downstream | Используется как is | Inject по роли (выборочно) |

Можно использовать `brand-voice` → потом `personality-files-bundle scaffold --from-brand-voice` чтобы развернуть один профиль в 5 файлов.

## Прецеденты использования

- TBD — первый клиент на котором обкатываем: Андрей Бурение (см. `examples/andrey-burenie-personality/`)

## Файлы скилла

```
personality-files-bundle/
├── SKILL.md (этот файл)
├── templates/
│   ├── voice.md
│   ├── humor.md
│   ├── stats.md
│   ├── stories.md
│   └── opinions.md
├── scripts/
│   ├── scaffold.py     # создание 5 файлов
│   ├── interview.py    # CLI-опрос (TODO)
│   └── inject.py       # подгрузка в downstream (TODO)
└── examples/
    └── andrey-burenie-personality/  # пример заполнения
```
