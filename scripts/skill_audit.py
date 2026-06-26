#!/usr/bin/env python3
"""
skill_audit.py — ЗЕРО-ТОКЕН аудит скиллов: конфликты триггеров, близнецы, полнота.

Зачем: то что мы делаем руками в чате (ищем дубли/конфликты) — здесь детерминированно,
0 LLM-токенов. Парсит SKILL.md frontmatter, находит:
  • КОНФЛИКТ триггеров — один триггер → 2+ скилла (fuzzy выбирает наугад)
  • БЛИЗНЕЦЫ — высокое сходство описаний (кандидаты на слияние)
  • ПОЛНОТА — тонкие скиллы (мало строк/без структуры)

Запуск:
  python3 skill_audit.py [prefix]        # все, или только с префиксом (напр. seo)
  python3 skill_audit.py seo --twins 0.5 # порог сходства близнецов

НЕ удаляет и не правит — только отчёт. Решение о слиянии — человек.
"""
import sys, os, re
from pathlib import Path

SKILLS = Path.home() / ".claude" / "skills"
STOP = set("seo the a to of and for in on with this when user use если для что как сайта аудит site page pages content data анализ skill триггеры triggers".split())


def parse(skill_dir):
    f = skill_dir / "SKILL.md"
    txt = f.read_text(encoding="utf-8", errors="ignore")
    name = skill_dir.name
    m = re.search(r'^description:\s*["\']?(.+?)["\']?\s*$', txt, re.M | re.S)
    desc = (m.group(1) if m else "").split("\n")[0]
    # ЯВНЫЕ триггеры = все фразы в кавычках в описании (так скиллы объявляют триггеры)
    trigs = set(t.strip().lower() for t in re.findall(r"['\"]([^'\"]{2,40})['\"]", desc)
                if len(t.strip()) >= 3 and t.strip().lower() not in STOP)
    # ключевые слова описания (для коллизий и сходства)
    words = set(w for w in re.findall(r'[a-zа-яё][a-zа-яё\-]{3,}', desc.lower()) if w not in STOP)
    lines = txt.count("\n") + 1
    refs = sum(1 for p in skill_dir.iterdir() if p.name != "SKILL.md")
    return dict(name=name, desc=desc[:120], trigs=trigs, words=words, lines=lines, refs=refs)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    prefix = args[0] if args else ""
    thr = 0.45
    if "--twins" in sys.argv:
        thr = float(sys.argv[sys.argv.index("--twins") + 1])

    skills = [parse(d) for d in sorted(SKILLS.iterdir())
              if d.is_dir() and (d / "SKILL.md").exists() and d.name.startswith(prefix)]
    print(f"=== skill_audit: {len(skills)} скиллов" + (f" (префикс '{prefix}')" if prefix else "") + " ===\n")

    # 1. КОНФЛИКТ ТРИГГЕРОВ (по ЯВНЫМ триггер-фразам в кавычках)
    wmap = {}
    for s in skills:
        for w in s["trigs"]:
            wmap.setdefault(w, []).append(s["name"])
    coll = {w: ss for w, ss in wmap.items() if len(ss) >= 2}
    print("── 1. КОНФЛИКТ ТРИГГЕРОВ (одна явная триггер-фраза → 2+ скиллов) ──")
    if not coll:
        print("  ✅ нет коллизий явных триггеров")
    for w, ss in sorted(coll.items(), key=lambda x: -len(x[1]))[:15]:
        print(f"  🔴 «{w}» → {len(ss)}: {', '.join(s.replace(prefix+'-','') for s in ss)}")

    # 2. БЛИЗНЕЦЫ (Jaccard описаний ≥ thr)
    print(f"\n── 2. БЛИЗНЕЦЫ (сходство описаний ≥ {thr}, кандидаты на слияние) ──")
    twins = []
    for i in range(len(skills)):
        for j in range(i + 1, len(skills)):
            a, b = skills[i]["words"], skills[j]["words"]
            if not a or not b:
                continue
            jac = len(a & b) / len(a | b)
            if jac >= thr:
                twins.append((jac, skills[i]["name"], skills[j]["name"]))
    if not twins:
        print("  ✅ нет явных близнецов")
    for jac, a, b in sorted(twins, reverse=True)[:15]:
        print(f"  🟡 {jac:.2f}  {a}  ≈  {b}")

    # 3. ПОЛНОТА (тонкие)
    print("\n── 3. ПОЛНОТА (тонкие: <60 строк И 0 доп.файлов) ──")
    thin = [s for s in skills if s["lines"] < 60 and s["refs"] == 0]
    if not thin:
        print("  ✅ нет подозрительно тонких")
    for s in sorted(thin, key=lambda x: x["lines"]):
        print(f"  ⚠️ {s['name']} — {s['lines']} стр")

    print(f"\n── ИТОГ ── конфликтов: {len(coll)} | близнецов: {len(twins)} | тонких: {len(thin)}")
    print("Решение о слиянии/разводе триггеров — человек. Этот отчёт = 0 LLM-токенов.")


if __name__ == "__main__":
    main()
