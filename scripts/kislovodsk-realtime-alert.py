#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
kislovodsk-realtime-alert.py — БЫСТРЫЙ real-time алерт БПЛА/воздушной тревоги
по КМВ (Кисловодск/Минводы/Ставрополье).

Отличие от kislovodsk-safety-digest.py:
  • дайджест = раз в сутки, обзор за 24ч;
  • этот скрипт = каждые ~30 мин (StartInterval 1800), ловит НОВЫЕ (по watermark)
    сигналы из быстрых каналов и сразу шлёт пуш 🔴 при явном КМВ-городе + триггере.

НОВИЗНА определяется ТОЛЬКО по watermark (id > watermark), НЕ по возрасту (bug #1:
раньше жёсткое окно 10 мин при интервале 30 мин теряло сообщения 10-30-мин
давности + watermark перескакивал). Возраст — лишь soft-cap (не алертить совсем
древние на первом прогоне, MAX_AGE_HOURS, буфер ≥ StartInterval).

Дедуп ОБЯЗАТЕЛЕН (anti-spam): один инцидент = один пуш. State-файл хранит
high-water-mark message.id по каждому каналу + хеши уже отправленных инцидентов.
Доступ к state защищён fcntl-локом (overlap прогонов → дубли/потеря watermark).

Общая логика (словари, гео, отправка, session) — в kislovodsk_common.py. Здесь
только оркестрация: список каналов, classify_realtime(), сборка пуша, state.

Секреты НЕ в коде (self-corrections #31) — читаются из tokens.json в рантайме.
Лог: ~/.claude/logs/kislovodsk-alert.log
"""

import asyncio
import os
import sys
import json
import hashlib
import re
import fcntl
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import kislovodsk_common as common
except ImportError:
    print("ERROR: kislovodsk_common.py not importable (нужен рядом)", file=sys.stderr)
    sys.exit(1)
from kislovodsk_common import (  # noqa: E402  (re-export для тестов/удобства)
    TOKENS_JSON, MAIN_SESSION, MSK, ANTON_CHAT, BOT_PREF,
    has, is_allclear, tg_link, normalize_snippet,
    DRONE, AIRRAID, PRIMARY, IMPACT, KMV_CITY, KMV_LOC, ROUTE_LOC,
    COORDS, PLACE_KEYS, detect_places, collect_points,
)

if common.TelegramClient is None:
    print("ERROR: pip install telethon", file=sys.stderr)
    sys.exit(1)

# ── Пути / параметры ────────────────────────────────────────────────────────
# отдельная session-копия от дайджеста, чтобы два job'а не лочили один SQLite
SESSION_BASE = os.path.join(common.STATE_DIR, 'telethon_kislovodsk_rt')  # без .session
SESSION_FILE = SESSION_BASE + '.session'
DIGEST_SESSION = os.path.join(common.STATE_DIR, 'telethon_kislovodsk.session')

STATE_FILE = os.path.expanduser('~/.claude/state/kislovodsk-alert-seen.json')
LOCK_FILE = STATE_FILE + '.lock'
LOG = os.path.expanduser('~/.claude/logs/kislovodsk-alert.log')

MAX_AGE_HOURS = 6            # soft-cap: не алертить сообщения старше N ч (≥ StartInterval)
READ_LIMIT = 40             # сколько последних сообщений тянуть на канал
CHANNEL_TIMEOUT = 25
MAX_PER_ZONE = 6            # сколько инцидентов показать в одном пуше
INCIDENT_KEEP = 800         # сколько хешей инцидентов хранить в state

# ── БЫСТРЫЕ каналы (zone: kmv | both) ───────────────────────────────────────
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


def log(line):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(f"{datetime.now(MSK).strftime('%Y-%m-%d %H:%M:%S')} | {line}\n")


# ── Классификация real-time (🔴 ТОЛЬКО при явном КМВ-городе + триггер БПЛА) ──
def classify_realtime(text):
    """Вариант «б»: мгновенный пуш ТОЛЬКО при ЯВНОМ КМВ-ГОРОДЕ + триггере (🔴).
    Общекраевые объявления (без города) и маршрут НЕ пушатся мгновенно — они
    всплывут в дайджесте как 🟡. Вернуть (zone, level) или (None, None)."""
    if is_allclear(text):          # отбой — не алертить
        return None, None
    t = text.lower()
    if not has(t, PRIMARY):        # нет триггерного слова
        return None, None
    if has(t, KMV_CITY):           # явный город-курорт КМВ
        return "kmv", "red"
    return None, None              # краевое/маршрут → не мгновенно (в дайджест)


# ── State (дедуп) с fcntl-локом ─────────────────────────────────────────────
def acquire_lock():
    """Эксклюзивный неблокирующий лок на весь прогон (bug #5: overlap прогонов →
    дубли/потеря watermark). Возвращает file-объект или None (другой прогон)."""
    os.makedirs(os.path.dirname(LOCK_FILE), exist_ok=True)
    f = open(LOCK_FILE, 'w')
    try:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return f
    except OSError:
        f.close()
        return None


def release_lock(f):
    if not f:
        return
    try:
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except OSError:
        pass
    try:
        f.close()
    except OSError:
        pass


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
    if len(st["incidents"]) > INCIDENT_KEEP:
        st["incidents"] = st["incidents"][-INCIDENT_KEEP:]
    tmp = STATE_FILE + ".tmp"
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(st, f, ensure_ascii=False, indent=1)
    os.replace(tmp, STATE_FILE)


def incident_hash(ch_u, text):
    norm = re.sub(r'\s+', ' ', text).strip().lower()[:120]
    return hashlib.sha1((ch_u + "|" + norm).encode('utf-8')).hexdigest()[:16]


def ensure_session():
    return common.ensure_session_copy(SESSION_FILE, extra_src=DIGEST_SESSION)


async def collect(st):
    """Вернуть (incidents, errors, read_any, new_watermark).
    incidents — список новых (не отправленных ранее) сигналов."""
    incidents = []     # {zone, level, ch, name, src, time, snippet, hash, msg_id, impact}
    errors = []
    read_any = False
    new_wm = dict(st["watermark"])

    api_id, api_hash = common.telethon_creds()
    if not api_id or not api_hash:
        errors.append("Нет api_id/api_hash в tokens.json")
        return incidents, errors, read_any, new_wm

    client = await common.authorized_client(
        SESSION_BASE, api_id, api_hash, errors, SESSION_FILE, extra_src=DIGEST_SESSION)
    if client is None:
        return incidents, errors, read_any, new_wm

    now_utc = datetime.now(timezone.utc)
    soft_cap = now_utc - timedelta(hours=MAX_AGE_HOURS)
    seen_hashes = set(st["incidents"])

    try:
        for ch in FAST_CHANNELS:
            u = ch["u"]
            old_wm = st["watermark"].get(u, 0)
            chan_max_seen = old_wm
            matched_unsent_ids = []  # id матчей: watermark не перешагнёт их до отправки
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
                    # НОВОЕ = строго больше watermark (bug #1: возраст НЕ условие)
                    if m.id <= old_wm:
                        continue
                    if not m.text:
                        continue
                    # soft-cap: не алертить совсем древние (watermark всё равно
                    # подвинется за них как за «просмотренные»).
                    if m.date and m.date < soft_cap:
                        continue
                    zone, level = classify_realtime(m.text)
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
                        "time": m.date.astimezone(MSK).strftime('%d.%m %H:%M')
                                if m.date else "?",
                        "snippet": normalize_snippet(m.text, 150),
                        "hash": h, "msg_id": m.id,
                        "impact": has(t, IMPACT),
                    })
                    matched_unsent_ids.append(m.id)
                # watermark двигаем до максимума прочитанного, НО не дальше самого
                # старого неотправленного матча (добьём после успешной отправки).
                if matched_unsent_ids:
                    new_wm[u] = min(matched_unsent_ids) - 1
                else:
                    new_wm[u] = chan_max_seen
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


def _block(title, items):
    out = [title]
    for i in items[:MAX_PER_ZONE]:
        mark = "‼️" if i["impact"] else "•"
        tag = "офиц." if i["src"] == "official" else (
            "локальн." if i["src"] == "local" else "агрегатор")
        line = f"{mark} [{i['name']} · {tag} · {i['time']}] {i['snippet']}"
        if i.get("ch") and i.get("msg_id"):
            line += f" → {tg_link(i['ch'], i['msg_id'])}"
        out.append(line)
    extra = len(items) - MAX_PER_ZONE
    if extra > 0:
        out.append(f"   …и ещё {extra} сообщ.")
    return out


def build_push(incidents):
    """Сгруппировать новые инциденты в ОДИН пуш. classify_realtime отдаёт только
    зону 'kmv' → пуш всегда 🔴 по КМВ (маршрут/краевое сюда не попадают)."""
    kmv = [i for i in incidents if i["zone"] == "kmv"]
    nowmsk = datetime.now(MSK).strftime('%d.%m %H:%M')
    L = [f"🔴 БПЛА/ВОЗДУШНАЯ ОПАСНОСТЬ — КМВ/Ставрополье ({nowmsk} МСК)", ""]
    L += _block("🏔 КМВ (Кисловодск/Минводы/Ставрополье):", kmv)
    L.append("")
    L.append("⚠️ быстрый сигнал из TG-каналов, не гарантия — сверь с официальным "
             "(губернатор @VVV5807 / МЧС / SMS-оповещение).")
    return "🔴", '\n'.join(L)


def dispatch_alert(text, incidents):
    """Алерт: карта-картинка (если есть точки) + текст; иначе текст. (rc, raw)."""
    return common.dispatch_with_map(
        text, incidents, short_caption="🗺 Карта сигналов БПЛА (детали ниже)",
        log_fn=log, map_prefix="kmv-alert-map-")


def amain_sync():
    """Синхронная обёртка вокруг асинхронного сбора (проще для launchd)."""
    lock = acquire_lock()
    if lock is None:
        log("OVERLAP: другой прогон держит лок, выходим тихо")
        print("OVERLAP (другой прогон активен)")
        return 0
    try:
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
            # ничего нового — двигаем watermark и выходим тихо
            for ch in FAST_CHANNELS:
                cm = ch.get("_chan_max")
                if cm is not None:
                    new_wm[ch["u"]] = max(new_wm.get(ch["u"], 0), cm)
            print("ТИХО: новых сигналов БПЛА/тревоги за окно нет")

        st["watermark"] = {k: v for k, v in new_wm.items() if isinstance(v, int)}
        save_state(st)

        log(f"incidents={len(incidents)} sent_rc={sent_rc} read_any={read_any} "
            f"errors={len(errors)}" + (f" :: {'; '.join(errors[:4])}" if errors else ""))
        return 0
    finally:
        release_lock(lock)


if __name__ == '__main__':
    sys.exit(amain_sync())
