#!/usr/bin/env python3
"""
State Graph Analyzer — парсит Python-код TG-бота и строит граф состояний.

Выводит JSON с nodes, edges, branching factors, путями и тест-группами.

Usage:
    python3 state-graph-analyzer.py /path/to/bot/
"""

import ast
import json
import os
import re
import sys
from collections import defaultdict
from math import ceil
from pathlib import Path


def find_py_files(bot_dir: str) -> list[str]:
    """Найти все .py файлы бота."""
    files = []
    for root, _, filenames in os.walk(bot_dir):
        if "__pycache__" in root or "node_modules" in root:
            continue
        for f in filenames:
            if f.endswith(".py"):
                files.append(os.path.join(root, f))
    return files


def extract_states(files: list[str]) -> dict:
    """Извлечь все session['state'] = '...' присваивания."""
    state_pattern = re.compile(
        r"""session\[["']state["']\]\s*=\s*["'](\w+)["']"""
    )
    get_state_pattern = re.compile(
        r"""session\.get\(["']state["']\)\s*==\s*["'](\w+)["']"""
        r"""|session\[["']state["']\]\s*==\s*["'](\w+)["']"""
        r"""|\.get\(["']state["']\)\s*(?:in\s*\(|==\s*)["'](\w+)["']"""
    )
    callback_pattern = re.compile(
        r"""callback_data\s*=\s*["']([^"']+)["']"""
        r"""|data\s*==\s*["']([^"']+)["']"""
        r"""|data\.startswith\(["']([^"']+)["']\)"""
    )

    states_set = set()
    states_write = {}  # state -> [files where set]
    states_read = {}   # state -> [files where checked]
    callbacks = set()

    for fpath in files:
        fname = os.path.basename(fpath)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue

        for m in state_pattern.finditer(content):
            st = m.group(1)
            states_set.add(st)
            states_write.setdefault(st, []).append(fname)

        for m in get_state_pattern.finditer(content):
            st = m.group(1) or m.group(2) or m.group(3)
            if st:
                states_set.add(st)
                states_read.setdefault(st, []).append(fname)

        for m in callback_pattern.finditer(content):
            cb = m.group(1) or m.group(2) or m.group(3)
            if cb:
                callbacks.add(cb)

    return {
        "states": sorted(states_set),
        "states_write": states_write,
        "states_read": states_read,
        "callbacks": sorted(callbacks),
    }


def extract_questions(files: list[str]) -> dict:
    """Найти QUESTIONS list и TOTAL_Q в config.py."""
    for fpath in files:
        if not fpath.endswith("config.py"):
            continue
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue

        # Count options per question
        options_pattern = re.compile(r'"options"\s*:\s*\[([^\]]+)\]')
        options_counts = []
        for m in options_pattern.finditer(content):
            opts = m.group(1).count('"text"')
            if opts == 0:
                opts = m.group(1).count(",") + 1
            options_counts.append(opts)

        total_q_match = re.search(r"TOTAL_Q\s*[:=]\s*(\d+|len\(QUESTIONS\))", content)
        total_q = len(options_counts) if options_counts else 0

        # Count doctors
        doctors_pattern = re.compile(r"DOCTORS\s*[:=]\s*\[")
        doctors_count = 0
        if doctors_pattern.search(content):
            doctor_entries = re.findall(r'"key"\s*:', content)
            doctors_count = len(doctor_entries)

        # Threshold
        threshold_match = re.search(r"CONCERN_THRESHOLD\s*[:=]\s*([\d.]+)", content)
        threshold = float(threshold_match.group(1)) if threshold_match else 3.5

        return {
            "total_q": total_q,
            "options_per_q": options_counts,
            "doctors_count": doctors_count,
            "concern_threshold": threshold,
        }
    return {"total_q": 0, "options_per_q": [], "doctors_count": 0, "concern_threshold": 3.5}


def extract_entry_points(files: list[str]) -> list[str]:
    """Найти entry points (/start args, deep links)."""
    entries = set()
    start_pattern = re.compile(r'args\s*=.*context\.args|deep_link|start_payload|arg\s*==')
    for fpath in files:
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue
        if "cmd_start" in content or "CommandHandler" in content:
            entries.add("/start")
        if "qr" in content.lower() and ("start" in content.lower()):
            entries.add("/start qr")
        if re.search(r'arg\s*==\s*["\']review', content):
            entries.add("/start review")
    return sorted(entries) if entries else ["/start"]


def build_edges(state_info: dict, q_info: dict) -> list[dict]:
    """Построить рёбра графа на основе найденных состояний и callbacks."""
    edges = []
    states = state_info["states"]
    callbacks = state_info["callbacks"]

    # Infer edges from callback names and state transitions
    # This is a heuristic — real edges come from code flow
    for cb in callbacks:
        edges.append({"callback": cb, "type": "callback"})

    return edges


def calculate_paths(state_info: dict, q_info: dict) -> dict:
    """Рассчитать количество уникальных путей."""
    total_q = q_info["total_q"]
    opts = q_info["options_per_q"]
    doctors = q_info["doctors_count"] or 9
    threshold = q_info["concern_threshold"]

    # Q6 variants (open_feedback)
    q6_variants = 4  # text, voice, video, skip

    # Has open_feedback state?
    has_q6 = "open_feedback" in state_info["states"]
    if not has_q6:
        q6_variants = 1

    # Review flow paths (moderation → platform → screenshot)
    # send_moderation → (review_use → platform(2) → screenshot(1)) + review_skip
    # + rewrite → confirm → same
    review_paths = 6  # 2+1+2+1

    # Platform choices
    platform_choices = 3  # yandex, 2gis, skip

    # Doctor choices
    doctor_choices = doctors + 1  # N doctors + skip
    doctor_rate_choices = 2  # rate_yes, skip → doctor_choices or 1

    # Channel review
    channel_choices = 7  # 3 types × 2 consent + skip

    # Has concern flow?
    has_concern = "concern" in " ".join(state_info["callbacks"]) or any(
        "concern" in s for s in state_info["states"]
    )
    concern_variants = 4 if has_concern else 1  # text, voice, video, skip

    # Happy path (avg >= threshold)
    happy_finish = (doctor_choices + 1) * channel_choices  # doctor_rate_yes(N+1) + skip(1) × channel
    # Simplify: offer_doctor = 2 branches (yes→N+1, skip→1) = N+2
    doctor_total = doctors + 2  # rate_yes→(N doctors + skip) + rate_skip
    happy_finish = doctor_total * channel_choices
    p_happy = review_paths * happy_finish

    # Unhappy path (avg < threshold)
    p_unhappy = concern_variants * doctor_total  # no channel for unhappy

    # Main flow (without deep link doctor)
    main_no_doc = q6_variants * (p_happy + p_unhappy) + 1  # +1 for call path

    # Main flow (with deep link doctor)
    p_happy_doc = review_paths * channel_choices
    p_unhappy_doc = concern_variants
    main_with_doc = q6_variants * (p_happy_doc + p_unhappy_doc) + 1

    # QR flow
    has_qr = any("qr" in s for s in state_info["states"])
    qr_paths = 0
    if has_qr:
        # 5★: 2 paths, 4★: 2 paths, 1-3★: 3 paths = 7 per doctor
        qr_per_doctor = 7
        qr_paths = doctors * qr_per_doctor

    total = main_no_doc + main_with_doc + qr_paths

    # Recommended tests: edge coverage
    n_states = len(state_info["states"])
    n_callbacks = len(state_info["callbacks"])
    # Minimum: cover every branch at least once
    recommended = max(25, ceil(n_callbacks / 3))
    # Optimal: branch coverage + edge cases
    optimal = recommended + 10

    return {
        "total_paths": total,
        "main_no_doc": main_no_doc,
        "main_with_doc": main_with_doc,
        "qr_paths": qr_paths,
        "recommended_tests_min": recommended,
        "recommended_tests_optimal": optimal,
        "branching_factors": {
            "Q1": opts[0] if len(opts) > 0 else "?",
            "Q2-Q5": opts[1] if len(opts) > 1 else "?",
            "Q6_open_feedback": q6_variants,
            "avg_branch": 2,
            "review_flow": review_paths,
            "platform": platform_choices,
            "doctors": f"{doctors} + skip",
            "channel_review": channel_choices,
            "concern": concern_variants,
            "qr_rating": 5,
            "qr_per_doctor": 7 if has_qr else 0,
        },
        "formula": {
            "happy": f"Q6({q6_variants}) × review({review_paths}) × doctor({doctor_total}) × channel({channel_choices})",
            "unhappy": f"Q6({q6_variants}) × concern({concern_variants}) × doctor({doctor_total})",
            "qr": f"doctors({doctors}) × paths_per(7)" if has_qr else "N/A",
        },
    }


def generate_test_groups(state_info: dict, q_info: dict, paths: dict) -> list[dict]:
    """Сгенерировать группы тестовых сценариев."""
    groups = []

    # Group 1: Happy path basics
    happy = {
        "name": "Happy path (avg >= порога)",
        "scenarios": [
            "Q1-Q5 все 5/5 → Q6 текст → review → moderation → platform yandex → screenshot → doctor выбор → channel текст consent yes → goodbye",
            "Q1-Q5 средние 4/5 → Q6 пропуск → review → moderation → platform skip → doctor skip → channel skip → goodbye",
            "Q1-Q5 все 5/5 → Q6 голос → review → rewrite → confirm → platform 2gis → doctor выбор → channel видео consent no → goodbye",
            "Q1-Q5 все 5/5 → Q6 видео → review → moderation → review_use → screenshot skip → doctor skip → channel голос consent yes → goodbye",
        ],
    }
    happy["count"] = len(happy["scenarios"])
    groups.append(happy)

    # Group 2: Unhappy path
    unhappy = {
        "name": "Unhappy path (avg < порога)",
        "scenarios": [
            "Q1-Q5 все 1/5 → Q6 текст → concern текст → doctor выбор → goodbye",
            "Q1-Q5 все 2/5 → Q6 пропуск → concern голос → doctor skip → goodbye",
            "Q1-Q5 все 1/5 → Q6 голос → concern видео → doctor выбор → goodbye",
            "Q1-Q5 смешанные → Q6 пропуск → concern skip → doctor skip → goodbye",
        ],
    }
    unhappy["count"] = len(unhappy["scenarios"])
    groups.append(unhappy)

    # Group 3: Q6 variants
    q6 = {
        "name": "Q6 открытый вопрос",
        "scenarios": [
            "Q6 текст → extra_comment в LLM промпте",
            "Q6 голос → file_id сохранён, complete_survey вызван",
            "Q6 видео (video_note) → file_id сохранён",
            "Q6 пропуск → complete_survey без open_feedback",
        ],
    }
    q6["count"] = len(q6["scenarios"])
    groups.append(q6)

    # Group 4: Review flow
    review = {
        "name": "Review flow",
        "scenarios": [
            "send_moderation → админам с кнопками approve/reject",
            "review_use → platform_choice показан",
            "review_skip → finish_session",
            "review_rewrite → writing_own → review_confirm → platform",
            "review_rewrite петля → writing_own → review_confirm → review_rewrite",
            "LLM cascade: gemini-flash → gemini-2.5 → glm-4.5 → fallback",
        ],
    }
    review["count"] = len(review["scenarios"])
    groups.append(review)

    # Group 5: Doctor flow
    doctor = {
        "name": "Оценка врача",
        "scenarios": [
            "doctor_rate_yes → список врачей → выбор → card + goodbye",
            "doctor_skip → finish_session продолжает",
            "deep link /start doc_X → doctor pre-set, skip doctor step",
        ],
    }
    doctor["count"] = len(doctor["scenarios"])
    groups.append(doctor)

    # Group 6: Channel moderation
    channel = {
        "name": "Канал + модерация",
        "scenarios": [
            "chanrev_video → consent yes → admin moderation → approve → publish",
            "chanrev_voice → consent no → finish_session",
            "chanrev_text → consent yes → admin reject → не публикуется",
            "chanrev_skip → finish_session",
            "Текст НЕ обещает публикацию до одобрения",
            "Пациент НЕ может сам опубликовать",
        ],
    }
    channel["count"] = len(channel["scenarios"])
    groups.append(channel)

    # Group 7: Other flows
    other = {
        "name": "Прочие потоки",
        "scenarios": [
            "format_call → awaiting_phone → валидация → done",
            "Невалидный телефон → повторный запрос",
            "Email содержит ВСЕ данные (ответы, баллы, доктор)",
            "sanitize_name от prompt injection",
            "Session cleanup после finish_session",
        ],
    }
    other["count"] = len(other["scenarios"])
    groups.append(other)

    # Group 8: QR lobby
    if any("qr" in s for s in state_info["states"]):
        qr = {
            "name": "QR Lobby",
            "scenarios": [
                "QR → врач → 5★ → platform offer → finish",
                "QR → врач → 4★ → feedback текст → done",
                "QR → врач → 4★ → skip → finish",
                "QR → врач → 1-3★ → complaint текст → done",
                "QR → врач → 1-3★ → complaint голос → done",
                "QR → врач → 1-3★ → skip → finish",
                "QR states обрабатываются ДО других в handle_text",
            ],
        }
        qr["count"] = len(qr["scenarios"])
        groups.append(qr)

    # Group 9: Edge cases
    edge = {
        "name": "Edge cases",
        "scenarios": [
            "avg ровно на пороге (3.5) → happy path",
            "Expired/missing session → no crash",
            "Handler registration порядок в bot.py",
            "TOTAL_Q == len(QUESTIONS)",
        ],
    }
    edge["count"] = len(edge["scenarios"])
    groups.append(edge)

    return groups


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 state-graph-analyzer.py <path-to-bot>", file=sys.stderr)
        sys.exit(1)

    bot_dir = sys.argv[1]
    if not os.path.isdir(bot_dir):
        print(f"Error: {bot_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    files = find_py_files(bot_dir)
    if not files:
        print(f"Error: no .py files found in {bot_dir}", file=sys.stderr)
        sys.exit(1)

    state_info = extract_states(files)
    q_info = extract_questions(files)
    entry_points = extract_entry_points(files)
    paths = calculate_paths(state_info, q_info)
    test_groups = generate_test_groups(state_info, q_info, paths)

    total_tests = sum(g["count"] for g in test_groups)

    result = {
        "bot_dir": bot_dir,
        "files_analyzed": len(files),
        "nodes": len(state_info["states"]),
        "states": state_info["states"],
        "callbacks_count": len(state_info["callbacks"]),
        "entry_points": entry_points,
        "terminal_states": ["done", "goodbye"],
        "questions": q_info,
        "paths": paths,
        "total_paths": paths["total_paths"],
        "recommended_tests": total_tests,
        "recommended_agents": ceil(total_tests / 13),
        "test_groups": test_groups,
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
