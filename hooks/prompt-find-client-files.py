#!/usr/bin/env python3
"""
UserPromptSubmit hook: авто-поиск файлов клиента через Spotlight (mdfind).
0 токенов LLM на сам поиск — инжектит готовые пути в контекст.
inject-only: всегда exit 0; печатает блок в stdout = additionalContext.
"""
import sys, json, re, subprocess, os, time

HOME = os.path.expanduser("~")

# Триггер: глагол/вопрос поиска + объект (файл/КП/аудит/...) ИЛИ «смотри на компе/диске»
TRIGGER = re.compile(
    r"(найд|покаж|где\b|восстанов|locate|find|search)"
    r".{0,40}"
    r"(файл|докум|кп\b|коммерч|предлож|аудит|отч[её]т|презентац|макет|html|"
    r"стат[иь]стик|договор|последн|делал)"
    r"|смотри\s+(на\s+)?(комп|диск|drive)"
    r"|что\s+делал[аи]?\s+для",
    re.IGNORECASE,
)

STOP = set("""найди найти покажи показать где восстанови locate find search файл файлы
документ документы кп коммерческое предложение аудит отчёт отчет презентация презентацию
макет html статистика статистику договор последние последний делали делал смотри компе
диске комп диск drive что для по на в и с the a of for client клиент клиента клиенту
мне нам наш наши был были это эта этот пожалуйста плиз дай давай можешь сделай""".split())

def extract_terms(prompt: str):
    # слова кириллица/латиница длиной >3, не стоп-слова
    words = re.findall(r"[A-Za-zА-Яа-яЁё][A-Za-zА-Яа-яЁё0-9.-]{2,}", prompt)
    terms = []
    for w in words:
        lw = w.lower()
        if lw in STOP or len(lw) < 4:
            continue
        terms.append(w)
    # уникальные, до 3 (имя клиента обычно 1-2 слова)
    seen = []
    for t in terms:
        if t.lower() not in [x.lower() for x in seen]:
            seen.append(t)
    return seen[:3]

NOISE = ("/logs/", "/.backups/", "/tokens/", "/prompts/", "/.cache/",
         "/.Trash/", "/__pycache__/", ".log", ".DS_Store", "/sessions/",
         "/recaps/", "/.codex/", "/shell-snapshots/")

def _mdfind(args, timeout=4):
    try:
        return subprocess.run(["mdfind", *args], capture_output=True,
                              text=True, timeout=timeout).stdout.splitlines()
    except Exception:
        return []

def mdfind(term: str, limit: int = 12):
    # priority 3 = term в ИМЕНИ файла, 2 = в ПУТИ, 1 = только в содержимом
    by_name = set(_mdfind(["-onlyin", HOME, "-name", term]))
    full = _mdfind(["-onlyin", HOME, term])
    cand = {}
    tl = term.lower()
    for p in list(by_name) + full:
        if any(n in p for n in NOISE) or "/.git/" in p or "/node_modules/" in p \
           or p.startswith(os.path.join(HOME, "Library")):
            continue
        if not os.path.isfile(p) or p in cand:
            continue
        try:
            st = os.stat(p)
        except OSError:
            continue
        base = os.path.basename(p).lower()
        prio = 3 if (p in by_name or tl in base) else (2 if tl in p.lower() else 1)
        cand[p] = (prio, st.st_mtime, st.st_size, p)
    res = sorted(cand.values(), reverse=True)  # prio desc, then mtime desc
    return [(mt, sz, p) for (_prio, mt, sz, p) in res[:limit]]

def main():
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except Exception:
        return
    prompt = data.get("prompt", "") or ""
    if not prompt or not TRIGGER.search(prompt):
        return
    terms = extract_terms(prompt)
    if not terms:
        return

    found = []
    seen_paths = set()
    for t in terms:
        for mt, sz, p in mdfind(t):
            if p in seen_paths:
                continue
            seen_paths.add(p)
            found.append((mt, sz, p))
    if not found:
        return
    found.sort(reverse=True)
    found = found[:15]

    lines = [
        "[find-client-files hook] Spotlight нашёл файлы по запросу "
        f"(термины: {', '.join(terms)}). Пути готовы — НЕ ищи заново, "
        "используй эти. Содержимое читай Read только для 1-2 нужных:",
    ]
    for mt, sz, p in found:
        d = time.strftime("%Y-%m-%d %H:%M", time.localtime(mt))
        kb = sz // 1024
        lines.append(f"  {d} | {kb}KB | {p}")
    lines.append(
        "  (полный поиск с фильтром по содержимому: "
        "find-client-files '<regex>')"
    )
    print("\n".join(lines))

if __name__ == "__main__":
    main()
