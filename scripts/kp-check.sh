#!/bin/zsh
# kp-check.sh <kp.html> [client-domain]
# Детерминированная проверка клиентского КП по правилам Artvision (0 LLM-токенов).
# Проверяет: запрет AI/сторонних тулов, mobile-first, источники/методология,
# бренд, «Задать вопрос», цены, автономность, TOC. Печатает таблицу PASS/WARN/FAIL.
# Пример: kp-check.sh clients/ds-lab/kp/ds-lab-kp-2026-06-25.html ds-lab.ru
set -u
F="${1:-}"
DOM="${2:-}"
[ -z "$F" ] && { print -u2 "Usage: kp-check.sh <kp.html> [client-domain]"; exit 2; }
[ -f "$F" ] || { print -u2 "Нет файла: $F"; exit 1; }

# base64-изображения вырезаем из текста ДО текстовых проверок (иначе ложные AI/tool-срабатывания)
TXT=$(sed -E 's@data:image/[a-zA-Z+]+;base64,[A-Za-z0-9+/=]+@[img]@g' "$F")

pass=0; warn=0; fail=0
row(){ # status text
  case "$1" in
    PASS) print "  ✅ PASS  $2"; pass=$((pass+1));;
    WARN) print "  🟡 WARN  $2"; warn=$((warn+1));;
    FAIL) print "  ❌ FAIL  $2"; fail=$((fail+1));;
  esac
}
cnt(){ printf '%s' "$TXT" | grep -ciE "$1" 2>/dev/null; }

print "КП-чек: $F"
print "────────────────────────────────────────"

# 1. Запрет AI/нейросетей (security.md)
n=$(cnt 'нейросет|нейронн[ыа]|искусственн.{0,3}интел|\bgpt\b|\bllm\b|machine learning|\bml\b')
[ "$n" -eq 0 ] && row PASS "нет AI/нейросетей" || row FAIL "AI-упоминания: $n (запрет)"

# 2. Запрет сторонних тулов (kp-brand.md)
n=$(cnt 'semrush|ahrefs|topvisor|serpstat|google analytics|яндекс.?метрик|screaming frog|keys\.so')
[ "$n" -eq 0 ] && row PASS "нет сторонних SEO-тулов" || row FAIL "сторонние тулы: $n (ребрендить в Artvision)"

# 3. Mobile-first (min-width, без max-width @media)
mn=$(grep -oc 'min-width' "$F" 2>/dev/null)
mx=$(grep -oE '@media[^{]*max-width' "$F" 2>/dev/null|wc -l|tr -d ' ')
{ [ "$mn" -gt 0 ] && [ "$mx" -eq 0 ]; } && row PASS "mobile-first (min-width:$mn, max@media:$mx)" || row WARN "проверь адаптив (min:$mn max@media:$mx)"

# 4. viewport meta
[ "$(cnt 'name=.viewport')" -gt 0 ] && row PASS "viewport meta есть" || row FAIL "нет viewport meta"

# 5. Автономность — нет CDN
[ "$(cnt 'cdn\.|bootstrap|tailwind|jquery|cdnjs')" -eq 0 ] && row PASS "без CDN" || row WARN "найден CDN/фреймворк"

# 6. Внешние URL только наши/клиента/шрифты
ext=$(grep -oE 'https?://[^"ّ'"'"'> )]+' "$F" 2>/dev/null | grep -viE "artvision\.pro|fonts\.(googleapis|gstatic)|${DOM:-NOCLIENTDOMAIN}" | sort -u)
if [ -z "$ext" ]; then row PASS "внешних URL (чужих) нет"; else row WARN "сторонние URL: $(print "$ext"|tr '\n' ' ')"; fi

# 7. Блок методологии/источников (calculations-need-sources.md)
[ "$(cnt 'методолог|источник')" -gt 0 ] && row PASS "блок методологии/источников есть" || row FAIL "нет блока «Методология и источники»"

# 8. Даты у данных
[ "$(grep -coE '[0-9]{2}\.[0-9]{2}\.20[0-9]{2}|20[0-9]{2}' "$F" 2>/dev/null)" -gt 0 ] && row PASS "даты данных присутствуют" || row WARN "не вижу дат снятия данных"

# 9. Бренд Artvision
[ "$(cnt 'artvision')" -gt 0 ] && row PASS "бренд Artvision есть" || row FAIL "нет бренда Artvision (прямой клиент)"

# 10. «Задать вопрос» (канал вопросов клиента)
[ "$(cnt 'задать вопрос|задайте вопрос|обсудить')" -gt 0 ] && row PASS "кнопка вопросов есть" || row WARN "нет «Задать вопрос»"

# 11. Цены/тарифы (₽)
[ "$(grep -coE '[0-9][0-9 ]*(000|К)[^<]{0,4}₽|₽' "$F" 2>/dev/null)" -gt 0 ] && row PASS "цены/тарифы указаны" || row WARN "не вижу цен (₽)"

# 12. TOC / содержание (core.md — HTML с TOC)
[ "$(cnt 'содержание|class=.toc|kp-toc|оглавление')" -gt 0 ] && row PASS "TOC/содержание есть" || row WARN "нет оглавления"

# 13. robots noindex (review-страница)
[ "$(cnt 'noindex')" -gt 0 ] && row PASS "noindex (тестовая страница)" || row WARN "нет noindex — если review-URL, добавь"

# 14. Структура: таблицы/списки (document-list-format)
[ "$(cnt '<table|<ul|<ol')" -gt 0 ] && row PASS "таблицы/списки есть" || row WARN "мало структуры (списки/таблицы)"

print "────────────────────────────────────────"
sz=$(du -h "$F"|cut -f1)
print "ИТОГ: ✅ $pass  ·  🟡 $warn  ·  ❌ $fail   (размер $sz)"
if [ "$fail" -gt 0 ]; then
  print "ВЕРДИКТ: ❌ НЕ отправлять — есть FAIL. Исправить, прогнать снова."
  exit 1
elif [ "$warn" -gt 2 ]; then
  print "ВЕРДИКТ: 🟡 REVIEW — много WARN, глянь перед отправкой."
  exit 0
else
  print "ВЕРДИКТ: ✅ структурно ОК (числа/смысл — отдельно через /factcheck + ревью)."
  exit 0
fi
