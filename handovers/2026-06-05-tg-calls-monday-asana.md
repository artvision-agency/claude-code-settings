# HANDOVER — Созвоны в понедельник → Asana/Календарь (TG check)

**Дата:** 2026-06-05 22:30 MSK · Сессия: 18204f05 · Контекст переполнен (102%) → /clear

## Задача Антона (дословно)
«чекни в тг все лк, созвоны в пн, в асана и календари напоминаний»
= прочитать личные чаты TG → найти договорённости о созвонах на ПОНЕДЕЛЬНИК 08.06 → завести напоминания в Asana + Google Calendar.

## Статус каналов (проверено)
| Канал | Статус |
|---|---|
| TG личка | 🔴 ВСЕ user-сессии Telethon МЕРТВЫ (tg_userbot/.tg_artvision/.telegram_session → NOT_AUTHORIZED, проверено 2×). Жив только bot_session (это бот — личку не видит). |
| Asana | 🟢 работает, workspace «Marketing» gid=860693669973770 |
| Google Calendar | 🔴 OAuth не настроен (в TODO «одноразовый OAuth bootstrap») |

## БЛОКЕР
Без живой TG-сессии нечего найти → нечем наполнить Asana/календарь. Re-auth требует ввода кода (только Антон).
- Путаница: Антон сказал «всё авторизовано» — он про логин в ПРИЛОЖЕНИИ TG. Claude использует ОТДЕЛЬНУЮ программную MTProto-сессию (Telethon), она протухла 9д назад. Класс ошибки = feedback_anthropic_api_vs_max_oauth.

## Что Антон должен сделать (1 команда)
```
! cd ~/artvision-data && python3 .claude_temp_scripts/tg_auth.py
```
Спросит phone + код из TG (+ 2FA если есть). Успех = `AUTH OK -> AntonKamer`.

## После AUTH OK — план Claude
1. `python3 .claude_temp_scripts/tg_calls_check.py` — сканит 80 диалогов за 10 дней, ищет триггеры созвонов + понедельник, сортирует ПН-хиты вперёд. (Скрипт ГОТОВ, рабочий — async, py3.14.)
2. Показать список: кто / когда / тема.
3. Завести в Asana: задача-напоминание на каждый созвон, due_on=2026-06-08, project_id по клиенту, assignee — НЕ автоназначать (спросить если не явно). Правило asana-required-fields.
4. Calendar — пропустить до OAuth bootstrap (или Антон диктует — тогда сразу в Asana).

## Готовые файлы (в ~/artvision-data/.claude_temp_scripts/)
- `tg_auth.py` — интерактивная авторизация (pyright-warnings ложные, async код рабочий)
- `tg_calls_check.py` — сканер созвонов

## Session Tasks
#1 Проверить TG созвоны пн — BLOCKED (нужна re-auth)
#2 Завести в Asana — pending (после #1)
#3 Завести в Calendar — blocked (нет OAuth)

## Побочная находка
asana-sync падал 24× из-за транзиентного `No space left` (лог /tmp), сейчас диск 31Gi свободно. Не Asana виновата. Если фейлы продолжатся — смотреть `~/Library/Logs/asana-sync.error.log`.
