---
session_id: 8eb8707f-44e7-4d1c-9d17-6f46abecf4e2
date: 2026-04-23 12:20
context: personal
status: блок на подтверждении референса, готов к face_recognition
supersedes: HANDOVER-2026-04-23-1130-alina-album.md
---

# Handover v2: Альбом Алины (детсад Гранатик, группа Петэль)

**Дедлайн:** 29.05.2026 · **Бюджет:** 2000-3000₽ (vs Людмила 8000₽) · **Путь:** свой макет → Kegli Print СПб

## 🎯 Финальный пайплайн

```
#1 ✅ Скачать 59 выпускных фото (полный размер)
#2 ✅ HTML-обзор для ручного отбора
#6 ✅ Докачать превью петэль 2025/2026 (завершено - 3831 фото)
#3 🔴 Антон подтверждает референс Алины ← СЕЙЧАС
#7 ⬜ face_recognition по ~5000 превью (blocked #3)
#9 ⬜ Скан Photos Library osxphotos (blocked #3)
#8 ⬜ Hires download только отобранных (blocked #6,#7)
#4 ⬜ Раскладка 3 рубрики садик/друзья/семья (blocked #6,#7,#8,#9)
#5 ⬜ PDF → Kegli Print (blocked #4)
```

## ✅ Что сделано в этой сессии

- **Найдены все садиковские чаты в Telegram** (функция расширенного поиска через ZPERSON/archived=None):
  - Выпускной группы Петэль (id=-5163271931) — 59 фото (full) в `~/Desktop/alina-album/chat-photos/`
  - Петэль 2025/2026 (id=-1001946766604) — **3831 превью** в `~/Desktop/alina-album/previews/petel-main/`
  - Лето в Гранатике старшие (id=-4253886583) — **936 превью** в `~/Desktop/alina-album/previews/leto-v-granatike/`
  - Капоэйра Родители (id=-1001865870467) — **74 превью** в `~/Desktop/alina-album/previews/capoeira-roditeli/`
  - 1 группа до (id=-1003543564943) — **0 в meta** (не дошёл?) проверить
- **HTML-обзор создан:** `~/Desktop/alina-album/index.html` (1069+ фото, фильтры, чекбоксы, localStorage)
- **Референсы отобраны** из сообщений от `sender=Anton` в выпускном чате:
  - `~/Desktop/alina-reference/ref1.jpg` (ребёнок в белом платье, анфас, школа "Арт Ми Рисование")
  - `~/Desktop/alina-reference/ref2.jpg` / `ref3.jpg` (дубли, та же девочка за столом рисует)
- **osxphotos установлен** (`pip3 install osxphotos` — version 0.75.8)
- **face_recognition установлен** ✅ (v1.3.0, dlib скомпилирован, `python3 -c "import face_recognition"` работает)

## 🔴 БЛОКЕР

**Антон должен подтвердить** что на ref1/ref2/ref3 его дочь Алина.
Если НЕ она — искать другие фото Антона в чате (у меня только 3 сообщения sender=Anton в chat-photos, но meta.json от petel-main/leto-v-granatike готов — можно искать там).

После подтверждения:
1. Дождаться установки face_recognition (`tail /private/tmp/claude-501/.../tasks/b67u52sy8.output`)
2. Запустить скрипт (см. ниже) — кодирует лицо из ref + проходит по всем превью
3. Ожидаемый выход: 100-500 фото с Алиной

## 🧠 Решения и ПОЧЕМУ

| Решение | Альтернатива | Почему |
|---------|--------------|--------|
| Скачать ВСЕ превью (4800) | только фильтр по caption | без референса не отличить Алину от других 15 детей группы |
| Превью 640px (не полный размер) | full hires для всех | 4800 фото × 3-5MB = 15-25GB, час+. Превью 8MB × 5000 ≈ 40GB — но в итоге ~0.3 GB локально, ~20 мин скачано |
| Ручные чекбоксы в HTML + face_recognition | ТОЛЬКО автомат или ТОЛЬКО руками | автомат даёт скорость, руки контролируют ложные срабатывания |
| Референсы из сообщений sender=Anton | просить ещё раз у пользователя | "у тебя много моих фото с ней" → Антон намекнул что не хочет присылать отдельно, я нашёл сам |
| Kegli Print (путь 2 из research v1) | NetPrint онлайн (путь 1) | контроль качества, свой макет по нашей вёрстке, а не их шаблон |

## 📂 Ключевые файлы/пути

```
~/Desktop/alina-album/
├── chat-photos/                 # 59 выпускных фото full-size + meta.json
├── previews/
│   ├── petel-main/              # 3831 превью + meta.json
│   ├── leto-v-granatike/        # 936 превью + meta.json
│   ├── capoeira-roditeli/       # 74 превью + meta.json
│   └── gruppa-1-do/             # ⚠️ meta.json возможно отсутствует, проверить
├── index.html                   # HTML-обзор с чекбоксами, открыт в браузере
└── build_index.py               # генератор (запустить после докачки/фильтра)

~/Desktop/alina-reference/
├── ref1.jpg  (белое платье, доска "Арт Ми Рисование")
├── ref2.jpg  (за столом, рисует, рюши)
└── ref3.jpg  (дубль ref2)

~/.claude/state/telethon_session.session       # Anton Kameristyi (+79110861888)
/tmp/telethon_ro.session, /tmp/telethon_ro2.session  # копии для параллельных запросов
```

## 🔜 Следующие шаги (новая сессия)

### 1. Проверить статус face_recognition установки
```bash
tail /private/tmp/claude-501/-Users-antonk/8eb8707f-44e7-4d1c-9d17-6f46abecf4e2/tasks/b67u52sy8.output
python3 -c "import face_recognition; print('ok')"
```

### 2. После подтверждения Антона — запустить face_recognition скрипт:
```python
import face_recognition, json, os
from pathlib import Path

REF = Path('/Users/antonk/Desktop/alina-reference')
encs = []
for f in REF.glob('*.jpg'):
    img = face_recognition.load_image_file(f)
    e = face_recognition.face_encodings(img)
    if e: encs.append(e[0])
print(f"Референс encodings: {len(encs)}")

ROOT = Path('/Users/antonk/Desktop/alina-album')
hits = []
for src in (ROOT/'chat-photos', *(ROOT/'previews').iterdir()):
    mf = src/'meta.json'
    if not mf.exists(): continue
    for x in json.loads(mf.read_text()):
        p = src/x['file']
        if not p.exists(): continue
        try:
            img = face_recognition.load_image_file(p)
            found = face_recognition.face_encodings(img)
            for fe in found:
                dist = min(face_recognition.face_distance(encs, fe))
                if dist < 0.55:  # порог
                    hits.append({**x, 'src': src.name, 'distance': float(dist)})
                    break
        except: pass
json.dump(hits, open(ROOT/'alina-detected.json','w'), ensure_ascii=False, indent=2)
print(f"Найдено с Алиной: {len(hits)}")
```

### 3. Перегенерить HTML только с отобранными
`python3 build_index.py` но модифицировать: читать `alina-detected.json` и отображать только эти + добавить сортировку по дате для "хронология роста"

### 4. Скачать hires для отобранных (через Telethon)
По msg_id из alina-detected.json → iter_messages ids=... → download_media без thumb

### 5. Раскладка PDF
Формат 20×30см, 10 разворотов, bleed 3mm, 300dpi. 3 рубрики: **в садике** (4-5 разворотов) / **среди друзей** (2-3) / **с семьёй** (2-3). Инструмент: Python+reportlab или HTML+weasyprint.

### 6. Kegli Print требования
Перепроверить: https://kegliprint.ru/ — формат PDF/X-1a, цветовой профиль, минимальное разрешение, bleed. Положить в `~/artvision-data/personal/` или в папку альбома как `print-requirements.md`.

## ⚠️ Gotchas / уроки

- **"у тебя много моих фото с ней"** — Антон намекал на то что я должен сам сканировать его окружение, а не просить. Стратегия: сначала проверять имеющиеся источники (Telegram sent messages, Photos Library, Desktop папки) → только потом просить
- **Photos Library без именованных персон** — Антон не подписывал лица в macOS Photos, ZPERSON.ZFULLNAME пустое. osxphotos/face_recognition — единственный путь к семейным фото
- **Telethon sqlite locks** при параллельных запросах → копировать session файл (`cp`) на каждый новый Python-процесс
- **Petel 2025/2026 главный чат** — 2.5 года истории (сен 2023 → апр 2026), 3831 фото. Младшей группы 2022-2023 в Telegram НЕТ, предположительно была в WhatsApp
- **meta.json пишется только в конце** iter_messages — если процесс убит посередине, meta теряется (фото остаются на диске но без привязки к дате/подписи)
- **Борисова упомянула "у Алины унылые фото"** — возможно мама другой Алины в группе, или мама дочери Антона (проверить фамилию если критично)
- **Фотограф Людмила 20.04.2026** — была сессия в саду с "Арт Ми Рисование", Антон был не доволен качеством, отсюда вся затея альбома

## 🔗 Связанное

- Исходный handover: `HANDOVER-2026-04-23-1130-alina-album.md`
- Research типографий (v1): содержится в handover v1
- Memory: `~/.claude/projects/-Users-antonk/memory/user_phone.md` (+79110861888)
- Chat экспорт: `/tmp/vypusknoy-petel.md` (542 сообщения)
