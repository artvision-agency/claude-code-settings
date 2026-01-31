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
            last_assistant_has_tool_use = False
            last_meaningful_type = None

            for line in reversed(lines[-20:]):
                try:
                    data = json.loads(line)
                    msg_type = data.get('type', '')
                    session_info['last_type'] = msg_type

                    # Явные признаки нормального завершения
                    if data.get('subtype') == 'stop_hook_summary':
                        session_info['is_interrupted'] = False
                        break
                    if msg_type == 'result' and data.get('subtype') == 'success':
                        session_info['is_interrupted'] = False
                        break

                    # Пропускаем служебные записи
                    if msg_type in ('file-history-snapshot', 'queue-operation', 'system'):
                        continue

                    # Запоминаем последний значимый тип
                    if not last_meaningful_type and msg_type in ('user', 'assistant'):
                        last_meaningful_type = msg_type

                        # Проверяем есть ли tool_use в assistant message
                        if msg_type == 'assistant':
                            message = data.get('message', {})
                            content = message.get('content', [])
                            if isinstance(content, list):
                                for item in content:
                                    if isinstance(item, dict) and item.get('type') == 'tool_use':
                                        last_assistant_has_tool_use = True
                                        break

                except json.JSONDecodeError:
                    continue

            # Мягкая логика: считаем completed если:
            # 1. Последнее сообщение от assistant БЕЗ незавершённого tool_use
            # 2. Или последнее сообщение от user (ждал ответа)
            # 3. И размер файла > 1KB (была реальная работа)
            if session_info['is_interrupted'] and session_info['size'] > 1024:
                if last_meaningful_type == 'assistant' and not last_assistant_has_tool_use:
                    session_info['is_interrupted'] = False
                elif last_meaningful_type == 'user':
                    # User написал но не получил ответ — это interrupted
                    pass

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

def export_session(session: dict, output_dir: Path) -> Path:
    """Экспорт сессии в markdown для синхронизации."""
    output_dir.mkdir(parents=True, exist_ok=True)

    date_str = session['modified'].strftime('%Y-%m-%d_%H-%M')
    filename = f"{date_str}_{session.get('slug') or session['id'][:8]}.md"
    filepath = output_dir / filename

    # Читаем полный контент сессии
    messages = []
    try:
        with open(session['path'], 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    if data.get('type') == 'user':
                        msg = data.get('message', {})
                        content = msg.get('content', '') if isinstance(msg, dict) else str(msg)
                        # Убираем system-reminder
                        if '<system-reminder>' in content:
                            parts = content.split('</system-reminder>')
                            content = parts[-1].strip() if len(parts) > 1 else content
                        if content:
                            messages.append(('user', content[:500]))
                    elif data.get('type') == 'assistant':
                        msg = data.get('message', {})
                        content = msg.get('content', '') if isinstance(msg, dict) else str(msg)
                        if content and len(content) > 20:
                            messages.append(('assistant', content[:500]))
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        messages.append(('error', str(e)))

    # Формируем markdown
    md_content = f"""# Session Export

## Metadata
- **ID**: {session['id']}
- **Slug**: {session.get('slug') or 'N/A'}
- **Date**: {session['modified'].strftime('%Y-%m-%d %H:%M')}
- **Status**: {'🔴 INTERRUPTED' if session.get('is_interrupted') else '🟢 Completed'}
- **Project**: {session['project']}
- **CWD**: {session.get('cwd') or 'N/A'}
- **Messages**: {session['message_count']}

## Summary
{session.get('first_message') or 'No first message'}

## Conversation (last {min(len(messages), 10)} exchanges)
"""

    for role, content in messages[-10:]:
        if role == 'user':
            md_content += f"\n### 👤 User\n{content}\n"
        elif role == 'assistant':
            md_content += f"\n### 🤖 Assistant\n{content[:300]}{'...' if len(content) > 300 else ''}\n"

    md_content += f"""
---
*Exported at {datetime.now().strftime('%Y-%m-%d %H:%M')} for cross-client sync*
"""

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(md_content)

    return filepath


def sync_sessions(args):
    """Синхронизация сессий в git репо."""
    sessions_dir = get_sessions_dir()
    if not sessions_dir:
        print(f"{Colors.RED}Sessions directory not found{Colors.RESET}")
        return

    # Директория для экспорта
    sync_repo = Path.home() / 'claude-code-settings' / 'session_logs'
    if not sync_repo.parent.exists():
        print(f"{Colors.YELLOW}Sync repo not found. Clone it first:{Colors.RESET}")
        print("  gh repo clone artvision-agency/claude-code-settings ~/claude-code-settings")
        return

    # Собираем незавершённые сессии
    all_sessions = []
    for project_dir in sessions_dir.iterdir():
        if not project_dir.is_dir():
            continue
        for jsonl_file in project_dir.glob('*.jsonl'):
            session = parse_session(jsonl_file)
            # Только за последние 7 дней
            if (datetime.now() - session['modified']).days <= 7:
                all_sessions.append(session)

    all_sessions.sort(key=lambda x: x['modified'], reverse=True)

    # Фильтр
    if args.interrupted:
        all_sessions = [s for s in all_sessions if s.get('is_interrupted')]

    if not all_sessions:
        print(f"{Colors.GREEN}No sessions to sync{Colors.RESET}")
        return

    # Лимит (--all убирает лимит)
    if args.all:
        sessions_to_export = all_sessions
    else:
        sessions_to_export = all_sessions[:args.limit]

    print(f"\n{Colors.BOLD}Syncing {len(sessions_to_export)} sessions...{Colors.RESET}\n")

    exported = []
    for session in sessions_to_export:
        filepath = export_session(session, sync_repo)
        status = f"{Colors.RED}INTERRUPTED{Colors.RESET}" if session.get('is_interrupted') else f"{Colors.GREEN}completed{Colors.RESET}"
        print(f"  ✅ {filepath.name} [{status}]")
        exported.append(filepath)

    # Git commit & push если указан флаг
    if args.push:
        print(f"\n{Colors.CYAN}Committing and pushing...{Colors.RESET}")
        os.chdir(sync_repo.parent)
        subprocess.run(['git', 'add', 'session_logs/'])
        result = subprocess.run(
            ['git', 'commit', '-m', f'sync: export {len(exported)} sessions\n\nCo-Authored-By: Claude <noreply@anthropic.com>'],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            subprocess.run(['git', 'push', 'origin', 'main'])
            print(f"{Colors.GREEN}✅ Pushed to git!{Colors.RESET}")
        else:
            print(f"{Colors.YELLOW}Nothing to commit (already up to date){Colors.RESET}")
    else:
        print(f"\n{Colors.DIM}Use --push to commit and push to git{Colors.RESET}")

    print(f"\n{Colors.BOLD}Sync complete!{Colors.RESET}")
    print(f"Other Claude clients can read: ~/claude-code-settings/session_logs/\n")


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
    parser.add_argument('--sync', '-s', action='store_true',
                        help='Export recent sessions to git repo for cross-client sync')
    parser.add_argument('--push', action='store_true',
                        help='With --sync: commit and push to git')

    args = parser.parse_args()

    if args.sync:
        sync_sessions(args)
    elif args.resume:
        resume_session(args)
    else:
        list_sessions(args)

if __name__ == '__main__':
    main()
