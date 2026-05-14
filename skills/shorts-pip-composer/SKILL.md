---
name: shorts-pip-composer
description: Создание YouTube Shorts/Reels (9:16) И 16:9 версий с PiP композицией (talking head автора + B-roll на весь экран). Полный pipeline под русский язык — Whisper small транскрипт с SEO-correction словарём, jump-cut пауз через concat-demuxer на 1080p proxy (НЕ filter_complex select на 4K), ffmpeg pre-crop PiP (320×400 для 9:16, 280×350 для 16:9), ffmpeg overlay direct (НЕ HyperFrames — не играет video), PiP fade на data-heavy моментах, лого 220px фиолет #614CE1 (text-PNG через make_logo.py, два варианта — purple для overlay + white для outro), outro 3s «Подписаться», burn-in ASS субтитров, loudness norm -14 LUFS под YouTube. Template — `artvision-data/personal/social_clips/templates/artvision-shorts-pipeline/`. Триггеры — 'shorts', 'reels', 'видео с лицом', 'pip композиция', 'shorts pip', 'монтаж шортс', 'tiktok видео', 'short с автором', 'talking head shorts', 'видео для канала', 'образовательный шортс', 'видео ctr', 'видео для youtube', 'выпуск shorts'.
---

# Shorts PiP Composer

Создание Shorts/Reels с Picture-in-Picture композицией под русский educational контент. Стандартизированный pipeline из 8 шагов.

**Установлено:** 2026-05-12, после полного цикла pilot Видео 1 (CTR теория) с консилиумом из 3 спецов + round_table. Антон утвердил параметры.

## Когда применять

- Антон записал видео на iPhone (vertical 4K@60fps HEVC, ~1 мин)
- Хочет получить YouTube Shorts / Instagram Reels с B-roll картинками поверх
- Канал @-Artvisionpro или личный
- Тема: SEO, CTR, маркетинг, бизнес-объяснения

## Когда НЕ применять

- Длинное видео (>2 мин) — не помещается в Shorts
- Контент без structured speech (vlog, нарративный)
- Клиентский контент (это для нашего канала, не для клиента)
- Нужна красивая color grading / cinematic look (не наш формат)

## ⚠️ Финальный pipeline (после prod 2026-05-13) — ОБЯЗАТЕЛЬНО

**Используй template, не пиши скрипты с нуля.** После Видео 1+2 (CTR теория + кейс шиномонтаж, 2026-05-13) зафиксирован финальный pipeline:

📁 **Template:** `~/artvision-data/personal/social_clips/templates/artvision-shorts-pipeline/`

Содержит 6 скриптов + 2 brand-лого + README с 5 шагами. Скопируй для нового видео, отредактируй storyboard сегменты, запусти. Подробности — [[shorts-pip-composition]] правило.

**Ключевые изменения относительно секции "Pipeline (8 шагов)" ниже:**
- ❌ HyperFrames для финала — НЕ играет `<video>` element (screenshot-seek). Используй ffmpeg overlay direct.
- ✅ 16:9 версии — letterbox layout (`#212121` bands), не split. Скрипт `compose_v2_16x9.sh`.
- ✅ Два варианта лого: `make_logo.py --color=purple` (overlay на B-roll) + `--color=white` (outro).
- ✅ Outro 3s «Подписаться» обязательно — `make_outro.sh out.mp4 W H`.
- ✅ PiP fade-out 0.25s на data-heavy моментах (phone mockups, графики) — НЕ полный hide.
- ✅ ffprobe duration check ОБЯЗАТЕЛЬНО после concat — без этого можно отдать broken файл.

См. также:
- `~/.claude/rules/shorts-pip-composition.md` — все параметры/анти-паттерны
- `~/artvision-data/decisions/2026-05-13-shorts-pip-pipeline-final.md` — 6 решений с trade-offs
- `~/.claude/projects/-Users-antonk/memory/lessons_shorts_pip_2026-05.md` — 4 урока

## 🚫 Строгие правила Антона при создании видео для @-Artvisionpro

Эти правила НЕ опциональны — нарушение = переделка:

| Правило | Что |
|---|---|
| **AI/нейросети = ТАБУ в видео** | Не упоминать в субтитрах/B-roll/voice. См. `security.md`. Использовать «Авторская методология», «Аналитическая система», «Экспертный анализ». Канал @-Artvisionpro — публичный |
| **Брендированные имена продуктов** | Если упоминаем наш продукт: Artvision LinkForge (не «PBN»), Artvision Radar (не «AI GEO»), Artvision Flow (не «SEO Pipeline»), Artvision Watch (не «ORM»), Artvision Insight (не «Sales Psychology»). Полный список — `security.md` |
| **Yandex логотип в B-roll** | ТОЛЬКО красный `#fc3f1d` (актуальный 2024-26). НЕ жёлтый |
| **Google Ads НЕ упоминать про РФ-рекламу** | Только Яндекс.Директ (Google Ads ушёл из РФ с 2022). Если кадр про Я.Директ — Google SERP запрещён |
| **Loudnorm -14 LUFS** | YouTube стандарт, обязательно `loudnorm=I=-14:TP=-1.5:LRA=11` в финале |
| **Pre-crop PiP через ffmpeg, не CSS** | CSS `transform: scale()` даёт дрейф рендера |
| **Border 3px white, radius 20px** | НЕ 5px+ (стримерский look), НЕ 30px+ радиус (рисованный) |

## Pipeline (8 шагов)

### 1. Извлечение и подготовка
```bash
WORK="$HOME/artvision-data/personal/social_clips/$(date +%Y-%m-%d)-<slug>"
mkdir -p "$WORK"/{source,audio,brand,transcript,storyboard,project,output}
ln -sf "/Users/antonk/Downloads/IMG_XXXX.MOV" "$WORK/source/source.mov"

# Audio extract для Whisper
ffmpeg -y -i "$WORK/source/source.mov" -vn -acodec pcm_s16le -ar 16000 -ac 1 "$WORK/audio/audio.wav"

# Proxy 1080p для быстрого jump-cut (4K HEVC тяжёлый для filter_complex)
ffmpeg -y -i "$WORK/source/source.mov" -vf "scale=-2:1080" -c:v libx264 -preset ultrafast -crf 26 -c:a aac "$WORK/source/proxy_1080.mp4"
```

### 2. Транскрипция Whisper small RU

**ВАЖНО:** `medium` модель часто падает по SHA-checksum при перекачке. `small` достаточно для русского + быстрее (~2 мин на 1 мин видео).

```bash
whisper "$WORK/audio/audio.wav" \
  --model small --language Russian --task transcribe \
  --output_format all --output_dir "$WORK/transcript/" \
  --word_timestamps True --verbose False
```

### 3. Чистка Whisper-ошибок (SEO-термины)

См. `templates/whisper-russian-corrections.json` — словарь типичных ошибок Whisper на русском SEO-контенте.

```bash
python3 scripts/clean-whisper-srt.py \
  --input "$WORK/transcript/audio.srt" \
  --output "$WORK/transcript/audio_corrected.srt"
```

### 4. Jump-cut по silence

**Threshold по умолчанию:** `d=0.5s noise=-30dB` — даёт ~17% сжатие, безопасно для русской речи.

**Aggressive:** `d=0.35s noise=-28dB` — дополнительно -2..-3s, не рекомендуется опускать ниже 0.3s (русский тогда «как пулемёт», падает разборчивость >188 WPM).

```bash
python3 scripts/jumpcut.py \
  --input "$WORK/source/proxy_1080.mp4" \
  --threshold 0.5 --noise -30 \
  --output "$WORK/output/v1_speak_only.mp4"
```

Метод — **concat-demuxer на 1080p proxy**, НЕ `filter_complex select` на 4K HEVC (часто фейлит, отдаёт пустой mp4).

### 5. PiP pre-crop через ffmpeg

**Стандарт:** 4:5 portrait, head & shoulders, 320×400 финальный размер.

```bash
ffmpeg -y -i "$WORK/output/v1_speak_only.mp4" \
  -vf "crop=500:624:54:200,scale=320:400" \
  -c:v libx264 -preset fast -crf 19 -pix_fmt yuv420p \
  -c:a aac -b:a 192k \
  "$WORK/output/speech_pip.mp4"
```

**Параметры crop:**
- Source 608×1080 (proxy)
- `crop=W:H:X:Y` = 500:624:54:200
  - W=500, H=624 (aspect 0.801 = 4:5)
  - X=54 (центрировать лицо со смещением вправо — типично для iPhone)
  - Y=200 (срезать ~20% неба сверху)
- Размеры ЧЁТНЫЕ (libx264 требует для yuv420p)
- Scale до 320×400 (4:5 ratio сохранён)

**Headroom:** ~6-8% сверху над макушкой после crop.

### 6. HyperFrames композиция с динамическим PiP

См. `templates/composition.html` — готовый шаблон.

**Правила позиционирования PiP** (стандарт после консилиума 2026-05-12):

| Тип слайда | PiP позиция |
|------------|------------|
| Формула / абстракция в центре (seg1-стиль) | bottom-left (40, 1480) |
| Карточка с плашкой слева (seg2-стиль) | bottom-right (720, 1480) |
| **Data money-shot** (графики, ТОП-3) | **fade-out PiP** на 0.3-4s |
| Chart с bottom-band (seg4-стиль) | top-right (720, 100) |
| Mobile mockup (seg5-стиль) | bottom-left mini (40, 1480) |
| Итог-плашка с tiles (seg6-стиль) | bottom-right (720, 1480) |

**Никогда** не оставлять PiP в одной позиции на 6 разных слайдах — гарантированно перекроет данные.

### 7. SRT remapping под jump-cut timeline

Whisper timestamps относительны исходного видео (55s). После jump-cut длительность другая (46s). Нужен пересчёт:

```bash
python3 scripts/remap-srt-to-jumpcut.py \
  --silence "$WORK/transcript/silence-parsed.json" \
  --input "$WORK/transcript/audio_corrected.srt" \
  --output "$WORK/transcript/audio_jumpcut.srt"
```

### 8. Burn-in subtitles + loudness norm

```bash
ffmpeg -y -i "$WORK/output/v1_pilot_v4_strategy_d.mp4" \
  -vf "subtitles=$WORK/transcript/audio_jumpcut.srt:force_style='FontName=Arial,FontSize=24,PrimaryColour=&Hffffff,OutlineColour=&H000000,BackColour=&H80000000,BorderStyle=4,Outline=8,Shadow=0,Alignment=2,MarginL=80,MarginR=80,MarginV=900,Bold=1,WrapStyle=0'" \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11" \
  -c:v libx264 -preset fast -crf 20 \
  -c:a aac -b:a 192k \
  "$WORK/output/v1_pilot_FINAL.mp4"
```

**Параметры subtitles (зафиксированы Антоном):**
- `FontSize=24` — не 36 (огромные, перекрывают)
- `BorderStyle=4` + `Outline=8` — полупрозрачный box backdrop
- `Alignment=2` + `MarginV=900` — НАД PiP (PiP top=1480, sub bottom=1920-900=1020)
- `MarginL=80, MarginR=80, WrapStyle=0` — wrap по ширине

## Стандарт композиции (зафиксировано 2026-05-12)

### Brand
- Извлечь палитру/шрифт/лого с сайта клиента ИЛИ нашего (artvision.pro)
- См. `/Users/antonk/.claude/rules/design-profile-routing.md` для выбора стиля

### PiP frame
- Размер: **320×400** (4:5 ratio), компактнее чем 380×480 (был "детский монтаж" по Антону)
- Border: **3px** white (НЕ 5+ — стримерский look)
- Border-radius: **20px** (subtle, professional)
- Box-shadow: `0 8px 32px rgba(0,0,0,0.35), 0 0 0 1px rgba(0,0,0,0.12)` (soft)
- НЕ применять `transform: scale()` или `object-position` — crop делает ffmpeg

### B-roll PNG
- Размер: 1080×1920 (vertical 9:16)
- ОБЯЗАТЕЛЬНО оставлять safe-zone в углах для PiP (см. таблицу)
- Источники цифр — реальные (Backlinko, SISTRIX, etc), со ссылкой в подписи

### Скриншоты SERP
- **Только Яндекс**, не Google. Google Ads ушёл из России в 2022.
- При SmartCaptcha — HTML mock через ui-designer agent (см. seg3.html / seg5.html прецеденты)
- Актуальный логотип Яндекса в 2024-26: **красный** #fc3f1d (не жёлтый, жёлтый только на главной)

### Логотип Artvision
- Файлы: `/Users/antonk/artvision-data/personal/social_clips/.../brand/logo_artvision_dark.png`
- Top-right, 220px ширина, opacity 0.85, drop-shadow

### Captions
- Whisper small RU с word_timestamps=True
- Чистка SEO-терминов через `templates/whisper-russian-corrections.json`
- Burn-in после рендера через ffmpeg `subtitles=` filter

### Audio
- Loudness norm `-14 LUFS` (YouTube стандарт)
- AAC 192kbps

## Помощники

- `scripts/clean-whisper-srt.py` — чистка SRT
- `scripts/jumpcut.py` — silence detect + concat-demuxer cut
- `scripts/remap-srt-to-jumpcut.py` — пересчёт SRT таймстемпов
- `scripts/burn-and-normalize.sh` — финальный burn-in + LUFS
- `templates/composition.html` — HyperFrames index.html шаблон
- `templates/whisper-russian-corrections.json` — словарь корректировок
- `templates/timeline.json` — JSON-конфиг для timeline сегментов

## Что узнали (lessons learned)

1. **Whisper medium часто фейлит SHA-checksum** при перекачке → использовать small (461 МБ) для русского
2. **filter_complex select на 4K@60fps HEVC часто отдаёт пустой mp4** → concat-demuxer на 1080p proxy надёжнее
3. **CSS transform scale + object-position** = "детский монтаж" → pre-crop ffmpeg выглядит профессионально
4. **PiP в одной позиции** = гарантированно перекрывает что-то → динамическая позиция через GSAP
5. **Data money-shot слайды** (графики, ТОП-X) → лучше **fade-out PiP** на 3-4 сек, дать данным экран
6. **PiP размер 380×480** = большой и навязчивый → **320×400** оптимально для educational
7. **Subtitles FontSize 36** = огромные, перекрывают → **24 + WrapStyle 0 + BackColour box**
8. **Jump-cut threshold 0.3s** = слишком резко (>200 WPM на русском) → 0.35-0.5s
9. **Antоn audio loudness** часто тише YouTube → loudnorm `-14 LUFS` обязательно
10. **SmartCaptcha на Яндексе** часто блокирует Playwright → HTML mock через ui-designer agent

## Trending music strategy (Антон 2026-05-12)

**Принцип:** один файл 1080×1920 → загружаем во все 4 платформы → на каждой добавляем СВОЙ trending sound из library платформы.

### Лучший путь (legal, free, trending)

1. **YouTube Shorts**: при загрузке в Shorts editor → Add sound → выбрать trending sound из YouTube Shorts library (лицензировано YouTube для Shorts, без claim)
2. **Instagram Reels**: в Reels editor → Audio → Trending → выбрать trending audio (лицензировано IG для Reels)
3. **TikTok**: при загрузке → выбрать trending sound из TikTok library
4. **VK Клипы**: добавить track из VK Music library

Каждая платформа автоматически продвигает видео с trending sound активнее — это в алгоритме.

### Источники trending (проверять ежедневно)

- [YouTube Shorts Top Songs Daily](https://charts.youtube.com/charts/TopShortsSongs/us/daily)
- [Shazam Top 200 Russia](https://www.shazam.com/charts/top-200/russia)
- [Shazam Top 50 Moscow](https://www.shazam.com/charts/top-50/russia/moscow)

### Если нужен background bed в видео (universal)

Royalty-free платформы (legal для монетизации):
- Uppbeat.io (free tier)
- Pixabay Music (полностью free)
- Bensound (no copyright claim)
- Chosic, YouTube Audio Library

Mix через ffmpeg на -22 dB под голос:
```bash
ffmpeg -i video.mp4 -i music.mp3 \
  -filter_complex "[1:a]volume=-22dB,aloop=loop=-1:size=2e9[bg];[0:a][bg]amix=inputs=2:duration=first[a]" \
  -map 0:v -map "[a]" -c:v copy output.mp4
```

### Антипаттерн

❌ **НЕ загружать Shazam-хит напрямую в видео** — copyright claim или demonetization. Только через platform-specific library.

## Multi-platform formats

Один файл 1080×1920 9:16 подходит для:
- ✅ YouTube Shorts (<60s)
- ✅ Instagram Reels (<90s, lately 3 min)
- ✅ TikTok (<10 min)
- ✅ VK Клипы (<3 min)
- ✅ Дзен Shorts

Делаем 1 файл, загружаем на 5 платформ — максимум reach без переделки.

## Связь с другими правилами

- `~/.claude/rules/no-smoothing.md` — честность при провалах (failed renders документировать)
- `~/.claude/rules/quality.md` — QA gates перед deploy
- `~/.claude/rules/design-profile-routing.md` — выбор дизайн-стиля под клиента
- `~/.claude/rules/recipient-personalization.md` — если контент адресный
- skill `audio-normalize` — для отдельной нормализации

## Прецедент

**Pilot Видео 1 «CTR теория» (12.05.2026):**
- IMG_9893 2.MOV (55.35s) → v1_pilot_v4_final.mp4 (46.18s, 6.3 МБ)
- 6 B-roll кадров через 2 параллельных Opus агента ($1.5)
- Консилиум из 3 моделей (round_table) + 2 Opus агентов для решения overlap
- 4 итерации композиции (детский → PiP basic → PiP fixed → Strategy D dynamic)

Подробный лог: `~/artvision-data/personal/social_clips/2026-05-12-research-video/`
