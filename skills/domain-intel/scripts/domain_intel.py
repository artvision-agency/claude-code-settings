#!/usr/bin/env python3
"""domain-intel — универсальный CLI для работы с доменами и архивами.

Команды:
  history <domain> [--limit N] [--from YYYY] [--to YYYY]
  diff <url> <date1> <date2>
  restore <url> [--full-site] [--out DIR]
  save <url>
  whois <domain>
  intel <domain>                       # комплексный отчёт
  expired-search [--niche N --tld ru]  # parsing expired площадок (Playwright)
  bulk <yaml-file>
  monitor <yaml-file> [--alert-tg]

Запуск:
  ~/.claude/skills/domain-intel/.venv/bin/python scripts/domain_intel.py <command> [args]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

CDX_API = "https://web.archive.org/cdx/search/cdx"
WAYBACK_TS_FORMAT = "%Y%m%d%H%M%S"
USER_AGENT = "ArtvisionDomainIntel/1.0 (+https://artvision.pro)"
DEFAULT_TIMEOUT = 60
RATE_LIMIT_SLEEP = 0.6  # ~10 req/s allowance
MAX_RETRIES = 4


# ─────────────────────────────────────────────────────────────────────────────
# HTTP с retry/back-off

def http_get(url: str, *, params: dict | None = None, timeout: int = DEFAULT_TIMEOUT) -> requests.Response:
    """GET с экспоненциальным back-off на 429/5xx и сетевые ошибки."""
    last_exc: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.get(url, params=params, timeout=timeout, headers={"User-Agent": USER_AGENT})
            if r.status_code == 429 or r.status_code >= 500:
                sleep_for = (2 ** attempt) + RATE_LIMIT_SLEEP
                time.sleep(sleep_for)
                continue
            return r
        except (requests.ConnectionError, requests.Timeout) as e:
            last_exc = e
            time.sleep((2 ** attempt) + RATE_LIMIT_SLEEP)
    if last_exc:
        raise last_exc
    raise RuntimeError(f"HTTP failed after {MAX_RETRIES} retries: {url}")


# ─────────────────────────────────────────────────────────────────────────────
# CDX (Wayback) primitives

@dataclass
class Snapshot:
    timestamp: str  # YYYYMMDDHHMMSS
    original_url: str
    status_code: str
    mime: str = ""
    digest: str = ""
    length: str = ""

    @property
    def date(self) -> str:
        try:
            return datetime.strptime(self.timestamp[:8], "%Y%m%d").strftime("%Y-%m-%d")
        except ValueError:
            return self.timestamp[:10]

    @property
    def archive_url(self) -> str:
        return f"https://web.archive.org/web/{self.timestamp}/{self.original_url}"


def cdx_query(domain_or_url: str, *, limit: int | None = None,
              date_from: str | None = None, date_to: str | None = None,
              collapse: str = "digest", match_type: str = "exact") -> list[Snapshot]:
    """Запросить CDX API. Возвращает список Snapshot."""
    params: dict[str, Any] = {
        "url": domain_or_url,
        "output": "json",
        "fl": "timestamp,original,statuscode,mimetype,digest,length",
        "matchType": match_type,
    }
    if collapse:
        params["collapse"] = collapse
    if limit:
        params["limit"] = str(limit)
    if date_from:
        params["from"] = date_from
    if date_to:
        params["to"] = date_to

    r = http_get(CDX_API, params=params)
    if r.status_code != 200 or not r.text.strip():
        return []
    try:
        data = r.json()
    except json.JSONDecodeError:
        return []
    if not data:
        return []
    rows = data[1:]  # skip header
    out = []
    for row in rows:
        if len(row) < 3:
            continue
        ts, orig, status, *rest = row + [""] * (6 - len(row))
        mime = rest[0] if len(rest) > 0 else ""
        digest = rest[1] if len(rest) > 1 else ""
        length = rest[2] if len(rest) > 2 else ""
        out.append(Snapshot(timestamp=ts, original_url=orig, status_code=status,
                            mime=mime, digest=digest, length=length))
    return out


def fetch_archived_html(snap: Snapshot) -> str:
    """Скачать HTML конкретного снапшота. Использует id_-modifier для raw HTML без Wayback toolbar."""
    raw_url = f"https://web.archive.org/web/{snap.timestamp}id_/{snap.original_url}"
    r = http_get(raw_url)
    return r.text if r.status_code == 200 else ""


# ─────────────────────────────────────────────────────────────────────────────
# COMMAND: history

def cmd_history(args: argparse.Namespace) -> int:
    domain = args.domain
    snaps = cdx_query(domain,
                      limit=args.limit,
                      date_from=args.date_from,
                      date_to=args.date_to,
                      match_type="domain" if args.full_domain else "exact")
    if not snaps:
        print(f"❌ Снапшотов не найдено для {domain}", file=sys.stderr)
        return 1

    print(f"# Wayback история: {domain}")
    print(f"Снапшотов: {len(snaps)}")
    print(f"Первый: {snaps[0].date}  →  Последний: {snaps[-1].date}\n")
    print(f"{'Дата':<12} {'Status':<7} {'MIME':<24} URL")
    print("-" * 100)
    for s in snaps:
        url = s.original_url[:50] + "…" if len(s.original_url) > 50 else s.original_url
        print(f"{s.date:<12} {s.status_code:<7} {s.mime[:24]:<24} {url}")

    if args.json:
        out_path = args.json
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump([asdict(s) for s in snaps], f, indent=2, ensure_ascii=False)
        print(f"\n💾 JSON сохранён: {out_path}")

    return 0


# ─────────────────────────────────────────────────────────────────────────────
# COMMAND: diff (DOM-diff title/H1/meta)

def extract_seo_fields(html: str) -> dict[str, str]:
    """Извлечь SEO-поля: title, H1, meta description, meta keywords, canonical, robots."""
    if not html:
        return {}
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(strip=True) if soup.title else ""
    h1_tags = [h.get_text(" ", strip=True) for h in soup.find_all("h1")]
    h1 = " | ".join(h1_tags) if h1_tags else ""

    def meta(name: str, by: str = "name") -> str:
        tag = soup.find("meta", attrs={by: name})
        if not tag:
            return ""
        content = tag.get("content")  # type: ignore[union-attr]
        return str(content).strip() if content else ""

    canonical_tag = soup.find("link", rel="canonical")
    canonical = ""
    if canonical_tag:
        href = canonical_tag.get("href")  # type: ignore[union-attr]
        canonical = str(href) if href else ""

    lang = ""
    if soup.html:
        lang_attr = soup.html.get("lang")  # type: ignore[union-attr]
        lang = str(lang_attr) if lang_attr else ""

    return {
        "title": title,
        "h1": h1,
        "meta_description": meta("description"),
        "meta_keywords": meta("keywords"),
        "og_title": meta("og:title", by="property"),
        "og_description": meta("og:description", by="property"),
        "canonical": canonical,
        "robots": meta("robots"),
        "lang": lang,
    }


def find_snapshot_near_date(url: str, target_date: str) -> Snapshot | None:
    """Найти снапшот ближайший к дате (YYYY-MM-DD или YYYYMMDD)."""
    target = re.sub(r"[^0-9]", "", target_date)[:8]
    if len(target) < 4:
        return None
    snaps = cdx_query(url, date_from=target[:4], date_to=str(int(target[:4]) + 1).zfill(4) + "1231",
                      collapse="digest")
    if not snaps:
        # расширим поиск
        snaps = cdx_query(url, collapse="digest", limit=200)
    if not snaps:
        return None
    # ближайший по timestamp
    target_dt = target.ljust(8, "0")
    best = min(snaps, key=lambda s: abs(int(s.timestamp[:8]) - int(target_dt)))
    return best


def cmd_diff(args: argparse.Namespace) -> int:
    url = args.url
    s1 = find_snapshot_near_date(url, args.date1)
    s2 = find_snapshot_near_date(url, args.date2)
    if not s1 or not s2:
        print(f"❌ Не найдены снапшоты для {url} рядом с датами {args.date1} / {args.date2}", file=sys.stderr)
        return 1

    print(f"# Diff: {url}")
    print(f"  Снимок 1: {s1.date}  ({s1.archive_url})")
    print(f"  Снимок 2: {s2.date}  ({s2.archive_url})\n")

    html1 = fetch_archived_html(s1)
    html2 = fetch_archived_html(s2)
    f1 = extract_seo_fields(html1)
    f2 = extract_seo_fields(html2)

    print(f"{'Поле':<22} {'Было ('+s1.date+')':<48} {'Стало ('+s2.date+')':<48}  Изменилось")
    print("-" * 130)
    changes = 0
    for key in ["title", "h1", "meta_description", "meta_keywords", "og_title", "og_description", "canonical", "robots", "lang"]:
        v1 = (f1.get(key) or "").replace("\n", " ")[:45]
        v2 = (f2.get(key) or "").replace("\n", " ")[:45]
        changed = "✅" if v1 != v2 else "  "
        if v1 != v2:
            changes += 1
        print(f"{key:<22} {v1:<48} {v2:<48}  {changed}")
    print(f"\nВсего изменений: {changes} из 9 SEO-полей")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump({
                "url": url,
                "snapshot_1": {"date": s1.date, "archive_url": s1.archive_url, "fields": f1},
                "snapshot_2": {"date": s2.date, "archive_url": s2.archive_url, "fields": f2},
                "changes_count": changes,
            }, f, indent=2, ensure_ascii=False)
        print(f"\n💾 JSON сохранён: {args.json}")
    return 0 if changes >= 0 else 1


# ─────────────────────────────────────────────────────────────────────────────
# COMMAND: restore — обёртка над waybackpack

def cmd_restore(args: argparse.Namespace) -> int:
    out_dir = args.out or f"./restored-{urlparse(args.url).netloc}"
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-m", "waybackpack", args.url, "-d", out_dir]
    if args.full_site:
        cmd.append("--uniques-only")
    if args.from_date:
        cmd.extend(["--from-date", args.from_date])
    if args.to_date:
        cmd.extend(["--to-date", args.to_date])

    print(f"# Restore: {args.url} → {out_dir}")
    print(f"  Команда: {' '.join(cmd)}\n")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        print(result.stdout)
        if result.returncode != 0:
            print(result.stderr, file=sys.stderr)
            return result.returncode
    except FileNotFoundError:
        print("❌ waybackpack не установлен. pip install waybackpack", file=sys.stderr)
        return 2
    except subprocess.TimeoutExpired:
        print("⏱  timeout 10 мин — большой сайт?", file=sys.stderr)
        return 3
    return 0


# ─────────────────────────────────────────────────────────────────────────────
# COMMAND: save — Save Page Now

def cmd_save(args: argparse.Namespace) -> int:
    try:
        import savepagenow as spn
    except ImportError:
        print("❌ savepagenow не установлен", file=sys.stderr)
        return 2
    try:
        archive_url = spn.capture(args.url)
        print(f"✅ Архивировано: {archive_url}")
        return 0
    except Exception as e:
        print(f"❌ Ошибка при архивации: {e}", file=sys.stderr)
        return 1


# ─────────────────────────────────────────────────────────────────────────────
# COMMAND: whois

def cmd_whois(args: argparse.Namespace) -> int:
    domain = args.domain.lower().strip()
    # Очистим до домена 2-го уровня
    parsed = urlparse(domain if "://" in domain else f"http://{domain}")
    netloc = parsed.netloc or domain
    netloc = netloc.split(":")[0]

    info = whois_lookup(netloc)
    if not info:
        print(f"❌ whois не вернул данные для {netloc}", file=sys.stderr)
        return 1

    print(f"# Whois: {netloc}\n")
    for k, v in info.items():
        print(f"  {k:<22} {v}")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(info, f, indent=2, ensure_ascii=False, default=str)
        print(f"\n💾 JSON сохранён: {args.json}")
    return 0


def whois_lookup(domain: str) -> dict[str, Any]:
    """Whois через python-whois с fallback на RDAP."""
    try:
        import whois as wlib  # type: ignore
        w = wlib.whois(domain)
        if w and (w.creation_date or w.registrar):
            return {
                "domain": domain,
                "registrar": _first(getattr(w, "registrar", None)),
                "creation_date": _first(getattr(w, "creation_date", None)),
                "expiration_date": _first(getattr(w, "expiration_date", None)),
                "updated_date": _first(getattr(w, "updated_date", None)),
                "name_servers": ", ".join(sorted(set((w.name_servers or [])))) if isinstance(w.name_servers, list) else str(w.name_servers or ""),
                "status": ", ".join(w.status) if isinstance(w.status, list) else str(w.status or ""),
                "country": _first(getattr(w, "country", None)),
                "org": _first(getattr(w, "org", None)),
            }
    except Exception:
        pass

    # RDAP fallback (rdap.org)
    try:
        r = http_get(f"https://rdap.org/domain/{domain}", timeout=15)
        if r.status_code == 200:
            d = r.json()
            return _parse_rdap(d, domain)
    except Exception:
        pass
    return {}


def _first(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, list):
        return str(v[0]) if v else ""
    return str(v)


def _parse_rdap(data: dict, domain: str) -> dict[str, Any]:
    events = {e.get("eventAction"): e.get("eventDate") for e in data.get("events", [])}
    return {
        "domain": domain,
        "registrar": next((e.get("vcardArray", [None, []])[1][1][3] for e in data.get("entities", []) if "registrar" in e.get("roles", []) and e.get("vcardArray")), ""),
        "creation_date": events.get("registration", ""),
        "expiration_date": events.get("expiration", ""),
        "updated_date": events.get("last changed", ""),
        "name_servers": ", ".join(ns.get("ldhName", "") for ns in data.get("nameservers", [])),
        "status": ", ".join(data.get("status", [])),
        "source": "RDAP",
    }


# ─────────────────────────────────────────────────────────────────────────────
# COMMAND: intel — комплексный отчёт

def cmd_intel(args: argparse.Namespace) -> int:
    domain = args.domain.lower().strip()
    parsed = urlparse(domain if "://" in domain else f"http://{domain}")
    netloc = (parsed.netloc or domain).split(":")[0]

    print(f"# Domain Intel: {netloc}")
    print(f"Дата отчёта: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    # 1. Whois
    print("## 🆔 Whois\n")
    w = whois_lookup(netloc)
    if w:
        for k in ("registrar", "creation_date", "expiration_date", "updated_date", "country", "org"):
            v = w.get(k, "")
            if v:
                print(f"  {k:<20} {v}")
        # возраст домена
        age = _age_years(w.get("creation_date"))
        if age is not None:
            print(f"  {'age_years':<20} {age:.1f}")
    else:
        print("  ❌ whois недоступен")

    # 2. Wayback summary
    print("\n## 🕰  Wayback история\n")
    snaps = cdx_query(netloc, collapse="digest", limit=1000, match_type="domain")
    if not snaps:
        snaps = cdx_query(netloc, collapse="digest", limit=1000)
    if snaps:
        first = snaps[0].date
        last = snaps[-1].date
        years = sorted({s.timestamp[:4] for s in snaps})
        print(f"  Снапшотов:           {len(snaps)}")
        print(f"  Первый:              {first}")
        print(f"  Последний:           {last}")
        print(f"  Активные годы:       {', '.join(years)}")
    else:
        print("  ❌ Wayback не знает этот домен (возможно, новый или robots.txt блокирует)")

    # 3. DNS текущий
    print("\n## 🌐 DNS (текущий)\n")
    for record in ("A", "MX", "NS", "TXT"):
        out = _dig(netloc, record)
        if out:
            print(f"  {record:<5} {out}")

    # 4. HTTP статус
    print("\n## 🩺 HTTP статус\n")
    try:
        r = http_get(f"https://{netloc}", timeout=10)
        print(f"  HTTPS  {r.status_code}  {r.headers.get('Server', '')}")
    except Exception as e:
        print(f"  HTTPS  ❌ {e}")

    if args.json:
        report = {
            "domain": netloc,
            "report_date": datetime.now().isoformat(),
            "whois": w,
            "wayback": {
                "count": len(snaps) if snaps else 0,
                "first": snaps[0].date if snaps else "",
                "last": snaps[-1].date if snaps else "",
                "active_years": sorted({s.timestamp[:4] for s in snaps}) if snaps else [],
            },
        }
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        print(f"\n💾 JSON сохранён: {args.json}")
    return 0


def _age_years(creation: Any) -> float | None:
    if not creation:
        return None
    if isinstance(creation, list):
        creation = creation[0] if creation else None
    if not creation:
        return None
    try:
        if isinstance(creation, str):
            # Попробуем разные форматы
            for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
                try:
                    dt = datetime.strptime(creation[:len(fmt) + 4], fmt)
                    break
                except ValueError:
                    continue
            else:
                return None
        else:
            dt = creation
        return (datetime.now() - dt).days / 365.25
    except Exception:
        return None


def _dig(domain: str, record: str) -> str:
    try:
        result = subprocess.run(["dig", "+short", record, domain], capture_output=True, text=True, timeout=10)
        return result.stdout.strip().replace("\n", "; ")[:120]
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""


# ─────────────────────────────────────────────────────────────────────────────
# COMMAND: expired-search (Playwright stub — TODO)

def cmd_expired_search(args: argparse.Namespace) -> int:
    print("# Expired Domains Search\n")
    print(f"  Niche:    {args.niche or '—'}")
    print(f"  TLD:      {args.tld}")
    print(f"  Min age:  {args.min_age}")
    print(f"  Max price: {args.max_price}\n")
    print("⚠️  Playwright-парсер expired.ru / expireddomains.net / xpire.ru находится в разработке.")
    print("    Для текущей сессии — ручной чеклист площадок:")
    print()
    queries = [
        ("expired.ru", f"https://expired.ru/?zone={args.tld}"),
        ("expireddomains.net", f"https://www.expireddomains.net/expired-domains/?ftlds[]={args.tld}"),
        ("xpire.ru", "https://xpire.ru/dropping/"),
        ("reg.ru аукцион", "https://www.reg.ru/domain/new/rereg"),
        ("webnames.ru", "https://www.webnames.ru/domains/deleted/"),
        ("Telderi", "https://telderi.ru/domains/"),
    ]
    for name, url in queries:
        print(f"  • {name:<22} {url}")
    print("\nПосле релиза Playwright-модуля — будет автоматический парсинг с фильтрами.")
    return 0


# ─────────────────────────────────────────────────────────────────────────────
# COMMAND: bulk

def cmd_bulk(args: argparse.Namespace) -> int:
    import yaml
    with open(args.yaml, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    domains = cfg.get("domains") if isinstance(cfg, dict) else cfg
    if not domains:
        print(f"❌ В {args.yaml} нет ключа 'domains' и список пуст", file=sys.stderr)
        return 1

    out_csv = args.out or "./bulk-report.csv"
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["domain", "wayback_count", "wayback_first", "wayback_last",
                         "whois_creation", "whois_expiration", "whois_registrar", "age_years"])
        for d in domains:
            try:
                snaps = cdx_query(d, collapse="digest", limit=1000, match_type="domain")
                w = whois_lookup(d) if not args.skip_whois else {}
                writer.writerow([
                    d,
                    len(snaps) if snaps else 0,
                    snaps[0].date if snaps else "",
                    snaps[-1].date if snaps else "",
                    w.get("creation_date", ""),
                    w.get("expiration_date", ""),
                    w.get("registrar", ""),
                    f"{_age_years(w.get('creation_date')):.1f}" if _age_years(w.get('creation_date')) else "",
                ])
                print(f"  ✓ {d}")
            except Exception as e:
                print(f"  ✗ {d}: {e}", file=sys.stderr)
                writer.writerow([d, "ERROR", str(e), "", "", "", "", ""])
            time.sleep(RATE_LIMIT_SLEEP)

    print(f"\n💾 Сохранено: {out_csv}")
    return 0


# ─────────────────────────────────────────────────────────────────────────────
# COMMAND: monitor (cron-режим)

def cmd_monitor(args: argparse.Namespace) -> int:
    import yaml
    with open(args.yaml, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    state_file = Path(args.yaml).with_suffix(".state.json")
    prev_state: dict[str, dict] = {}
    if state_file.exists():
        prev_state = json.loads(state_file.read_text(encoding="utf-8"))

    new_state: dict[str, dict] = {}
    alerts: list[str] = []

    urls = cfg.get("urls") if isinstance(cfg, dict) else cfg
    for url in urls or []:
        snaps = cdx_query(url, collapse="digest", limit=10)
        if not snaps:
            continue
        latest = snaps[-1]
        html = fetch_archived_html(latest)
        fields = extract_seo_fields(html)
        new_state[url] = {
            "last_snapshot": latest.timestamp,
            "fields": fields,
        }
        prev = prev_state.get(url, {})
        if prev and prev.get("fields"):
            for k in ("title", "h1", "meta_description"):
                if prev["fields"].get(k) != fields.get(k):
                    alerts.append(f"{url} — {k}: '{prev['fields'].get(k, '')[:60]}' → '{fields.get(k, '')[:60]}'")
        time.sleep(RATE_LIMIT_SLEEP)

    state_file.write_text(json.dumps(new_state, indent=2, ensure_ascii=False), encoding="utf-8")

    if alerts:
        print(f"# Monitor — найдено {len(alerts)} изменений\n")
        for a in alerts:
            print(f"  🔔 {a}")
        if args.alert_tg:
            tg_send_alerts(alerts)
    else:
        print("# Monitor — изменений нет")
    return 0


def tg_send_alerts(alerts: list[str]) -> None:
    """Отправить алерты в TG через ~/.claude/scripts/tg-send.sh team."""
    msg = "🔔 domain-intel monitor:\n\n" + "\n".join(f"• {a}" for a in alerts[:20])
    if len(alerts) > 20:
        msg += f"\n\n…и ещё {len(alerts) - 20} изменений"
    tg_script = Path.home() / ".claude/scripts/tg-send.sh"
    if tg_script.exists():
        try:
            subprocess.run([str(tg_script), "team", msg], timeout=30, check=False)
        except Exception as e:
            print(f"⚠️ TG send failed: {e}", file=sys.stderr)


# ─────────────────────────────────────────────────────────────────────────────
# Argparse / main

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="domain-intel", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    h = sub.add_parser("history", help="Все снапшоты Wayback по домену/URL")
    h.add_argument("domain")
    h.add_argument("--limit", type=int, default=None)
    h.add_argument("--from", dest="date_from", default=None, help="YYYY или YYYYMMDD")
    h.add_argument("--to", dest="date_to", default=None)
    h.add_argument("--full-domain", action="store_true", help="matchType=domain (все URL)")
    h.add_argument("--json", default=None, help="Сохранить результат в JSON-файл")

    d = sub.add_parser("diff", help="Diff title/H1/meta между двумя датами")
    d.add_argument("url")
    d.add_argument("date1", help="YYYY-MM-DD")
    d.add_argument("date2", help="YYYY-MM-DD")
    d.add_argument("--json", default=None)

    r = sub.add_parser("restore", help="Скачать страницу/сайт из Wayback (waybackpack)")
    r.add_argument("url")
    r.add_argument("--full-site", action="store_true")
    r.add_argument("--out", default=None)
    r.add_argument("--from-date", default=None)
    r.add_argument("--to-date", default=None)

    s = sub.add_parser("save", help="Отправить URL в Save Page Now")
    s.add_argument("url")

    w = sub.add_parser("whois", help="Whois через python-whois + RDAP fallback")
    w.add_argument("domain")
    w.add_argument("--json", default=None)

    i = sub.add_parser("intel", help="Комплексный отчёт по домену")
    i.add_argument("domain")
    i.add_argument("--json", default=None)

    e = sub.add_parser("expired-search", help="Поиск истекающих/освобождающихся доменов")
    e.add_argument("--niche", default=None)
    e.add_argument("--tld", default="ru")
    e.add_argument("--min-age", type=int, default=0)
    e.add_argument("--max-price", type=int, default=10000)

    b = sub.add_parser("bulk", help="Bulk-аудит списка доменов из YAML → CSV")
    b.add_argument("yaml")
    b.add_argument("--out", default=None)
    b.add_argument("--skip-whois", action="store_true")

    m = sub.add_parser("monitor", help="Cron-мониторинг: алерт при изменениях")
    m.add_argument("yaml")
    m.add_argument("--alert-tg", action="store_true")

    return p


HANDLERS = {
    "history": cmd_history,
    "diff": cmd_diff,
    "restore": cmd_restore,
    "save": cmd_save,
    "whois": cmd_whois,
    "intel": cmd_intel,
    "expired-search": cmd_expired_search,
    "bulk": cmd_bulk,
    "monitor": cmd_monitor,
}


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = HANDLERS[args.cmd]
    try:
        return handler(args)
    except KeyboardInterrupt:
        print("\n⏹  прервано", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
