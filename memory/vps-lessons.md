# VPS Lessons

### devops-agent: НИКОГДА не хардкодить пути (2026-02-20)
- **Проблема:** 4 скрипта в devops-agent хардкодили `/Users/antonk/...`. На VPS = FileNotFoundError.
- **Сломано:** health.py, telegram_notifier.py, token_monitor.py, backup_controller.py, settings.yaml
- **Фикс:** Создан `env_detect.py` — автодетект Mac vs VPS, экспортирует `TOKENS_PATH` и `BASE`.
- **Правило:** При создании скриптов для devops-agent → `from env_detect import TOKENS_PATH`, НЕ хардкодить.
- **Дополнительно:** settings.yaml тоже имел старый IP 109.71.242.6 → заменён на 80.90.181.152.

### VPS миграция — уроки (2026-02-17)
- Node.js НЕ подхватывает SOCKS5 через HTTPS_PROXY — нужен proxychains4
- WARP бесполезен для обхода геоблока из РФ — anycast → ближайший PoP (loc=RU)
- Проще перенести VPS в EU чем городить туннели
- PM2 cluster mode + dotenv: нужен явный `--cwd`
- Timeweb NL = тот же прайс что RU (4/8/80 = 1210₽)
- twc CLI: `/Library/Frameworks/Python.framework/Versions/3.14/bin/twc`
- Старый VPS IP (109.71.242.6) — УДАЛЁН
