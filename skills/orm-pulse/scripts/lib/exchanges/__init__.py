"""Биржи отзывов — провайдеры под единым интерфейсом ExchangeProvider."""
from .base import Brief, WriteResult, ExchangeProvider


def get_provider(name: str, *, slug: str | None = None):
    """Фабрика провайдера по имени: qcomment | turbotext."""
    if name == "qcomment":
        from .qcomment import QcommentProvider
        return QcommentProvider(slug=slug)
    if name == "turbotext":
        from .turbotext import TurbotextProvider
        return TurbotextProvider(slug=slug)
    raise ValueError(f"Неизвестный провайдер: {name!r} (qcomment | turbotext)")


__all__ = ["Brief", "WriteResult", "ExchangeProvider", "get_provider"]
