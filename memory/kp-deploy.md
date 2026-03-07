# Деплой КП — стандартный процесс

## URL-паттерн
```
https://artvision.pro/kp/[имя-проекта]/
```
Пример: `https://artvision.pro/kp/ortodental/`

## Шаги

1. **HTML** создаётся в `presales/[клиент]/kp/` → коммит в git
2. **FTP деплой** через lftp на artvision.pro:
   - Credentials: `tokens.json → artvision_pro.ftp`
   - Host: `vh254.timeweb.ru`
   - Path: `/artvisionver3/public_html/kp/[имя-проекта]/index.html`
3. **X-Robots-Tag: noindex** — `.htaccess` в `/kp/` (уже на месте, не нужно повторно)
4. **Ссылка клиенту** — `https://artvision.pro/kp/[имя-проекта]/`

## FTP-команды (lftp)
```python
import json, subprocess
with open('tokens.json') as f:
    ftp = json.load(f)['artvision_pro']['ftp']

cmds = f"""
mkdir -p {ftp['path']}/kp/[project]
put local.html -o {ftp['path']}/kp/[project]/index.html
exit
"""
subprocess.run(['lftp', '-u', f"{ftp['user']},{ftp['password']}", ftp['host']], input=cmds, text=True)
```

## Контакты в КП
- Телефон: +7 (911) 086-18-88 (Антон)
- Telegram: @antonkamer
- Сайт: artvision.pro

## Хостинг artvision.pro
- **Timeweb shared hosting** (НЕ VPS)
- IP: 92.53.96.201
- SSH нет (только FTP)
- WordPress + Apache (.htaccess работает)
- DNS: reg.ru (ns1.reg.ru, ns2.reg.ru)

## Важно
- `.htaccess` с noindex уже лежит в `/kp/` — при новых КП не нужно повторно загружать
- Все КП деплоятся по этому паттерну — СТАНДАРТНЫЙ процесс
- Не трогать DNS, не трогать nginx VPS — это shared hosting
