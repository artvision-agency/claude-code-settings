#!/usr/bin/env python3
"""
pre-deploy-coords-verify.py
PreToolUse hook: блокирует scp/cp HTML если координаты Я.Карты смещены >2 км от OSM.
Прецедент: IPOTEKA sessionId c052407c — пин Setl Ривьера смещён на 4 км.
Bypass: COORDS_VERIFY_SKIP=1
"""

import json
import math
import os
import re
import sys
import urllib.request
import urllib.parse
import urllib.error
import time
import logging

LOG_PATH = os.path.expanduser("~/.claude/logs/pre-deploy-coords-verify.log")
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("coords-verify")


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return distance in metres between two lat/lon points."""
    R = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


class NominatimNetworkError(Exception):
    """Сетевой/HTTP сбой обращения к Nominatim — НЕ путать с 'пусто' (нет такого места)."""


def nominatim_geocode(query: str, city: str = "Санкт-Петербург") -> tuple[float, float] | None:
    """Return (lat, lon) from Nominatim OSM, or None если место не найдено (пустой ответ).
    Поднимает NominatimNetworkError при сетевом/HTTP-сбое — чтобы caller мог fail-CLOSED,
    а не молча пропустить непроверенные координаты."""
    q = urllib.parse.quote(f"{query} {city}")
    url = f"https://nominatim.openstreetmap.org/search?q={q}&format=json&limit=1"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "artvision-hallucination-hook/1.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read())
    except Exception as exc:
        # FAIL-CLOSED: сетевой/HTTP/parse-сбой — НЕ можем проверить координату.
        log.warning("Nominatim network error for %r: %s", query, exc)
        raise NominatimNetworkError(str(exc)) from exc
    if data:
        return float(data[0]["lat"]), float(data[0]["lon"])
    return None  # валидный ответ, но место не найдено — это не сетевой сбой


def extract_html_path(command: str) -> str | None:
    """Extract first .html file path from scp/cp command string."""
    m = re.search(r"(\S+\.html)", command)
    return m.group(1) if m else None


def find_coords_in_html(html: str) -> list[dict]:
    """
    Extract coordinate pairs and nearby name context from HTML.
    Яндекс iframe: ll=LON,LAT or center/pt params.
    JS arrays: [LON, LAT] pattern near object name.
    Returns list of {lon, lat, context}.
    """
    results = []

    # Pattern 1: Yandex maps iframe pt=LON,LAT,pm2...
    for m in re.finditer(r"[?&]pt=([0-9]{1,3}\.[0-9]+),([0-9]{1,2}\.[0-9]+)", html):
        lon, lat = float(m.group(1)), float(m.group(2))
        start = max(0, m.start() - 500)
        end = min(len(html), m.end() + 500)
        context = html[start:end]
        results.append({"lon": lon, "lat": lat, "context": context, "source": "yandex-pt"})

    # Pattern 2: Yandex maps ll=LON,LAT (map center)
    for m in re.finditer(r"[?&]ll=([0-9]{1,3}\.[0-9]+),([0-9]{1,2}\.[0-9]+)", html):
        lon, lat = float(m.group(1)), float(m.group(2))
        start = max(0, m.start() - 500)
        end = min(len(html), m.end() + 500)
        context = html[start:end]
        results.append({"lon": lon, "lat": lat, "context": context, "source": "yandex-ll"})

    # Pattern 3: JS array [LON, LAT] near "coords" keyword
    for m in re.finditer(r"coords[\"']?\s*[:=]\s*\[([0-9]{1,3}\.[0-9]+),\s*([0-9]{1,2}\.[0-9]+)\]", html, re.IGNORECASE):
        lon, lat = float(m.group(1)), float(m.group(2))
        start = max(0, m.start() - 300)
        end = min(len(html), m.end() + 300)
        context = html[start:end]
        results.append({"lon": lon, "lat": lat, "context": context, "source": "js-coords"})

    return results


def extract_name_from_context(context: str) -> str | None:
    """Try to find a building/project name in context text."""
    # Common patterns for real estate: «Name» or data-title="Name" or >Name<
    for pat in [
        r'data-name=["\']([^"\']{5,60})["\']',
        r'data-title=["\']([^"\']{5,60})["\']',
        r'<b>([^<]{5,60})</b>',
        r'«([^»]{5,60})»',
        r'"name"\s*:\s*"([^"]{5,60})"',
        r'title["\']?\s*[:=]\s*["\']([^"\']{5,60})["\']',
    ]:
        m = re.search(pat, context, re.IGNORECASE)
        if m:
            name = m.group(1).strip()
            # Filter out HTML boilerplate
            if not any(skip in name.lower() for skip in ["<!doctype", "charset", "viewport", "https://"]):
                return name
    return None


def is_valid_spb_coords(lat: float, lon: float) -> bool:
    """Rough bounding box for Saint Petersburg region."""
    return 59.5 <= lat <= 60.5 and 29.0 <= lon <= 31.5


def is_valid_msk_coords(lat: float, lon: float) -> bool:
    """Rough bounding box for Moscow region."""
    return 55.0 <= lat <= 56.5 and 36.0 <= lon <= 38.5


def main() -> int:
    if os.environ.get("COORDS_VERIFY_SKIP") == "1":
        print("[coords-verify] SKIP via COORDS_VERIFY_SKIP=1", file=sys.stderr)
        return 0

    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        # Not JSON stdin — pass through
        return 0

    command = data.get("tool_input", {}).get("command", "")

    # Only trigger on scp/cp commands involving .html files
    if not re.search(r"\bscp\b|\bcp\b|\brsync\b", command):
        return 0
    if ".html" not in command:
        return 0

    html_path = extract_html_path(command)
    if not html_path or not os.path.isfile(html_path):
        return 0

    log.info("Checking coords in %s", html_path)

    try:
        with open(html_path, encoding="utf-8", errors="replace") as f:
            html = f.read()
    except OSError as exc:
        log.warning("Cannot read %s: %s", html_path, exc)
        return 0

    coords_list = find_coords_in_html(html)
    if not coords_list:
        log.info("No coordinates found in %s — PASS", html_path)
        return 0

    criticals = []
    warnings = []

    for entry in coords_list:
        lat, lon = entry["lat"], entry["lon"]

        # Skip non-SPb/MSK coordinates — not our context
        if not (is_valid_spb_coords(lat, lon) or is_valid_msk_coords(lat, lon)):
            continue

        name = extract_name_from_context(entry["context"])
        if not name:
            log.info("No name found near coords %s,%s — skipping geocode", lat, lon)
            continue

        city = "Санкт-Петербург" if is_valid_spb_coords(lat, lon) else "Москва"
        osm_result = nominatim_geocode(name, city)
        time.sleep(1.1)  # Nominatim rate limit: 1 req/sec

        if osm_result is None:
            log.info("Nominatim returned nothing for %r — skipping", name)
            continue

        osm_lat, osm_lon = osm_result
        dist = haversine_m(lat, lon, osm_lat, osm_lon)
        log.info("Name=%r coords=(%s,%s) osm=(%s,%s) dist=%.0fm", name, lat, lon, osm_lat, osm_lon, dist)

        if dist > 2000:
            criticals.append(
                f"CRITICAL: «{name}» — coords ({lon},{lat}) смещены на {dist:.0f} м от OSM ({osm_lon:.4f},{osm_lat:.4f})"
            )
        elif dist > 500:
            warnings.append(
                f"WARN: «{name}» — coords ({lon},{lat}) смещены на {dist:.0f} м от OSM ({osm_lon:.4f},{osm_lat:.4f})"
            )

    if criticals:
        print("\n[pre-deploy-coords-verify] BLOCKED — КРИТИЧЕСКИЕ ошибки координат:", file=sys.stderr)
        for msg in criticals:
            print(f"  {msg}", file=sys.stderr)
        if warnings:
            for msg in warnings:
                print(f"  {msg}", file=sys.stderr)
        print("\nИсправь координаты или: COORDS_VERIFY_SKIP=1", file=sys.stderr)
        log.error("BLOCK: %d critical coord errors in %s", len(criticals), html_path)
        return 2

    if warnings:
        print("\n[pre-deploy-coords-verify] WARN — подозрительные координаты:", file=sys.stderr)
        for msg in warnings:
            print(f"  {msg}", file=sys.stderr)
        print("Проверь вручную или: COORDS_VERIFY_SKIP=1", file=sys.stderr)
        log.warning("WARN: %d coord warnings in %s", len(warnings), html_path)
        return 1

    log.info("PASS: all coords OK in %s", html_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
