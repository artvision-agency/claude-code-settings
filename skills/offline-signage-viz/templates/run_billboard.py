import base64,json,os,sys,time,http.client,ssl
ROOT="/Users/antonk/artvision-data";OUT=f"{ROOT}/clients/usmile/ideas/signage-v5-corner/bakeoff"
KEY=json.load(open(f"{ROOT}/tokens.json"))["openrouter"]["api_key"];M="google/gemini-3-pro-image-preview"
BASE=("Photorealistic 3x6 meter outdoor BILLBOARD on a pole by a busy St-Petersburg avenue (Московский проспект near "
      "metro Московская), cars passing, daytime. On the billboard a clean premium DENTAL CLINIC ad: a bright healthy "
      "white smile / tooth, graphite #1D1D1F 'U SMILE СТОМАТОЛОГИЯ' logo, short line 'ИМПЛАНТАЦИЯ · ВИНИРЫ · Авиационная 9', "
      "and a QR code corner. Graphite + white + subtle blue accent, NO red. Realistic, readable from the road. No people. ")
JOBS=[("billboard-day__gemini3pro.png",BASE+"Wide daytime shot showing the billboard in street context."),
      ("billboard-closeup__gemini3pro.png",BASE+"Closer 3/4 shot, the creative fills most of the frame, crisp.")]
def gen(p,o,t=4):
 pl=json.dumps({"model":M,"messages":[{"role":"user","content":[{"type":"text","text":p}]}],"modalities":["image","text"]})
 ctx=ssl.create_default_context()
 for a in range(1,t+1):
  try:
   c=http.client.HTTPSConnection("openrouter.ai",timeout=240,context=ctx);c.request("POST","/api/v1/chat/completions",body=pl,headers={"Authorization":f"Bearer {KEY}","Content-Type":"application/json","HTTP-Referer":"https://artvision.pro","X-Title":"billboard"})
   r=c.getresponse();raw=r.read().decode();c.close()
   if r.status!=200:print(f"[{a}] {r.status}");time.sleep(5);continue
   im=json.loads(raw)["choices"][0]["message"].get("images") or []
   if not im:print(f"[{a}] no");time.sleep(3);continue
   open(o,"wb").write(base64.b64decode(im[0]["image_url"]["url"].split(",",1)[1]));print("OK",os.path.basename(o));return True
  except Exception as e:print(f"[{a}] {type(e).__name__}");time.sleep(4)
 return False
ok=sum(gen(p,os.path.join(OUT,n)) for n,p in JOBS);print(f"DONE {ok}/{len(JOBS)}")
