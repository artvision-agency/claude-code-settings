# Artvision Agency — Репозитории

**Обновлено:** 2026-01-28
**GitHub CLI:** ✅ Настроен (gh auth status)
**Всего репозиториев:** 33 (24 private, 9 public)

---

## Локальные репозитории (4 шт)

| Проект | Путь | Remote | Branch |
|--------|------|--------|--------|
| artvision-data | `/Users/antonk/artvision-data` | artvision-agency/artvision-data | main |
| artvision-tg-bot | `/Users/antonk/artvision-tg-bot` | artvision-agency/artvision-tg-bot | main |
| artvision-portal | `/Users/antonk/artvision-portal` | artvision-agency/artvision-portal | main |
| devops-agent | `/Users/antonk/devops-agent` | artvision-agency/devops-agent | main |

---

## Все репозитории (33 шт)

### Основные проекты

| Репозиторий | URL | Статус |
|-------------|-----|--------|
| artvision-data | https://github.com/artvision-agency/artvision-data | 🔒 private |
| artvision-tg-bot | https://github.com/artvision-agency/artvision-tg-bot | 🔒 private |
| devops-agent | https://github.com/artvision-agency/devops-agent | 🔒 private |
| sub-agents.directory | https://github.com/artvision-agency/sub-agents.directory | 🌍 public |

### SEO & Automation

| Репозиторий | URL | Статус |
|-------------|-----|--------|
| seo-factory | https://github.com/artvision-agency/seo-factory | 🔒 private |
| semantic-pipeline | https://github.com/artvision-agency/semantic-pipeline | 🔒 private |
| artvision-recommender | https://github.com/artvision-agency/artvision-recommender | 🌍 public |
| screenshot-service | https://github.com/artvision-agency/screenshot-service | 🌍 public |

### Боты & Интеграции

| Репозиторий | URL | Статус |
|-------------|-----|--------|
| elama-balance-bot | https://github.com/artvision-agency/elama-balance-bot | 🔒 private |
| youtube-summarizer-bot | https://github.com/artvision-agency/youtube-summarizer-bot | 🔒 private |
| x2tg-bot | https://github.com/artvision-agency/x2tg-bot | 🔒 private |
| familyfun-bot | https://github.com/artvision-agency/familyfun-bot | 🔒 private |
| smm-bot-artvision | https://github.com/artvision-agency/smm-bot-artvision | 🔒 private |
| artvision-bot | https://github.com/artvision-agency/artvision-bot | 🔒 private |

### Туризм & Развлечения

| Репозиторий | URL | Статус |
|-------------|-----|--------|
| trip-hunters | https://github.com/artvision-agency/trip-hunters | 🔒 private |
| trip-hunters-landing | https://github.com/artvision-agency/trip-hunters-landing | 🔒 private |
| triphunters | https://github.com/artvision-agency/triphunters | 🔒 private |
| Reelzzz-miniapp | https://github.com/artvision-agency/Reelzzz-miniapp | 🔒 private |

### Портфолио & Дизайн

| Репозиторий | URL | Статус |
|-------------|-----|--------|
| artvision-portal | https://github.com/artvision-agency/artvision-portal | 🔒 private |
| artvision-portfolio-2025 | https://github.com/artvision-agency/artvision-portfolio-2025 | 🔒 private |
| design-references | https://github.com/artvision-agency/design-references | 🔒 private |
| aivision-web | https://github.com/artvision-agency/aivision-web | 🔒 private |

### Claude Code & AI

| Репозиторий | URL | Статус |
|-------------|-----|--------|
| artvision-skills | https://github.com/artvision-agency/artvision-skills | 🔒 private |
| awesome-claude-code-subagents | https://github.com/artvision-agency/awesome-claude-code-subagents | 🌍 public |
| awesome-claude-code-plugins | https://github.com/artvision-agency/awesome-claude-code-plugins | 🌍 public |
| ralph-orchestrator | https://github.com/artvision-agency/ralph-orchestrator | 🌍 public |
| get-shit-done | https://github.com/artvision-agency/get-shit-done | 🌍 public |
| moltbot | https://github.com/artvision-agency/moltbot | 🌍 public |

### UI Components & Infra

| Репозиторий | URL | Статус |
|-------------|-----|--------|
| react-shadcn-components | https://github.com/artvision-agency/react-shadcn-components | 🌍 public |
| ccflare | https://github.com/artvision-agency/ccflare | 🌍 public |
| omarchy | https://github.com/artvision-agency/omarchy | 🌍 public |

### Специализированные

| Репозиторий | URL | Статус |
|-------------|-----|--------|
| stressed-skin-calculator | https://github.com/artvision-agency/stressed-skin-calculator | 🔒 private |
| demo-repository | https://github.com/artvision-agency/demo-repository | 🔒 private |

---

## Работа с репозиториями

### Через gh CLI (без клонирования)

```bash
# Читать файл из любого репо
gh api repos/artvision-agency/REPO_NAME/contents/PATH/TO/FILE --jq .content | base64 -d

# Список файлов
gh api repos/artvision-agency/REPO_NAME/contents/FOLDER

# Issues и PR
gh issue list --repo artvision-agency/REPO_NAME
gh pr list --repo artvision-agency/REPO_NAME

# Клонировать при необходимости
gh repo clone artvision-agency/REPO_NAME
```

### Обновление локальных репозиториев

```bash
cd ~/artvision-data && git pull
cd ~/artvision-tg-bot && git pull
cd ~/artvision-portal && git pull
cd ~/devops-agent && git pull
```

---

## Безопасность

✅ GitHub CLI авторизован через keyring macOS
✅ Все remote URL используют HTTPS без токенов
✅ Токен хранится в системном хранилище

**Проверка авторизации:**
```bash
gh auth status
```
