#!/bin/bash
# PostToolUse(Edit|Write): «волшебная кнопка» voice.js обязательна в клиентских HTML
# (КП/презентация/лендинг/отчёт прямого клиента) — правило kp-workflow-family §5.
# Срабатывает ТОЛЬКО если документ уже несёт брендинг Artvision (= клиентский),
# но в нём НЕТ widgets/voice.js. Это отсекает внутренние ч/б документы и AdvertMed white-label.
# Не блокирует (warn-only). Bypass: VOICE_WIDGET_OK=1.
# Прецедент: 2026-06-17 DS-Lab — ручная сборка документа без воркфлоу → забыл виджет с видео Антона.

[ -n "$VOICE_WIDGET_OK" ] && exit 0

INPUT=$(cat)
FILE=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('file_path',''))" 2>/dev/null)

[ -z "$FILE" ] && exit 0

# Только HTML в client/presale-папках
echo "$FILE" | grep -qE '(clients|presales)/[^/]+/.+\.html$' || exit 0
[ ! -f "$FILE" ] && exit 0

# Исключение: AdvertMed / white-label партнёры (им бренд Artvision НЕ ставим — branding-policy)
if grep -qiE 'advertmed|варикознет|varikoz' "$FILE" 2>/dev/null; then
  exit 0
fi
echo "$FILE" | grep -qiE 'advertmed|varikoz' && exit 0

# Признак КЛИЕНТСКОГО документа = уже есть брендинг Artvision (логотип/футер/кнопка/виджет).
# Если брендинга нет — это внутренний/технический документ (ч/б аудит и т.п.) → не наша забота тут.
if ! grep -qiE 'kp-logo|av-bar|av-logo|class="ask"|Задать вопрос|artvision\.pro|Artvision ×|widgets/voice' "$FILE" 2>/dev/null; then
  exit 0
fi

# Уже есть виджет voice.js → всё ок
if grep -qE 'widgets/voice\.js' "$FILE" 2>/dev/null; then
  exit 0
fi

# Клиентский документ с брендингом, но БЕЗ волшебной кнопки → предупреждение
cat <<EOF >&2

⚠️  post-client-html-voice-widget-check: $FILE
   Клиентский документ с брендингом Artvision, но БЕЗ «волшебной кнопки» voice.js
   (видео Антона + чат). Это HARD-правило kp-workflow-family §5.

   Поставь перед </body> виджет (палитру/чипсы — под клиента):
     <script src="https://artvision.pro/widgets/voice.js"
       data-avatar-img="https://artvision.pro/widgets/anton-portrait.jpg"
       data-avatar-vid="https://artvision.pro/widgets/anton-portrait.mp4"
       data-bot="avportal" data-chat-id="161261562"
       data-name="Артвижн · Антон" data-avatar="АК"
       data-palette-primary="<accent>" data-palette-secondary="<accent-d>"
       data-endpoint="https://artvision.pro/api/kp-message.php"
       data-tg-fallback="+79110861888" data-online-mode="hours"
       data-chips="вопрос1|вопрос2|вопрос3"></script>

   Правило: ~/artvision-data/.claude/rules/kp-workflow-family.md (§5)
   НЕ ставить для AdvertMed/white-label (там без бренда Artvision).
   Bypass: VOICE_WIDGET_OK=1

EOF

exit 0
