#!/usr/bin/env python3
"""
gcal.py — non-interactive Google Calendar CLI для Claude

Использует refresh_token из ~/.claude/.cache/gcal-token.json
(создаётся через ~/.claude/scripts/gcal-bootstrap.sh один раз).

Команды:
  list-calendars              — показать все календари
  list-events --start ... --end ... [--calendar primary]
  create --calendar primary --summary "X" --start "2026-05-22 10:30" --duration 60
                              [--alarm-min 1320]  (минут до события для reminder)
                              [--desc "..."] [--location "..."]
  delete --calendar primary --event-id <id>

Все времена в Europe/Moscow если без TZ суффикса.
"""

import argparse, sys, datetime
from pathlib import Path

try:
    import zoneinfo
except ImportError:
    print("ERR: Python 3.9+ required", file=sys.stderr); sys.exit(1)

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

TOKEN_PATH = Path.home() / ".claude" / ".cache" / "gcal-token.json"
SCOPES = ['https://www.googleapis.com/auth/calendar']
MSK = zoneinfo.ZoneInfo("Europe/Moscow")


def load_service():
    if not TOKEN_PATH.exists():
        print(f"ERR: {TOKEN_PATH} not found. Run ~/.claude/scripts/gcal-bootstrap.sh first.", file=sys.stderr)
        sys.exit(2)
    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
            TOKEN_PATH.write_text(creds.to_json())
        else:
            print("ERR: token invalid and cannot refresh. Re-run bootstrap.", file=sys.stderr)
            sys.exit(3)
    return build('calendar', 'v3', credentials=creds, cache_discovery=False)


def parse_dt(s):
    """Парсит '2026-05-22 10:30' или ISO; возвращает datetime с TZ Europe/Moscow."""
    s = s.strip()
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            d = datetime.datetime.strptime(s, fmt)
            return d.replace(tzinfo=MSK)
        except ValueError:
            continue
    # ISO с TZ
    try:
        return datetime.datetime.fromisoformat(s)
    except ValueError:
        raise SystemExit(f"Не могу распарсить дату: {s}")


def cmd_list_calendars(svc, args):
    res = svc.calendarList().list().execute()
    for c in res.get('items', []):
        print(f"  {c['id']:50} {c.get('summary','?')}  primary={c.get('primary', False)}")


def cmd_list_events(svc, args):
    start = parse_dt(args.start).isoformat()
    end = parse_dt(args.end).isoformat()
    res = svc.events().list(
        calendarId=args.calendar,
        timeMin=start, timeMax=end,
        singleEvents=True, orderBy='startTime'
    ).execute()
    items = res.get('items', [])
    print(f"# {len(items)} events in [{args.calendar}] {start} → {end}")
    for ev in items:
        s = ev.get('start', {}).get('dateTime') or ev.get('start', {}).get('date')
        e = ev.get('end', {}).get('dateTime') or ev.get('end', {}).get('date')
        print(f"  [{ev['id']}] {s} → {e}  {ev.get('summary','(no title)')}")
        if ev.get('location'):
            print(f"      📍 {ev['location']}")


def cmd_create(svc, args):
    start = parse_dt(args.start)
    end = start + datetime.timedelta(minutes=args.duration)
    body = {
        'summary': args.summary,
        'start': {'dateTime': start.isoformat(), 'timeZone': 'Europe/Moscow'},
        'end':   {'dateTime': end.isoformat(),   'timeZone': 'Europe/Moscow'},
    }
    if args.desc: body['description'] = args.desc
    if args.location: body['location'] = args.location
    if args.alarm_min:
        body['reminders'] = {
            'useDefault': False,
            'overrides': [{'method': 'popup', 'minutes': args.alarm_min}]
        }
    ev = svc.events().insert(calendarId=args.calendar, body=body).execute()
    print(f"OK: created {ev['id']} in {args.calendar}")
    print(f"  htmlLink: {ev.get('htmlLink')}")


def cmd_delete(svc, args):
    svc.events().delete(calendarId=args.calendar, eventId=args.event_id).execute()
    print(f"OK: deleted {args.event_id}")


def main():
    p = argparse.ArgumentParser()
    sp = p.add_subparsers(dest='cmd', required=True)

    sp.add_parser('list-calendars')

    le = sp.add_parser('list-events')
    le.add_argument('--calendar', default='primary')
    le.add_argument('--start', required=True)
    le.add_argument('--end', required=True)

    c = sp.add_parser('create')
    c.add_argument('--calendar', default='primary')
    c.add_argument('--summary', required=True)
    c.add_argument('--start', required=True, help='"2026-05-22 10:30"')
    c.add_argument('--duration', type=int, default=60, help='minutes')
    c.add_argument('--alarm-min', type=int, default=None, dest='alarm_min')
    c.add_argument('--desc', default=None)
    c.add_argument('--location', default=None)

    d = sp.add_parser('delete')
    d.add_argument('--calendar', default='primary')
    d.add_argument('--event-id', required=True, dest='event_id')

    args = p.parse_args()
    svc = load_service()

    try:
        {'list-calendars': cmd_list_calendars,
         'list-events': cmd_list_events,
         'create': cmd_create,
         'delete': cmd_delete}[args.cmd](svc, args)
    except HttpError as e:
        print(f"GCAL API ERR: {e}", file=sys.stderr); sys.exit(4)


if __name__ == '__main__':
    main()
