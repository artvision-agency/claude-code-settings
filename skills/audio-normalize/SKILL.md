---
name: audio-normalize
description: Финальная нормализация и проверка звука в видео перед публикацией. Выравнивает уровни громкости между клипами через EBU R128 loudnorm (стандарт TikTok/IG/YouTube Shorts = -14 LUFS), проверяет что речь слышна (mean RMS в речевых участках), отсутствие тишины в последних 200мс (не обрезаны слова), отсутствие клиппинга (max peak < -1 dBTP). Триггеры — 'проверь звук', 'нормализуй звук', 'audio check', 'звук тихий', 'разные уровни громкости', 'loudnorm', 'LUFS'.
---

# audio-normalize — финальный звуковой QA

## Когда использовать
- Финал монтажа перед отправкой клиенту / публикацией
- Склеил клипы из разных источников с разной громкостью
- Заметил что последние слова "проглочены" / тишина в конце
- Звук из одного клипа громче другого

## Что делает

1. **Измеряет** текущие LUFS / true peak / LRA каждого файла
2. **Нормализует** к -14 LUFS (TikTok/IG Reels/YouTube Shorts) или -16 LUFS (YouTube основной)
3. **Проверяет**:
   - Integrated loudness на целевом уровне ±1 LU
   - True peak < -1 dBTP (нет клиппинга)
   - Последние 200 мс: если RMS падает лесенкой (-40 → -60 → -inf) = естественный хвост; если плоский (-20 → -20 → -20 → резко -inf) = обрезано слово → REJECT
4. **Добавляет fade-out** 150мс на финальный клип чтобы замаскировать любой chop

## Основные команды

```bash
# Измерить LUFS
ffmpeg -i input.mp4 -af "loudnorm=I=-14:print_format=summary" -f null - 2>&1 | grep "Input Integrated"

# 1-pass нормализация (быстро, достаточно для мемов)
ffmpeg -y -i input.mp4 -af "loudnorm=I=-14:TP=-1.5:LRA=11" \
  -c:v copy -c:a aac -b:a 192k -ar 48000 -ac 2 output.mp4

# 2-pass нормализация (точнее, для клиента / продакшн)
# Pass 1: measure
MEAS=$(ffmpeg -i input.mp4 -af "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json" -f null - 2>&1 | \
  python3 -c "import sys,re,json; txt=sys.stdin.read(); m=re.search(r'\{[^{}]*input_i[^{}]*\}',txt,re.DOTALL); print(m.group(0))")
I=$(echo "$MEAS" | python3 -c "import json,sys; print(json.load(sys.stdin)['input_i'])")
TP=$(echo "$MEAS" | python3 -c "import json,sys; print(json.load(sys.stdin)['input_tp'])")
LRA=$(echo "$MEAS" | python3 -c "import json,sys; print(json.load(sys.stdin)['input_lra'])")
THR=$(echo "$MEAS" | python3 -c "import json,sys; print(json.load(sys.stdin)['input_thresh'])")
# Pass 2: apply
ffmpeg -y -i input.mp4 \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11:measured_I=$I:measured_TP=$TP:measured_LRA=$LRA:measured_thresh=$THR:linear=true" \
  -c:v copy -c:a aac -b:a 192k output.mp4

# Финальная проверка уровня
ffmpeg -i output.mp4 -af "volumedetect" -f null - 2>&1 | grep -E "mean_volume|max_volume"

# Проверка последних 0.5 сек (не обрезано ли слово)
ffmpeg -i output.mp4 -ss END-0.5 -af "asetnsamples=n=4800,astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level" \
  -f null - 2>&1 | grep RMS_level
# Правильный хвост: -40 → -55 → -70 → -inf (монотонное убывание)
# Обрезанное слово: -25 → -25 → -25 → резкое -inf

# Fade-out последних 150 мс (insurance)
ffmpeg -y -i input.mp4 -af "afade=t=out:st=$(echo "$TOTAL_DUR - 0.15" | bc):d=0.15" \
  -c:v copy output_faded.mp4
```

## Таблица стандартов

| Платформа | Target LUFS | True Peak |
|-----------|-------------|-----------|
| TikTok / IG Reels / YT Shorts | **-14** | -1 dBTP |
| YouTube (основной) | -14 | -1 dBTP |
| Spotify / Apple Music | -14 | -1 dBTP |
| Broadcast TV (EBU R128) | -23 | -1 dBTP |
| Podcast (Apple) | -16 | -1 dBTP |

## Автоматический agent-wrapper

Использовать `general-purpose` агент с промптом:
```
File: {path}. 
Target: -14 LUFS, TP -1.5. 
Verify: (1) Integrated ±1 LU of target, (2) max < -1 dBTP, (3) last 200ms shows natural decay (not hard cut mid-speech), (4) no silence gaps > 300ms in middle.
Return VERDICT: ACCEPT / REJECT with specific dB measurements.
```

## История

- **2026-04-18:** Создан после инцидента с монтажом Галустян+Мастерская Электро. Варианты A/B/C имели разные LUFS (-23/-22/-23). Нормализация вывела все к -14 ±0.9 LU.
