#!/usr/bin/env python3
"""brand-extraction — настоящий фирстиль клиента из CSS sprite сайта.

Применение:
  python3 extract_brand.py --slug usmile --url https://usmile.ru --output /path/to/logo-real/

Создаёт:
  <output>/elements/NN-<selector>.png   — вырезанные элементы
  <output>/vector/favicon.svg            — если есть
  <output>/brand-extracted.yaml          — манифест
"""
import argparse, re, sys, time
import urllib.parse, urllib.request
from collections import Counter
from pathlib import Path


def fetch(url, timeout=30):
    """GET URL → bytes. Хедер User-Agent чтобы не блочили."""
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (brand-extraction; Artvision)"
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def absolutize(base_url, ref):
    """Сделать абсолютным относительный URL/путь."""
    if ref.startswith(("http://", "https://", "//")):
        return ref if not ref.startswith("//") else "https:" + ref
    return urllib.parse.urljoin(base_url, ref)


def parse_css_rules(css_text):
    """Извлечь правила .selector { ... } из (минифицированного) CSS."""
    rules = []
    for m in re.finditer(r'([.#][^{}]*?)\{([^}]*)\}', css_text):
        sel = m.group(1).strip()
        body = m.group(2)
        rules.append((sel, body))
    return rules


def extract_sprite_slices(rules):
    """Для каждого правила со sprite-фоном извлечь координаты+размер."""
    slices = []
    sprite_urls = set()
    for sel, body in rules:
        # эвристика: правило содержит sprite-фон ИЛИ имеет background-position+width+height
        if 'sprite' not in body.lower() and 'background-position' not in body:
            continue
        bp = re.search(r'background-position\s*:\s*(-?\d+)px\s+(-?\d+)px', body)
        w = re.search(r'width\s*:\s*(\d+)px', body)
        h = re.search(r'height\s*:\s*(\d+)px', body)
        sp = re.search(r'background-image\s*:\s*url\(["\']?([^"\']+)["\']?\)', body)
        if sp and ('sprite' in sp.group(1).lower() or 'spritesheet' in sp.group(1).lower()):
            sprite_urls.add(sp.group(1))
        if bp and w and h:
            # имя из первого селектора (если их несколько — берём первый)
            name = sel.split(',')[0].strip().lstrip('.#').replace(' ', '_').replace(':', '-')
            name = re.sub(r'[^a-zA-Z0-9_-]', '_', name)[:60]
            slices.append({
                "name": name,
                "x": int(bp.group(1)),
                "y": int(bp.group(2)),
                "width": int(w.group(1)),
                "height": int(h.group(1)),
            })
    return slices, sprite_urls


def extract_colors(css_text, top=10):
    """Top-N hex-цветов по частоте использования."""
    hexes = re.findall(r'#[0-9a-fA-F]{6}(?![0-9a-fA-F])', css_text)
    return Counter(hexes).most_common(top)


def extract_fonts(css_text):
    """Семейства шрифтов + URL из @font-face. Дедуп по family."""
    seen = {}
    for m in re.finditer(r'@font-face\s*\{([^}]+)\}', css_text):
        body = m.group(1)
        family = re.search(r'font-family\s*:\s*["\']?([^;"\'}]+)', body)
        url_match = re.search(r'src\s*:\s*url\(["\']?([^"\')]+)', body)
        if family:
            fam = family.group(1).strip()
            if fam not in seen:
                seen[fam] = {
                    "family": fam,
                    "url_sample": url_match.group(1).strip() if url_match else None,
                }
    return list(seen.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True, help="client slug (usmile)")
    ap.add_argument("--url", required=True, help="https://client.ru")
    ap.add_argument("--output", required=True, help="path to assets/logo-real/")
    ap.add_argument("--max-sprite-size", type=int, default=5_000_000, help="bytes")
    args = ap.parse_args()

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    (out / "elements").mkdir(exist_ok=True)
    (out / "vector").mkdir(exist_ok=True)

    print(f"[1/7] Fetching HTML {args.url}")
    try:
        html = fetch(args.url).decode("utf-8", errors="ignore")
    except Exception as e:
        sys.exit(f"❌ fetch html: {e}")

    # CSS файлы из <link rel=stylesheet>
    print("[2/7] Parsing CSS links")
    css_links = re.findall(r'<link[^>]+rel=["\']stylesheet["\'][^>]*href=["\']([^"\']+)["\']', html)
    css_links += re.findall(r'<link[^>]+href=["\']([^"\']+\.css[^"\']*)["\']', html)
    css_links = list(dict.fromkeys(css_links))  # dedup, preserve order
    print(f"      found {len(css_links)} css")

    # Все CSS в один текст + запомнить какой URL у какого CSS (для резолва sprite-путей)
    full_css = ""
    css_urls = []  # для резолва относительных путей в sprite-URL
    for ref in css_links:
        css_url = absolutize(args.url, ref)
        try:
            full_css += "\n" + fetch(css_url).decode("utf-8", errors="ignore")
            css_urls.append(css_url)
            print(f"      ok {css_url[:80]}")
        except Exception as e:
            print(f"      skip {css_url[:80]}: {e}")

    print(f"[3/7] CSS total {len(full_css)} bytes")
    rules = parse_css_rules(full_css)
    print(f"      {len(rules)} rules")

    print("[4/7] Extract sprite slices")
    slices, sprite_urls = extract_sprite_slices(rules)
    print(f"      {len(slices)} slices in {len(sprite_urls)} sprite(s)")

    # Скачать sprite-картинки. URL в CSS относится к расположению CSS, не к домену.
    print("[5/7] Download sprites")
    sprite_paths = {}
    # Кандидатные base-URLs для резолва: каждый CSS-файл + корень домена
    candidate_bases = css_urls + [args.url]
    for sp_url in sprite_urls:
        local_name = sp_url.split("/")[-1]
        local_path = out / "vector" / local_name
        success = False
        for base in candidate_bases:
            abs_url = absolutize(base, sp_url)
            try:
                data = fetch(abs_url)
                if len(data) > args.max_sprite_size:
                    print(f"      skip {local_name}: too big {len(data)}")
                    break
                local_path.write_bytes(data)
                sprite_paths[sp_url] = local_path
                print(f"      ✓ {local_name} ({len(data)}b) via {base[:60]}")
                success = True
                break
            except Exception:
                continue
        if not success:
            print(f"      ✗ {local_name}: 404 on all bases")

    # Выбираем основной sprite (предпочитаем @2x если есть)
    main_sprite = None
    for url, path in sprite_paths.items():
        if "2x" in url.lower():
            main_sprite = (url, path)
            break
    if not main_sprite and sprite_paths:
        main_sprite = list(sprite_paths.items())[0]

    if not main_sprite:
        print("⚠️  no sprite — only colors/fonts/favicon will be extracted")
    else:
        # Вырезать каждый slice
        print(f"[6/7] Cut slices from {main_sprite[1].name}")
        try:
            from PIL import Image
            sp_img = Image.open(main_sprite[1]).convert("RGBA")
            is_2x = "2x" in main_sprite[0].lower()
            mult = 2 if is_2x else 1
            for i, s in enumerate(slices, 1):
                x = -s["x"] * mult
                y = -s["y"] * mult
                w = s["width"] * mult
                h = s["height"] * mult
                if x < 0 or y < 0 or x + w > sp_img.width or y + h > sp_img.height:
                    print(f"      skip {s['name']}: coords out of bounds")
                    continue
                crop = sp_img.crop((x, y, x + w, y + h))
                fname = f"{i:02d}-{s['name']}.png"
                crop.save(out / "elements" / fname)
        except ImportError:
            print("⚠️  PIL not available — pip install Pillow")
        except Exception as e:
            print(f"⚠️  cut error: {e}")

    # Favicon
    print("[7/7] Favicon, colors, fonts")
    try:
        fav_url = absolutize(args.url, "/favicon.svg")
        (out / "vector" / "favicon.svg").write_bytes(fetch(fav_url))
        print("      ✓ favicon.svg")
    except Exception as e:
        print(f"      no favicon.svg: {e}")

    colors = extract_colors(full_css, top=10)
    fonts = extract_fonts(full_css)

    # Manifest
    manifest = {
        "client": args.slug,
        "source": args.url,
        "extracted_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "sprite_source": main_sprite[0] if main_sprite else None,
        "colors": [{"hex": c[0], "usages": c[1]} for c in colors],
        "fonts": fonts,
        "elements": [
            {
                "name": s["name"],
                "file": f"elements/{i:02d}-{s['name']}.png",
                "size": [s["width"], s["height"]],
                "bg_position": [s["x"], s["y"]],
            }
            for i, s in enumerate(slices, 1)
        ],
    }
    (out / "brand-extracted.yaml").write_text(
        # Простой YAML вручную (без зависимости)
        f"client: {manifest['client']}\n"
        f"source: {manifest['source']}\n"
        f"extracted_at: {manifest['extracted_at']}\n"
        f"sprite_source: {manifest['sprite_source']}\n"
        f"colors:\n"
        + "".join([f"  - hex: \"{c['hex']}\"\n    usages: {c['usages']}\n" for c in manifest["colors"]])
        + "fonts:\n"
        + "".join([f"  - family: \"{f['family']}\"\n    url_sample: \"{f.get('url_sample') or ''}\"\n" for f in manifest["fonts"]])
        + f"elements_count: {len(manifest['elements'])}\n"
        + "elements:\n"
        + "".join([f"  - name: \"{e['name']}\"\n    file: \"{e['file']}\"\n    size: [{e['size'][0]}, {e['size'][1]}]\n    bg_position: [{e['bg_position'][0]}, {e['bg_position'][1]}]\n" for e in manifest["elements"]])
    )
    print(f"\n✅ Manifest: {out}/brand-extracted.yaml")
    print(f"   colors: {len(colors)}, fonts: {len(fonts)}, elements: {len(slices)}")


if __name__ == "__main__":
    main()
