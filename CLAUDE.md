# Claude Instructions

## Старт сессии

1. git pull → PROJECTS.md → TODO.md текущего контекста
2. Показать открытые задачи → TaskCreate для каждой
3. После compaction/resume → парсить summary → TaskCreate для pending items

## Поиск контекста прошлой работы

**При любых вопросах «вчера/недавно/делал X / что было сделано / где deploy / какие ссылки»:**
1. ПЕРВЫМ ДЕЛОМ → `ls handovers/HANDOVER-*.md | sort -r | head -10` + Read релевантного (имя содержит дату YYYY-MM-DD и тему).
2. SessionStart hook `start-recent-handovers.sh` уже выводит 3 последних handovers в начале сессии — использовать их.
3. Drive / Asana / GitHub — ТОЛЬКО если в handovers/ пусто или явно требуется внешний источник.
4. Антипаттерн: лезть в Google Drive по ключевым словам клиента, когда контекст лежит в локальном `handovers/`.

## Rules (загружаются всегда из ~/.claude/rules/)

| Файл | Что |
|------|-----|
| `core.md` | Автономность, workflow (Superpowers + Git), skills, параллельность, токены, VPS, антипаттерны |
| `session.md` | Старт, TODO-маршрутизация, меню, интервью, ready-чеклист, recap, comp recovery |
| `quality.md` | Gates по типу задачи, qa-full.sh, challenge-self, уроки B2B/Puratos |
| `security.md` | AUTO/CONFIRM, табу AI в публичных, бренды продуктов |
| `git.md` | Auto-commit, аккаунты, sync |
| `self-corrections.md` | Топ повторяющихся ошибок |
| `antipatterns.md` | ANTIPATTERN-теги: что запрещено |
| `agent-roster.md` | Маршрутизация задач → агенты |
| `consilium-matrix.md` | `/cons` vs `round_table` vs Agent-рой vs Codex |
| `bulletproof-patterns.md` | Challenge loop, 40% rule, anti-rationalization |
| `tool-adoption-proof.md` | Round-table перед adopt любого нового инструмента |
| `asana-required-fields.md` | assignee + due_on + project_id обязательны |
| `deploy-report-template.md` | Таблица 15 инструментов после deploy клиентского документа |
| `tg-auto-capture.md` | tg-send-tracked.sh для статус-запросов команде |
| `todo-routing.md` | TODO по контексту, sync через git |
| `no-smoothing.md` | Запрет сглаживания углов, обязательный формат при проблемах |
| `shortcuts.md` | Ключевые короткие команды |

## Skills (загружаются по запросу)

Полный словарь опечаток → skill `shorthand` (триггер: непонятная команда). Детали workflow → `artvision-workflow`. Quality gates → skill `factcheck`.
