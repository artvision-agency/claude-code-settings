import base64,json,os,sys,time,http.client,ssl
ROOT="/Users/antonk/artvision-data";OUT=f"{ROOT}/clients/usmile/ideas/signage-v5-corner/bakeoff"
KEY=json.load(open(f"{ROOT}/tokens.json"))["openrouter"]["api_key"]
M="google/gemini-3-pro-image-preview"
BRAND=("A premium FROSTED ACRYLIC tabletop sign standing in a solid OAK WOODEN base block (like HOT SPOT / "
       "LAVITA style table stands). On the frosted acrylic: at top a clean GRAPHITE #1D1D1F logo — a tooth icon "
       "with 'U SMILE СТОМАТОЛОГИЯ'; in the center a clear black-and-white QR code; below it the text "
       "'ЗАПИСЬ ОНЛАЙН'; at the bottom 'Авиационная 9 · СПб'. Photorealistic product photography, soft studio light, "
       "sharp, premium, the acrylic looks expensive and tactile. ")
JOBS=[
("qrreal-studio__gemini3pro.png", BRAND+"Studio shot on a light wooden table, neutral background, 45-degree angle, shallow depth of field."),
("qrreal-ozon-pvz__gemini3pro.png", BRAND+"The stand placed on a counter INSIDE an OZON pickup point (ПВЗ Ozon, blue/white branding visible softly in background), realistic interior."),
("qrreal-wb-pvz__gemini3pro.png", BRAND+"The stand placed on a counter INSIDE a WILDBERRIES pickup point (ПВЗ WB, purple/pink branding softly in background), realistic interior."),
]
def gen(p,o,t=4):
 pl=json.dumps({"model":M,"messages":[{"role":"user","content":[{"type":"text","text":p}]}],"modalities":["image","text"]})
 ctx=ssl.create_default_context()
 for a in range(1,t+1):
  try:
   c=http.client.HTTPSConnection("openrouter.ai",timeout=240,context=ctx)
   c.request("POST","/api/v1/chat/completions",body=pl,headers={"Authorization":f"Bearer {KEY}","Content-Type":"application/json","HTTP-Referer":"https://artvision.pro","X-Title":"USmile qr-real"})
   r=c.getresponse();raw=r.read().decode();c.close()
   if r.status!=200:
    print(f"[{a}] {r.status} {raw[:120]}");time.sleep(5);continue
   im=json.loads(raw)["choices"][0]["message"].get("images") or []
   if not im:print(f"[{a}] no img");time.sleep(3);continue
   open(o,"wb").write(base64.b64decode(im[0]["image_url"]["url"].split(",",1)[1]));print("OK",os.path.basename(o));return True
  except Exception as e:print(f"[{a}] {type(e).__name__}");time.sleep(4)
 return False
ok=sum(gen(p,os.path.join(OUT,n)) for n,p in JOBS);print(f"DONE {ok}/{len(JOBS)}")
