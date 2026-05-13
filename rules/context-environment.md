# Context Environment — file-system как контекст для коротких промптов

> **Принцип Anthropic Cowork:** один день на построение context environment → промпт из 10 слов даёт результат клиенту.
> **Установлено:** 2026-05-13 после сверки с habr-статьями про Cowork (см. `~/.claude/skills/cowork/SKILL.md` строка 179-183, ранее TBD).
> **Связано:** skill `cowork`, skill `presale-kp`, skill `page-create`, правило `kp-brand.md` (Pre-Task Protocol).

## Идея

Чем плотнее file-system контекст по клиенту/продукту, тем короче рабочий промпт может быть. Цель — чтобы 10-словный промпт «КП spadent v5» автоматически выдавал готовый артефакт нужного дизайна, тона и наполнения, без интервью на каждую новую задачу.

Это работает потому что Claude по обязательному Pre-Task Protocol (см. `kp-brand.md`) читает CLAUDE.md клиента + config.yaml + последний meeting summary + patches → подгружает все правила автоматически до первого Edit/Write.

## Минимум context environment для клиента (стандарт)

Папка `clients/<slug>/` (или `presales/<slug>/`) должна содержать:

| Файл | Назначение | Кто использует |
|------|-----------|----------------|
| `CLAUDE.md` | Бренд + контекст + статус + Pre-Task Protocol + связанные правила + next step | каждая сессия по клиенту |
| `config.yaml` | site, brand (цвета hex, шрифты), contacts, segment, status, design_profile, region | KP/page generators, design-system extract |
| `context-log.md` | Лог решений и действий (auto-update через hook) | при resume сессии и /goal Phase 1 |
| `access.md` | Доступы (CMS, хостинг, FTP, OAuth токены) — **gitignored** для секретов | deploy / publish skills |
| `meetings/YYYY-MM-DD_<тема>.md` | Саммари каждой встречи (участники, договорённости, action items) | загружается при работе с клиентом |
| `patches/*.md` | Особенности клиента, ошибки, уроки | предотвращает повтор инцидентов |
| `seo/`, `reports/`, `presale/kp/` | артефакты работы (аудиты, КП, ТЗ) | при тематических задачах |

**Без `CLAUDE.md` и `config.yaml`** — никакая 10-словная команда не сработает корректно, начнётся «расскажи о клиенте».

## Минимум для продукта/проекта (не клиент)

Для внутренних продуктов (`products/<slug>/`) или мета-папок (`personal/`, `decisions/`):

- `README.md` или `CLAUDE.md` — что это, для кого, текущий статус
- `roadmap.md` или `plan.md` — этапы / milestones
- `decisions/` — записи значимых решений (формат `decisions/YYYY-MM-DD-<topic>.md`)

## Чек-лист «готов ли клиент к /cowork»

Прежде чем запустить `/cowork КП <slug> v2`, проверь:

```
- [ ] clients/<slug>/CLAUDE.md существует и содержит бренд + статус + контакт
- [ ] clients/<slug>/config.yaml — палитра, шрифты, регион
- [ ] clients/<slug>/presale/kp/ — есть предыдущая версия КП (если v2/v3)
- [ ] clients/<slug>/meetings/ — есть свежий саммари (<14 дней)
- [ ] artvision-data/.claude/rules/clients-registry.md — клиент в правильной секции
- [ ] artvision-data/clients/artvision-pro/cases/cases-2026-*.md — есть тематический кейс по нише (если первый КП)
```

Если 4+/6 пунктов есть → 10-словный промпт сработает.
Если меньше → сначала `/new-client` или `/init` (см. `~/.claude/rules/cherny-tips.md` про mistake-log).

## Уровни плотности контекста

| Уровень | Что есть | Какой промпт работает |
|---------|----------|----------------------|
| **L0 — пусто** | только название клиента | «Кто такой X? Что мы знаем?» — нужен онбординг |
| **L1 — slot создан** | CLAUDE.md + config.yaml + access.md (даже если короткие) | «КП X с нуля по сайту example.com» — `/presale-kp` справится |
| **L2 — есть meetings** | + 1-2 meeting summaries за последний месяц | «КП X v2 с учётом замечаний» — поймёт что менять |
| **L3 — полный контекст** | + tematic case + design-system + brand-voice + patches | «КП X v3» — 3 слова, всё подтянет автоматом |

Цель — довести всех платящих клиентов до **L3**, presale минимум до **L1**.

## Аудит текущих клиентов (2026-05-13)

| Клиент | CLAUDE.md | config.yaml | meetings/ | Уровень |
|--------|:---------:|:-----------:|:---------:|---------|
| OTIDO, Blumart, Творим, Madwave | ✅ | ✅ | ✅ | L2-L3 |
| Avto.world, ANT Partners, Burenie-SKV | ✅ | ✅ | частично | L2 |
| Aleksandra-Dental (Dentix) | ✅ (8K) | ✅ | ✅ | L3 |
| Grelka-Gudelka | ✅ (8.6K) | ? | ✅ presale/ | L2 |
| Anzhee, S32, Радуга | ✅ (создано 13.05) | частично | n/a (presale) | L1 |
| Geely | ✅ (короткий) | ? | ❌ | L1 |

Цель Q2 2026: все active клиенты на L2+, все presale на L1+.

## Связь с другими механизмами

- **`/cowork`** — пользуется context environment как базой; короткий промпт = работает только при L1+
- **`/presale-kp`** — обязательно требует L1 (extract design-system из config.yaml)
- **`/page-create`** — обязательно требует L2 (есть design-system + последний meeting)
- **`/new-client`** (skill) — создаёт L0 → L1 за один прогон
- **Pre-Task Protocol** в `~/.claude/rules/kp-brand.md` — это автоматический загрузчик context environment

## Антипаттерны

- ❌ Запустить `/cowork КП X` если у X нет CLAUDE.md → cowork остановится на «не знаю кто это»
- ❌ Создавать CLAUDE.md клиенту с выдуманными фактами «чтобы был файл» → хуже чем отсутствие, ловушка для будущих сессий
- ❌ Дублировать в CLAUDE.md клиента то что уже в `~/.claude/rules/` (workflow, security, factcheck) → раздувает контекст
- ❌ Не обновлять `meetings/` после звонка — теряем L2 → L1, последующие промпты слабеют

## Прецеденты

- **2026-05-13 (DENTIX план M1):** L3-клиент → за 1 промпт «план M1 26.05» собран `plan-launch-2026-05-12.html` + 5 связанных артефактов в `clients/aleksandra-dental/plan/` без интервью
- **2026-05-13 (3× /init):** anzhee + s32 + radugazvukov переведены с L0 на L1 параллельно за 1 промпт «сделай им /init параллельно»
- **2026-05-12 (Grelka horeca template):** L2-клиент с полным context-log → правки template (Pulse → Watch, цены убрали) делались молча по правилу `feedback_no_petty_confirmations.md`

## История

- **2026-05-13** — создано (закрытие TBD из `cowork/SKILL.md`). Поводом стала сверка с habr-статьями про Anthropic Cowork и явный запрос Антона «чекай все ли еще сходится со статьей с habr про коворк и workflow»
