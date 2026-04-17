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
import sys
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
    r"\bда\b", r"\bготов(о|а)?\b", r"\bdone\b", r"\bпрош(ёл|ел)\b",
    r"\bзаверш(ён|ен|ено)\b", r"\bопубликован", r"\bсдела(но|на|л)\b",
    r"\bзакрыт", r"https?://",
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


def send_clarification(req, ambiguous_qs):
    """Отправляет follow-up через tg-send.sh team."""
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
            if auto_clarify and req.get("clarify_count", 0) < MAX_CLARIFY:
                if send_clarification(req, ambiguous_qs):
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
