#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
kislovodsk-safety-digest.py — ежедневный TG-дайджест «уровень безопасности»
для поездки в Кисловодск (КМВ) и по ж/д-маршруту СПб → Кисловодск через
Ростовскую обл. Оценка рисков от ударов БПЛА по югу РФ для путешественника.

Источник: публичные TG-каналы оповещения/новостей (Telethon, userbot-сессия).
Отправка: ~/.claude/scripts/tg-send.sh anton "<digest>".
Лог: ~/.claude/logs/kislovodsk-safety.log

Эвристика по сводкам каналов за 24ч, НЕ гарантия. Деградирует при недоступности
источника (шлёт дайджест с пометкой «данные частичные»).
"""

import asyncio
import os
import sys
import shutil
import subprocess
import re
from datetime import datetime, timezone, timedelta

try:
    from telethon import TelegramClient
except ImportError:
    print("ERROR: pip install telethon", file=sys.stderr)
    sys.exit(1)

# ── Telethon (та же учётка userbot @AntonKamer, отдельная session-копия,
#    т.к. основная telethon_session занята демоном tg-listener).
#    Секрет НЕ хранится в скрипте (этот файл синкается в публичный repo) —
#    api_id/api_hash читаются из ~/artvision-data/tokens.json в рантайме,
#    как bot-токены (self-corrections #31). ───────────────────────────────────
TOKENS_JSON = os.path.expanduser('~/artvision-data/tokens.json')
MAIN_SESSION = '/Users/antonk/.claude/state/telethon_session.session'
SESSION_BASE = '/Users/antonk/.claude/state/telethon_kislovodsk'  # без .session
SESSION_FILE = SESSION_BASE + '.session'


def _telethon_creds():
    """Вернуть (api_id:int, api_hash:str) из tokens.json или (None, None)."""
    try:
        import json
        tg = json.load(open(TOKENS_JSON))['telegram']
        return int(tg['api_id']), str(tg['api_hash'])
    except Exception:
        return None, None

LOG = os.path.expanduser('~/.claude/logs/kislovodsk-safety.log')
TG_SEND = os.path.expanduser('~/.claude/scripts/tg-send.sh')
HOURS = 24
MSK = timezone(timedelta(hours=3))

# ── Каналы (zone: kmv | route | both). both = нац. БПЛА-мониторинг,
#    его текст сканируется ПО ОБЕИМ зонам ────────────────────────────────────
CHANNELS = [
    # ── ОФИЦИАЛЬНЫЙ (приоритет для КМВ — губернатор лично объявляет режим БПЛА) ──
    {"u": "VVV5807",        "zone": "kmv",  "name": "Губернатор Ставрополья Владимиров (офиц.)"},
    # КМВ / Минводы / Кисловодск (локальные — приоритетнее для КМВ)
    {"u": "moy_kislovodsk", "zone": "kmv",  "name": "Мой Кисловодск"},
    {"u": "Kislovodsx7",    "zone": "kmv",  "name": "Кисловодск Live"},
    {"u": "MinVody_Life_1", "zone": "kmv",  "name": "МинВоды LIFE"},
    {"u": "MinvodyOnline",  "zone": "kmv",  "name": "Минводы Онлайн"},
    {"u": "mvairport",      "zone": "kmv",  "name": "Аэропорт Минводы"},
    {"u": "stav_kray",      "zone": "kmv",  "name": "Ставрополье сейчас"},
    {"u": "minvody26",      "zone": "kmv",  "name": "Минводские круги"},
    # Быстрый агрегатор БПЛА по всей РФ — фильтруется по зонам КМВ/маршрут
    {"u": "radarrussiia",   "zone": "both", "name": "Радар по РФ | БПЛА (быстрый)"},
    # Нац. мониторинг БПЛА/обстановки (ловит и КМВ, и Ростовскую обл.)
    {"u": "astrapress",     "zone": "both", "name": "ASTRA"},
    {"u": "exilenova_plus", "zone": "both", "name": "Exilenova+"},
    {"u": "SHOT_SHOT",      "zone": "both", "name": "SHOT"},
    {"u": "bazabazon",      "zone": "both", "name": "Baza"},
    {"u": "rybar",          "zone": "both", "name": "Рыбарь"},
    {"u": "kavkaz_leakbez", "zone": "both", "name": "Кавказ"},
]

# ── Ключевые слова (lower-case) ─────────────────────────────────────────────
# KMV_CITY — УЗКИЙ список ГОРОДОВ-курортов КМВ. Их явное упоминание = 🔴 (вариант
# «б»). Общекраевые объявления (без города) = 🟡-информер. KMV_LOC оставлен для
# зонирования (краевое тоже попадает в КМВ-блок дайджеста как информер).
# основы-стеммы (ловят падежи: Кисловодске, Ессентуках, Минеральными Водами…)
KMV_CITY = ["кисловодск", "минеральн", "минвод", "ессентук",
            "пятигорск", "железноводск"]
KMV_LOC = ["кисловодск", "минеральные воды", "минводы", "минвод", "ессентуки",
           "пятигорск", "ставрополь", "кмв", "георгиевск", "невинномыс"]
ROUTE_LOC = ["ростов", "тихорец", "невинномыс", "миллерово", "сулин", "батайск",
             "каменск", "лихая", "ростовск", "краснодарск", "кубан"]

# угроза БПЛА/воздушная — ВЫСОКОТОЧНЫЕ слова (не ловят спорт/погоду).
# Спец: "удар"/"атака" сами по себе шумные (футбол "удар по воротам") — убраны.
DRONE = ["бпла", "беспилотник", "беспилотн", "дрон", "шахед", "герань",
         "geran", "fpv", "ударный бпла"]
AIRRAID = ["план ковёр", "план ковер", "воздушная тревога", "ракетная опасность",
           "ракетопасн", "опасность атаки бпла", "угроза атаки бпла",
           "объявлен план", "беспилотная опасность"]
# транспорт ж/д/аэропорт — для маршрута
TRANSPORT = ["поезд", "поезда", "поездов", "ж/д", "жд ", "железнодорож",
             "электричк", "вокзал", "движение поездов", "состав"]
# сбой/последствие — для маршрута и красного уровня
DISRUPT = ["задержк", "задержив", "отмен", "перекры", "приостановлен",
           "обломк", "повреждён", "повреждена", "поврежден", "эвакуац",
           "изменён график", "изменен график"]
# красный уровень — прямое последствие удара/закрытие (только вместе с угрозой)
RED_IMPACT = ["пострадав", "погиб", "повреждён", "повреждена", "поврежден",
              "разрушен", "эвакуац", "прилёт", "прилет", "возгорание",
              "пожар на", "закрыт аэропорт", "аэропорт закрыт"]

now_utc = datetime.now(timezone.utc)
since = now_utc - timedelta(hours=HOURS)


def has(text, words):
    return any(w in text for w in words)


def ensure_session():
    """Гарантировать рабочую session-копию (auth тот же, отдельный файл —
    не конфликтует с демоном на основной сессии)."""
    if not os.path.exists(SESSION_FILE):
        if os.path.exists(MAIN_SESSION):
            shutil.copy2(MAIN_SESSION, SESSION_FILE)
        else:
            return False
    # Telethon .session = SQLite с авторизацией → строго 0600 (не 0644)
    try:
        os.chmod(SESSION_FILE, 0o600)
    except OSError:
        pass
    return True


# Таймауты, чтобы launchd-job не подвисал на сетевой операции Telethon
CONNECT_TIMEOUT = 25   # сек на connect
CHANNEL_TIMEOUT = 25   # сек на get_entity/get_messages одного канала


async def _authorized_client(api_id, api_hash, errors):
    """Подключить клиента (с таймаутом), при необходимости пере-скопировать
    main-сессию и зайти повторно. Возвращает авторизованного клиента или None.
    Сам закрывает неудачные/неавторизованные соединения."""
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
        # на первой попытке — пере-скопировать main-сессию (auth тот же)
        if attempt == 1 and os.path.exists(MAIN_SESSION):
            try:
                shutil.copy2(MAIN_SESSION, SESSION_FILE)
                os.chmod(SESSION_FILE, 0o600)
            except OSError:
                pass
    errors.append("Telethon НЕ авторизован (сессия)")
    return None


async def collect():
    """Вернуть (matches, errors) где matches — список dict с разбором."""
    matches = []   # {zone_hit:set, level:'red'/'yellow', ch, name, time, snippet, airport:bool}
    errors = []
    read_any = False

    api_id, api_hash = _telethon_creds()
    if not api_id or not api_hash:
        errors.append("Нет api_id/api_hash в tokens.json")
        return matches, errors, read_any

    client = await _authorized_client(api_id, api_hash, errors)
    if client is None:
        return matches, errors, read_any

    try:
        for ch in CHANNELS:
            try:
                entity = await asyncio.wait_for(
                    client.get_entity(ch["u"]), timeout=CHANNEL_TIMEOUT)
                msgs = await asyncio.wait_for(
                    client.get_messages(entity, limit=80),
                    timeout=CHANNEL_TIMEOUT)
                read_any = True
                for m in msgs:
                    if not (m.date and m.date >= since and m.text):
                        continue
                    t = m.text.lower()
                    tm = m.date.astimezone(MSK).strftime('%d.%m %H:%M')
                    snippet = re.sub(r'\s+', ' ', m.text).strip()[:140]

                    # угроза = БПЛА/воздушная тревога (высокоточно)
                    threat_hit = has(t, DRONE) or has(t, AIRRAID)
                    # аэропорт Минвод — закрытие/ограничение
                    airport_hit = ("аэропорт" in t and has(t, KMV_LOC) and
                                   has(t, ["закрыт", "ограничен", "не приним",
                                           "план ковёр", "план ковер", "задерж",
                                           "отмен"]))

                    zone_hits = set()
                    # КМВ-зона: для kmv-каналов достаточно угрозы; для both — нужна KMV-локация
                    if threat_hit:
                        if ch["zone"] == "kmv":
                            zone_hits.add("kmv")
                        elif ch["zone"] == "both" and has(t, KMV_LOC):
                            zone_hits.add("kmv")
                    # Маршрут-зона: локация маршрута + (угроза ИЛИ транспорт+сбой)
                    if has(t, ROUTE_LOC) and (threat_hit or
                                              (has(t, TRANSPORT) and has(t, DISRUPT))):
                        zone_hits.add("route")

                    if not zone_hits and not airport_hit:
                        continue

                    # вариант «б»: 🔴 ТОЛЬКО при явном КМВ-ГОРОДЕ + триггере;
                    # общекраевое (zone=kmv канала губернатора, без города) = 🟡
                    # информер. RED_IMPACT теперь лишь усиливает (город+последствие).
                    level = "red" if (threat_hit and has(t, KMV_CITY)) else "yellow"
                    matches.append({
                        "zone": zone_hits, "level": level, "ch": ch["u"],
                        "name": ch["name"], "time": tm, "snippet": snippet,
                        "airport": airport_hit, "mid": m.id,
                    })
            except asyncio.TimeoutError:
                errors.append(f"{ch['name']} (@{ch['u']}): timeout")
            except Exception as ex:
                errors.append(f"{ch['name']} (@{ch['u']}): {type(ex).__name__}")
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass
    return matches, errors, read_any


def zone_summary(matches, zone):
    items = [m for m in matches if zone in m["zone"]]
    if not items:
        return "🟢", "тихо, значимых сообщений нет", []
    red = [m for m in items if m["level"] == "red"]
    pick = (red or items)[:3]
    lvl = "🔴" if red else "🟡"
    txt = "ПРЯМЫЕ инциденты/удары" if red else "были упоминания угрозы/тревоги/ограничений"
    return lvl, txt, pick


def fmt_evidence(items):
    # ссылка на исходное сообщение для публичных каналов (@username/<msg.id>)
    out = []
    for m in items:
        line = f"• [{m['name']} {m['time']}] {m['snippet']}"
        if m.get("ch") and m.get("mid"):
            line += f" → https://t.me/{m['ch']}/{m['mid']}"
        out.append(line)
    return out


def build_digest(matches, errors, read_any):
    nowmsk = datetime.now(MSK).strftime('%d.%m %H:%M')
    partial = (not read_any) or bool(errors)

    kmv_lvl, kmv_txt, kmv_ev = zone_summary(matches, "kmv")
    rt_lvl, rt_txt, rt_ev = zone_summary(matches, "route")

    # аэропорт
    air = [m for m in matches if m["airport"]]
    if air:
        air_line = "⚠️ есть сообщения об ограничениях/задержках: " + air[0]["snippet"][:90]
    else:
        air_line = "штатно (за 24ч сообщений об ограничениях нет)"

    # общий уровень = худший из зон
    order = {"🟢": 0, "🟡": 1, "🔴": 2}
    overall = max([kmv_lvl, rt_lvl], key=lambda x: order[x])
    if overall == "🔴":
        overall_txt = "есть прямые инциденты — проверь детали ниже"
        rec = "следить за обстановкой, закладывать запас времени, гибкий план"
    elif overall == "🟡":
        overall_txt = "фоновая угроза БПЛА по югу / возможны сбои на маршруте"
        rec = "ехать можно, заложить запас по времени и следить за каналами Минвод"
    else:
        overall_txt = "за 24ч значимых событий по КМВ и маршруту не зафиксировано"
        rec = "ехать спокойно, плановых ограничений нет"

    L = []
    L.append(f"🛡 Безопасность Кисловодск/маршрут — {nowmsk} МСК")
    if partial:
        L.append("⚠️ данные частичные (часть источников недоступна)")
    L.append("")
    L.append(f"Общий уровень: {overall} — {overall_txt}")
    L.append("")
    L.append(f"🏔 КМВ/Минводы (24ч): {kmv_lvl} {kmv_txt}")
    for e in fmt_evidence(kmv_ev):
        L.append(f"   {e}")
    L.append("")
    L.append(f"🚆 Маршрут Ростов→Тихорецкая→Невинномысск (24ч): {rt_lvl} {rt_txt}")
    for e in fmt_evidence(rt_ev):
        L.append(f"   {e}")
    L.append("")
    L.append(f"✈️ Аэропорт Минводы: {air_line}")
    L.append("")
    L.append(f"Рекомендация: {rec}")
    if errors:
        L.append("")
        L.append("Недоступные источники: " + "; ".join(errors[:6]))
    L.append("")
    L.append("— эвристика по сводкам TG-каналов за 24ч, не гарантия безопасности")
    return overall, '\n'.join(L)


def log(line):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(f"{datetime.now(MSK).strftime('%Y-%m-%d %H:%M:%S')} | {line}\n")


ANTON_CHAT = "161261562"
# TOKENS_JSON определён выше (один источник секретов).
# Порядок предпочтения ботов: vps_bot подтверждённо DM-ит Антона; portal_bot
# (которым пользуется tg-send.sh) на 28.06.2026 даёт 401 Unauthorized.
# Секрет НЕ хранится в скрипте (этот файл синкается в публичный repo) — токен
# читается из tokens.json (artvision-data) в рантайме, как notify-telegram.sh.
BOT_PREF = ["vps_bot", "portal_bot", "backup_bot"]


def _bot_token(name):
    try:
        import json
        d = json.load(open(TOKENS_JSON))["telegram"].get(name)
        if isinstance(d, dict):
            return d.get("token")
        return d if isinstance(d, str) else None
    except Exception:
        return None


def send_tg(text):
    """Прямой Bot API → DM Антона. Возвращает (rc, raw). rc=0 при доставке.
    Перебирает живые боты (tg-send.sh/portal_bot мёртв 401)."""
    import urllib.request
    import urllib.parse
    last = ""
    for bot in BOT_PREF:
        tok = _bot_token(bot)
        if not tok:
            continue
        try:
            data = urllib.parse.urlencode(
                {"chat_id": ANTON_CHAT, "text": text}).encode()
            url = f"https://api.telegram.org/bot{tok}/sendMessage"
            with urllib.request.urlopen(url, data=data, timeout=20) as r:
                raw = r.read().decode()
            if '"ok":true' in raw:
                return 0, f"[{bot}] {raw}"
            last = f"[{bot}] {raw}"
        except Exception as ex:
            last = f"[{bot}] {type(ex).__name__}: {str(ex)[:80]}"
            continue
    # последний шанс — общий tg-send.sh (если portal_bot оживёт)
    try:
        res = subprocess.run([TG_SEND, "anton", text],
                             capture_output=True, text=True, timeout=120)
        if res.returncode == 0 and '"ok":false' not in (res.stdout + res.stderr):
            return 0, "[tg-send.sh] " + (res.stdout + res.stderr).strip()
    except Exception as ex:
        last += f" | tg-send.sh {type(ex).__name__}"
    return 1, last


# ── OSM-карта сигналов (одна картинка к дайджесту) ──────────────────────────
# Координаты ЗАПЕЧЕНЫ (геокод Nominatim ОДИН раз 28.06.2026, сверены на
# правдоподобность). В рантайме сети за геокодом НЕ ходим.
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
COL_KMV = "#ff3b30"
COL_ROUTE = "#ff9500"
COL_HOME = "#1769ff"
MAP_UA = {"User-Agent": "kislovodsk-safety-map/1.0 (personal monitoring)"}


def detect_places(text):
    t = (text or "").lower()
    found = set()
    for kw, key in PLACE_KEYS:
        if kw in t:
            found.add(key)
    # Ставрополь-ГОРОД только явно (НЕ «ставропольского края» — краевое)
    if (re.search(r'ставрополе[мн]?\b', t)
            or re.search(r'(?:г\.?\s*|город\s+)ставрополь', t)
            or re.search(r'ставрополь(?![а-яё])', t)):
        found.add("Ставрополь")
    return found


def collect_points(matches):
    """{place_key: 'kmv'/'route'} по матчам дайджеста (zone — set)."""
    pm = {}
    for m in matches:
        zset = m.get("zone") or set()
        zone = "kmv" if "kmv" in zset else "route"
        for key in detect_places(m.get("snippet", "")):
            if key in COORDS:
                if pm.get(key) != "kmv":
                    pm[key] = "kmv" if (zone == "kmv") else (pm.get(key) or "route")
    return pm


def render_map(point_map):
    """Одна PNG-карта со всеми точками + опорный Кисловодск. None при ошибке."""
    if not point_map:
        return None
    try:
        from staticmap import StaticMap, CircleMarker
    except Exception:
        return None
    try:
        import tempfile
        mp = StaticMap(720, 540,
                       url_template='https://a.tile.openstreetmap.org/{z}/{x}/{y}.png',
                       headers=MAP_UA, tile_request_timeout=20)
        for key, zone in point_map.items():
            if key == HOME:
                continue
            lat, lon = COORDS[key]
            col = COL_KMV if zone == "kmv" else COL_ROUTE
            mp.add_marker(CircleMarker((lon, lat), col, 18))
            mp.add_marker(CircleMarker((lon, lat), "#ffffff", 7))
        hlat, hlon = COORDS[HOME]
        mp.add_marker(CircleMarker((hlon, hlat), "#ffffff", 22))
        mp.add_marker(CircleMarker((hlon, hlat), COL_HOME, 16))
        img = mp.render()
        fd, path = tempfile.mkstemp(prefix="kmv-digest-map-", suffix=".png")
        os.close(fd)
        img.save(path)
        return path
    except Exception as ex:
        log(f"MAP_RENDER_FAIL {type(ex).__name__}: {str(ex)[:80]}")
        return None


def send_photo(png_path, caption):
    """sendPhoto (vps_bot) — карта с подписью. (rc, raw). caption ≤1024."""
    import urllib.request
    boundary = "----kmvDigestBoundary7e3f"
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


def dispatch_digest(text, matches):
    """Дайджест: карта-картинкой (если есть точки) + текст; иначе текст. (rc, raw)."""
    point_map = collect_points(matches)
    png = render_map(point_map) if point_map else None
    if not png:
        return send_tg(text)
    try:
        if len(text) <= 1024:
            rc, raw = send_photo(png, text)
            if rc != 0:
                return send_tg(text)
            return rc, raw + " (map+caption)"
        rc1, raw1 = send_photo(png, "🗺 Карта обстановки КМВ/маршрут (дайджест ниже)")
        rc2, raw2 = send_tg(text)
        if rc2 != 0:
            return 1, f"text_fail {raw2}"
        return 0, f"[map_rc={rc1}] {raw2} (photo+text)"
    finally:
        try:
            os.remove(png)
        except OSError:
            pass


async def amain():
    if not ensure_session():
        digest = ("🛡 Безопасность Кисловодск/маршрут\n⚠️ данные частичные: "
                  "Telethon-сессия недоступна. Источники не прочитаны.")
        rc, out = send_tg(digest)
        log(f"NO_SESSION sent rc={rc} {out[:120]}")
        print(digest)
        return

    try:
        matches, errors, read_any = await collect()
    except Exception as ex:
        errors = [f"collect fail: {type(ex).__name__}: {str(ex)[:80]}"]
        matches, read_any = [], False

    overall, digest = build_digest(matches, errors, read_any)
    rc, out = dispatch_digest(digest, matches)   # карта-картинка + текст
    msg_id = ""
    m = re.search(r'"message_id":(\d+)', out)
    if m:
        msg_id = m.group(1)
    log(f"level={overall} matches={len(matches)} errors={len(errors)} "
        f"read_any={read_any} send_rc={rc} msg_id={msg_id or '?'}")
    print(digest)
    print(f"\n[send rc={rc} msg_id={msg_id or '?'}]")
    if rc != 0:
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(amain())
