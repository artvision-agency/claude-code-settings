#!/usr/bin/env python3
"""USmile signage v7 — on the REAL Aviacionnaya 9 facade (src-original-1.jpg).
Fix: v6 used wrong location (Park Pobedy plaza). v7 uses verified real building photo
where the existing graphite U SMILE sign already is. Add a NEW projecting/console
corner sign in GRAPHITE #1D1D1F matching the existing mark. Day + night.
"""
import base64, json, os, sys, time, http.client, ssl

ROOT = "/Users/antonk/artvision-data"
OUTDIR = f"{ROOT}/clients/usmile/ideas/signage-v5-corner"
BASE = f"{ROOT}/clients/usmile/assets/photos/2026-05-29-aviacionnaya-correct/src-original-1.jpg"
MODEL = "google/gemini-3-pro-image-preview"

with open(f"{ROOT}/tokens.json") as f:
    KEY = json.load(f)["openrouter"]["api_key"]
with open(BASE, "rb") as f:
    b64 = base64.b64encode(f.read()).decode()
data_url = f"data:image/jpeg;base64,{b64}"

COMMON = (
    "Real photograph edit of THIS EXACT building facade — a St-Petersburg residential "
    "house at Aviacionnaya 9 with an existing dark graphite 'U SMILE СТОМАТОЛОГИЯ' dental "
    "clinic sign and an LED window. DO NOT change the building, the textured stone facade, "
    "windows, or the existing sign. KEEP the real photo realistic. Add a NEW PROJECTING / "
    "CONSOLE (flag-mounted, double-sided) illuminated sign box mounted on a short bracket "
    "that sticks OUT perpendicular from the facade near the building corner, so it is "
    "readable by pedestrians walking along the sidewalk from a distance (not flat on the wall). "
    "On the projecting sign: the USmile logo — a DARK GRAPHITE / CHARCOAL (#1D1D1F) round badge "
    "with a white capital letter U cut-out and the word 'SMILE' in the same dark graphite, "
    "matching the existing sign style. GRAPHITE and WHITE only — NOT red, NOT turquoise. "
    "Realistic perspective, shadows and lighting consistent with the source photo. No people."
)
PROMPTS = {
    "v7-real-day.png": COMMON + " DAYTIME overcast daylight matching the photo. Clean white lightbox cabinet, dark graphite logo, modern.",
    "v7-real-night.png": COMMON + " NIGHT, evening. The projecting sign GLOWS: white face lit from inside, dark graphite logo crisp on the bright glowing face, visible in the dark. Warm streetlight ambiance.",
}

def gen(prompt, outpath, tries=3):
    payload = json.dumps({"model": MODEL, "messages": [{"role": "user", "content": [
        {"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": data_url}}]}],
        "modalities": ["image", "text"]})
    ctx = ssl.create_default_context()
    for a in range(1, tries + 1):
        try:
            c = http.client.HTTPSConnection("openrouter.ai", timeout=240, context=ctx)
            c.request("POST", "/api/v1/chat/completions", body=payload, headers={
                "Authorization": f"Bearer {KEY}", "Content-Type": "application/json",
                "HTTP-Referer": "https://artvision.pro", "X-Title": "USmile v7"})
            r = c.getresponse(); raw = r.read().decode(); c.close()
            if r.status != 200:
                print(f"  [{a}] HTTP {r.status}: {raw[:300]}")
                if r.status in (429, 500, 502, 503): time.sleep(4); continue
                return False
            imgs = json.loads(raw)["choices"][0]["message"].get("images") or []
            if not imgs: print(f"  [{a}] no image"); time.sleep(3); continue
            b = base64.b64decode(imgs[0]["image_url"]["url"].split(",", 1)[1])
            open(outpath, "wb").write(b); print(f"  OK -> {outpath} ({len(b)}b)"); return True
        except (http.client.IncompleteRead, ssl.SSLError, OSError, TimeoutError) as e:
            print(f"  [{a}] socket {type(e).__name__}"); time.sleep(4)
        except Exception as e:
            print(f"  [{a}] err {type(e).__name__} {e}"); time.sleep(3)
    return False

ok = sum(gen(p, os.path.join(OUTDIR, n)) for n, p in PROMPTS.items())
print(f"DONE {ok}/{len(PROMPTS)}"); sys.exit(0 if ok else 1)
