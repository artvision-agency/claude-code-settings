#!/bin/bash
# PreToolUse(Write|Edit): блокирует client KP с CRITICAL bred
# Категории: финансовка / internal markers / AI-модели / резкие слова /
#            продажные клише / детализация плана / контакты Artvision
# Bypass: KP_BRED_OK=1
INPUT=$(cat)
TOOL=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_name',''))" 2>/dev/null)
FP=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin).get('tool_input',{}); print(d.get('file_path',''))" 2>/dev/null)
[ -z "$FP" ] && exit 0

# Только client KP файлы
case "$FP" in
  */clients/*/kp/*.html|*/clients/*/presale/kp/*.html|*/presales/*/kp/*.html|*/presale/*/kp/*.html|*/clients/*/presale/*kp*.html|*/var/www/artvision/kp/*) ;;
  *) exit 0 ;;
esac

[ "$KP_BRED_OK" = "1" ] && exit 0

# Извлечь записываемый контент
CONTENT=$(echo "$INPUT" | python3 -c "
import sys,json
d=json.load(sys.stdin).get('tool_input',{})
print(d.get('content') or d.get('new_string') or '', end='')
" 2>/dev/null)
[ -z "$CONTENT" ] && exit 0

# Проверка по 7 категориям
HITS=$(echo "$CONTENT" | python3 -c "
import sys, re
text = sys.stdin.read()
text = re.sub(r'<script.*?</script>',' ',text,flags=re.S|re.I)
text = re.sub(r'<style.*?</style>',' ',text,flags=re.S|re.I)
text = re.sub(r'<[^>]+>',' ',text)
critical = []

# 1. ФИНАНСЫ КЛИЕНТА — выручка/прибыль/ROI в рублях
if re.search(r'(Выручка\s*/\s*мес|ΔВыручк|чистая\s+прибыль|маржинальн[а-я]+\s+\d+\s*%|break.?even|точк[аи]\s+окупаем)', text, re.I):
    critical.append('FINANCIALS')
if re.search(r'\+\d{2,3}\s*\d{3}\s*₽', text):
    critical.append('REVENUE_DELTA')

# 2. ВНУТРЕННИЕ МАРКЕРЫ (служебная лексика)
if re.search(r'\b(?:UNCONFIRMED|CONFIRMED|WRONG)\b', text):
    critical.append('INTERNAL_MARKERS_TAGS')
if re.search(r'\b(?:WebFetch|WebSearch|curl[- ]парсинг|curl[- ]запрос|prompt|Bash|grep)\b', text):
    critical.append('INTERNAL_TOOLS')
if re.search(r'Topvisor\s+API|Wordstat\s+API|Я\.?Метрика\s+API', text, re.I):
    critical.append('INTERNAL_API_NAMES')

# 3. ARTVISION БРЕНД/ДОМЕН в публичных материалах партнёра
if re.search(r'\bartvision\.pro\b', text):
    critical.append('ARTVISION_PRO')
if re.search(r'\bArtvision\s+(Flow|Watch|Radar|Scout|LinkForge|Insight|Leads|Content\s+Lab|Pulse|VoxRate|Lens|Funnel)\b', text):
    critical.append('ARTVISION_BRAND')

# 4. AI/LLM МОДЕЛИ И ПРОВАЙДЕРЫ (security.md ТАБУ в публичных материалах)
if re.search(r'\b(?:Llama|Qwen|GPT-OSS|GLM-4|GLM-5|Nemotron|Gemma|DeepSeek|ChatGPT|Claude|Perplexity|Mistral|Phi-?\d|Anthropic|OpenAI)\b', text):
    critical.append('AI_MODELS')
if re.search(r'\b(?:Groq|OpenRouter|Fireworks|Together\.ai|Replicate)\b', text):
    critical.append('AI_PROVIDERS')
if re.search(r'\b(?:LLM|нейросет[ьи]|нейронн[ыа][ея]\s+сет[ьи])\b', text, re.I):
    critical.append('LLM_MENTIONS')

# 5. РЕЗКИЕ/ЭМОЦИОНАЛЬНЫЕ СЛОВА (не деловой стиль)
if re.search(r'(?:обвал|коллапс|мина под|мёртв|токсичн|галлюциниру|нулевая видимость|спам.?сигнал|демпингу|шаблонн|диссонанс|репутационная мина)', text, re.I):
    critical.append('HARSH_WORDS')

# 6. ПРОДАЖНЫЕ КЛИШЕ
if re.search(r'(?:гаранти[рую][а-я]*\s+ТОП|революционн|единственн[ыа][йя]\s+(?:в|на)|прорывн|эксклюзивн|уникальн\w+\s+(?:решен|подход|предложен)|премиум|стать\s+№\s*1|лучш\w+\s+(?:на\s+рынке|в\s+отрасли))', text, re.I):
    critical.append('SALES_CLICHES')
if re.search(r'(?:под\s+(?:ключ|вашу\s+задачу)|команда\s+професси|надёжн[ыа][йя]\s+партн|индивидуальн\w+\s+подход)', text, re.I):
    critical.append('SALES_CLICHES_GENERIC')

# 7. ВНУТРЕННИЕ ДЕТАЛИ ПЛАНА (избыточная техническая детализация)
if re.search(r'JSON-LD\s*:\s*LocalBusiness\s*\+\s*Service|robots\.txt\s*:\s*User-agent', text):
    critical.append('PLAN_OVER_DETAIL')

# 8. КОНТАКТЫ ARTVISION В КП КЛИЕНТА (только виджет/менеджер)
if re.search(r'\+7\s*\(?911\)?\s*086.18.88|antonkamer|@antonkamer|@andrey_artvision|info@artvision\.|boss@artvision\.', text, re.I):
    critical.append('ARTVISION_CONTACTS')

print(' '.join(critical))
")

if [ -n "$HITS" ]; then
  cat <<EOF
⛔ pre-kp-bred-block: ЗАБЛОКИРОВАНО

Файл: $FP
Критические нарушения: $HITS

Категории:
  • FINANCIALS / REVENUE_DELTA — выручка/прибыль клиента в КП запрещены (feedback_no_client_financials_in_kp.md)
  • INTERNAL_MARKERS_TAGS / INTERNAL_TOOLS / INTERNAL_API_NAMES — UNCONFIRMED/curl/WebFetch/API в видимом тексте (feedback_no_internal_markers_in_client_docs.md)
  • ARTVISION_PRO / ARTVISION_BRAND — упоминания artvision.pro / Flow/Radar/etc в КП партнёра (AdvertMed)
  • AI_MODELS / AI_PROVIDERS / LLM_MENTIONS — табу AI/LLM/Llama/ChatGPT/Groq/OpenRouter в публичных материалах (security.md)
  • HARSH_WORDS — резкие слова (обвал/мина/токсичн/галлюциниру/диссонанс) в деловом документе
  • SALES_CLICHES — продажные клише (гарантирую ТОП / стать №1 / уникальное решение / премиум)
  • SALES_CLICHES_GENERIC — «под ключ», «команда профессионалов», «надёжный партнёр»
  • PLAN_OVER_DETAIL — техническая детализация плана (JSON-LD: LocalBusiness + Service) — в КП общими формулировками
  • ARTVISION_CONTACTS — телефон/email/Telegram Артвишн в КП клиента (только виджет чата)

Исправить до записи. Bypass на свой риск: KP_BRED_OK=1
EOF
  exit 2
fi

exit 0
