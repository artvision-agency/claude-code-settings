# Claude Instructions

## СТИЛЬ РАБОТЫ

- Получил цель → сам разбей на шаги → сам выполни. НЕ спрашивать "а теперь шаг 2?"
- Plan mode — только для сложных/неоднозначных задач
- Короткие сообщения ("sync", "asana monday") = КОМАНДЫ, не вопросы. Делай, не спрашивай
- НЕ упрощать ради краткости — лучше длинный точный ответ, чем короткий неточный
- Учитывать workflow пользователя (git, клиенты) при сравнениях, не давать generic ответы

---

## ПУБЛИЧНЫЙ КОНТЕНТ — ТОЛЬКО ЧЕРЕЗ ПРОВЕРКУ ЧЕЛОВЕКОМ

Публикация на сайт/CMS/соцсети/рассылки = ЗАПРЕЩЕНО без подтверждения Антона или Андрея.
Автономно можно: файлы в репо, задачи Asana, аудиты, черновики.

---

## Git Auto-Commit

После изменения файлов автоматически: `git add` → `git commit` → `git push`.

Формат: `<type>: <short description>` + `Co-Authored-By: Claude <noreply@anthropic.com>`
Типы: feat, fix, docs, refactor, style, chore

**НЕ коммитить:** .env, credentials, keys (кроме tokens.json), .claude_temp_scripts/.
**tokens.json:** сообщить что изменилось → спросить подтверждение → закоммитить.
**"sync" / "пуш":** выполнять сразу без подтверждения.

---

## ОПТИМИЗАЦИЯ ТОКЕНОВ

### Правила чтения файлов
- Файл >2K строк → Grep или Read с offset/limit
- Файл >10K строк → ТОЛЬКО Grep
- node_modules/ → НИКОГДА не читать

### Тесты — через обёртку
```bash
~/.claude/scripts/run-tests.sh "<описание>" "<команда>"
```
Успех → 1 строка. Ошибка → полный вывод. Fail-fast.

### Хуки (~/.claude/hooks/)
- `pre-read.sh` — блокирует файлы >10K строк
- `context-monitor.sh` — предупреждает о переполнении

### Агенты
**Агент = Claude + системный промпт.** НЕ имеет суперспособностей.
Агент без данных = галлюцинации. Гибридный подход: собрать данные → передать агенту.

---

## HTML ФАЙЛЫ ДЛЯ КЛИЕНТОВ

### Автономность — ОБЯЗАТЕЛЬНО

Файлы для клиентов = без интернета. ЗАПРЕЩЕНО:
- CDN (Tailwind, Bootstrap, jQuery)
- Google Fonts / внешние шрифты
- Внешние изображения, скрипты, стили

Вместо этого:
- CSS/JS — inline в `<style>` / `<script>`
- Шрифты — системный стек: `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif`
- Изображения — base64 `data:image/...;base64,...`
- Проверка: `grep -oE 'https?://[^"'\''> ]+' file.html` — не должно быть внешних URL

**Tailwind JS CDN НЕ работает на iOS Safari!** Только предкомпилированный CSS (Tailwind 2.x) или обычный CSS.

### Изображения — оптимизация
- Макс размер HTML: 500KB, изображения: <100KB, ширина: 800px, JPEG: 70%
```bash
sips -Z 800 image.png --out optimized.png              # Ресайз
sips -Z 800 -s formatOptions 70 image.jpg --out opt.jpg # JPEG+качество
base64 -i optimized.png | tr -d '\n'                     # Base64
```

### Создание веб-страниц
```
1. ПАРСИНГ — WebFetch, ПОДСЧИТАТЬ блоки (H2, FAQ, карточки), НЕ сокращать
2. ГЕНЕРАЦИЯ — Task(frontend-developer), 100% контента + стили из config.yaml
3. ПРОВЕРКА — сверить блоки с оригиналом, открыть в браузере
```

Чек-лист: Hero+H1, описание, преимущества, цены, FAQ(5+), кейсы, форма, контакты, CTA.

---

## ТЕСТИРОВАНИЕ ПОСЛЕ СОЗДАНИЯ

Скрипты/cron/hooks/LaunchAgents — тестировать сразу.
- Cron: тестировать с `env -i HOME=... PATH=...` (cron НЕ наследует shell env)
- Перед новой автоматизацией: `crontab -l` и `ls ~/Library/LaunchAgents/` на дубли

---

## СИНХРОНИЗАЦИЯ

### Протокол
- **Начало сессии:** `git pull` + прочитать `sync/SYNC_STATUS.md`
- **Конец сессии:** обновить SYNC_STATUS.md + `git add sync/ && git commit && git push`

### Проекты

| Проект | Путь |
|--------|------|
| artvision-data | `/Users/antonk/artvision-data` |
| artvision-tg-bot | `/Users/antonk/artvision-tg-bot` |
| devops-agent | `/Users/antonk/devops-agent` |

### Аккаунты
- `justtrance@gmail.com` — основной (полные права)
- `adw.artvision.pro@gmail.com` — рабочий (полные права, планируется ограничение)

Между аккаунтами сессии НЕ видны — используй SYNC_STATUS.md через git.

---

## ПРОВЕРКА СОЗДАННЫХ ФАЙЛОВ

- Конфиги: проверить синтаксис (`python3 -c "import json; json.load(open('file'))"`)
- Расширять существующий файл, не создавать новый
- Проверить нет ли дубликатов и конфликтов приоритетов

---

## РАЗРАБОТКА СКИЛЛОВ

Скиллы: `~/.claude/skills/[name]/SKILL.md` (только верхний уровень, вложенные НЕ работают).

Ключевые поля frontmatter:
- `name`, `description` — обязательные
- `disable-model-invocation: true` — только ручной вызов `/name`
- `context: fork` + `agent: Explore` — изолированный субагент
- `allowed-tools` — ограничить инструменты

---

## ВЕРИФИКАЦИЯ ДАННЫХ

При сборе данных из интернета (цены, рейтинги, кейсы, метрики):
- Перекрёстная проверка 2-3 источниками ПЕРЕД вставкой в документ
- Неподтверждённые данные: "по данным компании" / "заявлено"
- Это встроенное поведение, не по запросу

---

## ПЛАТНЫЕ API

ЗАПРЕЩЕНО вызывать без явного "да": Topvisor, Яндекс.Директ, SMS, рассылки.
Показать действие + стоимость → дождаться подтверждения.

---

## РАЗНОЕ

- Временные скрипты → `.claude_temp_scripts/`
- Даты: проверять из env, использовать правильный год в поисковых запросах
- Восстановление сессий: `claude-sessions` / `claude --resume` / `claude --continue`
- При установке в `~/.claude/` — копировать в `artvision-data/.claude/` и пушить
- Агенты в `~/.claude/agents/` = справочник, НЕ влияют на Task tool

### Новая машина
```bash
curl -sL https://raw.githubusercontent.com/artvision-agency/claude-code-settings/main/scripts/full-setup.sh | bash
```
