#!/usr/bin/env python3
"""Vision-валидатор через OpenRouter (несколько моделей разных семейств = cross-confirm).
Usage: python3 vision-validate.py <image.png> "<контекст/что проверять>" [--models m1,m2]
Правило: ~/.claude/rules/checks-by-validators-multimodel.md — проверки несут спец-валидаторы, не глаз Claude.
"""
import sys,json,base64,urllib.request,urllib.error
def load_key():
    for p in ("/Users/antonk/artvision-data/tokens.json","/Users/antonk/.claude/tokens.json"):
        try: return json.load(open(p))["openrouter"]["api_key"]
        except Exception: pass
    raise SystemExit("no openrouter key")
def ask(key,model,prompt,img_b64):
    body=json.dumps({"model":model,"messages":[{"role":"user","content":[
        {"type":"text","text":prompt},
        {"type":"image_url","image_url":{"url":"data:image/png;base64,"+img_b64}}]}],"max_tokens":800}).encode()
    req=urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",data=body,
        headers={"Authorization":"Bearer "+key,"Content-Type":"application/json",
                 "HTTP-Referer":"https://artvision.pro","X-Title":"vision-validate"})
    try:
        r=json.load(urllib.request.urlopen(req,timeout=120))
        return r["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e: return f"HTTP {e.code}: {e.read().decode()[:160]}"
    except Exception as e: return f"ERR {e}"
def main():
    if len(sys.argv)<3: raise SystemExit(__doc__)
    img=sys.argv[1]; ctx=sys.argv[2]
    models=["openai/gpt-4o","google/gemini-2.5-pro"]
    for a in sys.argv[3:]:
        if a.startswith("--models="): models=a.split("=",1)[1].split(",")
    key=load_key(); img_b64=base64.b64encode(open(img,"rb").read()).decode()
    prompt=("Ты — независимый дизайн/UX/визуал-валидатор. Оцени скриншот строго.\nКОНТЕКСТ: "+ctx+
            "\nОтветь КРАТКО по-русски: ВЕРДИКТ (ГОДЕН/НЕ ГОДЕН НА РЕВЬЮ) + дефекты по severity (CRITICAL/HIGH/MID), конкретно где и что.")
    for m in models:
        print(f"\n===== {m} =====")
        print(ask(key,m,prompt,img_b64)[:1500])
if __name__=="__main__": main()
