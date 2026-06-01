import base64,json,os,sys,time,http.client,ssl
ROOT="/Users/antonk/artvision-data";OUT=f"{ROOT}/clients/usmile/ideas/signage-v5-corner/bakeoff"
KEY=json.load(open(f"{ROOT}/tokens.json"))["openrouter"]["api_key"];M="google/gemini-3-pro-image-preview"
CTX=("Photorealistic outdoor ad on a St-Petersburg street near metro Московская, daytime, cars, realistic. "
     "Premium DENTAL clinic creative: graphite #1D1D1F 'U SMILE СТОМАТОЛОГИЯ' logo + small QR. Graphite+white+subtle blue, NO red. No people except where stated. Readable from road. ")
JOBS=[
("bb2-implant-3x6__gemini3pro.png",CTX+"3x6 billboard, focus IMPLANTS: 'ИМПЛАНТАЦИЯ ЗУБОВ от Straumann · Авиационная 9', a confident smiling man 40s, clean."),
("bb2-veneers-3x6__gemini3pro.png",CTX+"3x6 billboard, focus VENEERS/esthetics: 'ВИНИРЫ · ГОЛЛИВУДСКАЯ УЛЫБКА · Авиационная 9', a beautiful white smile close-up."),
("bb2-city-format__gemini3pro.png",CTX+"VERTICAL city-format 1.2x1.8 lightbox on a sidewalk pole, 'U SMILE · Запись онлайн · Авиационная 9' + big QR, evening soft glow."),
("bb2-dooh-screen__gemini3pro.png",CTX+"Digital DOOH LED screen by the road showing the U SMILE ad with a bright healthy smile, night, glowing."),
]
def gen(p,o,t=4):
 pl=json.dumps({"model":M,"messages":[{"role":"user","content":[{"type":"text","text":p}]}],"modalities":["image","text"]})
 ctx=ssl.create_default_context()
 for a in range(1,t+1):
  try:
   c=http.client.HTTPSConnection("openrouter.ai",timeout=240,context=ctx);c.request("POST","/api/v1/chat/completions",body=pl,headers={"Authorization":f"Bearer {KEY}","Content-Type":"application/json","HTTP-Referer":"https://artvision.pro","X-Title":"bb2"})
   r=c.getresponse();raw=r.read().decode();c.close()
   if r.status!=200:print(f"[{a}] {r.status}");time.sleep(5);continue
   im=json.loads(raw)["choices"][0]["message"].get("images") or []
   if not im:print(f"[{a}] no");time.sleep(3);continue
   open(o,"wb").write(base64.b64decode(im[0]["image_url"]["url"].split(",",1)[1]));print("OK",os.path.basename(o));return True
  except Exception as e:print(f"[{a}] {type(e).__name__}");time.sleep(4)
 return False
ok=sum(gen(p,os.path.join(OUT,n)) for n,p in JOBS);print(f"DONE {ok}/{len(JOBS)}")
