---
name: cro
description: "Единый скилл оптимизации конверсии: страницы, формы, попапы, регистрация, онбординг, paywall. Триггеры: 'cro', 'конверсия', 'не конвертит', 'conversion rate', 'optimize page', 'page cro', 'popup', 'модальное окно', 'exit intent', 'форма не работает', 'form optimization', 'lead form', 'форма', 'signup flow', 'регистрация', 'signup conversions', 'onboarding', 'активация', 'activation rate', 'first-run', 'paywall', 'upgrade screen', 'upsell', 'freemium conversion', 'конверсия страницы', 'улучшить конверсию', 'почему не конвертит', 'оптимизация формы', 'попап', 'баннер'."
---

# CRO — Conversion Rate Optimization

Единый скилл оптимизации конверсии. Определи секцию по объекту оптимизации:

| Что оптимизируем | Секция |
|-----------------|--------|
| Страница (homepage, landing, pricing, feature) | §1 Страница |
| Форма (lead capture, контакт, демо, чекаут) | §2 Форма |
| Попап/модальное окно/баннер | §3 Попап |
| Регистрация/signup/trial | §4 Регистрация |
| Онбординг/активация/first-run | §5 Онбординг |
| In-app paywall/upgrade/upsell | §6 Paywall |

---

## §1 Страница (Page CRO)

### Initial Assessment
1. **Тип страницы**: Homepage / Landing / Pricing / Feature / Blog
2. **Цель конверсии**: Signup / Demo / Purchase / Subscribe / Download
3. **Источник трафика**: Organic / Paid / Social / Email / Direct

### 7 измерений анализа (по приоритету)

**1. Value Proposition Clarity** (высший приоритет)
- 5-секундный тест: понятно что это и зачем?
- Бенефит-ориентация vs фича-ориентация
- Язык клиента vs жаргон компании

**2. Headline Effectiveness**
- Передаёт core value proposition?
- Конкретика vs абстракция
- Соответствие источнику трафика (ad → landing match)

**3. CTA — placement, copy, hierarchy**
- Один чёткий primary CTA above the fold
- Copy = ценность, не действие ("Start Free Trial" > "Submit")
- Повтор CTA после каждого блока доказательств

**4. Visual Hierarchy & Scannability**
- Сканируя — получишь главное?
- Достаточно whitespace, нет стен текста
- Изображения поддерживают, а не отвлекают

**5. Trust & Social Proof**
- Логотипы, тестимониалы с фото, кейсы с цифрами
- Рядом с CTA (уменьшить трение в момент решения)

**6. Objection Handling**
- FAQ, гарантии, сравнения, прозрачность процесса
- Цена/ценность, "подойдёт ли мне", сложность, время до результата

**7. Friction Points**
- Лишние поля, непонятные шаги, медленная загрузка
- Мобильный опыт

### Формат рекомендаций
- **Quick Wins** — лёгкие, немедленный эффект
- **High-Impact** — серьёзные изменения, значительный рост
- **Test Ideas** — гипотезы для A/B тестирования
- **Copy Alternatives** — 2-3 варианта ключевых элементов

---

## §2 Форма (Form CRO)

### Core Principles
1. **Каждое поле = стоимость**: 3 поля baseline, 7+ полей → -25-50% completion
2. **Ценность > усилия**: что получат — очевидно
3. **Снижение когнитивной нагрузки**: один вопрос на поле, логический порядок

### Оптимизация полей
- **Email**: inline валидация, typo detection, без подтверждения
- **Имя**: одно поле "Name" vs First/Last — тестировать
- **Телефон**: optional если можно, объяснить зачем если required
- **Компания**: auto-suggest, обогащение после отправки
- **Dropdowns**: searchable если >5 опций, radio если <5

### Layout
- Single column > multi-column (кроме First/Last name)
- Labels всегда видимы (не placeholders)
- Порядок: лёгкие → сложные → чувствительные

### Multi-Step Forms (>5 полей)
- Progress indicator, one topic per step
- Начать с low-friction (email), постепенно усложнять
- Save progress, allow back navigation

### Submit Button
- Weak: "Submit" → Strong: "Get My Free Quote"
- Достаточный размер, контраст, сразу после последнего поля

### Trust Near Form
- "Мы не будем спамить, отписка в 1 клик"
- "Занимает 30 секунд"
- Тестимониал рядом с формой

---

## §3 Попап (Popup CRO)

### Core Principles
1. **Тайминг решает всё**: рано = раздражение, поздно = упущено
2. **Ценность очевидна**: стоит прерывания
3. **Уважение к пользователю**: легко закрыть, не ловушка

### Типы попапов

| Тип | Триггер | Цель |
|-----|---------|------|
| Exit intent | Курсор к X | Удержание, скидка |
| Scroll-based | 50-70% страницы | Lead capture |
| Time-based | 15-30 сек | Промо, подписка |
| Click-triggered | CTA клик | Детали, форма |
| Slide-in | Scroll | Мягкое предложение |

### Best Practices
- **Одно предложение на попап** — не каталог
- **Частота**: max 1 попап/визит, не показывать закрывшим 7-14 дней
- **Mobile**: full-screen осторожно (Google penalty), slide-in предпочтительнее
- **Копирайтинг**: заголовок = ценность, подзаголовок = как, CTA ≠ "Submit"
- **Визуал**: минимум полей (1-2), контрастный CTA, лёгкое закрытие

### Тактики по цели
- **Email capture**: "Получи [ценность] бесплатно" + 1 поле email
- **Exit intent**: "Подождите! Скидка 10% на первый заказ"
- **Announcement**: тонкий бар сверху, авто-скрытие через 10 сек

---

## §4 Регистрация (Signup Flow CRO)

### Принципы
1. Минимальное трение до "aha moment"
2. Social login если целевая аудитория использует
3. Progressive profiling — запрашивать данные позже
4. Clear value reminder на каждом шаге

### Оптимизация шагов
- **Шаг 1**: Email only (или social login)
- **Шаг 2**: Имя + пароль (или magic link)
- **Шаг 3**: Onboarding questions (опционально)

### Ключевые метрики
- Start rate (visit → begin signup)
- Step completion rate (per step)
- Overall completion rate
- Time to complete
- Error rate by field

### Best Practices
- Password: показать/скрыть, strength meter, min 8 chars
- Email verification: не блокировать вход, напоминать позже
- Error recovery: сохранять введённое, показывать inline
- A/B test: email+password vs social login vs magic link

---

## §5 Онбординг (Onboarding CRO)

### Цель: Time to Value → минимум

**Aha Moment** — момент когда пользователь понимает ценность продукта.
Вся задача онбординга: довести до этого момента как можно быстрее.

### Паттерны онбординга

| Паттерн | Когда | Пример |
|---------|-------|--------|
| Checklist | 3-7 шагов до активации | "Настройте за 5 минут" |
| Tour | Сложный UI | Пошаговые подсказки |
| Template | Пустой экран страшен | Стартовые данные |
| Video | Визуальный продукт | 60-сек обзор |
| Progressive | Много фич | Разблокировка по мере использования |

### Empty State → Action
- Пустой дашборд = dropout. Показать: что сделать первым, пример результата, шаблон.
- **Quick win**: дать пользователю успех за <2 минуты

### Метрики
- Activation rate (signup → aha moment)
- Time to first value
- Feature adoption rate
- Day 1/7/30 retention
- Checklist completion rate

---

## §6 Paywall / Upgrade (In-App CRO)

### Принцип: показать paywall когда пользователь уже получил ценность

### Типы paywall triggers

| Триггер | Пример | Эффективность |
|---------|--------|--------------|
| Usage limit | "Использовано 3/3 бесплатных" | Высокая |
| Feature gate | "Pro функция — перейдите на план" | Средняя |
| Time limit | "Осталось 3 дня триала" | Высокая |
| Value moment | После успешного действия | Высокая |

### Copy Framework
1. **Acknowledge value**: "Вы уже [достижение]"
2. **Show limitation**: "Бесплатный лимит исчерпан"
3. **Bridge to upgrade**: "С Pro вы сможете [результат]"
4. **Reduce risk**: "Отмена в 1 клик, 14 дней возврат"

### Антипаттерны
- ❌ Paywall до демонстрации ценности
- ❌ Агрессивные попапы каждые 5 минут
- ❌ Скрытые условия, мелкий шрифт
- ❌ Блокировка текущей работы без предупреждения

---

## Questions (для любой секции)

1. Текущий conversion rate и цель?
2. Источники трафика?
3. Есть ли аналитика (heatmaps, session recordings, field-level)?
4. Мобайл vs десктоп сплит?
5. Что уже пробовали?

## Related Skills
- **ab-test-setup** — тестирование рекомендаций
- **copywriting** — полная переписка страницы (EN)
- **content-writer** — русскоязычный контент
- **analytics-tracking** — настройка отслеживания
