# Архив агентов — автоматическая реакция

> Архив: `~/.claude/agents-archive-2026-04-21/`
> Создан: 2026-04-21 для снижения контекста агентов (-54%)

## Правило

Если пользователь упоминает технологию/домен из списка ниже — **автоматически вернуть** нужного агента в `~/.claude/agents/` через `mv`, без лишних вопросов. Реагировать на любые формы: "нужен powershell", "клиент на Azure", "реверс-инжиниринг бинаря", "напиши под embedded", "IoT проект".

## Что в архиве → триггеры для возврата

| Агент | Триггеры в речи пользователя |
|-------|------------------------------|
| `ad-security-reviewer.md` | active directory, AD, домен контроллер, GPO audit |
| `azure-infra-engineer.md` | azure, ажур, bicep, azure cloud |
| `c4-context.md` | C4 диаграмма, system context, контекстная архитектура |
| `chaos-engineer.md` | хаос, chaos testing, failure injection, game day |
| `embedded-systems.md` | embedded, микроконтроллер, RTOS, firmware, stm32, arduino |
| `fintech-engineer.md` | финтех, fintech, banking, платёжная система, PCI |
| `gan-evaluator.md` / `gan-generator.md` / `gan-planner.md` | GAN harness, генератор-эвалюатор, iterative spec |
| `harness-optimizer.md` | harness, агент-харнесс, оптимизация агент-фреймворка |
| `healthcare-reviewer.md` | healthcare, EMR, EHR, PHI, HIPAA, медицинский код |
| `iot-engineer.md` | IoT, устройства, MQTT, edge computing, умный дом |
| `it-ops-orchestrator.md` | IT ops, оркестрация IT-задач Windows |
| `llm-architect.md` | LLM архитектура, fine-tune pipeline, RAG production |
| `m365-admin.md` | microsoft 365, exchange online, teams admin, sharepoint |
| `powershell-5.1-expert.md` | powershell 5.1, windows powershell legacy |
| `powershell-7-expert.md` | powershell 7, pwsh, cross-platform powershell |
| `powershell-module-architect.md` | powershell модуль, psd1, module design |
| `powershell-security-hardening.md` | harden powershell, execution policy, applocker |
| `powershell-ui-architect.md` | WinForms PS, WPF PS, powershell GUI |
| `quant-analyst.md` | квант, HFT, derivatives pricing, algo trading |
| `reverse-engineer.md` | реверс, IDA, Ghidra, разобрать бинарь, CTF |
| `terraform-engineer.md` | terraform, opentofu, IaC terraform |
| `windows-infra-admin.md` | windows server, AD DS, DNS windows, DHCP windows |

## Алгоритм

1. Поймал триггер → `mv ~/.claude/agents-archive-2026-04-21/<agent>.md ~/.claude/agents/`
2. Сообщить пользователю: "Вернул из архива: `<agent>` — тема упомянута. Продолжаю."
3. Использовать агента в текущей задаче
4. После окончания работы с темой — **не возвращать** обратно в архив (пусть живёт пока не накопится мусора)

## Анти-паттерны

- ❌ Спрашивать "вернуть агента?" — просто вернуть
- ❌ Возвращать "на всякий случай" без явного триггера
- ❌ Копировать вместо `mv` — плодит дубли
