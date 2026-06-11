---
name: ext-vid-whisper
description: External speech-to-text (openai/whisper, 99K⭐ MIT). Self-host alternative to OpenAI Whisper API. Use for transcribing client calls, video subtitles, podcast → shorts pipeline. Triggers — 'whisper local', 'whisper self-host', 'транскрипт локально', 'shorts subtitles', 'voiceover transcribe', 'ext-vid-whisper'.
---

# ext-vid-whisper — local Whisper transcription

**Upstream:** github.com/artvision-agency/whisper ← openai/whisper (99K⭐, MIT)
**Category:** Video / Creative
**Use case:** замена платного Whisper API через OpenAI. Local GPU transcription.

## Когда вызывать

- Длинные клиентские созвоны → транскрипт (для protocol → Asana)
- Subtitles для Shorts/Reels (наш `shorts-pip-composer` стек)
- Транскрипт voiceovers для проверки качества
- Massive batch transcription где OpenAI API дорого

## Как пользоваться

```bash
gh repo clone artvision-agency/whisper ~/forks/whisper
cd ~/forks/whisper && pip install -e .
# CLI:
whisper <audio.mp3> --model medium --language ru --output_dir /tmp/transcript
```

## A/B vs OpenAI Whisper API

- Метрика: WER (word error rate), $ cost, time
- Кейс: один созвон 30 мин — local vs API
- На M1/M2 Mac — `medium` модель ~real-time. На VPS — см. `ext-vid-whisper-cpp` (CPU-friendly)

## Связанные

- VPS-вариант: `ext-vid-whisper-cpp` (faster, CPU)
- Skill `shorts-pip-composer` — subtitle pipeline после транскрипта
- Research: `~/artvision-data/research/2026-05-20-agency-tools-discovery/06-video-creative.md`
