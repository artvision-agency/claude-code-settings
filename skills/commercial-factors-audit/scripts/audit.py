#!/usr/bin/env python3
"""
Commercial Factors Audit — MVP

Краулит сайт клиента и проверяет 118 коммерческих факторов Яндекса.
Выход: JSON с результатами по каждому фактору.

CLI:
    python3 audit.py https://example.com --output=audit.json
    python3 audit.py https://example.com --output=audit.json --timeout=30 --no-verify-ssl

Exit codes:
    0 — успех
    1 — невалидный URL / сайт недоступен
    2 — ошибка чтения factors-100.yaml
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
import yaml
from bs4 import BeautifulSoup

# ============================================================
# Константы
# ============================================================
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
FACTORS_YAML = SKILL_ROOT / "data" / "factors-100.yaml"
TOKENS_PATH = Path(os.path.expanduser("~/artvision-data/tokens.json"))

USER_AGENT = "ArtvisionPulse/0.1 (commercial factors audit; +https://artvision.pro)"
DEFAULT_TIMEOUT = 10
RETRY_COUNT = 2

# Карта логических страниц → список кандидатных URL (в порядке приоритета)
PAGE_URL_CANDIDATES: dict[str, list[str]] = {
    "home": ["/"],
    "contacts": ["/contacts", "/kontakty", "/contact", "/contacts/", "/kontakty/"],
    "about": ["/about", "/o-kompanii", "/o-nas", "/company", "/about/"],
    "delivery": ["/delivery", "/dostavka", "/shipping", "/delivery/"],
    "catalog": ["/catalog", "/shop", "/katalog", "/products", "/catalog/"],
    "product": [],  # определяется динамически — первая ссылка из каталога
    "blog": ["/blog", "/news", "/novosti", "/articles", "/blog/"],
}

STATUS_PASS = "pass"
STATUS_WARN = "warn"
STATUS_FAIL = "fail"
STATUS_MANUAL = "manual"
STATUS_NA = "na"  # страница не найдена, нечего проверять


# ============================================================
# Токены — автообнаружение из tokens.json
# ============================================================
def load_tokens() -> dict[str, Any]:
    """Читаем tokens.json, возвращаем словарь. Если нет — возвращаем пустой."""
    if not TOKENS_PATH.exists():
        return {}
    try:
        with open(TOKENS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"[WARN] Не удалось прочитать tokens.json: {exc}", file=sys.stderr)
        return {}


def get_metrika_token(tokens: dict[str, Any]) -> str | None:
    """Извлечь OAuth-токен Яндекс.Метрики."""
    return tokens.get("yandex", {}).get("metrika", {}).get("token")


def auto_detect_counter_id(tokens: dict[str, Any], domain: str) -> str | None:
    """Автоопределение counter_id из tokens.json по домену.

    Ищет ключи внутри yandex.metrika, содержащие slug домена.
    Например, для avto.world ищет *avtoworld*, *avto_world* и т.д.
    """
    metrika = tokens.get("yandex", {}).get("metrika", {})
    domain_clean = domain.replace("https://", "").replace("http://", "").rstrip("/").lower()
    # slug без точек и дефисов для нечёткого совпадения
    slug = domain_clean.replace(".", "").replace("-", "")

    for key, val in metrika.items():
        if key.startswith("_") or key in ("token", "client_id", "client_secret", "account"):
            continue
        # Простое значение — counter_id
        if isinstance(val, (str, int)):
            key_clean = key.lower().replace("_counter", "").replace("_", "")
            if key_clean in slug or slug in key_clean:
                return str(val)
        # Вложенный словарь с несколькими счётчиками (как varikozanet_counters)
        elif isinstance(val, dict):
            key_clean = key.lower().replace("_counters", "").replace("_counter", "").replace("_", "")
            if key_clean in slug or slug in key_clean:
                # Берём первый числовой counter (skip meta-ключи _desc, _updated)
                for sub_key, sub_val in val.items():
                    if sub_key.startswith("_"):
                        continue
                    if isinstance(sub_val, (str, int)) and str(sub_val).isdigit():
                        return str(sub_val)
    return None


# ============================================================
# Яндекс.Метрика API — лёгкие проверки для коммерческого аудита
# ============================================================
def metrika_check_counter_active(
    counter_id: str,
    token: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Проверяет что счётчик существует и собирает данные.

    Returns:
        {"active": bool, "name": str, "site": str, "visits_today": int, "error": str|None}
    """
    url = f"https://api-metrika.yandex.net/management/v1/counter/{counter_id}"
    headers = {"Authorization": f"OAuth {token}"}
    result: dict[str, Any] = {"active": False, "name": "", "site": "", "error": None}
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        if resp.status_code == 200:
            data = resp.json().get("counter", {})
            result["active"] = data.get("status") != "deleted"
            result["name"] = data.get("name", "")
            result["site"] = data.get("site", "")
            result["code_status"] = data.get("code_status", 0)  # 0=не проверен, 1=OK, 2=нет кода
        elif resp.status_code == 403:
            result["error"] = "Нет доступа к счётчику (403)"
        elif resp.status_code == 404:
            result["error"] = f"Счётчик {counter_id} не найден (404)"
        else:
            result["error"] = f"HTTP {resp.status_code}"
    except requests.RequestException as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def metrika_check_goals(
    counter_id: str,
    token: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Проверяет наличие целей (goals) в Метрике.

    Returns:
        {"goals_count": int, "goal_names": list[str], "has_ecommerce": bool, "error": str|None}
    """
    url = f"https://api-metrika.yandex.net/management/v1/counter/{counter_id}/goals"
    headers = {"Authorization": f"OAuth {token}"}
    result: dict[str, Any] = {"goals_count": 0, "goal_names": [], "has_ecommerce": False, "error": None}
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        if resp.status_code == 200:
            goals = resp.json().get("goals", [])
            result["goals_count"] = len(goals)
            result["goal_names"] = [g.get("name", "") for g in goals[:10]]
            # Определяем ecommerce-цели
            ecom_keywords = {"покупка", "заказ", "корзина", "оплата", "purchase", "order", "cart", "checkout", "ecommerce"}
            for g in goals:
                name_lower = g.get("name", "").lower()
                gtype = g.get("type", "").lower()
                if gtype == "e_commerce" or any(kw in name_lower for kw in ecom_keywords):
                    result["has_ecommerce"] = True
                    break
        elif resp.status_code == 403:
            result["error"] = "Нет доступа к целям (403)"
        else:
            result["error"] = f"HTTP {resp.status_code}"
    except requests.RequestException as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


# ============================================================
# Модели
# ============================================================
@dataclass
class PageData:
    """Результат загрузки одной страницы."""

    url: str
    status_code: int | None = None
    html: str = ""
    text: str = ""  # нормализованный текст для text_contains
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.status_code is not None and 200 <= self.status_code < 400 and self.html != ""


@dataclass
class FactorResult:
    """Результат проверки одного фактора."""

    id: int
    category: str
    name: str
    status: str  # pass | warn | fail | manual | na
    severity: str
    evidence: str
    url_checked: str | None = None
    description: str = ""


@dataclass
class AuditResult:
    """Итоговый отчёт по сайту."""

    target_url: str
    audited_at: str  # ISO datetime
    pages_crawled: dict[str, str] = field(default_factory=dict)  # logical_name -> real_url
    factors: list[FactorResult] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_url": self.target_url,
            "audited_at": self.audited_at,
            "pages_crawled": self.pages_crawled,
            "factors": [asdict(f) for f in self.factors],
            "meta": self.meta,
        }


# ============================================================
# HTTP
# ============================================================
def make_session(verify_ssl: bool = True) -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    session.verify = verify_ssl
    return session


def fetch(session: requests.Session, url: str, timeout: int = DEFAULT_TIMEOUT) -> PageData:
    """Загружает страницу с retry. Возвращает PageData (ok=False если не удалось)."""
    last_error: str | None = None
    for attempt in range(RETRY_COUNT + 1):
        try:
            resp = session.get(url, timeout=timeout, allow_redirects=True)
            html = resp.text if resp.text else ""
            text = ""
            if html:
                soup = BeautifulSoup(html, "html.parser")
                # Убираем скрипты/стили из текстового слоя
                for tag in soup(["script", "style", "noscript"]):
                    tag.decompose()
                text = re.sub(r"\s+", " ", soup.get_text(" ").lower()).strip()
            return PageData(url=resp.url, status_code=resp.status_code, html=html, text=text)
        except requests.RequestException as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt < RETRY_COUNT:
                time.sleep(1)
    return PageData(url=url, status_code=None, html="", text="", error=last_error)


def robots_allowed(base_url: str, path: str) -> bool:
    """Проверка robots.txt. При ошибке — разрешаем (fail-open для аудита)."""
    try:
        rp = RobotFileParser()
        rp.set_url(urljoin(base_url, "/robots.txt"))
        rp.read()
        return rp.can_fetch(USER_AGENT, urljoin(base_url, path))
    except Exception:
        return True


# ============================================================
# Краулинг — находим реальные URL для логических страниц
# ============================================================
def discover_page(
    session: requests.Session,
    base_url: str,
    logical_name: str,
    home_page: PageData,
    timeout: int,
) -> tuple[str | None, PageData | None]:
    """
    Для логического имени страницы (about, contacts...) находим реальный URL.
    Стратегия:
      1. Перебор стандартных кандидатов из PAGE_URL_CANDIDATES
      2. Для 'product' — первая ссылка из каталога
    """
    candidates = PAGE_URL_CANDIDATES.get(logical_name, [])

    # Эвристика для product — ищем ссылку с /product/ или /tovar/
    if logical_name == "product" and home_page.ok:
        soup = BeautifulSoup(home_page.html, "html.parser")
        for a in soup.find_all("a", href=True):
            href = str(a["href"])
            if any(p in href.lower() for p in ["/product/", "/tovar/", "/item/", "/goods/", "-p-"]):
                full = urljoin(base_url, href)
                page = fetch(session, full, timeout)
                if page.ok:
                    return full, page
        return None, None

    for path in candidates:
        url = urljoin(base_url, path)
        if not robots_allowed(base_url, path):
            continue
        page = fetch(session, url, timeout)
        if page.ok:
            return url, page
    return None, None


# ============================================================
# Проверки факторов
# ============================================================
def _contains_any(text: str, patterns: list[str]) -> tuple[bool, str]:
    for p in patterns:
        if p.lower() in text:
            return True, p
    return False, ""


def check_text_contains(factor: dict, pages: dict[str, PageData]) -> FactorResult:
    target_pages = factor.get("pages") or ["home"]
    patterns = factor.get("patterns") or []

    for logical in target_pages:
        page = pages.get(logical)
        if page is None or not page.ok:
            continue
        found, matched = _contains_any(page.text, patterns)
        if found:
            return FactorResult(
                id=factor["id"],
                category=factor["category"],
                name=factor["name"],
                status=STATUS_PASS,
                severity=factor["severity"],
                evidence=f"Найдено '{matched}' на {logical}",
                url_checked=page.url,
                description=factor["description"],
            )
    return FactorResult(
        id=factor["id"],
        category=factor["category"],
        name=factor["name"],
        status=STATUS_FAIL,
        severity=factor["severity"],
        evidence=f"Не найдено ни одного из: {', '.join(patterns[:5])}{'...' if len(patterns) > 5 else ''}",
        url_checked=None,
        description=factor["description"],
    )


def check_url_exists(factor: dict, pages: dict[str, PageData], base_url: str, session: requests.Session) -> FactorResult:
    """Ищем указанные URL-паттерны либо как подстроку в путях ссылок home, либо как прямые запросы."""
    patterns = factor.get("patterns") or []
    home = pages.get("home")

    # 1. Проверка через ссылки на главной + текст меню
    if home and home.ok:
        soup = BeautifulSoup(home.html, "html.parser")
        link_hrefs = [str(a.get("href", "")).lower() for a in soup.find_all("a", href=True)]
        link_texts = [a.get_text(" ").lower().strip() for a in soup.find_all("a")]
        combined = " ".join(link_hrefs + link_texts)
        found, matched = _contains_any(combined, patterns)
        if found:
            return FactorResult(
                id=factor["id"],
                category=factor["category"],
                name=factor["name"],
                status=STATUS_PASS,
                severity=factor["severity"],
                evidence=f"Найдена ссылка/пункт меню: '{matched}'",
                url_checked=home.url,
                description=factor["description"],
            )

    # 2. Прямой HEAD-запрос по типовым путям (только если начинаются с /)
    for p in patterns:
        if p.startswith("/"):
            url = urljoin(base_url, p)
            try:
                resp = session.head(url, timeout=5, allow_redirects=True)
                if 200 <= resp.status_code < 400:
                    return FactorResult(
                        id=factor["id"],
                        category=factor["category"],
                        name=factor["name"],
                        status=STATUS_PASS,
                        severity=factor["severity"],
                        evidence=f"URL доступен: {p} ({resp.status_code})",
                        url_checked=url,
                        description=factor["description"],
                    )
            except requests.RequestException:
                continue

    return FactorResult(
        id=factor["id"],
        category=factor["category"],
        name=factor["name"],
        status=STATUS_FAIL,
        severity=factor["severity"],
        evidence=f"URL/пункт меню не найден: {', '.join(patterns[:5])}",
        url_checked=None,
        description=factor["description"],
    )


def check_element_exists(factor: dict, pages: dict[str, PageData]) -> FactorResult:
    target_pages = factor.get("pages") or ["home"]
    patterns = factor.get("patterns") or []

    for logical in target_pages:
        page = pages.get(logical)
        if page is None or not page.ok:
            continue
        soup = BeautifulSoup(page.html, "html.parser")
        for selector in patterns:
            try:
                if soup.select(selector):
                    return FactorResult(
                        id=factor["id"],
                        category=factor["category"],
                        name=factor["name"],
                        status=STATUS_PASS,
                        severity=factor["severity"],
                        evidence=f"Найден элемент '{selector}' на {logical}",
                        url_checked=page.url,
                        description=factor["description"],
                    )
            except Exception:
                continue
    return FactorResult(
        id=factor["id"],
        category=factor["category"],
        name=factor["name"],
        status=STATUS_FAIL,
        severity=factor["severity"],
        evidence=f"Элементы не найдены: {', '.join(patterns[:3])}",
        url_checked=None,
        description=factor["description"],
    )


def check_structured_data(factor: dict, pages: dict[str, PageData]) -> FactorResult:
    home = pages.get("home")
    if home is None or not home.ok:
        return FactorResult(
            id=factor["id"],
            category=factor["category"],
            name=factor["name"],
            status=STATUS_NA,
            severity=factor["severity"],
            evidence="Главная страница не загружена",
            description=factor["description"],
        )
    soup = BeautifulSoup(home.html, "html.parser")
    json_ld = soup.find_all("script", attrs={"type": "application/ld+json"})
    microdata = soup.find_all(attrs={"itemscope": True})
    if json_ld or microdata:
        types: list[str] = []
        for script in json_ld:
            try:
                data = json.loads(script.string or "{}")
                if isinstance(data, dict) and "@type" in data:
                    types.append(str(data["@type"]))
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and "@type" in item:
                            types.append(str(item["@type"]))
            except (json.JSONDecodeError, AttributeError):
                continue
        evidence_parts = []
        if json_ld:
            evidence_parts.append(f"JSON-LD: {len(json_ld)} блок(ов)")
        if types:
            evidence_parts.append(f"типы: {', '.join(set(types))}")
        if microdata:
            evidence_parts.append(f"microdata: {len(microdata)} элемент(ов)")
        return FactorResult(
            id=factor["id"],
            category=factor["category"],
            name=factor["name"],
            status=STATUS_PASS,
            severity=factor["severity"],
            evidence="; ".join(evidence_parts),
            url_checked=home.url,
            description=factor["description"],
        )
    return FactorResult(
        id=factor["id"],
        category=factor["category"],
        name=factor["name"],
        status=STATUS_FAIL,
        severity=factor["severity"],
        evidence="Микроразметки (JSON-LD или microdata) не обнаружено",
        url_checked=home.url,
        description=factor["description"],
    )


def check_http_status(factor: dict, target_url: str, session: requests.Session) -> FactorResult:
    """Проверка HTTPS и поведение при запросе http://"""
    parsed = urlparse(target_url)
    is_https = parsed.scheme == "https"
    if is_https:
        return FactorResult(
            id=factor["id"],
            category=factor["category"],
            name=factor["name"],
            status=STATUS_PASS,
            severity=factor["severity"],
            evidence=f"Сайт работает на HTTPS: {target_url}",
            url_checked=target_url,
            description=factor["description"],
        )
    # Попробуем редирект http → https
    http_url = target_url.replace("https://", "http://")
    try:
        resp = session.get(http_url, timeout=5, allow_redirects=True)
        if resp.url.startswith("https://"):
            return FactorResult(
                id=factor["id"],
                category=factor["category"],
                name=factor["name"],
                status=STATUS_PASS,
                severity=factor["severity"],
                evidence=f"Редирект HTTP→HTTPS настроен: {resp.url}",
                url_checked=resp.url,
                description=factor["description"],
            )
    except requests.RequestException:
        pass
    return FactorResult(
        id=factor["id"],
        category=factor["category"],
        name=factor["name"],
        status=STATUS_FAIL,
        severity=factor["severity"],
        evidence="Сайт не на HTTPS или нет редиректа с HTTP",
        url_checked=target_url,
        description=factor["description"],
    )


def check_manual(factor: dict) -> FactorResult:
    return FactorResult(
        id=factor["id"],
        category=factor["category"],
        name=factor["name"],
        status=STATUS_MANUAL,
        severity=factor["severity"],
        evidence="Требуется ручная проверка",
        url_checked=None,
        description=factor["description"],
    )


def check_metrika_counter(
    factor: dict,
    counter_id: str | None,
    metrika_token: str | None,
) -> FactorResult:
    """Проверяет что счётчик Метрики установлен и активен через API."""
    if not metrika_token:
        return FactorResult(
            id=factor["id"],
            category=factor["category"],
            name=factor["name"],
            status=STATUS_MANUAL,
            severity=factor["severity"],
            evidence="Нет yandex.metrika.token в tokens.json — автопроверка невозможна",
            description=factor["description"],
        )
    if not counter_id:
        return FactorResult(
            id=factor["id"],
            category=factor["category"],
            name=factor["name"],
            status=STATUS_WARN,
            severity=factor["severity"],
            evidence="Счётчик Метрики не найден в tokens.json для данного домена",
            description=factor["description"],
        )

    info = metrika_check_counter_active(counter_id, metrika_token)
    if info["error"]:
        return FactorResult(
            id=factor["id"],
            category=factor["category"],
            name=factor["name"],
            status=STATUS_WARN,
            severity=factor["severity"],
            evidence=f"Ошибка API Метрики: {info['error']}",
            description=factor["description"],
        )

    if info["active"]:
        code_note = ""
        if info.get("code_status") == 2:
            code_note = " (ВНИМАНИЕ: код счётчика не обнаружен на сайте)"
        return FactorResult(
            id=factor["id"],
            category=factor["category"],
            name=factor["name"],
            status=STATUS_PASS if info.get("code_status") != 2 else STATUS_WARN,
            severity=factor["severity"],
            evidence=f"Счётчик #{counter_id} активен, сайт: {info['site']}{code_note}",
            description=factor["description"],
        )

    return FactorResult(
        id=factor["id"],
        category=factor["category"],
        name=factor["name"],
        status=STATUS_FAIL,
        severity=factor["severity"],
        evidence=f"Счётчик #{counter_id} неактивен или удалён",
        description=factor["description"],
    )


def check_metrika_goals(
    factor: dict,
    counter_id: str | None,
    metrika_token: str | None,
) -> FactorResult:
    """Проверяет наличие целей конверсии в Метрике."""
    if not metrika_token:
        return FactorResult(
            id=factor["id"],
            category=factor["category"],
            name=factor["name"],
            status=STATUS_MANUAL,
            severity=factor["severity"],
            evidence="Нет yandex.metrika.token в tokens.json — автопроверка невозможна",
            description=factor["description"],
        )
    if not counter_id:
        return FactorResult(
            id=factor["id"],
            category=factor["category"],
            name=factor["name"],
            status=STATUS_WARN,
            severity=factor["severity"],
            evidence="Счётчик Метрики не найден в tokens.json для данного домена",
            description=factor["description"],
        )

    info = metrika_check_goals(counter_id, metrika_token)
    if info["error"]:
        return FactorResult(
            id=factor["id"],
            category=factor["category"],
            name=factor["name"],
            status=STATUS_WARN,
            severity=factor["severity"],
            evidence=f"Ошибка API Метрики: {info['error']}",
            description=factor["description"],
        )

    if info["goals_count"] == 0:
        return FactorResult(
            id=factor["id"],
            category=factor["category"],
            name=factor["name"],
            status=STATUS_FAIL,
            severity=factor["severity"],
            evidence="Цели конверсии не настроены в Метрике",
            description=factor["description"],
        )

    ecom_note = "e-commerce цель обнаружена" if info["has_ecommerce"] else "e-commerce цель НЕ найдена"
    names_preview = ", ".join(info["goal_names"][:5])
    return FactorResult(
        id=factor["id"],
        category=factor["category"],
        name=factor["name"],
        status=STATUS_PASS,
        severity=factor["severity"],
        evidence=f"{info['goals_count']} целей ({ecom_note}): {names_preview}",
        description=factor["description"],
    )


# ============================================================
# Основной pipeline
# ============================================================
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
    # Убираем хвостовой слеш для унификации base
    return url.rstrip("/")


def run_audit(
    target_url: str,
    timeout: int = DEFAULT_TIMEOUT,
    verify_ssl: bool = True,
) -> AuditResult:
    """
    Запуск аудита. Возвращает AuditResult (можно вызывать программно).

    Автоматически загружает tokens.json и определяет counter_id Метрики
    по домену. Не требует CLI-аргументов для токенов.
    """
    target_url = normalize_url(target_url)
    session = make_session(verify_ssl=verify_ssl)

    from datetime import datetime, timezone

    result = AuditResult(
        target_url=target_url,
        audited_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )

    # 0. Автозагрузка токенов — zero CLI arguments
    tokens = load_tokens()
    metrika_token = get_metrika_token(tokens)
    domain = urlparse(target_url).netloc
    counter_id = auto_detect_counter_id(tokens, domain)

    if tokens:
        result.meta["tokens_loaded"] = True
        available_keys = []
        if metrika_token:
            available_keys.append("yandex.metrika.token")
        if counter_id:
            available_keys.append(f"counter_id={counter_id}")
        if tokens.get("topvisor", {}).get("api_key"):
            available_keys.append("topvisor.api_key")
        result.meta["tokens_available"] = available_keys
        print(f"[TOKENS] Загружены: {', '.join(available_keys) or 'нет подходящих'}", file=sys.stderr)
    else:
        result.meta["tokens_loaded"] = False
        print("[TOKENS] tokens.json не найден — API-проверки будут пропущены", file=sys.stderr)

    # 1. Главная страница — обязательна
    print(f"[1/3] Загружаем главную: {target_url}", file=sys.stderr)
    home = fetch(session, target_url, timeout)
    if not home.ok:
        result.meta["error"] = f"Главная недоступна: {home.error or f'status {home.status_code}'}"
        print(f"[ERROR] {result.meta['error']}", file=sys.stderr)
        return result
    pages: dict[str, PageData] = {"home": home}
    result.pages_crawled["home"] = home.url

    # 2. Обнаруживаем остальные логические страницы
    print("[2/3] Ищем /contacts, /about, /delivery, /catalog, /product, /blog", file=sys.stderr)
    for logical in ["contacts", "about", "delivery", "catalog", "blog", "product"]:
        real_url, page = discover_page(session, target_url, logical, home, timeout)
        if real_url and page:
            pages[logical] = page
            result.pages_crawled[logical] = real_url
            print(f"      + {logical}: {real_url}", file=sys.stderr)
        else:
            print(f"      - {logical}: не найдено", file=sys.stderr)

    # 3. Прогоняем все факторы
    factors = load_factors()
    result.meta["factors_total"] = len(factors)
    print(f"[3/3] Проверяем {len(factors)} факторов...", file=sys.stderr)

    for factor in factors:
        check_type = factor.get("check_type", "manual")
        try:
            if check_type == "text_contains":
                fr = check_text_contains(factor, pages)
            elif check_type == "url_exists":
                fr = check_url_exists(factor, pages, target_url, session)
            elif check_type == "element_exists":
                fr = check_element_exists(factor, pages)
            elif check_type == "structured_data":
                fr = check_structured_data(factor, pages)
            elif check_type == "http_status":
                fr = check_http_status(factor, target_url, session)
            elif check_type == "metrika_counter":
                fr = check_metrika_counter(factor, counter_id, metrika_token)
            elif check_type == "metrika_goals":
                fr = check_metrika_goals(factor, counter_id, metrika_token)
            else:  # manual или неизвестный
                fr = check_manual(factor)
        except Exception as exc:
            fr = FactorResult(
                id=factor["id"],
                category=factor["category"],
                name=factor["name"],
                status=STATUS_NA,
                severity=factor["severity"],
                evidence=f"Ошибка проверки: {type(exc).__name__}: {exc}",
                description=factor["description"],
            )
        result.factors.append(fr)

    # 4. Сводка
    result.meta["summary"] = summarize(result.factors)
    return result


def summarize(factors: list[FactorResult]) -> dict[str, Any]:
    counts = {STATUS_PASS: 0, STATUS_WARN: 0, STATUS_FAIL: 0, STATUS_MANUAL: 0, STATUS_NA: 0}
    by_category: dict[str, dict[str, int]] = {}
    critical_fails: list[dict[str, str]] = []
    for f in factors:
        counts[f.status] = counts.get(f.status, 0) + 1
        cat = by_category.setdefault(f.category, {STATUS_PASS: 0, STATUS_WARN: 0, STATUS_FAIL: 0, STATUS_MANUAL: 0, STATUS_NA: 0})
        cat[f.status] = cat.get(f.status, 0) + 1
        if f.status == STATUS_FAIL and f.severity in ("critical", "high"):
            critical_fails.append({
                "id": str(f.id),
                "name": f.name,
                "severity": f.severity,
                "category": f.category,
            })
    # Сортируем критичные — сначала critical, потом high
    sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    critical_fails.sort(key=lambda x: sev_order.get(x["severity"], 9))
    return {
        "counts": counts,
        "by_category": by_category,
        "critical_fails_top": critical_fails[:5],
        "score": round(counts[STATUS_PASS] / max(len(factors), 1) * 100, 1),
    }


# ============================================================
# CLI
# ============================================================
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Commercial Factors Audit — аудит по 118 коммерческим факторам Яндекса"
    )
    parser.add_argument("url", help="URL сайта (например https://example.com)")
    parser.add_argument("--output", "-o", default="audit.json", help="Путь к выходному JSON")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Таймаут запроса (сек)")
    parser.add_argument("--no-verify-ssl", action="store_true", help="Не проверять SSL-сертификаты")
    args = parser.parse_args()

    try:
        result = run_audit(
            target_url=args.url,
            timeout=args.timeout,
            verify_ssl=not args.no_verify_ssl,
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
        f"     PASS: {counts.get('pass', 0)} / {result.meta.get('factors_total', 0)} "
        f"({summary.get('score', 0)}%)\n"
        f"     FAIL: {counts.get('fail', 0)}, WARN: {counts.get('warn', 0)}, "
        f"MANUAL: {counts.get('manual', 0)}, NA: {counts.get('na', 0)}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
