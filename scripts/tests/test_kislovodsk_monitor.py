#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Регрессионные тесты для монитора безопасности Кисловодска (КМВ).

Покрывают КЛЮЧЕВУЮ логику трёх модулей БЕЗ сети (Telethon не вызывается —
тестируются только чистые функции и константы; импорт модулей сети не делает):

  • kislovodsk_common.py            → is_allclear/near, COORDS, detect_places
  • kislovodsk-realtime-alert.py    → classify_realtime() truth-table + soft-cap
  • kislovodsk-safety-digest.py     → classify_digest_message() уровень/зоны

Плюс регрессии на исправленные баги:
  (а) сообщение старше 10 мин, но новее watermark → real-time НЕ теряет (age soft-cap);
  (б) «угроза Минеральным Водам … БПЛА» → НЕ all-clear, триггерит 🔴;
  (в) «отбой беспилотной опасности в Кисловодске» → в дайджесте НЕ red;
  (г) airport-only событие → zone kmv.

Запуск:
  pytest ~/.claude/scripts/tests/test_kislovodsk_monitor.py
  python3 -m unittest test_kislovodsk_monitor   (из этой папки)
"""

import importlib.util
import os
import sys
import unittest
from datetime import datetime, timezone, timedelta

SCRIPTS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SCRIPTS)  # чтобы скрипты нашли kislovodsk_common


def _load(mod_name, file_name):
    """Загрузить модуль по пути (имена файлов содержат дефисы → import нельзя)."""
    path = os.path.join(SCRIPTS, file_name)
    spec = importlib.util.spec_from_file_location(mod_name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # импорт не делает сетевых вызовов
    return mod


import kislovodsk_common as KC  # noqa: E402  (общий модуль на sys.path)
RT = _load("kislovodsk_rt", "kislovodsk-realtime-alert.py")
DG = _load("kislovodsk_dg", "kislovodsk-safety-digest.py")

# Города, которые ОБЯЗАНЫ присутствовать в карте
EXPECTED_CITIES = [
    "Кисловодск", "Минеральные Воды", "Ессентуки", "Пятигорск", "Ставрополь",
    "Невинномысск", "Ростов-на-Дону", "Батайск", "Тихорецк", "Миллерово",
    "Краснодар", "Волгоград",
]


# ── 1. Real-time classify_realtime() — truth-table (что пушится МГНОВЕННО) ───
class TestRealtimeClassify(unittest.TestCase):
    """Вариант «б»: 🔴 ТОЛЬКО при явном КМВ-городе + триггер БПЛА.
    Всё остальное (краевое / маршрут / отбой / не-курорт) — НЕ мгновенный пуш."""

    def test_kmv_city_plus_trigger_is_red(self):
        self.assertEqual(
            RT.classify_realtime("В Кисловодске объявлена опасность атаки БПЛА"),
            ("kmv", "red"))

    def test_kmv_city_pyatigorsk_drone_is_red(self):
        self.assertEqual(
            RT.classify_realtime("Над Пятигорском замечен беспилотник"),
            ("kmv", "red"))

    def test_oblast_wide_without_city_not_pushed(self):
        self.assertEqual(
            RT.classify_realtime(
                "На территории Ставропольского края объявлена опасность атаки БПЛА"),
            (None, None))

    def test_route_city_not_pushed_realtime(self):
        self.assertEqual(
            RT.classify_realtime("В Ростове-на-Дону угроза атаки БПЛА"),
            (None, None))

    def test_allclear_not_pushed_even_with_city(self):
        self.assertEqual(
            RT.classify_realtime("Отбой беспилотной опасности в Кисловодске"),
            (None, None))

    def test_nevinnomyssk_not_resort_not_pushed(self):
        self.assertEqual(
            RT.classify_realtime("В Невинномысске опасность атаки БПЛА"),
            (None, None))


# ── 2. Точный словарь — «удар»/«атака» без БПЛА-слов НЕ триггерят ────────────
class TestPreciseDictionary(unittest.TestCase):
    def test_udar_alone_no_realtime(self):
        self.assertEqual(
            RT.classify_realtime("Сильный удар по воротам в Кисловодске на матче"),
            (None, None))

    def test_ataka_alone_no_realtime(self):
        self.assertEqual(
            RT.classify_realtime("Мощная атака нападающего в Пятигорске"),
            (None, None))

    def test_udar_ataka_not_in_primary(self):
        self.assertNotIn("удар", RT.PRIMARY)
        self.assertNotIn("атака", RT.PRIMARY)

    def test_udar_ataka_not_in_digest_threat_words(self):
        self.assertNotIn("удар", DG.DRONE + DG.AIRRAID)
        self.assertNotIn("атака", DG.DRONE + DG.AIRRAID)

    def test_bare_dron_excluded_from_drone(self):
        # bare «дрон» исключён (ловит «квадродрон»/«дрон-шоу» → false-🔴)
        self.assertNotIn("дрон", KC.DRONE)
        self.assertIn("дрон-камикадзе", KC.DRONE)


# ── 3. is_allclear() — отбой vs ложное срабатывание на «Минеральн» (bug #2) ──
class TestAllClear(unittest.TestCase):
    def test_otboi_bespilotnoy_is_allclear(self):
        self.assertTrue(KC.is_allclear("Отбой беспилотной опасности"))

    def test_otboi_vozdushnoy_trevogi_is_allclear(self):
        self.assertTrue(KC.is_allclear("Отбой воздушной тревоги в регионе"))

    def test_opasnost_minovala_is_allclear(self):
        self.assertTrue(KC.is_allclear("Опасность миновала, можно выходить"))

    def test_ugroza_mineralnym_vodam_is_NOT_allclear(self):
        # bug #2: «угроза Минеральным Водам» НЕ должно считаться отбоем
        self.assertFalse(
            KC.is_allclear("Угроза Минеральным Водам, объявлена опасность атаки БПЛА"))

    def test_opasnost_minvod_is_NOT_allclear(self):
        self.assertFalse(KC.is_allclear("Опасность для Минвод сохраняется"))


# ── 4. Уровень/зоны ДАЙДЖЕСТА (classify_digest_message — реальная функция) ───
def _dg(text, channel_zone="kmv"):
    return DG.classify_digest_message(channel_zone, text)


class TestDigestLevel(unittest.TestCase):
    def test_kmv_city_threat_is_red(self):
        zones, level, _air = _dg("В Ессентуках сбит ударный БПЛА")
        self.assertEqual(level, "red")
        self.assertIn("kmv", zones)

    def test_oblast_wide_is_yellow(self):
        _zones, level, _air = _dg("Ставропольский край: объявлена опасность атаки БПЛА")
        self.assertEqual(level, "yellow")

    def test_route_is_yellow(self):
        _zones, level, _air = _dg("Ростов-на-Дону: угроза БПЛА, задержки поездов")
        self.assertEqual(level, "yellow")

    def test_no_threat_not_red(self):
        # без триггера БПЛА сообщение не релевантно и точно НЕ red
        zones, level, _air = _dg("Хорошая погода в Кисловодске")
        self.assertEqual(zones, set())
        self.assertNotEqual(level, "red")

    def test_red_requires_trigger_near_city(self):
        # bug #8: город как пункт назначения + БПЛА далеко → НЕ red
        far = ("Поезд Москва — Кисловодск задержан. " + ("ситуация спокойная. " * 6)
               + "В Брянской области объявлена опасность атаки БПЛА.")
        _zones, level, _air = _dg(far)
        self.assertNotEqual(level, "red")


# ── 5. zone_summary() — агрегация уровня по зоне ─────────────────────────────
class TestDigestZoneSummary(unittest.TestCase):
    def test_red_match_gives_red_emoji(self):
        matches = [{"zone": {"kmv"}, "level": "red", "name": "x", "time": "01.01 00:00",
                    "snippet": "s", "ch": "c", "mid": 1}]
        lvl, _txt, pick = DG.zone_summary(matches, "kmv")
        self.assertEqual(lvl, "🔴")
        self.assertEqual(len(pick), 1)

    def test_only_yellow_gives_yellow_emoji(self):
        matches = [{"zone": {"kmv"}, "level": "yellow", "name": "x", "time": "01.01 00:00",
                    "snippet": "s", "ch": "c", "mid": 1}]
        lvl, _txt, _pick = DG.zone_summary(matches, "kmv")
        self.assertEqual(lvl, "🟡")

    def test_empty_gives_green_emoji(self):
        lvl, _txt, pick = DG.zone_summary([], "kmv")
        self.assertEqual(lvl, "🟢")
        self.assertEqual(pick, [])

    def test_zone_filtering(self):
        matches = [{"zone": {"route"}, "level": "red", "name": "x", "time": "01.01 00:00",
                    "snippet": "s", "ch": "c", "mid": 1}]
        lvl, _txt, _pick = DG.zone_summary(matches, "kmv")
        self.assertEqual(lvl, "🟢")


# ── 6. COORDS — состав городов + sanity-диапазоны ───────────────────────────
class TestCoords(unittest.TestCase):
    def _check(self, coords):
        for city in EXPECTED_CITIES:
            self.assertIn(city, coords, f"город отсутствует в COORDS: {city}")
        for city, (lat, lon) in coords.items():
            self.assertTrue(43.0 <= lat <= 49.0, f"{city}: lat {lat} вне 43..49")
            self.assertTrue(38.0 <= lon <= 45.0, f"{city}: lon {lon} вне 38..45")
        klat, klon = coords["Кисловодск"]
        self.assertAlmostEqual(klat, 43.9, delta=0.1)
        self.assertAlmostEqual(klon, 42.7, delta=0.1)

    def test_common_coords(self):
        self._check(KC.COORDS)

    def test_modules_reexport_same_coords(self):
        # обе карты — один источник истины (общий модуль)
        self.assertIs(RT.COORDS, KC.COORDS)
        self.assertIs(DG.COORDS, KC.COORDS)


# ── 7. detect_places — гео-парсинг города из текста ─────────────────────────
class TestDetectPlaces(unittest.TestCase):
    def test_kislovodsk_detected(self):
        self.assertIn("Кисловодск", KC.detect_places("удар по Кисловодску"))

    def test_stavropol_krai_not_city_pin(self):
        self.assertNotIn("Ставрополь", KC.detect_places("на территории Ставропольского края"))

    def test_stavropol_city_detected(self):
        self.assertIn("Ставрополь", KC.detect_places("в городе Ставрополь"))


# ── 8. Регрессии на исправленные баги ───────────────────────────────────────
class TestBugRegressions(unittest.TestCase):

    def test_a_realtime_keeps_messages_older_than_10min(self):
        """(а) Сообщение 10-30 мин давности (старше прежнего окна 10 мин), но
        новее watermark, НЕ теряется: возраст — soft-cap (6ч ≥ интервал 30 мин),
        а не условие пуша. Проверяем решение по возрасту в collect()."""
        now = datetime.now(timezone.utc)
        soft_cap = now - timedelta(hours=RT.MAX_AGE_HOURS)
        for age_min in (11, 20, 29, 120):
            m_date = now - timedelta(minutes=age_min)
            self.assertFalse(m_date < soft_cap,
                             f"сообщение {age_min} мин давности не должно отсекаться по возрасту")
        # буфер ≥ StartInterval (1800 c = 30 мин)
        self.assertGreaterEqual(RT.MAX_AGE_HOURS * 3600, 1800)
        # и контент по-прежнему классифицируется как 🔴
        self.assertEqual(
            RT.classify_realtime("В Кисловодске опасность атаки БПЛА"), ("kmv", "red"))

    def test_b_ugroza_mineralnym_vodam_triggers_red(self):
        """(б) «угроза Минеральным Водам … БПЛА» → НЕ all-clear, мгновенный 🔴."""
        text = "Внимание! Угроза Минеральным Водам — объявлена опасность атаки БПЛА"
        self.assertFalse(KC.is_allclear(text))
        self.assertEqual(RT.classify_realtime(text), ("kmv", "red"))

    def test_c_otboi_in_digest_not_red(self):
        """(в) «отбой беспилотной опасности в Кисловодске» → в дайджесте НЕ red."""
        zones, level, _air = _dg("Отбой беспилотной опасности в Кисловодске")
        self.assertEqual(zones, set())
        self.assertIsNone(level)

    def test_d_airport_only_zone_kmv(self):
        """(г) airport-only событие → зона kmv (а не пустая → route на карте)."""
        zones, level, air = _dg("Аэропорт Минеральные Воды закрыт на приём и выпуск")
        self.assertTrue(air)
        self.assertIn("kmv", zones)
        self.assertNotIn("route", zones)


if __name__ == "__main__":
    unittest.main(verbosity=2)
