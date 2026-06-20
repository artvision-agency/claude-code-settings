#!/usr/bin/env python3
"""TurbotextProvider — биржа turbotext.ru через БРАУЗЕР (API не документирован).

Креды: tokens.json -> turbo_text {email, password}.
Автоматизация: agent-browser (паттерн как skill hostland-fm). Логин → создание заказа
с ТЗ → сообщение исполнителю.

⚠️ ЧЕСТНЫЙ СТАТУС (2026-06-19): селекторы ЛК turbotext.ru НЕ верифицированы
(нет живого доступа в этой сессии: ключ turbo_text отсутствует в локальном tokens.json).
dry_run (commit=False) — печатает что будет сделано, всегда работает.
commit=True — поднимает NotImplementedError с инструкцией, пока селекторы не сняты
с живого ЛК (НЕ выдумываю селекторы — правило no-false-negative / proven-tools-first).

NEXT (свежая сессия с доступом):
  1. agent-browser open https://www.turbotext.ru/ → логин (tokens.turbo_text)
  2. снять селекторы: форма создания заказа отзывов, поле ТЗ, кнопка отправки, чат с исполнителем
  3. заполнить _SELECTORS ниже + реализовать _commit_* через agent-browser
"""
from __future__ import annotations
import json
from pathlib import Path

from .base import Brief, WriteResult

try:
    from ..config import ROOT  # type: ignore
except Exception:
    import os
    ROOT = Path(os.environ.get("ORM_ROOT", str(Path.home() / "artvision-data")))

TOKENS_PATH = ROOT / "tokens.json"
BASE_URL = "https://www.turbotext.ru/"

# TODO(live-ЛК): снять реальные селекторы перед commit-операциями
_SELECTORS: dict[str, str] = {
    # "login_email": "...", "login_pwd": "...", "create_order_btn": "...",
    # "task_field": "...", "submit_btn": "...", "executor_chat_input": "...",
}

_NOT_READY = (
    "turbotext commit недоступен: селекторы ЛК не верифицированы. "
    "Сними их с живого ЛК (agent-browser) и заполни _SELECTORS — см. docstring."
)


class TurbotextProvider:
    name = "turbotext"

    def __init__(self, *, slug: str | None = None):
        self.slug = slug

    def _creds(self) -> dict:
        cfg = json.loads(TOKENS_PATH.read_text(encoding="utf-8")).get("turbo_text")
        if not cfg:
            raise RuntimeError(
                f"tokens.json не содержит 'turbo_text' ({TOKENS_PATH}). Восстанови email/password."
            )
        return cfg

    def list_orders(self, status: str = "all") -> list[dict]:
        # read-only через браузер — реализовать после верификации ЛК
        raise NotImplementedError("turbotext list_orders: нужна браузер-реализация (ЛК не верифицирован)")

    def _preview(self, action: str, detail: str) -> WriteResult:
        return WriteResult(True, True, self.name, action, f"[turbotext/browser] {action}: {detail}")

    def create_order(self, brief: Brief, *, commit: bool = False) -> WriteResult:
        detail = f"title={brief.title!r} platform={brief.platform} count={brief.count}\nТЗ:\n{brief.task}"
        if not commit:
            return self._preview("create_order", detail)
        raise NotImplementedError(_NOT_READY)

    def message(self, order_id: str, text: str, *, commit: bool = False) -> WriteResult:
        if not commit:
            return self._preview("message", f"order={order_id} text={text!r}")
        raise NotImplementedError(_NOT_READY)

    def rework(self, item_id: str, reason: str, *, commit: bool = False) -> WriteResult:
        if not commit:
            return self._preview("rework", f"item={item_id} reason={reason!r}")
        raise NotImplementedError(_NOT_READY)

    def reject(self, item_id: str, reason: str, *, commit: bool = False) -> WriteResult:
        if not commit:
            return self._preview("reject", f"item={item_id} reason={reason!r}")
        raise NotImplementedError(_NOT_READY)
