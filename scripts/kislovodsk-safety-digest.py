#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
kislovodsk-safety-digest.py — ежедневный TG-дайджест «уровень безопасности»
для поездки в Кисловодск (КМВ) и по ж/д-маршруту СПб → Кисловодск через
Ростовскую обл. Оценка рисков от ударов БПЛА по югу РФ для путешественника.

Источник: публичные TG-каналы (Telethon, userbot-сессия @AntonKamer).
Отправка: DM Антона через Bot API (фолбэк tg-send.sh).
Лог: ~/.claude/logs/kislovodsk-safety.log

Общая логика (словари, гео, отправка, session) — в kislovodsk_common.py. Здесь
только оркестрация: список каналов, classify_digest_message(), сборка дайджеста.

Эвристика по сводкам каналов за 24ч, НЕ гарантия. Деградирует при недоступности
источника (шлёт дайджест с пометкой «данные частичные»).
"""

import asyncio
import os
import sys
import re
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import kislovodsk_common as common
except ImportError:
    print("ERROR: kislovodsk_common.py not importable (нужен рядом)", file=sys.stderr)
    sys.exit(1)
from kislovodsk_common import (  # noqa: E402  (re-export для тестов/удобства)
    TOKENS_JSON, MAIN_SESSION, MSK, ANTON_CHAT, BOT_PREF,
    has, near, is_allclear, tg_link, normalize_snippet,
    DRONE, AIRRAID, PRIMARY, IMPACT, KMV_CITY, KMV_LOC, ROUTE_LOC,
    TRANSPORT, DISRUPT, COORDS, PLACE_KEYS, detect_places, collect_points,
)

if common.TelegramClient is None:
    print("ERROR: pip install telethon", file=sys.stderr)
    sys.exit(1)

# ── Пути / параметры ────────────────────────────────────────────────────────
SESSION_BASE = os.path.join(common.STATE_DIR, 'telethon_kislovodsk')  # без .session
SESSION_FILE = SESSION_BASE + '.session'
LOG = os.path.expanduser('~/.claude/logs/kislovodsk-safety.log')
TG_SEND = os.path.expanduser('~/.claude/scripts/tg-send.sh')
HOURS = 24
CHANNEL_TIMEOUT = 25   # сек на get_entity/get_messages одного канала

# ── Каналы (zone: kmv | route | both). both = нац. БПЛА-мониторинг ───────────
CHANNELS = [
    {"u": "VVV5807",        "zone": "kmv",  "name": "Губернатор Ставрополья Владимиров (офиц.)"},
    {"u": "moy_kislovodsk", "zone": "kmv",  "name": "Мой Кисловодск"},
    {"u": "Kislovodsx7",    "zone": "kmv",  "name": "Кисловодск Live"},
    {"u": "MinVody_Life_1", "zone": "kmv",  "name": "МинВоды LIFE"},
    {"u": "MinvodyOnline",  "zone": "kmv",  "name": "Минводы Онлайн"},
    {"u": "mvairport",      "zone": "kmv",  "name": "Аэропорт Минводы"},
    {"u": "stav_kray",      "zone": "kmv",  "name": "Ставрополье сейчас"},
    {"u": "minvody26",      "zone": "kmv",  "name": "Минводские круги"},
    {"u": "radarrussiia",   "zone": "both", "name": "Радар по РФ | БПЛА (быстрый)"},
    {"u": "astrapress",     "zone": "both", "name": "ASTRA"},
    {"u": "exilenova_plus", "zone": "both", "name": "Exilenova+"},
    {"u": "SHOT_SHOT",      "zone": "both", "name": "SHOT"},
    {"u": "bazabazon",      "zone": "both", "name": "Baza"},
    {"u": "rybar",          "zone": "both", "name": "Рыбарь"},
    {"u": "kavkaz_leakbez", "zone": "both", "name": "Кавказ"},
]

# слова закрытия/ограничения аэропорта Минвод
AIRPORT_DISRUPT = ["закрыт", "ограничен", "не приним", "план ковёр", "план ковер",
                   "задерж", "отмен"]

RED_NEAR_WINDOW = 80   # bug #8: триггер должен быть в N симв. от KMV-города


def log(line):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(f"{datetime.now(MSK).strftime('%Y-%m-%d %H:%M:%S')} | {line}\n")


def ensure_session():
    return common.ensure_session_copy(SESSION_FILE)


# ── Классификация одного сообщения дайджеста (чистая, тестируемая) ───────────
def classify_digest_message(channel_zone, text):
    """Вернуть (zone_hits:set, level:str|None, airport:bool).
    Пустой zone_hits → сообщение не релевантно. level: 'red'/'yellow'.
    bug #3: «отбой» отсекается. bug #4: аэропорт → зона kmv. bug #8: 🔴 требует
    БПЛА/тревога-триггер РЯДОМ с городом-курортом (не просто город-назначение)."""
    if is_allclear(text):                       # bug #3: отбой — не показывать
        return set(), None, False
    t = text.lower()
    threat_hit = has(t, DRONE) or has(t, AIRRAID)
    airport_hit = ("аэропорт" in t and has(t, KMV_LOC) and has(t, AIRPORT_DISRUPT))

    zone_hits = set()
    # КМВ-зона: для kmv-каналов достаточно угрозы; для both — нужна KMV-локация
    if threat_hit:
        if channel_zone == "kmv":
            zone_hits.add("kmv")
        elif channel_zone == "both" and has(t, KMV_LOC):
            zone_hits.add("kmv")
    # Маршрут-зона: локация маршрута + (угроза ИЛИ транспорт+сбой)
    if has(t, ROUTE_LOC) and (threat_hit or (has(t, TRANSPORT) and has(t, DISRUPT))):
        zone_hits.add("route")
    # bug #4: аэропорт Минвод — событие КМВ (иначе пустая зона → пин уходил в route)
    if airport_hit:
        zone_hits.add("kmv")

    if not zone_hits:
        return set(), None, False

    # bug #8: 🔴 только если БПЛА/тревога-триггер РЯДОМ с городом-курортом КМВ
    # (не «поезд до Кисловодска задержан из-за БПЛА в другом регионе»).
    red = (threat_hit and has(t, KMV_CITY)
           and near(t, KMV_CITY, PRIMARY, RED_NEAR_WINDOW))
    level = "red" if red else "yellow"
    return zone_hits, level, airport_hit


async def collect():
    """Вернуть (matches, errors, read_any). matches — список dict с разбором."""
    matches = []   # {zone:set, level, ch, name, time, snippet, airport, mid}
    errors = []
    read_any = False
    now_utc = datetime.now(timezone.utc)        # bug #7: окно считаем ВНУТРИ collect
    since = now_utc - timedelta(hours=HOURS)

    api_id, api_hash = common.telethon_creds()
    if not api_id or not api_hash:
        errors.append("Нет api_id/api_hash в tokens.json")
        return matches, errors, read_any

    client = await common.authorized_client(
        SESSION_BASE, api_id, api_hash, errors, SESSION_FILE)
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
                    zone_hits, level, airport_hit = classify_digest_message(
                        ch["zone"], m.text)
                    if not zone_hits:
                        continue
                    matches.append({
                        "zone": zone_hits, "level": level, "ch": ch["u"],
                        "name": ch["name"],
                        "time": m.date.astimezone(MSK).strftime('%d.%m %H:%M'),
                        "snippet": normalize_snippet(m.text, 140),
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
    out = []
    for m in items:
        line = f"• [{m['name']} {m['time']}] {m['snippet']}"
        if m.get("ch") and m.get("mid"):
            line += f" → {tg_link(m['ch'], m['mid'])}"
        out.append(line)
    return out


def build_digest(matches, errors, read_any):
    nowmsk = datetime.now(MSK).strftime('%d.%m %H:%M')
    partial = (not read_any) or bool(errors)

    kmv_lvl, kmv_txt, kmv_ev = zone_summary(matches, "kmv")
    rt_lvl, rt_txt, rt_ev = zone_summary(matches, "route")

    air = [m for m in matches if m["airport"]]
    if air:
        air_line = "⚠️ есть сообщения об ограничениях/задержках: " + air[0]["snippet"][:90]
    else:
        air_line = "штатно (за 24ч сообщений об ограничениях нет)"

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


def send_tg(text):
    return common.send_tg(text, tg_send_fallback=TG_SEND)


def dispatch_digest(text, matches):
    """Дайджест: карта-картинка (если есть точки) + текст; иначе текст. (rc, raw)."""
    return common.dispatch_with_map(
        text, matches, short_caption="🗺 Карта обстановки КМВ/маршрут (дайджест ниже)",
        log_fn=log, tg_send_fallback=TG_SEND, map_prefix="kmv-digest-map-")


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
