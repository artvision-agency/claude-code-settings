---
name: hostland-fm
description: "Работа с файлами на Hostland хостинге через Playwright + elFinder iframe API. Чтение, запись, навигация по директориям. Используй когда нужно редактировать файлы на сервере клиента с Hostland (avto.world и др.) без SSH/FTP. Триггеры: hostland, файл на сервере, elFinder, правка на хостинге, залить файл, изменить robots.txt, редактировать шаблон"
---

# Hostland File Manager — Playwright + elFinder

## Когда использовать

- Нужно прочитать/изменить файл на сервере клиента с Hostland
- SSH закрыт (порт 22), FTP не работает или пароль отвергнут
- Единственный доступ — через панель `panel.hostland.ru`

## Предварительные условия

1. **Закрыть Chrome** — Playwright конфликтует с запущенным Chrome
```bash
osascript -e 'tell application "Google Chrome" to quit' 2>/dev/null || true
```

2. **Учётные данные** — из `clients/[name]/access.md`:
   - Логин: `host1451713` (для avto.world)
   - Пароль: из access.md

## Алгоритм (Playwright MCP)

### 1. Логин в панель Hostland

```python
await page.goto("https://panel.hostland.ru")
await page.fill('input[name="login"]', LOGIN)
await page.fill('input[name="password"]', PASSWORD)
await page.keyboard.press("Enter")
await page.wait_for_load_state("networkidle")
```

### 2. Открыть файловый менеджер

```python
# Навигация через hash (не кликом!)
await page.evaluate("window.location.hash = '#fm'")
await asyncio.sleep(3)
```

### 3. Найти iframe elFinder

```python
fm_frame = None
for f in page.frames:
    if f != page.main_frame and 'fm' in f.url:
        fm_frame = f
        break
# ВАЖНО: все операции elFinder — ТОЛЬКО через fm_frame, НЕ page!
```

### 4. Навигация по директориям

```python
# Последовательно открываем каждую папку
for dirname in ['avto.world', 'htdocs', 'www']:
    await fm_frame.evaluate(f"""() => {{
        const ef = jQuery('.elfinder').elfinder('instance');
        const files = ef.files();
        for (const hash in files) {{
            if (files[hash].name === '{dirname}' && files[hash].mime === 'directory') {{
                ef.exec('open', hash);
                break;
            }}
        }}
    }}""")
    await asyncio.sleep(2)
```

### 5. Чтение файла

```python
# Сначала найти hash файла
file_hash = await fm_frame.evaluate("""() => {
    const ef = jQuery('.elfinder').elfinder('instance');
    const files = ef.files();
    for (const hash in files) {
        if (files[hash].name === 'robots.txt') return hash;
    }
    return null;
}""")

# Прочитать содержимое
content = await fm_frame.evaluate("""(hash) => {
    return new Promise((resolve) => {
        const ef = jQuery('.elfinder').elfinder('instance');
        ef.request({data: {cmd: 'get', target: hash}})
          .done(data => resolve(data.content));
    });
}""", file_hash)
```

### 6. Запись файла

```python
await fm_frame.evaluate("""(args) => {
    return new Promise((resolve) => {
        const ef = jQuery('.elfinder').elfinder('instance');
        ef.request({data: {cmd: 'put', target: args.hash, content: args.content}})
          .done(() => resolve(true));
    });
}""", {"hash": file_hash, "content": new_content})
```

## Типичные задачи

| Задача | Путь на сервере |
|--------|-----------------|
| robots.txt | `/www/robots.txt` |
| .htaccess | `/www/.htaccess` |
| MODX config | `/www/core/config/config.inc.php` |
| Шаблоны | `/www/core/components/...` |
| Контент (HTML) | `/www/assets/...` |

## Ошибки и решения

| Проблема | Решение |
|----------|---------|
| `jQuery is not defined` | Используешь `page.evaluate` вместо `fm_frame.evaluate` |
| Файл не найден | Проверь директорию — файлы видны только в текущей открытой папке |
| Timeout на evaluate | Увеличить sleep между навигациями, elFinder загружает файлы async |
| `Cannot read property of null` | Hash файла не найден — проверь имя (case-sensitive) |
| Chrome conflict | `osascript -e 'tell application "Google Chrome" to quit'` |

## Бэкап ПЕРЕД изменением

**ОБЯЗАТЕЛЬНО:** перед любой записью — прочитать файл и сохранить бэкап:
```
clients/[name]/backups/YYYY-MM-DD/filename.ext
```

## Document root для известных клиентов

| Клиент | Document root |
|--------|---------------|
| avto.world | `/home/host1451713/avto.world/htdocs/www/` |
