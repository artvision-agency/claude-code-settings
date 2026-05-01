# Handover: Ghostty crash loop на 8GB MacBook Air

**Дата:** 2026-05-01 21:16
**Контекст:** infra
**Сессия:** SOLVING (5807eefe → 9bb3aa9b → ef3a112f, resumed дважды)
**Статус:** в работе — диагноз есть, корневой фикс не применён (нужен апгрейд RAM или radикальное сокращение workload)

## 🎯 Цель сессии

Найти причину 4 крашей Ghostty за день и остановить crash loop.

## ✅ Что сделано

- **Диагноз через 5 параллельных каналов:**
  - 4 Claude-субагента (`debugger`, `performance-engineer`, `sre-engineer`, macOS-специалист через `general-purpose`)
  - 1 round_table (упал — нет tokens.json в /Users/antonk/artvision-data/, не критично)
- **Памятные команды (`/Users/antonk/.config/ghostty/config:1-2`)** — создан с `window-save-state = never`
- **savedState очищен:** `~/.backups/ghostty-savedState-20260501-210109.tar.gz` (12 окон) → удалено из `~/Library/Saved Application State/com.mitchellh.ghostty.savedState/`
- **Monitor поднят:** PID 44474, пишет в `/tmp/ghostty_mem.log` каждые 30 сек (но между крашами Ghostty жил недолго → лог пустой, надо удлинить uptime)
- **Убито 6 зомби `claude --resume`** (PIDs 25683/25691/25706/25724/25731/25780, утренний batch-resume) — освободило ~600 MB RAM, swap 12.7 → 10.6 GB
- **Форкнуты 2 топовых GitHub-репо агентов:**
  - https://github.com/justtrance-web/agents (wshobson, 34.6K⭐, 184 агента) — `~/forks/agents/agents/`
  - https://github.com/justtrance-web/awesome-claude-code-subagents (VoltAgent, 18.9K⭐) — `~/forks/agents/awesome-claude-code-subagents/`
- **Recap:** `/Users/antonk/artvision-data/sync/recaps/9bb3aa9b-eef4-4f35-b0e6-1ac6a5480618.md` (заполнен)

## 🧠 Решения и ПОЧЕМУ

| Решение | Альтернатива | Почему |
|---------|--------------|--------|
| **Корневая причина = jetsam OOM kill** (silent SIGKILL без crash report) | Metal device-lost / WindowServer kick / Ghostty Zig bug | `debugger` нашёл строку `runningboardd: [ghostty] Ignoring jetsam update because this process is not memory-managed` → kernel jetsam убивает напрямую без user-space callback. Подтверждено 4 силовыми завершениями подряд без `.diag` |
| **`window-save-state=never` оставлен**, но не считаем главным фиксом | Откатить (вернуть savedState), переключиться на OpenGL | Ghostty 1.2.x не поддерживает `renderer=opengl` (compile-time). Save-state помог снизить RSS на старте до 45 MB (vs 333 MB) — это полезно, но не блокирует jetsam при 9 параллельных Claude |
| **Не делать reboot прямо сейчас** | reboot Mac (clear swap) | Reboot решает swap, но через 2-3 часа всё вернётся. Это не лечение — это переоткрытие проблемы |
| **Корневой фикс — апгрейд RAM (Mac mini M4 24GB ~90K RUB)** | продолжать на 8GB с watchdog/мониторингом | sre-engineer + performance-engineer независимо: на 8GB **>3 параллельных Claude — capacity violation**, не баг. ROI: 3 краша × 15 мин восстановления = 45 мин/день = 15 ч/мес = ~45K RUB/мес упущенной работы. Окупаемость <2 мес |
| **Hiddify VPN — суспект**, к замене на Mihomo Party | Оставить Hiddify | sing-box wrapper держит NetworkExtension с leak (~200-400 MB), при дисконнекте не освобождает. 3 краша tunnel/день коррелируют с Ghostty крашами |
| **Не устанавливать launchd watchdog без подтверждения** | установить сейчас | Watchdog может убивать активные claude сессии (если CPU<1% и uptime>30мин — но это может быть idle-thinking сессия). Антон должен явно подтвердить пороги |

## ❌ Что НЕ сделано

- **Reboot Mac** — пользователь не подтвердил, swap до сих пор 10.6/11.3 GB (94%)
- **Установка launchd watchdog** (`claude-oom-guard.plist`) — готов скрипт от performance-engineer, не задеплоен
- **Замена Hiddify → Mihomo Party / WireGuard** — экономит ~300 MB
- **Переключение на iTerm2 с отключённым Metal или Alacritty + tmux** — radикальная альтернатива Ghostty, отложена
- **claude auth переключение на adw.artvision.pro** — интерактивная команда, должен запустить пользователь сам через `! claude auth logout`
- **round_table не сработал** — `/Users/antonk/artvision-data/tokens.json` не найден (другой cwd?). Не критично — диагноз сошёлся через 4 субагента

## 📚 Уроки

- **macOS jetsam НЕ пишет .diag когда процесс не memory-managed** (Ghostty не зарегистрирован в RunningBoard). Признак — отсутствие `Action taken: kill` в wakeups_resource.diag, отсутствие записи в `~/Library/Logs/DiagnosticReports/`. → создать `feedback_macos_jetsam_silent_kill.md`
- **Ghostty 1.2.x имеет известный memory leak именно при работе с Claude Code CLI** (issue #10289 — "Severe memory leak with Claude Code"). Mitchell Hashimoto post-mortem: log accumulation от unimplemented escape-sequences (~4.6/sec). Не пофиксано в 1.2.3, обещано в 1.3.0. → создать `feedback_ghostty_claude_code_leak.md`
- **При первичной диагностике краша на macOS — смотреть ОБА diag-каталога:** user-level `~/Library/Logs/DiagnosticReports/` И system-level `/Library/Logs/DiagnosticReports/` (root-owned). Я смотрел только user → пропустил 3 wakeups_resource.diag в первом ответе → пришлось извиняться и переделывать. → урок в `lessons.md` (root-cause analysis)
- **wshobson/agents (34.6K⭐) и VoltAgent/awesome-claude-code-subagents (18.9K⭐)** — два топовых публичных коллекции subagent-определений. Первая = production-grade plugin packs (DevOps/SRE упор), вторая = чистая каталогизация по 10 категориям. Полезно когда нужен specialist subagent type не из встроенных. Форки в `~/forks/agents/`. → создать `reference_agent_repos.md`
- **На 8GB Mac жёсткий лимит — 3 одновременных Claude CLI**, далее capacity violation. Hiddify+VS Code+Telegram+Chrome съедают headroom целиком. → лимит зафиксировать в `feedback_claude_cli_capacity_8gb.md`

## 🔜 Следующие шаги (приоритет)

1. **HIGH (сегодня):** Антон решает — A) reboot сейчас + далее наблюдать, B) заказать Mac mini M4 24GB сегодня (90K RUB, окупится за 2 мес), C) переход на iTerm2/Alacritty + tmux (radикально, но требует адаптации workflow)
2. **HIGH:** Заменить Hiddify на Mihomo Party или нативный WireGuard.app — освободит 200-400 MB
3. **MEDIUM:** Установить launchd watchdog `claude-oom-guard.plist` с порогами Pages free<25MB / swap>10GB → kill oldest idle Claude
4. **MEDIUM:** Перевести workflow в tmux (`tmux new -As main`) — даже краш Ghostty не убивает PTY, восстановление через `tmux attach`
5. **LOW:** Создать 5 memory-файлов из секции «Уроки»
6. **LOW:** Подождать Ghostty 1.3.0 — обещан фикс log-accumulation leak

## 🗺️ Карта файлов

```
~/.config/ghostty/config              ← новый, window-save-state=never
~/.backups/ghostty-savedState-*.tar.gz ← бэкап 12 окон
~/Library/Saved Application State/com.mitchellh.ghostty.savedState/  ← пусто
/Library/Logs/DiagnosticReports/ghostty_2026-05-01-{18,19,20}*.wakeups_resource.diag  ← 3 краша до фикса
/tmp/ghostty_mem.log                  ← monitor (PID 44474)
~/forks/agents/agents/                ← wshobson fork
~/forks/agents/awesome-claude-code-subagents/  ← VoltAgent fork
/Users/antonk/artvision-data/sync/recaps/9bb3aa9b-eef4-4f35-b0e6-1ac6a5480618.md  ← session recap
```

## ⚠️ Гачи

- **8 GB Mac + 9 Claude CLI = capacity violation**, не баг — лечится только апгрейдом или сокращением сессий до 3
- **`claude auth logout` интерактивная** — нельзя запустить из этой сессии (убьёт её). Только через `! claude auth logout`
- **round_table требует** `/Users/antonk/artvision-data/tokens.json` — если работаешь из другого cwd, MCP llm-consilium падает с FileNotFoundError. Диагноз можно пройти и без него (4 субагента дают согласованный результат)
- **gh auth — `justtrance-web`** (token: gho_***, scope: gist/read:org/repo/workflow). Форки идут под этот аккаунт
- **Monitor PID 44474** работает в фоне, но между крашами Ghostty живёт недолго → лог пустой. Если хочешь полезные данные — увеличь uptime Ghostty (открой и не закрывай 1 час)
- **3 wakeups_resource.diag** — это watchdog warnings, **не crash reports**. `Action taken: none`. Реальные kills — silent jetsam → нигде не зафиксированы

## 🔗 Связанные ресурсы

- Ghostty issue #10289 (Claude Code leak): https://github.com/ghostty-org/ghostty/issues/10289
- Mitchell Hashimoto post-mortem: https://mitchellh.com/writing/ghostty-memory-leak-fix
- wshobson/agents: https://github.com/wshobson/agents
- VoltAgent: https://github.com/VoltAgent/awesome-claude-code-subagents
- Прецедент 26.04 в memory: free 42 MB, диск 97% — те же 4 ttys падали 2× за 2 часа
- Recap: `artvision-data/sync/recaps/9bb3aa9b-eef4-4f35-b0e6-1ac6a5480618.md`
