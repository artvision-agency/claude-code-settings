# Настройка доступа к Artvision из нового аккаунта Claude

**Дата создания:** 2026-01-28
**Для:** Ваших личных аккаунтов Claude под разными email

---

## Шаг 1: Авторизация GitHub CLI

В новом аккаунте Claude выполните:

```bash
# Авторизация через токен
echo "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" | gh auth login --with-token

# Проверка авторизации
gh auth status

# Проверка доступа к репозиториям
gh repo list artvision-agency --limit 5
```

**Ожидаемый результат:**
```
✓ Logged in to github.com account justtrance-web (keyring)
- Active account: true
```

---

## Шаг 2: Проверка доступа к репозиториям

```bash
# Проверить локальные репозитории
ls -la ~/artvision-data
ls -la ~/artvision-tg-bot
ls -la ~/artvision-portal
ls -la ~/devops-agent

# Проверить git remote
cd ~/artvision-data && git remote get-url origin
```

**Все 4 репозитория должны быть доступны, т.к. они на одном компьютере.**

---

## Шаг 3: Синхронизация настроек Claude

Глобальные настройки и агенты доступны автоматически:

```bash
# Проверить наличие глобальных настроек
cat ~/.claude/CLAUDE.md

# Проверить список репозиториев
cat ~/.claude/ARTVISION_REPOS.md

# Проверить агенты
ls ~/.claude/agents/
```

**Все настройки общие для всех аккаунтов на этом компьютере.**

---

## Шаг 4: Тестовая команда

Проверьте доступ, прочитав файл из приватного репозитория:

```bash
# Через gh CLI (без клонирования)
gh api repos/artvision-agency/artvision-data/contents/sync/SYNC_STATUS.md --jq .content | base64 -d

# Через локальный репозиторий
cd ~/artvision-data && cat sync/SYNC_STATUS.md
```

---

## Шаг 5: Синхронизация между аккаунтами

### В НАЧАЛЕ сессии в любом аккаунте:

```bash
cd ~/artvision-data
git pull

cat sync/SYNC_STATUS.md
```

### В КОНЦЕ сессии:

```bash
cd ~/artvision-data

# Обновить sync/SYNC_STATUS.md с информацией о проделанной работе
# Затем:

git add sync/
git commit -m "sync: update from [account-name] session"
git push
```

---

## Важные файлы для синхронизации

| Файл | Назначение | Где обновлять |
|------|-----------|---------------|
| `~/artvision-data/sync/SYNC_STATUS.md` | Статус проекта | После каждой сессии |
| `~/artvision-data/tokens.json` | API токены | При добавлении новых |
| `~/.claude/CLAUDE.md` | Глобальные инструкции | Общие для всех аккаунтов |
| `~/.claude/ARTVISION_REPOS.md` | Список репозиториев | Общий справочник |

---

## Быстрая проверка доступа

Выполните эту команду в новом аккаунте:

```bash
echo "=== GitHub CLI ===" && gh auth status && echo "" && \
echo "=== Локальные репозитории ===" && ls -d ~/artvision-* ~/devops-agent 2>/dev/null && echo "" && \
echo "=== Глобальные настройки ===" && ls ~/.claude/*.md 2>/dev/null && echo "" && \
echo "✅ Всё настроено!"
```

---

## Troubleshooting

### Проблема: `gh` не авторизован

```bash
# Проверить статус
gh auth status

# Переавторизация
echo "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" | gh auth login --with-token
```

### Проблема: Нет доступа к приватным репозиториям

```bash
# Проверить права токена
gh api user -q '.login'
gh api user/repos --jq '.[].full_name' | grep artvision-agency
```

### Проблема: Git pull требует авторизацию

```bash
cd ~/artvision-data
git remote set-url origin https://github.com/artvision-agency/artvision-data.git
git pull
```

---

## Контакты

При проблемах проверьте:
1. GitHub CLI авторизован: `gh auth status`
2. Токен действителен на github.com/settings/tokens
3. Репозитории на месте: `ls ~/artvision-*`

**GitHub токен действителен до:** проверьте на github.com/settings/tokens
