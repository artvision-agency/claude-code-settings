# ArtVision deploy URL guarantee

Любой деплой HTML в `/var/www/artvision` должен завершаться живой публичной ссылкой.

## Обязательный путь

Для HTML-страниц ArtVision используй wrapper:

```bash
/Users/antonk/.claude/scripts/safe-deploy-html.sh <local_html> /var/www/artvision/<path>/index.html
```

Для внутренних отчётов `_priv-*` допускается:

```bash
FACTCHECK_SKIP=1 /Users/antonk/.claude/scripts/safe-deploy-html.sh <local_html> /var/www/artvision/_priv-<name>/index.html
```

## Формат ответа после деплоя

Первая строка ответа пользователю:

```text
Live URL: https://artvision.pro/<path>/
```

Ниже кратко:

- HTTP-код.
- Content-Length или размер файла.
- Что именно было опубликовано.

## Запрещённый паттерн

Не заканчивать деплой сообщением вида "залил", "готово", "scp выполнен" без публичной ссылки.

Если `scp` прошёл, но `curl -I` не вернул `HTTP 200`, деплой считается незавершённым.
