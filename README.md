# Claude Code Settings — Artvision Agency

> Глобальные настройки, агенты и хуки для Claude Code

**Репозиторий:** https://github.com/artvision-agency/claude-code-settings
**Статус:** 🔒 Private
**Обновлено:** 2026-01-28

---

## Что внутри

| Компонент | Описание | Количество |
|-----------|----------|------------|
| **Агенты** | Специализированные субагенты для разных задач | 130+ |
| **Хуки** | Автоматизация и оптимизация токенов | 4 |
| **Инструкции** | Глобальные правила и workflow | CLAUDE.md |
| **Скрипты** | Автоматизация setup и синхронизации | 2 |

---

## Быстрый старт

### Первая машина (уже настроена)

```bash
cd ~/.claude
git pull  # Получить обновления
```

### Вторая машина (новая)

```bash
# 1. Установить GitHub CLI
brew install gh  # macOS

# 2. Авторизация
echo "GITHUB_TOKEN" | gh auth login --with-token

# 3. Клонировать настройки
gh repo clone artvision-agency/claude-code-settings ~/.claude

# 4. Создать файл с токеном
echo "GITHUB_TOKEN=xxx" > ~/.claude/.secrets

# 5. Проверка
~/.claude/scripts/setup-github-access.sh
```

**Полная инструкция:** [SETUP_SECOND_MACHINE.md](SETUP_SECOND_MACHINE.md)

---

## Структура репозитория

```
.claude/
├── README.md                         # Этот файл
├── CLAUDE.md                         # Глобальные инструкции для Claude
├── ARTVISION_REPOS.md                # Список всех 33 репозиториев
├── SETUP_NEW_CLAUDE_ACCOUNT.md       # Настройка на той же машине
├── SETUP_SECOND_MACHINE.md           # Настройка на другой машине
│
├── agents/                           # 130+ специализированных агентов
│   ├── frontend-developer.md         # Frontend разработка
│   ├── seo-analyzer.md               # SEO аудит
│   ├── token-guardian.md             # Оптимизация токенов
│   └── ...                           # +127 агентов
│
├── hooks/                            # Автоматизация и оптимизация
│   ├── README.md                     # Документация хуков
│   ├── pre-read.sh                   # Блокировка больших файлов
│   ├── context-monitor.sh            # Мониторинг контекста
│   └── post-frontend.sh              # Обработка после frontend
│
├── scripts/                          # Скрипты автоматизации
│   ├── setup-github-access.sh        # Автоматическая настройка
│   └── sync-status.sh                # Синхронизация статуса
│
└── .secrets                          # Токены (НЕ в Git!)
```

---

## Ключевые компоненты

### 📋 CLAUDE.md — Глобальные инструкции

- **Синхронизация между клиентами** (Local CC, claude.ai/code, claude.ai)
- **Git Auto-Commit** правила
- **Платные API** — защита от случайных расходов
- **Оптимизация токенов** — правила и лимиты
- **Workflow** для создания веб-страниц

### 🤖 Агенты (130+)

Категории:
- **Core Development** (12): backend, frontend, fullstack, api-designer
- **Language Specialists** (20): python, typescript, go, php, rust
- **Infrastructure** (15): devops, kubernetes, terraform, cloud
- **Quality & Security** (12): code-reviewer, qa, security-auditor
- **Data & AI** (15): data-engineer, ml-engineer, llm-architect
- **Developer Experience** (10): documentation, refactoring, mcp
- **Specialized Domains** (18): seo, fintech, blockchain, game-dev
- **Business & Product** (10): product-manager, technical-writer
- **Meta-Orchestration** (8): multi-agent-coordinator, workflow
- **Research & Analysis** (10): competitive-analyst, market-researcher

### 🔧 Хуки

- `pre-read.sh` — Блокировка файлов >10K строк (защита от перерасхода токенов)
- `context-monitor.sh` — Предупреждение при переполнении контекста
- `post-frontend.sh` — Автоматическая обработка после frontend разработки
- `save_session.py` — Сохранение истории сессий

### 📜 Скрипты

- `setup-github-access.sh` — One-liner настройка для новой машины
- `sync-status.sh` — Синхронизация статуса проектов

---

## Синхронизация между машинами

### Workflow

```bash
# Машина 1: После работы
cd ~/.claude
git add .
git commit -m "chore: update agents"
git push

# Машина 2: Перед работой
cd ~/.claude
git pull
```

### Автоматизация

Добавьте в `~/.zshrc`:

```bash
alias claude-sync-push='cd ~/.claude && git add . && git commit -m "chore: sync" && git push && cd -'
alias claude-sync-pull='cd ~/.claude && git pull && cd -'
```

---

## Связанные репозитории

| Репозиторий | Назначение | Статус |
|-------------|-----------|--------|
| [artvision-data](https://github.com/artvision-agency/artvision-data) | Основной проект данных | 🔒 Private |
| [artvision-tg-bot](https://github.com/artvision-agency/artvision-tg-bot) | Telegram бот | 🔒 Private |
| [devops-agent](https://github.com/artvision-agency/devops-agent) | DevOps мониторинг | 🔒 Private |
| [sub-agents.directory](https://github.com/artvision-agency/sub-agents.directory) | Справочник агентов (100+) | 🌍 Public |

**Полный список:** [ARTVISION_REPOS.md](ARTVISION_REPOS.md)

---

## Безопасность

### ❌ НЕ коммитить в Git

- `.secrets` — Файл с токенами
- `settings.json` — Локальные настройки Claude Code
- `history.jsonl` — История сессий
- `cache/` — Кэши
- `projects/` — Приватные данные проектов

### ✅ Безопасное хранение токенов

Токены хранятся в `~/.claude/.secrets` (добавлен в `.gitignore`):

```bash
# GitHub Personal Access Token
GITHUB_TOKEN=ghp_xxx
```

---

## Использование

### В Claude Code (терминал)

Настройки применяются автоматически из `~/.claude/CLAUDE.md`

### В claude.ai/code (веб)

1. Клонировать репозиторий на локальной машине
2. Открыть проект в claude.ai/code
3. Настройки синхронизируются через Git

### В claude.ai (веб-чат)

1. Скопировать содержимое `~/.claude/CLAUDE.md`
2. Вставить в начало разговора или Project Knowledge

---

## Обновления

### Добавить нового агента

```bash
cd ~/.claude/agents
# Создать новый агент по шаблону
cp template.md new-agent.md
# Отредактировать
nano new-agent.md
# Закоммитить
git add new-agent.md
git commit -m "feat: add new-agent"
git push
```

### Обновить CLAUDE.md

```bash
cd ~/.claude
nano CLAUDE.md
git add CLAUDE.md
git commit -m "docs: update instructions"
git push
```

---

## Статистика

- **Агентов:** 130+
- **Хуков:** 4
- **Скриптов:** 2
- **Инструкций:** 1 (CLAUDE.md — 400+ строк)
- **Репозиториев Artvision:** 33
- **Строк кода:** 37,000+

---

## Лицензия

**Private** — только для Artvision Agency

---

## Контакты

**Artvision Agency** — SEO & Digital Marketing с 2007

- 🌐 [artvision.pro](https://artvision.pro)
- 📧 info@artvision.pro
- 💼 [LinkedIn](https://linkedin.com/company/artvision-agency)

---

**Последнее обновление:** 2026-01-28
**Версия:** 1.0.0
