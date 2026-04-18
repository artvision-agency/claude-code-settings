#!/usr/bin/env python3
"""
voice_listener.py — MVP голосового управления Claude Code.

Stack: sounddevice (mic capture) + Silero VAD (voice activity detection,
local/offline) + Groq Whisper API (STT, Russian).

Flow:
  1. Continuously listen from mic in small chunks (512 samples @ 16kHz).
  2. Silero VAD detects when speech starts/ends → buffers the utterance.
  3. After speech ends, send buffered audio to Groq Whisper (Russian).
  4. Check transcript for wake word "эй клод" / "привет клод" / "клод".
  5. If wake word found → next utterance is the COMMAND → transcribe,
     write to ~/.claude/voice/command.log and print to stdout.

MVP scope: prints recognized commands to stdout. No Claude integration yet —
that's the next task.

Run: ./venv/bin/python voice_listener.py
Stop: Ctrl-C
"""

from __future__ import annotations

import argparse
import io
import json
import os
import queue
import signal
import subprocess
import sys
import time
import wave
from datetime import datetime
from pathlib import Path

import numpy as np
import sounddevice as sd
import torch
from groq import Groq
from silero_vad import load_silero_vad

# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------
SAMPLE_RATE = 16000            # Silero VAD requires 16kHz
FRAME_MS = 32                  # 32ms frames → 512 samples @ 16kHz (VAD native)
FRAME_SAMPLES = int(SAMPLE_RATE * FRAME_MS / 1000)
VAD_THRESHOLD = 0.5            # 0..1, higher = less sensitive
SILENCE_MS_END = 700           # ms of silence to consider utterance ended
MIN_UTTERANCE_MS = 300         # skip utterances shorter than this
MAX_UTTERANCE_MS = 15000       # hard cap to avoid runaway buffers
COMMAND_MAX_MS = 20000         # longer for actual commands (after wake word)

WAKE_WORDS = [
    "эй клод", "эй клоуд", "эй код",
    "привет клод", "привет клоуд",
    "hey claude", "hey clod",
]

TOKENS_PATH = Path.home() / "artvision-data" / "tokens.json"
LOG_DIR = Path.home() / ".claude" / "voice"
LOG_DIR.mkdir(parents=True, exist_ok=True)
COMMAND_LOG = LOG_DIR / "command.log"
DEBUG_LOG = LOG_DIR / "debug.log"

GROQ_MODEL = "whisper-large-v3-turbo"  # faster than v3, same quality for RU


# -----------------------------------------------------------------------------
# Mic selection
# -----------------------------------------------------------------------------
def resolve_mic(selector: str | None) -> int | None:
    """Resolve mic selector to device index.

    - None → system default
    - digit → index
    - substring → first input device whose name contains it (case-insensitive)
    """
    if selector is None:
        return None
    if selector.isdigit():
        return int(selector)
    low = selector.lower()
    for i, d in enumerate(sd.query_devices()):
        if d["max_input_channels"] > 0 and low in d["name"].lower():
            return i
    raise SystemExit(f"No input device matches {selector!r}. Run list-mics.sh to see available.")


def describe_mic(index: int | None) -> str:
    if index is None:
        idx = sd.default.device[0] if sd.default.device else None
        if idx is None:
            return "<system default>"
        index = idx
    d = sd.query_devices(index)
    return f"[{index}] {d['name']} @ {int(d['default_samplerate'])}Hz"


# -----------------------------------------------------------------------------
# Send to terminal (frontmost app, via AppleScript)
# -----------------------------------------------------------------------------
APPLESCRIPT_SEND = r'''
on run argv
    set theText to item 1 of argv
    set theApp to (path to frontmost application as text)
    tell application "System Events"
        set frontApp to name of first process whose frontmost is true
    end tell
    if frontApp is "iTerm2" or frontApp is "iTerm" then
        tell application "iTerm"
            tell current session of current window
                write text theText
            end tell
        end tell
    else if frontApp is "Terminal" then
        tell application "Terminal"
            do script theText in front window
        end tell
    else
        -- Fallback: type the text into the frontmost app via keystrokes + Return
        tell application "System Events"
            keystroke theText
            key code 36  -- Return
        end tell
    end if
end run
'''


def send_to_frontmost_terminal(text: str) -> None:
    """Send text+Return to the frontmost Terminal/iTerm window."""
    try:
        subprocess.run(
            ["osascript", "-e", APPLESCRIPT_SEND, text],
            check=False,
            capture_output=True,
            timeout=5,
        )
    except Exception as e:  # noqa: BLE001
        log(f"osascript send failed: {e}", debug=True)

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
def log(msg: str, debug: bool = False) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    target = DEBUG_LOG if debug else COMMAND_LOG
    with target.open("a") as f:
        f.write(line + "\n")


# -----------------------------------------------------------------------------
# Groq client
# -----------------------------------------------------------------------------
def load_groq_key() -> str:
    if "GROQ_API_KEY" in os.environ:
        return os.environ["GROQ_API_KEY"]
    with TOKENS_PATH.open() as f:
        tokens = json.load(f)
    g = tokens.get("groq")
    if isinstance(g, dict):
        return g.get("api_key", "")
    return g or ""


def transcribe(audio_np: np.ndarray, client: Groq) -> str:
    """Send audio to Groq Whisper, return transcript (Russian)."""
    # Pack int16 PCM into WAV in-memory
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # int16
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes((audio_np * 32767).clip(-32768, 32767).astype(np.int16).tobytes())
    buf.seek(0)
    buf.name = "audio.wav"

    t0 = time.time()
    resp = client.audio.transcriptions.create(
        file=("audio.wav", buf.read()),
        model=GROQ_MODEL,
        language="ru",
        response_format="json",
        temperature=0.0,
    )
    dt = time.time() - t0
    text = (resp.text or "").strip()
    log(f"Groq {dt:.2f}s → {text!r}", debug=True)
    return text


# -----------------------------------------------------------------------------
# Wake word detection
# -----------------------------------------------------------------------------
def contains_wake_word(text: str) -> bool:
    low = text.lower().strip()
    # Strip common Whisper punctuation around the wake word
    for ch in ".,!?;:":
        low = low.replace(ch, " ")
    low = " ".join(low.split())
    return any(w in low for w in WAKE_WORDS)


def strip_wake_word(text: str) -> str:
    """If command text starts with a wake word, strip it."""
    low = text.lower().strip()
    for w in WAKE_WORDS:
        if low.startswith(w):
            return text[len(w):].lstrip(" ,.:!?")
    return text


# -----------------------------------------------------------------------------
# Main loop
# -----------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description="Voice listener for Claude Code")
    parser.add_argument("--mic", help="Input device: index or substring of name. Default = system default")
    parser.add_argument("--send", action="store_true", help="Send recognized commands to frontmost Terminal/iTerm window")
    parser.add_argument("--list-mics", action="store_true", help="List input devices and exit")
    args = parser.parse_args()

    if args.list_mics:
        print("Input devices:")
        default_in = sd.default.device[0] if sd.default.device else None
        for i, d in enumerate(sd.query_devices()):
            if d["max_input_channels"] > 0:
                mark = " (DEFAULT)" if i == default_in else ""
                print(f"  [{i}] {d['name']} — {int(d['default_samplerate'])}Hz{mark}")
        return 0

    mic_index = resolve_mic(args.mic)

    log("Loading Silero VAD...")
    vad = load_silero_vad()
    log("Connecting to Groq...")
    client = Groq(api_key=load_groq_key())
    log(f"Ready. Wake words: {WAKE_WORDS}")
    log(f"Mic: {describe_mic(mic_index)}")
    log(f"Send to terminal: {'ON' if args.send else 'OFF (stdout only)'}")

    audio_q: queue.Queue[np.ndarray] = queue.Queue()

    def audio_callback(indata, frames, time_info, status):
        if status:
            log(f"Audio status: {status}", debug=True)
        audio_q.put(indata[:, 0].copy())

    # State machine
    STATE_IDLE = "idle"
    STATE_RECORDING = "recording"
    state = STATE_IDLE
    awaiting_command = False  # True after wake word detected; next utterance = command

    utterance: list[np.ndarray] = []
    silent_frames = 0
    speech_frames = 0
    silence_threshold_frames = int(SILENCE_MS_END / FRAME_MS)
    min_utterance_frames = int(MIN_UTTERANCE_MS / FRAME_MS)

    stop_flag = {"stop": False}

    def on_sigint(signum, frame):
        stop_flag["stop"] = True
        log("Stopping...")

    signal.signal(signal.SIGINT, on_sigint)
    signal.signal(signal.SIGTERM, on_sigint)

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        blocksize=FRAME_SAMPLES,
        callback=audio_callback,
        device=mic_index,
    ):
        while not stop_flag["stop"]:
            try:
                frame = audio_q.get(timeout=0.2)
            except queue.Empty:
                continue

            # Silero expects exactly 512 samples at 16kHz
            if len(frame) != FRAME_SAMPLES:
                continue

            speech_prob = vad(torch.from_numpy(frame), SAMPLE_RATE).item()
            is_speech = speech_prob >= VAD_THRESHOLD

            if state == STATE_IDLE:
                if is_speech:
                    state = STATE_RECORDING
                    utterance = [frame]
                    silent_frames = 0
                    speech_frames = 1
            else:  # STATE_RECORDING
                utterance.append(frame)
                if is_speech:
                    speech_frames += 1
                    silent_frames = 0
                else:
                    silent_frames += 1

                total_ms = len(utterance) * FRAME_MS
                max_ms = COMMAND_MAX_MS if awaiting_command else MAX_UTTERANCE_MS

                # End of utterance?
                if silent_frames >= silence_threshold_frames or total_ms >= max_ms:
                    duration_ms = len(utterance) * FRAME_MS
                    if speech_frames >= min_utterance_frames:
                        audio_np = np.concatenate(utterance)
                        state = STATE_IDLE
                        utterance = []
                        silent_frames = 0
                        speech_frames = 0
                        try:
                            text = transcribe(audio_np, client)
                        except Exception as e:
                            log(f"Groq error: {e}", debug=True)
                            awaiting_command = False
                            continue

                        if not text:
                            continue

                        if awaiting_command:
                            command = strip_wake_word(text)
                            if command:
                                log(f"▶ COMMAND: {command}")
                                if args.send:
                                    send_to_frontmost_terminal(command)
                            awaiting_command = False
                        elif contains_wake_word(text):
                            # Wake word may come in the same utterance as the command
                            after = strip_wake_word(text)
                            if after:
                                log(f"▶ COMMAND (inline): {after}")
                                if args.send:
                                    send_to_frontmost_terminal(after)
                                awaiting_command = False
                            else:
                                log(f"✨ Wake word detected. Listening for command...")
                                awaiting_command = True
                        else:
                            # Not wake word, not command mode — ignore
                            log(f"  (ignored, {duration_ms}ms): {text}", debug=True)
                    else:
                        # Too short
                        state = STATE_IDLE
                        utterance = []
                        silent_frames = 0
                        speech_frames = 0

    log("Stopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
