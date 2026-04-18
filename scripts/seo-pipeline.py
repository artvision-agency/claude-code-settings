#!/usr/bin/env python3
"""
SEO Pipeline — единый запуск всех SEO-инструментов.

Использование:
  python3 ~/.claude/scripts/seo-pipeline.py --all                    # все инструменты
  python3 ~/.claude/scripts/seo-pipeline.py --backlinks              # только мониторинг бэклинков
  python3 ~/.claude/scripts/seo-pipeline.py --expired-domains        # поиск дропов
  python3 ~/.claude/scripts/seo-pipeline.py --serp --query "запрос"  # SERP анализ
  python3 ~/.claude/scripts/seo-pipeline.py --geo --domain site.com  # GEO аудит
  python3 ~/.claude/scripts/seo-pipeline.py --status                 # статус всех пайплайнов
"""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BASE = Path("/Users/antonk/artvision-data")
SCRIPTS = BASE / "scripts" / "seo-pipeline"
CRON_CONFIGS = BASE / "scripts" / "seo-pipeline" / "cron-configs"


def run_script(name, script_path, args=None):
    """Запустить скрипт SEO pipeline."""
    if not script_path.exists():
        print(f"[SKIP] {name}: {script_path} не найден")
        return False

    cmd = ["python3", str(script_path)]
    if args:
        cmd.extend(args)

    print(f"\n{'='*60}")
    print(f"[RUN] {name}")
    print(f"{'='*60}")

    try:
        result = subprocess.run(cmd, timeout=300, capture_output=False)
        if result.returncode == 0:
            print(f"[OK] {name} завершён")
            return True
        else:
            print(f"[ERR] {name} завершён с ошибкой (code {result.returncode})")
            return False
    except subprocess.TimeoutExpired:
        print(f"[TIMEOUT] {name} превышен лимит 5 мин")
        return False
    except Exception as e:
        print(f"[ERR] {name}: {e}")
        return False


def find_script(name):
    """Найти скрипт в нескольких местах."""
    candidates = [
        SCRIPTS / f"{name}.py",
        BASE / "scripts" / f"{name}.py",
        BASE / "scripts" / "seo-pipeline" / f"{name}.py",
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]  # вернём первый для сообщения об ошибке


def show_status():
    """Показать статус всех пайплайнов."""
    scripts = {
        "backlink-monitor": "Мониторинг бэклинков конкурентов",
        "expired-domains": "Поиск дропнутых доменов",
        "serp-crawler": "SERP краулер (DataForSEO)",
        "geo-keyword-prioritizer": "GEO приоритизация ключей",
        "parasitic-publisher": "Паразитное SEO (vc.ru, Dzen)",
    }

    print(f"\nSEO Pipeline Status — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    print(f"{'Скрипт':<30} {'Статус':<12} {'Путь'}")
    print("-" * 80)

    for name, desc in scripts.items():
        path = find_script(name)
        status = "OK" if path.exists() else "NOT FOUND"
        print(f"{desc:<30} {status:<12} {path}")

    # Проверить cron configs
    if CRON_CONFIGS.exists():
        configs = list(CRON_CONFIGS.glob("*.yaml")) + list(CRON_CONFIGS.glob("*.yml"))
        print(f"\nCron configs: {len(configs)} файлов в {CRON_CONFIGS}")
        for c in configs:
            print(f"  - {c.name}")
    else:
        print(f"\nCron configs: {CRON_CONFIGS} не найден")


def main():
    parser = argparse.ArgumentParser(description="SEO Pipeline — единый запуск")
    parser.add_argument("--all", "-a", action="store_true", help="Запустить все инструменты")
    parser.add_argument("--backlinks", "-b", action="store_true", help="Мониторинг бэклинков")
    parser.add_argument("--expired-domains", "-e", action="store_true", help="Поиск дропов")
    parser.add_argument("--serp", "-s", action="store_true", help="SERP краулер")
    parser.add_argument("--geo", "-g", action="store_true", help="GEO аудит")
    parser.add_argument("--parasitic", "-p", action="store_true", help="Паразитное SEO")
    parser.add_argument("--query", "-q", help="Поисковый запрос (для SERP)")
    parser.add_argument("--domain", "-d", help="Домен (для GEO/backlinks)")
    parser.add_argument("--status", action="store_true", help="Статус пайплайнов")
    args = parser.parse_args()

    if args.status:
        show_status()
        return

    if not any([args.all, args.backlinks, args.expired_domains, args.serp, args.geo, args.parasitic]):
        parser.print_help()
        return

    results = {}
    start = datetime.now()

    if args.all or args.backlinks:
        extra = ["--domain", args.domain] if args.domain else []
        results["backlinks"] = run_script("Backlink Monitor", find_script("backlink-monitor"), extra)

    if args.all or args.expired_domains:
        results["expired"] = run_script("Expired Domains", find_script("expired-domains"))

    if args.all or args.serp:
        extra = ["--query", args.query] if args.query else []
        results["serp"] = run_script("SERP Crawler", find_script("serp-crawler"), extra)

    if args.all or args.geo:
        extra = ["--domain", args.domain] if args.domain else []
        results["geo"] = run_script("GEO Prioritizer", find_script("geo-keyword-prioritizer"), extra)

    if args.all or args.parasitic:
        results["parasitic"] = run_script("Parasitic Publisher", find_script("parasitic-publisher"))

    # Итог
    elapsed = (datetime.now() - start).total_seconds()
    ok = sum(1 for v in results.values() if v)
    total = len(results)

    print(f"\n{'='*60}")
    print(f"ИТОГ: {ok}/{total} успешно за {elapsed:.0f}с")
    for name, status in results.items():
        print(f"  {'[OK]' if status else '[ERR]'} {name}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
