---
name: telegram-mini-app
description: Use when building or modifying Telegram Mini Apps — SDK integration, theming, component patterns, viewport handling. Use when touching webapp/static/*.html or building Mini App UI.
---

# Telegram Mini App Patterns

## Overview

Паттерны для Telegram Mini App (TMA) — правильное использование SDK, CSS-тем, компонентный подход без фреймворков.

## SDK Integration

```html
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<script>
const tg = window.Telegram.WebApp;
tg.ready();           // Сообщить TG что приложение загружено
tg.expand();          // Развернуть на весь экран
tg.enableClosingConfirmation(); // Подтверждение при закрытии
</script>
```

### Основные API

```javascript
// Данные пользователя
tg.initDataUnsafe.user   // {id, first_name, username, language_code}
tg.initData              // Подписанная строка для backend-верификации

// Кнопки
tg.MainButton.setText("Сохранить").show().onClick(handler);
tg.BackButton.show().onClick(handler);

// Haptic feedback
tg.HapticFeedback.impactOccurred("medium");  // light/medium/heavy
tg.HapticFeedback.notificationOccurred("success"); // success/error/warning

// Закрытие
tg.close();
```

## CSS Theming

ВСЕГДА использовать CSS-переменные Telegram — адаптируются к теме пользователя:

```css
:root {
    /* Основные — ОБЯЗАТЕЛЬНО использовать */
    --tg-theme-bg-color: var(--tg-bg, #fff);
    --tg-theme-text-color: var(--tg-text, #000);
    --tg-theme-hint-color: var(--tg-hint, #999);
    --tg-theme-link-color: var(--tg-link, #2481cc);
    --tg-theme-button-color: var(--tg-button, #2481cc);
    --tg-theme-button-text-color: var(--tg-button-text, #fff);
    --tg-theme-secondary-bg-color: var(--tg-secondary-bg, #f0f0f0);
}

body {
    background: var(--tg-theme-bg-color);
    color: var(--tg-theme-text-color);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    margin: 0;
    padding: 0;
    -webkit-text-size-adjust: 100%;
}
```

**Запрещено:**
- Хардкод цветов (`#fff`, `#000`, `rgb(...)`) — используй tg-переменные
- `background: white` — сломает тёмную тему

## Component Pattern (без фреймворков)

Вместо string concat (`html += '<div>...'`) — компонентные функции с template literals:

```javascript
// ❌ ПЛОХО — string concat
var html = "";
html += '<div class="card">';
html += '<span>' + escapeHtml(name) + '</span>';
html += '</div>';
container.innerHTML = html;

// ✅ ХОРОШО — компонентная функция
function UserCard(user) {
    return `
        <div class="card">
            <span>${esc(user.name)}</span>
            <span class="hint">${esc(user.city)}</span>
        </div>
    `;
}
container.innerHTML = users.map(UserCard).join("");
```

### Структура компонентов

```javascript
// Утилиты
function esc(str) {
    const d = document.createElement("div");
    d.textContent = str;
    return d.innerHTML;
}

function formatDate(iso) {
    if (!iso) return "";
    const d = new Date(iso + "Z");
    return d.toLocaleDateString("ru", {day:"2-digit", month:"2-digit"})
         + " " + d.toLocaleTimeString("ru", {hour:"2-digit", minute:"2-digit"});
}

// Атомарные компоненты
function Badge(text, type) {
    return `<span class="badge badge-${type}">${esc(text)}</span>`;
}

function ProgressBar({value, max, color}) {
    const pct = max > 0 ? Math.round(value / max * 100) : 0;
    return `
        <div class="bar-bg">
            <div class="bar-fill" style="width:${Math.max(pct, 4)}%;background:${color || 'var(--tg-theme-button-color)'}"></div>
        </div>
    `;
}

// Составные компоненты
function FunnelStep({label, value, total, color}) {
    const pct = total > 0 ? Math.round(value / total * 100) : 0;
    return `
        <div class="funnel-step">
            <div class="funnel-header">
                <span>${esc(label)}</span>
                <span class="hint">${value} (${pct}%)</span>
            </div>
            ${ProgressBar({value, max: total, color})}
        </div>
    `;
}

// Страница / секция
function FunnelSection(funnel) {
    const steps = [
        {label: "Зарегались", value: funnel.total, total: funnel.total},
        {label: "Настроили фильтр", value: funnel.with_filter, total: funnel.total},
    ];
    return `
        <h3>Воронка</h3>
        ${steps.map(FunnelStep).join("")}
    `;
}
```

### Рендеринг с пагинацией

```javascript
function PaginatedList({items, page, perPage, renderItem, container}) {
    const totalPages = Math.ceil(items.length / perPage);
    const start = page * perPage;
    const pageItems = items.slice(start, start + perPage);

    container.innerHTML = `
        ${pageItems.map(renderItem).join("")}
        ${totalPages > 1 ? Pagination(page, totalPages) : ""}
    `;

    // Bind pagination buttons
    const prev = container.querySelector("[data-page-prev]");
    const next = container.querySelector("[data-page-next]");
    if (prev) prev.onclick = () => PaginatedList({...arguments[0], page: page - 1});
    if (next) next.onclick = () => PaginatedList({...arguments[0], page: page + 1});
}

function Pagination(page, totalPages) {
    return `
        <div class="pagination">
            ${page > 0 ? '<button data-page-prev class="btn-outline">← Назад</button>' : ''}
            <span class="hint">${page + 1} / ${totalPages}</span>
            ${page < totalPages - 1 ? '<button data-page-next class="btn-outline">Далее →</button>' : ''}
        </div>
    `;
}
```

## Tab Pattern

```javascript
// HTML
`<div class="tabs">
    ${tabs.map(t => `<div class="tab ${t.active ? 'active' : ''}" data-tab="${t.id}">${t.label}</div>`).join("")}
</div>
${tabs.map(t => `<div id="tab-${t.id}" class="tab-content ${t.active ? 'active' : ''}"></div>`).join("")}`

// JS — lazy loading
const loaded = {};
document.querySelectorAll(".tab").forEach(tab => {
    tab.addEventListener("click", () => {
        const id = tab.dataset.tab;
        // Toggle active
        document.querySelectorAll(".tab").forEach(t => t.classList.toggle("active", t === tab));
        document.querySelectorAll(".tab-content").forEach(c => c.classList.toggle("active", c.id === "tab-" + id));
        // Lazy load
        if (!loaded[id] && loaders[id]) {
            loaded[id] = true;
            loaders[id]();
        }
    });
});
```

## CSS Base Classes

```css
/* Layout */
.container { padding: 12px; max-width: 480px; margin: 0 auto; }
.tabs { display: flex; overflow-x: auto; gap: 4px; padding: 8px 12px; }
.tab { padding: 6px 12px; border-radius: 16px; font-size: 13px; white-space: nowrap; cursor: pointer;
       background: var(--tg-theme-secondary-bg-color); color: var(--tg-theme-hint-color); }
.tab.active { background: var(--tg-theme-button-color); color: var(--tg-theme-button-text-color); }
.tab-content { display: none; padding: 12px; }
.tab-content.active { display: block; }

/* Cards */
.card { padding: 10px 0; border-bottom: 1px solid var(--tg-theme-secondary-bg-color); }
.card-row { display: flex; justify-content: space-between; align-items: center; }
.card-title { font-weight: 600; font-size: 14px; }

/* Typography */
.hint { color: var(--tg-theme-hint-color); font-size: 12px; }
.section-title { font-size: 14px; font-weight: 600; margin-bottom: 10px; color: var(--tg-theme-hint-color); }

/* Badges */
.badge { padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: 600; }
.badge-active { background: #e8f5e9; color: #2e7d32; }
.badge-inactive { background: #fce4ec; color: #c62828; }

/* Bars */
.bar-bg { background: var(--tg-theme-secondary-bg-color); border-radius: 4px; height: 8px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 4px; transition: width 0.3s; }

/* Buttons */
.btn-outline { padding: 6px 14px; border: 1px solid var(--tg-theme-button-color); border-radius: 6px;
               background: transparent; color: var(--tg-theme-button-color); cursor: pointer; font-size: 13px; }

/* Pagination */
.pagination { display: flex; justify-content: center; align-items: center; gap: 12px; padding: 12px 0; }

/* Loading */
.spinner { width: 24px; height: 24px; border: 3px solid var(--tg-theme-secondary-bg-color);
           border-top-color: var(--tg-theme-button-color); border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.loader { text-align: center; padding: 20px; }
```

## Viewport & Safe Area

```css
/* iOS safe area */
body { padding-top: env(safe-area-inset-top); padding-bottom: env(safe-area-inset-bottom); }

/* Prevent overscroll bounce */
html { overscroll-behavior: none; overflow: hidden; height: 100%; }
body { overflow-y: auto; height: 100%; -webkit-overflow-scrolling: touch; }
```

## Backend Auth

```python
# Верификация initData на backend (aiohttp)
import hmac, hashlib

def verify_init_data(init_data: str, bot_token: str) -> bool:
    data_dict = dict(pair.split("=", 1) for pair in init_data.split("&"))
    received_hash = data_dict.pop("hash", "")
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data_dict.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed_hash, received_hash)
```

## Common Mistakes

| Ошибка | Исправление |
|--------|-------------|
| `html += '<div>' + var + '</div>'` | Template literal: `` `<div>${esc(var)}</div>` `` |
| Хардкод цветов | `var(--tg-theme-*)` |
| Не вызвал `tg.ready()` | Всегда первым делом |
| XSS через innerHTML | Всегда escape пользовательских данных |
| Один большой рендер | Компонентные функции |
| Весь JS inline | Разделить на components / loaders / utils |
