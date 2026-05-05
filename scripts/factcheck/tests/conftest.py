"""Pytest fixtures for factcheck Loki pipeline tests.

We bias toward small synthetic HTML and only optionally pull live KP
samples (controlled by env var ARTVISION_TEST_REAL_KP=1) so the suite
runs offline by default and on CI.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Iterator

import pytest

# Make the parent package importable when running `pytest` from any cwd.
PKG_PARENT = Path(__file__).resolve().parents[2]
if str(PKG_PARENT) not in sys.path:
    sys.path.insert(0, str(PKG_PARENT))


SYNTHETIC_KP_HTML = """<!doctype html>
<html lang="ru">
<head>
    <meta charset="utf-8">
    <title>Коммерческое предложение — Стом-Shop</title>
    <meta name="description" content="Тестовое КП">
</head>
<body>
<header><nav>меню</nav></header>
<main>
<h1>SEO-продвижение Стом-Shop</h1>
<p>Стом-Shop — это магазин стоматологических материалов в Санкт-Петербурге.</p>
<p>В компании работает 25 человек, выручка по ФНС за 2024 год — 87 млн ₽.</p>
<p>Тариф «Старт» стоит 65 000 ₽/мес и включает технический аудит и публикации.</p>
<p>Тариф «Рост» стоит 95 000 ₽/мес — добавляются внешние ссылки и парасайтинг.</p>
<p>На Яндекс.Картах у Стом-Shop рейтинг 4.8 при 312 отзывах.</p>
<p>Конкурент DentalShop занимает 3-ю позицию по запросу «стоматологические материалы СПб».</p>
<p>Сайт https://stomshop.pro работает с 2018 года.</p>
<p>Команда уже опубликовала 47 статей на vc.ru за 12 месяцев.</p>
<p>В первый месяц подключаем Я.Метрику и Search Console — counter ID 12345678.</p>
<p>Ожидаемый прирост трафика — от 30% до 50% за полгода.</p>
<p>В Топ-10 Яндекс СПб по основному кластеру сегодня 4 позиции.</p>
<p>Контакт: hello@artvision.pro, +7 (911) 096-81-45.</p>
</main>
<footer>контакты</footer>
<script>console.log('skip me');</script>
</body>
</html>
"""


SHORT_HTML = """<!doctype html>
<html><head><title>Mini</title></head>
<body><p>Цена тарифа Старт — 50 000 ₽ в месяц. Сайт https://example.com работает с 2020.</p></body>
</html>
"""


EMPTY_HTML = """<!doctype html><html><head><title></title></head><body><script>x=1</script></body></html>
"""


@pytest.fixture
def synthetic_kp_path(tmp_path: Path) -> Path:
    p = tmp_path / "synthetic_kp.html"
    p.write_text(SYNTHETIC_KP_HTML, encoding="utf-8")
    return p


@pytest.fixture
def short_html_path(tmp_path: Path) -> Path:
    p = tmp_path / "short.html"
    p.write_text(SHORT_HTML, encoding="utf-8")
    return p


@pytest.fixture
def empty_html_path(tmp_path: Path) -> Path:
    p = tmp_path / "empty.html"
    p.write_text(EMPTY_HTML, encoding="utf-8")
    return p


@pytest.fixture
def real_kp_paths() -> Iterator[list[Path]]:
    """Optional fixture — only loaded when ARTVISION_TEST_REAL_KP=1.

    Returns up to 3 real KPs from the artvision-data repo so we can run
    smoke-tests on production-shaped input without spamming git diffs.
    """
    if os.environ.get("ARTVISION_TEST_REAL_KP") != "1":
        yield []
        return

    candidates = [
        Path("/Users/antonk/artvision-data/clients/na-sklad/kp/index.html"),
        Path("/Users/antonk/artvision-data/clients/zakvaski-rus/presale/kp/index.html"),
        Path("/Users/antonk/artvision-data/clients/dentalexpo/presale/kp/rocadamed_kp.html"),
        Path("/Users/antonk/artvision-data/clients/advertmed/40-audits/annurclinic/kp.html"),
    ]
    yield [p for p in candidates if p.is_file()]


class FakeGroqClient:
    """Stand-in for GroqClient used in unit tests; returns canned JSON."""

    def __init__(self, claims_per_chunk: list[list[dict]] | None = None) -> None:
        self.available = True
        self.calls: list[dict] = []
        if claims_per_chunk is None:
            claims_per_chunk = [
                [
                    {
                        "text": "Стом-Shop — магазин стоматологических материалов в Санкт-Петербурге.",
                        "subject": "Стом-Shop",
                        "predicate": "является",
                        "object": "магазин стоматологических материалов в Санкт-Петербурге",
                        "type": "fact",
                    },
                    {
                        "text": "Тариф Старт стоит 65 000 ₽/мес.",
                        "subject": "Тариф Старт",
                        "predicate": "стоит",
                        "object": "65 000 ₽/мес",
                        "type": "numeric",
                    },
                    {
                        "text": "Сайт https://stomshop.pro работает с 2018 года.",
                        "subject": "Сайт https://stomshop.pro",
                        "predicate": "работает с",
                        "object": "2018 года",
                        "type": "url",
                    },
                ]
            ]
        self._queue = list(claims_per_chunk)

    def chat(self, messages, **kwargs):
        self.calls.append({"messages": messages, "kwargs": kwargs})
        if self._queue:
            payload = self._queue.pop(0)
        else:
            payload = []
        import json as _json
        return _json.dumps({"claims": payload}, ensure_ascii=False)


@pytest.fixture
def fake_groq_client() -> FakeGroqClient:
    return FakeGroqClient()
