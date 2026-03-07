# ANT Partners — Section Patterns (extracted from wave1)

## Правила чередования
Секции СТРОГО чередуются:
```
.section           (белый фон)
.section.section-alt  (серый фон #f5f5f5)
.section           (белый фон)
.section.section-alt  (серый фон)
...
```

Каждая секция ОБЯЗАТЕЛЬНО содержит `<h2 class="h2-title">Заголовок</h2>` первым элементом.

---

## 1. Stats (первая секция, без id)
```html
<section class="section">
<h2 class="h2-title">{{STATS_TITLE}}</h2>
<div class="stats">
  <div class="stat">
    <div class="stat-num">{{NUM_1}}</div>
    <div class="stat-text">{{TEXT_1}}</div>
  </div>
  <div class="stat">
    <div class="stat-num">{{NUM_2}}</div>
    <div class="stat-text">{{TEXT_2}}</div>
  </div>
  <div class="stat">
    <div class="stat-num">{{NUM_3}}</div>
    <div class="stat-text">{{TEXT_3}}</div>
  </div>
  <div class="stat">
    <div class="stat-num">{{NUM_4}}</div>
    <div class="stat-text">{{TEXT_4}}</div>
  </div>
</div>
</section>
```

---

## 2. Text section (простой текст + опционально figure)
```html
<section class="section section-alt" id="sec-{{ID}}">
<h2 class="h2-title">{{TITLE}}</h2>
<p>{{PARAGRAPH_1}}</p>
<p>{{PARAGRAPH_2}}</p>
<!-- Опционально: -->
<figure class="full-img">
  <img alt="{{ALT}}" src="images/{{SLUG}}/{{IMG}}"/>
  <figcaption>{{CAPTION}}</figcaption>
</figure>
</section>
```

---

## 3. Features Grid (карточки с описанием)
```html
<section class="section" id="sec-{{ID}}">
<h2 class="h2-title">{{TITLE}}</h2>
<p>{{INTRO_TEXT}}</p>
<div class="features-grid">
  <div class="feature-card">
    <strong>1. {{FEATURE_TITLE}}</strong>
    <p>{{FEATURE_DESC}}</p>
  </div>
  <div class="feature-card">
    <strong>2. {{FEATURE_TITLE}}</strong>
    <p>{{FEATURE_DESC}}</p>
  </div>
  <!-- 3-6 карточек -->
</div>
<!-- Опционально: figure + quote-block -->
<figure class="full-img">
  <img alt="{{ALT}}" src="images/{{SLUG}}/{{IMG}}"/>
  <figcaption>{{CAPTION}}</figcaption>
</figure>
<div class="quote-block">
  <p><strong>{{QUOTE_TEXT}}</strong></p>
</div>
</section>
```

---

## 4. Timeline (пронумерованные шаги)
```html
<section class="section" id="sec-{{ID}}">
<h2 class="h2-title">{{TITLE}}</h2>
<p>{{INTRO_TEXT}}</p>
<div class="timeline">
  <div class="timeline-item">
    <div class="timeline-num">1</div>
    <div class="timeline-content">
      <h4>{{STEP_TITLE}}</h4>
      <p>{{STEP_DESC}}</p>
      <!-- Опционально: ul с деталями -->
      <ul style="margin: 10px 0 0; padding-left: 20px; font-size: 14px; color: #666;">
        <li>{{DETAIL_1}}</li>
        <li>{{DETAIL_2}}</li>
      </ul>
    </div>
  </div>
  <!-- 3-5 шагов -->
</div>
</section>
```

Вариант без timeline-content wrapper (для коротких шагов):
```html
<div class="timeline-item">
  <div class="timeline-num">01</div>
  <h4>{{STEP_TITLE}}</h4>
  <p>{{STEP_DESC}}</p>
</div>
```

---

## 5. Cases Grid (кейсы/примеры)
```html
<section class="section section-alt" id="sec-{{ID}}">
<h2 class="h2-title">{{TITLE}}</h2>
<p>{{INTRO_TEXT}}</p>
<h3 class="h3-title" style="margin-top: 40px;">{{SUBTITLE}}</h3>
<div class="cases-grid">
  <div class="case-card">
    <div class="case-card-header">
      <div class="label">{{LABEL}}</div>
      <h4>{{CASE_TITLE}}</h4>
    </div>
    <div class="case-card-body">
      <p><strong>Ситуация:</strong> {{SITUATION}}</p>
      <p><strong>Наши действия:</strong> {{ACTIONS}}</p>
      <p><strong>Результат:</strong> {{RESULT}}</p>
    </div>
  </div>
  <!-- 2-3 case-card, каждый следующий header может менять background: -->
  <!-- style="background: #2d5a7a;" или style="background: #1a3a5c;" -->
</div>
</section>
```

---

## 6. Advantages (преимущества с SVG иконками)
```html
<section class="section section-alt" id="sec-{{ID}}">
<h2 class="h2-title">{{TITLE}}</h2>
<div class="advantages">
  <div class="advantage-item">
    <div class="advantage-icon">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="{{SVG_PATH}}"></path>
      </svg>
    </div>
    <div class="advantage-text">
      <h4>{{ADV_TITLE}}</h4>
      <p>{{ADV_DESC}}</p>
    </div>
  </div>
  <!-- 3-4 advantage-item -->
</div>
</section>
```

**КРИТИЧНО:** SVG ОБЯЗАТЕЛЬНО имеет `width="24" height="24" fill="none" stroke="currentColor" stroke-width="2"`. Без этого иконки растянутся до 730px!

---

## 7. Services Grid (карточки услуг)
```html
<section class="section" id="sec-{{ID}}">
<h2 class="h2-title">{{TITLE}}</h2>
<div class="services-grid">
  <div class="service-card">
    <div class="service-card-header">
      <h4>{{SERVICE_TITLE}}</h4>
      <span class="service-card-price">Цена: {{PRICE}}</span>
    </div>
    <ul>
      <li>{{ITEM_1}}</li>
      <li>{{ITEM_2}}</li>
      <li>{{ITEM_3}}</li>
      <li>{{ITEM_4}}</li>
    </ul>
  </div>
  <!-- 3-4 service-card -->
</div>
</section>
```

---

## 8. Price Table
```html
<section class="section section-alt" id="sec-{{ID}}">
<h2 class="h2-title">{{TITLE}}</h2>
<table class="price-table">
<thead>
  <tr><th>Услуга</th><th>Стоимость</th></tr>
</thead>
<tbody>
  <tr>
    <td>{{SERVICE_NAME}}</td>
    <td>
      <div class="price-cell-content">
        <a class="price-tg-btn" href="https://t.me/dvaA_bussines_law" target="_blank" rel="noopener noreferrer">
          <svg viewBox="0 0 24 24"><path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.894 8.221l-1.97 9.28c-.145.658-.537.818-1.084.508l-3-2.21-1.446 1.394c-.14.18-.357.295-.6.295l.213-3.053 5.56-5.023c.242-.213-.054-.334-.373-.121l-6.869 4.326-2.96-.924c-.64-.203-.654-.64.135-.954l11.566-4.458c.538-.196 1.006.128.828.94z"></path></svg>
          Уточнить
        </a>
        <span class="price-value">{{PRICE}}</span>
      </div>
    </td>
  </tr>
  <!-- Повторить для каждой услуги -->
</tbody>
</table>
</section>
```

---

## 9. FAQ (аккордеон)
```html
<section class="section section-alt" id="sec-faq">
<h2 class="h2-title">Часто задаваемые вопросы</h2>
<div class="faq">
  <div class="faq-item">
    <div class="faq-q" role="button" tabindex="0" aria-expanded="false">{{QUESTION}}</div>
    <div class="faq-a"><p>{{ANSWER}}</p></div>
  </div>
  <!-- 5-8 faq-item -->
</div>
</section>
```

---

## 10. Form Section (перед footer)
```html
<section class="section-form">
<h2 class="h2-title">{{FORM_TITLE}}</h2>
<div class="text">
  <p>{{FORM_SUBTITLE}}</p>
</div>
<form action="#" method="post" onsubmit="return false;">
  <div class="form-row">
    <div class="form-inputs">
      <input type="text" name="name" class="form-input" placeholder="Ваше имя:" aria-label="Ваше имя"/>
      <input type="tel" name="phone" class="form-input" placeholder="Телефон:" required aria-required="true" aria-label="Телефон"/>
      <input type="email" name="email" class="form-input" placeholder="Email:" aria-label="Email"/>
    </div>
    <div>
      <button type="submit" class="btn-main">
        Оставить заявку
        <svg viewBox="0 0 50 12" fill="none"><path d="M0 6H48M48 6L42 1M48 6L42 11" stroke="currentColor" stroke-width="1.5"></path></svg>
      </button>
    </div>
  </div>
</form>
</section>
```

---

## Типичный порядок секций на странице

1. **Stats** (без id) — 4 числа
2. **Text** (sec-about) — вводный текст
3. **Features Grid** (sec-signs/sec-types) — карточки
4. **Text + figure** (sec-consequences) — текст с картинкой
5. **Timeline** (sec-how) — этапы работы
6. **Cases Grid** (sec-results) — кейсы
7. **Timeline short** (sec-consult) — как получить консультацию
8. **Advantages** (sec-advantages) — преимущества с SVG
9. **Services Grid** (sec-services) — карточки услуг
10. **Price Table** (sec-price) — таблица цен
11. **Timeline** (sec-process) — как мы работаем
12. **FAQ** (sec-faq) — вопросы-ответы
13. **Form** — форма заявки (section-form)

Не все секции обязательны. Минимум: stats + 3 контентных + advantages + services/price + FAQ + form.
