# Handover: Claude Code architecture education + rules/hooks setup

**Дата:** 2026-05-28 12:00 MSK
**Контекст:** infra (Claude Code config) + ops (Madwave eLama)
**Сессия:** EDUCATION (2f5e1101-cb2f-4d13-9fa9-54f7e8661a3c)
**Статус:** завершено (основное), контекст 309% — нужен /clear + рестарт для активации hooks

## 🎯 Цель сессии

Объяснить Антону архитектуру Claude Code (rules/hooks/skills/agents), сверить с официальной справкой, выполнить рекомендации по улучшению (новые правила + hooks). Параллельно — план Madwave eLama (новый аккаунт).

## ✅ Что сделано

### Madwave eLama (начало сессии)
- `clients/madwave/proposals/elama-newaccount-plan-2026-05-27.md` — план запуска НОВОГО аккаунта eLama (не миграция), A/B 14 дней, S1-S8
- `clients/madwave/proposals/yakov-tg-questions-2026-05-27.md` v3 — короткий вопрос Якову (только направления, 3 пункта). Отправлен Антону в TG для пересылки Якову
- Старый `elama-migration-plan-2026-05-21.md` оставлен как archive

### Claude Code architecture (основное)
- `personal/claude-architecture/architecture-2026-05-27.html` — HTML-документ v2 (1663 строки, 106KB, 8 SVG-диаграмм). Live: **https://artvision.pro/preview/claude-architecture/**
- `personal/claude-architecture/recommendations-validation-2026-05-28.md` — сверка всех рекомендаций со справкой (306 строк)

### Stage 1-8 (выполнение рекомендаций)
- **Stage 1:** 7 orphan-хуков зарегистрированы в `~/.claude/settings.json` (backup `bak-20260528-032439`)
- **Stage 2:** 4 групповых CLAUDE.md: `clients/`, `presales/`, `products/`, `personal/` + path-scoped `clients-pretask.md`
- **Stage 3:** 3 path-scoped правила: `ppc.md` (madwave/grelka/otido), `orm.md` (blumart), `legal-docs.md` (project-wide)
- **Stage 4:** перенос global→project: `branding-policy.md` + `dental-clinic-blueprint.md` (в global — stub-pointer'ы)
- **Stage 5:** ОТМЕНЁН — CLAUDE.md уже 179 строк (под лимитом 200)
- **Stage 6:** `deploy-report-template.md` усилен HARD-RULE про источники + колонка «Источник»
- **Stage 7:** 3 новых hook с unit-тестами (6/6, 3/3, 4/4 PASS): `pre-fork-without-roundtable.sh`, `pre-deploy-numbers-have-sources.sh`, `pre-finance-no-period-split.sh` (backup `bak-...-stage7`)
- **Stage 8:** git commit + push на `artvision-agency/artvision-data` ветка `feat/ops-crm-v1`

## 🧠 Решения и ПОЧЕМУ

| Решение | Альтернатива | Почему |
|---------|--------------|--------|
| Сверка со справкой ДО выполнения 2-7 | Сразу делать всё | Антон спросил «рекомендации основаны на справке?» — нашёл что часть моя, часть из docs |
| Path-scoped rules вместо только subdir CLAUDE.md | Только subdir CLAUDE.md | Subdir CLAUDE.md НЕ выживает /compact (из справки). Path-scoped пере-инжектятся |
| Stage 5 отменён | Сокращать CLAUDE.md | Реальный размер 179 строк < 200. Моё «сильно больше» было неверным |
| @import НЕ для экономии контекста | Вынести routing через @import | Справка: «imported files load at launch, не reduce context» |
| Hooks с тестами ДО регистрации | Сразу регистрировать | Логика проверок моя — без тестов риск false positive/negative |
| Новый eLama аккаунт Madwave (не миграция) | Миграция borisovaloves | Антон: «заводим новый». A/B без простоя, чистка legacy 444 кампаний |

## ❌ Что НЕ сделано

- **Hooks ещё НЕ активны** — нужен рестарт Claude Code (cherny-tips #9: hooks не hot-swap). В текущей сессии 10 новых hook зарегистрированы но не загружены
- **Тесты для 7 orphan-хуков** — не делал (они написаны Антоном ранее, тесты отдельная задача)
- **InstructionsLoaded hook для дебага** — отложено
- **Проблема слепоты (false negative)** — Антон поднял класс ошибок «не нашёл = нет нигде». Предложил 5 слоёв (правило no-false-negative.md + skill find-anywhere + hook + credentials-index + Keychain) — НЕ реализовано, ждёт решения

## 📚 Уроки (для memory)

- **@import не экономит контекст** — фундаментальный факт из справки, влияет на стратегию сокращения CLAUDE.md
- **Subdir CLAUDE.md не выживает /compact** — критично для клиентских правил, использовать path-scoped
- **Hooks могут читать transcript_path** — мощно для verification-хуков (использовал в pre-fork-without-roundtable)
- **30+ hook events, не 5** — я недооценивал систему. SubagentStart/Stop, InstructionsLoaded, TaskCreated и др.
- **Класс ошибок «слепота» (false negative)** защищён слабее чем галлюцинации — кандидат на новое правило

## 🔜 Следующие шаги

1. **HIGH:** Рестарт Claude Code во всех открытых сессиях для активации 10 новых hooks: `/exit` → `claude -c` (или `--resume <id>`). Контекст восстановится из transcript, hooks перечитаются
2. **HIGH:** После рестарта — `/hooks` проверить что 10 новых зарегистрированы и активны
3. **MEDIUM:** Антон отправляет Якову вопрос про направления Madwave (текст в TG)
4. **MEDIUM:** Решить про проблему «слепоты» — делать ли 5 слоёв защиты (no-false-negative.md + и т.д.)
5. **LOW:** Тесты для 7 orphan-хуков (валидация что они делают что декларируют)

## 🗺️ Карта файлов

```
~/.claude/
├── settings.json                          ← +10 hooks (backup bak-20260528-*)
├── rules/
│   ├── artvision-branding-policy.md       ← stub (переехало в project)
│   ├── dental-clinic-pages-blueprint.md   ← stub (переехало в project)
│   └── deploy-report-template.md          ← усилен (источники)
└── hooks/
    ├── pre-fork-without-roundtable.sh      ← новый, тесты 6/6
    ├── pre-deploy-numbers-have-sources.sh  ← новый, тесты 3/3
    └── pre-finance-no-period-split.sh      ← новый, тесты 4/4

~/artvision-data/
├── CLAUDE.md                              ← 179 строк (НЕ трогали, под лимитом)
├── .claude/rules/
│   ├── ppc.md                             ← новый (paths: madwave/grelka/otido)
│   ├── orm.md                             ← новый (paths: blumart)
│   ├── legal-docs.md                      ← новый (project-wide)
│   ├── branding-policy.md                 ← перенос из global
│   ├── dental-clinic-blueprint.md         ← перенос из global
│   └── clients-pretask.md                 ← новый path-scoped
├── clients/CLAUDE.md                      ← новый
├── presales/CLAUDE.md                     ← новый
├── products/CLAUDE.md                     ← новый
├── personal/CLAUDE.md                     ← новый
├── personal/claude-architecture/
│   ├── architecture-2026-05-27.html       ← deployed artvision.pro/preview/claude-architecture/
│   └── recommendations-validation-2026-05-28.md
└── clients/madwave/proposals/
    ├── elama-newaccount-plan-2026-05-27.md
    └── yakov-tg-questions-2026-05-27.md
```

## ⚠️ Гачи

- **Hooks не активны до рестарта** — главное. Зарегистрированы в settings.json, но текущая сессия их не загрузила
- **deploy-report-template.md в global** (`~/.claude/rules/`) — не в artvision-data. При sync на 3 аккаунта проверить что global-rules тоже синкаются (отдельный механизм, не git artvision-data)
- **pre-finance-no-period-split** может давать false positive на лимитных файлах. Bypass `FINANCE_SPLIT_OK=1`
- **pre-fork-without-roundtable** блокирует `gh repo fork`. Bypass `ROUNDTABLE_OK=1`
- Откат hooks: `cp ~/.claude/settings.json.bak-20260528-032439 ~/.claude/settings.json`

## 🔗 Связанные ресурсы

- Live документ: https://artvision.pro/preview/claude-architecture/
- Сверка: `personal/claude-architecture/recommendations-validation-2026-05-28.md`
- Recap: `~/artvision-data/sync/recaps/2f5e1101-cb2f-4d13-9fa9-54f7e8661a3c.md`
- Справка Claude Code: code.claude.com/docs/en/{memory,hooks,skills,sub-agents,cli-reference}
