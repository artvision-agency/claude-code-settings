---
name: design-profile-routing
description: Design Profile Routing — выбор стиля дизайна по клиенту
paths:
  - 'clients/**'
  - 'presales/**'
always: false
size_tokens: 2025
---

# Design Profile Routing — выбор стиля дизайна по клиенту

> **Установлено:** 2026-05-05 после adoption 10 design skills из github.
> **Применять:** при работе с любыми HTML/дизайн-задачами в `clients/<name>/`, КП, лендингах, дашбордах.
> **Связано:** `feedback_no_jargon_for_anton.md` — объяснять термины Антону при первом упоминании.

## 5 профилей дизайна

Каждый клиент относится к одному из 5 профилей. Профиль определяет какой Claude-skill использовать для дизайна страниц/КП/дашбордов клиента.

| Профиль | Когда применять | Primary skill | Secondary skill | НЕ применять (forbidden) |
|---|---|---|---|---|
| **`enterprise`** | Серьёзный B2B, медицина, инженерия, юр.услуги, заводы. Доверие важнее визуальной яркости. WCAG (стандарт доступности для слабовидящих). | `bencium-controlled-ux-designer` | `frontend-design` | `bencium-innovative-ux-designer` |
| **`b2c-polished`** | B2C сервисы (стом, авто, плавание, магазины). Полированный, аккуратный, но не bold (вызывающе-яркий). | `frontend-design` | `brand-guidelines` | — |
| **`lux-marketing`** | Премиум-бренды, lux-маркетплейсы, наши собственные продукты Artvision (Radar/Insight/Funnel). Bold, editorial (журнальный стиль), anti-AI (без штампов AI-картинок). | `bencium-innovative-ux-designer` | `frontend-design` + `svg-animator` | `bencium-controlled-ux-designer` |
| **`dashboard-relationship`** | Долгоживущие интерфейсы клиента (ORM-дашборды, Command Center, аналитика). Long-term retention (повторные визиты), память состояния, доверие к данным. | `relationship-design` | `bencium-controlled-ux-designer` | — |
| **`mvp-prototype`** | Прототипы для созвонов, demo идеи, presale-визуалы «на скорую руку». Высокий fidelity (детализация), MP4 export для отправки в TG/email. | `huashu-design` | `ui-mockup` | — |

## Как определить профиль клиента

### Сигналы для `enterprise`

- Медицина (клиники, стом, лаборатории, фарма)
- Юр.услуги, бухгалтерия, аудит
- B2B-инженерия (бурение, строительство, заводы)
- Госконтракты, тендеры
- ИНН/реквизиты юрлица в каждом видимом месте
- Целевая аудитория: «директор по…», «главврач», «закупщик»

### Сигналы для `b2c-polished`

- Розничный/средний B2C (стом-сервис для частных лиц, авто-запчасти, доставка)
- Есть корзина/каталог/бронирование
- Не премиум (средний чек до 50К)
- Обычная массовая аудитория

### Сигналы для `lux-marketing`

- Премиум-бренды, ювелирка, авто люкс, lux-маркетплейсы
- Тон «эксклюзив», «коллекция», «лимитированная серия»
- Наши продукты Artvision (мы продаём AI-возможности — нужно выглядеть smart, но без AI-картинок)
- Лендинг ради эмоции/wow-эффекта

### Сигналы для `dashboard-relationship`

- Внутренний инструмент клиента (не публичная страница)
- Пользователь возвращается ежедневно/еженедельно
- Отображает данные/метрики/статусы (ORM, аналитика, КРМ)
- Нужны фильтры, состояние, история действий

### Сигналы для `mvp-prototype`

- Прототип для созвона / питча
- Демо идеи до утверждения
- presale-визуал когда КП ещё не финализировано
- «Покажи как это будет выглядеть» — не «сделай продакшен»
- Нужен MP4/GIF для отправки в TG/email

## Запись в config.yaml клиента

В `clients/<name>/config.yaml` добавить блок:

```yaml
# Дизайн-профиль (см. ~/.claude/rules/design-profile-routing.md)
design_profile:
  type: enterprise           # один из 5: enterprise|b2c-polished|lux-marketing|dashboard-relationship|mvp-prototype
  reason: "стоматология, доверие важнее визуальной яркости"
```

Достаточно `type:` — `reason:` опционально для будущего напоминания почему так выбрано.

Hook `pre-client-design-work.sh` читает этот блок и инжектит подсказку Claude перед началом работы:

```
[DESIGN-PROFILE] Клиент anzhee-clinic → enterprise
   Primary skill: /bencium-controlled-ux-designer
   Reason: стоматология, доверие
```

## Если клиент имеет смешанный профиль

Например, BluMart = `b2c-polished` для публичной страницы, но `dashboard-relationship` для ORM Command Center.

Решение — два варианта:

**Вариант 1 (если разделение чёткое по подпапкам):**

```yaml
design_profile:
  default: b2c-polished
  overrides:
    - path: "orm-command-center/**"
      type: dashboard-relationship
      reason: "внутренний дашборд для заказчика"
```

**Вариант 2 (если редкие исключения):**

В config.yaml — `default: b2c-polished`. При работе над дашбордом — Антон явно говорит «используй `/relationship-design`», override через slash-команду.

## Когда НЕ применять профиль

- Технические скрипты (Python, Bash) — дизайна нет, профиль не нужен
- Внутренние markdown-документы (заметки, TODO) — не для клиента, дизайн не важен
- Email команде / в TG — обычный текст, дизайн не нужен

## Default fallback

Если у клиента нет `design_profile` в config.yaml и сложно определить с ходу — **default `b2c-polished`** + `frontend-design`. Самый нейтральный, не «загубит» ни один проект. Антон может уточнить позже.

## Связь с другими правилами

- `kp-brand.md` — фирменный стиль клиента (цвета/шрифты) применяется поверх профиля
- `medical-kp.md` — мед-клиники всегда `enterprise`, мед-аудит обязателен
- `recipient-personalization.md` — tone of voice по роли получателя (3 тезиса под роль)
- `feedback_no_jargon_for_anton.md` — без жаргона при объяснении Антону
- `clients-registry.md` — реестр клиентов с design_profile колонкой

## Прецедент

2026-05-05 — adoption 10 design skills с пересекающимися описаниями. Антон спросил: «как в будущем выбирать эти стили?». Решение — config.yaml + routing rule + hook injection.
