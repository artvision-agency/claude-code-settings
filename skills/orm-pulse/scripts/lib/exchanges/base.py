#!/usr/bin/env python3
"""ExchangeProvider — единый интерфейс бирж отзывов (qcomment / turbotext).

Назначение: ORM-команда пишет ТЗ (бриф) и сообщения ИСПОЛНИТЕЛЯМ на биржах.
Money-safety: любой write на биржу (create_order/message) тратит деньги / пишет
исполнителю → по умолчанию dry-run, реальная отправка только commit=True + CONFIRM Антона.

НЕ показывать заказчику: исполнителей, биржи, ТЗ, pending-очередь (NDA, rules/orm.md).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol, Any


@dataclass(frozen=True)
class Brief:
    """ТЗ для заказа отзывов — генерируется из данных клиента, БЕЗ выдуманных фактов."""
    title: str               # название проекта (видно исполнителям)
    task: str                # текст ТЗ: что писать, тон, что упомянуть
    platform: str            # площадка публикации (yandex_maps / 2gis / otzovik / ...)
    url: str = ""            # ссылка на карточку/страницу клиента
    language: str = "ru"
    count: int | None = None # сколько отзывов купить
    price: int | None = None # цена за отзыв (₽)
    keywords: list[str] = field(default_factory=list)  # ключи для упоминания
    require_screenshot: bool = True
    premoderation: bool = True
    extra: dict[str, Any] = field(default_factory=dict)  # provider-specific


@dataclass(frozen=True)
class WriteResult:
    """Результат write-операции. dry_run=True → ничего не отправлено, только preview."""
    ok: bool
    dry_run: bool
    provider: str
    action: str              # create_order / message / rework / reject
    preview: str             # что было бы отправлено (для dry-run) / что отправлено
    response: Any = None     # сырой ответ биржи (при commit)
    error: str = ""


class ExchangeProvider(Protocol):
    """Контракт провайдера биржи. Реализации: QcommentProvider, TurbotextProvider."""

    name: str

    def create_order(self, brief: Brief, *, commit: bool = False) -> WriteResult:
        """Создать заказ/проект с ТЗ для исполнителей. Тратит деньги при commit."""
        ...

    def message(self, order_id: str, text: str, *, commit: bool = False) -> WriteResult:
        """Сообщение исполнителю по заказу/комменту."""
        ...

    def rework(self, item_id: str, reason: str, *, commit: bool = False) -> WriteResult:
        """Отправить на доработку с причиной (= сообщение исполнителю)."""
        ...

    def reject(self, item_id: str, reason: str, *, commit: bool = False) -> WriteResult:
        """Отклонить с причиной (= сообщение исполнителю)."""
        ...

    def list_orders(self, status: str = "all") -> list[dict]:
        """Список заказов/проектов (read-only, без трат)."""
        ...
