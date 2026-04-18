#!/usr/bin/env python3
"""
Link Factors Audit — MVP

Аудит ссылочного профиля сайта по 27 факторам.
Выход: JSON с результатами + агрегаты для графиков.

CLI:
    python3 audit.py example.com --output=link.json
    python3 audit.py example.com --output=link.json --competitors=comp1.ru,comp2.ru

Exit codes:
    0 — успех
    1 — невалидный домен
    2 — ошибка чтения factors.yaml
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse
from collections import deque

import requests
import yaml
from bs4 import BeautifulSoup

# Локальные модули
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from providers import build_providers  # type: ignore[import-not-found]  # noqa: E402

SKILL_ROOT = SCRIPT_DIR.parent
FACTORS_YAML = SKILL_ROOT / "data" / "factors.yaml"

USER_AGENT = "ArtvisionLinkForge/0.1 (+https://artvision.pro)"
DEFAULT_TIMEOUT = 15
MAX_CRAWL_PAGES = 100  # для internal crawl — не жадничаем

STATUS_PASS = "pass"
STATUS_WARN = "warn"
STATUS_FAIL = "fail"
STATUS_MANUAL = "manual"
STATUS_NA = "na"


# ============================================================
# Модели
# ============================================================
@dataclass
class FactorResult:
    id: int
    group: str
    name: str
    status: str
    severity: str
    value: Any = None        # итоговое значение (число/словарь)
    evidence: str = ""
    method: str = ""
    description: str = ""
    source: str = ""         # какой API/метод дал данные


@dataclass
class AuditResult:
    target_domain: str
    audited_at: str
    providers_available: dict[str, bool] = field(default_factory=dict)
    competitors: list[str] = field(default_factory=list)
    factors: list[FactorResult] = field(default_factory=list)
    charts: dict[str, Any] = field(default_factory=dict)  # сырые данные для графиков
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_domain": self.target_domain,
            "audited_at": self.audited_at,
            "providers_available": self.providers_available,
            "competitors": self.competitors,
            "factors": [asdict(f) for f in self.factors],
            "charts": self.charts,
            "meta": self.meta,
        }


# ============================================================
# Helpers
# ============================================================
def normalize_domain(raw: str) -> str:
    """example.com, https://example.com/, www.example.com → example.com"""
    raw = raw.strip()
    if raw.startswith(("http://", "https://")):
        raw = urlparse(raw).netloc
    raw = raw.removeprefix("www.").rstrip("/")
    return raw.lower()


def load_factors() -> list[dict]:
    try:
        with open(FACTORS_YAML, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data["factors"]
    except (FileNotFoundError, yaml.YAMLError, KeyError) as exc:
        print(f"[ERROR] factors.yaml: {exc}", file=sys.stderr)
        sys.exit(2)


def make_result(
    factor: dict,
    status: str,
    value: Any = None,
    evidence: str = "",
    source: str = "",
) -> FactorResult:
    return FactorResult(
        id=factor["id"],
        group=factor["group"],
        name=factor["name"],
        status=status,
        severity=factor["severity"],
        value=value,
        evidence=evidence,
        method=factor.get("method", ""),
        description=factor.get("description", ""),
        source=source,
    )


def manual_stub(factor: dict, reason: str) -> FactorResult:
    """Заглушка когда нет API/данных."""
    method = factor.get("method", "")
    api_name = method.removeprefix("api_")
    return make_result(
        factor,
        STATUS_MANUAL,
        value=None,
        evidence=f"Требуется API [{api_name}]. Добавь токен в tokens.json. {reason}",
        source="stub",
    )


# ============================================================
# Оценка по порогам
# ============================================================
def _classify_by_threshold(value: int | float, thresholds: dict[str, Any]) -> str:
    """Универсальный классификатор. Возвращает pass/warn/fail на основе thresholds."""
    if not thresholds:
        return STATUS_PASS

    # "чем меньше — тем хуже"
    if "fail_below" in thresholds and value < thresholds["fail_below"]:
        return STATUS_FAIL
    if "warn_below" in thresholds and value < thresholds["warn_below"]:
        return STATUS_WARN

    # "чем больше — тем хуже"
    if "fail_above_pct" in thresholds and value > thresholds["fail_above_pct"]:
        return STATUS_FAIL
    if "warn_above_pct" in thresholds and value > thresholds["warn_above_pct"]:
        return STATUS_WARN
    if "fail_above" in thresholds and value > thresholds["fail_above"]:
        return STATUS_FAIL
    if "warn_above" in thresholds and value > thresholds["warn_above"]:
        return STATUS_WARN

    return STATUS_PASS


# ============================================================
# Чекеры факторов — ВНЕШНИЙ ПРОФИЛЬ
# ============================================================
def _extract_tld_from_samples(samples: list[dict]) -> dict[str, int]:
    """Извлекает TLD-распределение из сэмплов Yandex.Webmaster."""
    tld_counts: dict[str, int] = {}
    for sample in samples:
        src = sample.get("source_url", "")
        try:
            host = urlparse(src).netloc.lower()
            parts = host.rsplit(".", 1)
            tld = f".{parts[-1]}" if len(parts) >= 2 else ".unknown"
            # xn--p1ai = .рф
            if tld == ".xn--p1ai":
                tld = ".рф"
            tld_counts[tld] = tld_counts.get(tld, 0) + 1
        except (ValueError, IndexError):
            continue
    return dict(sorted(tld_counts.items(), key=lambda x: -x[1]))


def _extract_gov_edu_from_samples(samples: list[dict]) -> list[str]:
    """Находит gov/edu доноров среди сэмплов Webmaster."""
    gov_edu = []
    gov_edu_tlds = {".gov", ".edu", ".gov.ru", ".ac.ru", ".academy", ".mil"}
    for sample in samples:
        src = sample.get("source_url", "")
        try:
            host = urlparse(src).netloc.lower()
            for tld in gov_edu_tlds:
                if host.endswith(tld):
                    gov_edu.append(src)
                    break
        except (ValueError, IndexError):
            continue
    return gov_edu


def check_external_profile(
    factors: list[dict],
    domain: str,
    providers: dict[str, Any],
    audit: AuditResult,
) -> None:
    """Группа 1: 12 факторов внешнего профиля."""

    # 1. Ссылочная масса + 2. Ref domains (Serpstat → Yandex.Webmaster fallback)
    sp = providers.get("serpstat")
    summary = sp.backlinks_summary(domain) if sp and sp.available else None
    source = "serpstat" if summary else ""

    # Yandex.Webmaster fallback — пробуем получить данные по внешним ссылкам
    yw = providers.get("yandex_webmaster")
    yw_data: dict[str, Any] | None = None
    if yw and yw.available:
        print(f"[external] Запрашиваем Yandex.Webmaster external links для {domain}...", file=sys.stderr)
        yw_data = yw.get_external_links_full(domain)
        if yw_data:
            print(
                f"[external] Yandex.Webmaster: {yw_data.get('total_links', 0)} links, "
                f"{yw_data.get('total_hosts', 0)} hosts, "
                f"{yw_data.get('samples_count', 0)} samples",
                file=sys.stderr,
            )
            audit.meta["yandex_webmaster"] = {
                "host_id": yw_data.get("host_id"),
                "total_links": yw_data.get("total_links", 0),
                "total_hosts": yw_data.get("total_hosts", 0),
                "samples_count": yw_data.get("samples_count", 0),
            }
        else:
            print(f"[external] Yandex.Webmaster: host '{domain}' не найден или не подтверждён", file=sys.stderr)

    for factor in factors:
        if factor["id"] == 1:  # Ссылочная масса
            if summary and "data" in summary:
                total = summary["data"].get("backlinks", 0) or 0
                status = _classify_by_threshold(total, factor["thresholds"])
                audit.factors.append(make_result(
                    factor, status, total,
                    f"Всего бэклинков: {total:,}".replace(",", " "),
                    source,
                ))
            elif yw_data:
                total = yw_data.get("total_links", 0)
                status = _classify_by_threshold(total, factor["thresholds"])
                audit.factors.append(make_result(
                    factor, status, total,
                    f"Всего внешних ссылок (Yandex.Webmaster): {total:,}".replace(",", " ")
                    + " (только видимые Яндексу, реальное число может быть больше)",
                    "yandex_webmaster",
                ))
            else:
                audit.factors.append(manual_stub(factor, "Нет данных Serpstat/Checktrust/Webmaster."))

        elif factor["id"] == 2:  # Ref domains
            if summary and "data" in summary:
                rd = summary["data"].get("referring_domains", 0) or 0
                status = _classify_by_threshold(rd, factor["thresholds"])
                audit.factors.append(make_result(
                    factor, status, rd,
                    f"Ref domains: {rd:,}".replace(",", " "),
                    source,
                ))
                audit.charts["ref_domains_total"] = rd
            elif yw_data:
                rd = yw_data.get("total_hosts", 0)
                status = _classify_by_threshold(rd, factor["thresholds"])
                audit.factors.append(make_result(
                    factor, status, rd,
                    f"Ссылающихся хостов (Yandex.Webmaster): {rd:,}".replace(",", " ")
                    + " (hosts, не доменов 2-го уровня)",
                    "yandex_webmaster",
                ))
                audit.charts["ref_domains_total"] = rd
            else:
                audit.factors.append(manual_stub(factor, "Нет данных Serpstat/Webmaster."))

        elif factor["id"] == 3:  # Уникальность (new vs returning)
            nl = sp.new_lost(domain) if sp and sp.available else None
            if nl and "data" in nl:
                new = nl["data"].get("new_domains", 0) or 0
                total = max((nl["data"].get("referring_domains", 1) or 1), 1)
                pct = round(new / total * 100, 1)
                status = _classify_by_threshold(pct, factor["thresholds"])
                audit.factors.append(make_result(
                    factor, status, pct,
                    f"Новых донаров за 6 мес: {pct}% ({new} из {total})",
                    "serpstat",
                ))
            else:
                audit.factors.append(manual_stub(factor, "Нет данных по new/lost."))

        elif factor["id"] == 4:  # DR-распределение
            # Checktrust даёт XT — аппроксимируем как DR
            ct = providers.get("checktrust")
            if ct and ct.available:
                metrics = ct.domain_metrics(domain)
                if metrics:
                    # В реальном ответе структура: {"summary": {...}, "items": {domain: {xt: N, xs: M}}}
                    xt = None
                    try:
                        xt = metrics.get("items", {}).get(domain, {}).get("xt")
                    except (AttributeError, TypeError):
                        pass
                    if xt is not None:
                        # Заглушка гистограммы — в реальности нужен отдельный endpoint
                        histogram = {"0-20": 0, "20-40": 0, "40-60": 0, "60-80": 0, "80+": 0}
                        audit.charts["dr_histogram"] = histogram
                        audit.factors.append(make_result(
                            factor, STATUS_MANUAL, xt,
                            f"Собственный XT={xt}. Для гистограммы донаров нужен отдельный bulk-запрос.",
                            "checktrust",
                        ))
                        continue
            audit.factors.append(manual_stub(factor, "Нет Checktrust bulk-вызова по всем донорам."))

        elif factor["id"] == 5:  # Тематичность
            audit.factors.append(manual_stub(factor, "Тематичность требует ручной категоризации донаров."))

        elif factor["id"] == 6:  # TLD-распределение
            # Serpstat primary, Yandex.Webmaster samples fallback
            if summary and "data" in summary:
                audit.factors.append(manual_stub(factor, "getTLD метод в getBacklinksByTld Serpstat (платный плюс)."))
                audit.charts["tld_breakdown"] = {}
            elif yw_data and yw_data.get("samples"):
                tld_dist = _extract_tld_from_samples(yw_data["samples"])
                total_samples = sum(tld_dist.values())
                ru_count = tld_dist.get(".ru", 0) + tld_dist.get(".рф", 0)
                ru_pct = round(ru_count / max(total_samples, 1) * 100, 1)
                threshold = factor["thresholds"].get("warn_if_ru_below_pct", 40)
                status = STATUS_PASS if ru_pct >= threshold else STATUS_WARN
                top5 = list(tld_dist.items())[:5]
                top5_str = ", ".join(f"{tld}: {cnt}" for tld, cnt in top5)
                audit.factors.append(make_result(
                    factor, status, tld_dist,
                    f"TLD из {total_samples} сэмплов Webmaster. .ru+.рф: {ru_pct}%. Топ-5: {top5_str}",
                    "yandex_webmaster",
                ))
                audit.charts["tld_breakdown"] = tld_dist
            else:
                audit.factors.append(manual_stub(factor, "Нет Serpstat и Webmaster."))

        elif factor["id"] == 7:  # dofollow/nofollow
            if summary and "data" in summary:
                dofollow = summary["data"].get("dofollow_links", 0) or 0
                total = summary["data"].get("backlinks", 0) or 0
                if total > 0:
                    pct = round(dofollow / total * 100, 1)
                    status = STATUS_PASS if pct >= factor["thresholds"].get("warn_if_dofollow_pct_below", 50) else STATUS_WARN
                    audit.factors.append(make_result(
                        factor, status, pct,
                        f"dofollow: {pct}% ({dofollow:,} из {total:,})".replace(",", " "),
                        "serpstat",
                    ))
                    audit.charts["follow_breakdown"] = {
                        "dofollow": dofollow,
                        "nofollow": total - dofollow,
                    }
                    continue
            audit.factors.append(manual_stub(factor, "Нет follow-статистики."))

        elif factor["id"] == 8:  # Homepage vs inner
            # Webmaster samples fallback: подсчитываем сколько ссылок идёт на / vs внутренние
            if yw_data and yw_data.get("samples"):
                homepage_count = 0
                inner_count = 0
                for sample in yw_data["samples"]:
                    dest = sample.get("destination_url", "")
                    try:
                        path = urlparse(dest).path.rstrip("/")
                        if not path or path == "":
                            homepage_count += 1
                        else:
                            inner_count += 1
                    except (ValueError, IndexError):
                        inner_count += 1
                total = homepage_count + inner_count
                if total > 0:
                    inner_pct = round(inner_count / total * 100, 1)
                    threshold = factor["thresholds"].get("warn_if_inner_above_pct", 80)
                    status = STATUS_PASS if inner_pct <= threshold else STATUS_WARN
                    audit.factors.append(make_result(
                        factor, status, {"homepage": homepage_count, "inner": inner_count},
                        f"Homepage: {homepage_count} ({round(homepage_count/total*100)}%), "
                        f"Inner: {inner_count} ({round(inner_count/total*100)}%) "
                        f"(из {total} сэмплов Webmaster)",
                        "yandex_webmaster",
                    ))
                    continue
            audit.factors.append(manual_stub(factor, "Нет Serpstat getBacklinks / Webmaster samples."))

        elif factor["id"] == 9:  # Rel=canonical цитирование
            audit.factors.append(manual_stub(factor, "Нестандартный паттерн, требуется ручная SERP-проверка."))

        elif factor["id"] == 10:  # gov/edu
            # Webmaster samples fallback: ищем gov/edu среди доноров
            if yw_data and yw_data.get("samples"):
                gov_edu_links = _extract_gov_edu_from_samples(yw_data["samples"])
                count = len(gov_edu_links)
                status = _classify_by_threshold(count, factor["thresholds"])
                sample_str = ", ".join(gov_edu_links[:3]) if gov_edu_links else "нет"
                audit.factors.append(make_result(
                    factor, status, count,
                    f"gov/edu донаров: {count} (из {len(yw_data['samples'])} сэмплов). Примеры: {sample_str}",
                    "yandex_webmaster",
                ))
            else:
                audit.factors.append(manual_stub(factor, "Нет Serpstat getBacklinks / Webmaster samples."))

        elif factor["id"] == 11:  # Социальные сигналы
            # Парсим SERP через site:vk.com <brand>
            brand = domain.split(".")[0]
            count = _serp_count_mentions(brand)
            if count is not None:
                status = _classify_by_threshold(count, factor["thresholds"])
                audit.factors.append(make_result(
                    factor, status, count,
                    f"Упоминаний в соцсетях (SERP-оценка): ~{count}",
                    "serp_parse",
                ))
            else:
                audit.factors.append(manual_stub(factor, "SERP-парсинг заблокирован антиботом."))

        elif factor["id"] == 12:  # Brand mentions без ссылки
            audit.factors.append(manual_stub(factor, "Нужен Ahrefs Content Explorer или Brand24."))


def _serp_count_mentions(query: str) -> int | None:
    """Очень простая оценка количества SERP-упоминаний через публичный Яндекс.
    В проде не надёжно — Яндекс требует XML-поиска. Возвращаем None на любые ошибки."""
    try:
        resp = requests.get(
            "https://yandex.ru/search/",
            params={"text": f"{query} site:vk.com OR site:t.me"},
            headers={"User-Agent": USER_AGENT},
            timeout=10,
        )
        if resp.status_code != 200:
            return None
        # Очень грубая оценка — кол-во ссылок в выдаче
        soup = BeautifulSoup(resp.text, "html.parser")
        return min(len(soup.select("a")), 50)
    except requests.RequestException:
        return None


# ============================================================
# Чекеры — АНКОРЫ И ТОКСИЧНОСТЬ
# ============================================================
def check_anchor_toxicity(
    factors: list[dict],
    domain: str,
    providers: dict[str, Any],
    audit: AuditResult,
) -> None:
    sp = providers.get("serpstat")
    anchors_data = sp.anchors(domain) if sp and sp.available else None
    ct = providers.get("checktrust")

    # Распределение анкоров для графика
    anchor_dist = {"brand": 0, "exact": 0, "partial": 0, "naked_url": 0, "generic": 0, "empty": 0}

    if anchors_data and "data" in anchors_data:
        rows = anchors_data["data"].get("data", []) if isinstance(anchors_data["data"], dict) else []
        brand_token = domain.split(".")[0].lower()
        for row in rows[:200]:
            anchor = (row.get("anchor") or "").lower().strip()
            count = row.get("count") or 1
            if not anchor:
                anchor_dist["empty"] += count
            elif re.match(r"^https?://", anchor) or domain in anchor:
                anchor_dist["naked_url"] += count
            elif brand_token in anchor:
                anchor_dist["brand"] += count
            elif anchor in ("тут", "здесь", "сайт", "ссылка", "click here", "here"):
                anchor_dist["generic"] += count
            elif len(anchor.split()) <= 3:
                anchor_dist["exact"] += count
            else:
                anchor_dist["partial"] += count

    audit.charts["anchor_distribution"] = anchor_dist

    total_anchors = sum(anchor_dist.values()) or 1

    for factor in factors:
        if factor["id"] == 13:  # Распределение анкоров
            exact_pct = round(anchor_dist["exact"] / total_anchors * 100, 1)
            if anchor_dist["exact"] > 0 or anchor_dist["brand"] > 0:
                status = STATUS_PASS if exact_pct <= 20 else STATUS_WARN
                audit.factors.append(make_result(
                    factor, status, anchor_dist,
                    f"Brand {round(anchor_dist['brand']/total_anchors*100)}% | Exact {exact_pct}% | "
                    f"Partial {round(anchor_dist['partial']/total_anchors*100)}% | "
                    f"URL {round(anchor_dist['naked_url']/total_anchors*100)}% | "
                    f"Generic {round(anchor_dist['generic']/total_anchors*100)}%",
                    "serpstat",
                ))
            else:
                audit.factors.append(manual_stub(factor, "Нет данных по анкорам."))

        elif factor["id"] == 14:  # Переспам exact
            exact_pct = round(anchor_dist["exact"] / total_anchors * 100, 1)
            if anchor_dist["exact"] > 0:
                status = _classify_by_threshold(exact_pct, factor["thresholds"])
                audit.factors.append(make_result(
                    factor, status, exact_pct,
                    f"Точных вхождений: {exact_pct}% ({anchor_dist['exact']} из {total_anchors})",
                    "serpstat",
                ))
            else:
                audit.factors.append(manual_stub(factor, "Нет данных по анкорам."))

        elif factor["id"] == 15:  # Токсичные доноры
            if ct and ct.available:
                metrics = ct.domain_metrics(domain)
                xs = None
                if metrics:
                    try:
                        xs = metrics.get("items", {}).get(domain, {}).get("xs")
                    except (AttributeError, TypeError):
                        pass
                if xs is not None:
                    # XS 0-100, чем выше — тем спамнее. Используем как прокси для пула (не идеально)
                    status = _classify_by_threshold(xs, {"warn_above_pct": 5, "fail_above_pct": 15})
                    audit.factors.append(make_result(
                        factor, status, xs,
                        f"Собственный X-Spam={xs}. Для токсичности донаров нужен bulk-вызов по каждому.",
                        "checktrust",
                    ))
                    continue
            audit.factors.append(manual_stub(factor, "Checktrust bulk по всем донорам платный."))

        elif factor["id"] == 16:  # Footprint авторский
            audit.factors.append(manual_stub(factor, "Нужен Ahrefs Content Explorer для author detection."))

        elif factor["id"] == 17:  # Нулевой анкор
            empty_pct = round(anchor_dist["empty"] / total_anchors * 100, 1)
            if anchor_dist["empty"] > 0 or total_anchors > 1:
                status = _classify_by_threshold(empty_pct, factor["thresholds"])
                audit.factors.append(make_result(
                    factor, status, empty_pct,
                    f"Нулевой анкор: {empty_pct}%",
                    "serpstat",
                ))
            else:
                audit.factors.append(manual_stub(factor, "Нет данных по анкорам."))


# ============================================================
# Чекеры — ДИНАМИКА
# ============================================================
def check_dynamics_age(
    factors: list[dict],
    domain: str,
    providers: dict[str, Any],
    audit: AuditResult,
) -> None:
    ah = providers.get("ahrefs")
    sp = providers.get("serpstat")
    yw = providers.get("yandex_webmaster")

    # Pre-fetch Webmaster history if available (for velocity)
    yw_history: dict[str, Any] | None = None
    if yw and yw.available:
        host_id = audit.meta.get("yandex_webmaster", {}).get("host_id")
        if host_id:
            yw_history = yw.links_external_history(host_id)
            if yw_history:
                print("[dynamics] Yandex.Webmaster history loaded", file=sys.stderr)

    for factor in factors:
        if factor["id"] == 18:  # Median age
            if ah and ah.available:
                ah.overview(domain)  # check availability
                audit.factors.append(manual_stub(factor, "Ahrefs site-explorer/overview не возвращает median age. Нужен backlinks endpoint + расчёт."))
            else:
                audit.factors.append(manual_stub(factor, "Нужен Ahrefs API."))

        elif factor["id"] == 19:  # Velocity 12m
            nl = sp.new_lost(domain) if sp and sp.available else None
            if nl and "data" in nl:
                # Заглушка — без исторических данных за 12 мес
                monthly = [0] * 12  # TODO: нужен getReferringDomainsHistory
                audit.charts["velocity_12m"] = monthly
                audit.factors.append(manual_stub(factor, "Serpstat getReferringDomainsHistory в платном плане."))
            elif yw_history:
                # Yandex.Webmaster external links history — показывает total по месяцам
                indicators = yw_history.get("indicators", {})
                links_total = indicators.get("LINKS_TOTAL_COUNT", [])
                hosts_total = indicators.get("LINKS_TOTAL_HOSTS_COUNT", [])

                # Собираем помесячную динамику (последние 12 точек)
                if links_total:
                    points = links_total[-12:] if len(links_total) > 12 else links_total
                    monthly_values = [p.get("value", 0) for p in points]
                    monthly_labels = [p.get("date", "")[:7] for p in points]
                    audit.charts["velocity_12m"] = monthly_values
                    audit.charts["velocity_12m_labels"] = monthly_labels

                    # Detect spikes: >300% MoM growth
                    has_spike = False
                    spike_details = []
                    for i in range(1, len(monthly_values)):
                        prev = monthly_values[i - 1]
                        curr = monthly_values[i]
                        if prev > 0 and curr > prev * 4:  # >300% growth
                            has_spike = True
                            spike_details.append(f"{monthly_labels[i]}: +{round((curr-prev)/prev*100)}%")

                    if has_spike:
                        status = STATUS_WARN
                        evidence = f"Спайки в ссылочной: {', '.join(spike_details)}"
                    else:
                        status = STATUS_PASS
                        evidence = f"Динамика стабильная за {len(monthly_values)} месяцев"

                    evidence += f". Диапазон: {min(monthly_values)}-{max(monthly_values)} ссылок"

                    audit.factors.append(make_result(
                        factor, status,
                        {"monthly": monthly_values, "labels": monthly_labels},
                        evidence + " (данные Yandex.Webmaster)",
                        "yandex_webmaster",
                    ))
                else:
                    audit.factors.append(manual_stub(factor, "Webmaster history пуст."))
            else:
                audit.factors.append(manual_stub(factor, "Нужен Serpstat/Ahrefs history или Yandex.Webmaster."))

        elif factor["id"] == 20:  # Lost backlinks
            nl = sp.new_lost(domain) if sp and sp.available else None
            if nl and "data" in nl:
                lost = nl["data"].get("lost_domains", 0) or 0
                total = max((nl["data"].get("referring_domains", 1) or 1), 1)
                pct = round(lost / total * 100, 1)
                status = _classify_by_threshold(pct, factor["thresholds"])
                audit.factors.append(make_result(
                    factor, status, pct,
                    f"Lost за 30 дней: {pct}% ({lost} из {total})",
                    "serpstat",
                ))
            elif yw_history:
                # Webmaster fallback: сравниваем последний и предпоследний месяц
                indicators = yw_history.get("indicators", {})
                links_total = indicators.get("LINKS_TOTAL_COUNT", [])
                if len(links_total) >= 2:
                    current = links_total[-1].get("value", 0)
                    previous = links_total[-2].get("value", 0)
                    if previous > 0:
                        lost_pct = round(max(0, (previous - current)) / previous * 100, 1)
                        status = _classify_by_threshold(lost_pct, factor["thresholds"])
                        audit.factors.append(make_result(
                            factor, status, lost_pct,
                            f"Изменение за последний месяц: {previous} -> {current} "
                            f"(потеря {lost_pct}%, данные Yandex.Webmaster)",
                            "yandex_webmaster",
                        ))
                    else:
                        audit.factors.append(manual_stub(factor, "Нулевая база в Webmaster — нечего сравнивать."))
                else:
                    audit.factors.append(manual_stub(factor, "Недостаточно исторических данных в Webmaster."))
            else:
                audit.factors.append(manual_stub(factor, "Нет данных по lost."))


# ============================================================
# Чекеры — ВНУТРЕННЯЯ ПЕРЕЛИНКОВКА (свой crawler)
# ============================================================
def crawl_internal(domain: str, max_pages: int = MAX_CRAWL_PAGES, timeout: int = DEFAULT_TIMEOUT) -> dict[str, Any]:
    """
    Лёгкий BFS-краулер — считает внутренние ссылки, сирот, глубину, битые.
    Возвращает {pages_count, avg_links, orphans, max_depth, broken, redirects}.
    """
    base = f"https://{domain}"
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    visited: dict[str, dict[str, Any]] = {}  # url -> {depth, links_out, status}
    incoming: dict[str, int] = {}
    broken: list[str] = []
    redirects: list[str] = []
    queue: deque[tuple[str, int]] = deque([(base + "/", 0)])
    max_depth = 0

    while queue and len(visited) < max_pages:
        url, depth = queue.popleft()
        if url in visited:
            continue
        try:
            resp = session.get(url, timeout=timeout, allow_redirects=False)
            if 300 <= resp.status_code < 400:
                redirects.append(url)
                loc = resp.headers.get("Location", "")
                if loc:
                    new_url = urljoin(url, loc)
                    if new_url not in visited:
                        queue.append((new_url, depth))
                continue
            if resp.status_code >= 400:
                broken.append(url)
                visited[url] = {"depth": depth, "links_out": 0, "status": resp.status_code}
                continue
            html = resp.text
        except requests.RequestException:
            broken.append(url)
            visited[url] = {"depth": depth, "links_out": 0, "status": 0}
            continue

        max_depth = max(max_depth, depth)
        soup = BeautifulSoup(html, "html.parser")
        links_out = 0
        for a in soup.find_all("a", href=True):
            href = str(a["href"]).split("#")[0]
            if not href:
                continue
            full = urljoin(url, href)
            parsed = urlparse(full)
            if domain not in parsed.netloc:
                continue
            links_out += 1
            incoming[full] = incoming.get(full, 0) + 1
            if full not in visited and len(visited) + len(queue) < max_pages:
                queue.append((full, depth + 1))
        visited[url] = {"depth": depth, "links_out": links_out, "status": 200}

    orphans = [u for u in visited if incoming.get(u, 0) == 0 and u != base + "/"]
    total_links = sum(v["links_out"] for v in visited.values())
    avg_links = round(total_links / max(len(visited), 1), 1)

    return {
        "pages_count": len(visited),
        "avg_internal_links": avg_links,
        "orphans_count": len(orphans),
        "orphans_sample": orphans[:10],
        "max_click_depth": max_depth,
        "broken_internal": len(broken),
        "broken_sample": broken[:10],
        "redirect_chains": len(redirects),
    }


def check_internal_linking(
    factors: list[dict],
    domain: str,
    audit: AuditResult,
    enable_crawl: bool,
) -> None:
    if not enable_crawl:
        for f in factors:
            audit.factors.append(manual_stub(f, "Crawler отключён (--no-crawl)."))
        return

    print("[internal] BFS-краул до 100 страниц...", file=sys.stderr)
    try:
        data = crawl_internal(domain)
    except Exception as exc:
        print(f"[internal] crawler failed: {exc}", file=sys.stderr)
        for f in factors:
            audit.factors.append(manual_stub(f, f"Crawler упал: {exc}"))
        return

    audit.meta["crawl"] = {
        "pages_count": data["pages_count"],
        "orphans_sample": data["orphans_sample"],
        "broken_sample": data["broken_sample"],
    }

    for factor in factors:
        if factor["id"] == 21:  # Avg internal links
            val = data["avg_internal_links"]
            status = _classify_by_threshold(val, factor["thresholds"])
            audit.factors.append(make_result(
                factor, status, val,
                f"Среднее внутренних ссылок на страницу: {val}",
                "crawl",
            ))
        elif factor["id"] == 22:  # Orphans
            val = data["orphans_count"]
            status = _classify_by_threshold(val, factor["thresholds"])
            audit.factors.append(make_result(
                factor, status, val,
                f"Сирот: {val} (из {data['pages_count']} страниц)",
                "crawl",
            ))
        elif factor["id"] == 23:  # Click depth
            val = data["max_click_depth"]
            status = _classify_by_threshold(val, factor["thresholds"])
            audit.factors.append(make_result(
                factor, status, val,
                f"Максимальная глубина: {val} кликов",
                "crawl",
            ))
        elif factor["id"] == 24:  # Broken internal
            val = data["broken_internal"]
            status = _classify_by_threshold(val, factor["thresholds"])
            audit.factors.append(make_result(
                factor, status, val,
                f"Битых внутренних: {val}",
                "crawl",
            ))
        elif factor["id"] == 25:  # Redirects
            val = data["redirect_chains"]
            status = _classify_by_threshold(val, factor["thresholds"])
            audit.factors.append(make_result(
                factor, status, val,
                f"Цепочек редиректов в ссылочной: {val}",
                "crawl",
            ))


# ============================================================
# Чекеры — КОНКУРЕНТЫ
# ============================================================
def check_competitor_gap(
    factors: list[dict],
    domain: str,
    competitors: list[str],
    providers: dict[str, Any],
    audit: AuditResult,
) -> None:
    sp = providers.get("serpstat")

    if not competitors or not sp or not sp.available:
        for f in factors:
            audit.factors.append(manual_stub(f, "Нет списка конкурентов или нет Serpstat API."))
        return

    our = sp.backlinks_summary(domain)
    our_rd = 0
    if our and "data" in our:
        our_rd = our["data"].get("referring_domains", 0) or 0

    comp_rds: list[int] = []
    for comp in competitors:
        s = sp.backlinks_summary(comp)
        if s and "data" in s:
            comp_rds.append(s["data"].get("referring_domains", 0) or 0)

    avg_comp = int(sum(comp_rds) / len(comp_rds)) if comp_rds else 0
    audit.charts["competitor_comparison"] = {
        "labels": [domain] + competitors,
        "values": [our_rd] + comp_rds,
    }

    for factor in factors:
        if factor["id"] == 26:  # Ссылочный разрыв
            if avg_comp > 0 and our_rd > 0:
                gap_pct = round((avg_comp - our_rd) / avg_comp * 100, 1)
                if gap_pct < 0:
                    gap_pct = 0
                status = _classify_by_threshold(gap_pct, factor["thresholds"])
                audit.factors.append(make_result(
                    factor, status, gap_pct,
                    f"Разрыв: {gap_pct}% (мы {our_rd} ref domains vs средний конкурент {avg_comp})",
                    "serpstat",
                ))
            else:
                audit.factors.append(manual_stub(factor, "Не удалось получить данные по всем участникам."))

        elif factor["id"] == 27:  # Уникальные доноры конкурентов
            audit.factors.append(manual_stub(
                factor,
                "Нужен Serpstat getIntersect — сравнение доноров. Доступно в платной тарифке.",
            ))


# ============================================================
# Summary
# ============================================================
def summarize(factors: list[FactorResult]) -> dict[str, Any]:
    counts = {STATUS_PASS: 0, STATUS_WARN: 0, STATUS_FAIL: 0, STATUS_MANUAL: 0, STATUS_NA: 0}
    by_group: dict[str, dict[str, int]] = {}
    critical_fails: list[dict[str, str]] = []
    for f in factors:
        counts[f.status] = counts.get(f.status, 0) + 1
        g = by_group.setdefault(f.group, {STATUS_PASS: 0, STATUS_WARN: 0, STATUS_FAIL: 0, STATUS_MANUAL: 0, STATUS_NA: 0})
        g[f.status] = g.get(f.status, 0) + 1
        if f.status == STATUS_FAIL and f.severity in ("critical", "high"):
            critical_fails.append({
                "id": str(f.id),
                "name": f.name,
                "severity": f.severity,
                "group": f.group,
                "evidence": f.evidence,
            })
    sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    critical_fails.sort(key=lambda x: sev_order.get(x["severity"], 9))
    automated = counts[STATUS_PASS] + counts[STATUS_WARN] + counts[STATUS_FAIL]
    score = round(counts[STATUS_PASS] / max(automated, 1) * 100, 1)
    return {
        "counts": counts,
        "by_group": by_group,
        "critical_fails_top": critical_fails[:5],
        "score": score,
        "automated_factors": automated,
    }


# ============================================================
# Main pipeline
# ============================================================
def run_audit(
    target_domain: str,
    competitors: list[str] | None = None,
    enable_crawl: bool = True,
    timeout: int = DEFAULT_TIMEOUT,  # noqa: ARG001
) -> AuditResult:
    domain = normalize_domain(target_domain)
    competitors = [normalize_domain(c) for c in (competitors or [])]

    providers = build_providers()
    audit = AuditResult(
        target_domain=domain,
        audited_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        providers_available={k: v.available for k, v in providers.items()},
        competitors=competitors,
    )

    factors = load_factors()
    audit.meta["factors_total"] = len(factors)

    groups: dict[str, list[dict]] = {}
    for f in factors:
        groups.setdefault(f["group"], []).append(f)

    print(f"[1/5] Внешний ссылочный профиль ({len(groups.get('external_profile', []))} факторов)...", file=sys.stderr)
    check_external_profile(groups.get("external_profile", []), domain, providers, audit)

    print(f"[2/5] Анкор-лист и токсичность ({len(groups.get('anchor_toxicity', []))})...", file=sys.stderr)
    check_anchor_toxicity(groups.get("anchor_toxicity", []), domain, providers, audit)

    print(f"[3/5] Динамика и возраст ({len(groups.get('dynamics_age', []))})...", file=sys.stderr)
    check_dynamics_age(groups.get("dynamics_age", []), domain, providers, audit)

    print(f"[4/5] Внутренняя перелинковка ({len(groups.get('internal_linking', []))})...", file=sys.stderr)
    check_internal_linking(groups.get("internal_linking", []), domain, audit, enable_crawl)

    print(f"[5/5] Конкурентный разрыв ({len(groups.get('competitor_gap', []))})...", file=sys.stderr)
    check_competitor_gap(groups.get("competitor_gap", []), domain, competitors, providers, audit)

    # Сортируем по id
    audit.factors.sort(key=lambda f: f.id)
    audit.meta["summary"] = summarize(audit.factors)
    return audit


# ============================================================
# CLI
# ============================================================
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Link Factors Audit — аудит по 27 ссылочным факторам"
    )
    parser.add_argument("domain", help="Домен (например example.com)")
    parser.add_argument("--output", "-o", default="link-audit.json", help="Путь к JSON")
    parser.add_argument("--competitors", default="", help="Конкуренты через запятую")
    parser.add_argument("--no-crawl", action="store_true", help="Отключить внутренний краул")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    args = parser.parse_args()

    competitors = [c.strip() for c in args.competitors.split(",") if c.strip()]

    try:
        result = run_audit(
            target_domain=args.domain,
            competitors=competitors,
            enable_crawl=not args.no_crawl,
            timeout=args.timeout,
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
        f"     Score: {summary.get('score', 0)}% ({counts.get('pass', 0)}/{summary.get('automated_factors', 0)} автоматических)\n"
        f"     FAIL: {counts.get('fail', 0)}, WARN: {counts.get('warn', 0)}, MANUAL: {counts.get('manual', 0)}\n"
        f"     Providers: {result.providers_available}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
