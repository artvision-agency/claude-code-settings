#!/usr/bin/env python3
"""USmile зуб-маяк — состояния для видео-истории «U smile лечит» + LED-дисплей вариант.
A: зуб жёлтый/с кариесом (чёрное пятно), U SMILE не светится.
B: зуб идеально белый светящийся, U SMILE ярко подсвечено.
LED: вариант со сменяющимся LED-экраном (акции/QR/время).
База: реальное здание Авиационной 9. Модель: gemini-3-pro (Nano Banana Pro)."""
import base64, json, os, sys, time, http.client, ssl
ROOT = "/Users/antonk/artvision-data"
OUTDIR = f"{ROOT}/clients/usmile/ideas/signage-v5-corner/bakeoff"
BASE = f"{ROOT}/clients/usmile/assets/photos/2026-05-29-aviacionnaya-correct/src-original-1.jpg"
KEY = json.load(open(f"{ROOT}/tokens.json"))["openrouter"]["api_key"]
data_url = "data:image/jpeg;base64," + base64.b64encode(open(BASE, "rb").read()).decode()
M = "google/gemini-3-pro-image-preview"

REAL = ("Real photograph edit of THIS EXACT St-Petersburg building facade at Aviacionnaya 9 "
        "(textured stone facade, existing graphite 'U SMILE' sign, LED window). Keep building/facade real. "
        "NIGHT evening scene, realistic. No people. ")

JOBS = [
    # A — больной зуб (для старта истории)
    ("story-A-sick__gemini3pro.png", REAL +
     "Add a projecting corner sign shaped like a big TOOTH. The tooth is YELLOWISH / unhealthy with a small "
     "dark BLACK CARIES SPOT on it, looking dull and not glowing. The 'U SMILE' brand name nearby is DIM / UNLIT. "
     "Slightly gloomy lighting on the tooth."),
    # B — здоровый зуб (финал истории)
    ("story-B-healed__gemini3pro.png", REAL +
     "Add a projecting corner sign shaped like a big TOOTH that is PERFECTLY WHITE, clean, bright and GLOWING "
     "with healthy light. At the same moment the 'U SMILE' brand name is BRIGHTLY LIT and glowing graphite-on-white, "
     "celebrating a healthy smile. Premium, optimistic, the clinic healed the tooth."),
    # LED-дисплей вариант
    ("led-display__gemini3pro.png", REAL +
     "Add a modern projecting corner LED SCREEN display box (digital signage) that shows changing content: "
     "the graphite U-SMILE logo, the time, and a line 'ЧИСТКА 2500 ₽' plus a small QR code, like a small bright "
     "digital billboard on the building corner. Plus a discreet arrow toward the entrance arch."),
]

def gen(prompt, outpath, tries=4):
    payload = json.dumps({"model": M, "messages": [{"role": "user", "content": [
        {"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": data_url}}]}],
        "modalities": ["image", "text"]})
    ctx = ssl.create_default_context()
    for a in range(1, tries + 1):
        try:
            c = http.client.HTTPSConnection("openrouter.ai", timeout=240, context=ctx)
            c.request("POST", "/api/v1/chat/completions", body=payload, headers={
                "Authorization": f"Bearer {KEY}", "Content-Type": "application/json",
                "HTTP-Referer": "https://artvision.pro", "X-Title": "USmile story"})
            r = c.getresponse(); raw = r.read().decode(); c.close()
            if r.status != 200:
                print(f"  [{a}] HTTP {r.status}: {raw[:160]}")
                if r.status in (429, 500, 502, 503): time.sleep(5); continue
                return False
            imgs = json.loads(raw)["choices"][0]["message"].get("images") or []
            if not imgs: print(f"  [{a}] no image"); time.sleep(3); continue
            b = base64.b64decode(imgs[0]["image_url"]["url"].split(",", 1)[1])
            open(outpath, "wb").write(b); print(f"  OK -> {os.path.basename(outpath)} ({len(b)}b)"); return True
        except Exception as e:
            print(f"  [{a}] {type(e).__name__} {e}"); time.sleep(4)
    return False

ok = sum(gen(p, os.path.join(OUTDIR, n)) for n, p in JOBS)
print(f"DONE {ok}/{len(JOBS)}"); sys.exit(0)
