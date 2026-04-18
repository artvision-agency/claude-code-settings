"""Anti-detect smoke: наш скрейпер не должен быть помечен как бот на
типовых bot-detection лабах.

Запускать ТОЛЬКО headful (`--headed`) — headless всегда провалится на
sannysoft. В CI — weekly schedule, не per-commit (дорого и флаки).

Используем SeleniumBase UC mode — в 2026 признан сильнее plain
Playwright stealth-плагинов. Если результат падает — задача не в коде
теста, а в том что апдейтить stealth-конфиг.
"""

from __future__ import annotations

import pytest

pytest.importorskip("seleniumbase")

from seleniumbase import SB  # noqa: E402


@pytest.mark.stealth
@pytest.mark.slow
def test_not_detected_by_sannysoft(anti_detect_targets: list[str]):
    """Pass-criteria soft: sannysoft помечает до 20% checks красным даже
    на живом Chrome. Порог — не больше 30% failures из видимой таблицы.
    """
    url = anti_detect_targets[0]
    with SB(uc=True, test=True, headless=False) as sb:
        sb.open(url)
        sb.sleep(3)
        html = sb.get_page_source()

    failed = html.lower().count("result failed")
    passed = html.lower().count("result passed")
    total = failed + passed or 1
    ratio = failed / total
    assert ratio < 0.30, f"Bot detection ratio too high: {ratio:.0%} ({failed}/{total})"


@pytest.mark.stealth
@pytest.mark.slow
def test_webdriver_flag_is_false():
    """Базовая проверка `navigator.webdriver` — должен быть undefined/false
    в stealth-режиме.
    """
    with SB(uc=True, test=True, headless=False) as sb:
        sb.open("about:blank")
        webdriver = sb.execute_script("return navigator.webdriver")
    assert not webdriver, f"navigator.webdriver leaked: {webdriver!r}"
