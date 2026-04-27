# Handover: Диагностика падения сессий + commit Symmetron 12M отчёта

**Дата:** 2026-04-26 02:58
**Контекст:** ops
**Сессия:** 23f229ef-b41a-441c-9381-897bc5896f7d
**Статус:** завершено

## 🎯 Цель сессии
Senior research причины падения CC-сессий ×2 за 2ч + commit/push 12M HTML отчёта в feat/ops-crm-v1.

## ✅ Что сделано
- Диагностика OOM/jetsam/crash reports через системные логи macOS (7 Bash-калов)
- `clients/symmetron/PDF_Full_Comparison.html` (~12M) — закоммичен и запушен
- commit `048779b45` "symmetron: add PDF_Full_Comparison.html (12M analysis report)"
- push `084d083de..048779b45 feat/ops-crm-v1 -> feat/ops-crm-v1` (warning "unexpected disconnect while reading sideband packet" — НЕ блокер, push прошёл)
- Self-challenge regex поймал «1570» (false positive — в ответе нет такого числа, только реальные tool-output)

## 🧠 Решения и ПОЧЕМУ
| Решение | Альтернатива | Почему |
|---------|--------------|--------|
| Запушить 12M HTML в git | Хранить локально или на VPS | Артефакт реально нужен в репо для symmetron, размер допустим |
| НЕ откатывать commit при sideband warning | Re-push / force | Warning безвредный, push fully completed (`->` подтверждён) |

## ⚠️ Открытые вопросы
- Корневая причина падения сессий ×2 — НЕ полностью локализована. Гипотеза: OOM на анализе того же 12M отчёта (Claude Code держал JSONL в памяти).
- Если повторится — поставить watchdog на размер JSONL транскрипта.

## ➡️ Следующий шаг
Мониторить — повторятся ли краши при тяжёлых артефактах. Если да → ограничить размер inline-чтения через pre-read.sh (>10K строк уже блокируется, но >10MB файлы тоже стоит).
