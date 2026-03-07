---
name: client-monitor
description: "Мониторинг клиентов: позиции Topvisor, SEO-динамика, бриф для переговоров. Триггеры: 'мониторинг', 'позиции клиентов', 'динамика', 'бриф для звонка', 'client monitor'"
disable-model-invocation: true
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - WebFetch
---

# Client SEO Monitor

## Что делает
1. Запускает проверку позиций клиентов в Topvisor
2. Собирает результаты и анализирует динамику (рост/падение/стабильность)
3. Генерирует бриф для переговоров с клиентом

## Шаги выполнения

### 1. Запуск мониторинга
```bash
cd /Users/antonk/artvision-data
python3 scripts/client_monitor.py --check --report --brief
```

### 2. Если позиции ещё не собрались
Проверка Topvisor идёт 5-30 минут. Повтори через 10 мин:
```bash
python3 scripts/client_monitor.py --report --brief
```

### 3. Добавление нового клиента
Отредактируй `MONITORED_CLIENTS` в `scripts/client_monitor.py`:
```python
"client-slug": {
    "site": "domain.ru",
    "topvisor_id": 12345678,      # из Topvisor
    "region_index": 3,             # СПб=3, Москва=1
    "region_name": "Санкт-Петербург",
    "cms": "WordPress",
    "contact": None,               # TG ID
}
```

### 4. Cron-запуск (еженедельно)
```bash
# Проверка позиций каждый понедельник 8:00
0 8 * * 1 cd /Users/antonk/artvision-data && /usr/bin/python3 scripts/client_monitor.py --check 2>&1 | logger -t client-monitor

# Отчёт каждый понедельник 9:00 (через час после проверки)
0 9 * * 1 cd /Users/antonk/artvision-data && /usr/bin/python3 scripts/client_monitor.py --report --brief 2>&1 | logger -t client-monitor
```

### 5. Интерпретация результатов для переговоров

| Динамика | Что делать |
|----------|-----------|
| 📈 Положительная | Показать результат, предложить расширение, upsell |
| 📉 Отрицательная | Предупредить о падении, предложить аудит и план |
| ➡️ Стабильная | Обсудить план роста, новые направления |
| Нет данных | Предложить базовый SEO-аудит бесплатно |

## Структура файлов
```
clients/{name}/seo/
├── topvisor-keywords.json    # Семантическое ядро
├── topvisor-keywords.txt     # Читаемая версия
├── audit-YYYY-MM-DD.md       # Аудиты
└── reports/
    └── positions-YYYY-MM-DD.json  # Снятие позиций
```
