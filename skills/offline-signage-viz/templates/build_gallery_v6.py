#!/usr/bin/env python3
"""Build self-contained gallery-v6.html (graphite signage) with inline base64 + zoom + Artvision brand."""
import base64, os
D = "/Users/antonk/artvision-data/clients/usmile/ideas/signage-v5-corner"
def b64(p):
    with open(p, "rb") as f:
        return base64.b64encode(f.read()).decode()
day = b64(f"{D}/v6-corner-day-graphite.png")
night = b64(f"{D}/v6-corner-night-graphite.png")
sprite = b64("/Users/antonk/artvision-data/clients/usmile/assets/logo/usmile-sprite-main.png")

html = f"""<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>USmile — вывеска v6 (графит) угловая</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;background:#f4f5f7;color:#1d1d1f;line-height:1.5}}
.bar{{display:flex;align-items:center;gap:12px;padding:12px 18px;background:#fff;border-bottom:1px solid #e5e7eb;position:sticky;top:0;z-index:50}}
.bar b{{color:#614CE1}}
.bar .doc{{margin-left:auto;font-size:13px;color:#6b7280}}
.wrap{{max-width:1100px;margin:0 auto;padding:18px}}
h1{{font-size:22px;margin:8px 0 4px}}
.note{{font-size:14px;color:#4b5563;margin-bottom:18px}}
.card{{background:#fff;border:1px solid #e5e7eb;border-radius:14px;overflow:hidden;margin-bottom:22px;box-shadow:0 1px 4px rgba(0,0,0,.04)}}
.card h2{{font-size:16px;padding:14px 16px 0}}
.card p{{font-size:13px;color:#6b7280;padding:2px 16px 12px}}
.card img{{width:100%;display:block;cursor:zoom-in}}
.ref{{display:flex;gap:14px;align-items:center;padding:14px 16px;background:#fafafa;border-top:1px solid #eee}}
.ref img{{width:120px;border:1px solid #e5e7eb;border-radius:8px;background:#fff}}
.ref span{{font-size:13px;color:#4b5563}}
.lb{{position:fixed;inset:0;background:rgba(0,0,0,.9);display:none;align-items:center;justify-content:center;z-index:100;cursor:zoom-out}}
.lb img{{max-width:96%;max-height:96%}}
.lb.on{{display:flex}}
.foot{{padding:20px;text-align:center;font-size:13px;color:#6b7280}}
.foot a{{color:#614CE1;text-decoration:none}}
.ask{{position:fixed;bottom:20px;right:20px;background:#614CE1;color:#fff;padding:11px 16px;border-radius:24px;font-size:14px;font-weight:600;text-decoration:none;box-shadow:0 4px 14px rgba(97,76,225,.4);z-index:60}}
</style></head><body>
<div class="bar"><b>Artvision</b> · <a href="https://artvision.pro/" style="color:#614CE1">artvision.pro</a><span class="doc">USmile · вывеска v6 (графит) · 01.06.2026</span></div>
<div class="wrap">
<h1>Угловая вывеска USmile — v6, знак в графит #1D1D1F</h1>
<p class="note">Исправлено vs v5: знак был красный → теперь графит/чёрный как в официальном логотипе (Ⓤ SMILE). Консольный (флаговый) короб выступает от угла дома — читается с двух сторон. Нажми на фото для увеличения.</p>

<div class="card">
  <h2>День · консольный лайтбокс</h2>
  <p>Графитовый Ⓤ SMILE на белом коробе + фасадный знак + синяя стрелка ко входу.</p>
  <img src="data:image/png;base64,{day}" onclick="zoom(this.src)">
</div>

<div class="card">
  <h2>Ночь · подсветка</h2>
  <p>Подсвеченные панели с графитовым знаком на гранях угла. (композиция отличается от дневной — на обсуждение).</p>
  <img src="data:image/png;base64,{night}" onclick="zoom(this.src)">
</div>

<div class="card">
  <div class="ref"><img src="data:image/png;base64,{sprite}"><span>Эталон знака — официальный логотип Ⓤ SMILE (графит, синие иконки-акцент). По нему правили цвет.</span></div>
</div>
</div>
<div class="lb" id="lb" onclick="this.classList.remove('on')"><img id="lbi"></div>
<div class="foot">Artvision · <a href="https://artvision.pro/">artvision.pro</a> · вывеска USmile v6</div>
<a class="ask" href="https://t.me/AntonKamer">Задать вопрос</a>
<script>function zoom(s){{document.getElementById('lbi').src=s;document.getElementById('lb').classList.add('on')}}</script>
</body></html>"""
out = f"{D}/gallery-v6.html"
with open(out, "w") as f:
    f.write(html)
print(f"OK {out} ({len(html)} bytes)")
