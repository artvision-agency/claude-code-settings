# Безопасность и уровни автономии

## Два уровня: Auto и Confirm

### 🟢 AUTO — делать без подтверждения
- TG сообщения в **групповой чат команды** (Стас/Антон/Андрей)
- Asana: создание/обновление задач, назначение на команду
- Git: commit, push, sync
- Напоминания **команде** о дедлайнах
- Мониторинг, проверки, аудиты
- Файлы в репо, черновики

### 🔴 CONFIRM — ТОЛЬКО с подтверждением Антона или Андрея
- **Любой контакт с клиентом** (TG, email, ВК, звонок — даже напоминание)
- Публикация на сайт/CMS/соцсети/рассылки
- Платные API (Topvisor, Яндекс.Директ, SMS, рассылки) — показать действие + стоимость
- **ПЕРЕД вопросом о платных API:** сначала проверить наличие токенов в `tokens.json` (python3 -c "..."). Не спрашивать «есть ли доступ?» — проверь сам.
- Новые обязательства/обещания от имени Artvision
- Деструктивные операции (удаление данных клиента, откат продакшена)

**Правило:** если сомневаешься Auto или Confirm → это Confirm.

## ТАБУ: AI/нейросети в публичных материалах

**АБСОЛЮТНЫЙ ЗАПРЕТ** упоминать AI, нейросети, Claude, GPT, ML, LLM в:
- КП для клиентов
- Страницах услуг
- Публичных материалах (vc.ru, Habr, соцсети)
- Отчётах клиентам
- Лендингах продуктов (кроме AIvision — но там "мы делаем ВАС видимым для AI", НЕ "мы используем AI")

**Замены:**
- "Авторская методология" вместо "AI-генерация"
- "Аналитическая система" вместо "нейросеть"
- "Экспертный анализ" вместо "ML"
- Показывать РЕЗУЛЬТАТ, не инструмент

**Брендированные названия продуктов (ОБЯЗАТЕЛЬНО в публичных материалах):**

| Внутреннее | Публичное |
|-----------|-----------|
| PBN/дропы | **Artvision LinkForge** |
| AI GEO/AIvision | **Artvision Radar** |
| SEO Pipeline | **Artvision Flow** |
| Content writer | **Artvision Content Lab** |
| ORM / мониторинг репутации | **Artvision Watch** |
| Competitor monitor | **Artvision Scout** |
| Sales Psychology | **Artvision Insight** |
| HH-leadgen (B2B) | **Artvision Leads** |
| Lead generation factory | **Artvision Funnel** |
| Сбор отзывов (TG-бот) | **Artvision VoxRate** |
| A/B тестирование | **Artvision Lens** *(в КП, реализация — TBD)* |

Формат: `Artvision + [метафора результата]`. Никаких AI/Bot/Neural/Smart/Auto.

## Аккаунты Claude Max

**Три аккаунта:** `justtrance@gmail.com` + `adw.artvision.pro@gmail.com` + `antoniokmr@gmail.com`
**Лимит:** сброс еженедельно

**Проверка лимита:** `/status` → вкладка Usage (реальные данные от Anthropic)
**Переключение:** `claude auth logout && claude auth login --email <другой>`

## Разное

- Временные скрипты → `.claude_temp_scripts/`
- Даты: проверять из env, использовать правильный год в поисковых запросах
- Восстановление сессий: `claude-sessions` / `claude --resume` / `claude --continue`
- При установке в `~/.claude/` — копировать в `artvision-data/.claude/` и пушить
- Агенты в `~/.claude/agents/` = справочник, НЕ влияют на Task tool

### Новая машина
```bash
curl -sL https://raw.githubusercontent.com/artvision-agency/claude-code-settings/main/scripts/full-setup.sh | bash
```
