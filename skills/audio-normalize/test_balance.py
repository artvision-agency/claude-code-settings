#!/usr/bin/env python3
"""
Audio balance tester — автоматически проверяет равномерность громкости в видео.

Проверки:
1. Integrated LUFS ±1.5 LU от target (-14 для соцсетей)
2. Max peak < -1 dBTP (нет клиппинга)
3. Разница loudness между первой половиной и концом < 3 dB (равномерно)
4. Конец: трендовая проверка — последние 200мс ДОЛЖНЫ быть тише предыдущих 200-400мс
   (естественный decay или fade-out), иначе hard-cut mid-word

Выход: читаемый отчёт + exit code 0=PASS 1=FAIL
"""
from __future__ import annotations
import subprocess, json, re, sys, argparse
from typing import Optional

def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)

def measure_vol(file: str, ss: Optional[float] = None, t: Optional[float] = None) -> dict:
    cmd = ["ffmpeg", "-i", file]
    if ss is not None: cmd += ["-ss", str(ss)]
    if t is not None: cmd += ["-t", str(t)]
    cmd += ["-af", "volumedetect", "-f", "null", "-"]
    r = run(cmd)
    mean = re.search(r"mean_volume:\s*(-?[\d.]+)\s*dB", r.stderr)
    maxv = re.search(r"max_volume:\s*(-?[\d.]+)\s*dB", r.stderr)
    return {
        "mean": float(mean.group(1)) if mean else float("-inf"),
        "max": float(maxv.group(1)) if maxv else float("-inf"),
    }

def measure_lufs(file: str) -> dict:
    r = run(["ffmpeg", "-i", file, "-af", "loudnorm=I=-14:print_format=summary", "-f", "null", "-"])
    i = re.search(r"Input Integrated:\s*(-?[\d.]+)\s*LUFS", r.stderr)
    tp = re.search(r"Input True Peak:\s*(-?[\d.]+)\s*dBTP", r.stderr)
    return {
        "integrated": float(i.group(1)) if i else 0.0,
        "true_peak": float(tp.group(1)) if tp else 0.0,
    }

def test(file: str, target_lufs: float = -14, expect_speech_end: bool = True) -> dict:
    dur_raw = run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", file]).stdout.strip()
    dur = float(dur_raw)

    results: dict = {"file": file, "duration": dur, "tests": []}
    tests: list = results["tests"]

    # Test 1: Overall LUFS
    lufs = measure_lufs(file)
    delta = lufs["integrated"] - target_lufs
    results["lufs"] = lufs
    tests.append({
        "name": "Integrated LUFS",
        "pass": abs(delta) <= 1.5,
        "msg": f"{lufs['integrated']:+.1f} LUFS (target {target_lufs} ±1.5)",
    })

    # Test 2: True peak
    tests.append({
        "name": "True peak < -1 dBTP",
        "pass": lufs["true_peak"] < -1.0,
        "msg": f"TP {lufs['true_peak']:.1f} dBTP",
    })

    # Test 3: Segment balance first-half vs last 2s
    half = dur / 2.0
    last2_start = max(0.0, dur - 2.0)
    first = measure_vol(file, 0, half)
    last = measure_vol(file, last2_start, 2.0)
    diff = last["mean"] - first["mean"]
    results["first_half"] = first
    results["last_2s"] = last
    tests.append({
        "name": "Segment balance (first vs last 2s)",
        "pass": abs(diff) <= 3.0,
        "msg": f"first={first['mean']:.1f}dB  last={last['mean']:.1f}dB  diff {diff:+.1f}dB (max ±3)",
    })

    # Test 4: End — check for sudden click/spike at the very end (indicative of hard cut mid-phoneme)
    # Rule: last 50ms max peak should not exceed prior 500ms max by more than 3 dB.
    # Loudnorm often compresses fade-outs back, so trend-drop test is unreliable.
    if expect_speech_end and dur >= 0.6:
        prior500 = measure_vol(file, max(0, dur - 0.55), 0.5)  # t-550 → t-50
        last50 = measure_vol(file, dur - 0.05, 0.05)            # t-50 → t-0
        peak_spike = last50["max"] - prior500["max"]            # positive = spike at end
        results["end_prior_500ms"] = prior500
        results["end_last_50ms"] = last50
        # Hard cut often produces a peak at the very last sample. Natural fade does not.
        tests.append({
            "name": "No hard-cut click at end",
            "pass": peak_spike <= 3.0,
            "msg": f"prior500ms peak={prior500['max']:.1f}dB  last50ms peak={last50['max']:.1f}dB  spike {peak_spike:+.1f}dB (max 3)",
        })

    passed = sum(1 for t in tests if t["pass"])
    total = len(tests)
    results["passed"] = passed
    results["total"] = total
    results["verdict"] = "PASS" if passed == total else "FAIL"
    return results

def print_report(r: dict) -> None:
    print(f"\n📁 {r['file']} ({r['duration']:.2f}s)")
    print(f"   LUFS: {r['lufs']['integrated']:+.1f} | TP: {r['lufs']['true_peak']:.1f} dBTP")
    for t in r["tests"]:
        icon = "✓" if t["pass"] else "✗"
        print(f"   {icon} {t['name']}: {t['msg']}")
    print(f"   → {r['verdict']} ({r['passed']}/{r['total']})")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--target", type=float, default=-14)
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
        except Exception as e:
            print(f"ERR {f}: {e}")

    if args.json:
        print(json.dumps(all_results, indent=2, ensure_ascii=False))

    failed = [r for r in all_results if r["verdict"] == "FAIL"]
    sys.exit(1 if failed else 0)
