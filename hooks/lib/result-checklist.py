#!/usr/bin/env python3
# Логика stop-result-checklist: если последний ответ заявляет РЕЗУЛЬТАТ
# (готово/деплой/вот ссылк/PASS/HTTP 200), рендерит чек-бокс-таблицу из
# секции "Acceptance criteria" текущего recap. Детерминированно, ~0 токенов.
# stdin = JSON Stop-хука. Печатает напоминание в stdout. Никогда не блокирует.
import sys, json, os, re

def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    if not isinstance(data, dict):
        return 0

    sid = data.get("session_id", "") or ""
    transcript = data.get("transcript_path", "") or ""

    # 1. Последний текст ассистента из transcript (jsonl)
    last_text = ""
    if transcript and os.path.isfile(transcript):
        try:
            with open(transcript, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            for ln in reversed(lines[-40:]):
                try:
                    rec = json.loads(ln)
                except Exception:
                    continue
                if rec.get("type") != "assistant":
                    continue
                msg = rec.get("message", {})
                parts = msg.get("content", [])
                if isinstance(parts, list):
                    txt = " ".join(p.get("text", "") for p in parts if isinstance(p, dict) and p.get("type") == "text")
                else:
                    txt = str(parts)
                if txt.strip():
                    last_text = txt
                    break
        except Exception:
            pass

    # 2. Детект заявления результата
    claim = re.compile(r"(готов[оаы]|деплой|вот ссылк|развернул|задеплоил|PASS\b|HTTP\s*200|результат готов|можно отправлять|сделано ✅|✅ готов)", re.I)
    if not last_text or not claim.search(last_text):
        return 0

    # 3. Acceptance criteria из recap
    home = os.path.expanduser("~")
    recap = os.path.join(home, "artvision-data", "sync", "recaps", sid + ".md")
    crits = []
    if os.path.isfile(recap):
        try:
            with open(recap, "r", encoding="utf-8", errors="ignore") as f:
                rc = f.read()
            m = re.search(r"##\s*Acceptance criteria(.*?)(\n##\s|\Z)", rc, re.S)
            if m:
                for line in m.group(1).splitlines():
                    s = line.strip()
                    mm = re.match(r"^- \[[ xX]\]\s*(.+)$", s)
                    if mm:
                        item = mm.group(1).strip()
                        if item and "не заполнено" not in item.lower():
                            crits.append(item)
        except Exception:
            pass

    # 4. Рендер напоминания
    out = []
    out.append("─────────────────────────────────────────")
    out.append("✅ РЕЗУЛЬТАТ ЗАЯВЛЕН — покажи чек-бокс-таблицу (правило single-table-progress-report).")
    if crits:
        out.append("Acceptance criteria из recap — проставь статус ✅/❌/⏳ по факту:")
        out.append("")
        out.append("| # | Требование | Статус |")
        out.append("|---|------------|:------:|")
        for i, c in enumerate(crits, 1):
            c = c.replace("|", "/")
            out.append("| %d | %s | ⬜ |" % (i, c))
        out.append("")
        out.append("Заполни статусы фактом (это твоё суждение, не выдумывай ✅).")
    else:
        out.append("В recap секция Acceptance criteria пуста — выпиши требования сессии таблицей вручную.")
    out.append("Bypass: RESULT_CHECKLIST_OFF=1")
    out.append("─────────────────────────────────────────")
    sys.stdout.write("\n".join(out) + "\n")
    return 0

if __name__ == "__main__":
    sys.exit(main())
