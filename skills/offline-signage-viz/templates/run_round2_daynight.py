#!/usr/bin/env python3
"""USmile signage round2 — каждый концепт в ДЕНЬ + НОЧЬ, тест ОСТАВШИХСЯ моделей.
Модели этого захода: gemini-2.5-flash-image (NEW), gpt-5-image-mini (NEW), gemini-3-pro (ref).
База: реальное здание Авиационной 9. Все со стрелкой к арке + QR.
"""
import base64, json, os, sys, time, http.client, ssl
ROOT = "/Users/antonk/artvision-data"
OUTDIR = f"{ROOT}/clients/usmile/ideas/signage-v5-corner/bakeoff"
os.makedirs(OUTDIR, exist_ok=True)
BASE = f"{ROOT}/clients/usmile/assets/photos/2026-05-29-aviacionnaya-correct/src-original-1.jpg"
KEY = json.load(open(f"{ROOT}/tokens.json"))["openrouter"]["api_key"]
data_url = "data:image/jpeg;base64," + base64.b64encode(open(BASE, "rb").read()).decode()

REAL = ("Real photograph edit of THIS EXACT St-Petersburg building facade at Aviacionnaya 9 "
        "(textured stone facade, existing dark graphite 'U SMILE СТОМАТОЛОГИЯ' sign, LED window). "
        "DO NOT change the building, facade, windows, existing sign. Realistic perspective/shadows. "
        "Brand mark GRAPHITE #1D1D1F + white only, NOT red, NOT turquoise. No people. "
        "ALSO a small discreet directional ARROW pointing toward the entrance ARCH (вход под арку во двор). "
        "ALSO a small square QR-code plate (online booking) near the entrance. ")
TOOTH = "Projecting corner sign shaped like a stylized glowing TOOTH (зуб-маяк) lightbox with graphite U-SMILE logo. "
RIBBON = "Flowing ribbon/wave-shaped projecting illuminated sign wrapping the corner, graphite with white glow, U-SMILE logo. "
CONSOLE = "Premium minimalist double-sided console lightbox projecting from the corner, thin bracket, edge-lit graphite U-SMILE. "
DAY = "DAYTIME overcast daylight matching the photo, clean modern lightbox."
NIGHT = "NIGHT evening, the sign GLOWS from inside, graphite logo crisp on bright glowing face, warm streetlight ambiance."

JOBS = [
    ("r2-tooth-day__gemini25flash.png", "google/gemini-2.5-flash-image", REAL + TOOTH + DAY),
    ("r2-tooth-night__gemini25flash.png", "google/gemini-2.5-flash-image", REAL + TOOTH + NIGHT),
    ("r2-ribbon-day__gpt5mini.png", "openai/gpt-5-image-mini", REAL + RIBBON + DAY),
    ("r2-ribbon-night__gpt5mini.png", "openai/gpt-5-image-mini", REAL + RIBBON + NIGHT),
    ("r2-console-day__gemini3pro.png", "google/gemini-3-pro-image-preview", REAL + CONSOLE + DAY),
    ("r2-console-night__gemini3pro.png", "google/gemini-3-pro-image-preview", REAL + CONSOLE + NIGHT),
]

def gen(model, prompt, outpath, tries=3):
    payload = json.dumps({"model": model, "messages": [{"role": "user", "content": [
        {"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": data_url}}]}],
        "modalities": ["image", "text"]})
    ctx = ssl.create_default_context()
    for a in range(1, tries + 1):
        try:
            c = http.client.HTTPSConnection("openrouter.ai", timeout=240, context=ctx)
            c.request("POST", "/api/v1/chat/completions", body=payload, headers={
                "Authorization": f"Bearer {KEY}", "Content-Type": "application/json",
                "HTTP-Referer": "https://artvision.pro", "X-Title": "USmile round2"})
            r = c.getresponse(); raw = r.read().decode(); c.close()
            if r.status != 200:
                print(f"  [{a}] {model} HTTP {r.status}: {raw[:160]}")
                if r.status in (429, 500, 502, 503): time.sleep(5); continue
                return False
            imgs = json.loads(raw)["choices"][0]["message"].get("images") or []
            if not imgs: print(f"  [{a}] {model} no image"); time.sleep(3); continue
            b = base64.b64decode(imgs[0]["image_url"]["url"].split(",", 1)[1])
            open(outpath, "wb").write(b); print(f"  OK {model} -> {os.path.basename(outpath)} ({len(b)}b)"); return True
        except Exception as e:
            print(f"  [{a}] {model} {type(e).__name__} {e}"); time.sleep(4)
    return False

ok = sum(gen(m, p, os.path.join(OUTDIR, n)) for n, m, p in JOBS)
print(f"DONE {ok}/{len(JOBS)}"); sys.exit(0)
