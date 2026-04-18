#!/usr/bin/env python3
"""
Behavioral Factors Audit — MVP

Анализ поведенческих факторов клиента через Яндекс.Метрика, Вебмастер и
Google PageSpeed Insights API. Выход: JSON с результатами по каждому фактору.

CLI:
    python3 audit.py https://example.com --output=audit.json
    python3 audit.py https://example.com --counter-id=12345678 --output=audit.json
    python3 audit.py https://example.com --counter-id=12345678 --days=30 --output=audit.json

Что проверяем (32 фактора):
  - engagement: время, глубина, отказы, возвраты
  - serp: CTR, позиции (Вебмастер)
  - interaction: клики, формы, скролл (Метрика)
  - segmentation: mobile/desktop, источники, гео
  - conversions: цели, воронка
  - technical: Core Web Vitals (PageSpeed), 404, ошибки

Exit codes:
    0 — успех
    1 — невалидный URL / критическая ошибка
    2 — ошибка чтения factors.yaml
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests
import yaml

# ============================================================
# Константы
# ============================================================
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
FACTORS_YAML = SKILL_ROOT / "data" / "factors.yaml"

TOKENS_PATH = Path(os.path.expanduser("~/artvision-data/tokens.json"))

USER_AGENT = "ArtvisionPulse-Behavioral/0.1 (+https://artvision.pro)"
DEFAULT_TIMEOUT = 15
DEFAULT_DAYS = 30

METRIKA_API_BASE = "https://api-metrika.yandex.net/stat/v1/data"
WEBMASTER_API_BASE = "https://api.webmaster.yandex.net/v4"
PAGESPEED_API_BASE = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

STATUS_PASS = "pass"
STATUS_WARN = "warn"
STATUS_FAIL = "fail"
STATUS_MANUAL = "manual"
STATUS_NA = "na"  # нет данных / нет доступа


# ============================================================
# Модели
# ============================================================
@dataclass
class FactorResult:
    id: int
    category: str
    name: str
    status: str
    severity: str
    evidence: str
    value: Any = None
    recommendation: str = ""
    description: str = ""


@dataclass
class AuditResult:
    target_url: str
    audited_at: str
    counter_id: str | None = None
    period_days: int = DEFAULT_DAYS
    factors: list[FactorResult] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)
    raw_data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_url": self.target_url,
            "audited_at": self.audited_at,
            "counter_id": self.counter_id,
            "period_days": self.period_days,
            "factors": [asdict(f) for f in self.factors],
            "meta": self.meta,
            "raw_data": self.raw_data,
        }


# ============================================================
# Токены
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


def get_metrika_token(tokens: dict) -> str | None:
    return tokens.get("yandex", {}).get("metrika", {}).get("token")


def auto_detect_counter_id(tokens: dict, domain: str) -> str | None:
    """Автоопределение counter_id из tokens.json по домену."""
    metrika = tokens.get("yandex", {}).get("metrika", {})
    domain_clean = domain.replace("https://", "").replace("http://", "").rstrip("/").lower()
    slug = domain_clean.replace(".", "").replace("-", "")
    for key, val in metrika.items():
        if key.startswith("_") or key in ("token", "client_id", "client_secret", "account"):
            continue
        if not isinstance(val, (str, int)):
            continue
        key_clean = key.lower().replace("_counter", "").replace("_", "")
        if key_clean in slug or slug in key_clean:
            return str(val)
    return None


def get_webmaster_token(tokens: dict) -> str | None:
    return tokens.get("yandex", {}).get("webmaster", {}).get("token")


def get_webmaster_user_id(tokens: dict) -> str | None:
    return tokens.get("yandex", {}).get("webmaster", {}).get("user_id")


def get_pagespeed_key(tokens: dict) -> str | None:
    # Попробуем несколько вариантов ключей
    return (
        tokens.get("google_pagespeed", {}).get("api_key")
        or tokens.get("google", {}).get("pagespeed_api_key")
        or None
    )


# ============================================================
# Яндекс.Метрика API
# ============================================================
def metrika_request(
    counter_id: str,
    token: str,
    metrics: str,
    dimensions: str = "",
    date_from: str | None = None,
    date_to: str | None = None,
    filters: str | None = None,
    limit: int = 100,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict | None:
    headers = {
        "Authorization": f"OAuth {token}",
        "User-Agent": USER_AGENT,
    }
    params = {
        "ids": counter_id,
        "metrics": metrics,
        "limit": limit,
    }
    if dimensions:
        params["dimensions"] = dimensions
    if date_from:
        params["date1"] = date_from
    if date_to:
        params["date2"] = date_to
    if filters:
        params["filters"] = filters

    try:
        resp = requests.get(METRIKA_API_BASE, headers=headers, params=params, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
        print(
            f"[METRIKA] {resp.status_code} для metrics={metrics}: {resp.text[:200]}",
            file=sys.stderr,
        )
        return None
    except requests.RequestException as exc:
        print(f"[METRIKA] Сетевая ошибка: {exc}", file=sys.stderr)
        return None


def metrika_fetch_core(
    counter_id: str, token: str, date_from: str, date_to: str
) -> dict[str, Any]:
    """Одним махом забираем основные агрегаты для engagement-блока."""
    result: dict[str, Any] = {}

    # 1. Основные агрегаты
    data = metrika_request(
        counter_id=counter_id,
        token=token,
        metrics="ym:s:visits,ym:s:bounceRate,ym:s:pageDepth,ym:s:avgVisitDurationSeconds,ym:s:percentNewVisitors",
        date_from=date_from,
        date_to=date_to,
    )
    if data and data.get("totals"):
        raw_totals = data["totals"]
        totals = raw_totals[0] if raw_totals and isinstance(raw_totals[0], list) else raw_totals
        if isinstance(totals, list) and len(totals) >= 5:
            result["visits"] = totals[0]
            result["bounceRate"] = totals[1]
            result["pageDepth"] = totals[2]
            result["avgVisitDurationSeconds"] = totals[3]
            result["percentNewVisitors"] = totals[4]

    # 2. Разбивка по device
    data_dev = metrika_request(
        counter_id=counter_id,
        token=token,
        metrics="ym:s:visits,ym:s:bounceRate",
        dimensions="ym:s:deviceCategory",
        date_from=date_from,
        date_to=date_to,
    )
    if data_dev and data_dev.get("data"):
        devices = {}
        for row in data_dev["data"]:
            name = row["dimensions"][0].get("name", "unknown")
            devices[name] = {
                "visits": row["metrics"][0],
                "bounceRate": row["metrics"][1],
            }
        result["by_device"] = devices

    # 3. Источники трафика
    data_src = metrika_request(
        counter_id=counter_id,
        token=token,
        metrics="ym:s:visits,ym:s:bounceRate",
        dimensions="ym:s:trafficSource",
        date_from=date_from,
        date_to=date_to,
    )
    if data_src and data_src.get("data"):
        sources = {}
        total_src_visits = 0
        for row in data_src["data"]:
            name = row["dimensions"][0].get("name", "unknown")
            v = row["metrics"][0]
            total_src_visits += v
            sources[name] = {"visits": v, "bounceRate": row["metrics"][1]}
        result["by_source"] = sources
        result["total_source_visits"] = total_src_visits

    # 4. Поисковые фразы (разнообразие)
    data_phr = metrika_request(
        counter_id=counter_id,
        token=token,
        metrics="ym:s:visits",
        dimensions="ym:s:searchPhrase",
        date_from=date_from,
        date_to=date_to,
        limit=1000,
    )
    if data_phr and data_phr.get("data") is not None:
        # Исключаем строки "не определено" — это пустая фраза
        phrases = [
            row for row in data_phr["data"]
            if row["dimensions"][0].get("name") and "не определено" not in row["dimensions"][0].get("name", "").lower()
        ]
        result["search_phrases_count"] = len(phrases)

    # 5. Цели — список
    goals_url = f"https://api-metrika.yandex.net/management/v1/counter/{counter_id}/goals"
    headers = {"Authorization": f"OAuth {token}", "User-Agent": USER_AGENT}
    try:
        resp = requests.get(goals_url, headers=headers, timeout=DEFAULT_TIMEOUT)
        if resp.status_code == 200:
            goals = resp.json().get("goals", [])
            result["goals_list"] = goals
            result["goals_count"] = len(goals)
        else:
            print(f"[METRIKA] Goals list {resp.status_code}: {resp.text[:200]}", file=sys.stderr)
    except requests.RequestException as exc:
        print(f"[METRIKA] Goals list error: {exc}", file=sys.stderr)

    # 6. 404 страницы (заголовки с '404' или 'Страница не найдена')
    data_404 = metrika_request(
        counter_id=counter_id,
        token=token,
        metrics="ym:pv:pageviews",
        dimensions="ym:pv:title",
        filters="ym:pv:title=@'404'",
        date_from=date_from,
        date_to=date_to,
        limit=10,
    )
    if data_404 and data_404.get("totals"):
        raw_404 = data_404["totals"]
        pv_404 = raw_404[0] if raw_404 and not isinstance(raw_404[0], list) else (raw_404[0][0] if raw_404 else 0)
        data_total_pv = metrika_request(
            counter_id=counter_id,
            token=token,
            metrics="ym:pv:pageviews",
            date_from=date_from,
            date_to=date_to,
        )
        total_pv = 0
        if data_total_pv and data_total_pv.get("totals"):
            raw_t = data_total_pv["totals"]
            total_pv = raw_t[0] if raw_t and not isinstance(raw_t[0], list) else (raw_t[0][0] if raw_t else 0)
        result["pv_404"] = pv_404
        result["pv_total"] = total_pv
        result["share_404"] = (pv_404 / total_pv * 100) if total_pv else 0

    return result


# ============================================================
# Яндекс.Вебмастер API
# ============================================================
def webmaster_get_host_id(user_id: str, token: str, domain: str) -> str | None:
    """Находим host_id по домену."""
    url = f"{WEBMASTER_API_BASE}/user/{user_id}/hosts"
    headers = {"Authorization": f"OAuth {token}", "User-Agent": USER_AGENT}
    try:
        resp = requests.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
        if resp.status_code != 200:
            print(f"[WEBMASTER] hosts {resp.status_code}: {resp.text[:200]}", file=sys.stderr)
            return None
        hosts = resp.json().get("hosts", [])
        domain_clean = domain.replace("https://", "").replace("http://", "").rstrip("/")
        for h in hosts:
            host_url = h.get("unicode_host_url", "") or h.get("ascii_host_url", "")
            if domain_clean in host_url:
                return h.get("host_id")
    except requests.RequestException as exc:
        print(f"[WEBMASTER] host list error: {exc}", file=sys.stderr)
    return None


def webmaster_fetch(user_id: str, token: str, domain: str, days: int = 28) -> dict[str, Any]:  # pyright: ignore[reportUnusedParameter]
    """Собираем агрегированные данные из Вебмастера."""
    result: dict[str, Any] = {}
    host_id = webmaster_get_host_id(user_id, token, domain)
    if not host_id:
        result["_error"] = "Сайт не найден в Вебмастере (или нет прав)"
        return result

    result["host_id"] = host_id
    headers = {"Authorization": f"OAuth {token}", "User-Agent": USER_AGENT}

    # Запросы (TOP, последние N дней)
    url = f"{WEBMASTER_API_BASE}/user/{user_id}/hosts/{host_id}/search-queries/popular"
    params = {
        "order_by": "TOTAL_SHOWS",
        "query_indicator": ["TOTAL_SHOWS", "TOTAL_CLICKS", "AVG_SHOW_POSITION", "AVG_CLICK_POSITION"],
    }
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=DEFAULT_TIMEOUT)
        if resp.status_code == 200:
            queries = resp.json().get("queries", [])
            result["top_queries"] = queries[:50]
            result["queries_count"] = len(queries)

            # Агрегаты
            total_shows = 0
            total_clicks = 0
            positions: list[float] = []
            no_click_count = 0
            for q in queries:
                if not isinstance(q, dict):
                    continue
                raw_indicators = q.get("indicators", [])
                if not isinstance(raw_indicators, list):
                    continue
                indicators: dict[str, Any] = {}
                for i in raw_indicators:
                    if isinstance(i, dict) and "indicator" in i:
                        indicators[i["indicator"]] = i.get("value", 0)
                shows = indicators.get("TOTAL_SHOWS", 0)
                clicks = indicators.get("TOTAL_CLICKS", 0)
                pos = indicators.get("AVG_SHOW_POSITION", 0)
                total_shows += shows
                total_clicks += clicks
                if pos:
                    positions.append(pos)
                if shows > 10 and clicks == 0:
                    no_click_count += 1

            result["total_shows"] = total_shows
            result["total_clicks"] = total_clicks
            result["overall_ctr"] = (total_clicks / total_shows * 100) if total_shows else 0
            result["avg_position"] = sum(positions) / len(positions) if positions else 0
            result["no_click_queries"] = no_click_count
            result["no_click_share"] = (no_click_count / len(queries) * 100) if queries else 0
        else:
            print(f"[WEBMASTER] queries {resp.status_code}: {resp.text[:200]}", file=sys.stderr)
            result["_error"] = f"API Вебмастера вернул {resp.status_code}"
    except requests.RequestException as exc:
        print(f"[WEBMASTER] queries error: {exc}", file=sys.stderr)
        result["_error"] = f"Сетевая ошибка: {exc}"

    return result


# ============================================================
# Google PageSpeed Insights API
# ============================================================
def pagespeed_fetch(url: str, api_key: str | None = None, strategy: str = "mobile") -> dict[str, Any]:
    """Запрос к PageSpeed Insights. Работает и без ключа (низкий rate limit)."""
    params = {
        "url": url,
        "strategy": strategy,
        "category": ["performance", "accessibility"],
    }
    if api_key:
        params["key"] = api_key

    try:
        resp = requests.get(PAGESPEED_API_BASE, params=params, timeout=60)
        if resp.status_code != 200:
            return {"_error": f"PageSpeed API {resp.status_code}: {resp.text[:200]}"}
        data = resp.json()
        lh = data.get("lighthouseResult", {})
        audits = lh.get("audits", {})
        categories = lh.get("categories", {})

        result = {
            "strategy": strategy,
            "performance_score": round(categories.get("performance", {}).get("score", 0) * 100),
        }
        # Ключевые метрики
        for key, audit_id in [
            ("lcp_sec", "largest-contentful-paint"),
            ("cls", "cumulative-layout-shift"),
            ("inp_ms", "interaction-to-next-paint"),
            ("ttfb_ms", "server-response-time"),
            ("fcp_sec", "first-contentful-paint"),
            ("tbt_ms", "total-blocking-time"),
        ]:
            audit = audits.get(audit_id, {})
            value = audit.get("numericValue")
            if value is not None:
                if key.endswith("_sec"):
                    result[key] = round(value / 1000, 2)
                elif key.endswith("_ms"):
                    result[key] = round(value)
                else:
                    result[key] = round(value, 3)
        return result
    except requests.RequestException as exc:
        return {"_error": f"Сетевая ошибка PageSpeed: {exc}"}


# ============================================================
# Проверка факторов
# ============================================================
def _res(factor: dict, status: str, evidence: str, value: Any = None) -> FactorResult:
    return FactorResult(
        id=factor["id"],
        category=factor["category"],
        name=factor["name"],
        status=status,
        severity=factor.get("severity", "medium"),
        evidence=evidence,
        value=value,
        recommendation=factor.get("recommendation", ""),
        description=factor.get("description", ""),
    )


def _na(factor: dict, reason: str) -> FactorResult:
    return _res(factor, STATUS_NA, f"Нет данных: {reason}")


def _manual(factor: dict) -> FactorResult:
    return _res(factor, STATUS_MANUAL, "Требуется ручная проверка в интерфейсе Метрики / Вебмастера")


def _check_min(value: float | None, pass_min: float, warn_min: float) -> str:
    if value is None:
        return STATUS_NA
    if value >= pass_min:
        return STATUS_PASS
    if value >= warn_min:
        return STATUS_WARN
    return STATUS_FAIL


def _check_max(value: float | None, pass_max: float, warn_max: float) -> str:
    if value is None:
        return STATUS_NA
    if value <= pass_max:
        return STATUS_PASS
    if value <= warn_max:
        return STATUS_WARN
    return STATUS_FAIL


def run_factor_engagement(factor: dict, metrika: dict) -> FactorResult:
    fid = factor["id"]
    th = factor.get("thresholds", {})

    if not metrika:
        return _na(factor, "Метрика не подключена (нет counter_id или token)")

    if fid == 1:  # Avg session duration
        v = metrika.get("avgVisitDurationSeconds")
        if v is None:
            return _na(factor, "Метрика не вернула данные")
        status = _check_min(v, th["pass_min"], th["warn_min"])
        return _res(factor, status, f"Среднее время визита: {v:.0f} сек", round(v, 1))

    if fid == 2:  # Pages per session
        v = metrika.get("pageDepth")
        if v is None:
            return _na(factor, "Метрика не вернула данные")
        status = _check_min(v, th["pass_min"], th["warn_min"])
        return _res(factor, status, f"Глубина: {v:.2f} стр/визит", round(v, 2))

    if fid == 3:  # Bounce rate
        v = metrika.get("bounceRate")
        if v is None:
            return _na(factor, "Метрика не вернула данные")
        status = _check_max(v, th["pass_max"], th["warn_max"])
        return _res(factor, status, f"Отказы (15-сек правило): {v:.1f}%", round(v, 1))

    if fid == 4:  # Возвраты в SERP (комбинированно)
        br = metrika.get("bounceRate")
        dur = metrika.get("avgVisitDurationSeconds")
        if br is None or dur is None:
            return _na(factor, "Метрика не вернула данные")
        # Высокий bounce + короткая сессия = плохой dwell time
        if br > 30 and dur < 60:
            status = STATUS_FAIL
        elif br > 20 or dur < 90:
            status = STATUS_WARN
        else:
            status = STATUS_PASS
        return _res(
            factor,
            status,
            f"Отказы {br:.1f}% + время {dur:.0f}с → косвенный сигнал dwell time",
            {"bounce": round(br, 1), "duration": round(dur, 1)},
        )

    if fid == 5:  # Возвратные пользователи
        pct_new = metrika.get("percentNewVisitors")
        if pct_new is None:
            return _na(factor, "Метрика не вернула данные")
        status = _check_max(pct_new, th["pass_max"], th["warn_max"])
        returning = 100 - pct_new
        return _res(
            factor,
            status,
            f"Новых: {pct_new:.1f}%, возвратных: {returning:.1f}%",
            round(returning, 1),
        )

    return _manual(factor)


def run_factor_serp(factor: dict, webmaster: dict) -> FactorResult:
    fid = factor["id"]
    th = factor.get("thresholds", {})

    if not webmaster or webmaster.get("_error"):
        err = (webmaster or {}).get("_error", "Вебмастер не подключен")
        return _na(factor, err)

    if fid == 6:  # CTR
        v = webmaster.get("overall_ctr")
        if v is None:
            return _na(factor, "Нет данных Вебмастера")
        status = _check_min(v, th["pass_min"], th["warn_min"])
        return _res(
            factor,
            status,
            f"Средний CTR: {v:.2f}% (клики: {webmaster.get('total_clicks', 0)} / показы: {webmaster.get('total_shows', 0)})",
            round(v, 2),
        )

    if fid == 7:  # Позиции
        v = webmaster.get("avg_position")
        if not v:
            return _na(factor, "Нет данных о позициях")
        status = _check_max(v, th["pass_max"], th["warn_max"])
        return _res(
            factor,
            status,
            f"Средняя позиция по TOP-запросам: {v:.1f}",
            round(v, 1),
        )

    if fid == 8:  # Запросы без кликов
        v = webmaster.get("no_click_share")
        if v is None:
            return _na(factor, "Нет данных Вебмастера")
        status = _check_max(v, th["pass_max"], th["warn_max"])
        return _res(
            factor,
            status,
            f"Запросов с показами но без кликов: {webmaster.get('no_click_queries', 0)} ({v:.1f}%)",
            round(v, 1),
        )

    return _manual(factor)


def run_factor_metrika_misc(factor: dict, metrika: dict) -> FactorResult:
    fid = factor["id"]
    th = factor.get("thresholds", {})

    if not metrika:
        return _na(factor, "Метрика не подключена")

    if fid == 9:  # Разнообразие поисковых фраз
        v = metrika.get("search_phrases_count")
        if v is None:
            return _na(factor, "Нет данных")
        status = _check_min(v, th["pass_min"], th["warn_min"])
        return _res(factor, status, f"Уникальных поисковых фраз: {v}", v)

    if fid == 22:  # Goals count
        v = metrika.get("goals_count")
        if v is None:
            return _na(factor, "Нет доступа к списку целей (нужен management scope)")
        status = _check_min(v, th["pass_min"], th["warn_min"])
        goal_names = [g.get("name", "") for g in metrika.get("goals_list", [])][:5]
        return _res(
            factor,
            status,
            f"Настроено целей: {v}. Примеры: {', '.join(goal_names) if goal_names else '—'}",
            v,
        )

    if fid == 30:  # 404 share
        v = metrika.get("share_404")
        if v is None:
            return _na(factor, "Нет данных Метрики")
        status = _check_max(v, th["pass_max"], th["warn_max"])
        return _res(
            factor,
            status,
            f"Доля просмотров на 404-страницах: {v:.2f}% ({metrika.get('pv_404', 0)} из {metrika.get('pv_total', 0)})",
            round(v, 2),
        )

    # Сегменты
    if fid == 16:  # Mobile vs Desktop bounce delta
        devices = metrika.get("by_device") or {}
        if not devices:
            return _na(factor, "Нет разбивки по устройствам")
        mobile = devices.get("мобильные телефоны") or devices.get("mobile")
        desktop = devices.get("десктопы") or devices.get("desktop")
        if not mobile or not desktop:
            return _na(factor, "Нет данных по mobile или desktop сегменту")
        delta = abs(mobile["bounceRate"] - desktop["bounceRate"])
        max_delta = th.get("max_delta", 10)
        status = STATUS_PASS if delta <= max_delta else (STATUS_WARN if delta <= max_delta * 2 else STATUS_FAIL)
        return _res(
            factor,
            status,
            f"Mobile bounce: {mobile['bounceRate']:.1f}%, Desktop: {desktop['bounceRate']:.1f}%, Δ={delta:.1f} п.п.",
            {"mobile": mobile["bounceRate"], "desktop": desktop["bounceRate"], "delta": delta},
        )

    if fid == 17:  # Источники — распределение
        sources = metrika.get("by_source") or {}
        total_src = metrika.get("total_source_visits", 0)
        if not sources or not total_src:
            return _na(factor, "Нет данных по источникам")
        shares = {name: (data["visits"] / total_src * 100) for name, data in sources.items()}
        max_share = max(shares.values()) if shares else 0
        # Поиск organic
        organic_share = 0
        for name, share in shares.items():
            if "поис" in name.lower() or "search" in name.lower() or "organic" in name.lower():
                organic_share += share
        max_single = th.get("max_single_share", 70)
        min_organic = th.get("min_organic_share", 30)
        if max_share > max_single or organic_share < min_organic * 0.5:
            status = STATUS_FAIL
        elif organic_share < min_organic:
            status = STATUS_WARN
        else:
            status = STATUS_PASS
        top3 = sorted(shares.items(), key=lambda x: -x[1])[:3]
        return _res(
            factor,
            status,
            f"Органика: {organic_share:.1f}%. Топ-3 источника: "
            + ", ".join(f"{n} ({s:.0f}%)" for n, s in top3),
            shares,
        )

    if fid == 18:  # Отказы по каналам
        sources = metrika.get("by_source") or {}
        if not sources:
            return _na(factor, "Нет данных по источникам")
        high_bounce = [
            (n, d["bounceRate"]) for n, d in sources.items()
            if d["visits"] > 50 and d["bounceRate"] > th.get("warn_max", 40)
        ]
        status = STATUS_FAIL if high_bounce else STATUS_PASS
        evidence = (
            f"Каналов с bounce > {th.get('warn_max', 40)}%: {len(high_bounce)}"
            + (" → " + ", ".join(f"{n} ({b:.0f}%)" for n, b in high_bounce[:3]) if high_bounce else "")
        )
        return _res(factor, status if high_bounce else STATUS_PASS, evidence, high_bounce)

    return _manual(factor)


def run_factor_pagespeed(factor: dict, pagespeed: dict) -> FactorResult:
    fid = factor["id"]
    th = factor.get("thresholds", {})

    if not pagespeed or pagespeed.get("_error"):
        err = (pagespeed or {}).get("_error", "PageSpeed API не отвечает")
        return _na(factor, err)

    if fid == 25:  # LCP
        v = pagespeed.get("lcp_sec")
        if v is None:
            return _na(factor, "Нет LCP в ответе PageSpeed")
        status = _check_max(v, th["pass_max"], th["warn_max"])
        return _res(factor, status, f"LCP: {v:.2f} сек (mobile)", v)

    if fid == 26:  # CLS
        v = pagespeed.get("cls")
        if v is None:
            return _na(factor, "Нет CLS в ответе PageSpeed")
        status = _check_max(v, th["pass_max"], th["warn_max"])
        return _res(factor, status, f"CLS: {v:.3f} (mobile)", v)

    if fid == 27:  # INP
        v = pagespeed.get("inp_ms")
        if v is None:
            # Fallback на TBT
            tbt = pagespeed.get("tbt_ms")
            if tbt is None:
                return _na(factor, "Нет INP и TBT в ответе PageSpeed")
            status = _check_max(tbt, th["pass_max"], th["warn_max"])
            return _res(factor, status, f"TBT (прокси INP): {tbt} мс", tbt)
        status = _check_max(v, th["pass_max"], th["warn_max"])
        return _res(factor, status, f"INP: {v} мс", v)

    if fid == 28:  # TTFB
        v = pagespeed.get("ttfb_ms")
        if v is None:
            return _na(factor, "Нет TTFB в ответе PageSpeed")
        status = _check_max(v, th["pass_max"], th["warn_max"])
        return _res(factor, status, f"TTFB: {v} мс", v)

    if fid == 29:  # Performance score
        v = pagespeed.get("performance_score")
        if v is None:
            return _na(factor, "Нет performance score")
        status = _check_min(v, th["pass_min"], th["warn_min"])
        return _res(factor, status, f"Lighthouse Performance (mobile): {v}/100", v)

    return _manual(factor)


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
    return url.rstrip("/")


def run_audit(
    target_url: str,
    counter_id: str | None = None,
    days: int = DEFAULT_DAYS,
    timeout: int = DEFAULT_TIMEOUT,  # noqa: ARG001
) -> AuditResult:
    target_url = normalize_url(target_url)
    tokens = load_tokens()

    if not counter_id:
        counter_id = auto_detect_counter_id(tokens, target_url)
        if counter_id:
            print(f"[AUTO] counter_id={counter_id} (из tokens.json)", file=sys.stderr)

    result = AuditResult(
        target_url=target_url,
        audited_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        counter_id=counter_id,
        period_days=days,
    )

    # Даты
    date_to = datetime.now().strftime("%Y-%m-%d")
    date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    # 1. Метрика
    metrika_data: dict[str, Any] = {}
    metrika_token = get_metrika_token(tokens)
    if counter_id and metrika_token:
        print(f"[1/3] Метрика: counter_id={counter_id}, период {date_from}..{date_to}", file=sys.stderr)
        metrika_data = metrika_fetch_core(counter_id, metrika_token, date_from, date_to)
        result.raw_data["metrika"] = metrika_data
    else:
        if not counter_id:
            result.meta["metrika_skip"] = "counter_id не передан (--counter-id)"
        elif not metrika_token:
            result.meta["metrika_skip"] = "Нет yandex.metrika.token в tokens.json"
        print(f"[1/3] Метрика: пропуск — {result.meta.get('metrika_skip')}", file=sys.stderr)

    # 2. Вебмастер
    webmaster_data: dict[str, Any] = {}
    wm_token = get_webmaster_token(tokens)
    wm_user = get_webmaster_user_id(tokens)
    if wm_token and wm_user:
        print(f"[2/3] Вебмастер: user_id={wm_user}", file=sys.stderr)
        webmaster_data = webmaster_fetch(wm_user, wm_token, target_url)
        result.raw_data["webmaster"] = webmaster_data
    else:
        result.meta["webmaster_skip"] = "Нет yandex.webmaster.token или user_id в tokens.json"
        print(f"[2/3] Вебмастер: пропуск — {result.meta['webmaster_skip']}", file=sys.stderr)

    # 3. PageSpeed (работает и без ключа)
    pagespeed_data: dict[str, Any] = {}
    ps_key = get_pagespeed_key(tokens)
    print(f"[3/3] PageSpeed: {'с ключом' if ps_key else 'без ключа (низкий rate limit)'}", file=sys.stderr)
    pagespeed_data = pagespeed_fetch(target_url, api_key=ps_key, strategy="mobile")
    result.raw_data["pagespeed"] = pagespeed_data

    # Прогоняем факторы
    factors = load_factors()
    result.meta["factors_total"] = len(factors)
    print(f"Проверяем {len(factors)} поведенческих факторов...", file=sys.stderr)

    for factor in factors:
        fid = factor["id"]
        cat = factor["category"]
        check_type = factor.get("check_type", "manual")

        try:
            if check_type == "manual":
                fr = _manual(factor)
            elif cat == "engagement":
                fr = run_factor_engagement(factor, metrika_data)
            elif cat == "serp":
                fr = run_factor_serp(factor, webmaster_data)
            elif cat == "interaction":
                fr = _manual(factor)  # карты, вебвизор — только ручная
            elif cat == "segmentation":
                fr = run_factor_metrika_misc(factor, metrika_data)
            elif cat == "conversions":
                # fid 22 — goals, 23+24 — manual пока (требует per-goal данных)
                if fid == 22:
                    fr = run_factor_metrika_misc(factor, metrika_data)
                else:
                    fr = _manual(factor)
            elif cat == "technical":
                # pagespeed для 25-29, остальное — metrika или manual
                if fid in (25, 26, 27, 28, 29):
                    fr = run_factor_pagespeed(factor, pagespeed_data)
                elif fid == 30:
                    fr = run_factor_metrika_misc(factor, metrika_data)
                else:
                    fr = _manual(factor)
            else:
                fr = _manual(factor)
        except Exception as exc:  # noqa: BLE001
            fr = _res(factor, STATUS_NA, f"Ошибка проверки: {type(exc).__name__}: {exc}")

        result.factors.append(fr)

    # Сводка
    result.meta["summary"] = summarize(result.factors)
    return result


def summarize(factors: list[FactorResult]) -> dict[str, Any]:
    counts = {STATUS_PASS: 0, STATUS_WARN: 0, STATUS_FAIL: 0, STATUS_MANUAL: 0, STATUS_NA: 0}
    by_category: dict[str, dict[str, int]] = {}
    critical_fails: list[dict[str, str]] = []

    for f in factors:
        counts[f.status] = counts.get(f.status, 0) + 1
        cat = by_category.setdefault(
            f.category,
            {STATUS_PASS: 0, STATUS_WARN: 0, STATUS_FAIL: 0, STATUS_MANUAL: 0, STATUS_NA: 0},
        )
        cat[f.status] = cat.get(f.status, 0) + 1
        if f.status == STATUS_FAIL and f.severity in ("critical", "high"):
            critical_fails.append({
                "id": str(f.id),
                "name": f.name,
                "severity": f.severity,
                "category": f.category,
                "evidence": f.evidence,
            })

    sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    critical_fails.sort(key=lambda x: sev_order.get(x["severity"], 9))

    measurable = counts[STATUS_PASS] + counts[STATUS_WARN] + counts[STATUS_FAIL]
    score = round(counts[STATUS_PASS] / measurable * 100, 1) if measurable else 0

    return {
        "counts": counts,
        "by_category": by_category,
        "critical_fails_top": critical_fails[:7],
        "score": score,
    }


# ============================================================
# CLI
# ============================================================
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Behavioral Factors Audit — поведенческие факторы Яндекса"
    )
    parser.add_argument("url", help="URL сайта (например https://example.com)")
    parser.add_argument(
        "--counter-id", "-c", default=None,
        help="ID счётчика Яндекс.Метрики. Без него Метрика-факторы будут NA",
    )
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS, help="Период анализа (дней), default 30")
    parser.add_argument("--output", "-o", default="audit.json", help="Путь к выходному JSON")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Таймаут API (сек)")
    args = parser.parse_args()

    try:
        result = run_audit(
            target_url=args.url,
            counter_id=args.counter_id,
            days=args.days,
            timeout=args.timeout,
        )
    except Exception as exc:  # noqa: BLE001
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
        f"(score: {summary.get('score', 0)}%)\n"
        f"     FAIL: {counts.get('fail', 0)}, WARN: {counts.get('warn', 0)}, "
        f"MANUAL: {counts.get('manual', 0)}, NA: {counts.get('na', 0)}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
