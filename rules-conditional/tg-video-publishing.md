---
name: tg-video-publishing
paths:
  - 'personal/social_clips/**'
  - '**/social_clips/**'
  - 'clients/**/ads/**'
  - '**/*video*'
  - '**/*shorts*'
always: false
---

# TG Video Publishing — обязательные правила (каналы / сторис / личка)

> **Установлено:** 2026-05-30 (сессия 5498b74b, после потери времени на CRF 27/28 и неверной гипотезы про supports_streaming).
> **Цель:** будущие сессии автоматически выдавать качественное TG-видео + автоплей с первого раза, не повторять мои ошибки.
> **Связано:** `shorts-pip-composition.md` (создание видео), memory `feedback_tg_channel_autoplay_rules.md`, memory `reference_tg_user_stories_telethon.md`, скрипты `~/artvision-data/scripts/tg_send_video_streaming.sh` и `tg_post_user_stories.py`.

## TL;DR — что делать всегда

| Назначение | Размер | Resolution | Encoder | Кому слать |
|---|---|---|---|---|
| Канал (autoplay в ленте) | **<10 MB** | 720×1280 | x264 slower 2-pass tuned | Bot API sendVideo |
| User stories | **<30 MB** | 1080×1920 | x264 slow CRF 18 (max качество) | Telethon SendStoryRequest |
| Личка/group для проверки | как канал | как канал | как канал | Bot API sendVideo |
| Архив/важный документ | 1080p оригинал | оригинал | оригинал | Bot API sendDocument (не sendVideo!) |

## 🔴 КОРЕНЬ качества (2026-06-11, после 6 провальных encode-попыток + 2 workflow в петле)

**Истинная причина «текст мыло <10MB» — НЕ psy-rd/tune/resolution, а РЕЖИМ кодирования + ДЛИНА.**

1. **CRF (постоянное качество), НЕ ABR 2-pass fixed-bitrate, для смешанного motion+screenshot контента.** ABR с жёстким cap (`-b:v 1400k -maxrate`) душит сложные кадры (talking head + анимация + скриншот в один момент) — они получают «среднее» и текст превращается в мыло. CRF даёт каждому участку столько битрейта, сколько нужно. Проверено: t=18 (скриншот рядом с motion) — ABR 1.5 Mbps = мыло, **CRF 20 = читаемо как оригинал**.
2. **CRF 20 раскрывает истинный спрос на битрейт по секциям:**
   - motion/интро/talking head: ~3.5 Mbps (сложно сжать)
   - статичные текст-панели (скриншоты): ~1.0 Mbps (сжимается крошечной и резкой при CRF — постоянное качество)
3. **Арифметика, которую не обойти:** читаемое качество ≈ 2 Mbps усреднённо. Клип >~38с при 2 Mbps НЕ влезет под 10 MB. Никакой x264-tune этого не меняет — это длина×битрейт.
4. **РЕШЕНИЕ для клипа >38с: РАЗБИТЬ на 2 части по речевой паузе** (`silencedetect=n=-25dB:d=0.15` → точка реза ближе к середине), каждую кодировать **CRF 20 1080p**. Обе части автоплеят (<10MB) И читаемы. Прецедент V1: 48.7с → part1 0–21.3с (CRF20, 9.5MB, читаемо) + part2 21.3–48.7с (CRF20, 3.7MB, читаемо). Бонус: 2 поста = свежесть в ленте.
5. **Команда CRF-split (эталон):**
   ```bash
   CUT=$(речевая пауза ближе к середине из silencedetect)
   ffmpeg -y -i in.mp4 -t $CUT -c:v libx264 -preset slow -crf 20 -pix_fmt yuv420p \
     -profile:v high -movflags +faststart -c:a aac -b:a 128k part1.mp4
   ffmpeg -y -ss $CUT -i in.mp4 -c:v libx264 -preset slow -crf 20 -pix_fmt yuv420p \
     -profile:v high -movflags +faststart -c:a aac -b:a 128k part2.mp4
   # verify КАЖДУЮ часть глазами: ffmpeg -ss <screenshot-sec> -i partN.mp4 -vframes 1 frame.jpg && Read frame.jpg
   ```
6. **Долгосрочно (root content fix):** скриншоты Яндекс-выдачи с body-текстом — hardest-case. Но при CRF (не ABR) они держатся даже при 1 Mbps. Проблема была НЕ в контенте (источник 14MB резкий), а в режиме encode. Пересборка B-roll с крупным текстом — приятный бонус, но НЕ обязательна раз CRF решает.

> **Урок петли:** handover-author 6 раз варьировал psy-rd/tune/CAS/unsharp/720-vs-1080 **внутри ABR-режима** и объявлял «физический предел». Смена УГЛА (CRF + split) решила за 2 encode. `visual-content-not-just-ratio.md` R3: если 6× повтор и «предел» — метод слеп, менять класс решения, не параметры.

## Жёсткие факты (НЕ обсуждаются)

1. **Канал autoplay = ВСЕГДА muted by design.** Звук — только по тапу. Anti-spam политика клиента TG. Никаким флагом, никаким Premium, никаким Boost этого не обойти.
2. **Порог autoplay в канале = 10 MB.** Hard-coded в клиентах TG (Medium auto-download preset, default на mobile). Файлы 11-15 MB не автоплеят даже с включённым autoplay у юзера.
3. **`supports_streaming=null` в response Bot API video object — НОРМА.** Поле не в схеме ответа, только входной параметр sendVideo. **НЕ доказательство** что флаг не работает. Проверять автоплей надо ВИЗУАЛЬНО на mobile.
4. **HEVC (x265) НЕ работает в TG** — известный bug: autoplay не triggerится, на Android чёрный экран и шум вместо звука. **НЕ использовать x265 для TG.**
5. **AV1 НЕ работает в TG** — на iOS до сих пор не показывает, на Desktop — чёрный экран. **НЕ использовать AV1 для TG.**
6. **VP9 / WebM** — TG не принимает (только mp4 контейнер).
7. **Channel Boost / Premium НЕ снимает 10 MB autoplay порог.** Boost даёт сторис/реакции; Premium даёт 4 GB upload лимит (отправки, не autoplay). **НЕ тратить деньги на boost ради автоплея.**
8. **TG user stories — только Telethon (MTProto).** Bot API `postStory` существует с 2024 но только для каналов где бот админ, не для личных stories пользователя. Для личных сторис — `client.upload_file` + `SendStoryRequest`.
9. **TG stories cover — через `video_start_ts` в `DocumentAttributeVideo`, не отдельный thumb-файл.** Указываешь секунду — TG берёт frame оттуда для preview.
10. **TG Premium у user = лимит сторис 60s (без Premium 15s).** Pre-check перед постингом длинного видео.

## Pre-flight файла перед заливкой в КАНАЛ

```bash
ffprobe -v error \
  -show_entries format=size,duration,bit_rate \
  -show_entries stream=codec_name,profile,pix_fmt,width,height \
  -of default=noprint_wrappers=1 input.mp4
```

Должно быть:
- `size < 10485760` (10 MB)
- `codec_name=h264`, `profile=High`, `pix_fmt=yuv420p`
- `width=720, height=1280` ИЛИ `1080×1920` (но 720 даёт лучше качество per byte)
- moov atom в начале (faststart)
- audio AAC, 44.1/48 kHz, stereo

## Encoder profile (TOP-1 — deep workflow research 2026-05-30, 9 agents)

**Используй готовый скрипт:** `~/artvision-data/scripts/tg_publish.sh <input.mp4>` создаёт оба tier + thumbs + verify.

**КЛЮЧЕВЫЕ DIFF от ранних ошибок CRF 27/28 и MEDIA_FILE_INVALID:**
- `-profile:v main` (НЕ `high` — Stories validator строже Bot API)
- `-force_key_frames "expr:gte(t,0)"` — первый кадр обязательно keyframe
- `-g 30/60 -keyint_min -sc_threshold 0` — closed GOP, без scene-cut keyframes
- `-x264-params "no-scenecut=1"` для stories
- `-map_metadata -1` — срезать metadata прошлого encoder
- `-color_primaries bt709 -color_trc bt709 -colorspace bt709` — явный colorspace signaling

### TIER 1 — Канал (≤10 MB autoplay, two-pass target bitrate)

```bash
# Bitrate: 1400k для ≤50s, 1250k для 51-60s. Audio 96k AAC.
BV=1400  # или 1250
MR=$((BV + 200))
BS=$((BV * 2))

ffmpeg -y -i in.mp4 -vf "scale=720:1280:flags=lanczos" \
  -c:v libx264 -preset slow -profile:v main -level:v 4.0 \
  -b:v ${BV}k -maxrate ${MR}k -bufsize ${BS}k \
  -pix_fmt yuv420p -r 30 -g 60 -keyint_min 60 -sc_threshold 0 \
  -force_key_frames "expr:gte(t,0)" \
  -color_primaries bt709 -color_trc bt709 -colorspace bt709 \
  -pass 1 -an -f mp4 /dev/null

ffmpeg -y -i in.mp4 -vf "scale=720:1280:flags=lanczos" \
  -c:v libx264 -preset slow -profile:v main -level:v 4.0 \
  -b:v ${BV}k -maxrate ${MR}k -bufsize ${BS}k \
  -pix_fmt yuv420p -r 30 -g 60 -keyint_min 60 -sc_threshold 0 \
  -force_key_frames "expr:gte(t,0)" \
  -color_primaries bt709 -color_trc bt709 -colorspace bt709 \
  -pass 2 -c:a aac -b:a 96k -ar 48000 -ac 2 \
  -movflags +faststart -map_metadata -1 \
  out_channel.mp4

rm -f ffmpeg2pass-*.log*
ffmpeg -y -ss 2 -i out_channel.mp4 -vframes 1 -vf "scale=320:-2" -q:v 2 thumb.jpg
```

**Bitrate расчёт (для других длительностей):**
```
target_size_bits = 9.5 MB × 8 × 1024 × 1024 = 79.7 Mbit
audio_bits = 128k × duration_s
video_bits = (target_size_bits - audio_bits) / duration_s
```

**Почему 720p а не 1080p:**
- Telegram-feed превью рендерит ~360-540p всё равно (phone screen)
- 720×1280 при 1300k = **1.13 bits per pixel**
- 1080×1920 при 1300k = **0.32 bits per pixel** (в 3× меньше → мыло)
- Визуально 720p в feed неотличим от 1080p

### TIER 2 — Stories (Telethon, CRF 18 visually lossless, target ≤25 MB)

**Прецедент 2026-05-30:** мой CRF 18 + profile=high дал 15 MB и MEDIA_FILE_INVALID. Причина — Stories validator строже Bot API: требует profile=main, первый кадр keyframe, нет scene-cut, нет mismatched metadata.

```bash
ffmpeg -y -i in.mp4 \
  -c:v libx264 -preset slow -profile:v main -level:v 4.0 \
  -crf 18 -pix_fmt yuv420p -r 30 \
  -g 30 -keyint_min 30 -sc_threshold 0 \
  -force_key_frames "expr:gte(t,0)" \
  -x264-params "no-scenecut=1" \
  -color_primaries bt709 -color_trc bt709 -colorspace bt709 \
  -c:a aac -b:a 128k -ar 48000 -ac 2 \
  -movflags +faststart -map_metadata -1 \
  out_story.mp4

# Если размер > 25 MB → fallback CRF 20 (subjective lossless для talking head, экономия ~30%)
```

## Запретный список (что НЕ делать)

- ❌ CRF 25-28 на 1080p → мыло. Если нужен 1080p — `-b:v 1700k -maxrate 2000k` с 2-pass.
- ❌ `-preset fast` на финал → потеря 5-10% качества при том же размере. Только `slow` или `slower`.
- ❌ x265 / HEVC / AV1 для TG → autoplay не работает.
- ❌ WebM / VP9 → TG не принимает.
- ❌ 96 kHz audio sample rate → нестандарт, лучше 44.1 / 48 kHz.
- ❌ Audio 256k+ → перерасход места. 128k AAC LC достаточно для голоса; 192k для музыки.
- ❌ Полагаться на `response.video.supports_streaming` для проверки флага → поле не в схеме ответа.
- ❌ Тратить boost-stars на канал ради autoplay → не работает.
- ❌ Постить видео >15s в user stories без подтверждения Premium → API упадёт.
- ❌ Sending видео через `sendAnimation` со звуком → TG переклассифицирует обратно в video (animation требует БЕЗ audio track).
- ❌ Залить .mp4 через TG UI «Send as file» → отключит плеер, будет document с downloadable иконкой.

## Workflow по умолчанию (для будущих сессий)

1. **Видео готов в высоком качестве** (CRF 16 1080p из shorts-pipeline pipeline).
2. **Опубликовать на YouTube** (`/youtube-publish`) — оригинальный 1080p со звуком.
3. **Перекодировать в TG-канал profile** (720p slower 2-pass tuned, <10 MB).
4. **Bot API sendVideo** через `~/artvision-data/scripts/tg_send_video_streaming.sh`.
5. **(Опционально) Перекодировать в TG-stories profile** (1080p CRF 18, ≤30 MB).
6. **Telethon SendStoryRequest** через `~/artvision-data/scripts/tg_post_user_stories.py` с `video_start_ts` для cover.

## Скрипты-эталоны

| Скрипт | Назначение |
|---|---|
| `~/artvision-data/scripts/tg_send_video_streaming.sh` | Bot API sendVideo с pre-flight 10MB check + thumb + supports_streaming + --http1.1 retry |
| `~/artvision-data/scripts/tg_post_user_stories.py` | Telethon SendStoryRequest для user stories с video_start_ts cover |
| `~/.claude/skills/shorts-pip-composer/` | Создание PiP-композитного видео (вход для всего этого pipeline) |

## Кандидат-хук (TBD, ждёт approve)

`pre-tg-publish-encoding-check.sh` — PreToolUse Bash на `*/tg_send_video*.sh|/curl.*sendVideo`:
- Проверяет файл через ffprobe
- Если size > 10 MB **и** target = канал (chat_id отрицательный с префиксом -100): WARN «не автоплей в канале, перекодировать в 720p?»
- Если codec_name != h264 ИЛИ profile != High: BLOCK
- Если pix_fmt != yuv420p: BLOCK
- Bypass: `TG_PUBLISH_OK=1`

Не зарегистрирован — нужен явный approve Антона.

## Прецедент полный (2026-05-30, 5498b74b)

- V1 49s 14MB (оригинал CRF 16 slow) — НЕ автоплеит в канале (за порогом 10 MB)
- Ошибка #1: думал проблема в флаге supports_streaming (response=null) → впустую перезаливал с разными форматами флага. Реально флаг работал всё время.
- Ошибка #2: перекодировал CRF 27/28 на 1080p → 4 MB но мыло. Антон: «очень низкое качество!!!».
- Ошибка #3: пытался CRF 22 2-pass на 1080p → 8.3 MB лучше, но всё ещё 1080p compressed.
- Senior research исправил: 720p downscale + 1300k 2-pass + tuned x264-params + tune=film → 9.5 MB, качество 8.5/10. Bits per pixel в 3× больше.
- Также: HEVC/AV1 в TG broken, Boost не снимает порог — это окончательно. Не пробовать.
