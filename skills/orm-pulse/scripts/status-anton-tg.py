#!/usr/bin/env python3
"""orm-pulse: периодический status-апдейт в личку Антона (channel=anton).

Парсит свежий orders-state-YYYY-MM-DD.md и предыдущий → формирует короткую
табличку с Δ за день + критичными алёртами + что делать.

Запуск: status-anton-tg.py <client_slug>
Cron: ~/Library/LaunchAgents/pro.artvision.orm-pulse.<client>-status-anton.plist
"""
import re
import sys
import subprocess
from datetime import date, datetime, timedelta
from pathlib import Path

CLIENT = sys.argv[1] if len(sys.argv) > 1 else 'blumart'
BASE = Path.home() / 'artvision-data' / 'clients' / CLIENT / 'orm'
TG_SEND = Path.home() / '.claude' / 'scripts' / 'tg-send.sh'


def find_state_file(day):
    p = BASE / f'orders-state-{day.isoformat()}.md'
    return p if p.exists() else None


def parse_funnel(md):
    out = {}
    in_funnel = False
    for line in md.splitlines():
        if 'Воронка состояний' in line:
            in_funnel = True
            continue
        if in_funnel and line.startswith('##'):
            break
        m = re.match(r'\|\s*[^|]*\|\s*\**(\d+)\**\s*\|\s*([^|]+)\s*\|', line)
        if m and '|' in line:
            cells = [c.strip(' *') for c in line.split('|')[1:-1]]
            if len(cells) >= 3 and cells[1].isdigit():
                out[cells[2]] = int(cells[1])
    return out


def parse_qcomment(md):
    out = {'balance': None, 'pending_accept': None, 'projects_total': None, 'pending_list': []}
    m = re.search(r'Баланс:\*?\*?\s*([\d.]+)\s*₽', md)
    if m:
        out['balance'] = float(m.group(1))
    m = re.search(r'Принять работу:\s*\*?\*?(\d+)', md)
    if m:
        out['pending_accept'] = int(m.group(1))
    m = re.search(r'Проектов:\*?\*?\s*(\d+)', md)
    if m:
        out['projects_total'] = int(m.group(1))
    for ln in md.splitlines():
        m = re.match(r'-\s+\[(\d+)\]\([^)]+\)\s+—\s+(.+?)\s+·\s+Принять', ln)
        if m:
            out['pending_list'].append((m.group(1), m.group(2)))
    return out


def parse_tempo(md):
    out = {}
    m = re.search(r'За последние\s+([\d.]+)\s+дней:\s+\*?\*?\+?(\d+)', md)
    if m:
        out['period_days'] = float(m.group(1))
        out['new_reviews'] = int(m.group(2))
    m = re.search(r'Темп:\s*\*?\*?([\d.]+)\s*публ/день', md)
    if m:
        out['tempo'] = float(m.group(1))
    m = re.search(r'Цель\s+(\d+)/день', md)
    if m:
        out['target'] = int(m.group(1))
    m = re.search(r'Рейтинг сейчас:\s*\*?\*?([\d.]+)', md)
    if m:
        out['rating'] = float(m.group(1))
    m = re.search(r'Total:\s*\d+\s*→\s*(\d+)', md)
    if m:
        out['total'] = int(m.group(1))
    return out


def format_msg(today_md, yest_md, today_date):
    t_funnel = parse_funnel(today_md)
    y_funnel = parse_funnel(yest_md) if yest_md else {}
    t_q = parse_qcomment(today_md)
    t_tempo = parse_tempo(today_md)

    def delta(key):
        if not y_funnel:
            return ''
        d = t_funnel.get(key, 0) - y_funnel.get(key, 0)
        if d == 0:
            return ''
        return f' ({d:+d})'

    pub = t_funnel.get('На reviews.yandex.ru', 0)
    on_mod = t_funnel.get('Биржа отдала, ждём', 0)
    okpon = t_funnel.get('Match с Sheet2', 0)
    failed = t_funnel.get('Переписать', 0)
    lost = t_funnel.get('Деньги ушли, отзыв не появился', 0)

    now_str = datetime.now().strftime('%d.%m %H:%M')
    L = [f'📊 BluMart ORM — {now_str} МСК', '', '```']
    L.append(f'Опубликовано:   {pub}{delta("На reviews.yandex.ru")}')
    L.append(f'На модерации:   {on_mod}{delta("Биржа отдала, ждём")}')
    L.append(f'У okponrussia:  {okpon}{delta("Match с Sheet2")}')
    if failed:
        L.append(f'НЕ прошли мод.: {failed} ⚠️')
    if lost:
        L.append(f'Потрачены 0:    {lost} 💸')
    if t_tempo.get('tempo') is not None and t_tempo.get('target'):
        gap = t_tempo['target'] - t_tempo['tempo']
        L.append(f'Темп: {t_tempo["tempo"]:.2f}/день (цель {t_tempo["target"]}, недобор {gap:.2f})')
    if t_tempo.get('rating') is not None:
        L.append(f'Рейтинг: {t_tempo["rating"]}')
    L.append('```')

    if t_q.get('balance') is not None:
        L.append('')
        L.append('🔧 qcomment:')
        warn = ' ⚠️ ПОПОЛНИТЬ' if t_q['balance'] < 500 else ''
        L.append(f'• Баланс: {t_q["balance"]:.0f} ₽{warn}')
        if t_q.get('pending_accept'):
            L.append(f'• 🚨 Принять (auto-accept ≤3 дн): {t_q["pending_accept"]}')
            for pid, lab in t_q['pending_list'][:5]:
                L.append(f'  • {pid} — {lab}')

    actions = []
    if t_q.get('pending_accept'):
        actions.append('принять qcomment работы')
    if t_q.get('balance') is not None and t_q['balance'] < 500:
        actions.append(f'пополнить qcomment ({t_q["balance"]:.0f} ₽)')
    if failed:
        actions.append(f'переписать {failed} (модерация ЯК отклонила)')
    if t_tempo.get('tempo') is not None and t_tempo.get('target') and t_tempo['tempo'] < t_tempo['target']:
        gap = t_tempo['target'] - t_tempo['tempo']
        actions.append(f'добавить +{gap:.1f}/день к темпу')

    if actions:
        L.append('')
        L.append('🎯 Действия:')
        for a in actions:
            L.append(f'• {a}')

    L.append('')
    L.append(f'📊 https://artvision.pro/orm-command-center/{CLIENT}.html')
    L.append(f'src: orders-state-{today_date.isoformat()}.md')
    return '\n'.join(L)


def main():
    today = date.today()
    today_file = find_state_file(today)
    if not today_file:
        today = today - timedelta(days=1)
        today_file = find_state_file(today)
    if not today_file:
        print(f'❌ Нет orders-state для {date.today()} и вчера. Запусти orm-pulse refresh.', file=sys.stderr)
        sys.exit(1)

    yest_file = find_state_file(today - timedelta(days=1))
    today_md = today_file.read_text(encoding='utf-8')
    yest_md = yest_file.read_text(encoding='utf-8') if yest_file else None

    msg = format_msg(today_md, yest_md, today)
    print(msg)

    if not TG_SEND.exists():
        print(f'❌ tg-send.sh not found: {TG_SEND}', file=sys.stderr)
        sys.exit(2)
    r = subprocess.run([str(TG_SEND), 'anton', msg], capture_output=True, text=True)
    if r.returncode == 0 or 'msg_id' in r.stdout:
        print('✅ Sent to anton')
    else:
        print(f'⚠️  tg-send rc={r.returncode}\n  STDOUT: {r.stdout}\n  STDERR: {r.stderr}', file=sys.stderr)


if __name__ == '__main__':
    main()
