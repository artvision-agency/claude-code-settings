---
name: site-clone
description: Пиксель-клон любого сайта/лендинга проверенным инструментом + замена контента на нашего клиента. Триггеры — 'клонируй сайт', 'склонируй лендинг', 'скопируй дизайн', 'сделай как у <url>', 'clone design', 'копия лендинга конкурента', 'site-clone', 'по референсу <url> с нашим контентом'.
---

# /site-clone — клонирование сайта + content-swap (проверенный пайплайн)

> Обёртка над правилом `~/.claude/rules-conditional/site-clone-pipeline.md`. Рецепт доказан 2026-06-28 (USmile-клон MIA all-on-4, end-to-end).
> Связано: `proven-tools-first`, `medical-facts-verification`, `calculations-need-sources`, `mobile-first-all-html`, `checks-by-validators-multimodel` (ui-visual пост-гейт).

## Когда
Нужна копия дизайна конкурента/референса 1:1 → подставить контент нашего клиента. НЕ текст-спека→frontend-агент (теряет дизайн+картинки).

## Пайплайн (по шагам)

### 1. Пиксель-клон проверенным тулом (НЕ хендролл)
```bash
# single-file-cli (≈14k⭐) — ВАЖНО: на JS-страницах с 1-й попытки падает
# «Execution context not found» → retry + флаг wait (доказано 28.06):
npx --yes single-file-cli --browser-wait-until=networkidle0 --browser-load-max-time=45000 "<URL>" clone.html
# fallback: brew install monolith && monolith "<URL>" -o clone.html
```
Результат — автономный HTML с CSS+шрифтами+картинками base64.

### 2. Strip чужого (python, НЕ sed на больших файлах с кириллицей)
- Счётчики/аналитику: `mc.yandex.ru`/`gtag(`/`ym(`/`fbq(`/`vk.com/rtrg`/`googletagmanager` → заглушить (replace на `void(` / `disabled.local`).
- `<meta name="robots" content="noindex,nofollow">` в `<head>`.

### 3. Content-swap на нашего клиента (читать config.yaml + clinic-facts.yaml клиента)
- Бренд конкурента → наш (везде: текст, `<title>`, og, alt).
- Контакты: телефон/адрес/email/часы → наши — И в `tel:`-href, И в видимый текст, И в формы. Чужой регион/филиалы убрать.
- **ЦИФРЫ (medical/факты) — КРИТИЧНО:** чужие метрики (приживаемость %, кол-во пациентов, гарантия, цены) НЕ присваивать клиенту и НЕ выдумывать. Брать ТОЛЬКО проверенные (с сайта клиента / clinic-facts.yaml `verified_metrics`). Чего нет — видимый плейсхолдер `[уточнить у клиента]`. (medical-facts-verification, calculations-need-sources).

### 4. Аудит остатков ПЕРЕД деплоем (grep)
- Чужие телефоны: `grep -oE '\+?7?\(?[0-9]{3}\)?[ -]?[0-9]{3}[- ][0-9]{2}[- ][0-9]{2}'` → всё не-клиента заменить.
- Чужой бренд/домен источника, чужие счётчики = 0.
- Чужие фото/лица/лого/до-после base64 → заменить на фото клиента (этика+ФЗ-323) ИЛИ пометить TODO (для теста).

### 5. Деплой review-URL + verify
```bash
FACTCHECK_SKIP=1 ~/.claude/scripts/safe-deploy-html.sh clone.html /var/www/artvision/_priv-<name>/index.html
# → HTTP 200, дать live-URL первой строкой
```
### 6. Пост-гейт (для прод-кандидата)
`ui-visual-validator` 375+1440 (mobile-first, ниша мед = 80% mobile) + замена фото + заполнение `[уточнить]` реальными данными → ОК Антона → прод.

## Антипаттерны
- ❌ «Клонируй дизайн» → текст-описание → frontend-агент (generic, без картинок).
- ❌ Клон без проверенного тула (single-file/monolith) — нарушение proven-tools-first.
- ❌ Присвоить клиенту чужие цифры/метрики или выдумать (medical-facts).
- ❌ Оставить чужие телефоны/счётчики/фото в нашем клоне.
- ❌ Деплой на прод без ui-visual + ОК Антона.

## Прецедент
2026-06-28: MIA all-on-4 → клон 1:1 (`artvision.pro/_priv-clone-test-mia/`) → content-swap на USmile (`_priv-usmile-clone-test/`). single-file-cli с retry+wait сработал; цифры USmile только verified (11970 пациентов/54 года/105000₽), остальное `[уточнить]`. Реестр фишек: `clients/usmile/competitors/dental-landing-fishki-master.md`.
