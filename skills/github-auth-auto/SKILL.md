---
name: github-auth-auto
description: Автоматическая авторизация в GitHub без участия Антона. Когда tokens.json.github.primary истёк (gh api возвращает 401), скилл сам запускает gh auth device flow, читает код, открывает github.com/login/device в Safari, через AppleScript + JavaScript вводит код и нажимает кнопки. Работает благодаря: (a) Ghostty имеет Accessibility permission, (b) Safari "Allow JavaScript from Apple Events" включён, (c) Safari уже залогинен как justtrance-web. Если Safari НЕ залогинен — скилл остановится на auth page и попросит Антона ввести креды. Триггеры — 'github token', 'gh auth', 'форк репо', 'токен протух', 'fork repo to artvision-agency'.
---

# github-auth-auto — GitHub OAuth без рук

## Когда срабатывать
- `gh auth status` показывает invalid token / 401
- Нужно форкнуть репо / создать репо / push в artvision-agency, а токены протухли
- Любая операция требующая свежий токен на github.com/settings/tokens

## Пререквизиты (проверить перед запуском)
```bash
# 1. Ghostty accessibility (osascript работает без ошибок)
osascript -e 'tell application "System Events" to keystroke ""' 2>&1 | grep -qi "not authorized" && echo "NEED_ACCESSIBILITY" || echo "OK"

# 2. Safari JS automation
defaults read com.apple.Safari AllowJavaScriptFromAppleEvents 2>/dev/null | grep -q 1 || \
  defaults write com.apple.Safari AllowJavaScriptFromAppleEvents -bool true

# 3. Safari залогинен в GitHub (проверяется косвенно — если после открытия URL попадаем на /select_account, значит OK; если на /login — нужны креды)
```

## Алгоритм

1. **Запустить gh device flow в фоне:**
```bash
gh auth login --git-protocol https --hostname github.com --web --scopes "repo,workflow" > /tmp/gh-auth.log 2>&1 &
```

2. **Дождаться кода** (Monitor tool с until-циклом):
```bash
until grep -E "one-time code" /tmp/gh-auth.log; do sleep 1; done
CODE=$(grep "one-time code" /tmp/gh-auth.log | grep -oE '[A-Z0-9]{4}-[A-Z0-9]{4}')
```

3. **Открыть URL в Safari и подождать загрузки:**
```applescript
tell application "Safari"
    activate
    if (count of documents) is 0 then
        make new document with properties {URL:"https://github.com/login/device"}
    else
        set URL of front document to "https://github.com/login/device"
    end if
end tell
```

4. **Проверить текущий URL после редиректа:**
   - `/select_account` → залогинен, идти дальше
   - `/login` → СТОП, сказать Антону "Safari не залогинен, нужны креды"

5. **Клик Continue на /select_account:**
```applescript
do JavaScript "Array.from(document.querySelectorAll('button,input[type=submit]')).find(b => (b.textContent||b.value).trim() === 'Continue').click()" in front document
```

6. **Ввести код на /device (8 однобуквенных input-ов, пропустить тире):**
```javascript
var code = 'XXXX-XXXX'.replace('-','').split('');
var inputs = Array.from(document.querySelectorAll('input')).filter(i => i.type !== 'hidden' && !i.disabled);
var setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;
var f=0;
for (var i=0; i<inputs.length && f<code.length; i++) {
  inputs[i].focus();
  setter.call(inputs[i], code[f]);
  inputs[i].dispatchEvent(new Event('input',{bubbles:true}));
  inputs[i].dispatchEvent(new Event('change',{bubbles:true}));
  f++;
}
```
GitHub авто-submit при вводе последнего символа. Если нет — клик Continue.

7. **Дождаться `/success` в URL** → gh auth process завершится автоматом.

8. **Сохранить новый токен в tokens.json:**
```bash
NEW=$(gh auth token)
python3 -c "
import json, datetime
with open('/Users/antonk/artvision-data/tokens.json') as f: t=json.load(f)
t['github']['primary']={'token':'$NEW','created':'$(date +%F)','status':'active','scopes':'repo,workflow,gist,read:org'}
t['github']['token']='$NEW'; t['_updated']='$(date +%F)'
open('/Users/antonk/artvision-data/tokens.json','w').write(json.dumps(t,indent=2,ensure_ascii=False))
"
```

9. **Сообщить Антону** что токен обновлён и можно продолжать (форк/push/etc). Коммит tokens.json — confirm level (не AUTO, tokens.json требует согласия).

## Известные подводные камни

| Проблема | Решение |
|----------|---------|
| "JS BLOCKED" в AppleScript | `defaults write com.apple.Safari AllowJavaScriptFromAppleEvents -bool true` + рестарт Safari |
| Safari редиректит на /login | Антон должен залогиниться руками ОДИН раз, дальше сессия держится |
| Device code таймаут (~15 мин) | Перезапустить `gh auth login --web` с новым кодом |
| Accessibility prompt Ghostty | System Settings → Privacy → Accessibility → Ghostty ON (одноразово) |

## История

- **2026-04-18:** Созданo после инцидента. Антон просил форк 5 репо, оба токена в tokens.json были отмечены `active` но 401'или. Ручной flow занял ~20 мин переговоров о правильном решении. Автоматизировано через Safari AppleScript + JS injection. Следующая авторизация должна занять <30 сек без участия.
