#!/usr/bin/env python3
"""Audio balance tester — automatically checks loudness uniformity in video.

Tests:
  1. Integrated LUFS within tolerance of target (-14 LUFS for socials)
  2. Max peak below true-peak ceiling (no clipping)
  3. Loudness difference between first half vs last 2s < THRESHOLD (balanced)
  4. No hard-cut click at end — last 50ms peak not higher than preceding 500ms peak

Exit: 0 = PASS (all checks), 1 = FAIL (one or more checks failed).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from typing import Optional

# ─── Tunable thresholds ──────────────────────────────────────────────
LUFS_TARGET = -14.0           # TikTok/IG Reels/YouTube Shorts standard
LUFS_TOLERANCE = 1.5          # ± deviation considered acceptable
TRUE_PEAK_MAX = -1.0          # dBTP — stricter than broadcast
SEGMENT_BALANCE_MAX_DB = 3.0  # max diff between first-half and last-2s mean
END_SPIKE_MAX_DB = 3.0        # max peak spike in last 50ms vs prior 500ms
END_WINDOW_SEC = 0.05         # "last" window to detect click
PRIOR_WINDOW_SEC = 0.50       # "prior" window for comparison
LAST_SEGMENT_SEC = 2.0        # size of "last segment" for balance check
FFPROBE_TIMEOUT = 30
FFMPEG_TIMEOUT = 120

# Regex patterns for ffmpeg stderr parsing
RE_MEAN_VOL = re.compile(r"mean_volume:\s*(-?[\d.]+)\s*dB")
RE_MAX_VOL = re.compile(r"max_volume:\s*(-?[\d.]+)\s*dB")
RE_LUFS_INT = re.compile(r"Input Integrated:\s*(-?[\d.]+)\s*LUFS")
RE_LUFS_TP = re.compile(r"Input True Peak:\s*(-?[\d.]+)\s*dBTP")


class FFmpegError(RuntimeError):
    """Raised when ffmpeg/ffprobe fails or output is unparsable."""


# ─── FFmpeg helpers ──────────────────────────────────────────────────

def ffprobe_duration(file: str) -> float:
    """Get video duration in seconds. Raises FFmpegError on failure."""
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", file],
        capture_output=True, text=True, timeout=FFPROBE_TIMEOUT, check=False,
    )
    stdout = r.stdout.strip()
    if r.returncode != 0 or not stdout:
        raise FFmpegError(
            f"ffprobe failed for {file}: rc={r.returncode} "
            f"stderr={r.stderr[:200]!r} stdout={stdout!r}"
        )
    try:
        return float(stdout)
    except ValueError as e:
        raise FFmpegError(f"ffprobe returned non-numeric duration: {stdout!r}") from e


def ffmpeg_filter(file: str, af: str, ss: Optional[float] = None,
                  t: Optional[float] = None) -> str:
    """Run ffmpeg with audio filter and return stderr (where ffmpeg prints stats)."""
    cmd = ["ffmpeg", "-i", file]
    if ss is not None:
        cmd += ["-ss", str(ss)]
    if t is not None:
        cmd += ["-t", str(t)]
    cmd += ["-af", af, "-f", "null", "-"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=FFMPEG_TIMEOUT, check=False)
    if r.returncode != 0:
        raise FFmpegError(f"ffmpeg rc={r.returncode}: {r.stderr[-500:]}")
    return r.stderr


def parse_kv(stderr: str, patterns: dict[str, re.Pattern]) -> dict[str, float]:
    """Extract matched values from stderr. Raises if any expected key missing."""
    out: dict[str, float] = {}
    for key, pat in patterns.items():
        m = pat.search(stderr)
        if not m:
            raise FFmpegError(f"pattern for {key!r} not found in stderr")
        out[key] = float(m.group(1))
    return out


# ─── Measurement functions ──────────────────────────────────────────

def measure_vol(file: str, ss: Optional[float] = None,
                t: Optional[float] = None) -> dict[str, float]:
    """Measure mean + max volume (dB) in a window."""
    stderr = ffmpeg_filter(file, "volumedetect", ss=ss, t=t)
    return parse_kv(stderr, {"mean": RE_MEAN_VOL, "max": RE_MAX_VOL})


def measure_lufs(file: str) -> dict[str, float]:
    """Measure integrated LUFS + true peak dBTP."""
    stderr = ffmpeg_filter(file, f"loudnorm=I={LUFS_TARGET}:print_format=summary")
    return parse_kv(stderr, {"integrated": RE_LUFS_INT, "true_peak": RE_LUFS_TP})


# ─── Test checks ────────────────────────────────────────────────────

def test(file: str, target_lufs: float = LUFS_TARGET,
         expect_speech_end: bool = True) -> dict:
    dur = ffprobe_duration(file)
    results: dict = {"file": file, "duration": dur, "tests": []}
    tests: list = results["tests"]

    # Test 1: integrated LUFS
    lufs = measure_lufs(file)
    results["lufs"] = lufs
    delta = lufs["integrated"] - target_lufs
    tests.append({
        "name": "Integrated LUFS",
        "pass": abs(delta) <= LUFS_TOLERANCE,
        "msg": f"{lufs['integrated']:+.1f} LUFS (target {target_lufs} ±{LUFS_TOLERANCE})",
    })

    # Test 2: true peak
    tests.append({
        "name": f"True peak < {TRUE_PEAK_MAX} dBTP",
        "pass": lufs["true_peak"] < TRUE_PEAK_MAX,
        "msg": f"TP {lufs['true_peak']:.1f} dBTP",
    })

    # Test 3: segment balance (first half vs last 2s)
    half = dur / 2.0
    last_start = max(0.0, dur - LAST_SEGMENT_SEC)
    first = measure_vol(file, 0, half)
    last = measure_vol(file, last_start, LAST_SEGMENT_SEC)
    diff = last["mean"] - first["mean"]
    results["first_half"] = first
    results["last_segment"] = last
    tests.append({
        "name": f"Segment balance (first vs last {LAST_SEGMENT_SEC}s)",
        "pass": abs(diff) <= SEGMENT_BALANCE_MAX_DB,
        "msg": (f"first={first['mean']:.1f}dB  last={last['mean']:.1f}dB  "
                f"diff {diff:+.1f}dB (max ±{SEGMENT_BALANCE_MAX_DB})"),
    })

    # Test 4: end-click detection
    if expect_speech_end and dur >= (PRIOR_WINDOW_SEC + END_WINDOW_SEC + 0.1):
        prior = measure_vol(file, dur - (PRIOR_WINDOW_SEC + END_WINDOW_SEC), PRIOR_WINDOW_SEC)
        last_ms = measure_vol(file, dur - END_WINDOW_SEC, END_WINDOW_SEC)
        peak_spike = last_ms["max"] - prior["max"]
        results["end_prior"] = prior
        results["end_last"] = last_ms
        tests.append({
            "name": "No hard-cut click at end",
            "pass": peak_spike <= END_SPIKE_MAX_DB,
            "msg": (f"prior{int(PRIOR_WINDOW_SEC*1000)}ms peak={prior['max']:.1f}dB  "
                    f"last{int(END_WINDOW_SEC*1000)}ms peak={last_ms['max']:.1f}dB  "
                    f"spike {peak_spike:+.1f}dB (max {END_SPIKE_MAX_DB})"),
        })

    passed = sum(1 for t in tests if t["pass"])
    results.update(passed=passed, total=len(tests),
                   verdict="PASS" if passed == len(tests) else "FAIL")
    return results


def print_report(r: dict) -> None:
    print(f"\n📁 {r['file']} ({r['duration']:.2f}s)")
    print(f"   LUFS: {r['lufs']['integrated']:+.1f} | TP: {r['lufs']['true_peak']:.1f} dBTP")
    for t in r["tests"]:
        icon = "✓" if t["pass"] else "✗"
        print(f"   {icon} {t['name']}: {t['msg']}")
    print(f"   → {r['verdict']} ({r['passed']}/{r['total']})")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--target", type=float, default=LUFS_TARGET)
    ap.add_argument("--no-speech-check", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    all_results = []
    for f in args.files:
        try:
            r = test(f, args.target, not args.no_speech_check)
            all_results.append(r)
            if not args.json:
                print_report(r)
        except FFmpegError as e:
            print(f"✗ {f}: {e}", file=sys.stderr)
            all_results.append({"file": f, "verdict": "ERROR", "error": str(e)})

    if args.json:
        print(json.dumps(all_results, indent=2, ensure_ascii=False))

    return 1 if any(r.get("verdict") != "PASS" for r in all_results) else 0


if __name__ == "__main__":
    sys.exit(main())
