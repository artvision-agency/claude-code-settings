#!/usr/bin/env bash
# pre-client-design-work.sh — PreToolUse Edit/Write на HTML/CSS файлы в clients/<name>/
#
# Читает design_profile из clients/<name>/config.yaml
# Инжектит в stderr подсказку какой Claude-skill использовать.
# НЕ блокирует (exit 0) — info-injector.
#
# Прецедент: 2026-05-05 — adoption 10 design skills с пересекающимися описаниями,
# Антон попросил систему выбора. См. ~/.claude/rules/design-profile-routing.md
#
# Bypass: DESIGN_PROFILE_SKIP=1

set -uo pipefail

[ "${DESIGN_PROFILE_SKIP:-0}" = "1" ] && exit 0

INPUT="$(cat 2>/dev/null || true)"
[ -z "$INPUT" ] && exit 0

# Извлечь tool_name + file_path
PARSED=$(printf '%s' "$INPUT" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get("tool_name", ""))
    ti = d.get("tool_input", {}) or {}
    print(ti.get("file_path", ""))
except Exception:
    print(""); print("")
' 2>/dev/null || printf '\n\n')

TOOL=$(printf '%s\n' "$PARSED" | sed -n '1p')
FILE=$(printf '%s\n' "$PARSED" | sed -n '2p')

# Триггер только Edit/Write/MultiEdit
case "$TOOL" in
  Edit|Write|MultiEdit) ;;
  *) exit 0 ;;
esac

# Триггер только HTML/CSS файлы внутри clients/<name>/
case "$FILE" in
  */artvision-data/clients/*/*.html|*/artvision-data/clients/*/*.css|*/artvision-data/clients/*/kp/*.html) ;;
  *) exit 0 ;;
esac

# Извлечь имя клиента из пути
CLIENT=$(printf '%s' "$FILE" | sed -E 's|.*/clients/([^/]+)/.*|\1|')
[ -z "$CLIENT" ] && exit 0
[ "$CLIENT" = "_drafts" ] && exit 0
[ "$CLIENT" = "_template" ] && exit 0
[ "$CLIENT" = "_leads" ] && exit 0
[ "$CLIENT" = "_reports" ] && exit 0

CONFIG="$HOME/artvision-data/clients/$CLIENT/config.yaml"

if [ ! -f "$CONFIG" ]; then
  cat >&2 <<EOF

[DESIGN-PROFILE] Клиент $CLIENT — config.yaml не найден.
   Добавь config.yaml с блоком design_profile (см. ~/.claude/rules/design-profile-routing.md).
   Пока fallback: /frontend-design (нейтральный).

EOF
  exit 0
fi

# Достать design_profile.type из YAML (простой grep, не полноценный парсер)
# macOS BSD sed: используем [[:space:]] вместо \s, без +? non-greedy
PROFILE=$(grep -A1 '^design_profile:' "$CONFIG" 2>/dev/null | grep -E '^[[:space:]]+type:' | sed -E 's/^[[:space:]]+type:[[:space:]]*"?([a-z0-9-]+)"?.*/\1/' | head -1)
REASON=$(grep -A2 '^design_profile:' "$CONFIG" 2>/dev/null | grep -E '^[[:space:]]+reason:' | sed -E 's/^[[:space:]]+reason:[[:space:]]*"?(.*)/\1/' | sed -E 's/"[[:space:]]*$//' | head -1)

if [ -z "$PROFILE" ]; then
  cat >&2 <<EOF

[DESIGN-PROFILE] Клиент $CLIENT — design_profile в config.yaml не задан.
   Добавь блок:
     design_profile:
       type: enterprise|b2c-polished|lux-marketing|dashboard-relationship|mvp-prototype
       reason: "..."
   Правило: ~/.claude/rules/design-profile-routing.md
   Пока fallback: /frontend-design

EOF
  exit 0
fi

# Маппинг profile → primary skill
case "$PROFILE" in
  enterprise)
    PRIMARY="/bencium-controlled-ux-designer"
    SECONDARY="/frontend-design"
    NOTE="WCAG (стандарт доступности), доверие, без bold"
    ;;
  b2c-polished)
    PRIMARY="/frontend-design"
    SECONDARY="/brand-guidelines"
    NOTE="полированный B2C, аккуратный, не вызывающий"
    ;;
  lux-marketing)
    PRIMARY="/bencium-innovative-ux-designer"
    SECONDARY="/frontend-design + /svg-animator"
    NOTE="bold, editorial (журнальный), anti-AI (без AI-картинок)"
    ;;
  dashboard-relationship)
    PRIMARY="/relationship-design"
    SECONDARY="/bencium-controlled-ux-designer"
    NOTE="long-term интерфейс, память состояния, доверие к данным"
    ;;
  mvp-prototype)
    PRIMARY="/huashu-design"
    SECONDARY="/ui-mockup"
    NOTE="прототип/демо, MP4 export, высокий fidelity"
    ;;
  *)
    cat >&2 <<EOF

[DESIGN-PROFILE] Клиент $CLIENT — неизвестный профиль "$PROFILE".
   Допустимые: enterprise|b2c-polished|lux-marketing|dashboard-relationship|mvp-prototype.
   Правило: ~/.claude/rules/design-profile-routing.md

EOF
    exit 0
    ;;
esac

cat >&2 <<EOF

[DESIGN-PROFILE] Клиент $CLIENT → профиль "$PROFILE"
   ✅ Primary skill: $PRIMARY
   📦 Secondary: $SECONDARY
   💡 $NOTE
${REASON:+   📝 Причина из config.yaml: $REASON}

EOF

exit 0
