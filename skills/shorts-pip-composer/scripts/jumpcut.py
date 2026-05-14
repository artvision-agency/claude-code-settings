#!/usr/bin/env python3
"""
Jump-cut speech video by removing silence.

Method: ffmpeg silencedetect → speak segments → concat-demuxer.
WHY concat-demuxer instead of filter_complex select:
  - 4K@60fps HEVC + filter_complex select often outputs empty mp4
  - concat-demuxer is robust on 1080p proxy
  - 16x faster than re-encoding 4K

Usage:
  python3 jumpcut.py --input proxy.mp4 --threshold 0.5 --noise -30 \\
    --output speak_only.mp4
"""
import argparse, json, pathlib, subprocess, re, sys, tempfile

def detect_silence(input_path, threshold, noise_db):
    """Run ffmpeg silencedetect, return list of (start, end) silence tuples."""
    cmd = [
        "ffmpeg", "-i", str(input_path),
        "-af", f"silencedetect=noise={noise_db}dB:d={threshold}",
        "-f", "null", "-"
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    log = r.stderr
    starts = [float(m.group(1)) for m in re.finditer(r'silence_start: ([\d.]+)', log)]
    ends = [float(m.group(1)) for m in re.finditer(r'silence_end: ([\d.]+)', log)]
    return list(zip(starts, ends))

def probe_duration(input_path):
    r = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(input_path)
    ], capture_output=True, text=True)
    return float(r.stdout.strip())

def silence_to_speak(silences, total_dur):
    """Invert silence segments to speak segments."""
    speak = []
    prev_end = 0.0
    for s, e in silences:
        if s > prev_end:
            speak.append((prev_end, s))
        prev_end = e
    if prev_end < total_dur:
        speak.append((prev_end, total_dur))
    return speak

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--threshold", type=float, default=0.5,
                    help="Silence duration threshold in seconds (0.5 default, 0.35 aggressive)")
    ap.add_argument("--noise", type=int, default=-30,
                    help="Noise floor in dB (-30 default, -28 aggressive)")
    ap.add_argument("--padding", type=float, default=0.12,
                    help="Padding (seconds) added before/after each speak segment to prevent word clipping (default 0.12s)")
    ap.add_argument("--save-segments-json", help="Optional: save speak segments to JSON")
    args = ap.parse_args()

    print(f"Analyzing silence (threshold={args.threshold}s, noise={args.noise}dB)...")
    silences = detect_silence(args.input, args.threshold, args.noise)
    dur = probe_duration(args.input)
    speak_raw = silence_to_speak(silences, dur)

    # Apply padding to prevent word clipping at segment boundaries
    speak = []
    for i, (s, e) in enumerate(speak_raw):
        # Extend start backwards by padding, but not past previous segment end
        prev_end = speak_raw[i-1][1] if i > 0 else 0.0
        s_padded = max(prev_end, s - args.padding)
        # Extend end forwards by padding, but not past next segment start
        next_start = speak_raw[i+1][0] if i+1 < len(speak_raw) else dur
        e_padded = min(next_start, e + args.padding)
        speak.append((s_padded, e_padded))
    if args.padding > 0:
        print(f"  Padding: {args.padding}s applied to each segment boundary")

    total_speak = sum(e - s for s, e in speak)
    total_silence = dur - total_speak
    print(f"  Duration: {dur:.2f}s")
    print(f"  Silences: {len(silences)} ({total_silence:.1f}s removed)")
    print(f"  Speech: {total_speak:.2f}s ({len(speak)} segments)")
    print(f"  Reduction: {(total_silence/dur)*100:.1f}%")

    if args.save_segments_json:
        json.dump({
            "duration_total": dur,
            "pauses": [{"start": s, "end": e, "dur": e-s} for s, e in silences],
            "speak_segments": [{"start": s, "end": e, "dur": e-s} for s, e in speak],
            "total_speak": total_speak,
            "total_pause": total_silence
        }, open(args.save_segments_json, "w"), ensure_ascii=False, indent=2)
        print(f"  Saved JSON: {args.save_segments_json}")

    # Build concat list via per-segment cuts
    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        concat_list = td / "concat.txt"
        with concat_list.open("w") as f:
            for i, (s, e) in enumerate(speak):
                seg_path = td / f"seg_{i:02d}.mp4"
                r = subprocess.run([
                    "ffmpeg", "-y", "-loglevel", "error",
                    "-ss", f"{s}", "-to", f"{e}",
                    "-i", str(args.input),
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                    "-c:a", "aac", "-b:a", "192k",
                    "-avoid_negative_ts", "make_zero",
                    str(seg_path)
                ], capture_output=True, text=True)
                if r.returncode != 0:
                    print(f"FAIL seg {i}: {r.stderr[-200:]}", file=sys.stderr)
                    sys.exit(1)
                f.write(f"file '{seg_path.absolute()}'\n")

        # Concat
        r = subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "concat", "-safe", "0", "-i", str(concat_list),
            "-c", "copy", args.output
        ], capture_output=True, text=True)
        if r.returncode != 0:
            print(f"CONCAT FAIL: {r.stderr[-300:]}", file=sys.stderr)
            sys.exit(1)

    out_dur = probe_duration(args.output)
    print(f"\n✅ Output: {args.output}")
    print(f"   Duration: {out_dur:.2f}s (expected {total_speak:.2f}s)")

if __name__ == "__main__":
    main()
