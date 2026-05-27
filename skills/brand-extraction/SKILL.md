---
name: brand-extraction
description: Извлечение настоящего фирстиля клиента с его сайта — лого, иконки, цвета, шрифты, sprite-элементы. Парсит CSS background-position координаты и вырезает каждый элемент в отдельный PNG + собирает brand-extracted.yaml. Скачивает favicon.svg как вектор-источник. Триггеры — 'brand extraction', 'извлечь бренд', 'фирстиль клиента', 'настоящий лого', 'sprite клиента', 'извлеки логотип'. Запускать ОБЯЗАТЕЛЬНО при работе с новым клиентом до первого Edit/Write дизайна.
---

# /brand-extraction — настоящий фирстиль клиента из его сайта

## Зачем

**Прецедент 27.05.2026 (USmile):** Claude построил вывеску из выдуманного «USmile»-wordmark белым на красном, тогда как настоящий бренд = `ⓤ SMILE` (красный круг с U + слово SMILE) — лежал в sprite сайта. Антон забраковал: «слабый дизайн / пропустил тучи требований». 4 часа итераций впустую.

**Этот скилл предотвращает повтор** — за 30 секунд достаёт ВСЕ брендовые элементы из CSS клиента до начала любого дизайна.

## Когда вызывать (триггеры)

- `/new-client <slug>` — обязательно как Шаг N
- Любая дизайн-задача для клиента (КП / лендинг / вывеска / макет)
- При создании reference-pack клиента
- При повторении ошибки «выдумал цвет» — STOP, запустить /brand-extraction

## Что делает

1. **Скачивает HTML** главной + всех linked CSS (`<link rel=stylesheet>`)
2. **Парсит CSS** на:
   - `background-image: url(...sprite*.png|svg)` — sprite-картинки
   - `background-position: -Xpx -Ypx` + `width:Wpx; height:Hpx` — координаты элементов
   - Имена селекторов (`.icon-tooth`, `.header_logo` и т.п.) — определяют семантику
3. **Скачивает sprite-картинки** (1x + @2x если есть)
4. **Вырезает каждый элемент** по точным координатам (умножая на 2 для @2x)
5. **Скачивает favicon.svg** — вектор-источник логотипа
6. **Извлекает шрифты** из `@font-face` (имена + URL .woff2/.ttf)
7. **Извлекает hex-цвета** из CSS с частотой использования (top-10)
8. **Сохраняет всё в `clients/<slug>/assets/logo-real/`:**
   - `elements/01-logo-header.png`, `02-icon-tooth.png` ... (имена из CSS-селекторов)
   - `vector/favicon.svg`
   - `brand-extracted.yaml` — машино-читаемый манифест (цвета, шрифты, элементы, источник CSS-файла)

## Использование

```
/brand-extraction <client-slug>
```

или с явным URL:
```
/brand-extraction usmile https://usmile.ru
```

## Скрипт

См. `scripts/extract_brand.py`. Запуск:
```bash
python3 ~/.claude/skills/brand-extraction/scripts/extract_brand.py \
  --slug usmile \
  --url https://usmile.ru \
  --output ~/artvision-data/clients/usmile/assets/logo-real/
```

## Что в результате должно быть (acceptance)

- [ ] `assets/logo-real/elements/` — минимум 5 PNG (логотип + 4+ иконки)
- [ ] `assets/logo-real/vector/favicon.svg` (если у клиента есть)
- [ ] `assets/logo-real/brand-extracted.yaml`:
  ```yaml
  client: usmile
  source: https://usmile.ru
  extracted_at: 2026-05-27T17:30:00Z
  fonts:
    - family: "SF Pro Display"
      url: "/templates/usmile/assets/fonts/SFProDisplay-Bold.woff2"
  colors:
    primary: "#DC143C"   # 142 usages
    text: "#1A1A1A"      # 89 usages
  sprite_source: https://usmile.ru/templates/usmile/assets/sprites/main@2x.png
  elements:
    - name: "header_logo"
      file: "elements/01-header_logo.png"
      size: [122, 46]
      bg_position: [0, -114]
    - name: "icon-tooth-karies"
      file: "elements/06-icon-tooth-karies.png"
      size: [34, 42]
      bg_position: [-260, -168]
  ```

## После запуска

1. Read `brand-extracted.yaml` — это authoritative источник для всех дизайн-задач клиента
2. Использовать ТОЛЬКО эти цвета (не выдумывать)
3. Использовать ТОЛЬКО эти иконки (не генерировать нейросетью)
4. Шрифт — тот же что на сайте клиента (downloaded в `vector/fonts/` опц.)

## Связанные

- `~/.claude/rules/quality.md` — Pre-Task Protocol
- `~/.claude/rules/no-smoothing.md` — не выдумывать
- `~/.claude/skills/new-client/SKILL.md` — общий онбординг
- Hook `pre-design-without-brand-source.sh` — блокирует Edit/Write дизайна пока нет свежего `brand-extracted.yaml` (< 7 дн)
- Прецедент: `clients/usmile/LESSONS-2026-05-27.md`
