---
name: advertmed-brand
description: >-
  Бренд-стиль Advertmed (Варикознет) для HTML-документов, КП, инструкций, страниц.
  Автоматически применяет цветовую палитру, градиенты, типографику клиента.
  Триггеры: advertmed, варикознет, varikozanet, адвертмед.
  Use when creating or styling any document for Advertmed / Varikozanet client.
user-invocable: true
allowed-tools: Read Write Edit Bash(scp *)
metadata:
  author: artvision
  version: "1.0"
  category: client-branding
  client: advertmed
---

# Advertmed Brand Style

Применяй этот стиль при создании ЛЮБОГО документа для клиента **Advertmed / Варикознет**.

## Клиент

| Поле | Значение |
|------|----------|
| Агентство | Advertmed (advertmed.com) — рекламное агентство, наш партнёр |
| Заказчик | Варикознет (varikozanet.pro) — клиника, клиент Advertmed |
| Сайт агентства | advertmed.com |
| Сайт заказчика | varikozanet.pro |
| Папка | `clients/advertmed-varikozanet/` |

## CSS-переменные (обязательные)

```css
:root {
  --p: #3d6098;    /* Primary — основной синий */
  --h: #1e293b;    /* Headings — тёмно-графитовый */
  --t: #475569;    /* Text — серый для текста */
  --t1: #5b7ba5;   /* Text accent — светло-синий */
  --t3: #1e3a5f;   /* Text dark — тёмно-синий */
  --b: #e2e8f0;    /* Border — светло-серый */
  --l: #f8fafc;    /* Light bg — почти белый */
  --r: #b91c1c;    /* Red — акцент ошибок */
  --gold: #8b7355; /* Gold — премиальный акцент */
}
```

## Градиент шапки

```css
.header {
  background: linear-gradient(135deg, #111827 0%, #1e293b 50%, #1e3a5f 100%);
  color: #fff;
  padding: 48px 24px;
  text-align: center;
}
```

## Типографика

- **Шрифт:** системный стек — `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`
- **H1:** 28px, font-weight 700, color #fff (в шапке)
- **H2:** 20px, font-weight 700, color var(--h)
- **Body:** 15-16px, line-height 1.6, color var(--h)
- **Small:** 12-13px, color var(--t)

## Шапка документа

Всегда включать подзаголовок клиента:
```html
<div class="header">
  <p style="font-size:13px;opacity:.6;margin-bottom:4px;letter-spacing:1px;text-transform:uppercase">Advertmed · Варикознет</p>
  <h1>[Заголовок документа]</h1>
  <p>[Подзаголовок]</p>
  <div class="badge">Artvision · [Тип документа] · [Месяц Год]</div>
</div>
```

## UI-элементы

### Карточки
```css
.card {
  background: #fff;
  border-radius: 16px;
  padding: 28px;
  margin-bottom: 20px;
  box-shadow: 0 1px 3px rgba(30, 58, 95, .08);
}
```

### Нумерованные шаги
```css
.num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  background: var(--p);
  color: #fff;
  border-radius: 50%;
  font-size: 13px;
  font-weight: 700;
}
```

### Выделения (highlight)
```css
.highlight { background: #edf2f7; border-left: 4px solid var(--p); }
.highlight.warn { background: #fef3c7; border-left-color: var(--gold); }
.highlight.green { background: #ecfdf5; border-left-color: #059669; }
```

### Кнопки
```css
.copy-btn {
  background: var(--p);
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 6px 14px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}
.copy-btn:hover { background: var(--t3); }
```

## Общий фон страницы

```css
body { background: #edf2f7; }
```

## Обязательные мета-теги

```html
<meta name="robots" content="noindex, nofollow">
```

## Деплой

Документы для Advertmed → `reports.artvision.pro`:
```bash
scp file.html root@80.90.181.152:/var/www/reports/
```
