#!/usr/bin/env python3
"""
Providers — обёртки над внешними API ссылочных данных.

Поддержка (по приоритету):
    1. Checktrust       — checktrust.ru/api, XT/XS доноров, доступно через API key
    2. Serpstat         — api.serpstat.com/v4, backlinks, конкуренты
    3. Ahrefs           — api.ahrefs.com/v3, backlinks + lost links + anchors
    4. Majestic         — api.majestic.com, trust flow / citation flow
    5. Yandex Webmaster — api.webmaster.yandex.net/v4, только свои ссылки
    6. Topvisor         — api.topvisor.com, позиции + backlinks (ограниченно)

Автоматическое обнаружение токенов из ~/artvision-data/tokens.json.
Структура tokens.json вложенная — провайдер сам знает путь к своему ключу.

Все провайдеры возвращают нормализованный dict или None если API недоступен.

Важно: НЕ делает fake endpoint. Если токена нет — возвращает None, вызывающий код
создаёт фактор со статусом `manual` и рекомендацией "добавить токен в tokens.json".
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import requests

TOKENS_CANDIDATES = [
    Path("/Users/antonk/artvision-data/tokens.json"),
    Path.home() / "artvision-data" / "tokens.json",
]


def _load_tokens() -> dict[str, Any]:
    """Загружает tokens.json из первого найденного пути."""
    for path in TOKENS_CANDIDATES:
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                print(f"[tokens] Loaded from {path}", file=sys.stderr)
                return data
            except (json.JSONDecodeError, OSError) as exc:
                print(f"[tokens] Failed to read {path}: {exc}", file=sys.stderr)
                continue
    print("[tokens] tokens.json not found in any candidate path", file=sys.stderr)
    return {}


def _deep_get(d: dict, *keys: str, default: Any = None) -> Any:
    """Безопасный доступ к вложенным ключам: _deep_get(d, 'yandex', 'webmaster', 'token')."""
    current = d
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
        if current is None:
            return default
    return current


TOKENS = _load_tokens()


# ============================================================
# Автоопределение токенов по вложенной структуре tokens.json
# ============================================================
def _discover_token(provider: str) -> str | None:
    """Находит API-токен для провайдера в tokens.json.

    Маршруты поиска (в порядке приоритета):
        checktrust  → tokens["checktrust"] (строка или dict.api_key)
        serpstat     → tokens["serpstat"] (строка или dict.api_key)
        ahrefs       → tokens["ahrefs"] (строка или dict.api_key)
        majestic     → tokens["majestic"] (строка или dict.api_key)
        topvisor     → tokens["topvisor"]["api_key"]
        yandex_webmaster → tokens["yandex"]["webmaster"]["token"]
        semrush      → tokens["semrush"]["api_key"]
        dataforseo   → tokens["dataforseo"]["api_login"]  (empty = unavailable)
    """
    # Прямое поле верхнего уровня (checktrust, serpstat, ahrefs, majestic)
    if provider in ("checktrust", "serpstat", "ahrefs", "majestic"):
        val = TOKENS.get(provider)
        if isinstance(val, str) and val:
            return val
        if isinstance(val, dict):
            return val.get("api_key") or val.get("token") or None
        return None

    if provider == "topvisor":
        return _deep_get(TOKENS, "topvisor", "api_key") or None

    if provider == "yandex_webmaster":
        token = _deep_get(TOKENS, "yandex", "webmaster", "token")
        return token if (isinstance(token, str) and token) else None

    if provider == "semrush":
        key = _deep_get(TOKENS, "semrush", "api_key")
        return key if (isinstance(key, str) and key) else None

    if provider == "dataforseo":
        login = _deep_get(TOKENS, "dataforseo", "api_login")
        return login if (isinstance(login, str) and login) else None

    return None


def available_providers() -> dict[str, bool]:
    """Возвращает карту {provider: True/False} по наличию токенов."""
    providers = [
        "checktrust", "serpstat", "ahrefs", "majestic",
        "topvisor", "yandex_webmaster", "semrush", "dataforseo",
    ]
    result = {p: bool(_discover_token(p)) for p in providers}
    found = [p for p, v in result.items() if v]
    missing = [p for p, v in result.items() if not v]
    print(f"[tokens] Available: {found or 'none'}", file=sys.stderr)
    print(f"[tokens] Missing: {missing or 'none'}", file=sys.stderr)
    return result


# ============================================================
# Checktrust
# ============================================================
class CheckTrustProvider:
    """
    checktrust.ru — реальный endpoint:
        https://checktrust.ru/api.html
    Типовой вызов: GET https://checktrust.ru/bulk/items.json?token=<KEY>&items=<domain>&params=xt,xs
    """

    BASE_URL = "https://checktrust.ru/bulk"

    def __init__(self, token: str | None = None):
        self.token = token or _discover_token("checktrust")

    @property
    def available(self) -> bool:
        return bool(self.token)

    def domain_metrics(self, domain: str) -> dict[str, Any] | None:
        """XT (trust 0-100), XS (spam 0-100), DR-похожие метрики."""
        if not self.available:
            return None
        try:
            resp = requests.get(
                f"{self.BASE_URL}/items.json",
                params={
                    "token": self.token,
                    "items": domain,
                    "params": "xt,xs,domain_ibl",
                },
                timeout=15,
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            return data
        except (requests.RequestException, json.JSONDecodeError):
            return None


# ============================================================
# Serpstat
# ============================================================
class SerpstatProvider:
    """
    api.serpstat.com/v4 — JSON-RPC.
    Методы: SerpstatBacklinksProcedure.getSummaryV2, getAnchors, getNewLostBacklinks.
    """

    BASE_URL = "https://api.serpstat.com/v4"

    def __init__(self, token: str | None = None):
        self.token = token or _discover_token("serpstat")

    @property
    def available(self) -> bool:
        return bool(self.token)

    def _rpc(self, method: str, params: dict[str, Any]) -> dict[str, Any] | None:
        if not self.available:
            return None
        try:
            resp = requests.post(
                self.BASE_URL,
                params={"token": self.token},
                json={"id": 1, "method": method, "params": params},
                timeout=30,
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            return data.get("result")
        except (requests.RequestException, json.JSONDecodeError):
            return None

    def backlinks_summary(self, domain: str) -> dict[str, Any] | None:
        return self._rpc(
            "SerpstatBacklinksProcedure.getSummaryV2",
            {"query": domain, "searchType": "domain"},
        )

    def anchors(self, domain: str, limit: int = 100) -> dict[str, Any] | None:
        return self._rpc(
            "SerpstatBacklinksProcedure.getAnchors",
            {"query": domain, "searchType": "domain", "size": limit},
        )

    def new_lost(self, domain: str) -> dict[str, Any] | None:
        return self._rpc(
            "SerpstatBacklinksProcedure.getNewLostSummary",
            {"query": domain, "searchType": "domain"},
        )


# ============================================================
# Ahrefs (premium, often absent)
# ============================================================
class AhrefsProvider:
    """
    ahrefs.com/api — v3, Bearer token.
    Endpoint: https://api.ahrefs.com/v3/site-explorer/...
    """

    BASE_URL = "https://api.ahrefs.com/v3"

    def __init__(self, token: str | None = None):
        self.token = token or _discover_token("ahrefs")

    @property
    def available(self) -> bool:
        return bool(self.token)

    def _get(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any] | None:
        if not self.available:
            return None
        try:
            resp = requests.get(
                f"{self.BASE_URL}/{endpoint}",
                headers={"Authorization": f"Bearer {self.token}"},
                params=params,
                timeout=30,
            )
            if resp.status_code != 200:
                return None
            return resp.json()
        except (requests.RequestException, json.JSONDecodeError):
            return None

    def overview(self, target: str) -> dict[str, Any] | None:
        return self._get(
            "site-explorer/overview",
            {"target": target, "mode": "domain"},
        )

    def lost_backlinks(self, target: str, days: int = 30) -> dict[str, Any] | None:
        return self._get(
            "site-explorer/broken-backlinks",
            {"target": target, "mode": "domain", "history": days},
        )


# ============================================================
# Majestic
# ============================================================
class MajesticProvider:
    """
    api.majestic.com/api/json
    Типовой вызов: GetIndexItemInfo, GetBackLinkData.
    """

    BASE_URL = "https://api.majestic.com/api/json"

    def __init__(self, token: str | None = None):
        self.token = token or _discover_token("majestic")

    @property
    def available(self) -> bool:
        return bool(self.token)

    def index_item_info(self, domain: str) -> dict[str, Any] | None:
        if not self.available:
            return None
        try:
            resp = requests.get(
                self.BASE_URL,
                params={
                    "app_api_key": self.token,
                    "cmd": "GetIndexItemInfo",
                    "items": "1",
                    "item0": domain,
                    "datasource": "fresh",
                },
                timeout=15,
            )
            if resp.status_code != 200:
                return None
            return resp.json()
        except (requests.RequestException, json.JSONDecodeError):
            return None


# ============================================================
# Topvisor
# ============================================================
class TopvisorProvider:
    """
    api.topvisor.com — REST API.

    Topvisor primarily tracks keyword positions, but also provides:
    - Project summary with external link counts
    - Competitor comparison data

    Not a full backlink index (like Ahrefs/Serpstat), but useful as
    supplementary data source for position-based competitor analysis.

    Docs: https://topvisor.com/api/v2/
    """

    BASE_URL = "https://api.topvisor.com/v2/json"

    def __init__(self, api_key: str | None = None, user_id: str | None = None):
        self.api_key = api_key or _discover_token("topvisor")
        self.user_id = user_id or str(_deep_get(TOKENS, "topvisor", "user_id") or "")

    @property
    def available(self) -> bool:
        return bool(self.api_key and self.user_id)

    def _post(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        if not self.available:
            return None
        try:
            resp = requests.post(
                f"{self.BASE_URL}/{endpoint}",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"bearer {self.api_key}",
                    "User-Id": self.user_id,
                },
                json=payload,
                timeout=30,
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            if data.get("errors"):
                return None
            return data.get("result")
        except (requests.RequestException, json.JSONDecodeError):
            return None

    def get_projects(self) -> list[dict[str, Any]] | None:
        """Список проектов пользователя — можно найти project_id по домену."""
        result = self._post("user/projects/get", {
            "show_site_stat": True,
            "show_searcher_and_region": True,
        })
        return result if isinstance(result, list) else None

    def find_project_by_domain(self, domain: str) -> dict[str, Any] | None:
        """Находит проект в Topvisor по домену сайта."""
        projects = self.get_projects()
        if not projects:
            return None
        domain_lower = domain.lower().rstrip("/")
        for proj in projects:
            site = (proj.get("site") or "").lower().rstrip("/")
            if site == domain_lower or site == f"https://{domain_lower}" or site == f"http://{domain_lower}":
                return proj
        return None

    def get_positions_summary(self, project_id: int) -> dict[str, Any] | None:
        """Сводка по позициям проекта — полезна для competitor_gap."""
        return self._post("get/positions_2/summary", {
            "project_id": project_id,
        })


# ============================================================
# Yandex Webmaster (свои ссылки + external samples)
# ============================================================
class YandexWebmasterProvider:
    """
    api.webmaster.yandex.net/v4 — OAuth token.

    Endpoints:
        /user/{user-id}/hosts                                        — список хостов
        /user/{user-id}/hosts/{host-id}/links/external/summary       — сводка внешних ссылок
        /user/{user-id}/hosts/{host-id}/links/external/samples       — сэмплы внешних ссылок
        /user/{user-id}/hosts/{host-id}/links/external/history       — история внешних ссылок

    Ограничения:
        - Показывает только ссылки на СВОИ хосты (подтверждённые в Webmaster)
        - Не видит конкурентов
        - Но даёт реальные данные Яндекса о входящих ссылках
    """

    BASE_URL = "https://api.webmaster.yandex.net/v4"

    def __init__(self, token: str | None = None, user_id: str | None = None):
        self.token = token or _discover_token("yandex_webmaster")
        self.user_id = user_id or str(_deep_get(TOKENS, "yandex", "webmaster", "user_id") or "")

    @property
    def available(self) -> bool:
        return bool(self.token and self.user_id)

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
        if not self.available:
            return None
        try:
            resp = requests.get(
                f"{self.BASE_URL}{path}",
                headers={"Authorization": f"OAuth {self.token}"},
                params=params or {},
                timeout=15,
            )
            if resp.status_code != 200:
                print(
                    f"[yandex_webmaster] {path} returned {resp.status_code}: {resp.text[:200]}",
                    file=sys.stderr,
                )
                return None
            return resp.json()
        except (requests.RequestException, json.JSONDecodeError) as exc:
            print(f"[yandex_webmaster] {path} error: {exc}", file=sys.stderr)
            return None

    def get_hosts(self) -> list[dict[str, Any]] | None:
        """Список подтверждённых хостов."""
        data = self._get(f"/user/{self.user_id}/hosts")
        if data and "hosts" in data:
            return data["hosts"]
        return None

    def find_host_id(self, domain: str) -> str | None:
        """Находит host_id по домену среди подтверждённых хостов."""
        hosts = self.get_hosts()
        if not hosts:
            return None
        domain_lower = domain.lower().rstrip("/")
        for host in hosts:
            host_url = (host.get("ascii_host_url") or "").lower().rstrip("/")
            unicode_url = (host.get("unicode_host_url") or "").lower().rstrip("/")
            # host_url формат: "https://example.com:443" или "http://example.com:80"
            if domain_lower in host_url or domain_lower in unicode_url:
                return host.get("host_id")
        return None

    def links_summary(self, host_id: str, user_id: str | None = None) -> dict[str, Any] | None:
        """Сводка по внешним ссылкам на хост."""
        uid = user_id or self.user_id
        return self._get(f"/user/{uid}/hosts/{host_id}/links/external/summary")

    def links_external_samples(
        self,
        host_id: str,
        offset: int = 0,
        limit: int = 100,
    ) -> dict[str, Any] | None:
        """
        Сэмплы внешних ссылок на хост.

        Возвращает:
        {
            "links": [
                {
                    "source_url": "https://donor.com/page",
                    "destination_url": "https://our.com/page",
                    "discovery_date": "2025-01-15T00:00:00.000+0000",
                    "source_last_access_date": "2025-03-10T...",
                }
            ],
            "count": 1234
        }
        """
        return self._get(
            f"/user/{self.user_id}/hosts/{host_id}/links/external/samples",
            params={"offset": offset, "limit": limit},
        )

    def links_external_history(self, host_id: str) -> dict[str, Any] | None:
        """
        История количества внешних ссылок по месяцам.

        Возвращает:
        {
            "indicators": {
                "LINKS_TOTAL_COUNT": [{"date": "2025-01-01", "value": 100}, ...],
                "LINKS_TOTAL_HOSTS_COUNT": [{"date": "2025-01-01", "value": 50}, ...]
            }
        }
        """
        return self._get(
            f"/user/{self.user_id}/hosts/{host_id}/links/external/history",
        )

    def get_external_links_full(self, domain: str) -> dict[str, Any] | None:
        """
        Высокоуровневый метод: домен → host_id → summary + samples + history.

        Возвращает нормализованный dict:
        {
            "host_id": "...",
            "total_links": N,
            "total_hosts": N,
            "samples": [...],
            "samples_count": N,
            "history": {...},
        }
        или None если хост не найден / не подтверждён.
        """
        host_id = self.find_host_id(domain)
        if not host_id:
            print(
                f"[yandex_webmaster] Host not found for domain '{domain}'. "
                f"Domain must be verified in Yandex.Webmaster.",
                file=sys.stderr,
            )
            return None

        result: dict[str, Any] = {"host_id": host_id}

        # Summary
        summary = self.links_summary(host_id)
        if summary:
            result["total_links"] = summary.get("total_links_count", 0)
            result["total_hosts"] = summary.get("total_hosts_count", 0)
        else:
            result["total_links"] = 0
            result["total_hosts"] = 0

        # Samples (first 100)
        samples_data = self.links_external_samples(host_id, offset=0, limit=100)
        if samples_data:
            result["samples"] = samples_data.get("links", [])
            result["samples_count"] = samples_data.get("count", 0)
        else:
            result["samples"] = []
            result["samples_count"] = 0

        # History
        history = self.links_external_history(host_id)
        if history:
            result["history"] = history.get("indicators", {})
        else:
            result["history"] = {}

        return result


# ============================================================
# Factory
# ============================================================
def build_providers() -> dict[str, Any]:
    """Создаёт все провайдеры, возвращает dict с instance. Недоступные — .available=False."""
    providers = {
        "checktrust": CheckTrustProvider(),
        "serpstat": SerpstatProvider(),
        "ahrefs": AhrefsProvider(),
        "majestic": MajesticProvider(),
        "yandex_webmaster": YandexWebmasterProvider(),
        "topvisor": TopvisorProvider(),
    }

    # Отчёт о доступности
    for name, prov in providers.items():
        status = "AVAILABLE" if prov.available else "not configured"
        print(f"[providers] {name}: {status}", file=sys.stderr)

    return providers
