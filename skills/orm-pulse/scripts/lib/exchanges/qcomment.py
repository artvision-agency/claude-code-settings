#!/usr/bin/env python3
"""QcommentProvider — биржа qcomment.com через API (apicode).

API: https://qcomment.com/api
  newproject   — создать проект с ТЗ (task) для исполнителей  [ТРАТИТ ДЕНЬГИ при pay/оплате]
  projectedit  — изменить проект/ТЗ (task), статус
  revision     — accept(0)/rework(1)/reject(2) коммента + reason-сообщение исполнителю
  projects     — список проектов (read-only)
  requests     — pending-комменты (read-only)

Money-safety: create_order/update_brief/rework/reject делают HTTP ТОЛЬКО при commit=True.
dry_run (commit=False) — печатает preview, ничего не отправляет.

Креды: tokens.json -> qcomment {api_code, api_base}. ⚠️ На 2026-06-19 ключ qcomment
ОТСУТСТВУЕТ в локальном tokens.json (см. HANDOVER) — нужен перед живым прогоном.
"""
from __future__ import annotations
import json
import time
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from typing import Any

from .base import Brief, WriteResult

# lib.config.ROOT — env-override ORM_ROOT, fallback artvision-data
try:
    from ..config import ROOT  # type: ignore
except Exception:
    import os
    ROOT = Path(os.environ.get("ORM_ROOT", str(Path.home() / "artvision-data")))

try:
    from ..budget_guard import append_audit_trail  # type: ignore
except Exception:
    append_audit_trail = None  # type: ignore

TOKENS_PATH = ROOT / "tokens.json"

# comment_configs: 0=reviews 1=questions 2=positive 3=neutral 4=negative 5=replies
COMMENT_CONFIG_POSITIVE_REVIEW = "0,2"


class QcommentError(RuntimeError):
    pass


class QcommentProvider:
    name = "qcomment"

    def __init__(self, *, slug: str | None = None):
        self.slug = slug
        self._creds: dict | None = None  # кэш (фикс LOW: не читать tokens на каждый вызов)

    # --- creds ---
    def _load_creds(self) -> dict:
        if self._creds is None:
            try:
                cfg = json.loads(TOKENS_PATH.read_text(encoding="utf-8"))["qcomment"]
                api_code = cfg["api_code"]
            except KeyError:
                raise QcommentError(
                    f"tokens.json: нет 'qcomment.api_code' ({TOKENS_PATH}). "
                    "Восстанови api_code/api_base (см. HANDOVER — вероятно убран secret-purge / на VPS)."
                )
            except FileNotFoundError:
                raise QcommentError(f"tokens.json не найден: {TOKENS_PATH}")
            self._creds = {"api_code": api_code, "api_base": cfg.get("api_base", "https://qcomment.com/api")}
        return self._creds

    @staticmethod
    def _check(resp):
        """qcomment отдаёт логические ошибки в HTTP-200 JSON ({error:...}) → не считать успехом."""
        if isinstance(resp, dict) and (resp.get("error") or resp.get("errors")):
            raise QcommentError(f"qcomment API error: {resp.get('error') or resp.get('errors')}")
        return resp

    # --- HTTP (фикс HIGH: retry/backoff/обработка ошибок) ---
    def _post(self, endpoint: str, *, retries: int = 3, **params) -> Any:
        creds = self._load_creds()
        params.setdefault("apicode", creds["api_code"])
        params.setdefault("result", "json")
        # фильтр None — не слать пустые параметры
        data = urllib.parse.urlencode(
            {k: v for k, v in params.items() if v is not None}
        ).encode()
        url = f"{creds['api_base']}/{endpoint}"
        last_err: Exception | None = None
        for attempt in range(retries):
            try:
                req = urllib.request.Request(url, data=data, method="POST")
                with urllib.request.urlopen(req, timeout=20) as r:
                    raw = r.read().decode("utf-8", "replace")
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    raise QcommentError(f"{endpoint}: не-JSON ответ: {raw[:200]}")
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", "replace")[:200] if e.fp else ""
                last_err = QcommentError(f"{endpoint}: HTTP {e.code} {body}")
                if e.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                    time.sleep(1.5 * (attempt + 1))  # backoff
                    continue
                break
            except (urllib.error.URLError, TimeoutError) as e:
                last_err = QcommentError(f"{endpoint}: сеть {e}")
                if attempt < retries - 1:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                break
        raise last_err or QcommentError(f"{endpoint}: unknown error")

    def _audit(self, action: str, **extra) -> None:
        if append_audit_trail and self.slug:
            try:
                append_audit_trail(self.slug, {"type": action, "source": f"qcomment-{action}", **extra})
            except Exception:
                pass

    # --- read-only ---
    def list_orders(self, status: str = "all") -> list[dict]:
        resp = self._post("projects", status=status)
        if isinstance(resp, dict):
            return [v for k, v in resp.items() if str(k).startswith("project")]
        return resp if isinstance(resp, list) else []

    # --- writes (money / executor-facing) ---
    def create_order(self, brief: Brief, *, commit: bool = False) -> WriteResult:
        """newproject — заказ с ТЗ. ТРАТИТ ДЕНЬГИ → commit=True + CONFIRM Антона."""
        params = {
            "title": brief.title,
            "task": brief.task,
            "url": brief.url or None,
            "language": brief.language,
            "price": brief.price,
            "pay": brief.count,
            "premoderation": 1 if brief.premoderation else 0,
            "screenshot": 1 if brief.require_screenshot else 0,
            "comment_configs": brief.extra.get("comment_configs", COMMENT_CONFIG_POSITIVE_REVIEW),
            "subjects": brief.extra.get("subjects"),
            "tarif_id": brief.extra.get("tarif_id"),
        }
        preview = (
            f"[qcomment newproject] title={brief.title!r} platform={brief.platform} "
            f"count={brief.count} price={brief.price} url={brief.url}\nТЗ:\n{brief.task}"
        )
        if not commit:
            return WriteResult(True, True, self.name, "create_order", preview)
        if not params.get("subjects") or not params.get("tarif_id"):
            return WriteResult(False, False, self.name, "create_order", preview,
                               error="subjects (категория) и tarif_id обязательны для newproject")
        try:
            resp = self._check(self._post("newproject", **params))
        except QcommentError as e:
            return WriteResult(False, False, self.name, "create_order", preview, error=str(e))
        self._audit("create_order", title=brief.title, count=brief.count, price=brief.price)
        return WriteResult(True, False, self.name, "create_order", preview, response=resp)

    def update_brief(self, project_id: str, task: str, *, commit: bool = False) -> WriteResult:
        """projectedit — изменить ТЗ (сообщение исполнителям проекта)."""
        preview = f"[qcomment projectedit] project_id={project_id}\nНовое ТЗ:\n{task}"
        if not commit:
            return WriteResult(True, True, self.name, "update_brief", preview)
        try:
            resp = self._check(self._post("projectedit", project_id=project_id, task=task))
        except QcommentError as e:
            return WriteResult(False, False, self.name, "update_brief", preview, error=str(e))
        self._audit("update_brief", project_id=project_id)
        return WriteResult(True, False, self.name, "update_brief", preview, response=resp)

    def message(self, order_id: str, text: str, *, commit: bool = False) -> WriteResult:
        """qcomment: сообщение исполнителям проекта = обновление ТЗ (projectedit task).
        Per-comment сообщение конкретному исполнителю → rework/reject (carry reason)."""
        return self.update_brief(order_id, text, commit=commit)

    def _revision(self, comment_id: str, operation: int, reason: str, action: str, commit: bool) -> WriteResult:
        preview = f"[qcomment revision op={operation}] comment_id={comment_id} reason={reason!r}"
        if not commit:
            return WriteResult(True, True, self.name, action, preview)
        if not reason:
            return WriteResult(False, False, self.name, action, preview, error="reason обязателен")
        try:
            resp = self._check(self._post("revision", comment_id=comment_id, operation=operation, reason=reason))
        except QcommentError as e:
            return WriteResult(False, False, self.name, action, preview, error=str(e))
        self._audit(action, comment_id=comment_id, reason=reason, operation=operation)
        return WriteResult(True, False, self.name, action, preview, response=resp)

    def rework(self, item_id: str, reason: str, *, commit: bool = False) -> WriteResult:
        return self._revision(item_id, 1, reason, "rework", commit)

    def reject(self, item_id: str, reason: str, *, commit: bool = False) -> WriteResult:
        return self._revision(item_id, 2, reason, "reject", commit)
