# HANDOVER — Reels publish + gallery + cons/swarm hook

**Сессия:** c052407c (15.05 — 30.05) · **Контекст:** 689% при handover

## Что сделано (live)

### YouTube @-Artvisionpro (public, live)
- V1 CTR теория — https://youtube.com/shorts/QXKl4M8Xy_A
- V2 Шиномонтаж — https://youtube.com/shorts/CBegu9ExNKo
- Playlist «SEO и реклама — короткие разборы» — https://youtube.com/playlist?list=PLKVhcNIgi0y2_wLRSNUCYTfPjCENtly8k
- Описания cross-linked (V1↔V2)
- **Канал подтверждён:** UCjscpShycpJCA5sRRuumijg

### VPS галерея (artvision.pro/internal/reels-week/)
- 37 роликов, mobile-first TikTok-style (scroll-snap 100dvh, IntersectionObserver autoplay, tap=unmute)
- 3 heavy-edit (V1 CTR 14MB · V2 Шиномонтаж 14MB · v3/p1/v4 PREMIUM по 4 формата) + 34 refresh-batch
- v3 PiP headroom fix (crop Y 200→170)
- v4 mobile scroll (Playwright viewport 390×844 + iPhone UA → @media срабатывает)
- TG-ссылки → Антон + recap

### Cons/swarm disambiguation
- Hook `~/.claude/hooks/pre-tool-cons-vs-swarm-disambiguate.sh` (warn-only PreToolUse Skill)
- Memory `feedback_cons_vs_swarm_disambiguate.md`
- CLAUDE.md routing: рой=/swarm (ДЕЛАТЬ), cons=ДУМАТЬ, mixed промпт = cons→swarm пайплайн

## Что блокировано (нужно от Антона)

### TG-канал «Артвижн про маркетинг»
- НЕ опубликовано (V1+V2 ждут)
- Блокер: **нет @username канала** (или t.me/... ссылки)
- `@avportal_bot` getUpdates видит только 3 чата, канала среди них нет
- Действие: Антон → даёт ссылку на канал ИЛИ добавляет `@avportal_bot` в админы канала с правом «Публикация»

### VK Клипы
- НЕ опубликовано
- Блокер: VK-токена в tokens.json нет (проверено: `vk`/`vkontakte`/`clip` ключи отсутствуют)
- /crosspost skill — для X/LinkedIn/Threads/Bluesky, не VK
- Опции: (1) API-токен с scope `video` для `shortVideo.create` (недокументированный, research-verified — habr q/864545); (2) Playwright через залогиненный Chrome Антона

### RuTube
- НЕ опубликовано
- Блокер: публичного API нет (research-verified: github discussion #165690, partner-only)
- Опция: Playwright через rutube.ru/studio

### Instagram Reels
- НЕ опубликовано
- Блокер: Meta заблокирована в РФ (юр.риск), нужен VPN + IG Business

## Файлы

- Publish-pack: `personal/social_clips/2026-05-12-research-video/publish-pack/PUBLISHED-URLS.md`
- Скрипт upload (рабочий v2 OAuth): `/tmp/yt_upload_v2.py` — **скилл `/youtube-publish/upload.py` захардкожен на протухший youtube_token.json, надо починить на v2-токен**
- Goal-файлы: `goals/GOAL_shorts-pipeline-audit_2026-05-16.md`, `goals/audit-content-qa-2026-05-16.md`, `goals/audit-montage-pip-2026-05-16.md`, `goals/synthesis-shorts-audit-2026-05-16.md`, `goals/factcheck-shorts-results-2026-05-18.md`, `goals/GOAL_show-refresh-reels_2026-05-17.md`

## Решения зафиксированы

- PREMIUM (preset slow + CRF 16 single-pass composition) = дефолт для всех Shorts с 16.05 — `~/.claude/rules/shorts-pip-composition.md` секция «PREMIUM качество»
- v4 mobile-scroll: viewport CSS pixels < 760 → mobile @media (правило в shorts-pip-composition.md)

## Следующие шаги (по приоритету)

1. Антон даёт TG-канал @username → залив V1+V2 в канал (1 минута)
2. Антон даёт VK-токен ИЛИ подтверждает Playwright-путь → VK Клипы V1+V2
3. RuTube Playwright (закрытое окно — нужен Chrome закрыть, профиль Антона)
4. Починить `/youtube-publish/upload.py` чтобы брал `youtube_token_v2.json` (5-минутный фикс)
