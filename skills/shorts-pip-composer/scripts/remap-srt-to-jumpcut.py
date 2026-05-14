#!/usr/bin/env python3
"""
Remap SRT timestamps from original video to jump-cut timeline.

Whisper transcript timestamps are relative to the FULL source video.
After jump-cut (silence removed), the duration changes — SRT must be remapped
so subtitles sync with the new, shorter video.

Method:
  - Read silence-parsed.json (output of jumpcut.py with --save-segments-json)
  - For each SRT entry, map raw_t → cut_t using the speak_segments mapping
  - Skip entries entirely in pauses

Usage:
  python3 remap-srt-to-jumpcut.py \\
    --silence silence-parsed.json \\
    --input audio_corrected.srt \\
    --output audio_jumpcut.srt
"""
import argparse, json, pathlib, re

def srt_to_sec(t):
    h, m, rest = t.split(':')
    s, ms = rest.split(',')
    return int(h)*3600 + int(m)*60 + int(s) + int(ms)/1000.0

def sec_to_srt(t):
    if t < 0: t = 0
    h = int(t // 3600); t -= h*3600
    m = int(t // 60); t -= m*60
    s = int(t); ms = int(round((t-s)*1000))
    if ms >= 1000: s += 1; ms -= 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def make_raw_to_cut(speak_segments):
    """Returns function raw_t -> cut_t (or None if in pause)."""
    def fn(raw_t):
        cum = 0.0
        for s in speak_segments:
            if raw_t < s['start']:
                return None
            if raw_t <= s['end']:
                return cum + (raw_t - s['start'])
            cum += s['dur']
        return None
    return fn

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--silence", required=True, help="silence-parsed.json from jumpcut.py")
    ap.add_argument("--input", required=True, help="Source SRT")
    ap.add_argument("--output", required=True, help="Output remapped SRT")
    args = ap.parse_args()

    silence = json.loads(pathlib.Path(args.silence).read_text())
    speak = silence["speak_segments"]
    raw_to_cut = make_raw_to_cut(speak)

    src = pathlib.Path(args.input).read_text()
    blocks = re.split(r'\n\n+', src.strip())

    out_entries = []
    new_idx = 1
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3: continue
        m = re.match(r'(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})', lines[1])
        if not m: continue
        start = srt_to_sec(m.group(1))
        end = srt_to_sec(m.group(2))
        text = '\n'.join(lines[2:])

        cs = raw_to_cut(start)
        ce = raw_to_cut(end)
        if cs is None and ce is None:
            continue
        if cs is None:
            for nudge in [0.1, 0.2, 0.3]:
                cs = raw_to_cut(start + nudge)
                if cs is not None: break
            cs = cs or 0
        if ce is None:
            for back in [0.1, 0.3, 0.5, 0.8]:
                ce = raw_to_cut(end - back)
                if ce is not None: break
        if cs is None or ce is None or ce <= cs:
            continue
        out_entries.append(f"{new_idx}\n{sec_to_srt(cs)} --> {sec_to_srt(ce)}\n{text}\n")
        new_idx += 1

    pathlib.Path(args.output).write_text("\n".join(out_entries))
    print(f"✅ Remapped {len(blocks)} → {len(out_entries)} SRT entries → {args.output}")

if __name__ == "__main__":
    main()
