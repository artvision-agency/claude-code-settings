# Shorts PiP Composition — стандарт композиции YouTube Shorts с автором

> **Установлено:** 2026-05-12, после полного цикла pilot Видео 1 (CTR теория, IMG_9893) с консилиумом 3 спецов (round_table + 2 Opus агентов). Антон утвердил параметры.
> **Применять:** ВСЕГДА когда делаем Shorts/Reels с PiP композицией (talking head автора + B-roll картинки).
> **Связано:** skill `shorts-pip-composer` (~/.claude/skills/shorts-pip-composer/).

## Главное правило

**PiP-фрейм автора НЕ ДОЛЖЕН перекрывать данные на B-roll слайдах.** Это критично — нарушение Антон сразу замечает («сам мелкий фрейм не должен перекрывать данные слайда это ни в коем случае не должно быть»).

## 🎬 PREMIUM качество — дефолт с 2026-05-16

**Все Shorts/Reels рендерим в PREMIUM** (решение Антона 16.05.2026 после сравнения с прошлым CRF 18 fast):

| Параметр | Значение | Зачем |
|----------|---------|-------|
| `preset` | `slow` | Тщательное motion estimation, меньше артефактов |
| `crf` | `16` | Visually lossless (CRF 18 был "near-lossless") |
| `pix_fmt` | `yuv420p` | Совместимость со всеми платформами |
| **Single-pass composition** | filter_complex объединяет всё в одном вызове | Убирает generation loss от 3-4 цепочек re-encode |
| `-c:v copy` для concat | где возможно | Не пересжимать без необходимости |

### Single-pass template (B-roll + PiP + лого + audio + loudnorm):
```bash
ffmpeg -y \
  -i broll_segs.mp4 \
  -ss 5 -t [DUR] -i pip.mp4 \
  -i brand/logo_artvision_purple_220.png \
  -ss 5 -t [DUR] -i speech_full_HD.mp4 \
  -filter_complex "
[0:v]scale=1080:1920,setpts=PTS-STARTPTS[bg];
[1:v]scale=320:400,setpts=PTS-STARTPTS[pip];
[2:v]scale=220:-1[logo];
[bg][pip]overlay=40:1480[v1];
[v1][logo]overlay=W-w-40:60[v]
" -map "[v]" -map 3:a \
  -c:v libx264 -preset slow -crf 16 -pix_fmt yuv420p -r 30 \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11" \
  -c:a aac -b:a 192k -t [DUR] \
  broll_premium.mp4
```

Размер файла +25% vs fast/CRF 18, но качество заметно лучше на мелких деталях (текст в графиках, лицо в PiP, антиалиасинг).

## 🚫 Строгие правила Антона в видео для @-Artvisionpro (security.md контекст)

Применяется при ВСЕХ Shorts/Reels/16:9 для канала. Нарушение = переделка.

| Правило | Что | Источник |
|---|---|---|
| **AI/нейросети = ТАБУ в видео** | НЕ упоминать в субтитрах/B-roll-тексте/voice. Канал публичный. Замены: «Авторская методология», «Аналитическая система», «Экспертный анализ» | `~/.claude/rules/security.md` |
| **Брендированные имена продуктов** | Если упоминаем наш продукт: Artvision LinkForge (НЕ «PBN»), Artvision Radar (НЕ «AI GEO»), Artvision Flow (НЕ «SEO Pipeline»), Artvision Watch (НЕ «ORM»), Artvision Insight (НЕ «Sales Psychology»), Artvision Content Lab (НЕ «content writer»), Artvision Scout (НЕ «competitor monitor»), Artvision Leads (НЕ «HH-leadgen»), Artvision Funnel (НЕ «lead generation factory»), Artvision VoxRate (НЕ «сбор отзывов TG-бот») | `~/.claude/rules/security.md` |
| **Чужие сервисы в видео** | НЕ показывать Wordstat/Semrush/Ahrefs логотипы — ребрендим в Artvision-продукты или описываем без бренда | то же |
| **Yandex логотип** | ТОЛЬКО красный `#fc3f1d` (актуальный 2024-26), НЕ жёлтый | (уже было) |
| **Google Ads в РФ-кадре** | Google Ads ушёл из РФ с 2022 — НЕ упоминать Google Ads как канал. Только Яндекс.Директ. Google SERP в кадре про Я.Директ — нарушение | (уже было) |
| **Цены клиента в кадре** | НЕ показывать конкретные суммы клиентов (NDA) — обобщённо «крупный заказчик», «средняя клиника» | `~/.claude/rules/security.md` |
| **Cyrillic шрифт в outro/subs** | Использовать `/System/Library/Fonts/HelveticaNeue.ttc` или Helvetica.ttc — есть Cyrillic поддержка. НЕ Google Fonts CDN | `~/.claude/rules/shorts-pip-composition.md` |
| **Loudnorm -14 LUFS** | YouTube стандарт, обязательно `loudnorm=I=-14:TP=-1.5:LRA=11` | то же |
| **Pre-task read protocol для клиентских видео** | Если видео для клиента (НЕ канала) — прочитать `clients/<slug>/CLAUDE.md` + `context-log.md` ПЕРЕД монтажом | `~/.claude/rules/quality.md` |

## Размер PiP

- **320×400 px** (4:5 ratio) — оптимально для educational Shorts
- НЕ 380×480 («детский монтаж» по фидбеку Антона)
- НЕ 420×524 (перекрывает данные)
- НЕ круглый — для educational контента слишком игривый стиль

## Crop кадра автора

- **Делать ffmpeg pre-crop**, НЕ через CSS `transform: scale()` или `object-position`
- CSS-методы дают «дрейф» рендера, плохое качество, неровный результат
- Стандарт для iPhone vertical (608×1080 proxy):
  - `ffmpeg ... -vf "crop=500:624:54:200,scale=320:400"`
  - Crop W:H:X:Y = 500:624:54:200 → 4:5 ratio
  - Headroom ~6-8% над макушкой
  - Scale до 320×400 (final PiP frame size)
- Размеры ОБЯЗАТЕЛЬНО чётные (libx264 yuv420p)

## Стилизация PiP frame

- **Border:** 3px white (НЕ 5+, стримерский look 2018)
- **Border-radius:** 20px (subtle, не 30+ который «рисованный»)
- **Box-shadow:** `0 8px 32px rgba(0,0,0,0.35), 0 0 0 1px rgba(0,0,0,0.12)` (soft, large blur)
- **Background:** `#000` (на случай пустоты)

## PiP стратегия (обновлено 2026-05-12 после фидбека Антона v5 → v6)

**ГЛАВНЫЙ ПРИНЦИП:** PiP видим **только на text-card** слайдах. На **data-heavy** слайдах (графики, SERP, mockups) — PiP **полностью скрыт** (`opacity: 0`).

### Классификация слайдов

| Тип | Описание | PiP |
|---|---|---|
| **text-card** | Формула, заголовок, summary plate, итог | ✅ Видим (320×400 в углу) |
| **mockup-mini** | SERP-карточка одна, lifestyle illustration | ✅ Видим (safe-zone сбоку) |
| **data-heavy** | Bar chart, реальная SERP с данными, phone mockup с UI | ❌ Hide — полный экран |

### Позиции PiP (только когда видим)

- Default: `left: 40px, top: 1480px` (bottom-left)
- Если на слайде заголовок/плашка слева сверху → `left: 720px, top: 1480px` (bottom-right)
- Если слайд имеет важные элементы в нижней части → top corners (40 или 720, top: 100)

### Transition между позициями

**ОБЯЗАТЕЛЬНО** fade-out → teleport → fade-in (НЕ slide-through):

```js
// 1. Fade-out до transition (PIP_FADE = 0.25s)
tl.to("#speech-pip", { opacity: 0, duration: 0.25, ease: "power2.in" }, start - 0.35);
// 2. Teleport (instant, while invisible)
tl.set("#speech-pip", { left: ..., top: ... }, start - 0.05);
// 3. Fade-in до target opacity
tl.to("#speech-pip", { opacity: 1, duration: 0.25, ease: "power2.out" }, start + 0.1);
```

**ПОЧЕМУ:** Slide-transition `tl.to({ left: 720, duration: 0.35 })` создаёт промежуточные кадры где PiP проходит через центр экрана = перекрывает данные. Fade pattern избегает этого полностью.

### Прецедент

Антон 2026-05-12, после 6 итераций пилот Видео 1:
- v1-v4: PiP на всех slides → "иногда появляются закрытие контент фреймом"
- **v6 (FINAL):** PiP только на text-cards, на data-slides hide → утверждено

## Логотип бренда

- **Top-right** угол (60px от края), 220px ширина, opacity 0.85
- Drop-shadow: `0 4px 12px rgba(0,0,0,0.6)`
- Постоянно видим throughout видео

## B-roll PNG слайды

- Размер: **1080×1920** (vertical 9:16)
- **ОБЯЗАТЕЛЬНО** оставлять safe-zone в углах для PiP (см. таблицу выше)
- Шрифт: system stack `-apple-system, BlinkMacSystemFont, "Inter", ...` — НЕ Google Fonts CDN
- Цифры — реальные с источником (Backlinko, SISTRIX, etc), URL под чартом
- НЕ упоминать «AI», «нейросеть», «GPT», «ML» в visible тексте

### Скриншоты SERP

- **Только Яндекс**, НЕ Google. Google Ads ушёл из России в 2022.
- При SmartCaptcha Яндекса → HTML mock через ui-designer agent
- Актуальный Яндекс логотип 2024-26: **красный** #fc3f1d (жёлтый только на yandex.ru главной)

## Captions / Subtitles

### Параметры (зафиксированы Антоном после v1 «огромные, ничего не видно»):

```
FontName=Arial, FontSize=24, Bold=1
PrimaryColour=&Hffffff (белый), OutlineColour=&H000000 (чёрный)
BackColour=&H80000000 (50% черный box backdrop)
BorderStyle=4, Outline=8, Shadow=0
Alignment=2 (bottom-center)
MarginV=900 (НАД PiP — PiP top=1480, sub bottom=1920-900=1020)
MarginL=80, MarginR=80
WrapStyle=0 (smart wrap)
```

### Sync с jump-cut timeline

Whisper SRT timestamps относительны исходного видео. После jump-cut длительность другая.
**ОБЯЗАТЕЛЬНО** пересчитать SRT через `scripts/remap-srt-to-jumpcut.py`.

### Чистка SEO-терминов

Whisper small RU делает типичные ошибки на спец-терминах. Применять словарь `templates/whisper-russian-corrections.json`:
- «Click-True Rate» → «Click-Through Rate»
- «SEO-вудачу»/«SEO-шкул» → «SEO-выдачу»
- «шамонтаж» → «шиномонтаж»
- «проянный» → «рекламный»
- (см. файл для полного списка)

## Audio

- **Loudness normalization** до `-14 LUFS` (YouTube стандарт)
- `ffmpeg -af "loudnorm=I=-14:TP=-1.5:LRA=11"`
- Без этого видео может быть тише/громче соседних в ленте

## Jump-cut threshold

| Уровень | d (s) | noise (dB) | Reduction | Когда |
|---------|-------|-----------|-----------|-------|
| **Safe** | **0.5** | -30 | ~17% | Default. Естественная речь сохраняется. |
| Aggressive | 0.35 | -28 | ~22% | Дополнительно -2..-3s. Норма для educational. |
| ⚠️ Too tight | 0.3 | -25 | ~28% | Русский >200 WPM = «пулемёт», падает разборчивость |

**Текущий стандарт: 0.5s** (188 WPM на пилоте, у предела комфортного).

## Метод jump-cut

**ВАЖНО:** использовать **concat-demuxer на 1080p proxy**, НЕ `filter_complex select` на 4K HEVC.

`filter_complex select` на 4K@60fps часто выдаёт пустой MP4 (известная проблема ffmpeg). Concat-demuxer работает надёжно + 16× быстрее.

## Антипаттерны (что НЕ делать)

| ❌ | ✅ |
|---|---|
| CSS `transform: scale(1.45)` + `object-position` для crop | ffmpeg pre-crop с фиксированными координатами |
| PiP fullscreen overlay (1080×1920) на лице | PiP 320×400 в углу + B-roll fullscreen |
| Одна позиция PiP на все 6 slides | Динамическая позиция per slide + fade на data |
| Border 5+ px белый «стримерский» | Border 3px |
| Border-radius 30+ px | Border-radius 20px |
| Hard shadow `0 0 0 8px` | Soft shadow `0 8px 32px 35% opacity` |
| FontSize 36 subtitles (огромные) | FontSize 24 + WrapStyle 0 + box backdrop |
| Subtitles на PiP/лице | Subtitles НАД PiP (MarginV 900+) |
| `filter_complex select` на 4K HEVC | concat-demuxer на 1080p proxy |
| Whisper medium RU | Whisper small RU (часто фейлит SHA на medium) |
| Сырой Whisper SRT | Через `clean-whisper-srt.py` + `remap-srt-to-jumpcut.py` |
| Google SERP в кадре про Я.Директ | Только Яндекс (Google Ads нет в РФ с 2022) |
| Жёлтый Яндекс логотип в mock | Красный #fc3f1d (актуальный 2024-26) |
| Без `loudnorm` | -14 LUFS обязательно |

## Формат 16:9 (YouTube long-form, Rutube горизонталь) — добавлено 2026-05-13

Для тех же видео в 16:9 — letterbox layout, не split.

| Параметр | 9:16 (1080×1920) | 16:9 (1920×1080) |
|---|---|---|
| Resolution | 1080×1920 | 1920×1080 |
| B-roll | Fullscreen vertical | Scale to height 1080, letterbox padded до 1920×1080, color `#212121` (dark gray) |
| PiP размер | 320×400 | 280×350 |
| PiP позиция | x=40, y=1480 (BL) | x=W-w-40, y=H-h-40 (BR) |
| Лого ширина | 220px | 200px |
| Лого позиция | x=W-w-60, y=60 | x=W-w-40, y=40 |
| Subtitles MarginV | 900 (над PiP BL) | стандарт ASS 16:9 |

**Почему letterbox, а не split-layout:** B-roll storyboards рисуются в 9:16 (1080×1920) — split в 16:9 кропит важный контент. Letterbox сохраняет полный B-roll, dark gray bands не отвлекают.

## Brand logo — два варианта (добавлено 2026-05-13)

Для одного видео нужны **два варианта** brand-логотипа Artvision:

| Назначение | Цвет | Файл | Где |
|---|---|---|---|
| Overlay на B-roll (top-right corner) | `#614CE1` (фиолетовый) | `logo_artvision_purple_220.png` | На всех слайдах кроме hook и outro |
| Outro (на фиолетовом фоне) | `#FFFFFF` (белый) | `logo_artvision_white_220.png` | Только на outro 3s |

**Почему два:** фиолетовый лого на фиолетовом outro-фоне (`#614CE1`) сливается, виден только outline (визуальный fail в первой итерации 2026-05-13).

**Источник лого:** генерируется через `make_logo.py` (PIL text), не использовать существующий `logo_artvision_dark.png` (199×130 PNG — не соответствует #614CE1, выглядит серым).

## Outro 3s «Подписаться» (добавлено 2026-05-13)

Каждое видео заканчивается outro-screen 3s — для retention метрики и роста подписок.

| Элемент | Параметры |
|---|---|
| Длительность | 3s (минимум — успеть прочитать CTA + кликнуть Subscribe) |
| Фон | `#614CE1` (брендовый фиолет) |
| Лого | Белый PNG 220px, top of center, smaller scale `-1:140` |
| Главный текст | «Подписаться», 110px (9:16) / 140px (16:9), Helvetica, white |
| Sub-текст | «@-Artvisionpro», 42px (9:16) / 52px (16:9), `#C7BFFC` (bg-pale) |
| Audio | Silence 3s (anullsrc) — не отвлекает от CTA |
| Концат | filter_complex `concat=n=2:v=1:a=1` (не `-c copy` — рисково при разных stream params) |

## Pipeline scripts (template) — добавлено 2026-05-13

Все 5 скриптов pipeline зафиксированы как template в `~/artvision-data/personal/social_clips/templates/artvision-shorts-pipeline/`. Используй для нового видео:

1. `make_logo.py --color=purple|white` → brand PNG
2. `make_outro.sh <out.mp4> <W> <H>` → 3s outro
3. `build_ffmpeg.sh` → 9:16 B-roll concat из storyboards (с дюрациями per segment)
4. `build_16x9_broll.sh` → 16:9 B-roll concat (letterbox)
5. `compose_v2.sh` или `compose_v2_16x9.sh` → финал (main + outro concat)

Template README содержит шаги для каждого нового видео.

## Чек-лист готовности видео (verify-video.sh)

```bash
# Все 4 файла обязаны пройти:
ffprobe -v error -show_entries format=duration -of csv=p=0 "$f"          # > 0
ffprobe -v error -select_streams v:0 -show_entries stream=width,height ...  # совпадает с форматом
ffprobe -v error -select_streams a:0 -show_entries stream=codec_name ...    # aac
[[ $(wc -c < "$f") -gt 1000000 ]]                                          # > 1 MB
# Visual smoke check — PiP fade окна:
ffmpeg -ss <data_t> -i "$f" -vframes 1 ...                                 # глазами проверить
```

**Прецедент 2026-05-13:** V2 16:9 concat прервался при shutdown сессии — ffprobe вернул пустоту. Перерендер исправил. **Урок:** после концата всегда проверять ffprobe duration.

## Прецеденты

- **2026-05-12 Видео 1 «CTR теория»** (IMG_9893):
  - Iteration 1: overlay fullscreen → «детский монтаж» (Антон)
  - Iteration 2: PiP basic 380×480 → нормально
  - Iteration 3: PiP fixed 420×524 + ffmpeg crop → лучше
  - Iteration 4 (FINAL): PiP 320×400 + dynamic position + fade on seg3 → утверждено

- **2026-05-13 Финал Видео 1 + Видео 2 (CTR теория + шиномонтаж кейс)**:
  - 3 фикса по аудиту senior'ов: PiP fade на data-heavy моментах, лого 220px #614CE1 (новый PNG text-based), outro 3s «Подписаться»
  - 4 финала готовы: 9:16 V1 (51.55s), V2 (57.42s), 16:9 V1/V2 letterbox
  - Решение: letterbox 16:9 (не split) — сохраняет полный B-roll
  - Решение: два варианта лого (overlay фиолет + outro белый) — фиолет на фиолет невидим
  - Урок: HyperFrames screenshot-seek не играет video-element → ffmpeg overlay direct
  - Git: scripts/* + brand/logo_artvision_{purple,white}_220.png в template для будущих видео

## Связь со скиллами

- `shorts-pip-composer` — основной pipeline (этот стандарт)
- `frontend-design` / `ui-designer` — генерация B-roll PNG
- `agent-browser` — скриншоты SERP (если не блокируется капчей)
- `audio-normalize` — для отдельной нормализации
- `video-editing` — родительский ECC skill (общий video pipeline)
- `youtube-publish` — публикация на YouTube
- Template: `~/artvision-data/personal/social_clips/templates/artvision-shorts-pipeline/`
- `youtube-publish` — финальный шаг публикации на канал
