import json, glob, os
os.chdir(os.path.expanduser('~/.claude/projects/-Users-antonk'))
files = sorted(glob.glob('*.jsonl'), key=os.path.getmtime, reverse=True)[:35]
seen = set(); out = []
for f in files:
    try:
        lines = open(f, encoding='utf-8', errors='ignore').readlines()
    except Exception:
        continue
    for line in lines:
        low0 = line.lower()
        if 'авто' not in low0 and 'avto' not in low0 and 'ворлд' not in low0:
            continue
        try:
            o = json.loads(line)
        except Exception:
            continue
        if o.get('type') != 'user':
            continue
        ts = (o.get('timestamp') or '')[:16]
        if not ts.startswith('2026-06-19'):
            continue
        msg = o.get('message', {}); c = msg.get('content'); txt = ''
        if isinstance(c, str):
            txt = c
        elif isinstance(c, list):
            txt = ' '.join(x.get('text', '') for x in c if isinstance(x, dict) and x.get('type') == 'text')
        low = txt.lower()
        if not txt or 'tool_result' in low:
            continue
        if 'авто' in low or 'avto' in low or 'ворлд' in low:
            k = txt[:50]
            if k in seen:
                continue
            seen.add(k); out.append((ts, txt[:600]))
out.sort()
for ts, txt in out:
    print('[' + ts + '] ' + txt + '\n---')
print('Найдено: ' + str(len(out)) + ' сообщений Антона про Avto за 19.06')
