---
name: qcomment-accept-only-published
description: qcomment — принимать ТОЛЬКО опубликованные
paths:
  - 'clients/blumart/**'
  - 'clients/*/orm/**'
always: false
size_tokens: 1109
---

# qcomment — принимать ТОЛЬКО опубликованные

> **Установлено:** 2026-05-11, Антон. Прецедент: 2 коммента (97494004, 97491553) приняты со статусом «На проверке» на скриншотах → деньги ушли за недоведённую работу.

## Правило

**При accept в qcomment (`/api/revision` operation=0) — обязательно убедиться что отзыв ОПУБЛИКОВАН в Яндексе.**

Не достаточно того что:
- ❌ исполнитель разместил отзыв (статус «На проверке» — Яндекс модерация ещё идёт)
- ❌ скриншот показывает отзыв (Яндекс может снести в течение часов-дней)
- ❌ qcomment-робот не проверял (robot_find=0)

## Что считается «опубликовано»

✅ **Отзыв найден в live-crawl reviews.yandex.ru/shop/<domain>** ПО СОРТИРОВКЕ «по новизне»:
- crawl снят не более 24ч назад
- сортировка `?sort=date` или эквивалент (см. `live-reviews-by-newness.md`)
- найден по match: author + text_substr (минимум 30 символов)

ИЛИ

✅ **На скриншоте qcomment-исполнителя ЯВНО видна метка «Опубликован»** (НЕ «На проверке»). Открыть скриншот, прочитать статус.

## Workflow

Перед `qcomment-accept-pending.py accept ...`:

1. **Запустить crawl с sort=date**:
   ```bash
   ~/.claude/skills/orm-pulse/scripts/playwright-full-crawl.py blumart --sort newest
   ```
2. **Проверить match для каждого pending comment**:
   ```python
   from lib.loaders import find_in_live
   if not find_in_live(slug, comment['name'], comment['message'][:50]):
       print(f"⚠️ {cid}: not published yet — SKIP accept")
   ```
3. **Если найден** → accept.
4. **Если НЕ найден** → проверить скрин: статус «Опубликован»?
   - Если ДА — accept (crawl мог не дойти до этой страницы).
   - Если «На проверке» — **НЕ accept**, перепроверить через 24-48ч.

## Что делать с уже принятыми «На проверке»

- Откат невозможен (qcomment error 603 «Комментарий уже оплачен» после status=1)
- Claim через `/api/claim` после accept → **автоматически отклоняется** (status=1 «оплату не отменили», подтверждено 11.05.2026 за 20 мин)
- Учесть в loss-таблице: цена × N
- Записать в `clients/<slug>/orm/loss-log.csv`

## ⛔ ПРАВИЛЬНЫЙ FLOW при «На проверке» (обновлено 11.05.2026 19:00)

Если коммент в pending (`/api/requests` status=0):
1. **Проверь published** в свежем live-crawl (sort=newest)
2. Если **найден** в live → `accept` (operation=0) ✓
3. Если **НЕ найден** в live → `reject` (operation=2, reason="не опубликован после X дней") — деньги вернутся исполнителю в qcomment, а нашему балансу restore
4. **НЕ accept→claim** — claim после accept отклоняется автоматически

## Прецедент

**2026-05-11 17:27** — Claude через `qcomment-accept-pending.py accept --all` принял оба pending:
- comment_97494004 «крючки в ванную» (Тарас Комаров)
- comment_97491553 «инсталляцию для подвесного» (Павел Васильевич)

Оба со статусом «На проверке» на скрине qcomment-исполнителя Anna762. Live-crawl не нашёл их в 1006 свежих отзывов. Откат заблокирован qcomment API.

## Связь с другими правилами

- `live-reviews-by-newness.md` — сортировка «по новизне» обязательна (Антон 11.05)
- `blumart/CLAUDE.md` — оплачиваем только за результат, не за работу
