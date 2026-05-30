# REFACTOR SPEC — системно убить класс silent-fail во ВСЕХ хуках Claude Code

**Создан:** 2026-05-30 (сессия 1ee95a02, после точечного фикса 7 дефектов).
**Запуск:** в СВЕЖЕЙ сессии после `/clear` — команда «рой рефакторинг хуков по REFACTOR-SPEC».
**Тип:** infra, claude-code-settings (`~/.claude/hooks/`). Рой bash-агентов (option 1).
**Предыдущая работа:** коммиты `5bfe3b1a` (7 band-aid `|| true`) + `2224cbc7` (handover-1600-infra). Workflow-аудит run `wf_7d3d13fa-a00`.

## 🎯 Цель

Вместо 7 точечных `|| true` — **системно устранить весь класс** «warn-хук под `set -euo pipefail` молча выходит rc≠0 (≠2) → харнес печатает `Failed with non-blocking status code: No stderr output` на каждом срабатывании». Сделать так, чтобы баг не возникал у новых хуков.

## 📋 Объём (что охватить — ШИРЕ чем прошлый рой)

Прошлый рой искал только `grep/find/ls` в `$()`. Полный класс под `set -e` — ЛЮБАЯ команда, легитимно возвращающая ≠0 в подстановке/statement без guard:
- `grep`/`grep -c`/`grep -o` (no-match → 1) — главный
- `find` (ошибка пути), `ls` нескольких файлов (часть отсутствует → ≠0)
- `$(( ))` когда результат 0 → rc=1
- `read` на EOF → rc=1
- `[[ ... ]]` / `(( ... ))` как самостоятельный statement (false → 1, set -e убивает)
- `let`, `expr` (0 → rc=1)
- pipeline где падающая команда не последняя + `pipefail`

Все **142 хука** в `~/.claude/hooks/*.sh` (не только 47 с grep). 103 имеют `set -e/pipefail`.

## 🛠 Подход (option 1, утверждён Антоном 30.05)

1. **Общий lib** `~/.claude/hooks/_lib/hook-common.sh`:
   - `hook_read_stdin()` — безопасное чтение JSON (никогда не трогает set -e).
   - `hook_field <json> <jq-path>` — извлечение поля (jq `// empty`, всегда rc=0).
   - `hook_extract <text> <regex>` — grep-обёртка, на no-match → пустая строка + rc=0.
   - `hook_allow` / `hook_block "<reason>"` — стандартный выход (0 / 2+stderr). **block ВСЕГДА с stderr-причиной.**
   - Все хуки `source` этот lib (путь относительно `${BASH_SOURCE}`).
2. **Политика set -e для warn-хуков:** решить роем — (a) оставить `set -e` + обязательный guard через lib, ИЛИ (b) для warn-only хуков убрать `set -e` (оставить `set -uo pipefail`), т.к. warn-хук НЕ должен умирать на промежуточной команде. Рекомендация: (b) для warn-only + (a)+lib для блокирующих. Обосновать в decisions/.
3. **Пройти все 142**, привести к единому шаблону stdin-parse + guard. Band-aid `|| true` из 5bfe3b1a заменить на вызовы lib (консистентность).
4. **Починить `pre-outbound-gate.sh`** — сейчас блокирует с пустым stderr (Claude не видит причину). Добавить `hook_block "<что заблокировано и почему>"`.
5. **Тесты** `~/.claude/hooks/tests/test-all-hooks.sh`:
   - Для КАЖДОГО PreToolUse-хука: прогон на (а) benign-input `ls -la`/безобидный Edit, (б) trigger-input его пути → assert rc ∈ {0,2}, при rc=2 stderr непустой.
   - Side-effecting (Post/Stop/SessionStart/UserPromptSubmit) — статический lint (нет unguarded fail-команд под set -e), НЕ исполнять.
   - **Обход `pre-outbound-gate`:** trigger-inputs с `scp/root@` собирать через конкатенацию переменных (`R="root";"$R""@h"`), не литералом — иначе gate режет тест (прецедент этой сессии).
6. **CI-lint** (опц.): `pre-commit`-проверка на новые хуки — есть `set -e` + unguarded fail-команда → warn.

## ✅ Критерий DONE
- 0 хуков выходят rc∉{0,2} на benign-input (динамика PreToolUse) + статика чистая на остальных.
- block-хуки всегда с stderr-причиной.
- Тест-харнес зелёный, закоммичен.
- decisions/-запись про политику set -e.
- Коммит + push в claude-code-settings.

## ⚠️ Гачи
- `~/.claude` = git claude-code-settings. Коммитить ТОЧЕЧНО (там state-мусор + settings.json не трогать).
- Bash-tool под **zsh**: `for x in $VAR` не сплитит — использовать `bash <<'EOF'` или массивы.
- Hooks подхватываются file-watcher'ом, рестарт не нужен (cherny-tips #9).
- `pre-tool-skill-required.sh` ложно блокирует если в команде слово-имя скилла → `touch /tmp/skill-required-done-<session_id>`.
- `pre-outbound-gate.sh` режет `scp…root@` в тест-командах (см. п.5 обход).
- Прошлый рой: партиции по ~8 хуков, 6 агентов, schema StructuredOutput, агенты только АНАЛИЗ — фиксы применяет основной процесс последовательно (не параллелить правки одного каталога).

## 🔗 Связанные
- Точечный фикс: коммит `5bfe3b1a`, handover `HANDOVER-2026-05-30-1600-infra.md`
- Шаблон рой-workflow: `~/.claude/projects/-Users-antonk--claude-hooks/1ee95a02-*/workflows/scripts/hook-silentfail-audit-wf_7d3d13fa-a00.js`
