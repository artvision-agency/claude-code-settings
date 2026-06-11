# Handover: plan/fact ТЗ + backlog консолидации (продолжение EDUCATION)

**Дата:** 2026-05-29 11:30 MSK
**Контекст:** infra (Claude Code config)
**Сессия:** 6f79d39e (resume EDUCATION, был контекст 416%)
**Статус:** завершено (всё закоммичено), требуется /clear
**Предыдущий handover:** `HANDOVER-2026-05-28-1200-infra.md` (architecture + Stage 1-8)

## 🎯 Цель сессии

Продолжение EDUCATION: ответить на вопросы Антона про plan/fact (хук или правило?), зафиксировать ТЗ и backlog незакрытых рекомендаций перед /clear. Несколько /sync по ходу.

## ✅ Что сделано

- `~/.claude/rules/cherny-tips.md` #9 — ИСПРАВЛЕН (был «hooks require restart», стало «file watcher подхватывает авто», с цитатой справки)
- `~/.claude/rules/self-corrections.md` #22 — новая запись «уверенные утверждения о CC-механике из памяти без сверки справки» (прецедент: 5 ошибок за сессию)
- `~/.claude/hooks/stop-claude-code-claim-unverified.sh` — создан, тесты 8/8 PASS, зарегистрирован Stop
- `~/.claude/handovers/TZ-plan-fact-skill-hook-2026-05-29.md` — ТЗ на plan/fact + backlog (секции A/B/C)
- Несколько /sync — artvision-data + .claude запушены, unpushed=0

## 🧠 Решения и ПОЧЕМУ

| Решение | Альтернатива | Почему |
|---|---|---|
| plan/fact = хук+skill пара | только правило | правило не гарантирует (за сессию 3× игнорировал правила из памяти). Хук-детектор = гарантия срабатывания «когда прошу» |
| plan/fact НЕ строить сейчас | строить | контекст 416% = Dumb Zone, наврежу. ТЗ записан → строить после /clear |
| Консолидацию дублей отложить | сделать сейчас | у каждого хука тесты/прецеденты, слить неаккуратно = потерять защиту. Нужен round_table + чистый контекст |
| Security-фильтр при «полный коммит всего» | git add -A как сказал Антон | правило безопасности > команды: исключил tokens-backup, telethon session, venv, daemon-auth |
| cherny-tips #9 исправить | оставить | справка опровергла — был источником моей ошибки про рестарт |

## ❌ Что НЕ сделано (backlog в ТЗ-файле)

- **plan/fact skill+hook** — только ТЗ, постройка после /clear (HIGH)
- **Защита от «слепоты»** (5 слоёв: no-false-negative.md, find-anywhere, credentials-index, cred-get.sh, хук) — НЕ начато (MEDIUM)
- **Консолидация дублей** — 5 stop-хуков честности + 4 finance-хука, кандидаты (MEDIUM, нужен round_table)
- InstructionsLoaded debug hook, тесты 7 orphan-хуков (LOW)

## 📚 Уроки

- **Класс ошибки #22:** уверенные утверждения о Claude Code из памяти без WebFetch справки. 5 раз за сессию, все ловил Антон фразой-зондом «уверен?/справка?/проверка?». Зафиксировано rule+hook
- **plan/fact метод:** сверка не по recap-чеклисту (это itog), а по РЕАКЦИЯМ пользователя (переспрос/поправка = факт ≠ заявлению)
- **При 416% контексте строить нельзя** — только фиксировать ТЗ, строить после /clear

## 🔜 Следующие шаги (приоритет)

1. **HIGH:** Построить plan/fact skill+hook — `~/.claude/handovers/TZ-plan-fact-skill-hook-2026-05-29.md` (полное ТЗ)
2. **MEDIUM:** Защита от «слепоты» (секция A в ТЗ)
3. **MEDIUM:** Консолидация stop-хуков честности (секция C, через round_table)
4. **LOW:** InstructionsLoaded hook, тесты orphan-хуков

## 🗺️ Карта файлов

```
~/.claude/
├── handovers/
│   ├── HANDOVER-2026-05-28-1200-infra.md   ← architecture + Stage 1-8
│   ├── HANDOVER-2026-05-29-1130-infra.md   ← этот файл
│   └── TZ-plan-fact-skill-hook-2026-05-29.md ← ТЗ + backlog (ГЛАВНЫЙ для продолжения)
├── rules/
│   ├── cherny-tips.md                       ← #9 исправлен
│   └── self-corrections.md                  ← #22 добавлен
└── hooks/
    └── stop-claude-code-claim-unverified.sh ← новый, 8/8 тестов
```

## ⚠️ Гачи

- **Контекст был 416%** — все утверждения этой сессии проверены, но если что-то делал в Dumb Zone — перепроверить
- **Security при коммитах:** НИКОГДА не `git add -A` в `~/.claude` без фильтра — там secure-backups/tokens, telethon session, venv. Исключать всегда
- **cherny-tips #9 теперь говорит ОБРАТНОЕ** прежнему — hooks подхватываются file watcher, рестарт НЕ обязателен (но /clear гарантирует)
- **recap 6f79d39e** содержит ORM-цель НЕ из этого диалога (фоновый процесс с тем же session_id) — не путать
- Telethon session expired (8 дней) — для TG-операций нужна re-auth (код вводит Антон)

## 🔗 Связанные ресурсы

- ТЗ продолжения: `~/.claude/handovers/TZ-plan-fact-skill-hook-2026-05-29.md`
- Architecture doc: https://artvision.pro/preview/claude-architecture/
- Предыдущий handover: `HANDOVER-2026-05-28-1200-infra.md`
- Класс ошибки: `self-corrections.md` #22
