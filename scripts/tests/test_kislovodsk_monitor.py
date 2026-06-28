#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Регрессионные тесты для монитора безопасности Кисловодска (КМВ).

Покрывают КЛЮЧЕВУЮ логику двух скриптов БЕЗ сети (Telethon не вызывается —
тестируются только чистые функции и константы, импорт модулей не ходит в сеть):

  • kislovodsk-realtime-alert.py  → classify() truth-table (что пушится мгновенно)
  • kislovodsk-safety-digest.py   → уровень дайджеста + zone_summary() агрегация
  • COORDS (обоих скриптов)        → состав городов + sanity-диапазоны координат
  • точный словарь триггеров        → «удар»/«атака» без БПЛА-слов НЕ срабатывают

Запуск:
  pytest ~/.claude/scripts/tests/test_kislovodsk_monitor.py
  python3 -m unittest test_kislovodsk_monitor   (из этой папки)
"""

import importlib.util
import os
import unittest

SCRIPTS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(mod_name, file_name):
    """Загрузить модуль по пути (имена файлов содержат дефисы → import нельзя)."""
    path = os.path.join(SCRIPTS, file_name)
    spec = importlib.util.spec_from_file_location(mod_name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # импорт не делает сетевых вызовов (collect — async, вызывается только в main)
    return mod


RT = _load("kislovodsk_rt", "kislovodsk-realtime-alert.py")
DG = _load("kislovodsk_dg", "kislovodsk-safety-digest.py")

# Любой ch для classify (он сигнатурный, внутри не используется)
ANY_CH = {"u": "test", "zone": "kmv", "name": "test", "src": "local"}

# Города, которые ОБЯЗАНЫ присутствовать в карте обоих скриптов
EXPECTED_CITIES = [
    "Кисловодск", "Минеральные Воды", "Ессентуки", "Пятигорск", "Ставрополь",
    "Невинномысск", "Ростов-на-Дону", "Батайск", "Тихорецк", "Миллерово",
    "Краснодар", "Волгоград",
]


# ── 1. Real-time classify() — truth-table (что пушится МГНОВЕННО) ────────────
class TestRealtimeClassify(unittest.TestCase):
    """Вариант «б»: 🔴 ТОЛЬКО при явном КМВ-городе + триггер БПЛА.
    Всё остальное (краевое / маршрут / отбой / не-курорт) — НЕ мгновенный пуш."""

    def test_kmv_city_plus_trigger_is_red(self):
        zone, level = RT.classify(ANY_CH, "В Кисловодске объявлена опасность атаки БПЛА")
        self.assertEqual((zone, level), ("kmv", "red"))

    def test_kmv_city_pyatigorsk_drone_is_red(self):
        zone, level = RT.classify(ANY_CH, "Над Пятигорском замечен беспилотник")
        self.assertEqual((zone, level), ("kmv", "red"))

    def test_oblast_wide_without_city_not_pushed(self):
        # Общекраевое объявление губернатора (без города-курорта) → НЕ мгновенно
        zone, level = RT.classify(
            ANY_CH, "На территории Ставропольского края объявлена опасность атаки БПЛА")
        self.assertEqual((zone, level), (None, None))

    def test_route_city_not_pushed_realtime(self):
        # Маршрутный город (Ростов) → НЕ мгновенный пуш (в дайджест как 🟡)
        zone, level = RT.classify(ANY_CH, "В Ростове-на-Дону угроза атаки БПЛА")
        self.assertEqual((zone, level), (None, None))

    def test_allclear_not_pushed_even_with_city(self):
        # «Отбой» = снятие угрозы → НЕ алертить даже при упоминании города
        zone, level = RT.classify(ANY_CH, "Отбой беспилотной опасности в Кисловодске")
        self.assertEqual((zone, level), (None, None))

    def test_nevinnomyssk_not_resort_not_pushed(self):
        # Невинномысск — НЕ город-курорт КМВ (нет в KMV_CITY) → НЕ мгновенно
        zone, level = RT.classify(ANY_CH, "В Невинномысске опасность атаки БПЛА")
        self.assertEqual((zone, level), (None, None))


# ── 2. Точный словарь — «удар»/«атака» без БПЛА-слов НЕ триггерят ────────────
class TestPreciseDictionary(unittest.TestCase):
    """«удар»/«атака» сами по себе шумные (футбол «удар по воротам») —
    не должны давать срабатывание ни в real-time, ни на уровне дайджеста."""

    def test_udar_alone_no_realtime(self):
        zone, level = RT.classify(ANY_CH, "Сильный удар по воротам в Кисловодске на матче")
        self.assertEqual((zone, level), (None, None))

    def test_ataka_alone_no_realtime(self):
        zone, level = RT.classify(ANY_CH, "Мощная атака нападающего в Пятигорске")
        self.assertEqual((zone, level), (None, None))

    def test_udar_ataka_not_in_primary(self):
        self.assertNotIn("удар", RT.PRIMARY)
        self.assertNotIn("атака", RT.PRIMARY)

    def test_udar_ataka_not_in_digest_threat_words(self):
        self.assertNotIn("удар", DG.DRONE + DG.AIRRAID)
        self.assertNotIn("атака", DG.DRONE + DG.AIRRAID)


# ── 3. Уровень ДАЙДЖЕСТА (КМВ-город → red, краевое/маршрут → yellow) ─────────
def _digest_level(text):
    """Реконструкция per-message формулы дайджеста через РЕАЛЬНЫЕ функции/константы
    модуля (collect() сетевой, но формула level из него вынесена 1-в-1):
        level = 'red' if (threat_hit and has(KMV_CITY)) else 'yellow'
    Тест ловит регресс при изменении словарей DRONE/AIRRAID/KMV_CITY."""
    t = text.lower()
    threat_hit = DG.has(t, DG.DRONE) or DG.has(t, DG.AIRRAID)
    return "red" if (threat_hit and DG.has(t, DG.KMV_CITY)) else "yellow"


class TestDigestLevel(unittest.TestCase):
    def test_kmv_city_threat_is_red(self):
        self.assertEqual(_digest_level("В Ессентуках сбит ударный БПЛА"), "red")

    def test_oblast_wide_is_yellow(self):
        self.assertEqual(
            _digest_level("Ставропольский край: объявлена опасность атаки БПЛА"), "yellow")

    def test_route_is_yellow(self):
        self.assertEqual(_digest_level("Ростов-на-Дону: угроза БПЛА, задержки поездов"), "yellow")

    def test_no_threat_is_yellow_floor(self):
        # без триггера БПЛА уровень не поднимается до red даже с городом
        self.assertEqual(_digest_level("Хорошая погода в Кисловодске"), "yellow")


class TestDigestZoneSummary(unittest.TestCase):
    """zone_summary() — РЕАЛЬНАЯ чистая функция агрегации уровня по зоне."""

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
        # сообщение зоны route не должно попасть в сводку kmv
        matches = [{"zone": {"route"}, "level": "red", "name": "x", "time": "01.01 00:00",
                    "snippet": "s", "ch": "c", "mid": 1}]
        lvl, _txt, _pick = DG.zone_summary(matches, "kmv")
        self.assertEqual(lvl, "🟢")


# ── 4. COORDS — состав городов + sanity-диапазоны (чтобы не «уехать») ────────
class TestCoords(unittest.TestCase):
    """Защита от неверных координат (был прецедент сдвига): все ожидаемые города
    на месте, lat 43..49, lon 38..45, Кисловодск ≈ 43.9, 42.7."""

    def _check_module_coords(self, coords):
        for city in EXPECTED_CITIES:
            self.assertIn(city, coords, f"город отсутствует в COORDS: {city}")
        for city, (lat, lon) in coords.items():
            self.assertTrue(43.0 <= lat <= 49.0, f"{city}: lat {lat} вне 43..49")
            self.assertTrue(38.0 <= lon <= 45.0, f"{city}: lon {lon} вне 38..45")
        klat, klon = coords["Кисловодск"]
        self.assertAlmostEqual(klat, 43.9, delta=0.1)
        self.assertAlmostEqual(klon, 42.7, delta=0.1)

    def test_realtime_coords(self):
        self._check_module_coords(RT.COORDS)

    def test_digest_coords(self):
        self._check_module_coords(DG.COORDS)

    def test_coords_consistent_between_modules(self):
        # обе карты должны совпадать (один источник истины)
        self.assertEqual(RT.COORDS, DG.COORDS)


# ── 5. detect_places — гео-парсинг города из текста (вспомог., для карты) ────
class TestDetectPlaces(unittest.TestCase):
    def test_kislovodsk_detected(self):
        self.assertIn("Кисловодск", RT.detect_places("удар по Кисловодску"))

    def test_stavropol_krai_not_city_pin(self):
        # «ставропольского края» НЕ должно ставить пин города Ставрополь
        self.assertNotIn("Ставрополь", RT.detect_places("на территории Ставропольского края"))

    def test_stavropol_city_detected(self):
        self.assertIn("Ставрополь", RT.detect_places("в городе Ставрополь"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
