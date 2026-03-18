#!/usr/bin/env python3
"""
Semantic search по memory-файлам Claude Code Artvision.
TF-IDF-like scoring без внешних зависимостей.

Использование:
  python3 memory-search.py "ключевые слова"
  python3 memory-search.py --json "query"
  echo "контекст" | python3 memory-search.py --stdin
"""

import os
import sys
import re
import json
import math
from collections import Counter
from pathlib import Path

MEMORY_DIR = os.path.expanduser("~/.claude/projects/-Users-antonk/memory")
TOP_N = 5

# Вес по зонам
WEIGHT_NAME = 3.0
WEIGHT_DESCRIPTION = 2.5
WEIGHT_BODY = 1.0

# Бонус по type
TYPE_BONUS = {
    "feedback": 1.5,
    "project": 1.2,
    "reference": 1.1,
    "user": 1.0,
}

# Русские стоп-слова
STOP_WORDS_RU = {
    "и", "в", "на", "с", "по", "для", "из", "к", "у", "о", "от", "за", "не",
    "что", "как", "но", "а", "это", "все", "он", "она", "они", "мы", "вы",
    "его", "её", "их", "мой", "свой", "при", "до", "после", "через", "между",
    "без", "над", "под", "про", "уже", "ещё", "еще", "так", "тоже", "также",
    "если", "то", "же", "бы", "ли", "был", "была", "были", "быть", "есть",
    "нет", "да", "или", "ни", "только", "когда", "где", "чтобы", "потому",
    "может", "нужно", "надо", "очень", "более", "менее", "каждый", "каждая",
    "который", "которая", "которые", "этот", "эта", "эти", "тот", "та", "те",
}

STOP_WORDS_EN = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "can", "shall", "to", "of", "in", "for",
    "on", "with", "at", "by", "from", "as", "into", "through", "during",
    "before", "after", "above", "below", "between", "out", "off", "over",
    "under", "again", "further", "then", "once", "here", "there", "when",
    "where", "why", "how", "all", "each", "every", "both", "few", "more",
    "most", "other", "some", "such", "no", "nor", "not", "only", "own",
    "same", "so", "than", "too", "very", "just", "because", "but", "and",
    "or", "if", "while", "about", "up", "it", "its", "this", "that",
    "these", "those", "i", "you", "he", "she", "we", "they", "me", "him",
    "her", "us", "them", "my", "your", "his", "our", "their",
}

STOP_WORDS = STOP_WORDS_RU | STOP_WORDS_EN


def tokenize(text: str) -> list[str]:
    """Токенизация: lowercase, разбивка по не-буквенным символам, фильтрация стоп-слов."""
    text = text.lower()
    # Разбиваем по границам слов (поддержка кириллицы и латиницы)
    tokens = re.findall(r'[a-zа-яёA-ZА-ЯЁ0-9_-]+', text)
    # Фильтруем стоп-слова и короткие токены
    return [t for t in tokens if t not in STOP_WORDS and len(t) > 1]


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Парсинг YAML frontmatter (простой, без pyyaml)."""
    meta = {"name": "", "description": "", "type": "user"}
    body = content

    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm_text = parts[1].strip()
            body = parts[2].strip()
            for line in fm_text.split("\n"):
                line = line.strip()
                if ":" in line:
                    key, _, val = line.partition(":")
                    key = key.strip().lower()
                    val = val.strip().strip('"').strip("'")
                    if key in meta:
                        meta[key] = val

    return meta, body


def load_memories() -> list[dict]:
    """Загрузка всех memory-файлов."""
    memories = []
    memory_path = Path(MEMORY_DIR)

    if not memory_path.exists():
        return memories

    for f in sorted(memory_path.glob("*.md")):
        if f.name == "MEMORY.md":
            # Пропускаем индексный файл — он агрегирует остальные
            continue

        content = f.read_text(encoding="utf-8", errors="replace")
        meta, body = parse_frontmatter(content)

        # Если нет frontmatter, используем имя файла
        if not meta["name"]:
            meta["name"] = f.stem

        memories.append({
            "file": f.name,
            "path": str(f),
            "name": meta["name"],
            "description": meta["description"],
            "type": meta["type"],
            "body": body,
            "tokens_name": tokenize(meta["name"]),
            "tokens_desc": tokenize(meta["description"]),
            "tokens_body": tokenize(body),
        })

    return memories


def compute_idf(memories: list[dict]) -> dict[str, float]:
    """IDF по всем документам (name + description + body как единый документ)."""
    n_docs = len(memories)
    if n_docs == 0:
        return {}

    doc_freq: Counter = Counter()
    for mem in memories:
        # Уникальные токены документа
        all_tokens = set(mem["tokens_name"] + mem["tokens_desc"] + mem["tokens_body"])
        for token in all_tokens:
            doc_freq[token] += 1

    idf = {}
    for token, df in doc_freq.items():
        idf[token] = math.log((n_docs + 1) / (df + 1)) + 1  # smoothed IDF

    return idf


def search(query: str, memories: list[dict], idf: dict[str, float]) -> list[dict]:
    """TF-IDF поиск с весами по зонам и типу."""
    query_tokens = tokenize(query)
    if not query_tokens:
        return []

    query_tf = Counter(query_tokens)
    results = []

    for mem in memories:
        score = 0.0

        # TF в каждой зоне
        tf_name = Counter(mem["tokens_name"])
        tf_desc = Counter(mem["tokens_desc"])
        tf_body = Counter(mem["tokens_body"])

        for qt, q_count in query_tf.items():
            token_idf = idf.get(qt, 1.0)

            # Зональный TF-IDF
            name_score = tf_name.get(qt, 0) * WEIGHT_NAME * token_idf
            desc_score = tf_desc.get(qt, 0) * WEIGHT_DESCRIPTION * token_idf
            body_score = tf_body.get(qt, 0) * WEIGHT_BODY * token_idf

            score += (name_score + desc_score + body_score) * q_count

        # Exact phrase bonus: если вся query-фраза есть в name или description
        query_lower = query.lower()
        if query_lower in mem["name"].lower():
            score *= 2.0
        elif query_lower in mem["description"].lower():
            score *= 1.5

        # Type bonus
        type_mult = TYPE_BONUS.get(mem["type"], 1.0)
        score *= type_mult

        if score > 0:
            results.append({
                "file": mem["file"],
                "path": mem["path"],
                "name": mem["name"],
                "description": mem["description"],
                "type": mem["type"],
                "score": round(score, 2),
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:TOP_N]


def format_results(results: list[dict], output_json: bool = False) -> str:
    """Форматирование результатов."""
    if output_json:
        return json.dumps(results, ensure_ascii=False, indent=2)

    if not results:
        return "MEMORY RECALL: no relevant memories found."

    lines = [f"MEMORY RECALL (top {len(results)}):"]
    for i, r in enumerate(results, 1):
        desc = r["description"][:80] + "..." if len(r["description"]) > 80 else r["description"]
        lines.append(f"  {i}. [{r['type']}] {r['name']} (score: {r['score']})")
        if desc:
            lines.append(f"     {desc}")
        lines.append(f"     -> {r['file']}")

    return "\n".join(lines)


def main():
    output_json = "--json" in sys.argv
    use_stdin = "--stdin" in sys.argv

    # Получаем query
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    if use_stdin:
        query = sys.stdin.read().strip()
    elif args:
        query = " ".join(args)
    else:
        print("Usage: memory-search.py [--json] [--stdin] <query>", file=sys.stderr)
        sys.exit(1)

    if not query:
        print("Empty query", file=sys.stderr)
        sys.exit(1)

    memories = load_memories()
    if not memories:
        print("No memory files found in " + MEMORY_DIR, file=sys.stderr)
        sys.exit(1)

    idf = compute_idf(memories)
    results = search(query, memories, idf)
    print(format_results(results, output_json))


if __name__ == "__main__":
    main()
