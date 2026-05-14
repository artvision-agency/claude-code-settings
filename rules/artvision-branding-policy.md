# Брендирование документов — обязательное лого + кнопка чата

> **Установлено:** 2026-05-13 на сессии DENTIX (85419c66) после правки Антона по dentix-FINAL.
> **Применять:** ко ВСЕМ клиентским и внутренним HTML/PDF-документам Артвижн (планы, аудиты, КП, отчёты, презентации).
> **Связано:** `kp-brand.md` (запрет чужих сервисов), `feedback_no_internal_markers_in_client_docs.md`.

## Когда добавлять лого + кнопку чата

✅ **ОБЯЗАТЕЛЬНО** в:
- КП клиентам (presale)
- Планы работ (M1/M2/M6)
- SEO-аудиты
- Отчёты (месячные, квартальные)
- Деплои на artvision.pro/preview/, artvision.pro/kp/
- Внутренние документы по клиентам (даже если для Антона)

❌ **НЕ ДОБАВЛЯТЬ** в документах для **партнёров-агентств**:
- Роман / ДвериГранит / roman-mebel (через посредника)
- Адвертмед-партнёры (Варикоз / Радуга / Стом-Эксперт / s32 / Lumiere — это субподряд через AdvertMed)
- Любые **white-label** (мы делаем для другого агентства, оно ставит свой бренд)

Принцип: документы где **конечный заказчик — наш прямой клиент** → лого Artvision. Документы где **посредник-агентство** → без лого (или с лого партнёра).

## Что добавлять

### 1. Sticky brand bar (вверху страницы)

```html
<div class="av-brand-bar">
  <img src="_assets/logo-artvision.png" alt="Artvision">
  <div class="av-brand-name">Artvision · <a href="https://artvision.pro/" target="_blank">artvision.pro</a></div>
  <div class="av-brand-spacer"></div>
  <div class="av-brand-doc">[Название клиента + тип документа + дата]</div>
</div>
```

CSS:
```css
.av-brand-bar {
    display: flex; align-items: center; gap: 14px;
    padding: 10px 24px; background: #fff;
    border-bottom: 1px solid var(--al-border);
    position: sticky; top: 0; z-index: 100;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.av-brand-bar img { height: 32px; width: auto; }
```

### 2. Sticky кнопка «Задать вопрос» (правый нижний угол)

```html
<a class="av-ask-button" href="https://t.me/AntonKamer" target="_blank" rel="noopener">Задать вопрос</a>
```

CSS:
```css
.av-ask-button {
    position: fixed; bottom: 24px; right: 24px;
    display: inline-flex; align-items: center; gap: 8px;
    background: var(--al-gold); color: #fff;
    padding: 12px 18px; border-radius: 28px;
    font-size: 14px; font-weight: 600;
    box-shadow: 0 4px 16px rgba(5,152,86,0.4);
    text-decoration: none; z-index: 1000;
}
.av-ask-button::before { content: "💬"; font-size: 18px; }
```

URL чата:
- **По умолчанию:** `https://t.me/AntonKamer` (личка Антона)
- **Для презейл-КП:** можно указать `mailto:anton@artvision.pro`
- **Для дашбордов / отчётов клиентов:** TG-бот `@avportal_bot` (если будет публичный endpoint)

### 3. Подвал-блок с реквизитами Artvision

```html
<div class="av-footer">
  <img src="_assets/logo-artvision.png" alt="Artvision">
  <div class="av-footer-text">
    <strong>Артвижн</strong> — SEO и интернет-маркетинг.<br>
    [Дополнительный контекст документа]
  </div>
  <div class="av-footer-links">
    <a href="https://artvision.pro/">artvision.pro</a>
    <a href="https://t.me/AntonKamer">Telegram</a>
    <a href="mailto:anton@artvision.pro">anton@artvision.pro</a>
  </div>
</div>
```

## Файлы лого

| Файл | Где | Когда использовать |
|---|---|---|
| `logo_artvision_dark.png` (199×130) | `personal/social_clips/2026-05-12-research-video/brand/` | **По умолчанию** для светлого фона документов |
| `logo_artvision_purple_220.png` (220×N, #614CE1) | то же | Для покрашенных под бренд видео-обложек |
| `logo_artvision_white_220.png` (220×N) | то же | Для outro темного фона видео |
| `logo_artvision_220.png` | то же | Универсальный |

**Стандартный путь в client-папках:** `clients/<name>/<doc-folder>/_assets/logo-artvision.png`

**Стандартный URL deploy:** `https://artvision.pro/preview/<client>/<doc>/_assets/logo-artvision.png`

## Шаблон применения (пример)

```html
<!DOCTYPE html>
<html>
<head>
  <link rel="stylesheet" href="dentix-style.css">
  <style>
    /* брендирование CSS — копировать из av-brand-bar / av-ask-button / av-footer выше */
  </style>
</head>
<body>
  <!-- 1. Sticky brand bar -->
  <div class="av-brand-bar">
    <img src="_assets/logo-artvision.png" alt="Artvision">
    <div class="av-brand-name">Artvision · <a href="https://artvision.pro/">artvision.pro</a></div>
    <div class="av-brand-spacer"></div>
    <div class="av-brand-doc">[Клиент] · [тип] · [дата]</div>
  </div>

  <!-- Контент документа -->
  <div class="kp-document">
    ...

    <!-- 3. Подвал перед закрытием kp-document -->
    <div class="av-footer">
      <img src="_assets/logo-artvision.png" alt="Artvision">
      <div class="av-footer-text">...</div>
      <div class="av-footer-links">...</div>
    </div>
  </div>

  <!-- 2. Sticky кнопка чата -->
  <a class="av-ask-button" href="https://t.me/AntonKamer" target="_blank">Задать вопрос</a>
</body>
</html>
```

## Прецеденты

- **2026-05-13 — DENTIX-FINAL:** Антон попросил добавить лого и кнопку чата → правило установлено как глобальное для всех документов. Применено к `dentix-FINAL-2026-05-13.html`.
- **AdvertMed Wave 2 КП 04-05.05.2026** — это subcontract, лого НЕ ставится (партнёрский pipeline).
- **Roman-Mebel КП** — через ДвериГранит, посредник → без лого Artvision (он клиент ДвериГранита, не наш).

## Антипаттерны

- ❌ Документ для прямого клиента БЕЗ лого Artvision
- ❌ Документ для AdvertMed-партнёра С лого Artvision (нарушение партнёрского соглашения)
- ❌ Сторонние логотипы партнёров/конкурентов в шапке (только Artvision)
- ❌ Ссылки на чужие сервисы в подвале (только artvision.pro / TG / email)

## Маршрут проверки

При создании любого нового HTML/PDF-документа клиента — проверять чеклист:
- [ ] Лого Artvision в sticky шапке
- [ ] Кнопка «Задать вопрос» (TG/mailto) sticky внизу справа
- [ ] Подвал с реквизитами Artvision
- [ ] last-modified timestamp в шапке (для версионирования)
- [ ] Список версий документа (для возврата к предыдущей)
- [ ] Если документ для партнёра-агентства — ОТМЕНИТЬ всё выше, добавить пометку «партнёрский / white-label»
