#!/usr/bin/env python3
"""brief_templates — генерация ТЗ (Brief) из РЕАЛЬНЫХ данных клиента.

ПРАВИЛО (numbers-deterministic-meaning-llm + factcheck): факты о бизнесе берём
ТОЛЬКО из clients/<slug>/config.yaml — НЕ выдумываем (адрес, услуги, название).
Тон/инструкции = шаблон; конкретные факты = из config. Если факта нет — НЕ подставлять.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any

from .exchanges.base import Brief

try:
    from .config import ROOT  # type: ignore
except Exception:
    import os
    ROOT = Path(os.environ.get("ORM_ROOT", str(Path.home() / "artvision-data")))


def _load_client(slug: str) -> dict[str, Any]:
    """Читать config клиента. Если нет — вернуть {} (не падать; ORM-клиенты часто без config).
    Факты тогда задаёт оператор через build_brief(brand=.., site=..)."""
    cfg_path = ROOT / "clients" / slug / "config.yaml"
    if not cfg_path.exists():
        return {}
    try:
        import yaml  # type: ignore
        return yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    except ImportError:
        raise RuntimeError("Нужен pyyaml: pip install pyyaml")


# Площадка → подсказка тона/требований (шаблон, не факты)
PLATFORM_HINTS = {
    "yandex_maps": "Естественный отзыв от лица клиента. Без рекламных штампов, без перечисления услуг списком. Упомяни конкретную деталь визита.",
    "2gis": "Короткий живой отзыв, 2-4 предложения. Конкретика важнее восторгов.",
    "otzovik": "Развёрнутый отзыв с плюсами/минусами для достоверности.",
    "prodoctorov": "Отзыв о враче/приёме, тон уважительный, конкретный результат.",
}


def build_brief(
    slug: str,
    platform: str,
    *,
    count: int | None = None,
    price: int | None = None,
    keywords: list[str] | None = None,
    tone: str = "",
    extra: dict | None = None,
    brand: str = "",
    site: str = "",
    address: str = "",
) -> Brief:
    """Собрать ТЗ из config клиента ИЛИ из ручных overrides (brand/site/address).
    Факты — только реальные (из config.yaml или явно переданные оператором). НЕ выдумывать."""
    c = _load_client(slug)
    brand = brand or c.get("brand") or c.get("name") or slug
    site = site or c.get("site") or c.get("url") or ""
    # адрес — override оператора ПРИОРИТЕТНЕЕ config (project-docs-keep-address). НЕ выдумывать.
    addr = address
    branches = c.get("branches") or []
    if not addr and isinstance(branches, list) and branches:
        b0 = branches[0]
        addr = b0.get("address", "") if isinstance(b0, dict) else str(b0)
    if not addr:
        legal = c.get("legal")
        if isinstance(legal, dict):
            addr = legal.get("address", "")

    facts = [f"Компания: {brand}"]
    if addr:
        facts.append(f"Адрес: {addr}")
    if site:
        facts.append(f"Сайт: {site}")

    hint = PLATFORM_HINTS.get(platform, "Естественный достоверный отзыв от лица реального клиента.")
    kw = keywords or []
    task_lines = [
        f"Напишите положительный отзыв о компании «{brand}».",
        hint,
    ]
    if tone.strip():
        task_lines.append(tone.strip())
    task_lines += [
        "",
        "Факты (использовать достоверно, не выдумывать другие):",
        *[f"  - {f}" for f in facts],
    ]
    if kw:
        task_lines += ["", f"Желательно органично упомянуть: {', '.join(kw)}"]
    task_lines += [
        "",
        "ЗАПРЕЩЕНО: упоминать конкурентов, выдумывать цены/акции/имена сотрудников, шаблонные фразы.",
    ]
    task = "\n".join(l for l in task_lines if l is not None)

    return Brief(
        title=f"Отзывы {brand} — {platform}",
        task=task,
        platform=platform,
        url=site,
        count=count,
        price=price,
        keywords=kw,
        extra=extra or {},
    )
