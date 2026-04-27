---
session_id: e8b48a28
date: 2026-04-24 01:05
context: personal
status: refs подтверждены (неявно), готово к face_recognition → приватный деплой
supersedes: HANDOVER-2026-04-23-1220-alina-album-v2.md
---

# Handover v3: Альбом Алины — запуск face_recognition + приватный деплой

## Что подтверждено в этой сессии

- **Refs** `/Users/antonk/Desktop/alina-reference/ref1.jpg` + `ref2.jpg` (ref3 = дубль ref2) — Антон подтвердил неявно ("только с Алиной"). На ref1 — девочка в белом тюлевом платье, фронтально, доска "Арт Ми Рисование"; на ref2 — она же за столом рисует, 3/4
- **Решение:** деплой только фото с Алиной, приватно (htpasswd), noindex
- **НЕ делать:** публичный деплой всех 4922, даже с noindex

## Следующие шаги (новая сессия, в cwd `~/Desktop/alina-album` или `~/artvision-data`)

### 1. Запустить face_recognition в фоне (15-25 мин)

```bash
cd ~/Desktop/alina-album
python3 << 'PY' > /tmp/alina-fr.log 2>&1 &
import face_recognition, json
from pathlib import Path

REF = Path('/Users/antonk/Desktop/alina-reference')
encs = []
for f in sorted(REF.glob('*.jpg')):
    img = face_recognition.load_image_file(f)
    e = face_recognition.face_encodings(img)
    if e: encs.append(e[0])
print(f"Refs encoded: {len(encs)}")

ROOT = Path('/Users/antonk/Desktop/alina-album')
hits = []
sources = [ROOT/'chat-photos'] + list((ROOT/'previews').iterdir())
for src in sources:
    mf = src/'meta.json'
    if not mf.exists(): continue
    meta = json.loads(mf.read_text())
    meta_by_file = {m['file']: m for m in meta if 'file' in m}
    for p in sorted(src.iterdir()):
        if p.suffix.lower() not in ('.jpg','.jpeg','.png'): continue
        try:
            img = face_recognition.load_image_file(p)
            faces = face_recognition.face_encodings(img)
            for fe in faces:
                dist = min(face_recognition.face_distance(encs, fe))
                if dist < 0.55:
                    m = meta_by_file.get(p.name, {})
                    hits.append({'path': str(p), 'src': src.name,
                                  'file': p.name, 'distance': float(dist),
                                  'date': m.get('date'), 'text': m.get('text','')[:100]})
                    break
        except: pass
json.dump(hits, open(ROOT/'alina-detected.json','w'), ensure_ascii=False, indent=2)
print(f"Matches: {len(hits)}")
PY
echo "Started PID=$!"
```

Мониторить: `tail -f /tmp/alina-fr.log` и `wc -l ~/Desktop/alina-album/alina-detected.json`

### 2. Photos Library scan (параллельно, отдельный процесс)

```bash
python3 -c "
import osxphotos, face_recognition, json
db = osxphotos.PhotosDB()
# TODO: закодировать refs, пройти по db.photos(), compare
"
```

Фильтр: только photos с людьми (`not p.shared`, `p.path`). Ожидаемое: ~200-1000 фото Алины в семейной библиотеке.

### 3. Перегенерить HTML только с Алиной

Модифицировать `~/Desktop/alina-album/build_index.py`:
- Читать `alina-detected.json`
- Показывать только hits
- Сортировка по `date` (хронология)
- Добавить секции: "Садик" (petel-main, leto-v-granatike), "Доп." (capoeira), "Семья" (Photos Library hits)

### 4. Приватный деплой

```bash
# URL: https://artvision.pro/private/alina-<hash>/
HASH=$(openssl rand -hex 4)
ssh root@80.90.181.152 "mkdir -p /var/www/artvision/private/alina-${HASH}"

# htpasswd
ssh root@80.90.181.152 "htpasswd -bc /var/www/artvision/private/alina-${HASH}/.htpasswd anton <PASSWORD>"

# .htaccess
cat > /tmp/alina.htaccess << 'HT'
AuthType Basic
AuthName "Private"
AuthUserFile /var/www/artvision/private/alina-HASH/.htpasswd
Require valid-user
Header set X-Robots-Tag "noindex, nofollow, noarchive"
HT
# заменить HASH и залить

# Upload (только hits, не все 4963)
# Сначала скопировать hits в отдельную папку ~/Desktop/alina-album-filtered/
python3 -c "
import json, shutil
from pathlib import Path
hits = json.load(open('/Users/antonk/Desktop/alina-album/alina-detected.json'))
dst = Path('/Users/antonk/Desktop/alina-album-filtered/photos')
dst.mkdir(parents=True, exist_ok=True)
for h in hits:
    shutil.copy(h['path'], dst/h['file'])
"
# Потом rsync filtered + index.html
rsync -avz ~/Desktop/alina-album-filtered/ root@80.90.181.152:/var/www/artvision/private/alina-${HASH}/
```

### 5. nginx location (если не через .htaccess)

Если apache нет (только nginx) — использовать nginx basic auth:
```nginx
location /private/alina-HASH/ {
    auth_basic "Private";
    auth_basic_user_file /var/www/artvision/private/alina-HASH/.htpasswd;
    add_header X-Robots-Tag "noindex, nofollow, noarchive" always;
}
```

## Gotchas

- face_recognition на 4963 фото: ~15-25 мин на M1 Mac, может больше. Запускать в фоне через `&`, мониторить через `tail`
- Photos Library: osxphotos требует Full Disk Access для Terminal/Ghostty
- htpasswd может не быть на VPS: `apt install apache2-utils`
- nginx уже на VPS (не apache) — значит auth через nginx config, НЕ .htaccess
- Пароль для htpasswd Антон придумает сам или сгенерить `openssl rand -base64 12`
- Hash в URL — чтобы URL не угадать

## TODO при старте новой сессии

1. `git pull ~/artvision-data`
2. `cd ~/Desktop/alina-album`
3. Запустить face_recognition в фоне (команда выше)
4. Пока идёт — читать этот handover
5. Ждать завершения (ping через `tail -f /tmp/alina-fr.log`)
6. Перегенерить HTML
7. Уточнить у Антона: пароль для htpasswd, hash в URL
8. Деплой через rsync + nginx config

## Файлы

- Refs: `~/Desktop/alina-reference/{ref1,ref2,ref3}.jpg`
- Фото: `~/Desktop/alina-album/{chat-photos,previews/*}/*.jpg` (4963 штук)
- Meta: `~/Desktop/alina-album/previews/*/meta.json`
- HTML: `~/Desktop/alina-album/index.html` (будет перегенерён)
- Skip-list (неактуален): `/tmp/alina-skip-list.txt` — можно удалить, face_recognition заменит
- VPS: `80.90.181.152`, `tokens.json → timeweb_cloud.vps`
