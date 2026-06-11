import base64,json,os,sys,time,http.client,ssl
ROOT="/Users/antonk/artvision-data";OUT=f"{ROOT}/clients/usmile/ideas/signage-v5-corner/bakeoff"
BASE=f"{ROOT}/clients/usmile/assets/photos/2026-05-29-aviacionnaya-correct/src-original-1.jpg"
KEY=json.load(open(f"{ROOT}/tokens.json"))["openrouter"]["api_key"]
du="data:image/jpeg;base64,"+base64.b64encode(open(BASE,"rb").read()).decode()
M="google/gemini-3-pro-image-preview"
REAL=("Real photograph edit of THIS EXACT facade at Aviacionnaya 9 (existing graphite 'U SMILE' sign, window with red LED). Keep building real. No people. ")
JOBS=[
("frontal-day-tv__gemini3pro.png",REAL+"DAYTIME. Make the existing 'U SMILE' wall sign a clean ILLUMINATED lightbox. Add a STRAIGHT horizontal ARROW pointing RIGHT (toward the building corner). In the window install a VERTICAL TV SCREEN showing dental content (a bright smile / white tooth / 'ЗАПИШИСЬ' + QR). Realistic."),
("frontal-night-tv__gemini3pro.png",REAL+"NIGHT. The existing 'U SMILE' wall sign GLOWS (illuminated, bright). A STRAIGHT horizontal ARROW pointing RIGHT toward the corner, lit. In the window a VERTICAL TV SCREEN glowing with dental content (white tooth, smile, QR). Warm streetlight."),
]
def gen(p,o,t=4):
 pl=json.dumps({"model":M,"messages":[{"role":"user","content":[{"type":"text","text":p},{"type":"image_url","image_url":{"url":du}}]}],"modalities":["image","text"]})
 ctx=ssl.create_default_context()
 for a in range(1,t+1):
  try:
   c=http.client.HTTPSConnection("openrouter.ai",timeout=240,context=ctx)
   c.request("POST","/api/v1/chat/completions",body=pl,headers={"Authorization":f"Bearer {KEY}","Content-Type":"application/json","HTTP-Referer":"https://artvision.pro","X-Title":"USmile frontal"})
   r=c.getresponse();raw=r.read().decode();c.close()
   if r.status!=200:
    print(f"[{a}] HTTP {r.status} {raw[:120]}");time.sleep(5);continue
   im=json.loads(raw)["choices"][0]["message"].get("images") or []
   if not im:print(f"[{a}] no img");time.sleep(3);continue
   open(o,"wb").write(base64.b64decode(im[0]["image_url"]["url"].split(",",1)[1]));print("OK",os.path.basename(o));return True
  except Exception as e:print(f"[{a}] {type(e).__name__}");time.sleep(4)
 return False
ok=sum(gen(p,os.path.join(OUT,n)) for n,p in JOBS);print(f"DONE {ok}/{len(JOBS)}")
