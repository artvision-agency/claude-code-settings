---
name: usmile-photos
description: USmile — конвейер фото пациентов до/после из облака в лендинги. Качает из cloud.mail.ru → коммитит в git (anti-rewind #31) → вшивает СОГЛАСОВАННЫЕ (ФЗ-323) before/after в лендинги → verify. Решает корень: фото пациентов дважды стирались git-rewind как untracked. Триггеры — 'фото usmile', 'usmile photos', 'вшить кейсы usmile', 'где фото usmile', 'скачать фото пациентов usmile', 'до/после usmile', 'фото на лендинг usmile'.
---

# USmile Photos Pipeline

> **Зачем скилл:** фото пациентов (~126, облако) ДВАЖДЫ стирались git-rewind (#31) как untracked → лендинги тонкие, каждый раз заново. Скилл = один вызываемый процесс, ничего не забываем, ничего не ломается.
> **Связано:** `asset-capture-no-loss.md`, `determinism-first-and-verify.md`, `legal-team-engagement.md` (ФЗ-323), `image-edit-preserve-subjects.md`, `checks-by-validators-multimodel.md`.

## Источник (один на всё)
- **Облако:** `cloud.mail.ru/public/EQdX/kFrPVMdS8` — ~126 фото до/после.
- **Доступ:** `artvision.pro@mail.ru` / пароль в `clients/usmile/access.md` — ТОЛЬКО браузер/agent-browser (НЕ IMAP).
- **Согласие ФЗ-323 — ТОЛЬКО 8 фамилий:** Качан, Бегунова, Зимаков, Сусленников, Тофанюк, Кныш, Старцева, ТофанюкТА. Остальных НЕ публиковать.
- Скрипт: `clients/usmile/scripts/usmile_photos.py`

## 🔴 Корень бага «фото пропадают» (#31)
Скачанные фото лежали в **untracked**-каталоге → `git rebase`/rewind стирал. **Гарантия:** ничего не «готово» пока не `git add` + проверка `git diff --cached`. Каталог-источник истины: `assets/photos/cases-cloud/` (TRACKED).

## Шаги

### 1. download (agent-browser — НЕ детерминируется в bash)
```
Skill agent-browser → cloud.mail.ru/public/EQdX/kFrPVMdS8
логин artvision.pro@mail.ru (пароль из access.md)
скачать все → clients/usmile/assets/photos/cases-cloud/
```
Идемпотентно: уже скачанные (по имени/хешу) пропускать.

### 2. track (anti-rewind — КРИТИЧНО, делать СРАЗУ после скачивания)
```bash
python3 clients/usmile/scripts/usmile_photos.py track
```
git add + GATE-проверка `git diff --cached`. Без этого rewind сотрёт снова.

### 3. manifest (консент-фильтр ФЗ-323)
```bash
python3 clients/usmile/scripts/usmile_photos.py manifest
```
Показывает какие файлы публикабельны (согласованные фамилии) vs нет.

### 4. wire (вшить в лендинг — с бэкапом, только согласованные)
- Бэкап страницы перед правкой (`cp page.html page.html.bak`).
- Вшить before/after ТОЛЬКО согласованных в блок «Результаты работ» (эталон вёрстки — `pages/allon4-final.html`).
- Подпись юр-корректная: «Публикация медматериалов с письменного согласия пациента (ФЗ-323)» — НЕ только ФЗ-152.
- ⚠️ Цели: `pages/odnomomentnaya-implantaciya-landing.html` (имплант-кейсы), `pages/parodontologiya-landing.html` (плейсхолдеры «Фото до/после»).

### 5. verify (gate перед «готово»)
```bash
python3 clients/usmile/scripts/usmile_photos.py verify   # PASS только если tracked + не пусто
```
+ скриншот лендинга (ui-visual-validator 375+1440) — фото реально рендерятся.

### 6. commit + deploy review-URL
git commit (один источник = кейсы + РСЯ-баннеры) → deploy `_priv-usmile-*` → Антону на одобрение.

## 🔴 Юр-блокер (нашёл Codex 26.06)
`allon4-final.html` содержит фото «Нина Николаевна» — её НЕТ в 8 согласованных → **ФЗ-323 риск**. Решить с Антоном/юр-командой (`legal-team-engagement.md`) ДО показа клиенту.

## Антипаттерны
- ❌ Скачать фото и не `git add` (rewind сотрёт — корень #31).
- ❌ Публиковать фото пациента вне 8 согласованных (ФЗ-323).
- ❌ Вшить без бэкапа страницы / без verify-скриншота.
- ❌ Считать «готово» пока `git diff --cached` пуст.
