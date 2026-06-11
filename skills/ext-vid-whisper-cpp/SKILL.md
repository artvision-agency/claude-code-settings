---
name: ext-vid-whisper-cpp
description: External CPU-port of Whisper (ggml-org/whisper.cpp, 49K⭐ MIT). C/C++ port for fast inference on CPU only (no GPU). Use on VPS without GPU, batch transcription, embedded scenarios. Triggers — 'whisper cpp', 'whisper vps', 'cpu transcribe', 'whisper.cpp', 'fast whisper cpu', 'ext-vid-whisper-cpp'.
---

# ext-vid-whisper-cpp — Whisper CPU port

**Upstream:** github.com/artvision-agency/whisper.cpp ← ggml-org/whisper.cpp (49K⭐, MIT)
**Category:** Video / Creative
**Use case:** Whisper transcription **без GPU** — для VPS, batch-обработки, embedded.

## Когда вызывать

- На нашем VPS (нет GPU) — заменить платный Whisper API
- Batch-обработка большого количества аудио без GPU-аккаунта
- Когда нужна меньшая память (quantized ggml модели)

## Как пользоваться

```bash
gh repo clone artvision-agency/whisper.cpp ~/forks/whisper.cpp
cd ~/forks/whisper.cpp && make
# Скачать модель
./models/download-ggml-model.sh medium
# Транскрипция:
./main -m models/ggml-medium.bin -f audio.wav --language ru --output-srt
```

## A/B vs `ext-vid-whisper` (Python)

- whisper.cpp быстрее на CPU x2-5
- Python whisper удобнее интегрировать в pipeline
- Метрика: time per minute audio, output quality

## Использование в `shorts-pip-composer`

Заменить вызов OpenAI Whisper API на `whisper.cpp` через subprocess. Экономия $cost.

## Связанные

- GPU-вариант: `ext-vid-whisper`
- Research: `~/artvision-data/research/2026-05-20-agency-tools-discovery/06-video-creative.md`
