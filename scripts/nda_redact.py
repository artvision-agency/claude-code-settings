#!/usr/bin/env python3
"""NDA-редактор v2: по whisper-json с таймкодами слов глушит NDA-слова (silence)
и вычищает их из транскрипта. Морфология (pymorphy3) ловит все падежи русского.
Аудит-лог замен — локально (для проверки человеком, юр.требование).

Использование: nda_redact.py <whisper.json> <stoplist.txt> <audio_in> <audio_out> <txt_out>
"""
import json, sys, re, subprocess

try:
    import pymorphy3
    _morph = pymorphy3.MorphAnalyzer()
except Exception:
    _morph = None

PAD = 0.20  # запас по краям слова, сек (round_table: 150-300мс)

def norm(w):
    return re.sub(r'[^0-9a-zа-яё]', '', w.lower())

def lemma(w):
    n = norm(w)
    if not n or _morph is None:
        return n
    try:
        return _morph.parse(n)[0].normal_form
    except Exception:
        return n

json_path, stoplist_path, audio_in, audio_out, txt_out = sys.argv[1:6]

stop_norm, stop_lemma = set(), set()
with open(stoplist_path, encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        for tok in line.split():
            nn = norm(tok)
            if nn:
                stop_norm.add(nn)
                stop_lemma.add(lemma(tok))

data = json.load(open(json_path, encoding='utf-8'))
windows, red_lines, audit, hits = [], [], [], 0
for seg in data.get('segments', []):
    words = seg.get('words') or []
    if words:
        out = []
        for w in words:
            token = w.get('word', '')
            nn = norm(token)
            if nn and (nn in stop_norm or lemma(token) in stop_lemma):
                hits += 1
                s, e = max(0, w['start'] - PAD), w['end'] + PAD
                windows.append((s, e))
                audit.append(f"{s:7.2f}s  {token.strip()}")
                out.append((' ' if token[:1] == ' ' else '') + '███')
            else:
                out.append(token)
        red_lines.append(''.join(out).strip())
    else:
        red_lines.append(seg.get('text', '').strip())

windows.sort()
merged = []
for s, e in windows:
    if merged and s <= merged[-1][1]:
        merged[-1][1] = max(merged[-1][1], e)
    else:
        merged.append([s, e])

with open(txt_out, 'w', encoding='utf-8') as f:
    f.write('\n'.join(red_lines) + '\n')

# Аудит-лог замен — ЛОКАЛЬНО (содержит NDA-слова, не делиться)
log_path = audio_out.rsplit('.', 1)[0] + '-REDACTIONLOG.txt'
with open(log_path, 'w', encoding='utf-8') as f:
    f.write(f"NDA-редакция: заглушено {hits} слов в {len(merged)} участках\n")
    f.write(f"Морфология: {'pymorphy3 (падежи ловятся)' if _morph else 'НЕТ (только точное слово!)'}\n\n")
    f.write('\n'.join(audit) + '\n')

if not merged:
    subprocess.run(['ffmpeg', '-y', '-i', audio_in, '-c', 'copy', audio_out],
                   check=True, capture_output=True)
    print('NDA-совпадений: 0 — звук без изменений')
else:
    expr = '+'.join(f'between(t,{s:.3f},{e:.3f})' for s, e in merged)
    subprocess.run(['ffmpeg', '-y', '-i', audio_in,
                    '-af', f"volume=enable='{expr}':volume=0", audio_out],
                   check=True, capture_output=True)
    print(f'NDA-слов заглушено: {hits} (в {len(merged)} участках)')

print(f'Чистый текст: {txt_out}')
print(f'Чистый звук:  {audio_out}')
print(f'Аудит-лог:    {log_path}  (локально, NDA)')
print('⚠️  ОБЯЗАТЕЛЬНО: прослушай чистую версию перед передачей —')
print('    whisper мог ОСЛЫШАТЬСЯ и не заглушить имя (главная дыра NDA).')
