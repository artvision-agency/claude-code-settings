#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
kislovodsk-realtime-alert.py — БЫСТРЫЙ real-time алерт БПЛА/воздушной тревоги
по КМВ (Кисловодск/Минводы/Ставрополье) и ж/д-маршруту Ростов→Невинномысск.

Отличие от kislovodsk-safety-digest.py:
  • дайджест = раз в сутки, обзор за 24ч;
  • этот скрипт = каждые ~5 мин, ловит ТОЛЬКО НОВЫЕ сигналы за последние ~10 мин
    из БЫСТРЫХ каналов и сразу шлёт пуш (🔴 КМВ / 🟡 маршрут).

Дедуп ОБЯЗАТЕЛЕН (anti-spam): один инцидент = один пуш. State-файл хранит
high-water-mark message.id по каждому каналу + хеши уже отправленных инцидентов.

Источник: те же публичные TG-каналы (Telethon, userbot-сессия @AntonKamer).
Секреты НЕ в коде (файл синкается в публичный repo) — api_id/api_hash и bot-токен
читаются из ~/artvision-data/tokens.json в рантайме (self-corrections #31).

Эвристика по сводкам каналов, НЕ гарантия. Деградирует при сбое канала/сети
(таймауты, не падает весь job). Лог: ~/.claude/logs/kislovodsk-alert.log
"""

import asyncio
import os
import sys
import json
import shutil
import hashlib
import re
from datetime import datetime, timezone, timedelta

try:
    from telethon import TelegramClient
except ImportError:
    print("ERROR: pip install telethon", file=sys.stderr)
    sys.exit(1)

# ── Пути / секреты (как в дайджесте — один источник) ────────────────────────
TOKENS_JSON = os.path.expanduser('~/artvision-data/tokens.json')
MAIN_SESSION = '/Users/antonk/.claude/state/telethon_session.session'
# отдельная session-копия от дайджеста, чтобы два job'а не лочили один SQLite
SESSION_BASE = '/Users/antonk/.claude/state/telethon_kislovodsk_rt'  # без .session
SESSION_FILE = SESSION_BASE + '.session'
DIGEST_SESSION = '/Users/antonk/.claude/state/telethon_kislovodsk.session'

STATE_FILE = os.path.expanduser('~/.claude/state/kislovodsk-alert-seen.json')
LOG = os.path.expanduser('~/.claude/logs/kislovodsk-alert.log')

ANTON_CHAT = "161261562"
# vps_bot подтверждённо DM-ит Антона; portal_bot на 28.06 даёт 401.
BOT_PREF = ["vps_bot", "portal_bot", "backup_bot"]

MSK = timezone(timedelta(hours=3))
ALERT_WINDOW_MIN = 10        # окно «свежести» сигнала (минуты)
READ_LIMIT = 40              # сколько последних сообщений тянуть на канал
CONNECT_TIMEOUT = 25
CHANNEL_TIMEOUT = 25
MAX_PER_ZONE = 6             # сколько инцидентов показать в одном пуше на зону
INCIDENT_KEEP = 800          # сколько хешей инцидентов хранить в state

# ── БЫСТРЫЕ каналы (zone: kmv | route | both) ───────────────────────────────
#    official  = губернатор (приоритет/достоверность),
#    local     = локальные КМВ (приоритетнее для КМВ),
#    aggregate = быстрые нац. агрегаторы БПЛА (фильтр по зоне)
FAST_CHANNELS = [
    {"u": "VVV5807",        "zone": "kmv",  "name": "Губернатор Ставрополья (офиц.)", "src": "official"},
    {"u": "moy_kislovodsk", "zone": "kmv",  "name": "Мой Кисловодск",   "src": "local"},
    {"u": "Kislovodsx7",    "zone": "kmv",  "name": "Кисловодск Live",   "src": "local"},
    {"u": "MinVody_Life_1", "zone": "kmv",  "name": "МинВоды LIFE",      "src": "local"},
    {"u": "MinvodyOnline",  "zone": "kmv",  "name": "Минводы Онлайн",    "src": "local"},
    {"u": "stav_kray",      "zone": "kmv",  "name": "Ставрополье сейчас", "src": "local"},
    {"u": "minvody26",      "zone": "kmv",  "name": "Минводские круги",  "src": "local"},
    {"u": "mvairport",      "zone": "kmv",  "name": "Аэропорт Минводы",  "src": "local"},
    {"u": "radarrussiia",   "zone": "both", "name": "Радар по РФ | БПЛА", "src": "aggregate"},
    {"u": "astrapress",     "zone": "both", "name": "ASTRA",             "src": "aggregate"},
    {"u": "SHOT_SHOT",      "zone": "both", "name": "SHOT",              "src": "aggregate"},
    {"u": "exilenova_plus", "zone": "both", "name": "Exilenova+",        "src": "aggregate"},
    {"u": "rybar",          "zone": "both", "name": "Рыбарь",            "src": "aggregate"},
    {"u": "bazabazon",      "zone": "both", "name": "Baza",              "src": "aggregate"},
    {"u": "kavkaz_leakbez", "zone": "both", "name": "Кавказ",            "src": "aggregate"},
]

# ── ТОЧНЫЙ словарь (lower-case). PRIMARY = триггер. ──────────────────────────
# Высокоточные слова про БПЛА/воздушную опасность. «удар»/«атака» сами по себе
# шумные (футбол «удар по воротам») — НЕ включены как триггер.
DRONE = ["бпла", "беспилотник", "беспилотн", "шахед", "герань", "geran",
         "fpv", "ударный бпла", "дрон-камикадзе", "вражеский дрон"]
AIRRAID = ["воздушная тревога", "план ковёр", "план ковер", "беспилотная опасность",
           "опасность пролёта", "опасность пролета", "ракетная опасность",
           "ракетопасн", "опасность атаки бпла", "угроза атаки бпла",
           "объявлен план", "объявлена беспилотная", "объявлена опасность"]
PRIMARY = DRONE + AIRRAID
# IMPACT — НЕ триггер сам по себе (нужен PRIMARY рядом), повышает важность.
IMPACT = ["сбит", "сбили", "сбито", "перехвач", "обломк", "прилёт", "прилет",
          "пострадав", "погиб", "разрушен", "возгорание", "пожар на"]
# ОТБОЙ — НЕ алертить (это снятие угрозы)
ALLCLEAR = ["отбой беспилот", "отбой опасн", "отбой воздушн", "угроза мин",
            "опасность мин", "отбой ракетн"]

# зоны
KMV_LOC = ["кисловодск", "минеральные воды", "минводы", "минвод", "ессентуки",
           "пятигорск", "ставрополь", "кмв", "георгиевск", "невинномыс",
           "будённовск", "буденновск", "ставрополье", "ставропольск"]
ROUTE_LOC = ["ростов", "тихорец", "невинномыс", "миллерово", "сулин", "батайск",
             "каменск", "лихая", "ростовск", "краснодарск", "кубан", "аксай",
             "шахт", "новочеркасск"]


def has(text, words):
    return any(w in text for w in words)


def log(line):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(f"{datetime.now(MSK).strftime('%Y-%m-%d %H:%M:%S')} | {line}\n")


# ── State (дедуп) ───────────────────────────────────────────────────────────
def load_state():
    try:
        with open(STATE_FILE, encoding='utf-8') as f:
            st = json.load(f)
        st.setdefault("watermark", {})    # {channel_username: max_seen_id}
        st.setdefault("incidents", [])    # [hash, ...] уже отправленных
        return st
    except Exception:
        return {"watermark": {}, "incidents": []}


def save_state(st):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    # ограничить рост списка инцидентов
    if len(st["incidents"]) > INCIDENT_KEEP:
        st["incidents"] = st["incidents"][-INCIDENT_KEEP:]
    tmp = STATE_FILE + ".tmp"
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(st, f, ensure_ascii=False, indent=1)
    os.replace(tmp, STATE_FILE)


def incident_hash(ch_u, text):
    norm = re.sub(r'\s+', ' ', text).strip().lower()[:120]
    return hashlib.sha1((ch_u + "|" + norm).encode('utf-8')).hexdigest()[:16]


# ── Telethon (как в дайджесте) ──────────────────────────────────────────────
def _telethon_creds():
    try:
        tg = json.load(open(TOKENS_JSON))['telegram']
        return int(tg['api_id']), str(tg['api_hash'])
    except Exception:
        return None, None


def ensure_session():
    """Своя session-копия (auth тот же). Источник копии: основная сессия, либо
    уже готовая копия дайджеста."""
    if not os.path.exists(SESSION_FILE):
        src = MAIN_SESSION if os.path.exists(MAIN_SESSION) else (
            DIGEST_SESSION if os.path.exists(DIGEST_SESSION) else None)
        if not src:
            return False
        shutil.copy2(src, SESSION_FILE)
    try:
        os.chmod(SESSION_FILE, 0o600)
    except OSError:
        pass
    return True


async def _authorized_client(api_id, api_hash, errors):
    for attempt in (1, 2):
        client = TelegramClient(SESSION_BASE, api_id, api_hash)
        try:
            await asyncio.wait_for(client.connect(), timeout=CONNECT_TIMEOUT)
            if await asyncio.wait_for(
                    client.is_user_authorized(), timeout=CONNECT_TIMEOUT):
                return client
        except asyncio.TimeoutError:
            errors.append("connect: TimeoutError")
        except Exception as ex:
            errors.append(f"connect: {type(ex).__name__}")
        try:
            await client.disconnect()
        except Exception:
            pass
        if attempt == 1:
            src = MAIN_SESSION if os.path.exists(MAIN_SESSION) else (
                DIGEST_SESSION if os.path.exists(DIGEST_SESSION) else None)
            if src:
                try:
                    shutil.copy2(src, SESSION_FILE)
                    os.chmod(SESSION_FILE, 0o600)
                except OSError:
                    pass
    errors.append("Telethon НЕ авторизован (сессия)")
    return None


def classify(ch, text):
    """Вернуть (zone, level) или (None, None). zone: 'kmv'|'route'."""
    t = text.lower()
    if has(t, ALLCLEAR):           # отбой — не алертить
        return None, None
    if not has(t, PRIMARY):        # нет триггерного слова
        return None, None
    # КМВ-зона
    if ch["zone"] == "kmv":
        return "kmv", "red"
    if ch["zone"] == "both" and has(t, KMV_LOC):
        return "kmv", "red"
    # Маршрут-зона (нужна локация маршрута + триггер уже есть)
    if has(t, ROUTE_LOC):
        return "route", "yellow"
    return None, None


async def collect(st):
    """Вернуть (incidents, errors, read_any, new_watermark).
    incidents — список новых (не отправленных ранее) сигналов."""
    incidents = []     # {zone, level, ch, name, src, time, snippet, hash, msg_id, impact}
    errors = []
    read_any = False
    new_wm = dict(st["watermark"])

    api_id, api_hash = _telethon_creds()
    if not api_id or not api_hash:
        errors.append("Нет api_id/api_hash в tokens.json")
        return incidents, errors, read_any, new_wm

    client = await _authorized_client(api_id, api_hash, errors)
    if client is None:
        return incidents, errors, read_any, new_wm

    now_utc = datetime.now(timezone.utc)
    since = now_utc - timedelta(minutes=ALERT_WINDOW_MIN)
    seen_hashes = set(st["incidents"])

    try:
        for ch in FAST_CHANNELS:
            u = ch["u"]
            old_wm = st["watermark"].get(u, 0)
            chan_max_seen = old_wm
            matched_unsent_ids = []  # id матчей, которые НЕ дадим перешагнуть watermark пока не отправлены
            try:
                entity = await asyncio.wait_for(
                    client.get_entity(u), timeout=CHANNEL_TIMEOUT)
                msgs = await asyncio.wait_for(
                    client.get_messages(entity, limit=READ_LIMIT),
                    timeout=CHANNEL_TIMEOUT)
                read_any = True
                for m in msgs:
                    if not m.id:
                        continue
                    chan_max_seen = max(chan_max_seen, m.id)
                    # НОВОЕ = id строго больше watermark И в окне свежести
                    if m.id <= old_wm:
                        continue
                    if not (m.date and m.date >= since and m.text):
                        continue
                    zone, level = classify(ch, m.text)
                    if not zone:
                        continue
                    h = incident_hash(u, m.text)
                    if h in seen_hashes:
                        continue          # уже отправляли этот инцидент
                    seen_hashes.add(h)
                    t = m.text.lower()
                    incidents.append({
                        "zone": zone, "level": level, "ch": u,
                        "name": ch["name"], "src": ch["src"],
                        "time": m.date.astimezone(MSK).strftime('%d.%m %H:%M'),
                        "snippet": re.sub(r'\s+', ' ', m.text).strip()[:150],
                        "hash": h, "msg_id": m.id,
                        "impact": has(t, IMPACT),
                    })
                    matched_unsent_ids.append(m.id)
                # watermark по каналу двигаем до максимума прочитанного,
                # НО не дальше самого старого матча (отправку проверим позже).
                if matched_unsent_ids:
                    new_wm[u] = min(matched_unsent_ids) - 1
                    # запомним, чтобы после отправки добить до chan_max_seen
                    new_wm.setdefault("_full", {})
                else:
                    new_wm[u] = chan_max_seen
                # сохраним «потолок» канала для добивания после успешной отправки
                ch["_chan_max"] = chan_max_seen
            except asyncio.TimeoutError:
                errors.append(f"{ch['name']} (@{u}): timeout")
                new_wm[u] = old_wm   # не двигаем при сбое
            except Exception as ex:
                errors.append(f"{ch['name']} (@{u}): {type(ex).__name__}")
                new_wm[u] = old_wm
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass
    return incidents, errors, read_any, new_wm


# ── Bot API push (как в дайджесте) ──────────────────────────────────────────
def _bot_token(name):
    try:
        d = json.load(open(TOKENS_JSON))["telegram"].get(name)
        if isinstance(d, dict):
            return d.get("token")
        return d if isinstance(d, str) else None
    except Exception:
        return None


def send_tg(text):
    """Прямой Bot API → DM Антона. (rc, raw). rc=0 при доставке."""
    import urllib.request
    import urllib.parse
    last = ""
    for bot in BOT_PREF:
        tok = _bot_token(bot)
        if not tok:
            continue
        try:
            data = urllib.parse.urlencode({
                "chat_id": ANTON_CHAT, "text": text,
                "disable_web_page_preview": "true",
                "disable_notification": "false",   # пуш с уведомлением (важно)
            }).encode()
            url = f"https://api.telegram.org/bot{tok}/sendMessage"
            with urllib.request.urlopen(url, data=data, timeout=20) as r:
                raw = r.read().decode()
            if '"ok":true' in raw:
                return 0, f"[{bot}] ok"
            last = f"[{bot}] {raw[:120]}"
        except Exception as ex:
            last = f"[{bot}] {type(ex).__name__}: {str(ex)[:60]}"
            continue
    return 1, last


# ── OSM-карта сигналов (одна картинка на пуш) ───────────────────────────────
# Координаты ЗАПЕЧЕНЫ (детерминированно): геокодированы через Nominatim ОДИН раз
# (28.06.2026, с User-Agent+паузой), сверены на правдоподобность
# (Ставрополье ~44-46N, Ростовская/Кубань ~45-49N, 38-45E). В рантайме — НЕ
# ходим в сеть за геокодом (cron без сетевой зависимости от Nominatim).
COORDS = {
    "Кисловодск": (43.9055, 42.7157),
    "Минеральные Воды": (44.2107, 43.135),
    "Ессентуки": (44.047, 42.8577),
    "Пятигорск": (44.0398, 43.0707),
    "Ставрополь": (45.0433, 41.9691),
    "Невинномысск": (44.6246, 41.9476),
    "Кочубеевское": (44.6867, 41.826),
    "Михайловск": (45.1325, 42.0263),
    "Ростов-на-Дону": (47.2223, 39.7199),
    "Батайск": (47.1385, 39.7423),
    "Новочеркасск": (47.4107, 40.102),
    "Тихорецк": (45.8547, 40.1281),
    "Кавказская": (45.4393, 40.6698),
    "Миллерово": (48.9196, 40.3919),
    "Красный Сулин": (47.8932, 40.058),
    "Сальск": (46.4767, 41.541),
    "Волгоград": (48.7082, 44.5153),
    "Краснодар": (45.0352, 38.9772),
    "Славянск-на-Кубани": (45.2492, 38.1093),
}
# ключевое слово (lower) → ключ COORDS. Длинные/специфичные первыми.
PLACE_KEYS = [
    ("минеральные воды", "Минеральные Воды"), ("минвод", "Минеральные Воды"),
    ("кисловодск", "Кисловодск"), ("ессентуки", "Ессентуки"),
    ("пятигорск", "Пятигорск"), ("невинномыс", "Невинномысск"),
    ("кочубеев", "Кочубеевское"), ("михайловск", "Михайловск"),
    ("славянск-на-кубан", "Славянск-на-Кубани"), ("новочеркасск", "Новочеркасск"),
    ("батайск", "Батайск"), ("тихорец", "Тихорецк"), ("кавказская", "Кавказская"),
    ("миллерово", "Миллерово"), ("сулин", "Красный Сулин"), ("сальск", "Сальск"),
    ("волгоград", "Волгоград"), ("краснодар", "Краснодар"),
    ("ростов", "Ростов-на-Дону"),
]
HOME = "Кисловодск"
COL_KMV = "#ff3b30"     # красный — КМВ
COL_ROUTE = "#ff9500"   # оранжевый — маршрут
COL_HOME = "#1769ff"    # синий — опорный (где мы)
MAP_UA = {"User-Agent": "kislovodsk-safety-map/1.0 (personal monitoring)"}


def detect_places(text):
    """Множество ключей COORDS, упомянутых в тексте (детерминированно)."""
    import re
    t = (text or "").lower()
    found = set()
    for kw, key in PLACE_KEYS:
        if kw in t:
            found.add(key)
    # Ставрополь-ГОРОД: только явные городские формы, НЕ краевое
    # «ставропольского края» (иначе каждое краевое объявление = пин города)
    if (re.search(r'ставрополе[мн]?\b', t)
            or re.search(r'(?:г\.?\s*|город\s+)ставрополь', t)
            or re.search(r'ставрополь(?![а-яё])', t)):
        found.add("Ставрополь")
    return found


def collect_points(incidents):
    """{place_key: zone} по всем инцидентам. zone худший (kmv>route)."""
    pm = {}
    for i in incidents:
        zone = i.get("zone")
        for key in detect_places(i.get("snippet", "")):
            if key in COORDS:
                if pm.get(key) != "kmv":   # kmv приоритетнее route
                    pm[key] = zone if pm.get(key) is None else (
                        "kmv" if (zone == "kmv" or pm[key] == "kmv") else "route")
    return pm


def render_map(point_map):
    """Отрендерить ОДНУ PNG-карту со всеми точками + опорный Кисловодск.
    Возврат: путь к PNG или None (если нет точек/ошибка — не падать)."""
    if not point_map:
        return None
    try:
        from staticmap import StaticMap, CircleMarker, IconMarker  # noqa
    except Exception:
        try:
            from staticmap import StaticMap, CircleMarker
        except Exception:
            return None   # библиотеки нет → фолбэк без карты
    try:
        import tempfile
        m = StaticMap(720, 540,
                      url_template='https://a.tile.openstreetmap.org/{z}/{x}/{y}.png',
                      headers=MAP_UA, tile_request_timeout=20)
        # сначала сигнальные точки
        for key, zone in point_map.items():
            if key == HOME:
                continue
            lat, lon = COORDS[key]
            col = COL_KMV if zone == "kmv" else COL_ROUTE
            m.add_marker(CircleMarker((lon, lat), col, 18))
            m.add_marker(CircleMarker((lon, lat), "#ffffff", 7))
        # опорный Кисловодск (синий «дом») — всегда поверх
        hlat, hlon = COORDS[HOME]
        m.add_marker(CircleMarker((hlon, hlat), "#ffffff", 22))
        m.add_marker(CircleMarker((hlon, hlat), COL_HOME, 16))
        img = m.render()
        fd, path = tempfile.mkstemp(prefix="kmv-alert-map-", suffix=".png")
        os.close(fd)
        img.save(path)
        return path
    except Exception as ex:
        log(f"MAP_RENDER_FAIL {type(ex).__name__}: {str(ex)[:80]}")
        return None


def send_photo(png_path, caption):
    """Отправить фото (карту) с подписью через Bot API sendPhoto (vps_bot).
    (rc, raw). Подпись Telegram ограничивает 1024 симв. — caller следит."""
    import urllib.request
    boundary = "----kmvAlertBoundary7e3f"
    try:
        with open(png_path, "rb") as f:
            photo = f.read()
    except Exception as ex:
        return 1, f"open_png: {type(ex).__name__}"
    last = ""
    for bot in BOT_PREF:
        tok = _bot_token(bot)
        if not tok:
            continue
        parts = []

        def field(name, value):
            parts.append(("--" + boundary + "\r\n"
                          f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
                          + value + "\r\n").encode("utf-8"))
        field("chat_id", ANTON_CHAT)
        field("caption", caption[:1024])
        field("disable_notification", "false")
        head = ("--" + boundary + "\r\n"
                'Content-Disposition: form-data; name="photo"; '
                'filename="map.png"\r\nContent-Type: image/png\r\n\r\n').encode("utf-8")
        body = b"".join(parts) + head + photo + ("\r\n--" + boundary + "--\r\n").encode()
        url = f"https://api.telegram.org/bot{tok}/sendPhoto"
        req = urllib.request.Request(url, data=body, headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}"})
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                raw = r.read().decode()
            if '"ok":true' in raw:
                return 0, f"[{bot}] photo ok"
            last = f"[{bot}] {raw[:120]}"
        except Exception as ex:
            last = f"[{bot}] {type(ex).__name__}: {str(ex)[:60]}"
            continue
    return 1, last


def dispatch_alert(text, incidents):
    """Отправить алерт: карта-картинкой (если есть распознанные точки) + текст;
    иначе обычный текст. t.me-ссылки в тексте сохранены. (rc, raw)."""
    point_map = collect_points(incidents)
    png = render_map(point_map) if point_map else None
    if not png:
        return send_tg(text)   # фолбэк: текст без карты, не падаем
    try:
        if len(text) <= 1024:
            rc, raw = send_photo(png, text)
            if rc != 0:                       # фото не ушло → хотя бы текст
                return send_tg(text)
            return rc, raw + " (map+caption)"
        # текст длиннее лимита caption → фото с краткой подписью + текст отдельно
        rc1, raw1 = send_photo(png, "🗺 Карта сигналов БПЛА (детали ниже)")
        rc2, raw2 = send_tg(text)
        if rc2 != 0:
            return 1, f"text_fail {raw2}"
        return 0, f"[map_rc={rc1}] {raw2} (photo+text)"
    finally:
        try:
            os.remove(png)
        except OSError:
            pass


def build_push(incidents):
    """Сгруппировать новые инциденты в ОДИН пуш (🔴 КМВ + 🟡 маршрут)."""
    kmv = [i for i in incidents if i["zone"] == "kmv"]
    rt = [i for i in incidents if i["zone"] == "route"]
    # уровень шапки = худшее
    head_emoji = "🔴" if kmv else "🟡"
    nowmsk = datetime.now(MSK).strftime('%d.%m %H:%M')
    L = []
    if kmv:
        L.append(f"🔴 БПЛА/ВОЗДУШНАЯ ОПАСНОСТЬ — КМВ/Ставрополье ({nowmsk} МСК)")
    else:
        L.append(f"🟡 БПЛА/угроза на ж/д-маршруте ({nowmsk} МСК)")
    L.append("")

    def block(title, items):
        out = [title]
        for i in items[:MAX_PER_ZONE]:
            mark = "‼️" if i["impact"] else "•"
            tag = "офиц." if i["src"] == "official" else (
                "локальн." if i["src"] == "local" else "агрегатор")
            line = f"{mark} [{i['name']} · {tag} · {i['time']}] {i['snippet']}"
            # кликабельная ссылка на исходное сообщение (публичный @username/<id>)
            if i.get("ch") and i.get("msg_id"):
                line += f" → https://t.me/{i['ch']}/{i['msg_id']}"
            out.append(line)
        extra = len(items) - MAX_PER_ZONE
        if extra > 0:
            out.append(f"   …и ещё {extra} сообщ.")
        return out

    if kmv:
        L += block("🏔 КМВ (Кисловодск/Минводы/Ставрополье):", kmv)
        L.append("")
    if rt:
        L += block("🚆 Маршрут (Ростов→Тихорецкая→Невинномысск):", rt)
        L.append("")
    L.append("⚠️ быстрый сигнал из TG-каналов, не гарантия — сверь с официальным "
             "(губернатор @VVV5807 / МЧС / SMS-оповещение).")
    return head_emoji, '\n'.join(L)


def amain_sync():
    """Синхронная обёртка вокруг асинхронного сбора (проще для launchd)."""
    if not ensure_session():
        log("NO_SESSION: Telethon-сессия недоступна, источники не прочитаны")
        print("NO_SESSION (тихо, пуш не слан)")
        return 0

    st = load_state()
    try:
        incidents, errors, read_any, new_wm = asyncio.run(collect(st))
    except Exception as ex:
        log(f"COLLECT_FAIL {type(ex).__name__}: {str(ex)[:80]}")
        print(f"COLLECT_FAIL {type(ex).__name__}")
        return 0   # не падаем жёстко — попробуем в след. раз

    sent_rc = None
    if incidents:
        head, text = build_push(incidents)
        sent_rc, raw = dispatch_alert(text, incidents)   # карта-картинка + текст
        if sent_rc == 0:
            # успех → фиксируем инциденты + добиваем watermark до потолка каналов
            for i in incidents:
                if i["hash"] not in st["incidents"]:
                    st["incidents"].append(i["hash"])
            for ch in FAST_CHANNELS:
                cm = ch.get("_chan_max")
                if cm is not None:
                    new_wm[ch["u"]] = max(new_wm.get(ch["u"], 0), cm)
            print(text)
            print(f"\n[ALERT SENT {head} incidents={len(incidents)} rc=0]")
        else:
            # НЕ двигаем watermark за неотправленные матчи (retry в след. раз)
            log(f"SEND_FAIL incidents={len(incidents)} {raw}")
            print(f"SEND_FAIL incidents={len(incidents)} {raw}")
    else:
        # ничего нового — просто двигаем watermark и выходим тихо
        for ch in FAST_CHANNELS:
            cm = ch.get("_chan_max")
            if cm is not None:
                new_wm[ch["u"]] = max(new_wm.get(ch["u"], 0), cm)
        print("ТИХО: новых сигналов БПЛА/тревоги за окно нет")

    new_wm.pop("_full", None)
    st["watermark"] = {k: v for k, v in new_wm.items() if isinstance(v, int)}
    save_state(st)

    log(f"incidents={len(incidents)} sent_rc={sent_rc} read_any={read_any} "
        f"errors={len(errors)}" + (f" :: {'; '.join(errors[:4])}" if errors else ""))
    return 0


if __name__ == '__main__':
    sys.exit(amain_sync())
