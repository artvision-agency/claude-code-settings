#!/usr/bin/env python3
"""
Text Factors Audit — MVP

Аудит текстовых SEO-факторов Яндекса: уникальность, тошнота, водность, LSI,
структура, мета-теги, читаемость, антиспам, картинки, ссылки, свежесть.

CLI:
    python3 audit.py https://example.com --output=audit.json
    python3 audit.py https://example.com --output=audit.json --keyword="купить пластиковые окна" --lsi-words="профиль,стеклопакет,монтаж"
    python3 audit.py https://example.com --sitemap --output=audit.json

Exit codes:
    0 — успех
    1 — невалидный URL / сайт недоступен
    2 — ошибка чтения factors.yaml
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
import yaml
from bs4 import BeautifulSoup

# =============================================================
# Константы
# =============================================================
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
FACTORS_YAML = SKILL_ROOT / "data" / "factors.yaml"
TOKENS_PATH = Path("/Users/antonk/artvision-data/tokens.json")

USER_AGENT = (
    "ArtvisionTextAudit/0.1 (text factors audit; +https://artvision.pro)"
)
DEFAULT_TIMEOUT = 15
RETRY_COUNT = 2

STATUS_PASS = "pass"
STATUS_WARN = "warn"
STATUS_FAIL = "fail"
STATUS_MANUAL = "manual"
STATUS_NA = "na"

# Русские стоп-слова (базовый набор; можно расширить через NLTK, но избегаем
# тяжёлой зависимости на старте)
RU_STOPWORDS = {
    "а", "без", "более", "больше", "будет", "будто", "бы", "был", "была",
    "были", "было", "быть", "в", "вам", "вас", "вдруг", "ведь", "во", "вот",
    "впрочем", "все", "всегда", "всего", "всех", "всю", "вы", "где", "да",
    "даже", "два", "для", "до", "другой", "его", "ее", "ей", "ему", "если",
    "есть", "еще", "ещё", "же", "за", "здесь", "и", "из", "или", "им", "их",
    "к", "кажется", "как", "какая", "какой", "когда", "конечно", "которого",
    "которые", "кто", "куда", "ли", "лучше", "между", "меня", "мне", "много",
    "может", "можно", "мой", "моя", "мы", "на", "над", "надо", "наконец",
    "нас", "не", "него", "нее", "ей", "ней", "нельзя", "нет", "ни",
    "нибудь", "никогда", "ним", "них", "ничего", "но", "ну", "о", "об",
    "однако", "он", "она", "они", "опять", "от", "перед", "по", "под",
    "после", "потом", "потому", "почти", "при", "про", "раз", "разве", "с",
    "сам", "свою", "себе", "себя", "сегодня", "сейчас", "со", "совсем",
    "так", "такой", "там", "тебя", "тем", "теперь", "то", "тогда", "того",
    "тоже", "только", "том", "тот", "три", "тут", "ты", "у", "уж", "уже",
    "хоть", "хотя", "чего", "чей", "чем", "через", "что", "чтоб", "чтобы",
    "чуть", "эта", "эти", "это", "этой", "этом", "этот", "эту", "я",
}

# Для подсчёта предложений
SENT_END = re.compile(r"[.!?…]+\s+")
WORD_PATTERN = re.compile(r"[а-яёa-z0-9]+", re.IGNORECASE)
SYLLABLE_VOWELS = set("аеёиоуыэюяaeiouy")

PAGE_TYPES_ALL = ["home", "blog", "product", "catalog"]


# =============================================================
# Token auto-discovery
# =============================================================
def load_tokens() -> dict[str, Any]:
    """Load tokens.json, return dict. Empty dict if file missing or broken."""
    if not TOKENS_PATH.exists():
        return {}
    try:
        with open(TOKENS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"[WARN] Failed to read tokens.json: {exc}", file=sys.stderr)
        return {}


def auto_detect_counter_id(tokens: dict[str, Any], domain: str) -> str | None:
    """Auto-detect Yandex.Metrika counter_id from tokens.json by domain slug."""
    metrika = tokens.get("yandex", {}).get("metrika", {})
    domain_clean = (
        domain.replace("https://", "")
        .replace("http://", "")
        .rstrip("/")
        .lower()
    )
    slug = domain_clean.replace(".", "").replace("-", "")
    for key, val in metrika.items():
        if key.startswith("_") or key in (
            "token", "client_id", "client_secret", "account",
        ):
            continue
        if not isinstance(val, (str, int)):
            continue
        key_clean = key.lower().replace("_counter", "").replace("_", "")
        if key_clean in slug or slug in key_clean:
            return str(val)
    return None


def get_metrika_token(tokens: dict[str, Any]) -> str | None:
    """Extract Yandex.Metrika OAuth token."""
    return tokens.get("yandex", {}).get("metrika", {}).get("token")


def get_webmaster_token(tokens: dict[str, Any]) -> str | None:
    """Extract Yandex.Webmaster OAuth token."""
    return tokens.get("yandex", {}).get("webmaster", {}).get("token")


def get_webmaster_user_id(tokens: dict[str, Any]) -> str | None:
    """Extract Yandex.Webmaster user_id."""
    uid = tokens.get("yandex", {}).get("webmaster", {}).get("user_id")
    return str(uid) if uid is not None else None


def get_topvisor_key(tokens: dict[str, Any]) -> str | None:
    """Extract Topvisor API key."""
    tv = tokens.get("topvisor", {})
    if isinstance(tv, dict):
        return tv.get("api_key")
    return None


def get_topvisor_user_id(tokens: dict[str, Any]) -> str | None:
    """Extract Topvisor user_id."""
    tv = tokens.get("topvisor", {})
    if isinstance(tv, dict):
        uid = tv.get("user_id")
        return str(uid) if uid is not None else None
    return None


def get_text_ru_key(tokens: dict[str, Any]) -> str | None:
    """Extract text.ru API key (supports nested and flat layouts)."""
    text_ru = tokens.get("text_ru")
    if isinstance(text_ru, dict):
        return text_ru.get("api_key")
    return tokens.get("text_ru_api_key")


def get_content_watch_key(tokens: dict[str, Any]) -> str | None:
    """Extract content-watch.ru API key (supports nested and flat layouts)."""
    cw = tokens.get("content_watch")
    if isinstance(cw, dict):
        return cw.get("api_key")
    return tokens.get("content_watch_api_key")


# =============================================================
# Yandex.Webmaster API helpers (search queries)
# =============================================================
def webmaster_host_id(
    session: requests.Session,
    wm_token: str,
    user_id: str,
    domain: str,
) -> str | None:
    """Find host_id for *domain* in Webmaster via API."""
    url = f"https://api.webmaster.yandex.net/v4/user/{user_id}/hosts"
    try:
        resp = session.get(
            url,
            headers={"Authorization": f"OAuth {wm_token}"},
            timeout=DEFAULT_TIMEOUT,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        domain_clean = (
            domain.replace("https://", "")
            .replace("http://", "")
            .rstrip("/")
            .lower()
        )
        for host in data.get("hosts", []):
            hid = host.get("host_id", "")
            # host_id looks like "https:example.com:443"
            host_domain = (
                hid.replace("https:", "")
                .replace("http:", "")
                .replace(":443", "")
                .replace(":80", "")
                .strip("/")
                .lower()
            )
            if host_domain == domain_clean or domain_clean in host_domain:
                return hid
    except Exception:
        pass
    return None


def webmaster_top_queries(
    session: requests.Session,
    wm_token: str,
    user_id: str,
    host_id: str,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Fetch top search queries from Webmaster for keyword suggestions.

    Returns list of {query, clicks, impressions, position}.
    """
    url = (
        f"https://api.webmaster.yandex.net/v4/user/{user_id}"
        f"/hosts/{host_id}/search-queries/popular"
    )
    try:
        resp = session.get(
            url,
            headers={"Authorization": f"OAuth {wm_token}"},
            params={"order_by": "TOTAL_CLICKS", "limit": limit},
            timeout=DEFAULT_TIMEOUT,
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
        queries = []
        for q in data.get("queries", []):
            queries.append({
                "query": q.get("query_text", {}).get("text_indicator", {}).get("value", ""),
                "clicks": q.get("clicks", 0),
                "impressions": q.get("impressions", 0),
                "position": q.get("position", 0),
            })
        return queries
    except Exception:
        return []


# =============================================================
# Topvisor API helpers (keyword positions)
# =============================================================
def topvisor_find_project(
    session: requests.Session,
    api_key: str,
    user_id: str,
    domain: str,
) -> int | None:
    """Find Topvisor project_id by domain."""
    url = "https://api.topvisor.com/v2/json/get/projects_2/projects"
    try:
        resp = session.post(
            url,
            headers={
                "Authorization": f"bearer {api_key}",
                "User-Id": user_id,
                "Content-Type": "application/json",
            },
            json={"show_site_stat": False},
            timeout=DEFAULT_TIMEOUT,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        domain_clean = (
            domain.replace("https://", "")
            .replace("http://", "")
            .rstrip("/")
            .lower()
        )
        for proj in data.get("result", []):
            site = (proj.get("site", "") or "").lower().rstrip("/")
            if domain_clean in site or site in domain_clean:
                return proj.get("id")
    except Exception:
        pass
    return None


def topvisor_get_positions(
    session: requests.Session,
    api_key: str,
    user_id: str,
    project_id: int,
    limit: int = 30,
) -> list[dict[str, Any]]:
    """Fetch recent keyword positions from Topvisor.

    Returns list of {keyword, position, url}.
    """
    url = "https://api.topvisor.com/v2/json/get/positions_2/history"
    try:
        resp = session.post(
            url,
            headers={
                "Authorization": f"bearer {api_key}",
                "User-Id": user_id,
                "Content-Type": "application/json",
            },
            json={
                "project_id": project_id,
                "regions_indexes": [0],
                "limit": limit,
                "dates": [1],
                "show_headers": True,
            },
            timeout=DEFAULT_TIMEOUT,
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
        result_data = data.get("result", {})
        keywords_list = result_data.get("keywords", [])
        positions = []
        for kw in keywords_list:
            name = kw.get("name", "")
            posits = kw.get("positionsData", {})
            # Get latest position from the first date entry
            pos_value = None
            for _region, dates_data in posits.items():
                if isinstance(dates_data, dict):
                    for _date, pdata in dates_data.items():
                        if isinstance(pdata, dict):
                            pos_value = pdata.get("position")
                            break
                break
            positions.append({
                "keyword": name,
                "position": pos_value,
            })
        return positions
    except Exception:
        return []


# =============================================================
# Модели
# =============================================================
@dataclass
class PageData:
    url: str
    status_code: int | None = None
    html: str = ""
    text: str = ""
    soup: Any = None
    title: str = ""
    description: str = ""
    h1_list: list[str] = field(default_factory=list)
    h2_list: list[str] = field(default_factory=list)
    h3_list: list[str] = field(default_factory=list)
    paragraphs: list[str] = field(default_factory=list)
    list_count: int = 0
    table_count: int = 0
    alt_coverage: float = 0.0
    alt_with_keyword_count: int = 0
    img_count: int = 0
    internal_links: int = 0
    external_links: int = 0
    anchors: list[str] = field(default_factory=list)
    og_tags: dict[str, str] = field(default_factory=dict)
    lastmod: str | None = None
    page_type: str = "home"
    error: str | None = None

    @property
    def ok(self) -> bool:
        return (
            self.status_code is not None
            and 200 <= self.status_code < 400
            and self.html != ""
        )


@dataclass
class FactorResult:
    id: int
    category: str
    name: str
    status: str
    severity: str
    weight: int
    evidence: str
    url_checked: str | None = None
    description: str = ""


@dataclass
class AuditResult:
    target_url: str
    audited_at: str
    keyword: str | None = None
    lsi_words: list[str] = field(default_factory=list)
    pages_crawled: dict[str, str] = field(default_factory=dict)
    factors: list[FactorResult] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_url": self.target_url,
            "audited_at": self.audited_at,
            "keyword": self.keyword,
            "lsi_words": self.lsi_words,
            "pages_crawled": self.pages_crawled,
            "factors": [asdict(f) for f in self.factors],
            "meta": self.meta,
        }


# =============================================================
# HTTP и загрузка страниц
# =============================================================
def make_session(verify_ssl: bool = True) -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    session.verify = verify_ssl
    return session


def fetch(session: requests.Session, url: str, timeout: int) -> PageData:
    last_error: str | None = None
    for attempt in range(RETRY_COUNT + 1):
        try:
            resp = session.get(url, timeout=timeout, allow_redirects=True)
            html = resp.text or ""
            return _parse_page(resp.url, resp.status_code, html)
        except requests.RequestException as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt < RETRY_COUNT:
                time.sleep(1)
    return PageData(url=url, status_code=None, html="", text="", error=last_error)


def _parse_page(url: str, status_code: int, html: str) -> PageData:
    page = PageData(url=url, status_code=status_code, html=html)
    if not html:
        return page
    soup = BeautifulSoup(html, "html.parser")
    page.soup = soup

    # Title
    if soup.title and soup.title.string:
        page.title = soup.title.string.strip()

    # Description
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc and meta_desc.get("content"):
        page.description = meta_desc["content"].strip()

    # OG tags
    for og in soup.find_all("meta", attrs={"property": True}):
        prop = og.get("property", "")
        if prop.startswith("og:"):
            page.og_tags[prop] = og.get("content", "")

    # Headings
    page.h1_list = [h.get_text(" ", strip=True) for h in soup.find_all("h1")]
    page.h2_list = [h.get_text(" ", strip=True) for h in soup.find_all("h2")]
    page.h3_list = [h.get_text(" ", strip=True) for h in soup.find_all("h3")]

    # Убираем script / style перед извлечением body text
    body_soup = BeautifulSoup(html, "html.parser")
    for tag in body_soup(["script", "style", "noscript", "nav", "footer", "header"]):
        tag.decompose()

    page.paragraphs = [
        p.get_text(" ", strip=True)
        for p in body_soup.find_all("p")
        if p.get_text(strip=True)
    ]
    page.text = re.sub(
        r"\s+", " ", body_soup.get_text(" ")
    ).strip()

    # Lists / tables
    page.list_count = len(soup.find_all(["ul", "ol"]))
    page.table_count = len(soup.find_all("table"))

    # Images
    imgs = soup.find_all("img")
    page.img_count = len(imgs)
    if imgs:
        with_alt = sum(1 for img in imgs if (img.get("alt") or "").strip())
        page.alt_coverage = with_alt / len(imgs)

    # Links
    parsed_base = urlparse(url)
    base_host = parsed_base.netloc
    for a in soup.find_all("a", href=True):
        href = a["href"]
        anchor_text = a.get_text(" ", strip=True)
        if anchor_text:
            page.anchors.append(anchor_text.lower())
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        link_parsed = urlparse(urljoin(url, href))
        if link_parsed.netloc == base_host or not link_parsed.netloc:
            page.internal_links += 1
        else:
            page.external_links += 1

    # Lastmod
    mod = soup.find("meta", attrs={"property": "article:modified_time"})
    if mod and mod.get("content"):
        page.lastmod = mod["content"]

    return page


# =============================================================
# Текстовая аналитика
# =============================================================
def tokenize_words(text: str) -> list[str]:
    return [w.lower() for w in WORD_PATTERN.findall(text)]


def count_sentences(text: str) -> int:
    if not text.strip():
        return 0
    parts = SENT_END.split(text)
    return max(1, len([p for p in parts if p.strip()]))


def count_syllables_ru(word: str) -> int:
    return max(1, sum(1 for c in word.lower() if c in SYLLABLE_VOWELS))


def flesch_kincaid_ru(text: str) -> float:
    """
    Русская адаптация индекса Флеша (Оборнева, 2006):
        FRE_ru = 206.836 - (60.1 * ASL) - (1.3 * ASW)
    где ASL = средняя длина предложения (слов), ASW = средняя длина слова (слогов).
    """
    words = tokenize_words(text)
    sentences = count_sentences(text)
    if not words or not sentences:
        return 0.0
    asl = len(words) / sentences
    asw = sum(count_syllables_ru(w) for w in words) / len(words)
    return round(206.836 - (60.1 * asw) - (1.3 * asl), 1)


def stopwords_ratio(words: list[str]) -> float:
    if not words:
        return 0.0
    stop = sum(1 for w in words if w in RU_STOPWORDS)
    return round(stop / len(words) * 100, 2)


def classic_nausea(words: list[str]) -> tuple[float, str]:
    if not words:
        return 0.0, ""
    freq: dict[str, int] = {}
    for w in words:
        if w in RU_STOPWORDS or len(w) < 3:
            continue
        freq[w] = freq.get(w, 0) + 1
    if not freq:
        return 0.0, ""
    top = max(freq.items(), key=lambda kv: kv[1])
    return round(math.sqrt(top[1]), 2), top[0]


def academic_nausea(words: list[str]) -> float:
    """Академическая тошнота = доля повторов самых частых знач. слов, %."""
    total = len(words)
    if total == 0:
        return 0.0
    freq: dict[str, int] = {}
    for w in words:
        if w in RU_STOPWORDS or len(w) < 3:
            continue
        freq[w] = freq.get(w, 0) + 1
    if not freq:
        return 0.0
    top10 = sorted(freq.values(), reverse=True)[:10]
    repeats_sum = sum(c for c in top10 if c >= 2)
    return round(repeats_sum / total * 100, 2)


def tf_density(words: list[str], keyword: str) -> float:
    if not words or not keyword:
        return 0.0
    key_tokens = tokenize_words(keyword)
    if not key_tokens:
        return 0.0
    # Для многословного ключа считаем количество вхождений биграмм/триграмм
    n = len(key_tokens)
    hits = 0
    for i in range(len(words) - n + 1):
        if words[i : i + n] == key_tokens:
            hits += 1
    return round(hits * n / len(words) * 100, 2)


def lsi_coverage(text: str, lsi_words: list[str]) -> tuple[float, list[str]]:
    if not lsi_words:
        return 0.0, []
    text_lower = text.lower()
    found = [w for w in lsi_words if w.lower() in text_lower]
    pct = round(len(found) / len(lsi_words) * 100, 1)
    return pct, found


def caps_words_count(text: str) -> list[str]:
    tokens = re.findall(r"[А-ЯA-Z]{4,}", text)
    # Исключаем аббревиатуры в словаре (ООО, ИП и т.п.) — ограничение: оставляем
    # только слова длиннее 4 символов, т.к. аббревиатуры типа ООО=3 отсеиваются.
    return tokens


def exclamation_spam_count(text: str) -> int:
    return len(re.findall(r"!{2,}", text))


def word_key_exact_or_morph(text: str, keyword: str, morph: Any | None) -> bool:
    """Проверяет вхождение ключа в текст: точное или морфологическое."""
    if not keyword:
        return False
    text_lower = text.lower()
    if keyword.lower() in text_lower:
        return True
    if morph is None:
        return False
    key_lemmas = [morph.parse(k)[0].normal_form for k in tokenize_words(keyword)]
    text_lemmas = [morph.parse(w)[0].normal_form for w in tokenize_words(text_lower)[:500]]
    # Проверяем подпоследовательность
    for i in range(len(text_lemmas) - len(key_lemmas) + 1):
        if text_lemmas[i : i + len(key_lemmas)] == key_lemmas:
            return True
    return False


def load_morph() -> Any | None:
    try:
        import pymorphy3  # type: ignore[import-untyped]

        return pymorphy3.MorphAnalyzer()
    except Exception:
        return None


# =============================================================
# text.ru / content-watch API
# =============================================================
def check_uniqueness_api(
    text: str, session: requests.Session, tokens: dict[str, Any] | None = None,
) -> tuple[float | None, str]:
    """
    Пытается проверить уникальность через text.ru API, если ключ есть в
    tokens.json. Возвращает (percent, evidence). Если ключа нет — (None, note).
    """
    if tokens is None:
        tokens = load_tokens()
    if not tokens:
        return None, "tokens.json не найден или пуст"

    text_ru_key = get_text_ru_key(tokens)
    content_watch_key = get_content_watch_key(tokens)

    if text_ru_key:
        try:
            post = session.post(
                "https://api.text.ru/post",
                data={"text": text[:50000], "userkey": text_ru_key},
                timeout=30,
            )
            post_data = post.json()
            uid = post_data.get("text_uid")
            if not uid:
                return None, f"text.ru: {post_data.get('error_desc', 'нет uid')}"
            # text.ru асинхронный — ждём результата (до 60 сек)
            for _ in range(30):
                time.sleep(2)
                r = session.post(
                    "https://api.text.ru/post",
                    data={"uid": uid, "userkey": text_ru_key},
                    timeout=30,
                )
                rd = r.json()
                if "text_unique" in rd:
                    return float(rd["text_unique"]), f"text.ru: uid={uid}"
            return None, "text.ru: таймаут ожидания результата"
        except Exception as exc:
            return None, f"text.ru error: {exc}"

    if content_watch_key:
        try:
            r = session.post(
                "https://content-watch.ru/public/api/?r=api/check",
                data={"key": content_watch_key, "text": text[:50000]},
                timeout=60,
            )
            rd = r.json()
            if "percent" in rd:
                return float(rd["percent"]), "content-watch.ru"
            return None, f"content-watch: {rd}"
        except Exception as exc:
            return None, f"content-watch error: {exc}"

    return None, (
        "API-ключ уникальности не настроен (нет ключей text_ru / "
        "content_watch в tokens.json)"
    )


# =============================================================
# Загрузка факторов и конфигурации
# =============================================================
def load_factors() -> list[dict]:
    try:
        with open(FACTORS_YAML, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data["factors"]
    except (FileNotFoundError, yaml.YAMLError, KeyError) as exc:
        print(f"[ERROR] Не удалось загрузить {FACTORS_YAML}: {exc}", file=sys.stderr)
        sys.exit(2)


def normalize_url(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url.rstrip("/")


def robots_allowed(base_url: str, path: str) -> bool:
    try:
        rp = RobotFileParser()
        rp.set_url(urljoin(base_url, "/robots.txt"))
        rp.read()
        return rp.can_fetch(USER_AGENT, urljoin(base_url, path))
    except Exception:
        return True


# =============================================================
# Фабрики результатов
# =============================================================
def _make_result(factor: dict, status: str, evidence: str, url: str | None = None) -> FactorResult:
    return FactorResult(
        id=factor["id"],
        category=factor["category"],
        name=factor["name"],
        status=status,
        severity=factor["severity"],
        weight=factor.get("weight", 5),
        evidence=evidence,
        url_checked=url,
        description=factor.get("description", ""),
    )


# =============================================================
# Чекеры факторов
# =============================================================
def check_meta_title(factor: dict, page: PageData) -> FactorResult:
    params = factor.get("params", {})
    min_len = params.get("min_length", 30)
    max_len = params.get("max_length", 70)
    title = page.title
    if not title:
        return _make_result(factor, STATUS_FAIL, "Title не задан", page.url)
    length = len(title)
    if min_len <= length <= max_len:
        return _make_result(
            factor,
            STATUS_PASS,
            f"Длина title: {length} символов (в диапазоне {min_len}-{max_len})",
            page.url,
        )
    status = STATUS_WARN if abs(length - (min_len + max_len) / 2) < 30 else STATUS_FAIL
    return _make_result(
        factor,
        status,
        f"Длина title: {length} (ожидается {min_len}-{max_len}). Текст: «{title}»",
        page.url,
    )


def check_meta_description(factor: dict, page: PageData) -> FactorResult:
    params = factor.get("params", {})
    if "cta_patterns" in params:
        if not page.description:
            return _make_result(factor, STATUS_FAIL, "Description не задан", page.url)
        desc_lower = page.description.lower()
        found = [p for p in params["cta_patterns"] if p in desc_lower]
        if found:
            return _make_result(
                factor,
                STATUS_PASS,
                f"Призывы к действию найдены: {', '.join(found[:3])}",
                page.url,
            )
        return _make_result(
            factor, STATUS_WARN, "В description нет явного призыва к действию", page.url
        )
    min_len = params.get("min_length", 120)
    max_len = params.get("max_length", 170)
    desc = page.description
    if not desc:
        return _make_result(factor, STATUS_FAIL, "Description не задан", page.url)
    length = len(desc)
    if min_len <= length <= max_len:
        return _make_result(
            factor,
            STATUS_PASS,
            f"Длина description: {length} (в диапазоне {min_len}-{max_len})",
            page.url,
        )
    return _make_result(
        factor,
        STATUS_WARN if length > 50 else STATUS_FAIL,
        f"Длина description: {length} (ожидается {min_len}-{max_len})",
        page.url,
    )


def check_og_tags(factor: dict, page: PageData) -> FactorResult:
    required = ["og:title", "og:description", "og:image"]
    missing = [tag for tag in required if tag not in page.og_tags]
    if not missing:
        return _make_result(
            factor,
            STATUS_PASS,
            "Все OG-теги заполнены: og:title, og:description, og:image",
            page.url,
        )
    return _make_result(
        factor,
        STATUS_FAIL if len(missing) == 3 else STATUS_WARN,
        f"Отсутствуют OG-теги: {', '.join(missing)}",
        page.url,
    )


def check_h1_count(factor: dict, page: PageData) -> FactorResult:
    expected = factor.get("params", {}).get("expected", 1)
    actual = len(page.h1_list)
    if actual == expected:
        return _make_result(
            factor, STATUS_PASS, f"Найден ровно один H1: «{page.h1_list[0][:80]}»", page.url
        )
    if actual == 0:
        return _make_result(factor, STATUS_FAIL, "H1 не найден на странице", page.url)
    return _make_result(
        factor,
        STATUS_FAIL,
        f"H1 count = {actual}, ожидается {expected}. Заголовки: {', '.join(h[:40] for h in page.h1_list[:3])}",
        page.url,
    )


def check_h1_content(factor: dict, page: PageData) -> FactorResult:
    params = factor.get("params", {})
    max_len = params.get("max_length", 70)
    if not page.h1_list:
        return _make_result(factor, STATUS_FAIL, "H1 отсутствует", page.url)
    h1 = page.h1_list[0]
    if len(h1) <= max_len:
        return _make_result(
            factor, STATUS_PASS, f"H1 длиной {len(h1)} символов (<={max_len})", page.url
        )
    return _make_result(
        factor, STATUS_WARN, f"H1 длиной {len(h1)} — превышает {max_len}. «{h1[:100]}»", page.url
    )


def check_h2_count(factor: dict, page: PageData) -> FactorResult:
    params = factor.get("params", {})
    min_count = params.get("min_count", 3)
    min_body = params.get("min_body_words", 0)
    body_words = len(tokenize_words(page.text))
    if body_words < min_body:
        return _make_result(
            factor,
            STATUS_NA,
            f"Текст {body_words} слов < порога {min_body} — проверка неприменима",
            page.url,
        )
    actual = len(page.h2_list)
    if actual >= min_count:
        return _make_result(factor, STATUS_PASS, f"Найдено {actual} H2 (>= {min_count})", page.url)
    return _make_result(
        factor,
        STATUS_WARN if actual > 0 else STATUS_FAIL,
        f"Найдено {actual} H2, требуется минимум {min_count}",
        page.url,
    )


def check_headings_hierarchy(factor: dict, page: PageData) -> FactorResult:
    soup = page.soup
    if soup is None:
        return _make_result(factor, STATUS_NA, "HTML не распарсен", page.url)
    seq = []
    for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        seq.append(int(tag.name[1]))
    if not seq:
        return _make_result(factor, STATUS_FAIL, "Заголовков на странице нет", page.url)
    issues = []
    for i in range(1, len(seq)):
        if seq[i] > seq[i - 1] + 1:
            issues.append(f"h{seq[i - 1]} → h{seq[i]}")
    if issues:
        return _make_result(
            factor,
            STATUS_WARN,
            f"Нарушения иерархии ({len(issues)}): {', '.join(issues[:3])}",
            page.url,
        )
    return _make_result(factor, STATUS_PASS, "Иерархия заголовков корректна", page.url)


def check_paragraph_length(factor: dict, page: PageData) -> FactorResult:
    params = factor.get("params", {})
    min_s = params.get("min_sentences", 2)
    max_s = params.get("max_sentences", 5)
    if not page.paragraphs:
        return _make_result(factor, STATUS_NA, "Абзацы <p> не найдены", page.url)
    sent_counts = [count_sentences(p) for p in page.paragraphs]
    # Учитываем только абзацы с хотя бы 20 символами
    meaningful = [c for c, p in zip(sent_counts, page.paragraphs) if len(p) > 20]
    if not meaningful:
        return _make_result(factor, STATUS_WARN, "Содержательных абзацев <20 символов", page.url)
    avg = sum(meaningful) / len(meaningful)
    if min_s <= avg <= max_s:
        return _make_result(
            factor, STATUS_PASS, f"Средняя длина абзаца: {avg:.1f} предложения", page.url
        )
    return _make_result(
        factor,
        STATUS_WARN,
        f"Средняя длина абзаца: {avg:.1f} предложений (ожидается {min_s}-{max_s})",
        page.url,
    )


def check_body_length(factor: dict, page: PageData) -> FactorResult:
    params = factor.get("params", {})
    min_words = params.get("min_words", 300)
    words = len(tokenize_words(page.text))
    if words >= min_words:
        return _make_result(
            factor, STATUS_PASS, f"Объём текста: {words} слов (>= {min_words})", page.url
        )
    ratio = words / min_words if min_words else 0
    status = STATUS_WARN if ratio > 0.6 else STATUS_FAIL
    return _make_result(
        factor,
        status,
        f"Объём текста: {words} слов, требуется минимум {min_words}",
        page.url,
    )


def check_tf_density(factor: dict, page: PageData, keyword: str) -> FactorResult:
    if not keyword:
        return _make_result(factor, STATUS_MANUAL, "Не задан --keyword для проверки TF", page.url)
    words = tokenize_words(page.text)
    pct = tf_density(words, keyword)
    params = factor.get("params", {})
    min_p = params.get("min_percent", 2.0)
    max_p = params.get("max_percent", 4.0)
    if min_p <= pct <= max_p:
        return _make_result(factor, STATUS_PASS, f"TF для «{keyword}»: {pct}%", page.url)
    if pct < min_p:
        return _make_result(
            factor,
            STATUS_WARN,
            f"TF для «{keyword}»: {pct}% — ниже минимума {min_p}%",
            page.url,
        )
    return _make_result(
        factor, STATUS_FAIL, f"TF для «{keyword}»: {pct}% — переспам (> {max_p}%)", page.url
    )


def check_classic_nausea(factor: dict, page: PageData) -> FactorResult:
    words = tokenize_words(page.text)
    nausea, top_word = classic_nausea(words)
    max_val = factor.get("params", {}).get("max_value", 7.0)
    if nausea <= max_val:
        return _make_result(
            factor,
            STATUS_PASS,
            f"Классическая тошнота: {nausea} (топ-слово «{top_word}»)",
            page.url,
        )
    return _make_result(
        factor,
        STATUS_FAIL,
        f"Классическая тошнота: {nausea} > {max_val} (топ-слово «{top_word}»)",
        page.url,
    )


def check_academic_nausea(factor: dict, page: PageData) -> FactorResult:
    pct = academic_nausea(tokenize_words(page.text))
    params = factor.get("params", {})
    min_p = params.get("min_percent", 5.0)
    max_p = params.get("max_percent", 9.0)
    if min_p <= pct <= max_p:
        return _make_result(factor, STATUS_PASS, f"Академическая тошнота: {pct}%", page.url)
    return _make_result(
        factor,
        STATUS_WARN,
        f"Академическая тошнота: {pct}% (диапазон {min_p}-{max_p}%)",
        page.url,
    )


def check_stopwords_ratio(factor: dict, page: PageData) -> FactorResult:
    pct = stopwords_ratio(tokenize_words(page.text))
    max_p = factor.get("params", {}).get("max_percent", 30.0)
    if pct <= max_p:
        return _make_result(factor, STATUS_PASS, f"Водность: {pct}% (<= {max_p}%)", page.url)
    return _make_result(factor, STATUS_WARN, f"Водность: {pct}% > {max_p}%", page.url)


def check_key_in_first_para(factor: dict, page: PageData, keyword: str, morph) -> FactorResult:
    if not keyword:
        return _make_result(factor, STATUS_MANUAL, "Не задан --keyword", page.url)
    first_n = factor.get("params", {}).get("first_words", 100)
    words = tokenize_words(page.text)[:first_n]
    first_text = " ".join(words)
    if word_key_exact_or_morph(first_text, keyword, morph):
        return _make_result(
            factor, STATUS_PASS, f"Ключ «{keyword}» найден в первых {first_n} словах", page.url
        )
    return _make_result(
        factor,
        STATUS_WARN,
        f"Ключ «{keyword}» НЕ найден в первых {first_n} словах страницы",
        page.url,
    )


def check_key_in_title(factor: dict, page: PageData, keyword: str, morph) -> FactorResult:
    if not keyword:
        return _make_result(factor, STATUS_MANUAL, "Не задан --keyword", page.url)
    if not page.title:
        return _make_result(factor, STATUS_FAIL, "Title отсутствует", page.url)
    if word_key_exact_or_morph(page.title, keyword, morph):
        return _make_result(
            factor,
            STATUS_PASS,
            f"Ключ «{keyword}» найден в title",
            page.url,
        )
    return _make_result(
        factor, STATUS_FAIL, f"Ключ «{keyword}» НЕ найден в title: «{page.title}»", page.url
    )


def check_key_in_h1(factor: dict, page: PageData, keyword: str, morph) -> FactorResult:
    if not keyword:
        return _make_result(factor, STATUS_MANUAL, "Не задан --keyword", page.url)
    if not page.h1_list:
        return _make_result(factor, STATUS_FAIL, "H1 отсутствует", page.url)
    if word_key_exact_or_morph(page.h1_list[0], keyword, morph):
        return _make_result(factor, STATUS_PASS, f"Ключ найден в H1", page.url)
    return _make_result(
        factor,
        STATUS_FAIL,
        f"Ключ «{keyword}» НЕ найден в H1: «{page.h1_list[0][:80]}»",
        page.url,
    )


def check_lsi_coverage(factor: dict, page: PageData, lsi_words: list[str]) -> FactorResult:
    if not lsi_words:
        return _make_result(
            factor,
            STATUS_MANUAL,
            "Не задан --lsi-words (через запятую) для проверки LSI-покрытия",
            page.url,
        )
    pct, found = lsi_coverage(page.text, lsi_words)
    min_p = factor.get("params", {}).get("min_percent", 60.0)
    if pct >= min_p:
        return _make_result(
            factor,
            STATUS_PASS,
            f"LSI-покрытие: {pct}% ({len(found)}/{len(lsi_words)}). Найдено: {', '.join(found[:5])}",
            page.url,
        )
    missing = [w for w in lsi_words if w not in found]
    return _make_result(
        factor,
        STATUS_WARN,
        f"LSI-покрытие: {pct}% (< {min_p}%). Отсутствуют: {', '.join(missing[:5])}",
        page.url,
    )


def check_readability(factor: dict, page: PageData) -> FactorResult:
    score = flesch_kincaid_ru(page.text)
    params = factor.get("params", {})
    min_s = params.get("min_score", 60)
    max_s = params.get("max_score", 80)
    if min_s <= score <= max_s:
        return _make_result(factor, STATUS_PASS, f"Индекс Флеша: {score} (оптимум)", page.url)
    if score < min_s:
        return _make_result(
            factor,
            STATUS_WARN,
            f"Индекс Флеша: {score} — текст сложен для восприятия (нужно {min_s}-{max_s})",
            page.url,
        )
    return _make_result(
        factor,
        STATUS_WARN,
        f"Индекс Флеша: {score} — текст слишком простой (нужно {min_s}-{max_s})",
        page.url,
    )


def check_caps_spam(factor: dict, page: PageData) -> FactorResult:
    caps = caps_words_count(page.text)
    max_caps = factor.get("params", {}).get("max_caps_words", 2)
    if len(caps) <= max_caps:
        return _make_result(
            factor, STATUS_PASS, f"Слов в CAPS LOCK: {len(caps)} (<= {max_caps})", page.url
        )
    return _make_result(
        factor,
        STATUS_WARN,
        f"Слов в CAPS LOCK: {len(caps)} (> {max_caps}). Примеры: {', '.join(caps[:5])}",
        page.url,
    )


def check_exclamation_spam(factor: dict, page: PageData) -> FactorResult:
    count = exclamation_spam_count(page.text)
    if count == 0:
        return _make_result(factor, STATUS_PASS, "Множественные «!!!» не найдены", page.url)
    return _make_result(
        factor, STATUS_WARN, f"Найдено {count} серий «!!!» в тексте", page.url
    )


def check_alt_images(factor: dict, page: PageData) -> FactorResult:
    if page.img_count == 0:
        return _make_result(factor, STATUS_NA, "На странице нет картинок", page.url)
    min_cov = factor.get("params", {}).get("min_coverage", 0.9)
    if page.alt_coverage >= min_cov:
        return _make_result(
            factor,
            STATUS_PASS,
            f"Alt есть у {page.alt_coverage * 100:.0f}% картинок ({page.img_count} всего)",
            page.url,
        )
    return _make_result(
        factor,
        STATUS_FAIL,
        f"Alt есть только у {page.alt_coverage * 100:.0f}% картинок (порог {min_cov * 100:.0f}%)",
        page.url,
    )


def check_alt_keyword(factor: dict, page: PageData, keyword: str) -> FactorResult:
    if not keyword:
        return _make_result(factor, STATUS_MANUAL, "Не задан --keyword", page.url)
    if page.soup is None or page.img_count == 0:
        return _make_result(factor, STATUS_NA, "Нет картинок", page.url)
    key_lower = keyword.lower()
    key_tokens = tokenize_words(key_lower)
    matches = 0
    for img in page.soup.find_all("img"):
        alt = (img.get("alt") or "").lower()
        if not alt:
            continue
        if key_lower in alt or any(t in alt for t in key_tokens):
            matches += 1
    if matches >= 1:
        return _make_result(
            factor, STATUS_PASS, f"Ключ найден в alt у {matches} картинок", page.url
        )
    return _make_result(
        factor, STATUS_WARN, "Ключевое слово не встречается ни в одном alt", page.url
    )


def check_internal_links(factor: dict, page: PageData) -> FactorResult:
    min_count = factor.get("params", {}).get("min_count", 3)
    if page.internal_links >= min_count:
        return _make_result(
            factor,
            STATUS_PASS,
            f"Внутренних ссылок: {page.internal_links} (>= {min_count})",
            page.url,
        )
    return _make_result(
        factor,
        STATUS_WARN,
        f"Внутренних ссылок: {page.internal_links} (< {min_count})",
        page.url,
    )


def check_external_links(factor: dict, page: PageData) -> FactorResult:
    params = factor.get("params", {})
    min_count = params.get("min_count", 1)
    max_count = params.get("max_count", 5)
    actual = page.external_links
    if min_count <= actual <= max_count:
        return _make_result(
            factor, STATUS_PASS, f"Внешних ссылок: {actual} (в диапазоне {min_count}-{max_count})", page.url
        )
    return _make_result(
        factor,
        STATUS_WARN,
        f"Внешних ссылок: {actual} (оптимум {min_count}-{max_count})",
        page.url,
    )


def check_anchor_diversity(factor: dict, page: PageData) -> FactorResult:
    params = factor.get("params", {})
    generic = set(params.get("generic_anchors", []))
    max_ratio = params.get("max_generic_ratio", 0.3)
    if not page.anchors:
        return _make_result(factor, STATUS_NA, "На странице нет ссылок с анкорами", page.url)
    generic_count = sum(1 for a in page.anchors if a in generic)
    ratio = generic_count / len(page.anchors)
    if ratio <= max_ratio:
        return _make_result(
            factor,
            STATUS_PASS,
            f"Generic-анкоров: {ratio * 100:.0f}% ({generic_count}/{len(page.anchors)})",
            page.url,
        )
    return _make_result(
        factor,
        STATUS_WARN,
        f"Generic-анкоров: {ratio * 100:.0f}% (> {max_ratio * 100:.0f}%)",
        page.url,
    )


def check_lists_count(factor: dict, page: PageData) -> FactorResult:
    min_count = factor.get("params", {}).get("min_count", 1)
    if page.list_count >= min_count:
        return _make_result(factor, STATUS_PASS, f"Списков на странице: {page.list_count}", page.url)
    return _make_result(
        factor, STATUS_WARN, f"Списков: {page.list_count} (требуется {min_count})", page.url
    )


def check_tables_count(factor: dict, page: PageData) -> FactorResult:
    min_count = factor.get("params", {}).get("min_count", 1)
    if page.table_count >= min_count:
        return _make_result(factor, STATUS_PASS, f"Таблиц: {page.table_count}", page.url)
    return _make_result(
        factor, STATUS_WARN, f"Таблиц: {page.table_count} (требуется {min_count})", page.url
    )


def check_text_contains(factor: dict, page: PageData) -> FactorResult:
    params = factor.get("params", {})
    patterns = params.get("patterns", [])
    min_matches = params.get("min_matches", 1)
    text_lower = page.text.lower()
    found = [p for p in patterns if p in text_lower]
    if len(found) >= min_matches:
        return _make_result(
            factor, STATUS_PASS, f"Найдены триггеры: {', '.join(found[:5])}", page.url
        )
    return _make_result(
        factor,
        STATUS_FAIL,
        f"Не найдено ни одного из: {', '.join(patterns[:5])}",
        page.url,
    )


def check_freshness(factor: dict, page: PageData) -> FactorResult:
    if not page.lastmod:
        return _make_result(
            factor,
            STATUS_WARN,
            "Дата публикации/обновления не найдена (нет article:modified_time)",
            page.url,
        )
    try:
        dt = datetime.fromisoformat(page.lastmod.replace("Z", "+00:00"))
        age_days = (datetime.now(timezone.utc) - dt).days
    except Exception:
        return _make_result(factor, STATUS_WARN, f"Не удалось распарсить дату: {page.lastmod}", page.url)
    max_age = factor.get("params", {}).get("max_age_days", 365)
    if age_days <= max_age:
        return _make_result(
            factor, STATUS_PASS, f"Обновлено {age_days} дней назад (<= {max_age})", page.url
        )
    return _make_result(
        factor,
        STATUS_WARN,
        f"Обновлено {age_days} дней назад — контент устарел (> {max_age})",
        page.url,
    )


def check_uniqueness(
    factor: dict,
    page: PageData,
    session: requests.Session,
    tokens: dict[str, Any] | None = None,
) -> FactorResult:
    pct, evidence = check_uniqueness_api(page.text, session, tokens)
    if pct is None:
        return _make_result(
            factor, STATUS_MANUAL, f"Автопроверка невозможна — {evidence}", page.url
        )
    min_p = factor.get("params", {}).get("min_percent", 85.0)
    if pct >= min_p:
        return _make_result(
            factor, STATUS_PASS, f"Уникальность: {pct}% ({evidence})", page.url
        )
    return _make_result(
        factor, STATUS_FAIL, f"Уникальность: {pct}% (< {min_p}%, {evidence})", page.url
    )


def check_duplicate_internal(factor: dict, pages: list[PageData]) -> FactorResult:
    if len(pages) < 2:
        return _make_result(
            factor,
            STATUS_NA,
            "Одна страница — внутренние дубли проверить нельзя",
        )
    threshold = factor.get("params", {}).get("similarity_threshold", 0.85)
    # Упрощённая оценка: Jaccard по множеству слов
    sigs = []
    for p in pages:
        words = set(tokenize_words(p.text))
        sigs.append((p.url, words))
    pairs_high = []
    for i in range(len(sigs)):
        for j in range(i + 1, len(sigs)):
            a = sigs[i][1]
            b = sigs[j][1]
            if not a or not b:
                continue
            sim = len(a & b) / max(len(a | b), 1)
            if sim >= threshold:
                pairs_high.append((sigs[i][0], sigs[j][0], round(sim, 2)))
    if not pairs_high:
        return _make_result(
            factor,
            STATUS_PASS,
            f"Дублей (Jaccard >= {threshold}) не обнаружено среди {len(pages)} страниц",
        )
    evidence = "; ".join([f"{a} ≈ {b} ({s})" for a, b, s in pairs_high[:3]])
    return _make_result(factor, STATUS_FAIL, f"Найдены дубли: {evidence}")


def check_canibalization(factor: dict, pages: list[PageData]) -> FactorResult:
    """Ищем страницы с очень похожими title."""
    if len(pages) < 2:
        return _make_result(factor, STATUS_NA, "Одна страница")
    from collections import Counter

    titles = [(p.url, (p.title or "").lower().strip()) for p in pages if p.title]
    if len(titles) < 2:
        return _make_result(factor, STATUS_NA, "Недостаточно title для сравнения")
    cnt = Counter(t for _, t in titles)
    dups = [(u, t) for u, t in titles if cnt[t] > 1]
    if not dups:
        # Проверим высокую Jaccard близость по токенам
        def toks(s: str) -> set[str]:
            return set(tokenize_words(s))

        high = []
        for i in range(len(titles)):
            for j in range(i + 1, len(titles)):
                a = toks(titles[i][1])
                b = toks(titles[j][1])
                if not a or not b:
                    continue
                sim = len(a & b) / max(len(a | b), 1)
                if sim >= 0.8:
                    high.append((titles[i][0], titles[j][0], round(sim, 2)))
        if not high:
            return _make_result(factor, STATUS_PASS, "Каннибализации title не обнаружено")
        return _make_result(
            factor,
            STATUS_WARN,
            "Близкие title: " + "; ".join([f"{a} ≈ {b} ({s})" for a, b, s in high[:3]]),
        )
    return _make_result(
        factor, STATUS_FAIL, "Идентичные title: " + "; ".join([u for u, _ in dups[:3]])
    )


def check_manual(factor: dict, page: PageData | None = None) -> FactorResult:
    url = page.url if page else None
    return _make_result(factor, STATUS_MANUAL, "Требуется ручная проверка", url)


# =============================================================
# Основной pipeline
# =============================================================
def determine_page_type(url: str) -> str:
    low = url.lower()
    if "/blog" in low or "/news" in low or "/articles" in low or "/novosti" in low:
        return "blog"
    if "/product" in low or "/tovar" in low or "/item" in low:
        return "product"
    if "/catalog" in low or "/katalog" in low or "/shop" in low:
        return "catalog"
    return "home"


def run_audit(
    target_url: str,
    keyword: str | None = None,
    lsi_words: list[str] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    verify_ssl: bool = True,
    extra_urls: list[str] | None = None,
) -> AuditResult:
    target_url = normalize_url(target_url)
    session = make_session(verify_ssl=verify_ssl)
    morph = load_morph()

    # ── Token auto-discovery ──────────────────────────────────
    tokens = load_tokens()
    tokens_found: dict[str, bool] = {
        "metrika": bool(get_metrika_token(tokens)),
        "webmaster": bool(get_webmaster_token(tokens)),
        "topvisor": bool(get_topvisor_key(tokens)),
        "text_ru": bool(get_text_ru_key(tokens)),
        "content_watch": bool(get_content_watch_key(tokens)),
    }
    active_providers = [k for k, v in tokens_found.items() if v]
    if active_providers:
        print(
            f"[tokens] Auto-discovered: {', '.join(active_providers)}",
            file=sys.stderr,
        )
    else:
        print("[tokens] No API keys found in tokens.json", file=sys.stderr)

    # Auto-detect Metrika counter for the target domain
    counter_id = auto_detect_counter_id(tokens, target_url)
    if counter_id:
        print(f"[tokens] Metrika counter auto-detected: {counter_id}", file=sys.stderr)

    result = AuditResult(
        target_url=target_url,
        audited_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        keyword=keyword,
        lsi_words=lsi_words or [],
    )
    result.meta["tokens_discovered"] = tokens_found
    if counter_id:
        result.meta["metrika_counter_id"] = counter_id

    if morph is None:
        result.meta["morph_warning"] = (
            "pymorphy3 не установлен — морфологические проверки ключа отключены"
        )

    # ── Webmaster: auto-suggest keyword from top queries ──────
    wm_token = get_webmaster_token(tokens)
    wm_user_id = get_webmaster_user_id(tokens)
    wm_queries: list[dict[str, Any]] = []
    if wm_token and wm_user_id and not keyword:
        parsed = urlparse(target_url)
        host_id = webmaster_host_id(session, wm_token, wm_user_id, parsed.netloc)
        if host_id:
            wm_queries = webmaster_top_queries(
                session, wm_token, wm_user_id, host_id, limit=10,
            )
            if wm_queries:
                top_query = wm_queries[0].get("query", "")
                if top_query:
                    keyword = top_query
                    result.meta["keyword_source"] = "yandex_webmaster_auto"
                    result.meta["webmaster_top_queries"] = wm_queries[:5]
                    print(
                        f"[webmaster] Auto-detected keyword: '{keyword}' "
                        f"(from {len(wm_queries)} top queries)",
                        file=sys.stderr,
                    )
    elif wm_token and wm_user_id and keyword:
        # Even with keyword provided, fetch queries for enrichment
        parsed = urlparse(target_url)
        host_id = webmaster_host_id(session, wm_token, wm_user_id, parsed.netloc)
        if host_id:
            wm_queries = webmaster_top_queries(
                session, wm_token, wm_user_id, host_id, limit=10,
            )
            if wm_queries:
                result.meta["webmaster_top_queries"] = wm_queries[:5]

    # Update keyword in result after auto-detection
    result.keyword = keyword

    # ── Topvisor: fetch keyword positions for enrichment ──────
    tv_key = get_topvisor_key(tokens)
    tv_user_id = get_topvisor_user_id(tokens)
    tv_positions: list[dict[str, Any]] = []
    if tv_key and tv_user_id:
        parsed = urlparse(target_url)
        proj_id = topvisor_find_project(session, tv_key, tv_user_id, parsed.netloc)
        if proj_id:
            tv_positions = topvisor_get_positions(
                session, tv_key, tv_user_id, proj_id, limit=20,
            )
            if tv_positions:
                result.meta["topvisor_positions"] = tv_positions[:10]
                print(
                    f"[topvisor] Fetched {len(tv_positions)} keyword positions",
                    file=sys.stderr,
                )

    # Загружаем целевую страницу
    print(f"[1/3] Загрузка: {target_url}", file=sys.stderr)
    primary = fetch(session, target_url, timeout)
    if not primary.ok:
        result.meta["error"] = (
            f"Главная недоступна: {primary.error or f'status {primary.status_code}'}"
        )
        print(f"[ERROR] {result.meta['error']}", file=sys.stderr)
        return result
    primary.page_type = determine_page_type(target_url)
    pages = [primary]
    result.pages_crawled[primary.page_type] = primary.url

    # Extra URLs для проверки дублей / каннибализации
    for extra in extra_urls or []:
        print(f"      + extra: {extra}", file=sys.stderr)
        p = fetch(session, extra, timeout)
        if p.ok:
            p.page_type = determine_page_type(extra)
            pages.append(p)
            key = f"{p.page_type}_{len([x for x in pages if x.page_type == p.page_type])}"
            result.pages_crawled[key] = p.url

    # Прогоняем факторы
    factors = load_factors()
    result.meta["factors_total"] = len(factors)
    print(f"[2/3] Проверка {len(factors)} факторов на {len(pages)} страницах", file=sys.stderr)

    for factor in factors:
        ct = factor.get("check_type", "manual")
        target_page = primary  # по умолчанию проверяем главную

        try:
            if ct == "meta_title":
                fr = check_meta_title(factor, target_page)
            elif ct == "meta_description":
                fr = check_meta_description(factor, target_page)
            elif ct == "og_tags":
                fr = check_og_tags(factor, target_page)
            elif ct == "h1_count":
                fr = check_h1_count(factor, target_page)
            elif ct == "h1_content":
                fr = check_h1_content(factor, target_page)
            elif ct == "h2_count":
                fr = check_h2_count(factor, target_page)
            elif ct == "headings_hierarchy":
                fr = check_headings_hierarchy(factor, target_page)
            elif ct == "paragraph_length":
                fr = check_paragraph_length(factor, target_page)
            elif ct == "body_length":
                fr = check_body_length(factor, target_page)
            elif ct == "tf_density":
                fr = check_tf_density(factor, target_page, keyword or "")
            elif ct == "classic_nausea":
                fr = check_classic_nausea(factor, target_page)
            elif ct == "academic_nausea":
                fr = check_academic_nausea(factor, target_page)
            elif ct == "stopwords_ratio":
                fr = check_stopwords_ratio(factor, target_page)
            elif ct == "key_in_first_para":
                fr = check_key_in_first_para(factor, target_page, keyword or "", morph)
            elif ct == "key_in_title":
                fr = check_key_in_title(factor, target_page, keyword or "", morph)
            elif ct == "key_in_h1":
                fr = check_key_in_h1(factor, target_page, keyword or "", morph)
            elif ct == "lsi_coverage":
                fr = check_lsi_coverage(factor, target_page, lsi_words or [])
            elif ct == "readability_flesch":
                fr = check_readability(factor, target_page)
            elif ct == "caps_spam":
                fr = check_caps_spam(factor, target_page)
            elif ct == "exclamation_spam":
                fr = check_exclamation_spam(factor, target_page)
            elif ct == "alt_images":
                fr = check_alt_images(factor, target_page)
            elif ct == "alt_keyword":
                fr = check_alt_keyword(factor, target_page, keyword or "")
            elif ct == "internal_links":
                fr = check_internal_links(factor, target_page)
            elif ct == "external_links":
                fr = check_external_links(factor, target_page)
            elif ct == "anchor_diversity":
                fr = check_anchor_diversity(factor, target_page)
            elif ct == "lists_count":
                fr = check_lists_count(factor, target_page)
            elif ct == "tables_count":
                fr = check_tables_count(factor, target_page)
            elif ct == "text_contains":
                fr = check_text_contains(factor, target_page)
            elif ct == "freshness":
                fr = check_freshness(factor, target_page)
            elif ct == "uniqueness_api":
                fr = check_uniqueness(factor, target_page, session, tokens)
            elif ct == "duplicate_internal":
                fr = check_duplicate_internal(factor, pages)
            elif ct == "canibalization":
                fr = check_canibalization(factor, pages)
            else:
                fr = check_manual(factor, target_page)
        except Exception as exc:
            fr = _make_result(
                factor,
                STATUS_NA,
                f"Ошибка проверки: {type(exc).__name__}: {exc}",
                target_page.url,
            )
        result.factors.append(fr)

    print("[3/3] Формирование сводки", file=sys.stderr)
    result.meta["summary"] = summarize(result.factors)
    return result


def summarize(factors: list[FactorResult]) -> dict[str, Any]:
    counts = {STATUS_PASS: 0, STATUS_WARN: 0, STATUS_FAIL: 0, STATUS_MANUAL: 0, STATUS_NA: 0}
    by_category: dict[str, dict[str, int]] = {}
    critical_fails: list[dict[str, str]] = []
    weighted_pass = 0.0
    weighted_total = 0.0
    for f in factors:
        counts[f.status] = counts.get(f.status, 0) + 1
        cat = by_category.setdefault(
            f.category,
            {STATUS_PASS: 0, STATUS_WARN: 0, STATUS_FAIL: 0, STATUS_MANUAL: 0, STATUS_NA: 0},
        )
        cat[f.status] = cat.get(f.status, 0) + 1
        if f.status not in (STATUS_MANUAL, STATUS_NA):
            weighted_total += f.weight
            if f.status == STATUS_PASS:
                weighted_pass += f.weight
            elif f.status == STATUS_WARN:
                weighted_pass += f.weight * 0.5
        if f.status == STATUS_FAIL and f.severity in ("critical", "high"):
            critical_fails.append(
                {
                    "id": str(f.id),
                    "name": f.name,
                    "severity": f.severity,
                    "category": f.category,
                }
            )
    sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    critical_fails.sort(key=lambda x: sev_order.get(x["severity"], 9))
    score = round(weighted_pass / weighted_total * 100, 1) if weighted_total else 0.0
    return {
        "counts": counts,
        "by_category": by_category,
        "critical_fails_top": critical_fails[:5],
        "score": score,
    }


# =============================================================
# CLI
# =============================================================
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Text Factors Audit — аудит текстовых SEO-факторов Яндекса"
    )
    parser.add_argument("url", help="URL целевой страницы (https://example.com/page)")
    parser.add_argument("--output", "-o", default="text-audit.json", help="Путь к выходному JSON")
    parser.add_argument("--keyword", default=None, help="Основной ключевой запрос страницы")
    parser.add_argument(
        "--lsi-words",
        default=None,
        help="LSI-синонимы через запятую (пример: 'профиль,стеклопакет,монтаж')",
    )
    parser.add_argument(
        "--extra-urls",
        default=None,
        help="Дополнительные URL через запятую для проверки дублей и каннибализации",
    )
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Таймаут запросов")
    parser.add_argument("--no-verify-ssl", action="store_true", help="Отключить проверку SSL")
    args = parser.parse_args()

    lsi_words = (
        [w.strip() for w in args.lsi_words.split(",") if w.strip()]
        if args.lsi_words
        else []
    )
    extra_urls = (
        [u.strip() for u in args.extra_urls.split(",") if u.strip()]
        if args.extra_urls
        else []
    )

    try:
        result = run_audit(
            target_url=args.url,
            keyword=args.keyword,
            lsi_words=lsi_words,
            timeout=args.timeout,
            verify_ssl=not args.no_verify_ssl,
            extra_urls=extra_urls,
        )
    except Exception as exc:
        print(f"[FATAL] {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)

    summary = result.meta.get("summary", {})
    counts = summary.get("counts", {})
    print(
        f"\n[OK] Saved: {output_path}\n"
        f"     Score (weighted): {summary.get('score', 0)}%\n"
        f"     PASS: {counts.get('pass', 0)}  WARN: {counts.get('warn', 0)}  "
        f"FAIL: {counts.get('fail', 0)}  MANUAL: {counts.get('manual', 0)}  NA: {counts.get('na', 0)}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
