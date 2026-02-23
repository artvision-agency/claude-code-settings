## Регистрация внешних сервисов

### Паттерн
При регистрации на новых сервисах (API, SaaS) использовать:
- **Email:** adw.artvision.pro@gmail.com (рабочий аккаунт)
- **Имя:** Artvision Agency
- **Все ключи → tokens.json** в соответствующую секцию
- При регистрации сохранять: email, пароль (в tokens.json), API key, план (free/paid)

### Сервисы для регистрации
- **remove.bg** — удаление фона с фото (есть free tier: 50 calls/month)
  - Статус: НЕ зарегистрирован
  - Нужен для: обработка фото клиентов

### Шаблон записи в tokens.json
```json
"service_name": {
  "email": "adw.artvision.pro@gmail.com",
  "api_key": "...",
  "plan": "free",
  "limits": "50 calls/month",
  "registered": "2026-02-23"
}
```
