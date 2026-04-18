#!/usr/bin/env python3
"""
MODX CMS Remote Editor — правка страниц через SSH/FTP.

Использование:
  python3 ~/.claude/scripts/modx-edit.py --site ant-partners.ru --list           # список страниц
  python3 ~/.claude/scripts/modx-edit.py --site ant-partners.ru --page about     # скачать страницу
  python3 ~/.claude/scripts/modx-edit.py --site ant-partners.ru --page about --edit "old text" "new text"
  python3 ~/.claude/scripts/modx-edit.py --site ant-partners.ru --page about --upload  # загрузить обратно
  python3 ~/.claude/scripts/modx-edit.py --site ant-partners.ru --page about --screenshot  # скриншот до/после

Для ANT Partners и других клиентов на MODX.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

BASE = Path("/Users/antonk/artvision-data")
TOKENS = BASE / "tokens.json"
LOCAL_CACHE = Path("/tmp/modx-cache")

# Конфигурация сайтов
SITES = {
    "ant-partners.ru": {
        "ssh": None,  # нет SSH
        "ftp_host": "ant-partners.ru",
        "ftp_user": None,  # из tokens.json
        "ftp_pass": None,  # из tokens.json
        "web_root": "/www/",
        "template_dir": "/www/core/components/",
        "url": "https://ant-partners.ru",
    }
}


def load_credentials(site):
    """Загрузить credentials из tokens.json."""
    try:
        data = json.loads(TOKENS.read_text())
        # Ищем по ключу сайта
        for key in [site, site.replace(".", "_"), site.replace("-", "_").replace(".", "_")]:
            if key in data:
                return data[key]
        # Ищем в clients
        if "clients" in data:
            for k, v in data["clients"].items():
                if site in str(v):
                    return v
    except Exception as e:
        print(f"[WARN] tokens.json: {e}")
    return {}


def ftp_list(config, path="/"):
    """Список файлов по FTP."""
    host = config["ftp_host"]
    user = config.get("ftp_user", "")
    passwd = config.get("ftp_pass", "")
    cmd = f"curl -s ftp://{user}:{passwd}@{host}{path} --list-only"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    return result.stdout.strip().split("\n") if result.returncode == 0 else []


def ftp_download(config, remote_path, local_path):
    """Скачать файл по FTP."""
    host = config["ftp_host"]
    user = config.get("ftp_user", "")
    passwd = config.get("ftp_pass", "")
    cmd = f"curl -s ftp://{user}:{passwd}@{host}{remote_path} -o {local_path}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    return result.returncode == 0


def ftp_upload(config, local_path, remote_path):
    """Загрузить файл по FTP."""
    host = config["ftp_host"]
    user = config.get("ftp_user", "")
    passwd = config.get("ftp_pass", "")
    cmd = f"curl -s -T {local_path} ftp://{user}:{passwd}@{host}{remote_path}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    return result.returncode == 0


def ssh_edit(config, remote_path, old_text, new_text):
    """Правка файла через SSH (если есть доступ)."""
    ssh = config.get("ssh")
    if not ssh:
        return False

    # Бэкап
    subprocess.run(
        ["ssh", ssh, f"cp {remote_path} {remote_path}.bak"],
        capture_output=True, timeout=15
    )

    # Замена через sed
    old_escaped = old_text.replace("/", "\\/").replace("'", "\\'")
    new_escaped = new_text.replace("/", "\\/").replace("'", "\\'")
    cmd = f"sed -i 's/{old_escaped}/{new_escaped}/g' {remote_path}"
    result = subprocess.run(["ssh", ssh, cmd], capture_output=True, text=True, timeout=15)
    return result.returncode == 0


def take_screenshot(url, output_path):
    """Скриншот через Playwright."""
    script = f"""
import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={{"width": 1440, "height": 900}})
        await page.goto("{url}", wait_until="networkidle", timeout=30000)
        await page.screenshot(path="{output_path}", type="jpeg", quality=70, full_page=True)
        await browser.close()
asyncio.run(main())
"""
    subprocess.run(["python3", "-c", script], capture_output=True, timeout=60)
    return Path(output_path).exists()


def main():
    parser = argparse.ArgumentParser(description="MODX CMS Remote Editor")
    parser.add_argument("--site", "-s", required=True, help="Домен сайта")
    parser.add_argument("--list", "-l", action="store_true", help="Список страниц")
    parser.add_argument("--page", "-p", help="Страница (slug или путь)")
    parser.add_argument("--edit", "-e", nargs=2, metavar=("OLD", "NEW"), help="Замена текста")
    parser.add_argument("--upload", "-u", action="store_true", help="Загрузить обратно")
    parser.add_argument("--screenshot", action="store_true", help="Скриншот")
    parser.add_argument("--dry-run", action="store_true", help="Без реальных изменений")
    args = parser.parse_args()

    site = args.site
    config = SITES.get(site, {"ftp_host": site, "web_root": "/www/", "url": f"https://{site}"})

    # Подгрузить credentials
    creds = load_credentials(site)
    if creds:
        config["ftp_user"] = creds.get("ftp_user", creds.get("user", ""))
        config["ftp_pass"] = creds.get("ftp_pass", creds.get("password", ""))
        if "ssh" in creds:
            config["ssh"] = creds["ssh"]

    LOCAL_CACHE.mkdir(parents=True, exist_ok=True)

    if args.list:
        print(f"Файлы на {site}:")
        files = ftp_list(config, config.get("web_root", "/"))
        for f in files:
            print(f"  {f}")
        return

    if args.page:
        page_slug = args.page
        # Определить путь к файлу
        remote_path = f"{config['web_root']}{page_slug}.html"
        local_path = LOCAL_CACHE / f"{site}_{page_slug}.html"

        if args.screenshot:
            url = f"{config['url']}/{page_slug}"
            out = f"/tmp/modx-{site}-{page_slug}.jpg"
            print(f"[...] Скриншот {url}...")
            if take_screenshot(url, out):
                print(f"[OK] {out}")
            else:
                print("[ERR] Не удалось сделать скриншот")
            return

        if args.edit:
            old_text, new_text = args.edit
            if args.dry_run:
                print(f"[DRY] Заменить '{old_text}' → '{new_text}' в {remote_path}")
                return

            # Скачать → заменить → загрузить
            print(f"[...] Скачиваю {remote_path}...")
            if not ftp_download(config, remote_path, str(local_path)):
                # Попробовать SSH
                if config.get("ssh"):
                    subprocess.run(
                        ["scp", f"{config['ssh']}:{remote_path}", str(local_path)],
                        capture_output=True, timeout=15
                    )

            if local_path.exists():
                content = local_path.read_text()
                if old_text in content:
                    # Бэкап
                    backup = local_path.with_suffix(".bak")
                    backup.write_text(content)

                    new_content = content.replace(old_text, new_text)
                    local_path.write_text(new_content)
                    count = content.count(old_text)
                    print(f"[OK] Заменено {count} вхождений")

                    if args.upload or True:  # always upload after edit
                        print(f"[...] Загружаю {remote_path}...")
                        if ftp_upload(config, str(local_path), remote_path):
                            print("[OK] Загружено")
                        elif config.get("ssh"):
                            subprocess.run(
                                ["scp", str(local_path), f"{config['ssh']}:{remote_path}"],
                                capture_output=True, timeout=15
                            )
                            print("[OK] Загружено через SSH")
                else:
                    print(f"[WARN] Текст '{old_text}' не найден")
            else:
                print(f"[ERR] Не удалось скачать {remote_path}")
            return

        # Просто скачать
        print(f"[...] Скачиваю {remote_path}...")
        if ftp_download(config, remote_path, str(local_path)):
            print(f"[OK] Сохранено: {local_path}")
            print(f"     Размер: {local_path.stat().st_size} bytes")
        else:
            print(f"[ERR] Не удалось скачать")

    if not args.list and not args.page:
        parser.print_help()


if __name__ == "__main__":
    main()
