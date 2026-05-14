#!/usr/bin/env python3
"""
Convert SRT to ASS with proper PlayResX/Y=1080×1920 for vertical Shorts.

WHY: ffmpeg `subtitles=...:force_style=` filter on SRT files uses libass's
default PlayRes (384×288), which causes font size to scale incorrectly
on vertical 1080×1920 video. Converting to ASS with explicit PlayRes
gives predictable pixel-accurate rendering.

Default style (zero-config — Антон 2026-05-12):
  - Arial 40px Bold
  - White text (#FFFFFF) on semi-transparent black box (alpha BE)
  - Outline 8, BorderStyle=4 (opaque box)
  - Alignment=2 (bottom-center)
  - MarginV=540 (positioned above PiP, below B-roll content)
  - Smart wrap (WrapStyle=0)
"""
import argparse, re, pathlib

ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{size},&H00FFFFFF,&H000000FF,&H00000000,&HBE000000,1,0,0,0,100,100,0,0,4,8,0,2,{ml},{mr},{mv},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

def srt_time_to_ass(t):
    h, m, rest = t.split(':')
    sec, ms = rest.split(',')
    return f"{int(h)}:{m}:{sec}.{int(ms)//10:02d}"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Source SRT")
    ap.add_argument("--output", required=True, help="Output ASS")
    ap.add_argument("--font", default="Arial")
    ap.add_argument("--size", type=int, default=40)
    ap.add_argument("--margin-v", type=int, default=540,
                    help="Bottom margin (default 540 — above PiP)")
    ap.add_argument("--margin-l", type=int, default=80)
    ap.add_argument("--margin-r", type=int, default=80)
    args = ap.parse_args()

    src = pathlib.Path(args.input).read_text()
    blocks = re.split(r'\n\n+', src.strip())

    lines = []
    for block in blocks:
        parts = block.strip().split('\n')
        if len(parts) < 3:
            continue
        m = re.match(r'(\S+)\s*-->\s*(\S+)', parts[1])
        if not m:
            continue
        start = srt_time_to_ass(m.group(1))
        end = srt_time_to_ass(m.group(2))
        text = ' '.join(parts[2:]).replace('\n', '\\N')
        lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")

    header = ASS_HEADER.format(
        font=args.font, size=args.size,
        ml=args.margin_l, mr=args.margin_r, mv=args.margin_v
    )
    pathlib.Path(args.output).write_text(header + '\n'.join(lines) + '\n')
    print(f"✅ {args.output} ({len(lines)} entries, {args.size}px {args.font}, MarginV={args.margin_v})")

if __name__ == "__main__":
    main()
