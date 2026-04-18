#!/usr/bin/env bash
# UserPromptSubmit hook: reminds Claude to use authority-barter skill
# when user talks about B2B link-building, content placements, industry media,
# barter deals, evergreen links, authority/trust signals.

set -euo pipefail

PROMPT="$(cat 2>/dev/null || true)"

# Case-insensitive match against authority-barter keywords
if echo "$PROMPT" | grep -iqE "бартер|размещени[еяй] в медиа|отраслев[а-я]+ медиа|карточк[аи] компании|евергрин|евершгрин|authority|траст|гостев[а-я]+ пост|линкбилдинг.*b2b|b2b.*линкбилдинг|цитатн[а-я]+ вес|e-?e-?a-?t|партнёрск[а-я]+ материал|статья в журнал|опубликова[а-я]+ в (жур|медиа|издан)"; then
  cat <<'EOF'
[SKILL-HINT] authority-barter релевантен текущей задаче.
Загрузить: Skill tool → authority-barter

Что внутри:
- Tier-модель площадок + реестр sites.yaml (agro уже заполнена)
- 3 шаблона: pitch-editor, content-brief, barter-agreement
- Pipeline: research → питч → check → fact-check → client approval → отправка → monitoring
- Усиления: authorship (schema.org/Person), digital PR с датасетами
- Риски: Google paid links penalty, Яндекс Минусинск, токсичные доноры
- Метрики: DR/ИКС, Referring Domains, brand mentions, referral traffic

Главный аргумент для клиента:
«Публикация = перенос цитатного веса от РБК/Интерфакса/Минсельхоза на сайт клиента»
EOF
fi

exit 0
