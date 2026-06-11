import base64,json,os,sys,time,http.client,ssl
ROOT="/Users/antonk/artvision-data";OUT=f"{ROOT}/clients/usmile/ideas/signage-v5-corner/bakeoff"
KEY=json.load(open(f"{ROOT}/tokens.json"))["openrouter"]["api_key"];M="google/gemini-3-pro-image-preview"
P=("Photorealistic product photo of a CLEAR TRANSPARENT acrylic glass sheet standing in a solid DARK WALNUT wooden base "
   "(LAVITA-style table QR stand). On the clear acrylic a printed sticker: a stylish ROUNDED-DOT QR code in dark graphite "
   "#1D1D1F with a small round tooth/'U' logo in center. Under the QR the text 'ЗАПИСЬ ОНЛАЙН' and below 'usmile.ru' and "
   "'USMILE СТОМАТОЛОГИЯ'. NO Instagram, NO social handle. Clean minimal, premium, soft daylight, shallow depth of field. ")
JOBS=[("lavita-v2-1__gemini3pro.png",P+"3/4 angle, light grey wall."),
      ("lavita-v2-2__gemini3pro.png",P+"On a clinic reception desk, warm light.")]
def gen(p,o,t=4):
 pl=json.dumps({"model":M,"messages":[{"role":"user","content":[{"type":"text","text":p}]}],"modalities":["image","text"]})
 ctx=ssl.create_default_context()
 for a in range(1,t+1):
  try:
   c=http.client.HTTPSConnection("openrouter.ai",timeout=240,context=ctx);c.request("POST","/api/v1/chat/completions",body=pl,headers={"Authorization":f"Bearer {KEY}","Content-Type":"application/json","HTTP-Referer":"https://artvision.pro","X-Title":"lavita2"})
   r=c.getresponse();raw=r.read().decode();c.close()
   if r.status!=200:print(f"[{a}] {r.status}");time.sleep(5);continue
   im=json.loads(raw)["choices"][0]["message"].get("images") or []
   if not im:print(f"[{a}] no");time.sleep(3);continue
   open(o,"wb").write(base64.b64decode(im[0]["image_url"]["url"].split(",",1)[1]));print("OK",os.path.basename(o));return True
  except Exception as e:print(f"[{a}] {type(e).__name__}");time.sleep(4)
 return False
ok=sum(gen(p,os.path.join(OUT,n)) for n,p in JOBS);print(f"DONE {ok}/{len(JOBS)}")
