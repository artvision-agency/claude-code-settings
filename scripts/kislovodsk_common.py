#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
kislovodsk_common.py — общий модуль монитора безопасности Кисловодска (КМВ).

Вынесено из kislovodsk-safety-digest.py и kislovodsk-realtime-alert.py всё, что
у них совпадало: словари триггеров/городов, гео-данные (COORDS/PLACE_KEYS),
парсеры мест, Telegram-отправка (Bot API), рендер OSM-карты, session-хелперы.

В скриптах остаётся ТОЛЬКО оркестрация (список каналов, классификация под их
задачу, сборка дайджеста/пуша, какой state/session/log использовать).

ВАЖНО: импорт этого модуля НЕ делает сетевых вызовов (telethon только
импортируется; connect/get_messages — внутри async-функций, вызываются из main).

Секреты НЕ в коде (файлы синкаются в публичный repo): api_id/api_hash и
bot-токены читаются из ~/artvision-data/tokens.json в рантайме (self-corrections #31).

Словари — КОНСОЛИДИРОВАННЫЙ superset обоих скриптов:
  • DRONE — без бесплатного «дрон» (защита real-time от false-🔴 на «квадродрон»),
    с точными «дрон-камикадзе»/«вражеский дрон».
  • AIRRAID/KMV_LOC/ROUTE_LOC — объединение (расширяет recall дайджеста, real-time
    не трогает: real-time режет только KMV_CITY + триггер).
  • ALLCLEAR заменён на is_allclear() (regex) — старый substring ловил «угроза
    МИНеральным Водам» как «угроза мин» (ложный отбой). См. bug #2.
"""

import asyncio
import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import timezone, timedelta

try:
    from telethon import TelegramClient
except ImportError:  # pragma: no cover - проверяется в скриптах
    TelegramClient = None

# ── Пути / секреты ──────────────────────────────────────────────────────────
TOKENS_JSON = os.path.expanduser('~/artvision-data/tokens.json')
# исходная auth-сессия userbot @AntonKamer (рабочие копии делаются из неё)
MAIN_SESSION = '/Users/antonk/.claude/state/telethon_session.session'

MSK = timezone(timedelta(hours=3))
ANTON_CHAT = "161261562"
# vps_bot подтверждённо DM-ит Антона; portal_bot на 28.06 даёт 401.
BOT_PREF = ["vps_bot", "portal_bot", "backup_bot"]

CONNECT_TIMEOUT = 25   # сек на connect/is_user_authorized

# ── Словари триггеров (lower-case) ──────────────────────────────────────────
# DRONE — высокоточные слова про БПЛА. Бесплатное «дрон» НЕ включено: оно ловит
# «квадродрон»/«дрон-шоу» и т.п. → false-🔴 в real-time (там KMV_CITY+триггер).
DRONE = ["бпла", "беспилотник", "беспилотн", "шахед", "герань", "geran",
         "fpv", "ударный бпла", "дрон-камикадзе", "вражеский дрон"]
# AIRRAID — объявления воздушной/ракетной/беспилотной опасности.
AIRRAID = ["воздушная тревога", "план ковёр", "план ковер", "беспилотная опасность",
           "опасность пролёта", "опасность пролета", "ракетная опасность",
           "ракетопасн", "опасность атаки бпла", "угроза атаки бпла",
           "объявлен план", "объявлена беспилотная", "объявлена опасность"]
# PRIMARY — любой триггерный сигнал (БПЛА ИЛИ воздушная тревога).
PRIMARY = DRONE + AIRRAID
# IMPACT — НЕ триггер сам по себе (нужен PRIMARY рядом), повышает важность.
IMPACT = ["сбит", "сбили", "сбито", "перехвач", "обломк", "прилёт", "прилет",
          "пострадав", "погиб", "разрушен", "возгорание", "пожар на"]

# ── Зоны (стеммы — ловят падежи) ────────────────────────────────────────────
# KMV_CITY — УЗКИЙ список ГОРОДОВ-курортов КМВ. Только их явное упоминание даёт
# 🔴 (вариант «б»): отсекает шум частых ОБЩЕКРАЕВЫХ объявлений губернатора.
KMV_CITY = ["кисловодск", "минеральн", "минвод", "ессентук",
            "пятигорск", "железноводск"]
# KMV_LOC — широкая КМВ/краевая зона (для зонирования both-каналов в дайджесте).
KMV_LOC = ["кисловодск", "минеральные воды", "минводы", "минвод", "ессентуки",
           "пятигорск", "ставрополь", "кмв", "георгиевск", "невинномыс",
           "будённовск", "буденновск", "ставрополье", "ставропольск"]
ROUTE_LOC = ["ростов", "тихорец", "невинномыс", "миллерово", "сулин", "батайск",
             "каменск", "лихая", "ростовск", "краснодарск", "кубан", "аксай",
             "шахт", "новочеркасск"]
# транспорт ж/д/аэропорт — для маршрута (дайджест)
TRANSPORT = ["поезд", "поезда", "поездов", "ж/д", "жд ", "железнодорож",
             "электричк", "вокзал", "движение поездов", "состав"]
# сбой/последствие — для маршрута и красного уровня (дайджест)
DISRUPT = ["задержк", "задержив", "отмен", "перекры", "приостановлен",
           "обломк", "повреждён", "повреждена", "поврежден", "эвакуац",
           "изменён график", "изменен график"]

# ── ОТБОЙ (снятие угрозы) — regex, НЕ substring (bug #2) ─────────────────────
# Старый ALLCLEAR=["угроза мин", "опасность мин", ...] ловил «угроза МИНеральным
# Водам» как отбой. Точная функция: «отбой … опасности/тревоги/беспилотн…» ИЛИ
# «опасность/угроза миновала». НЕ срабатывает на «Минеральн/Минвод».
_ALLCLEAR_RE = re.compile(
    r'отбой\w*\b.{0,40}?(?:опасн|тревог|беспилотн|ракетн|угроз)'
    r'|(?:опасност\w*|угроз\w*)\s+миновал'
    r'|миновал\w*\s+(?:опасност|угроз|тревог)',
    re.IGNORECASE | re.DOTALL)


def is_allclear(text):
    """True, если сообщение — ОТБОЙ/снятие угрозы (не алертить)."""
    return bool(_ALLCLEAR_RE.search(text or ""))


# ── Текстовые помощники ─────────────────────────────────────────────────────
def has(text, words):
    return any(w in text for w in words)


def normalize_snippet(text, limit=150):
    """Схлопнуть пробелы, обрезать до limit символов (для показа в сообщении)."""
    return re.sub(r'\s+', ' ', text or '').strip()[:limit]


def tg_link(channel, msg_id):
    """Кликабельная ссылка на исходное публичное сообщение."""
    return f"https://t.me/{channel}/{msg_id}"


def _positions(text, words):
    pos = []
    for w in words:
        start = 0
        while True:
            i = text.find(w, start)
            if i < 0:
                break
            pos.append(i)
            start = i + 1
    return pos


def near(text, words_a, words_b, window):
    """True, если хоть одно слово из words_a встречается в пределах window
    символов от слова из words_b (проверка «триггер рядом с городом»)."""
    t = (text or "").lower()
    pa = _positions(t, [w.lower() for w in words_a])
    pb = _positions(t, [w.lower() for w in words_b])
    if not pa or not pb:
        return False
    return min(abs(a - b) for a in pa for b in pb) <= window


# ── Гео (координаты ЗАПЕЧЕНЫ: геокод Nominatim один раз 28.06.2026, sanity
#    lat 43..49 / lon 38..45; в рантайме за геокодом в сеть НЕ ходим) ──────────
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
    t = (text or "").lower()
    found = set()
    for kw, key in PLACE_KEYS:
        if kw in t:
            found.add(key)
    # Ставрополь-ГОРОД: только явные городские формы, НЕ краевое
    # «ставропольского края» (иначе каждое краевое объявление = пин города).
    if (re.search(r'ставрополе[мн]?\b', t)
            or re.search(r'(?:г\.?\s*|город\s+)ставрополь', t)
            or re.search(r'ставрополь(?![а-яё])', t)):
        found.add("Ставрополь")
    return found


def _item_zone(item):
    """Зона элемента: realtime хранит str ('kmv'/'route'); digest — set."""
    z = item.get("zone")
    if isinstance(z, str):
        return z
    zs = z or set()
    return "kmv" if "kmv" in zs else "route"


def collect_points(items):
    """{place_key: zone} по всем элементам (zone худший: kmv>route)."""
    pm = {}
    for it in items:
        zone = _item_zone(it)
        for key in detect_places(it.get("snippet", "")):
            if key not in COORDS:
                continue
            if pm.get(key) == "kmv":
                continue
            if pm.get(key) is None:
                pm[key] = zone
            else:
                pm[key] = "kmv" if (zone == "kmv" or pm[key] == "kmv") else "route"
    return pm


# ── Telegram Bot API ────────────────────────────────────────────────────────
def _bot_token(name):
    try:
        d = json.load(open(TOKENS_JSON))["telegram"].get(name)
        if isinstance(d, dict):
            return d.get("token")
        return d if isinstance(d, str) else None
    except Exception:
        return None


def send_tg(text, disable_preview=True, notify=True, tg_send_fallback=None):
    """Прямой Bot API → DM Антона, перебор живых ботов. (rc, raw). rc=0 при ok.
    tg_send_fallback — путь к tg-send.sh (последний шанс, если все боты молчат)."""
    import urllib.request
    import urllib.parse
    last = ""
    for bot in BOT_PREF:
        tok = _bot_token(bot)
        if not tok:
            continue
        try:
            params = {"chat_id": ANTON_CHAT, "text": text,
                      "disable_notification": "false" if notify else "true"}
            if disable_preview:
                params["disable_web_page_preview"] = "true"
            data = urllib.parse.urlencode(params).encode()
            url = f"https://api.telegram.org/bot{tok}/sendMessage"
            with urllib.request.urlopen(url, data=data, timeout=20) as r:
                raw = r.read().decode()
            if '"ok":true' in raw:
                return 0, f"[{bot}] {raw}"
            last = f"[{bot}] {raw[:200]}"
        except Exception as ex:
            last = f"[{bot}] {type(ex).__name__}: {str(ex)[:80]}"
            continue
    if tg_send_fallback:
        try:
            res = subprocess.run([tg_send_fallback, "anton", text],
                                 capture_output=True, text=True, timeout=120)
            if res.returncode == 0 and '"ok":false' not in (res.stdout + res.stderr):
                return 0, "[tg-send.sh] " + (res.stdout + res.stderr).strip()
        except Exception as ex:
            last += f" | tg-send.sh {type(ex).__name__}"
    return 1, last


_BOUNDARY = "----kmvSafetyBoundary7e3f"


def send_photo(png_path, caption, notify=True):
    """sendPhoto (перебор ботов) — карта с подписью. (rc, raw). caption ≤1024."""
    import urllib.request
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
            parts.append(("--" + _BOUNDARY + "\r\n"
                          f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
                          + value + "\r\n").encode("utf-8"))
        field("chat_id", ANTON_CHAT)
        field("caption", caption[:1024])
        field("disable_notification", "false" if notify else "true")
        head = ("--" + _BOUNDARY + "\r\n"
                'Content-Disposition: form-data; name="photo"; '
                'filename="map.png"\r\nContent-Type: image/png\r\n\r\n').encode("utf-8")
        body = b"".join(parts) + head + photo + ("\r\n--" + _BOUNDARY + "--\r\n").encode()
        url = f"https://api.telegram.org/bot{tok}/sendPhoto"
        req = urllib.request.Request(url, data=body, headers={
            "Content-Type": f"multipart/form-data; boundary={_BOUNDARY}"})
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


def render_map(point_map, log_fn=None, prefix="kmv-map-"):
    """Одна PNG-карта со всеми точками + опорный Кисловодск. None при ошибке/нет
    точек/нет staticmap (фолбэк на текст — не падаем)."""
    if not point_map:
        return None
    try:
        from staticmap import StaticMap, CircleMarker
    except Exception:
        return None
    try:
        m = StaticMap(720, 540,
                      url_template='https://a.tile.openstreetmap.org/{z}/{x}/{y}.png',
                      headers=MAP_UA, tile_request_timeout=20)
        for key, zone in point_map.items():
            if key == HOME:
                continue
            lat, lon = COORDS[key]
            col = COL_KMV if zone == "kmv" else COL_ROUTE
            m.add_marker(CircleMarker((lon, lat), col, 18))
            m.add_marker(CircleMarker((lon, lat), "#ffffff", 7))
        hlat, hlon = COORDS[HOME]
        m.add_marker(CircleMarker((hlon, hlat), "#ffffff", 22))
        m.add_marker(CircleMarker((hlon, hlat), COL_HOME, 16))
        img = m.render()
        fd, path = tempfile.mkstemp(prefix=prefix, suffix=".png")
        os.close(fd)
        img.save(path)
        return path
    except Exception as ex:
        if log_fn:
            log_fn(f"MAP_RENDER_FAIL {type(ex).__name__}: {str(ex)[:80]}")
        return None


def dispatch_with_map(text, items, short_caption, log_fn=None,
                      tg_send_fallback=None, map_prefix="kmv-map-"):
    """Отправить: карта-картинкой (если есть распознанные точки) + текст; иначе
    обычный текст. t.me-ссылки в тексте сохранены. (rc, raw)."""
    point_map = collect_points(items)
    png = render_map(point_map, log_fn=log_fn, prefix=map_prefix) if point_map else None
    if not png:
        return send_tg(text, tg_send_fallback=tg_send_fallback)
    try:
        if len(text) <= 1024:
            rc, raw = send_photo(png, text)
            if rc != 0:                       # фото не ушло → хотя бы текст
                return send_tg(text, tg_send_fallback=tg_send_fallback)
            return rc, raw + " (map+caption)"
        # текст длиннее лимита caption → фото с краткой подписью + текст отдельно
        rc1, raw1 = send_photo(png, short_caption)
        rc2, raw2 = send_tg(text, tg_send_fallback=tg_send_fallback)
        if rc2 != 0:
            return 1, f"text_fail {raw2}"
        return 0, f"[map_rc={rc1}] {raw2} (photo+text)"
    finally:
        try:
            os.remove(png)
        except OSError:
            pass


# ── Telethon session-хелперы ────────────────────────────────────────────────
def telethon_creds(tokens_json=TOKENS_JSON):
    """(api_id:int, api_hash:str) из tokens.json или (None, None)."""
    try:
        tg = json.load(open(tokens_json))['telegram']
        return int(tg['api_id']), str(tg['api_hash'])
    except Exception:
        return None, None


def _secure(path):
    """Telethon .session = SQLite с авторизацией → строго 0600 (не 0644)."""
    try:
        if path and os.path.exists(path):
            os.chmod(path, 0o600)
    except OSError:
        pass


def ensure_session_copy(session_file, extra_src=None):
    """Гарантировать рабочую session-копию (auth тот же, отдельный файл — не
    конфликтует с демоном на основной сессии). Также chmod 600 исходной
    auth-сессии (bug #6 — она бывает world-readable 0644). Возвращает bool."""
    _secure(MAIN_SESSION)          # bug #6: source auth session → 600
    _secure(extra_src)
    if not os.path.exists(session_file):
        src = MAIN_SESSION if os.path.exists(MAIN_SESSION) else (
            extra_src if (extra_src and os.path.exists(extra_src)) else None)
        if not src:
            return False
        shutil.copy2(src, session_file)
    _secure(session_file)
    return True


async def authorized_client(session_base, api_id, api_hash, errors,
                            session_file, extra_src=None,
                            connect_timeout=CONNECT_TIMEOUT):
    """Подключить клиента (с таймаутом), при необходимости пере-скопировать
    исходную сессию и зайти повторно. Возвращает авторизованного клиента или
    None. Сам закрывает неудачные/неавторизованные соединения."""
    for attempt in (1, 2):
        client = TelegramClient(session_base, api_id, api_hash)
        try:
            await asyncio.wait_for(client.connect(), timeout=connect_timeout)
            if await asyncio.wait_for(
                    client.is_user_authorized(), timeout=connect_timeout):
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
                extra_src if (extra_src and os.path.exists(extra_src)) else None)
            if src:
                try:
                    shutil.copy2(src, session_file)
                    _secure(session_file)
                except OSError:
                    pass
    errors.append("Telethon НЕ авторизован (сессия)")
    return None
