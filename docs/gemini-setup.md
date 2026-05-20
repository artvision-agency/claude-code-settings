# Gemini handoff — setup для Антона

> Что готово автоматически: wrapper-скрипт, subagent, правило routing. Тебе остаётся 2 интерактивных шага: VPN-режим + OAuth.

## Что уже сделано (автоматом)

- `~/.claude/scripts/gemini-rescue.sh` — bash-wrapper с pre-flight (geo + auth check)
- `~/.claude/agents/gemini-rescue.md` — subagent, доступен через `Agent({subagent_type: "gemini-rescue", ...})`
- `~/.claude/rules/consilium-matrix.md` — Gemini добавлен как 5-е семейство (Claude/OpenAI/open-source/Google)
- `@google/gemini-cli` v0.42.0 установлен глобально

## 2 шага от тебя (интерактивно)

### Шаг 1. Geo (если нужно)

**Проверь свой IP сейчас:**

```bash
curl -s https://ipinfo.io/country
```

- Если **`FI` / `NL` / `DE` / `US`** и т.п. — geo ок, переходи к Шагу 2.
- Если **`RU`** — нужен VPN. Варианты:

| Вариант | Стоимость | Сложность | Стабильность |
|---------|-----------|-----------|--------------|
| **Mullvad** (mullvad.net) | $5/мес фикс (можно крипто) | низкая (.dmg → 3 клика) | высокая |
| **AmneziaVPN** (amnezia.org) — open-source клиент + свой Wireguard на иностранном VPS | бесплатно (если VPS уже есть) | средняя (настроить VPS) | высокая |
| **ProtonVPN free** | бесплатно | низкая | средняя (лимит скорости) |

> **Split-tunneling совет:** если боишься «VPN-сломал-всё», поставь Mullvad + включай только когда нужен Gemini handoff. Asana/TG/русские сервисы — direct.

### Шаг 2. OAuth Code Assist (или новый API key)

**Опция A — OAuth (бесплатно, 60 RPM, рекомендую):**

```bash
gemini
# Откроется браузер → залогинься в личный Google → Authorize → готово
# Creds сохранятся в ~/.gemini/oauth_creds.json
# Выйди из interactive: /quit
```

**Опция B — Новый API key с billing:**

1. Залогинься в [aistudio.google.com](https://aistudio.google.com) (только из не-РФ IP)
2. Get API key → Create API key in new project
3. Enable billing на проекте (Google Cloud Console)
4. Update `tokens.json → gemini.api_key`

> **Текущий key в tokens.json** имеет `limit: 0` (свободный tier выключен), нужен или OAuth, или новый key с billing.

## Проверка после setup

```bash
# 1. Wrapper preflight
~/.claude/scripts/gemini-rescue.sh task "Reply exactly: HANDOFF_OK"

# 2. Через subagent в Claude Code
# Agent({subagent_type: "gemini-rescue", prompt: "Reply exactly: HANDOFF_OK"})
```

Ожидаемый результат: ответ Gemini "HANDOFF_OK".

## Когда что использовать

| Кейс | Инструмент |
|------|-----------|
| Frontend (Figma→React, UI рефакторинг, mockup) | **Gemini** (multimodal + 1M ctx) |
| Backend / архитектура / алгоритмы | **Codex** GPT-5.4 |
| Спорный код, рои-агенты застряли | **Gemini ИЛИ Codex** (для разнообразия мнений) |
| Cross-валидация решения | **round_table** (open-source) + Gemini/Codex |
| Большое репо (>30 файлов в контексте) | **Gemini 1M ctx** |

Полная routing-матрица: `~/.claude/rules/consilium-matrix.md`.

## Антипаттерны

- ❌ Запускать Gemini handoff для задач которые Claude закроет сам быстрее
- ❌ Гонять платный gemini-2.5-pro для UI mockup — используй `--model gemini-2.5-flash` (10× дешевле)
- ❌ `--yolo` режим без явного approve пользователя
- ❌ Забывать `--plan` для read-only диагностики
