#!/usr/bin/env python3
"""USmile зуб-маяк — видео медленной пульсации подсветки (ночь). PIL кадры -> ffmpeg MP4.
База: r2-tooth-night (реальное здание Авиационной 9). Зуб ~ (cx,cy) пульсирует как маяк."""
import math, os, subprocess
from PIL import Image, ImageEnhance, ImageDraw, ImageFilter

D = "/Users/antonk/artvision-data/clients/usmile/ideas/signage-v5-corner"
SRC = f"{D}/bakeoff/r2-tooth-night__gemini25flash.png"
FRAMES = "/tmp/usmile-beacon-frames"
os.makedirs(FRAMES, exist_ok=True)
for f in os.listdir(FRAMES):
    os.remove(os.path.join(FRAMES, f))

base = Image.open(SRC).convert("RGB")
W, H = base.size
# зуб (правый-верхний): подобрано по картинке 864x1184
CX, CY, R = int(W * 0.81), int(H * 0.30), int(W * 0.16)

FPS = 30
SECONDS = 8          # 2 медленных цикла по 4с
PERIOD = 4.0         # медленный маяк: 4 сек на цикл
N = FPS * SECONDS

# мягкий радиальный glow-слой (белый/голубоватый) для зуба
glow = Image.new("L", (W, H), 0)
gd = ImageDraw.Draw(glow)
gd.ellipse([CX - R, CY - R, CX + R, CY + R], fill=255)
glow = glow.filter(ImageFilter.GaussianBlur(R * 0.55))
glow_rgb = Image.new("RGB", (W, H), (210, 235, 255))  # холодный маяк-свет

for i in range(N):
    t = i / FPS
    # медленный «вдох-выдох» + лёгкий пик (маяк): 0..1
    base_pulse = 0.5 - 0.5 * math.cos(2 * math.pi * t / PERIOD)  # плавно 0->1->0
    peak = max(0, math.sin(2 * math.pi * t / PERIOD)) ** 4        # короткий яркий пик
    amt = 0.35 + 0.65 * base_pulse + 0.5 * peak                   # сила свечения
    amt = min(amt, 1.4)

    frame = base.copy()
    # 1) подмешать холодный glow по маске с силой amt
    alpha = glow.point(lambda v, a=amt: int(min(255, v * a)))
    frame = Image.composite(glow_rgb, frame, alpha)
    # 2) локально поднять яркость зуба
    eb = ImageEnhance.Brightness(frame).enhance(1.0)
    # сохранить
    frame.save(f"{FRAMES}/f{i:04d}.png")

out = f"{D}/tooth-beacon-night.mp4"
cmd = ["ffmpeg", "-y", "-framerate", str(FPS), "-i", f"{FRAMES}/f%04d.png",
       "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-pix_fmt", "yuv420p",
       "-movflags", "+faststart", "-r", str(FPS), out]
r = subprocess.run(cmd, capture_output=True, text=True)
print("ffmpeg rc", r.returncode, r.stderr[-300:] if r.returncode else "OK")
print("OUT", out, os.path.getsize(out) if os.path.exists(out) else "MISSING")
