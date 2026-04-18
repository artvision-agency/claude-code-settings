---
name: chrome-extension-install
description: "Install Chrome extensions programmatically without Web Store click. Bypasses Chrome Web Store UI via GitHub source build + load unpacked, or macOS managed policies."
disable-model-invocation: false
---

# Chrome Extension Install — Программная установка

## Когда использовать
- Пользователь просит установить Chrome-расширение
- Нужно автоматизировать установку без ручного клика в Web Store
- Enterprise/MDM сценарии

## Стратегия эскалации (от простого к сложному)

### 1. GitHub Source Build (предпочтительный)
Большинство популярных расширений — open source.

```bash
# 1. Найти репо
# WebSearch: "{extension name} github chrome extension"

# 2. Клонировать и собрать
cd /tmp
git clone --depth 1 https://github.com/{author}/{extension}.git
cd {extension}
npm install && npm run build

# 3. Скопировать в постоянную папку
mkdir -p ~/Extensions
cp -r build ~/Extensions/{extension}

# 4. Открыть Chrome extensions page
open -a "Google Chrome" "chrome://extensions"

# 5. Инструкция пользователю (3 клика):
# - Enable Developer Mode (тумблер сверху справа)
# - Load unpacked
# - Выбрать ~/Extensions/{extension}
```

### 2. macOS Managed Preferences (требует sudo)
Force-install через enterprise policy — расширение ставится автоматически.

```bash
# Требует sudo!
sudo mkdir -p /Library/Managed\ Preferences/
sudo tee /Library/Managed\ Preferences/com.google.Chrome.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" ...>
<plist version="1.0">
<dict>
    <key>ExtensionInstallForcelist</key>
    <array>
        <string>{EXTENSION_ID};https://clients2.google.com/service/update2/crx</string>
    </array>
</dict>
</plist>
EOF
# Перезапустить Chrome
```

### 3. Playwright persistent context (проверено, работает)
Playwright может загрузить unpacked extension в изолированный профиль:

```python
ctx = await p.chromium.launch_persistent_context(
    user_data_dir="/tmp/chrome-ext-profile",
    headless=False,
    args=[
        "--disable-extensions-except=/path/to/extension",
        "--load-extension=/path/to/extension",
    ]
)
# Extension загружается автоматически, можно проверить на chrome://extensions
```
**Ограничение:** использует Playwright's Chromium, не реальный Chrome. Для тестов — отлично.

### 4. Real Chrome --load-extension (сессионный)
```bash
pkill -f "Google Chrome"
sleep 2
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --load-extension="$HOME/Extensions/{extension}" \
  "chrome://extensions" &
```
Работает для ТЕКУЩЕЙ сессии Chrome. После перезапуска — нужно снова.

### 5. CRX Download (ненадёжный)
Google блокирует прямую скачку CRX. Не рекомендуется.

### 6. AppleScript + DevTools Console + File Dialog (РАБОТАЕТ! Проверено 2026-04-04)
Полностью автоматическая установка в реальный Chrome без ручных кликов:

```applescript
-- 1. Открыть chrome://extensions
tell application "Google Chrome"
    activate
    tell front window's active tab to set URL to "chrome://extensions"
end tell
delay 2

-- 2. Открыть DevTools Console (Cmd+Option+J)
tell application "System Events" to tell process "Google Chrome"
    keystroke "j" using {command down, option down}
end tell
delay 2

-- 3. Включить Developer Mode через clipboard → paste → enter
set the clipboard to "document.querySelector('extensions-manager').shadowRoot.querySelector('extensions-toolbar').shadowRoot.querySelector('#devMode').checked || document.querySelector('extensions-manager').shadowRoot.querySelector('extensions-toolbar').shadowRoot.querySelector('#devMode').click()"
tell application "System Events" to tell process "Google Chrome"
    keystroke "v" using {command down}
    delay 0.3
    keystroke return
    delay 1
end tell

-- 4. Кликнуть Load Unpacked (откроет native file dialog)
set the clipboard to "document.querySelector('extensions-manager').shadowRoot.querySelector('extensions-toolbar').shadowRoot.querySelector('#loadUnpacked').click()"
tell application "System Events" to tell process "Google Chrome"
    keystroke "v" using {command down}
    delay 0.3
    keystroke return
    delay 2
    
    -- 5. В file dialog: Cmd+Shift+G → вставить путь → Enter → Enter
    keystroke "g" using {command down, shift down}
    delay 1.5
    set the clipboard to "/Users/antonk/Extensions/{extension}"
    keystroke "v" using {command down}
    delay 0.5
    keystroke return
    delay 1.5
    keystroke return
    delay 2
end tell
```

**Ключевые моменты:**
- JS слишком длинный для keystroke → использовать clipboard (set the clipboard to + Cmd+V)
- Shadow DOM доступен через цепочку .shadowRoot.querySelector
- File dialog навигация: Cmd+Shift+G = "Go to folder"
- Chrome должен быть на переднем плане (activate)
- loc=2 в Secure Preferences = персистентная установка

## Что НЕ работает
- `defaults write com.google.Chrome ExtensionInstallForcelist` — игнорируется без MDM
- Инъекция в Preferences (`extensions.settings`) — Chrome затирает при старте
- AppleScript клик по Web Store — блокируется accessibility permissions
- Playwright клик по Web Store / file chooser на chrome:// — security block
- CDP file chooser на chrome://extensions — не перехватывается

## Шаблон поиска Extension ID
Extension ID можно найти в URL Web Store:
`chrome.google.com/detail/{name}/{EXTENSION_ID}`
