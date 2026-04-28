# External Agents — подключённые репозитории

> Внешние репозитории агентов/скиллов клонированы shallow в `~/external-agents/`, подключение через symlink.
> Дата подключения: 2026-04-18.

## Клонированные репо

| Репо | Путь | Что взято |
|---|---|---|
| [VoltAgent/awesome-claude-code-subagents](https://github.com/VoltAgent/awesome-claude-code-subagents) | `~/external-agents/voltagent-subagents/` | Просмотрено 08-business-product (11 дубликатов, не подключали) |
| [VoltAgent/awesome-agent-skills](https://github.com/VoltAgent/awesome-agent-skills) | `~/external-agents/voltagent-skills/` | Листинг 1000+ skills (pptx от Anthropic — отдельная установка через plugin) |
| [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | `~/external-agents/alirezarezvani-skills/` | Подключено 7 C-level скиллов (см. ниже) |

## Подключённые скиллы (symlink в ~/.claude/skills/)

| Скилл | Приоритет | Зачем |
|---|:---:|---|
| `board-deck-builder` | ★★★ | Структура deck: Headline → Data → Narrative → So what. Для визитки/КП информативность |
| `internal-narrative` | ★★★ | Один факт → разные аудитории. Консистентность сообщений для разных типов клиентов |
| `cmo-advisor` | ★★ | Стратегия C-уровня маркетинга (дополняет наш marketing-playbook) |
| `ceo-advisor` | ★★ | Founder/CEO narrative, вводные слайды |
| `executive-mentor` | ★★ | Как подавать себя C-level клиентам (корпорации типа Puratos) |
| `founder-coach` | ★ | Ракурс на основателя |
| `scenario-war-room` | ★★ | Отработка возражений клиентов |

## Почему symlink (не copy)

- При `git pull` в `external-agents/alirezarezvani-skills/` — обновления подтягиваются автоматически
- Не дублируем файлы
- Легко отключить: `rm ~/.claude/skills/<имя>`

## Обновление

```bash
cd ~/external-agents/alirezarezvani-skills && git pull
cd ~/external-agents/voltagent-subagents && git pull
cd ~/external-agents/voltagent-skills && git pull
```

## Что ПРОВЕРЕНО и НЕ подключено (дубликаты)

| Внешний | Наш аналог |
|---|---|
| marketing-psychology | marketing-psychology |
| copywriting | copywriting |
| landing-page-generator | landing-page-agent |
| brand-guidelines | brand-guidelines |
| marketing-ops | marketing-ops |
| competitive-intel | competitive-intel |
| decision-logger | /decision |
| sales-engineer | sales-engineer (встроенный + sub-agents.directory) |
| ux-researcher-designer | ux-researcher (встроенный) |
| ui-design-system | design-extract + ui-ux-pro-max |
| VoltAgent: 08-business-product × 11 | все встроенные |

## Не подключено пока (нужно обсудить)

- `anthropics/pptx` — официальный skill от Anthropic для PowerPoint. Установка через `claude plugin install` (не symlink). Нужно, если планируем экспорт визитки в PPTX для enterprise.
- `contract-and-proposal-writer` (alirezarezvani) — jurisdiction-aware (US/EU/UK/DACH). Пересекается с нашим `presale-kp`+`doc-manager`+`legal-doc`. Подключать если появятся EU-клиенты (Puratos Бельгия)
- `competitive-teardown` (внешний vs наш `competitive-intel` + `competitive-teardown`) — проверить какой сильнее

## Лицензии

Все три репо — MIT (проверено в SKILL.md каждого). Можно свободно использовать.
