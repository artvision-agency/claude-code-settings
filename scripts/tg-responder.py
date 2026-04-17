#!/usr/bin/env python3
"""
tg-responder.py — обрабатывает необработанные ответы из tg_responses.jsonl:
  - классифицирует (confirmed/partial/blocker/ambiguous)
  - мержит в status_requests.jsonl (обновляет вопрос)
  - пишет в context-log клиента
  - если request полностью закрыт → архивирует
  - если есть ambiguous → формирует список вопросов для follow-up
    (отправка follow-up — опционально, через --auto-clarify)

Запуск:
  python3 tg-responder.py                    # обработать pending
  python3 tg-responder.py --auto-clarify     # и автоматически отправить follow-up
  python3 tg-responder.py --dry-run          # показать что сделает
"""
import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

TRACK_DIR = Path.home() / "artvision-data" / "sync" / "tg-tracking"
REQUESTS_FILE = TRACK_DIR / "status_requests.jsonl"
RESPONSES_FILE = TRACK_DIR / "tg_responses.jsonl"
ARCHIVE_DIR = TRACK_DIR / "archive"
LOG_FILE = TRACK_DIR / "responder.log"
CONTEXT_LOG_DEFAULT = Path.home() / "artvision-data" / "context-log.md"

MAX_CLARIFY = 2  # сколько раз Claude переспрашивает перед эскалацией

# Ключевые слова для классификации
PATTERNS_CONFIRMED = [
    r"\bда\b", r"\bготов(о|а|ы)?\b", r"\bdone\b", r"\bпрош(ёл|ел|ли)\b",
    r"\bзаверш(ён|ен|ено|ены)\b", r"\bопубликован", r"\bсдела(но|на|л|ла|ли|ны)\b",
    r"\bзакрыт", r"https?://", r"\bпролив\s+заверш",
]
PATTERNS_BLOCKER = [
    r"\bнет\b", r"не (сделано|закрыт|готов)", r"\bблокер\b",
    r"\bзаблок", r"\bупал", r"\bошибк",
]
PATTERNS_PARTIAL = [
    r"\bчастично\b", r"\bтолько\b", r"\bне весь\b", r"\bне вс[её]\b",
    r"\b(март|апрель|май|июнь) (есть|нет|done)", r"\+\d+", r"\b\d+\s*(из|/)\s*\d+",
]


def log(msg):
    ts = datetime.now(timezone.utc).isoformat()
    line = f"{ts} {msg}"
    print(line, flush=True)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def classify(text):
    """Возвращает (status, confidence)."""
    t = text.lower() if text else ""
    if not t.strip():
        return ("ambiguous", 0.0)

    confirmed = any(re.search(p, t) for p in PATTERNS_CONFIRMED)
    blocker = any(re.search(p, t) for p in PATTERNS_BLOCKER)
    partial = any(re.search(p, t) for p in PATTERNS_PARTIAL)

    if blocker and not confirmed:
        return ("blocker", 0.8)
    if partial or (confirmed and blocker):
        return ("partial", 0.6)
    if confirmed:
        return ("confirmed", 0.7)
    if len(t) < 4:
        return ("ambiguous", 0.2)
    return ("ambiguous", 0.4)


def read_jsonl(path):
    if not path.exists():
        return []
    out = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out


def write_jsonl(path, records):
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def mark_response_processed(resp_id):
    responses = read_jsonl(RESPONSES_FILE)
    for r in responses:
        if r.get("response_id") == resp_id:
            r["processed"] = True
    write_jsonl(RESPONSES_FILE, responses)


def update_request_with_response(requests, req_id, qn, resp):
    """Мержит ответ в вопрос. Возвращает обновлённый request."""
    for req in requests:
        if req["id"] != req_id:
            continue
        # Если qn не определён — прикрепляем как "general comment"
        if qn is None:
            req.setdefault("uncategorized_replies", []).append({
                "text": resp["text"],
                "sender": resp["sender_name"],
                "received_at": resp["received_at"],
            })
            return req
        # Иначе — обновляем конкретный вопрос
        for q in req["questions"]:
            if q["n"] == qn:
                status, conf = classify(resp["text"])
                q["status"] = status
                q["answer"] = resp["text"]
                q["answered_at"] = resp["received_at"]
                q["confidence"] = conf
                break
        return req
    return None


def is_request_complete(req):
    """Все вопросы имеют status != pending и != ambiguous."""
    return all(q["status"] in ("confirmed", "partial", "blocker") for q in req["questions"])


def ambiguous_questions(req):
    return [q for q in req["questions"] if q["status"] in ("pending", "ambiguous")]


def archive_request(req):
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    date = datetime.fromisoformat(req["sent_at"].replace("Z", "+00:00")).strftime("%Y-%m-%d")
    archive_file = ARCHIVE_DIR / f"{date}_{req['id']}.md"

    lines = [
        f"# {req['id']}",
        f"**Отправлено:** {req['sent_at']}",
        f"**Получатель:** {req['recipient']}",
        f"**msg_id:** {req['msg_id']}",
        "",
        "## Вопросы и ответы",
        "",
        "| # | Вопрос | Статус | Ответ |",
        "|---|--------|--------|-------|",
    ]
    for q in req["questions"]:
        ans = (q.get("answer") or "").replace("|", "\\|").replace("\n", " ")[:200]
        lines.append(f"| {q['n']} | {q['text']} | {q['status']} | {ans} |")

    if req.get("uncategorized_replies"):
        lines.extend(["", "## Нераспределённые реплики", ""])
        for r in req["uncategorized_replies"]:
            lines.append(f"- [{r['sender']} @ {r['received_at']}] {r['text']}")

    archive_file.write_text("\n".join(lines) + "\n")
    log(f"📦 archived: {archive_file}")


def append_context_log(req, target_path=None):
    """Append итог в context-log (по умолчанию общий; позже можно роутить по клиенту)."""
    target = Path(target_path) if target_path else CONTEXT_LOG_DEFAULT
    target.parent.mkdir(parents=True, exist_ok=True)
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    lines = [
        f"\n### {date} — TG статус-ответ: {req['recipient']} на msg_id={req['msg_id']}",
    ]
    for q in req["questions"]:
        ans = (q.get("answer") or "—")[:150]
        lines.append(f"- **{q['text']}** → `{q['status']}`: {ans}")
    if not target.exists():
        target.write_text("# Context Log\n")
    with open(target, "a") as f:
        f.write("\n".join(lines) + "\n")


CONTEXT_LOG_PATH = Path.home() / "artvision-data" / "context-log.md"
CLIENTS_DIR = Path.home() / "artvision-data" / "clients"
ARTVISION_REPO = Path.home() / "artvision-data"
STOPWORDS = {
    "и","в","на","по","для","за","с","у","к","от","до","из","а","но","или",
    "что","как","это","уже","ещё","же","ли","не","the","a","an","of","to","for"
}


def _keywords(text, min_len=4, max_kw=6):
    """Извлекает значимые слова из вопроса для поиска по логам."""
    if not text:
        return []
    words = re.findall(r"[A-Za-zА-Яа-я0-9\.\-]+", text.lower())
    kws = []
    seen = set()
    for w in words:
        if len(w) < min_len:
            continue
        if w in STOPWORDS:
            continue
        if w in seen:
            continue
        seen.add(w)
        kws.append(w)
        if len(kws) >= max_kw:
            break
    return kws


def _has_completion_marker(text):
    """Строка содержит признаки выполнения: done/готово/опубликовано/✅/URL/N/M."""
    t = text.lower() if text else ""
    return (
        any(re.search(p, t) for p in PATTERNS_CONFIRMED)
        or "✅" in text
        or "[x]" in text
    )


def _factcheck_context_log(question_text, since_hours=48):
    """
    Grep по всем clients/*/context-log.md + общий.
    Evidence зачитывается ТОЛЬКО если строка содержит:
    - минимум 2 ключевых слова вопроса
    - маркер выполнения (done/готово/URL/✅/[x]/числа X/Y)
    """
    kws = _keywords(question_text)
    if len(kws) < 2:
        return None

    candidates = []
    if CONTEXT_LOG_PATH.exists():
        candidates.append(CONTEXT_LOG_PATH)
    if CLIENTS_DIR.exists():
        candidates.extend(CLIENTS_DIR.glob("*/context-log.md"))

    cutoff = datetime.now(timezone.utc).timestamp() - since_hours * 3600

    for path in candidates:
        try:
            content = path.read_text(errors="ignore")
        except Exception:
            continue
        lines = content.splitlines()[-500:]
        # Окно вокруг совпадения: соседние строки часто содержат "сделано"
        for i, ln in enumerate(reversed(lines)):
            ln_low = ln.lower()
            matched_kws = sum(1 for k in kws if k in ln_low)
            if matched_kws < 2:
                continue
            # Проверить дату
            m = re.search(r"(\d{4}-\d{2}-\d{2})", ln)
            if m:
                try:
                    ts = datetime.strptime(m.group(1), "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()
                    if ts < cutoff:
                        continue
                except Exception:
                    pass
            # Проверить маркер выполнения — в этой строке ИЛИ в соседних 3
            idx = len(lines) - 1 - i
            window = "\n".join(lines[max(0, idx-2):min(len(lines), idx+3)])
            if not _has_completion_marker(window):
                continue
            rel = path.relative_to(Path.home() / "artvision-data") if path.is_relative_to(Path.home() / "artvision-data") else path.name
            return (ln.strip()[:200], f"context-log ({rel})")
    return None


def _factcheck_git_log(question_text, since_hours=48):
    """git log за N часов. Требуем минимум 2 keyword match + feat/fix/docs/add/publish в сообщении."""
    if not (ARTVISION_REPO / ".git").exists():
        return None
    kws = _keywords(question_text)
    if len(kws) < 2:
        return None
    ACTION_VERBS = re.compile(r"\b(feat|fix|add|publish|deploy|docs|опубликован|готов|сдела|заверш)", re.I)
    try:
        result = subprocess.run(
            ["git", "-C", str(ARTVISION_REPO), "log", f"--since={since_hours} hours ago",
             "--pretty=format:%h %s", "-n", "200"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return None
        for line in result.stdout.splitlines():
            ll = line.lower()
            matched = sum(1 for k in kws if k in ll)
            if matched < 2:
                continue
            if not ACTION_VERBS.search(line):
                continue
            return (line.strip()[:200], "git-log (artvision-data)")
    except Exception:
        return None
    return None


def _factcheck_responses_history(question_text, since_hours=168):
    """
    Ищет в tg_responses.jsonl свежий ответ (last 7 days по умолчанию),
    текст которого содержит keywords вопроса И классифицируется как confirmed.
    Это покрывает кейс: задача уже была закрыта ранее в этом же или предыдущем запросе.
    """
    kws = _keywords(question_text)
    if len(kws) < 2:
        return None
    if not RESPONSES_FILE.exists():
        return None
    cutoff = datetime.now(timezone.utc).timestamp() - since_hours * 3600
    try:
        with open(RESPONSES_FILE) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                text = r.get("text", "")
                tl = text.lower()
                matched = sum(1 for k in kws if k in tl)
                if matched < 2:
                    continue
                # свежесть
                recv = r.get("received_at", "")
                try:
                    ts = datetime.fromisoformat(recv.replace("Z", "+00:00")).timestamp()
                    if ts < cutoff:
                        continue
                except Exception:
                    pass
                # маркер выполнения
                status, _ = classify(text)
                if status not in ("confirmed", "partial"):
                    continue
                sender = r.get("sender_name", "?")
                return (f"{sender}: {text[:160]}", f"tg_responses (msg {r.get('msg_id')})")
    except Exception:
        return None
    return None


def _factcheck_archive(question_text):
    """Ищет закрытые ранее похожие вопросы в archive/."""
    kws = _keywords(question_text)
    if not kws or not ARCHIVE_DIR.exists():
        return None
    try:
        # Последние 20 архивных файлов
        files = sorted(ARCHIVE_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)[:20]
        for f in files:
            content = f.read_text(errors="ignore").lower()
            if not all(k in content for k in kws[:2]):  # первые 2 ключа обязательны
                continue
            # Искать строку с confirmed и текстом вопроса
            for ln in content.splitlines():
                if ("confirmed" in ln or "✅" in ln) and any(k in ln for k in kws):
                    return (ln.strip()[:200], f"archive/{f.name}")
    except Exception:
        return None
    return None


def pre_clarify_factcheck(question):
    """
    Перед отправкой follow-up — проверить, не выполнено ли уже.
    Возвращает (evidence, source) если найдено, иначе None.
    Источники: context-log → git log → архив запросов.
    """
    qtext = question.get("text", "")
    for check in (_factcheck_responses_history, _factcheck_context_log, _factcheck_git_log, _factcheck_archive):
        try:
            result = check(qtext)
            if result:
                return result
        except Exception as e:
            log(f"  factcheck error ({check.__name__}): {e}")
    return None


def send_clarification(req, ambiguous_qs):
    """Отправляет follow-up через tg-send.sh team."""
    if not ambiguous_qs:
        log("  no ambiguous questions left after factcheck — skipping clarification")
        return False
    lines = [f"@PandaCaffe уточнение по утреннему статусу:" if req["recipient"] == "andrey" else "Уточнение:"]
    for q in ambiguous_qs:
        prev = (q.get("answer") or "—")[:80]
        lines.append(f"• По «{q['text']}»: получил «{prev}» — непонятно, можешь конкретнее?")
    msg = "\n".join(lines)
    log(f"📤 sending clarification ({len(ambiguous_qs)} questions)")
    try:
        subprocess.run(
            ["/Users/antonk/.claude/scripts/tg-send.sh", "team", msg],
            check=True, capture_output=True, timeout=10
        )
        log("✅ clarification sent")
        return True
    except Exception as e:
        log(f"❌ clarification failed: {e}")
        return False


def process(auto_clarify=False, dry_run=False, context_log_path=None):
    requests = read_jsonl(REQUESTS_FILE)
    responses = read_jsonl(RESPONSES_FILE)
    pending = [r for r in responses if not r.get("processed")]
    log(f"🔍 {len(pending)} unprocessed responses, {sum(1 for r in requests if r['status']=='awaiting')} active requests")

    if not pending:
        return

    # Применяем ответы
    touched_req_ids = set()
    for resp in pending:
        req_id = resp["request_id"]
        qn = resp.get("matched_question_n")
        updated = update_request_with_response(requests, req_id, qn, resp)
        if updated:
            touched_req_ids.add(req_id)
            log(f"  applied {resp['response_id']} → {req_id} q={qn}")
        if not dry_run:
            resp["processed"] = True

    if dry_run:
        log("DRY RUN — no writes")
        return

    # Сохранить обновлённые responses
    write_jsonl(RESPONSES_FILE, responses)

    # Пройти по тронутым запросам: завершены / нужен follow-up?
    for req in requests:
        if req["id"] not in touched_req_ids:
            continue
        ambiguous_qs = ambiguous_questions(req)

        if is_request_complete(req) and not ambiguous_qs:
            req["status"] = "completed"
            req["completed_at"] = datetime.now(timezone.utc).isoformat()
            append_context_log(req, context_log_path)
            archive_request(req)
        elif ambiguous_qs:
            # PRE-CLARIFY FACTCHECK: для каждого вопроса проверить, не закрыт ли уже
            # (context-log, git log, архив запросов). Если evidence найден — отметить
            # confirmed с пометкой auto-factcheck, чтобы не спрашивать лишнего.
            still_ambiguous = []
            for q in ambiguous_qs:
                evidence = pre_clarify_factcheck(q)
                if evidence:
                    ev_text, ev_source = evidence
                    q["status"] = "confirmed"
                    q["confidence"] = 0.5
                    q["auto_factcheck"] = {
                        "source": ev_source,
                        "evidence": ev_text,
                        "at": datetime.now(timezone.utc).isoformat(),
                    }
                    if not q.get("answer"):
                        q["answer"] = f"[auto-factcheck: {ev_source}] {ev_text}"
                    log(f"  ✓ auto-factcheck q{q['n']} «{q['text'][:40]}» → {ev_source}")
                else:
                    still_ambiguous.append(q)

            # Перепроверить: может после factcheck всё закрыто
            if is_request_complete(req) and not ambiguous_questions(req):
                req["status"] = "completed"
                req["completed_at"] = datetime.now(timezone.utc).isoformat()
                append_context_log(req, context_log_path)
                archive_request(req)
                log(f"  ✅ {req['id']} closed by factcheck without clarification")
                continue

            # Если остались реально непонятные — только тогда спрашивать
            if auto_clarify and still_ambiguous and req.get("clarify_count", 0) < MAX_CLARIFY:
                if send_clarification(req, still_ambiguous):
                    req["clarify_count"] = req.get("clarify_count", 0) + 1
                    req["last_clarify_at"] = datetime.now(timezone.utc).isoformat()
            elif req.get("clarify_count", 0) >= MAX_CLARIFY:
                req["status"] = "escalate"
                log(f"⚠️  {req['id']} exceeded clarify limit, marking escalate")

    write_jsonl(REQUESTS_FILE, requests)
    log("✅ processing done")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--auto-clarify", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--context-log", help="path to context-log.md (default: ~/artvision-data/context-log.md)")
    args = ap.parse_args()
    process(auto_clarify=args.auto_clarify, dry_run=args.dry_run, context_log_path=args.context_log)


if __name__ == "__main__":
    main()
