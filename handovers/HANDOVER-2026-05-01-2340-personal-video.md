# Handover: Семейный тизер «МИР! ТРУД! МАЙ!» — Hollywood-style 25-сек коллаж

**Дата:** 2026-05-01 23:40
**Контекст:** personal-video (cwd ~)
**Сессия:** fcb50238-7f3d → 555f1d20 → 3209ef76 (3 resume цепочкой)
**Статус:** в работе, итерация 8 в процессе

## 🎯 Цель сессии

Скачать YouTube-видео в mp3, собрать вертикальный 25-сек коллаж семейного дня (роспись матрёшек, 1 мая) под The Power of Love, придать Hollywood-эстетику с overlay-текстом и плёночным фильтром.

## ✅ Что сделано

- `~/Downloads/youtube-mp3/The Power of Love.mp3` — скачан yt-dlp из https://www.youtube.com/watch?v=ZCXlI3eMoJE (8.3 МБ, ~4 мин, 22 сек тишины в начале файла)
- `~/Downloads/youtube-mp3/alina_matryoshka_25s.mp4` — основной body, 25 сек, 1080×1920, 30fps:
  - Источники: 4 видео `~/Downloads/IMG_9343.MOV`, `IMG_9344.MOV`, `IMG_9361.mov`, `IMG_9362.mov`
  - 16 фото из image-cache (см. ниже про потерю)
  - Структура: 7 видео-сегментов + 16 фото-вставок (по 0.55 сек, всего 23 нарезки). IMG_9362 (Алиша + матрёшка, slow-mo волосы) проходит сквозной нитью 4 раза.
  - Audio fix: mp3 от 27-й секунды (после fade-in источника) через atrim (не `-ss`), потому что input-`-ss` давал плавный fade-in 4 сек. Звук теперь сразу на полном уровне -19 dB.
- `~/Downloads/youtube-mp3/alina_hollywood_25s.mp4` — текущая версия с overlay'ями + cool blue фильтром (12 МБ, CRF 24, grain alls=4)
- `~/.claude/handovers/HANDOVER-...md` (этот файл)

Промежуточные артефакты:
- `/tmp/intro/render_overlays.py` — генератор PNG-оверлеев
- `/tmp/intro/ov{1..6}.png` — 6 текстовых оверлеев (Impact font, deprecated)
- `/tmp/intro/fonts/RussoOne.ttf`, `BowlbyOne.ttf`, `FugazOne.ttf` — 3 cartoon-cinema шрифта на выбор для следующей итерации

## 🧠 Решения и ПОЧЕМУ

| Решение | Альтернатива | Почему |
|---------|--------------|--------|
| Music start от mp3:27s | mp3:25s (вокальный онсет) | На 25s ещё идёт hit→тонический fade. На 27s — устойчивый куплет. Источник имеет 22 сек цифровой тишины + 3 сек фейд. |
| atrim вместо input -ss для аудио | -ss before -i | input -ss давал размазанный 4-сек fade-in (видимо keyframe seek inaccuracy). atrim точный → -19 dB сразу. |
| transpose=1 на все фото | rotate=PI/2 | Фото 2000×1500 без EXIF-флага ориентации (cache-формат), снято с iPhone в портрете. Исправляется только transpose. |
| Cool blue filter | Tarantino orange/teal | Антон явно сказал «нужен синеватый фильтр», 23:30. |
| Overlay-текст поверх существующего видео | Отдельные intro-карточки 5.4 сек | Антон сказал «ты удалил весь видеоряд… текст планировалось просто поверх». Концепт исправлен v6→v7. |
| Impact (system font) для текста | Bebas Neue (Google) | github.com/dharmatype/Bebas-Neue/raw/master/... возвращает 404. fonts.gstatic.com без User-Agent отдаёт HTML. Impact — system, поддерживает Cyrillic, Tarantino-adjacent. **Антон отверг — нужен «полумультяшный, полукиношный»** → перешёл на Russo One / Bowlby One / Fugaz One (не доделано). |
| Не делать freeze-frame под имена в v7 | Сделать freeze | Image-cache для photos #41-60 был стёрт при resume сессии → не могу пересобрать body с расширенной длительностью photo #48 для freeze под "AND ANTOSHA". Workaround предложен: вырезать кадр 17.6s из v4 как PNG, вставить как 1.5-сек фриз, удлинив таймлайн до ~26 сек. |
| Не использовать HyperFrames для intro | HyperFrames (наш аналог Remotion) | Overlay через ffmpeg drawtext+overlay проще и быстрее для 5 текстовых блоков. HyperFrames оправдан если интро будет сложнее (анимация, transitions, scene graph). |

## ❌ Что НЕ сделано и почему

- **v8 с Russo One + freeze-frame ANTOSHA + точные тайминги overlay'ев** — прервано на этапе сравнения шрифтов (`/tmp/intro/font_compare.png`). Антон сказал handover.
- **Photos #41-60 потеряны** — image-cache очистился при resume сессии (старая папка `fcb50238...` удалена, новая `72765bf5...` пустая). Чтобы пересобрать body — Антону нужно перетащить фото снова, ИЛИ использовать `ffmpeg -ss N -i alina_matryoshka_25s.mp4 -vframes 1 photo.png` для извлечения из существующего файла.
- **Free GitHub LUT** — Антон спросил про готовые .cube. Перепробовал ~6 URL: все 404 или требуют auth. github API search требует токен. Решение: либо вручную найти на rocketstock.com / lutify.me (требует email), либо продолжать ffmpeg `eq+curves+colorbalance` (текущий подход).
- **Hollywood freeze-frame intro по раскадровке агента** — агент `ui-designer` прислал детальную таблицу 14 кадров с shutter-snap SFX, RGB-split, slam-zoom 5%, light leaks, cut-to-black перед финалом. Не реализовано — ждёт фокус на одной задаче.
- **Audio sync с overlay'ями** — overlay'и сейчас на хардкод-секундах. Не привязаны к ритму музыки. Для следующей итерации можно использовать `silencedetect` или beat-detection чтобы попасть в долю.

## 📚 Уроки (новое знание для memory)

- **fonts.gstatic.com без User-Agent отдаёт HTML, а не TTF.** Нужен `curl -A "Mozilla/5.0..."`. Сохранить в `feedback_google_fonts_user_agent.md`.
- **github.com/.../raw/master/ ≠ raw.githubusercontent.com/.../master/**. Первый редиректит на HTML preview если файл большой/binary. Второй отдаёт raw сразу. Сохранить как урок.
- **`-ss` перед `-i mp3` неточен** — для bit-accurate seek используй atrim после декодирования. Сохранить в `feedback_ffmpeg_audio_seek.md`.
- **iPhone фото в Claude Code image-cache теряют EXIF orientation** — нужен `transpose=1` явно. Сохранить.
- **Image-cache очищается при resume сессии** — не полагаться на `~/.claude/image-cache/<sessionId>/` для долгоживущих артефактов. Если фото нужны для дальнейшей работы — копировать в `~/Downloads` или другое стабильное место СРАЗУ. Сохранить в `feedback_session_cache_volatile.md`.

## 🔜 Следующие шаги (приоритет)

1. **HIGH:** Спросить Антона о Russo One vs Bowlby One vs Fugaz One — показать `/tmp/intro/font_compare.png` (там видны 3 варианта на тексте «АНТОША»). Bowlby/Fugaz почему-то отрисовались мелким каше — проверить, что Cyrillic glyphs в файле есть.
2. **HIGH:** Извлечь photo #48 (selfie дочка+папа) из v4 как frame: `ffmpeg -ss 17.6 -i alina_matryoshka_25s.mp4 -vframes 1 /tmp/intro/antosha_freeze.png`. Это единственный кадр с Антошей.
3. **HIGH:** Пересобрать v8: Russo One (или выбранный) + freeze-frame ANTOSHA на 17.0-18.5s + переразместить overlay'и:
   - `KAMERISTYI FAMILY presents` — 0.3-2.0s (top-third, на фоне Алиши, не закрывая лицо)
   - `STARRING ALISHA` — 10.5-12.5s (slow-mo волосы, bottom-third)
   - `AND ANTOSHA` — 17.0-18.5s (на freeze #48, top или bottom — не на лицах)
   - `МИР! ТРУД! МАЙ!` — 22-25s (центр, gradient yellow→orange→red)
4. **MEDIUM:** Freeze-frame техника — добавить shutter-snap SFX (короткий 0.05s click) при каждом фризе. Tarantino-vibe.
5. **MEDIUM:** Найти готовый .cube LUT через `rocketstock.com/free-after-effects-templates/35-free-luts-for-color-grading/` или `lutify.me/free-luts/` (требует email). Применить через `lut3d=file=...`. Альтернатива: продолжать вручную накручивать `eq+curves+colorbalance`.
6. **LOW:** Раскадровка от агента-кинооператора (28 сек, 14 freeze-frame) — амбициозная версия с RGB-split, light leaks, cut-to-black. Транскрипт в `/private/tmp/claude-501/-Users-antonk/3209ef76.../tasks/a2843191868056eb8.output` (агент завершён).

## 🗺️ Карта файлов

```
~/Downloads/
├── IMG_9343.MOV (3 сек, 4K) — кисточка/процесс, мальчик
├── IMG_9344.MOV (10 сек, 4K) — учительница даёт матрёшку
├── IMG_9361.mov (28 сек, HD) — Алиша смотрит вверх с радужной матрёшкой
├── IMG_9362.mov (37 сек, HD) — Алиша + матрёшка, slow-mo волосы (главное!)
└── youtube-mp3/
    ├── The Power of Love.mp3 (8.3 МБ)
    ├── alina_matryoshka_25s.mp4 (24 МБ, body, исходный коллаж)
    └── alina_hollywood_25s.mp4 (12 МБ, текущая версия с overlays + blue filter)

/tmp/intro/
├── render_cards.py — для отдельных black-bg карточек (deprecated)
├── render_overlays.py — для transparent overlay'ев (используется)
├── ov1..ov6.png — 6 overlay'ев в Impact font (старый шрифт)
├── fonts/
│   ├── RussoOne.ttf (Cyrillic, geometric display)
│   ├── BowlbyOne.ttf (cartoon bold)
│   └── FugazOne.ttf (italic display)
├── card1..card6.png — старые black-bg карточки
└── font_compare.png — превью 3 шрифтов на «АНТОША»

~/.claude/image-cache/
├── 72765bf5-... (текущая сессия, ПУСТАЯ)
└── (fcb50238 удалён при resume — здесь были фото #41-60)
```

## 🎬 Раскадровка body (для понимания где какой человек)

| Время | Источник | Кто в кадре |
|-------|----------|-------------|
| 0.0-3.0 | IMG_9362 | **Алиша** + матрёшка (full body, открытие) |
| 3.0-3.55 | photo 44 | **Алиша** closeup |
| 3.55-4.10 | photo 47 | **Алиша** closeup |
| 4.10-5.7 | IMG_9344 | учительница (руки, без лица) |
| 5.7-6.25 | photo 43 | группа: учительница + Алиша + другие дети |
| 6.25-6.8 | photo 45 | учительница с феном |
| 6.8-7.35 | photo 52 | Стас с банкой |
| 7.35-8.95 | IMG_9361 | **Алиша** смотрит вверх |
| 8.95-9.5 | photo 41 | Стас с луком |
| 9.5-10.05 | photo 58 | блондинка-подружка с луком |
| 10.05-13.55 | IMG_9362 | **Алиша** slow-mo волосы (КУЛЬМИНАЦИЯ) |
| 13.55-14.1 | photo 57 | матрёшки Iron Man + Batman |
| 14.1-14.65 | photo 60 | руки расписывают |
| 14.65-15.2 | photo 53 | рука с бутылкой |
| 15.2-16.8 | IMG_9343 | учительница + мальчик |
| 16.8-17.35 | photo 50 | мальчик + Алиша selfie |
| **17.35-17.9** | **photo 48** | **АНТОША** + Алиша selfie ← ЕДИНСТВЕННЫЙ кадр Антоши |
| 17.9-18.45 | photo 54 | прялки |
| 18.45-19.0 | photo 56 | Стас |
| 19.0-19.55 | photo 59 | wooden trough |
| 19.55-22.05 | IMG_9362 | **Алиша** financial |
| 22.05-22.6 | photo 46 | **Алиша** + матрёшка |
| 22.6-25.0 | IMG_9362 | **Алиша** closing |

## ⚠️ Гачи (gotchas)

- **Image-cache волатильна** — при resume сессии папка переименовывается, старая удаляется. Не пытаться использовать `/Users/antonk/.claude/image-cache/<sessionId>/N.jpeg` после resume. Извлекать кадры из MP4 через ffmpeg.
- **Pillow + Google Fonts** — без User-Agent скачивается HTML, Pillow падает с `OSError: unknown file format`. Всегда: `curl -A "Mozilla/5.0..."`.
- **Файл получается 165 МБ при CRF 20 + grain** — film grain убивает x264 compression. Использовать CRF 24 + grain alls=4 → ~12 МБ. Если нужно ещё меньше — отключить grain или использовать `-tune grain` для x264.
- **Антон не любит фейд-ин аудио** — на 0:04 заметил. Музыка должна стартовать сразу на полной громкости. atrim точный, input -ss даёт фейд.
- **Антон ОЧЕНЬ требователен к попаданию текста на правильного человека** — overlay «ANTOSHA» в районе 11.5-13.5s = на Алише = ОШИБКА. Проверять раскадровку до билда.
- **«Стас» ≠ «Антоша»** — в исходниках есть человек со светлыми волосами, который держит лук (фото 41, 42, 56) — это Стас, друг семьи. Антоша — только на photo 48 (тёмные волосы, седина, селфи с дочкой). Не путать!
- **При новом resume сессии** — в новом cache `72765bf5-...` папке. Старая `fcb50238` НЕ доступна. Если нужны фото — попросить Антона перетащить заново.

## 🔗 Связанные ресурсы

- YouTube source: https://www.youtube.com/watch?v=ZCXlI3eMoJE (Frankie Goes to Hollywood — The Power of Love? или Huey Lewis BTTF version — title не указан)
- Recap: `/Users/antonk/artvision-data/sync/recaps/fcb50238-7f3d-4ccf-96ec-6102ea95d421.md`
- Агент-раскадровка (28 сек, freeze-frames): `/private/tmp/claude-501/-Users-antonk/3209ef76-4c2a-4c60-84c8-1749ebc11d58/tasks/a2843191868056eb8.output`
- TaskList активный: `#5 completed (intro+filter v6)`, `#6 pending (v8 Russo One)`

## 🎨 Стилистический референс (от Антона)

- «Just Go With It» (2011, Adam Sandler + Jennifer Aniston) — сцена в McFinnigan's: 80s/70s music + slow-motion hero shot. У нас это уже передано через slow-mo Алиши + Power of Love (1985).
- Tarantino — «Once Upon a Time in Hollywood» — large bold display font, orange/yellow palette на тёмном фоне, slam-cuts на представлении персонажей.
- Финальный титул «МИР! ТРУД! МАЙ!» — советский 1 мая lockup, gradient yellow→orange→red.
- Шрифт — «полумультяшный, полукиношный» (т.е. НЕ Impact, НЕ Helvetica). Кандидаты: Russo One / Bowlby One / Fugaz One. Антон выберет.
