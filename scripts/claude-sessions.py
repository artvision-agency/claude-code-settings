#!/usr/bin/env python3
"""
Claude Code Sessions Manager
============================
Утилита для просмотра, анализа и восстановления сессий Claude Code.

Использование:
    claude-sessions              # Показать последние 20 сессий
    claude-sessions --all        # Показать все сессии
    claude-sessions --interrupted # Только оборванные сессии
    claude-sessions --resume ID  # Восстановить сессию по ID или номеру
    claude-sessions --project X  # Фильтр по проекту

Автор: Claude Code
"""

import json
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import argparse

# Цвета для терминала
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'

def get_sessions_dir():
    """Найти директорию с сессиями."""
    claude_dir = Path.home() / '.claude' / 'projects'
    if not claude_dir.exists():
        return None
    return claude_dir

def parse_session(jsonl_path: Path) -> dict:
    """Парсинг сессии из JSONL файла."""
    session_info = {
        'id': jsonl_path.stem,
        'path': str(jsonl_path),
        'size': jsonl_path.stat().st_size,
        'modified': datetime.fromtimestamp(jsonl_path.stat().st_mtime),
        'slug': None,
        'cwd': None,
        'first_message': None,
        'last_type': None,
        'is_interrupted': True,  # По умолчанию считаем оборванной
        'message_count': 0,
        'project': jsonl_path.parent.name,
    }

    try:
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            session_info['message_count'] = len(lines)

            # Парсим первые строки для метаданных
            for line in lines[:50]:
                try:
                    data = json.loads(line)

                    # Ищем slug
                    if data.get('slug') and not session_info['slug']:
                        session_info['slug'] = data['slug']

                    # Ищем cwd
                    if data.get('cwd') and not session_info['cwd']:
                        session_info['cwd'] = data['cwd']

                    # Ищем первое сообщение пользователя
                    if data.get('type') == 'user' and not session_info['first_message']:
                        msg = data.get('message', {})
                        if isinstance(msg, dict):
                            content = msg.get('content', '')
                        else:
                            content = str(msg)
                        # Убираем system-reminder теги
                        if '<system-reminder>' in content:
                            parts = content.split('</system-reminder>')
                            content = parts[-1] if len(parts) > 1 else content
                        session_info['first_message'] = content[:80].strip()

                except json.JSONDecodeError:
                    continue

            # Проверяем последние строки на предмет нормального завершения
            for line in reversed(lines[-10:]):
                try:
                    data = json.loads(line)
                    session_info['last_type'] = data.get('type', '')

                    # Признаки нормального завершения
                    if data.get('subtype') == 'stop_hook_summary':
                        session_info['is_interrupted'] = False
                        break
                    if data.get('type') == 'result' and data.get('subtype') == 'success':
                        session_info['is_interrupted'] = False
                        break

                except json.JSONDecodeError:
                    continue

    except Exception as e:
        session_info['error'] = str(e)

    return session_info

def format_size(size: int) -> str:
    """Форматирование размера файла."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"

def format_time_ago(dt: datetime) -> str:
    """Форматирование времени (сколько прошло)."""
    now = datetime.now()
    diff = now - dt

    if diff.days > 0:
        return f"{diff.days}d ago"
    elif diff.seconds >= 3600:
        return f"{diff.seconds // 3600}h ago"
    elif diff.seconds >= 60:
        return f"{diff.seconds // 60}m ago"
    else:
        return "just now"

def print_session(idx: int, session: dict, show_project: bool = False):
    """Вывод информации о сессии."""
    c = Colors

    # Статус
    if session.get('is_interrupted'):
        status = f"{c.RED}●{c.RESET}"
        status_text = f"{c.RED}INTERRUPTED{c.RESET}"
    else:
        status = f"{c.GREEN}●{c.RESET}"
        status_text = f"{c.GREEN}completed{c.RESET}"

    # Slug или ID
    name = session.get('slug') or session['id'][:8]

    # Время
    time_str = format_time_ago(session['modified'])

    # Размер
    size_str = format_size(session['size'])

    # Первое сообщение
    first_msg = session.get('first_message') or ''
    msg = first_msg[:60] or '(no message)'
    if len(first_msg) > 60:
        msg += '...'

    # Проект
    project = ""
    if show_project:
        project = f" {c.DIM}[{session['project']}]{c.RESET}"

    # Рабочая директория
    cwd = session.get('cwd', '')
    if cwd:
        cwd = cwd.replace(str(Path.home()), '~')
        if len(cwd) > 40:
            cwd = '...' + cwd[-37:]

    print(f"{c.BOLD}{idx:3d}{c.RESET} {status} {c.CYAN}{name:25s}{c.RESET} {time_str:10s} {size_str:8s} {status_text}{project}")
    print(f"     {c.DIM}{msg}{c.RESET}")
    if cwd:
        print(f"     {c.DIM}📁 {cwd}{c.RESET}")
    print()

def list_sessions(args):
    """Список сессий."""
    sessions_dir = get_sessions_dir()
    if not sessions_dir:
        print(f"{Colors.RED}Sessions directory not found{Colors.RESET}")
        return

    # Собираем все сессии
    all_sessions = []

    for project_dir in sessions_dir.iterdir():
        if not project_dir.is_dir():
            continue

        # Фильтр по проекту
        if args.project and args.project not in project_dir.name:
            continue

        for jsonl_file in project_dir.glob('*.jsonl'):
            session = parse_session(jsonl_file)
            all_sessions.append(session)

    # Сортировка по времени (новые первые)
    all_sessions.sort(key=lambda x: x['modified'], reverse=True)

    # Фильтр по статусу
    if args.interrupted:
        all_sessions = [s for s in all_sessions if s.get('is_interrupted')]

    # Лимит
    if not args.all:
        all_sessions = all_sessions[:args.limit]

    # Статистика
    total = len(all_sessions)
    interrupted = sum(1 for s in all_sessions if s.get('is_interrupted'))

    print(f"\n{Colors.BOLD}Claude Code Sessions{Colors.RESET}")
    print(f"{Colors.DIM}{'─' * 60}{Colors.RESET}")
    print(f"Total: {total} | {Colors.RED}Interrupted: {interrupted}{Colors.RESET} | {Colors.GREEN}Completed: {total - interrupted}{Colors.RESET}")
    print(f"{Colors.DIM}{'─' * 60}{Colors.RESET}\n")

    # Проверяем нужен ли показ проекта
    projects = set(s['project'] for s in all_sessions)
    show_project = len(projects) > 1

    for idx, session in enumerate(all_sessions, 1):
        print_session(idx, session, show_project)

    print(f"{Colors.DIM}Use: claude-sessions --resume <number> to resume a session{Colors.RESET}\n")

def resume_session(args):
    """Восстановление сессии."""
    sessions_dir = get_sessions_dir()
    if not sessions_dir:
        print(f"{Colors.RED}Sessions directory not found{Colors.RESET}")
        return

    target = args.resume

    # Если передан номер — находим сессию по индексу
    if target.isdigit():
        idx = int(target)
        all_sessions = []

        for project_dir in sessions_dir.iterdir():
            if not project_dir.is_dir():
                continue
            for jsonl_file in project_dir.glob('*.jsonl'):
                session = parse_session(jsonl_file)
                all_sessions.append(session)

        all_sessions.sort(key=lambda x: x['modified'], reverse=True)

        if args.interrupted:
            all_sessions = [s for s in all_sessions if s.get('is_interrupted')]

        if idx < 1 or idx > len(all_sessions):
            print(f"{Colors.RED}Invalid session number: {idx}{Colors.RESET}")
            return

        session_id = all_sessions[idx - 1]['id']
    else:
        session_id = target

    print(f"{Colors.CYAN}Resuming session: {session_id}{Colors.RESET}")

    # Запускаем claude с --resume
    subprocess.run(['claude', '--resume', session_id])

def main():
    parser = argparse.ArgumentParser(
        description='Claude Code Sessions Manager',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  claude-sessions                    Show recent sessions
  claude-sessions --interrupted      Show only interrupted sessions
  claude-sessions --resume 3         Resume session #3
  claude-sessions --project antonk   Filter by project name
        """
    )

    parser.add_argument('--all', '-a', action='store_true',
                        help='Show all sessions (no limit)')
    parser.add_argument('--interrupted', '-i', action='store_true',
                        help='Show only interrupted sessions')
    parser.add_argument('--resume', '-r', type=str, metavar='ID',
                        help='Resume session by number or ID')
    parser.add_argument('--project', '-p', type=str,
                        help='Filter by project name')
    parser.add_argument('--limit', '-l', type=int, default=20,
                        help='Limit number of sessions (default: 20)')

    args = parser.parse_args()

    if args.resume:
        resume_session(args)
    else:
        list_sessions(args)

if __name__ == '__main__':
    main()
