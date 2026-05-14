# Контакт с мероприятия → атомарный лид-слот в git

> **Триггер:** получен живой контакт с выставки / конференции / нетворкинга.
> Минимум {имя, бренд, телефон} ИЛИ {имя, бренд, мессенджер} ИЛИ {имя, email, бренд}.
> **Цель:** не потерять контакт между сессиями. Каждый лид = коммит в git за <5 минут.
> **Связано:** `new-client.md` (для уже подписанного клиента), `recipient-personalization.md` (для КП).

## Когда срабатывает

- Запись в TG Saved Messages с выставки (имя + бренд + телефон)
- Голосовое «вот контакт с …»
- Фото визитки
- Любое упоминание формата «<имя> <компания> <тел/email>» без существующей папки `clients/<slug>/`

## Когда НЕ срабатывает

- Контакт уже есть в `clients/<slug>/contacts.yaml` или `access.md` → обновляем существующий слот
- Холодный контакт без живой встречи (LinkedIn, входящая заявка) → обычный `/new-client`
- Минимум полей не выполнен → дозапросить, не создавать слот

## SOP (атомарный, без КП)

```
ШАГ 1. Резолвинг идентичности
  - Бренд → канонический сайт через WebSearch "<бренд> официальный сайт"
  - Если 2+ доменов конкурируют (stomshop.pro vs stom-shop.ru) → НЕ угадывать, спросить пользователя
  - Бренд → юрлицо через rusprofile/checko/list-org (ИНН, ОКВЭД, выручка ФНС)
  - Source: код телефона (+7 911 = СПб; +7 495 = МСК) — ориентир, не вердикт

ШАГ 2. Слот клиента (структура из /new-client)
  mkdir -p clients/<slug>/{seo,presale/kp,patches,meetings,contacts}
  Файлы (минимум для лида):
    clients/<slug>/CLAUDE.md             ← контекст: кто, бренд, источник, ICP
    clients/<slug>/config.yaml           ← {site, brand, contacts, segment, status: lead}
    clients/<slug>/contacts/contacts.yaml← структура из reference (см. ниже)
    clients/<slug>/meetings/<YYYY-MM-DD>_<event>.md ← запись встречи
    clients/<slug>/context-log.md        ← журнал: первый коммит = «лид с <event>»

  Обязательные поля contacts.yaml — без `?`-плейсхолдеров где есть данные:
    id, name, role, company, phone, source, source_date, status

ШАГ 3. Реестры
  - artvision-data/PROJECTS.md — добавить строку в раздел Presale/Lead
  - artvision-data/.claude/rules/clients-registry.md — добавить в «Presale — КП отправлено» ИЛИ создать раздел «Lead — нет КП»
  Формат: | <slug> | <бренд> | lead | <event> <date> | next: <конкретное действие> |

ШАГ 4. Коммит в git (atomic, до 5 файлов)
  cd ~/artvision-data
  git add clients/<slug>/ PROJECTS.md .claude/rules/clients-registry.md
  git commit -m "feat(client): добавлен <slug> — лид с <event> <date>"
  git push

ШАГ 5. Asana — задача с явными полями
  Создать задачу: «<slug>: первый контакт после <event>»
  Обязательные поля (asana-required-fields.md + .claude/rules/asana.md):
    - assignee: ТОЛЬКО по явному указанию (НЕ автоназначение)
    - due_on: задаёт постановщик; если не сказал — БЕЗ due_on + спросить «Когда?»
    - project_id: presale (или проект клиента если уже есть)
  Subtasks:
    - подтвердить юрлицо + выручку (rusprofile/checko)
    - профиль получателя (recipient-personalization.md)
    - решить: КП / простой follow-up / проигнорировать

ШАГ 6 (опционально, по подтверждению пользователя)
  → /presale-kp <site>  (если решено КП)
  → /new-client          (если контакт перешёл в подписанного клиента → доступы)
```

## Что НЕ делать

- ❌ Не создавать `presale/kp/<slug>_kp.html` без явного подтверждения «делаем КП»
- ❌ Не угадывать сайт если есть 2+ домена-кандидата
- ❌ Не назначать assignee автоматически (см. `asana-required-fields.md`)
- ❌ Не ставить due_on по интуиции — только если постановщик назвал срок
- ❌ Не пушить медиа-файлы (фото визиток) в основной репо без `git lfs` — складывать в `meetings/media/` с .gitignore-фильтром если репо требует

## Прецедент

**DentalExpo 2026 (21-24.04, Crocus Expo):**
- Создан `clients/dentalexpo/contacts/contacts.yaml` (28.04, через 5 дней после выставки)
- Зафиксированы: Татьяна / Стом-Shop / +7 (911) 096-81-45 + Дмитрий Сапожников / Стомарт
- **Проблема:** контакт пролежал 5 дней между записью в TG (23.04 14:02) и фиксацией в git (28.04). При сегодняшней проверке (03.05) пришлось искать по полям сессии — этого избегает SOP «коммит в день мероприятия».
- **Источник:** session `f18f6668-e144-4164-b567-ba10dad678b2`, lines 373, 420.

## Связь с другими правилами

- `new-client.md` — структура папок и шаблоны access.md / config.yaml / README.md
- `asana-required-fields.md` — ЗАПРЕТ автоназначения assignee и угадывания due_on
- `recipient-personalization.md` — 3 тезиса под роль получателя для будущего КП
- `quality.md` — фактчек юрлица через 2+ источника (rusprofile + checko)
- `core.md` (no-smoothing) — поля без данных = `?` явно, не «вероятно»
- `artvision-data/.claude/rules/clients-registry.md` — реестр клиентов, обновлять при создании слота
