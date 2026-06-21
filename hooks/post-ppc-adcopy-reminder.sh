#!/usr/bin/env bash
# post-ppc-adcopy-reminder.sh — PostToolUse(Edit|Write), WARN-ONLY (не блокирует)
# Напоминает применять ppc-ad-copy-relevance + прогнать /ppc-ad-check при правке
# файлов текстов объявлений Я.Директа (путь */ppc/* или */ads/* + имя про объявления).
# Установлен 2026-06-21 (Антон). Bypass: PPC_ADCOPY_OK=1
[ -n "${PPC_ADCOPY_OK:-}" ] && exit 0

input=$(cat)
fp=$(printf '%s' "$input" | grep -oE '"file_path"[[:space:]]*:[[:space:]]*"[^"]+"' | head -1 \
     | sed -E 's/.*"file_path"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/')
[ -z "$fp" ] && exit 0

low=$(printf '%s' "$fp" | tr '[:upper:]' '[:lower:]')
case "$low" in
  */ppc/*|*/ads/*) ;;
  *) exit 0 ;;
esac
case "$low" in
  *ad-text*|*ad_text*|*adtext*|*объявлен*|*ad-copy*|*ads-text*|*ad-creative*) ;;
  *) exit 0 ;;
esac

cat <<'EOF'
[PPC-ADCOPY] Правишь тексты объявлений Я.Директа.
→ Применяй правило ~/.claude/rules/ppc-ad-copy-relevance.md (релевантность ключ↔текст↔интент + AVpro-конкретика).
→ Перед заливкой прогони /ppc-ad-check (13-пунктный DoD; заливка всегда OFF — ppc-upload-always-off).
Bypass: PPC_ADCOPY_OK=1
EOF
exit 0
