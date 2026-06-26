#!/usr/bin/env python3
"""
render_check.py — ЗЕРО-ТОКЕН проверка что картинки на странице РЕАЛЬНО рендерятся.

Ловит баг класса «<img> есть в HTML, base64 валиден, но на странице БЕЛО»
(lazy-load не сработал / CSS height:0 / display:none / 0×0) — БЕЗ LLM и vision-моделей.

Метод: Playwright headless грузит URL → для каждого <img> читает
naturalWidth (загрузилась ли картинка) + boundingBox (видна ли, размер >0).

Запуск:
  python3 render_check.py <url> [<url2> ...]
  python3 render_check.py https://artvision.pro/_priv-usmile-parodontologiya/

Выход: таблица «url | всего img | OK | БИТЫХ/НЕВИДИМЫХ» + список проблемных.
Код возврата 1 если есть проблемы (для CI/гейтов).
"""
import sys
from playwright.sync_api import sync_playwright

JS = """() => {
  const out = [];
  document.querySelectorAll('img').forEach((im, i) => {
    const r = im.getBoundingClientRect();
    out.push({
      i,
      src: (im.currentSrc || im.src || '').slice(0, 60),
      natW: im.naturalWidth,        // 0 = не загрузилась
      natH: im.naturalHeight,
      w: Math.round(r.width),       // 0 = невидима/схлопнута
      h: Math.round(r.height),
      lazy: im.loading === 'lazy',
    });
  });
  return out;
}"""


def check(url):
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 390, "height": 900})
        pg.goto(url, wait_until="networkidle", timeout=45000)
        pg.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")  # триггер lazy
        pg.wait_for_timeout(1500)
        imgs = pg.evaluate(JS)
        b.close()
    bad = [im for im in imgs
           if im["natW"] == 0 or im["h"] < 8 or im["w"] < 8]
    return imgs, bad


def main():
    urls = sys.argv[1:]
    if not urls:
        print(__doc__)
        return 1
    any_bad = False
    print(f"{'URL':<60} {'img':>4} {'OK':>4} {'BAD':>4}")
    detail = []
    for u in urls:
        try:
            imgs, bad = check(u)
        except Exception as e:
            print(f"{u[:58]:<60} ERROR: {e}")
            any_bad = True
            continue
        ok = len(imgs) - len(bad)
        flag = "🔴" if bad else "✅"
        print(f"{flag} {u[-57:]:<58} {len(imgs):>4} {ok:>4} {len(bad):>4}")
        if bad:
            any_bad = True
            for im in bad[:10]:
                why = ("not-loaded(natW=0)" if im["natW"] == 0 else f"hidden({im['w']}x{im['h']})")
                detail.append(f"    {u[-40:]}  img#{im['i']} {why} lazy={im['lazy']} src={im['src']}")
    if detail:
        print("\n── ПРОБЛЕМНЫЕ img ──")
        print("\n".join(detail))
    print(f"\n{'🔴 ЕСТЬ невидимые/битые картинки' if any_bad else '✅ все картинки рендерятся'} · 0 LLM-токенов")
    return 1 if any_bad else 0


if __name__ == "__main__":
    sys.exit(main())
