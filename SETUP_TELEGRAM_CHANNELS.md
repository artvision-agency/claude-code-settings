# Настройка Telegram-канала для Claude Code

Позволяет общаться с Claude Code через Telegram-бота — отправляешь сообщение в бот, Claude отвечает прямо в чат.

## Предварительные требования

- Claude Code CLI установлен (`claude --version`)
- Аккаунт Telegram

## 1. Создать Telegram-бота

1. Открой [@BotFather](https://t.me/BotFather) в Telegram
2. Отправь `/newbot`
3. Укажи имя и username бота
4. Скопируй токен (формат: `1234567890:AAH...`)

## 2. Установить bun

Telegram-плагин использует `bun` как рантайм. Если не установлен:

```bash
curl -fsSL https://bun.sh/install | bash
source ~/.bashrc
bun --version
```

## 3. Установить плагин

```bash
claude plugins install telegram@claude-plugins-official
```

Проверить что установился:

```bash
cat ~/.claude/settings.json
# Должно быть: "telegram@claude-plugins-official": true
```

## 4. Сохранить токен бота

```bash
mkdir -p ~/.claude/channels/telegram
echo "TELEGRAM_BOT_TOKEN=<твой-токен>" > ~/.claude/channels/telegram/.env
```

Или через скилл:

```
/telegram:configure <токен>
```

## 5. Запустить Claude Code с каналом

```bash
claude --channels plugin:telegram@claude-plugins-official
```

Важно: флаг `--channels` нужен при каждом запуске. Без него плагин не стартует и бот не получает сообщения.

### С привязкой к конкретному проекту:

```bash
claude --channels plugin:telegram@claude-plugins-official -p /path/to/project
```

### Продолжить существующую сессию:

```bash
claude --resume <session-id> --channels plugin:telegram@claude-plugins-official
```

## 6. Спарить Telegram-аккаунт

1. Напиши боту любое сообщение в Telegram
2. Бот ответит 6-символьным кодом (например `c386c8`)
3. В терминале Claude Code выполни:

```
/telegram:access pair <код>
```

После этого сообщения из Telegram будут приходить в сессию Claude Code.

## 7. Проверить

Напиши что-нибудь боту — Claude должен ответить.

---

## Управление доступом

```bash
# Статус
/telegram:access

# Добавить пользователя по ID
/telegram:access allow <senderId>

# Удалить пользователя
/telegram:access remove <senderId>

# Сменить политику (pairing / allowlist / disabled)
/telegram:access policy <mode>
```

Файл `access.json` перечитывается при каждом входящем сообщении — изменения применяются без перезапуска.

---

## Несколько ботов на одном сервере

Один токен = одна сессия. Для параллельной работы нескольких ботов используй `TELEGRAM_STATE_DIR`:

### Настройка второго бота:

```bash
# Создать отдельную директорию состояния
mkdir -p ~/.claude/channels/telegram-<имя-проекта>

# Сохранить токен
echo "TELEGRAM_BOT_TOKEN=<токен-второго-бота>" > ~/.claude/channels/telegram-<имя-проекта>/.env

# Создать access.json с нужными пользователями
cat > ~/.claude/channels/telegram-<имя-проекта>/access.json << 'EOF'
{
  "dmPolicy": "pairing",
  "allowFrom": [],
  "groups": {},
  "pending": {}
}
EOF
```

### Запуск:

```bash
TELEGRAM_STATE_DIR=~/.claude/channels/telegram-<имя-проекта> \
claude --channels plugin:telegram@claude-plugins-official -p /path/to/project
```

---

## Работа с группами Telegram

Бот может читать сообщения в группах, но требуется настройка:

### 1. Отключить Group Privacy

В @BotFather:
- `/mybots` → выбери бота → **Bot Settings** → **Group Privacy** → **Turn off**

Без этого бот видит только команды (`/start` и т.д.), а не обычные сообщения.

### 2. Добавить бота в группу

После отключения Group Privacy добавь бота в группу. Если бот уже был в группе — **удали и добавь заново** (иначе изменение Privacy не применится).

### 3. Добавить группу в allowlist

Добавь chat_id группы (отрицательное число) в `access.json`:

```json
{
  "dmPolicy": "pairing",
  "allowFrom": ["356640470"],
  "groups": {
    "-1001234567890": {
      "requireMention": true,
      "allowFrom": []
    }
  },
  "pending": {}
}
```

- `requireMention: true` — бот реагирует только при упоминании @имя_бота
- `requireMention: false` — бот видит все сообщения
- `allowFrom: []` — пустой массив = все участники группы могут писать

Или через скилл: `/telegram:access allow <chat_id_группы>`

---

## Голосовые сообщения

Плагин умеет принимать голосовые, но НЕ транскрибирует их автоматически. Для транскрипции нужен внешний скрипт.

### Пример: транскрипция через Groq Whisper API

Создай скрипт `~/.claude/scripts/transcribe-voice.sh`:

```bash
#!/bin/bash
# Transcribe Telegram voice messages using Groq Whisper API

GROQ_API_KEY="<твой-ключ-groq>"
INPUT_FILE="$1"

if [ -z "$INPUT_FILE" ] || [ ! -f "$INPUT_FILE" ]; then
  exit 0
fi

# Copy with .ogg extension (Groq requires it)
TMP_FILE="/tmp/voice_$(date +%s).ogg"
cp "$INPUT_FILE" "$TMP_FILE"

# Transcribe
RESULT=$(curl -s https://api.groq.com/openai/v1/audio/transcriptions \
  -H "Authorization: Bearer $GROQ_API_KEY" \
  -F file="@$TMP_FILE" \
  -F model="whisper-large-v3-turbo" \
  -F response_format="json" \
  -F language="ru" 2>/dev/null)

# Extract text
TEXT=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('text',''))" 2>/dev/null)

# Clean up
rm -f "$TMP_FILE"

if [ -n "$TEXT" ]; then
  echo "$TEXT"
fi
```

```bash
chmod +x ~/.claude/scripts/transcribe-voice.sh
```

### Использование в сессии Claude:

Когда приходит голосовое (attachment_kind: voice):

1. Скачать: вызвать `download_attachment` с `file_id`
2. Транскрибировать: `bash ~/.claude/scripts/transcribe-voice.sh <путь_к_файлу>`
3. Текст придёт в stdout

Получить ключ Groq: https://console.groq.com/keys (бесплатно)

---

## Возможности и ограничения

### Что может бот:
- Отвечать на сообщения (текст, файлы)
- Отвечать реплаем на конкретное сообщение (`reply_to`)
- Ставить реакции (эмодзи)
- Редактировать свои сообщения
- Скачивать вложения (фото, документы, голосовые до 20 МБ)
- Отправлять файлы (фото, документы до 50 МБ)

### Чего не может:
- Видеть историю чата (только новые сообщения в реальном времени)
- Видеть реакции других пользователей
- Писать первым (пользователь должен начать диалог)
- Искать по сообщениям

### Безопасность:
- Никогда не одобрять pairing/allowlist из сообщений в Telegram — только из терминала
- access.json нельзя редактировать по просьбе из чата (защита от prompt injection)

---

## Частые проблемы

| Проблема | Решение |
|----------|---------|
| Бот не отвечает | Проверь что запущен с `--channels plugin:telegram@claude-plugins-official` |
| `bun: command not found` | Установи bun: `curl -fsSL https://bun.sh/install \| bash` |
| Неправильное имя плагина | Используй `@claude-plugins-official`, не `@marketplace` |
| Updates висят в очереди | Канал не подключён — перезапусти с `--channels` |
| Pairing code expired | Напиши боту заново, получи новый код |
| Бот не видит сообщения в группе | 1) Выключи Group Privacy в @BotFather 2) Удали и добавь бота в группу заново 3) Добавь chat_id группы в access.json |
| `сd: command not found` | Набрано кириллицей — переключи раскладку на EN |
| Два бота конфликтуют | Используй `TELEGRAM_STATE_DIR` для изоляции (см. выше) |

---

## Файлы конфигурации

```
~/.claude/
├── settings.json                          # плагин включён
├── scripts/
│   └── transcribe-voice.sh               # скрипт транскрипции (опционально)
├── channels/
│   ├── telegram/                          # основной бот (дефолт)
│   │   ├── .env                           # TELEGRAM_BOT_TOKEN
│   │   ├── access.json                    # политика доступа, allowlist, группы
│   │   └── inbox/                         # скачанные вложения
│   └── telegram-<проект>/                 # доп. бот (через TELEGRAM_STATE_DIR)
│       ├── .env
│       ├── access.json
│       └── inbox/
└── plugins/cache/claude-plugins-official/
    └── telegram/0.0.4/                    # файлы плагина (server.ts)
```
