#!/usr/bin/env python3
"""
playwright-services.py — unified UI-automation wrapper для сервисов без публичного API.

Решает проблему ad-hoc `/tmp/tv_*.py` скриптов (session 87d9412c 2026-05-20).
Любая UI-задача (Topvisor UI, SBIS UI, и т.д.) ходит через единый класс
`PlaywrightService` с общими: stealth-init, save/load storage_state, SPA-ожидание,
чтение credentials из `~/artvision-data/tokens.json`.

Подклассы реализуют только service-specific логику логина.

Использование (как скрипт):
    python3 ~/.claude/scripts/playwright-services.py topvisor --check
    python3 ~/.claude/scripts/playwright-services.py topvisor --check --headless=0

Использование (как модуль):
    from playwright_services import TopvisorService
    svc = TopvisorService()
    page = svc.ensure_logged_in()  # переиспользует storage_state если есть
    page.goto("https://topvisor.com/ru/cabinet/...")
    ...
    svc.close()

CLI:
    --check        тест авторизации + sanity check + обновить marker
    --headless=0   видимый браузер (default headless=1)
    --force-login  игнорировать сохранённый storage_state, делать свежий логин

State:
    ~/.claude_temp_scripts/playwright-services-state/<service>.json    (storage_state)
    ~/.claude_temp_scripts/playwright-services-state/.<service>-auth-ok  (marker, mtime = last success)

Зависимости:
    pip install playwright && playwright install chromium

Прецеденты:
    - 2026-05-20 session 87d9412c — логин Topvisor через UI для настройки региона
      проектов где API настройка недоступна.
    - SBIS UI — для отправки тикетов в техподдержку (skill `sbis-support`),
      placeholder ниже.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

# --- Defer playwright import до actual use, чтобы --help работало без установки --
try:
    from playwright.sync_api import sync_playwright, Page, BrowserContext, Browser
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    sync_playwright = None  # type: ignore[assignment]
    Page = None  # type: ignore[assignment,misc]
    BrowserContext = None  # type: ignore[assignment,misc]
    Browser = None  # type: ignore[assignment,misc]


HOME = Path.home()
TOKENS_PATH = HOME / "artvision-data" / "tokens.json"
STATE_DIR = HOME / ".claude_temp_scripts" / "playwright-services-state"
STATE_DIR.mkdir(parents=True, exist_ok=True)

# Stealth init script — минимальный набор патчей для обхода basic bot detection.
# Не для серьёзного anti-bot (Cloudflare turnstile / DataDome) — но достаточно
# для большинства legitimate сервисов где мы платный пользователь.
STEALTH_INIT_SCRIPT = """
// Override webdriver flag
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined,
});

// Plugins length
Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5],
});

// Languages
Object.defineProperty(navigator, 'languages', {
    get: () => ['ru-RU', 'ru', 'en-US', 'en'],
});

// Permissions API — chrome.permissions.query возвращает default
const originalQuery = (window.navigator.permissions && window.navigator.permissions.query)
    ? window.navigator.permissions.query.bind(window.navigator.permissions)
    : null;
if (originalQuery) {
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications' ?
            Promise.resolve({ state: Notification.permission }) :
            originalQuery(parameters)
    );
}
"""


class PlaywrightService:
    """Базовый класс UI-сервиса.

    Подклассы должны:
    1. Установить `service_name` (для tokens.json и storage_state file).
    2. Реализовать `login(page)` — service-specific логин flow.
    3. Опционально: `sanity_check(page)` — проверка что мы залогинены
       (для --check).
    """

    service_name: str = ""              # override в подклассе
    login_url: str = ""                  # override
    sanity_url: str = ""                 # URL который доступен только залогиненным
    sanity_text_marker: str = ""         # текст который должен быть на sanity_url

    def __init__(
        self,
        headless: bool = True,
        force_login: bool = False,
        timeout_ms: int = 30000,
    ):
        if not self.service_name:
            raise ValueError("Subclass must set service_name")
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError(
                "playwright not installed. Run: pip install playwright "
                "&& playwright install chromium"
            )
        self.headless = headless
        self.force_login = force_login
        self.timeout_ms = timeout_ms
        self.state_file = STATE_DIR / f"{self.service_name}.json"
        self.marker_file = STATE_DIR / f".{self.service_name}-auth-ok"

        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None

        self.credentials = self._load_credentials()

    def _load_credentials(self) -> dict:
        """Читает tokens.json → <service_name>. Требует минимум login + password."""
        if not TOKENS_PATH.exists():
            raise FileNotFoundError(
                f"tokens.json not found at {TOKENS_PATH}. "
                f"Check `~/artvision-data/tokens.json`."
            )
        with open(TOKENS_PATH) as f:
            data = json.load(f)
        if self.service_name not in data:
            raise KeyError(
                f"Service '{self.service_name}' not in tokens.json. "
                f"Available top-level keys: {list(data.keys())[:20]}"
            )
        creds = data[self.service_name]
        if "login" not in creds:
            raise KeyError(
                f"tokens.json → {self.service_name} missing 'login' field"
            )
        if "password" not in creds:
            raise KeyError(
                f"tokens.json → {self.service_name} missing 'password' field"
            )
        return creds

    def _start_browser(self):
        """Поднимает playwright + browser + context."""
        if self._playwright is not None:
            return  # уже стартовали
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=self.headless,
            args=["--disable-blink-features=AutomationControlled"],
        )

        # Решение: использовать сохранённый storage_state если он есть и
        # force_login=False. Явно передаём аргументы (pyright корректно типизирует).
        storage_state = (
            str(self.state_file)
            if self.state_file.exists() and not self.force_login
            else None
        )
        self._context = self._browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/130.0.0.0 Safari/537.36"
            ),
            locale="ru-RU",
            timezone_id="Europe/Moscow",
            storage_state=storage_state,
        )
        self._context.add_init_script(STEALTH_INIT_SCRIPT)
        self._context.set_default_timeout(self.timeout_ms)

    def _new_page(self) -> "Page":
        self._start_browser()
        return self._context.new_page()

    # ------------------------------------------------------------------
    # Override points
    # ------------------------------------------------------------------

    def login(self, page: "Page") -> None:
        """Service-specific login flow. Должен довести страницу до залогиненного
        состояния."""
        raise NotImplementedError("Subclass must implement login()")

    def sanity_check(self, page: "Page") -> bool:
        """Проверка что мы действительно залогинены. Возвращает True/False.

        Default: если есть `sanity_url` и `sanity_text_marker` — открыть URL и
        проверить наличие текста. Подклассы могут переопределить для custom logic.
        """
        if not self.sanity_url or not self.sanity_text_marker:
            # Нет sanity-config — считаем что логин уже что-то проверил
            return True
        page.goto(self.sanity_url, wait_until="domcontentloaded")
        self.wait_render(page, key_text=self.sanity_text_marker, timeout=20)
        content = page.content()
        return self.sanity_text_marker in content

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def wait_render(
        self,
        page: "Page",
        key_text: Optional[str] = None,
        timeout: int = 25,
        poll_interval: float = 1.0,
    ) -> bool:
        """Длинный sleep + poll для SPA. Без этого `page.content()` часто
        возвращает пустой body для React/Vue.

        Возвращает True если key_text найден за timeout секунд.
        Если key_text не задан — просто ждёт `timeout` секунд (fallback).
        """
        if key_text is None:
            time.sleep(timeout)
            return True

        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                if key_text in page.content():
                    return True
            except Exception:
                pass
            time.sleep(poll_interval)
        return False

    def save_state(self) -> None:
        """Сохраняет cookies + localStorage в storage_state.json."""
        if self._context is None:
            return
        self._context.storage_state(path=str(self.state_file))

    def load_state(self) -> bool:
        """True если есть сохранённый storage_state."""
        return self.state_file.exists()

    def update_marker(self, success: bool) -> None:
        """Обновляет marker файл (mtime = время последнего успешного --check)."""
        if success:
            self.marker_file.touch()
        else:
            # При неуспехе НЕ удаляем — оставляем старый mtime для diagnostics.
            pass

    def ensure_logged_in(self) -> "Page":
        """Главный entry point для модулей-потребителей.

        1. Открыть страницу (с сохранённым state если есть)
        2. Если sanity_check OK — вернуть страницу
        3. Иначе — login() + save_state() + проверить ещё раз
        """
        page = self._new_page()

        # Try with existing state first
        if self.load_state() and not self.force_login:
            try:
                if self.sanity_check(page):
                    return page
            except Exception:
                pass  # fall through к свежему логину

        # Fresh login
        page.goto(self.login_url, wait_until="domcontentloaded")
        self.login(page)
        self.save_state()
        return page

    def close(self) -> None:
        try:
            if self._context:
                self._context.close()
            if self._browser:
                self._browser.close()
            if self._playwright:
                self._playwright.stop()
        except Exception as e:
            print(f"[warn] close error: {e}", file=sys.stderr)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# ============================================================================
# Topvisor
# ============================================================================


class TopvisorService(PlaywrightService):
    """Topvisor UI — нужен для настройки регионов проектов где API недоступен
    (см. session 87d9412c, `feedback_topvisor_ui_required_for_region.md`)."""

    service_name = "topvisor"
    login_url = "https://topvisor.com/ru/#view-dialog_auth=auth"
    # После логина — главная cabinet содержит «Проекты» / список проектов
    sanity_url = "https://topvisor.com/ru/"
    sanity_text_marker = "Выйти"  # ссылка «Выйти» видна только залогиненному

    def login(self, page: "Page") -> None:
        """Topvisor login flow.

        Стратегия:
        1. Открыть login_url (модальное окно auth)
        2. Если есть кнопка «Войти в аккаунт» — кликнуть (раскрывает форму)
        3. Найти input[type=email] / input[name=email] / input по placeholder,
           ввести login
        4. Найти input[type=password], ввести password
        5. Submit (Enter или button submit)
        6. Подождать редиректа на cabinet
        """
        # Step 1: на странице может быть кнопка «Войти в аккаунт» открывающая
        # форму. Если её нет — форма уже открыта.
        try:
            btn = page.get_by_text("Войти в аккаунт", exact=False).first
            if btn.is_visible(timeout=3000):
                btn.click()
                time.sleep(1)
        except Exception:
            pass  # форма уже открыта

        # Step 2: email/login input
        login_value = self.credentials["login"]
        password_value = self.credentials["password"]

        # Пробуем несколько селекторов в порядке убывания specificity
        email_selectors = [
            'input[type="email"]',
            'input[name="login"]',
            'input[name="email"]',
            'input[placeholder*="mail" i]',
            'input[placeholder*="логин" i]',
        ]
        email_input = None
        for sel in email_selectors:
            try:
                el = page.locator(sel).first
                if el.is_visible(timeout=2000):
                    email_input = el
                    break
            except Exception:
                continue
        if email_input is None:
            raise RuntimeError(
                "Topvisor: email/login input not found. "
                "Возможно изменился HTML формы — обнови селекторы."
            )
        email_input.fill(login_value)

        # Step 3: password input
        pwd_input = page.locator('input[type="password"]').first
        pwd_input.fill(password_value)

        # Step 4: submit
        try:
            pwd_input.press("Enter")
        except Exception:
            # Fallback: ищем submit button
            for sel in ['button[type="submit"]', 'button:has-text("Войти")']:
                try:
                    page.locator(sel).first.click()
                    break
                except Exception:
                    continue

        # Step 5: ждём редиректа — после успеха пропадает форма
        # либо мы попадаем на /ru/cabinet или появляется «Выйти»
        self.wait_render(page, key_text="Выйти", timeout=20)


# ============================================================================
# SBIS (placeholder — для skill `sbis-support`)
# ============================================================================


class SbisService(PlaywrightService):
    """SBIS / online.sbis.ru — для отправки тикетов техподдержки.

    TODO: implement login flow.
    Скорее всего:
    - login_url = "https://online.sbis.ru/auth/"
    - login через СНИЛС/телефон + пароль ИЛИ через QR-код в моб. приложении
      (QR — мы не сможем автоматизировать, требует ручного шага).
    - Проверить наличие токена СБИС API — возможно UI не нужен.
    """

    service_name = "sbis"  # ожидает запись в tokens.json
    login_url = "https://online.sbis.ru/auth/"
    sanity_url = "https://online.sbis.ru/"
    sanity_text_marker = "Выход"  # типичный паттерн RU SaaS

    def login(self, page: "Page") -> None:
        raise NotImplementedError(
            "SbisService.login() not yet implemented. "
            "Use skill `sbis-support` for manual flow. "
            "Прежде чем реализовать — проверить есть ли публичное API "
            "(СБИС API через токен) которое покрывает use case без UI."
        )


# ============================================================================
# Registry
# ============================================================================


SERVICES = {
    "topvisor": TopvisorService,
    "sbis": SbisService,
}


def _check(service_name: str, headless: bool, force_login: bool) -> int:
    """Возвращает exit code: 0=OK, 1=fail."""
    if service_name not in SERVICES:
        print(
            f"Unknown service '{service_name}'. Available: "
            f"{list(SERVICES.keys())}",
            file=sys.stderr,
        )
        return 1

    cls = SERVICES[service_name]
    print(f"[playwright-services] --check {service_name} "
          f"(headless={headless}, force_login={force_login})")

    try:
        svc = cls(headless=headless, force_login=force_login)
    except (FileNotFoundError, KeyError, RuntimeError) as e:
        print(f"[fail] init: {e}", file=sys.stderr)
        return 1

    start = time.time()
    try:
        page = svc.ensure_logged_in()
        ok = svc.sanity_check(page)
        elapsed = time.time() - start
        if ok:
            print(f"[ok] {service_name} logged in & sanity OK ({elapsed:.1f}s)")
            svc.update_marker(success=True)
            return 0
        else:
            print(
                f"[fail] sanity_check returned False after login "
                f"({elapsed:.1f}s). Marker '{svc.sanity_text_marker}' "
                f"not found at {svc.sanity_url}.",
                file=sys.stderr,
            )
            return 1
    except Exception as e:
        elapsed = time.time() - start
        print(f"[fail] {service_name} after {elapsed:.1f}s: {type(e).__name__}: {e}",
              file=sys.stderr)
        return 1
    finally:
        svc.close()


def main():
    parser = argparse.ArgumentParser(
        description="Unified Playwright wrapper для UI-сервисов без публичного API"
    )
    parser.add_argument(
        "service",
        choices=list(SERVICES.keys()),
        help="Сервис: " + ", ".join(SERVICES.keys()),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Тест авторизации + sanity check + обновление marker",
    )
    parser.add_argument(
        "--headless",
        type=int,
        default=1,
        choices=[0, 1],
        help="0 = видимый браузер (для debug), 1 = headless (default)",
    )
    parser.add_argument(
        "--force-login",
        action="store_true",
        help="Игнорировать сохранённый storage_state, делать свежий логин",
    )
    args = parser.parse_args()

    if not args.check:
        parser.error("Сейчас поддерживается только --check. "
                     "Для других задач — импортируй модуль и используй "
                     "ensure_logged_in().")

    sys.exit(_check(args.service, bool(args.headless), args.force_login))


if __name__ == "__main__":
    main()
