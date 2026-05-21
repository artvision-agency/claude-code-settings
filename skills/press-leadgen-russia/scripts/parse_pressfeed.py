#!/usr/bin/env python3
"""
parse_pressfeed.py — парсер журналистских запросов Pressfeed через TG-preview
================================================================================

Pressfeed зеркалит все опубликованные запросы в TG-канал @Pressfeed_queries.
Public preview (t.me/s/Pressfeed_queries) отдаёт HTML без авторизации.

Формат сообщений:
    <Outlet>: <Заголовок-запроса>
    https://pressfeed.ru/query/<ID>?utm_source=telegram_queries...
    <Полное тело запроса>
    Дедлайн: <DD.MM.YYYY HH:MM>

Output: JSON-array с полями:
    source, id, url, title, outlet, deadline, topic_tags, body, fetched_at, hash

Idempotency: hash-set в ~/.claude/state/press-leadgen-seen.json
Повторный запуск не выдаёт дубликаты (но всё равно сохраняет в файл — для аудита).

Usage:
    python3 parse_pressfeed.py --since 24h -o /tmp/press-queries-pressfeed.json
    python3 parse_pressfeed.py --since 7d --include-seen
    python3 parse_pressfeed.py --debug

Зависимости: только stdlib + requests (no Playwright нужен — TG preview = static HTML).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

# --------------------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------------------

TG_CHANNEL_URL = "https://t.me/s/Pressfeed_queries"
STATE_DIR = Path.home() / ".claude" / "state"
STATE_FILE = STATE_DIR / "press-leadgen-seen.json"
LOG_FILE = Path.home() / ".claude" / "logs" / "press-leadgen.log"

DEFAULT_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

# --------------------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------------------

LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [pressfeed] %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stderr),
    ],
)
log = logging.getLogger("pressfeed")

# --------------------------------------------------------------------------------------
# State management (idempotency)
# --------------------------------------------------------------------------------------


def load_seen() -> set[str]:
    if not STATE_FILE.exists():
        return set()
    try:
        with open(STATE_FILE) as f:
            data = json.load(f)
        return set(data.get("pressfeed", []))
    except (json.JSONDecodeError, OSError) as e:
        log.warning(f"State file corrupt: {e}, treating as empty")
        return set()


def save_seen(seen: set[str]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    all_data: dict[str, Any] = {}
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE) as f:
                all_data = json.load(f)
        except json.JSONDecodeError:
            pass
    all_data["pressfeed"] = sorted(seen)
    with open(STATE_FILE, "w") as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)


# --------------------------------------------------------------------------------------
# Time helpers
# --------------------------------------------------------------------------------------


def parse_since(since: str) -> timedelta:
    """Parse '24h', '7d', '30m' → timedelta."""
    m = re.match(r"^(\d+)([hdm])$", since.strip().lower())
    if not m:
        raise ValueError(f"--since должен быть формата '24h', '7d', '30m', получено: {since}")
    n, unit = int(m.group(1)), m.group(2)
    return {"h": timedelta(hours=n), "d": timedelta(days=n), "m": timedelta(minutes=n)}[unit]


def parse_tg_datetime(s: str) -> datetime | None:
    """TG datetime tag: <time datetime="2026-05-20T18:00:00+00:00">.
    Также пробуем русские форматы 'Дедлайн: 23.05.2026 18:00'.
    """
    if not s:
        return None
    s = s.strip()
    # ISO format
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        pass
    # Russian format dd.mm.yyyy hh:mm
    m = re.match(r"(\d{1,2})\.(\d{1,2})\.(\d{4})(?:\s+(\d{1,2}):(\d{2}))?", s)
    if m:
        day, mon, yr = int(m.group(1)), int(m.group(2)), int(m.group(3))
        hr = int(m.group(4)) if m.group(4) else 23
        mn = int(m.group(5)) if m.group(5) else 59
        try:
            return datetime(yr, mon, day, hr, mn, tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


# --------------------------------------------------------------------------------------
# HTTP fetch
# --------------------------------------------------------------------------------------


def fetch_tg_channel(before: str | None = None, timeout: int = 30) -> str:
    """Fetch TG channel preview HTML. `before` = message_id для пагинации (?before=N)."""
    url = TG_CHANNEL_URL
    if before:
        url += f"?before={before}"
    log.debug(f"Fetching {url}")
    req = Request(url, headers={"User-Agent": DEFAULT_UA, "Accept-Language": "ru,en;q=0.9"})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


# --------------------------------------------------------------------------------------
# HTML parsing (regex-based — без lxml, чтобы не плодить зависимости)
# --------------------------------------------------------------------------------------

# TG preview wraps each message in <div class="tgme_widget_message_wrap"> ... </div>
# We anchor on data-post="<channel>/<id>" and slice each block manually.
MSG_ID_RE = re.compile(r'data-post="[^/]+/(\d+)"')
MSG_TEXT_RE = re.compile(
    r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>\s*(?:<div class="tgme_widget_message_(?:footer|info|user|reply))',
    re.DOTALL,
)
# Fallback: до закрытия любого div (менее точно, но не теряет)
MSG_TEXT_FALLBACK_RE = re.compile(
    r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>',
    re.DOTALL,
)
MSG_DATETIME_RE = re.compile(r'<time[^>]*datetime="([^"]+)"')
PRESSFEED_QUERY_LINK_RE = re.compile(r"https?://pressfeed\.ru/query/(\d+)", re.IGNORECASE)
ANCHOR_RE = re.compile(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")
BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)


def strip_html(html: str) -> str:
    """Преобразовать HTML в plaintext, сохранив переносы строк от <br>."""
    text = BR_RE.sub("\n", html)
    text = TAG_RE.sub("", text)
    # Unescape common entities
    text = (
        text.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&laquo;", "«")
        .replace("&raquo;", "»")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
        .replace("&ndash;", "–")
        .replace("&mdash;", "—")
        .replace("&hellip;", "…")
    )
    # Collapse whitespace but keep paragraph breaks
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_query_id(text: str, html: str) -> str | None:
    """Сначала пробуем достать pressfeed.ru/query/<ID> из ссылок, затем из текста."""
    for source in (html, text):
        m = PRESSFEED_QUERY_LINK_RE.search(source)
        if m:
            return m.group(1)
    return None


def split_outlet_title(first_line: str) -> tuple[str, str]:
    """Первая строка обычно вида '<Outlet>: <Title>'. Возвращает (outlet, title)."""
    parts = first_line.split(":", 1)
    if len(parts) == 2 and len(parts[0]) < 80:
        return parts[0].strip(), parts[1].strip()
    return "Pressfeed", first_line.strip()


def extract_deadline(text: str) -> str | None:
    """Поиск 'Дедлайн: dd.mm.yyyy [hh:mm]' или 'до dd.mm.yyyy' в теле."""
    for pattern in (
        r"[Дд]едлайн[^\d]*?(\d{1,2}\.\d{1,2}\.\d{4}(?:\s+\d{1,2}:\d{2})?)",
        r"\sдо\s+(\d{1,2}\.\d{1,2}\.\d{4}(?:\s+\d{1,2}:\d{2})?)",
        r"срок[^\d]*?(\d{1,2}\.\d{1,2}\.\d{4}(?:\s+\d{1,2}:\d{2})?)",
    ):
        m = re.search(pattern, text)
        if m:
            dt = parse_tg_datetime(m.group(1))
            if dt:
                return dt.isoformat()
    return None


def naive_topic_tags(text: str) -> list[str]:
    """Простая эвристика — keywords которые часто встречаются в названиях ниш.
    Не ML, но даёт сигнал для match_clients.py.
    """
    text_l = text.lower()
    catalogue = {
        "медицина": ["клиник", "врач", "стомат", "медицин", "имплант", "лечен", "паци", "здоров"],
        "seo": ["seo", "сео", "поисков", "продвижен", "ранжиров", "трафик", "семантик"],
        "маркетинг": ["маркетинг", "реклам", "контент", "smm", "ppc", "директ", "growth"],
        "недвижимость": ["недвижим", "новостройк", "ипотек", "жильё", "квартир", "застройщик"],
        "образование": ["обучен", "образован", "школа", "курс", "ученик", "студент", "школьник"],
        "финансы": ["банк", "вклад", "кредит", "инвестиц", "офз", "брокер", "налог"],
        "психология": ["психолог", "тревог", "стресс", "выгоран", "ментал"],
        "родители": ["родител", "ребён", "дет", "мам", "пап", "семья"],
        "b2b": ["b2b", "корпорат", "оптов", "тендер", "поставщик"],
        "it": ["программ", "разработк", "стартап", "айти", " it ", "tech"],
        "ритейл": ["ритейл", "магазин", "торговл", "ecom", "маркетплейс"],
        "hr": ["hr", "найм", "сотрудник", "вакансия", "рекрут"],
    }
    return [tag for tag, kws in catalogue.items() if any(kw in text_l for kw in kws)]


def make_hash(source: str, qid: str, title: str) -> str:
    h = hashlib.sha256(f"{source}|{qid}|{title}".encode()).hexdigest()
    return h[:16]


def split_message_blocks(html: str) -> list[tuple[str, str]]:
    """Делит HTML на блоки по data-post маркерам.
    Возвращает [(msg_id, block_html), ...].
    """
    # Найти позиции всех data-post маркеров
    positions: list[tuple[str, int]] = []
    for m in MSG_ID_RE.finditer(html):
        positions.append((m.group(1), m.start()))
    if not positions:
        return []

    blocks: list[tuple[str, str]] = []
    for i, (msg_id, start) in enumerate(positions):
        end = positions[i + 1][1] if i + 1 < len(positions) else len(html)
        blocks.append((msg_id, html[start:end]))
    return blocks


def parse_messages(html: str) -> list[dict[str, Any]]:
    """Извлечь все сообщения из preview HTML и собрать query-объекты."""
    queries: list[dict[str, Any]] = []
    blocks = split_message_blocks(html)
    log.debug(f"Found {len(blocks)} message blocks in HTML")

    for tg_msg_id, block_html in blocks:
        text_match = MSG_TEXT_RE.search(block_html) or MSG_TEXT_FALLBACK_RE.search(block_html)
        if not text_match:
            continue
        raw_html = text_match.group(1)
        text = strip_html(raw_html)
        if not text:
            continue

        dt_match = MSG_DATETIME_RE.search(block_html)
        posted_at = dt_match.group(1) if dt_match else None

        qid = extract_query_id(text, raw_html)
        if not qid:
            log.debug(f"Skip msg {tg_msg_id}: no pressfeed.ru/query/ link")
            continue

        # Title = first non-empty line; outlet = prefix before ':'
        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
        if not lines:
            continue
        outlet, title = split_outlet_title(lines[0])

        # Body = всё после первой строки и до первого URL pressfeed.ru
        body_parts = []
        for ln in lines[1:]:
            if "pressfeed.ru/query/" in ln:
                continue
            body_parts.append(ln)
        body = "\n".join(body_parts).strip()

        deadline = extract_deadline(body) or extract_deadline(text)
        topic_tags = naive_topic_tags(f"{title} {body}")
        url_clean = f"https://pressfeed.ru/query/{qid}"

        q: dict[str, Any] = {
            "source": "pressfeed",
            "id": qid,
            "url": url_clean,
            "title": title[:300],
            "outlet": outlet[:120],
            "deadline": deadline,
            "topic_tags": topic_tags,
            "body": body[:5000],
            "tg_message_id": tg_msg_id,
            "posted_at": posted_at,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "hash": make_hash("pressfeed", qid, title),
        }
        queries.append(q)

    return queries


# --------------------------------------------------------------------------------------
# Main loop
# --------------------------------------------------------------------------------------


def collect_queries(since: timedelta, max_pages: int = 5) -> list[dict[str, Any]]:
    """Соберём запросы за period, листая preview назад по `before=`."""
    cutoff = datetime.now(timezone.utc) - since
    log.info(f"Collecting queries since {cutoff.isoformat()} (max {max_pages} pages)")

    all_queries: list[dict[str, Any]] = []
    before: str | None = None
    seen_msg_ids: set[str] = set()

    for page in range(max_pages):
        try:
            html = fetch_tg_channel(before=before)
        except Exception as e:
            log.error(f"Fetch page {page + 1} failed: {e}")
            break

        queries = parse_messages(html)
        if not queries:
            log.info(f"Page {page + 1}: 0 messages → stop")
            break

        # Cutoff check: if все messages on page старше cutoff → stop
        in_range = []
        for q in queries:
            if q["tg_message_id"] in seen_msg_ids:
                continue
            seen_msg_ids.add(q["tg_message_id"])

            if q.get("posted_at"):
                try:
                    posted = datetime.fromisoformat(q["posted_at"].replace("Z", "+00:00"))
                    if posted < cutoff:
                        log.debug(f"Skip {q['id']}: posted {posted} < cutoff {cutoff}")
                        continue
                except ValueError:
                    pass  # keep query even if datetime broken
            in_range.append(q)

        log.info(f"Page {page + 1}: {len(queries)} parsed, {len(in_range)} in range")
        all_queries.extend(in_range)

        if len(in_range) < len(queries) / 2:
            # большинство на этой странице уже out of range → следующая будет ещё старее
            log.info("Most messages out of cutoff → stop pagination")
            break

        # Pagination: take smallest msg id from this page
        min_id = min((int(q["tg_message_id"]) for q in queries), default=None)
        if not min_id:
            break
        before = str(min_id)

    return all_queries


def main() -> int:
    ap = argparse.ArgumentParser(description="Parse Pressfeed queries via @Pressfeed_queries TG mirror")
    ap.add_argument("--since", default="24h", help="Time window (24h, 7d, 30m). Default: 24h")
    ap.add_argument("-o", "--output", default="/tmp/press-queries-pressfeed.json", help="Output JSON path")
    ap.add_argument("--max-pages", type=int, default=5, help="Max TG preview pages to fetch")
    ap.add_argument(
        "--include-seen",
        action="store_true",
        help="Include queries already in state (default: filter them out)",
    )
    ap.add_argument("--debug", action="store_true", help="Verbose logging")
    args = ap.parse_args()

    if args.debug:
        log.setLevel(logging.DEBUG)

    try:
        since_delta = parse_since(args.since)
    except ValueError as e:
        log.error(str(e))
        return 2

    queries = collect_queries(since=since_delta, max_pages=args.max_pages)
    log.info(f"Total collected (in window): {len(queries)}")

    seen = load_seen()
    new_queries = [q for q in queries if args.include_seen or q["hash"] not in seen]

    log.info(f"New (not in seen-set): {len(new_queries)} (seen total: {len(seen)})")

    # Persist hashes BEFORE writing output so concurrent runs don't dupe
    new_hashes = {q["hash"] for q in queries}
    seen.update(new_hashes)
    save_seen(seen)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(new_queries, f, ensure_ascii=False, indent=2)

    log.info(f"Wrote {len(new_queries)} queries → {out_path}")
    print(f"RESULT: {json.dumps({'source': 'pressfeed', 'count': len(new_queries), 'output': str(out_path), 'window': args.since}, ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
