# TG-статусы: ВСЕГДА через tg-send-tracked.sh

> При любом статус-запросе Андрею/Стасу/команде — не `tg-send.sh` напрямую, а `tg-send-tracked.sh` с `--questions`. Иначе ответы не попадут в автотрекер.

## Правило

```bash
# ❌ НЕ ТАК (ответы потеряются для авто-обработки):
~/.claude/scripts/tg-send.sh team "@PandaCaffe что со статьями?"

# ✅ ТАК:
~/.claude/scripts/tg-send-tracked.sh team andrey \
  "@PandaCaffe 1. Статьи опубликованы? 2. Сколько доноров?" \
  --questions "Статьи Avto.world||60 доноров"
```

## Когда обязательно

- Статус-запросы команде (утро/день/вечер)
- Follow-up по открытым задачам
- Любое «жду ответа» от Андрея/Стаса в общем чате

## Когда НЕ нужно

- Нотификации себе (автобот в общий чат)
- Сообщения без ожидания ответа (apology, info, дайджесты)
- Клиентские DM (пока не в scope — только общий чат команды)

## Что происходит автоматически

1. `tg-send-tracked.sh` отправляет + регистрирует вопросы в `status_requests.jsonl`
2. Telethon daemon `pro.artvision.tg-listener` ловит ответ (по reply_to или sender+window)
3. `pro.artvision.tg-responder` каждые 120 сек классифицирует, мержит, пишет в `context-log.md`
4. При `ambiguous` → авто-follow-up (max 2 раза, потом эскалация)
5. При полном закрытии → архив в `sync/tg-tracking/archive/<date>_<id>.md`

Детали: `memory/reference_tg_auto_capture.md`.
