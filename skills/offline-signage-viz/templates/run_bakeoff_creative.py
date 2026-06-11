#!/usr/bin/env python3
"""USmile signage — CREATIVE bakeoff: 4 концепта x разные модели на реальном здании Авиационной 9.
Тест инструментов (model-bakeoff) + креативные варианты. Все на src-original-1.jpg.
"""
import base64, json, os, sys, time, http.client, ssl

ROOT = "/Users/antonk/artvision-data"
OUTDIR = f"{ROOT}/clients/usmile/ideas/signage-v5-corner/bakeoff"
os.makedirs(OUTDIR, exist_ok=True)
BASE = f"{ROOT}/clients/usmile/assets/photos/2026-05-29-aviacionnaya-correct/src-original-1.jpg"
with open(f"{ROOT}/tokens.json") as f:
    KEY = json.load(f)["openrouter"]["api_key"]
with open(BASE, "rb") as f:
    data_url = "data:image/jpeg;base64," + base64.b64encode(f.read()).decode()

REAL = ("Real photograph edit of THIS EXACT St-Petersburg building facade at Aviacionnaya 9 "
        "(textured stone facade, existing dark graphite 'U SMILE СТОМАТОЛОГИЯ' sign, LED window). "
        "DO NOT change the building, facade texture, windows, or existing sign. Keep realistic, "
        "correct perspective/shadows. Brand mark GRAPHITE #1D1D1F + white only, NOT red, NOT turquoise. No people. "
        "ALSO add a small discreet directional ARROW pointing toward the entrance ARCH (вход под арку во двор). "
        "ALSO add a small square QR-code plate (online booking) near the entrance or on the sign. ")

# (имя, модель, креативный концепт)
JOBS = [
    ("c1-tooth-beacon__gemini3pro.png", "google/gemini-3-pro-image-preview",
     REAL + "Add a CREATIVE projecting corner sign shaped like a stylized glowing TOOTH (зуб-маяк) "
     "as a modern lightbox, with the graphite U-SMILE logo on it, premium dental-clinic look, soft illumination."),
    ("c2-letter-U-artobject__gpt54.png", "openai/gpt-5.4-image-2",
     REAL + "Add a CREATIVE oversized 3D sculptural letter 'U' as a backlit art-object mounted on the corner, "
     "graphite and white, minimal premium design, plus a small 'SMILE' wordmark beneath it. Architectural signage."),
    ("c3-ribbon-wave__gemini31flash.png", "google/gemini-3.1-flash-image-preview",
     REAL + "Add a CREATIVE flowing ribbon / wave-shaped projecting illuminated sign wrapping the building corner, "
     "graphite with white glow, carrying the U-SMILE logo, elegant modern dental brand."),
    ("c4-premium-console__gpt5.png", "openai/gpt-5-image",
     REAL + "Add a CREATIVE premium minimalist double-sided console lightbox projecting from the corner, "
     "thin elegant bracket, soft edge-lit graphite U-SMILE logo, high-end clinic aesthetic, evening soft glow."),
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
                "HTTP-Referer": "https://artvision.pro", "X-Title": "USmile bakeoff"})
            r = c.getresponse(); raw = r.read().decode(); c.close()
            if r.status != 200:
                print(f"  [{a}] {model} HTTP {r.status}: {raw[:200]}")
                if r.status in (429, 500, 502, 503): time.sleep(5); continue
                return False
            imgs = json.loads(raw)["choices"][0]["message"].get("images") or []
            if not imgs: print(f"  [{a}] {model} no image"); time.sleep(3); continue
            b = base64.b64decode(imgs[0]["image_url"]["url"].split(",", 1)[1])
            open(outpath, "wb").write(b); print(f"  OK {model} -> {os.path.basename(outpath)} ({len(b)}b)"); return True
        except Exception as e:
            print(f"  [{a}] {model} {type(e).__name__} {e}"); time.sleep(4)
    return False


ok = 0
for name, model, prompt in JOBS:
    print(f"== {name} [{model}]")
    if gen(model, prompt, os.path.join(OUTDIR, name)): ok += 1
print(f"DONE {ok}/{len(JOBS)}"); sys.exit(0)
