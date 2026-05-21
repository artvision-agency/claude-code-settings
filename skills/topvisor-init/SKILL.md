---
name: topvisor-init
description: Завести нового клиента в Topvisor (проект + ключи + конкуренты + регион) за одну команду. Читает clients/<slug>/seo/queries.txt + competitors.txt + config.yaml. Триггеры — topvisor init, topvisor-init, заведи в топвизор, новый проект топвизор, topvisor onboard, topvisor bootstrap, добавь клиента в топвизор.
---

# /topvisor-init — Topvisor onboarding в одну команду

Создаёт Topvisor проект для клиента: проект + группа ключей + конкуренты. Регионы и snapshot — автоматически из defaults аккаунта dune87 (СПб + Москва + Екатеринбург, depth=100).

## Вызов

```
/topvisor-init <slug>
```

Где `<slug>` — папка клиента в `~/artvision-data/clients/<slug>/`.

## Что должно быть в папке клиента

```
clients/<slug>/
├── config.yaml           # site, region (опц., default СПб)
├── seo/
│   ├── queries.txt       # 1 запрос на строку (10-50 шт)
│   └── competitors.txt   # 1 домен на строку (2-5 шт)
```

Если queries.txt или competitors.txt нет — спросить Антона, не запускать.

## Алгоритм

1. **Read** `clients/<slug>/config.yaml` — извлечь `site` (если нет — спросить)
2. **Read** `seo/queries.txt` + `seo/competitors.txt`
3. **Punycode** для кириллических доменов конкурентов (`с-лог.рф` → `xn----ftbxmm.xn--p1ai`)
4. **Estimate cost** — 25 ключей × 2 ПС × 0.19 RUB ≈ 10 RUB
5. **CONFIRM** — показать summary + спросить Антона перед запуском (деньги)
6. **Run** `scripts/presale/topvisor_bootstrap.py --domain <site> --region <region> --keywords ... --competitors ... --skip-polling`
7. **Save** project_id в `clients/<slug>/topvisor_project_id.txt`
8. **Append** запись в `clients/<slug>/context-log.md`:
   - project_id, URL `/project/dynamics/<pid>/`, кол-во ключей, конкуренты, регион
9. **Commit** изменения в git (auto-sync hook сам подхватит)

## Известные quirks (важно при использовании)

См. `~/.claude/projects/-Users-antonk/memory/feedback_topvisor_api_v2_quirks.md`:

- API endpoint = `add/projects_2/projects` (НЕ `projects/projects`)
- Параметр `url=` (НЕ `site=`)
- Searcher region НЕ настраивать через API — defaults аккаунта подхватываются автоматически
- Конкуренты активны сразу через `add/projects_2/competitors` с `urls[]`
- UI URL формат — `/project/<section>/<pid>/`, НЕ `/positions/?project_id=`

## Безопасность

- Только EQUALS [PID] для `checker/go` (см. `feedback_topvisor_filter_safety.md` — broadcast сжигает баланс)
- Hook `pre-bash-topvisor-guard.sh` блокирует NOT_IN/MATCH/EXISTS

## Прецедент

Session 87d9412c (2026-05-20) — na-sklad.ru → project 28545848, 25 ключей, 3 конкурента, snapshot снят автоматически за 10 RUB.

## Анти-паттерны

- ❌ Запускать без queries.txt+competitors.txt — теряем смысл (что снимать без ключей?)
- ❌ Создавать проект через UI вручную — может создаться дубль если API уже сделал
- ❌ Игнорировать CONFIRM перед запуском — это деньги клиента в Topvisor аккаунте

## Связанные скиллы

- `/new-client` — онбординг с нуля, может предлагать `/topvisor-init` как доп. шаг
- `/seo-master` — полный SEO-аудит, использует Topvisor позиции
- `/client-monitor` — еженедельный мониторинг (будет использовать данные Topvisor проекта)
