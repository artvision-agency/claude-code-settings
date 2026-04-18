---
name: sbis-support
description: "Отправка обращения в техподдержку СБИС (Saby) через чат. Триггеры: 'сбис поддержка', 'sbis support', 'написать в сбис', 'обращение в сбис', 'тикет сбис', 'сбис техподдержка', 'проблема сбис', 'saby support'."
---

# СБИС (Saby) Support — обращение в техподдержку через чат

## Важно

- **Yandex Browser** обязателен (Chrome НЕ видит КриптоПро/ЭЦП)
- **ЭЦП** должна быть вставлена (USB-токен)
- Поддержка = `?` → **Поддержка Saby** (НЕ "Контакт-центр" — это наш для клиентов)
- Профиль сохраняется в `/tmp/yandex-sbis-profile` (переиспользуется между сессиями)

## Конфигурация

| Параметр | Значение |
|----------|----------|
| Browser | Yandex `/Applications/Yandex.app/Contents/MacOS/Yandex` |
| Profile | `/tmp/yandex-sbis-profile` |
| URL | `https://online.sbis.ru/` |
| Аккаунт | ИП Камеристый Антон Германович, ИНН 781301004787 |
| Сертификат | ЭЦП на USB-токене |
| Скрипт | `~/.claude/scripts/sbis-support-chat.py` |
| Копии тикетов | `/Users/antonk/artvision-data/docs/support/` |

## Алгоритм

### 1. Собрать информацию для обращения

Получить от пользователя (или из контекста):
- **Категория** бота: ЭДО и EDI, Отчетность, Электронная подпись, и т.д.
- **Описание проблемы** — подробно, с ИНН/КПП контрагента
- **Что просим** — конкретные действия от поддержки

### 2. Отправить через скрипт

```bash
# Отправка сообщения
python3 ~/.claude/scripts/sbis-support-chat.py --message "текст обращения" --category "ЭДО и EDI"

# Из файла
python3 ~/.claude/scripts/sbis-support-chat.py --message-file /tmp/sbis-msg.txt

# Проверка ответа
python3 ~/.claude/scripts/sbis-support-chat.py --status
```

### 3. Если скрипт не работает — ручной Playwright

```python
# Yandex Browser + ECP login
context = await p.chromium.launch_persistent_context(
    user_data_dir="/tmp/yandex-sbis-profile",
    executable_path="/Applications/Yandex.app/Contents/MacOS/Yandex",
    headless=False,
    args=["--no-first-run", "--disable-blink-features=AutomationControlled"],
    viewport={"width": 1440, "height": 900},
    ignore_default_args=["--enable-automation"],
    timeout=90000,
)
```

**Путь по боту:**
1. `?` (sabyPage-HelpButton) → **Поддержка Saby**
2. Выбрать категорию (ЭДО и EDI)
3. Подкатегория → детализация
4. **"Нет, позови оператора"** — КЛЮЧЕВАЯ КНОПКА
5. Отправить описание проблемы в textarea

### 4. Сохранить копию

В `/Users/antonk/artvision-data/docs/support/sbis-ticket-{YYYY-MM-DD}.md`

### 5. Follow-up

```bash
# Проверить ответ
python3 ~/.claude/scripts/sbis-support-chat.py --status
# Или вручную: online.sbis.ru → ? → Поддержка Saby
```

## Категории бота (верхний уровень)

| Категория | Когда использовать |
|-----------|-------------------|
| ЭДО и EDI | Документооборот, подписание, роуминг |
| Отчетность | Налоговая, ФНС, отчёты |
| Электронная подпись | Проблемы с ЭЦП, сертификаты |
| Бухгалтерия и зарплата | Учёт, расчёты |
| МЧД и другие вопросы | Всё остальное |

## Путь до оператора (проверено 2026-04-03)

```
? → Поддержка Saby → ЭДО и EDI → Работа с документами →
  Подписать или отклонить документ → Нет права подписи по организации →
  "Нет, позови оператора" → [описание проблемы]
```

## Типичные ошибки

| Ошибка | Решение |
|--------|---------|
| Chrome не видит ЭЦП | Использовать Yandex Browser |
| "Контакт-центр" не то | Это НАШ контакт-центр, а не поддержка |
| "Чат" открывает новости | Это новости Saby, а не чат поддержки |
| Бот зацикливается | Нажать "Нет, позови оператора" |
| Профиль заблокирован | `rm -f /tmp/yandex-sbis-profile/SingletonLock` |
| Yandex не закрывается | `pkill -9 -f Yandex` |

## Безопасность

- **CONFIRM-уровень:** показать текст обращения ПЕРЕД отправкой
- Не отправлять пароли/токены в текст тикета
- Не упоминать Claude/AI в тексте обращения
