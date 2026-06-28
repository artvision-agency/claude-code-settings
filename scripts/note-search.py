#!/usr/bin/env python3
"""
note-search.py — единый БЕСПЛАТНЫЙ поиск по:
  1) Telegram «Избранное» (Saved Messages) через Telethon
  2) Google Keep заметки justtrance@gmail.com через gkeepapi

Заточен под поиск по 3 цифрам (#касса 235 191 448 и т.п.), но ищет и текст.

Примеры:
  note-search.py 235 191 448            # AND: сообщения/заметки со ВСЕМИ тремя числами
  note-search.py --any 235 191 448      # OR: с любым из чисел
  note-search.py "#касса"               # текстовый поиск
  note-search.py --tg-only 235 191      # только Telegram
  note-search.py --keep-only касса      # только Keep
  note-search.py --keep-auth-token 'oauth2_4/...'  # одноразовая настройка Keep
  note-search.py --keep-auth-app 'app-password'    # альтернатива: app-password

Бесплатно. Повторяемо. Токены — в tokens.json (google_keep).
"""
import sys, os, re, json, argparse, asyncio, shutil, tempfile

TOKENS = '/Users/antonk/artvision-data/tokens.json'
TG_API_ID = 35195969
TG_API_HASH = '576ad787126be6f43f28df1a1279aa4a'
TG_SESSION = '/Users/antonk/.claude/state/telethon_session.session'
KEEP_EMAIL_DEFAULT = 'justtrance@gmail.com'


def load_tokens():
    try:
        with open(TOKENS) as f:
            return json.load(f)
    except Exception:
        return {}


def save_keep_token(email, master_token):
    d = load_tokens()
    d.setdefault('google_keep', {})
    d['google_keep']['email'] = email
    d['google_keep']['master_token'] = master_token
    d['google_keep']['_desc'] = 'Google Keep master token для gkeepapi (note-search.py)'
    with open(TOKENS, 'w') as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    print(f"[keep] master_token сохранён в tokens.json/google_keep ({email})", file=sys.stderr)


def build_matcher(terms, mode_any):
    """Возвращает функцию match(text)->bool. Числа матчатся как целые токены (\\b)."""
    checks = []
    for t in terms:
        if re.fullmatch(r'\d+', t):
            checks.append(re.compile(r'(?<!\d)' + re.escape(t) + r'(?!\d)'))
        else:
            esc = re.escape(t.lower())
            checks.append(re.compile(esc))
    def match(text):
        low = text.lower()
        results = []
        for c in checks:
            results.append(bool(c.search(low)))
        return any(results) if mode_any else all(results)
    return match


# ---------------- Telegram ----------------
async def search_tg(matcher, limit):
    try:
        from telethon import TelegramClient
    except ImportError:
        return None, "telethon не установлен (pip install telethon)"
    # копируем сессию чтобы не словить database is locked (демон держит оригинал)
    tmpdir = tempfile.mkdtemp(prefix='nsearch_')
    sess_copy = os.path.join(tmpdir, 'tg')
    try:
        if os.path.exists(TG_SESSION):
            shutil.copy(TG_SESSION, sess_copy + '.session')
        else:
            return None, f"нет файла сессии {TG_SESSION}"
        c = TelegramClient(sess_copy, TG_API_ID, TG_API_HASH)
        await c.connect()
        if not await c.is_user_authorized():
            await c.disconnect()
            return None, "Telethon не авторизован"
        hits = []
        async for m in c.iter_messages('me', limit=limit):
            t = m.text or ''
            if t and matcher(t):
                hits.append({
                    'date': m.date.strftime('%Y-%m-%d %H:%M'),
                    'id': m.id,
                    'text': t.replace('\n', ' / ').strip()[:240],
                })
        await c.disconnect()
        return hits, None
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------- Google Keep ----------------
def keep_auth_with_token(email, oauth_token):
    import gpsoauth
    android_id = '0123456789abcdef'
    res = gpsoauth.exchange_token(email, oauth_token, android_id)
    tok = res.get('Token')
    if not tok:
        raise RuntimeError(f"exchange_token не вернул Token: {res}")
    return tok


def keep_auth_with_app(email, app_password):
    import gpsoauth
    android_id = '0123456789abcdef'
    res = gpsoauth.perform_master_login(email, app_password, android_id)
    tok = res.get('Token')
    if not tok:
        raise RuntimeError(f"perform_master_login не вернул Token: {res}")
    return tok


def search_keep(matcher):
    try:
        import gkeepapi
    except ImportError:
        return None, "gkeepapi не установлен (pip install gkeepapi)"
    d = load_tokens()
    cfg = d.get('google_keep', {})
    email = cfg.get('email')
    master = cfg.get('master_token')
    if not (email and master):
        return None, "NO_TOKEN"
    try:
        keep = gkeepapi.Keep()
        # gkeepapi 0.17: authenticate(email, master_token) или resume
        try:
            keep.authenticate(email, master, sync=True)
        except TypeError:
            keep.resume(email, master, sync=True)
        notes = list(keep.all())
        hits = []
        for n in notes:
            blob = ((n.title or '') + '\n' + (n.text or '')).strip()
            # списки Keep: подтянуть items
            try:
                if hasattr(n, 'items'):
                    blob += '\n' + '\n'.join((it.text or '') for it in n.items)
            except Exception:
                pass
            if blob and matcher(blob):
                ts = ''
                try:
                    ts = n.timestamps.updated.strftime('%Y-%m-%d %H:%M')
                except Exception:
                    pass
                hits.append({
                    'date': ts,
                    'title': (n.title or '').strip()[:80],
                    'text': blob.replace('\n', ' / ').strip()[:240],
                })
        return hits, None
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def run_selftest():
    """Детерминированный verify-gate: проверяет логику matcher без сети."""
    cases = [
        # (terms, any_mode, text, expected)
        (['235', '191', '448'], False, '#касса 28.06.26 235 191 448', True),   # AND все есть
        (['235', '191', '448'], False, 'касса 235 191', False),                # AND не все
        (['235', '191', '448'], True,  'касса 235 only', True),                # OR один есть
        (['235'], False, 'avito.ru/7615600235?context', False),                # число внутри URL не матчит (\b)
        (['235'], False, 'итог 235 руб', True),                                # отдельное число матчит
        (['касса'], False, '#КАССА за день', True),                            # регистронезависимо
        (['касса'], False, 'выручка дня', False),                              # нет слова
    ]
    fails = []
    for terms, any_mode, text, exp in cases:
        got = build_matcher(terms, any_mode)(text)
        ok = (got == exp)
        if not ok:
            fails.append((terms, any_mode, text, exp, got))
        print(f"  [{'PASS' if ok else 'FAIL'}] {'OR' if any_mode else 'AND'} {terms} ∈ {text!r} -> {got} (ждали {exp})")
    print(f"\nSELFTEST: {len(cases)-len(fails)}/{len(cases)} PASS" + (" ✅" if not fails else " ❌"))
    return 0 if not fails else 1


def main():
    ap = argparse.ArgumentParser(description='Единый поиск TG-Избранное + Google Keep')
    ap.add_argument('terms', nargs='*', help='слова/числа для поиска')
    ap.add_argument('--any', action='store_true', help='OR вместо AND (по умолчанию AND)')
    ap.add_argument('--tg-only', action='store_true')
    ap.add_argument('--keep-only', action='store_true')
    ap.add_argument('--limit', type=int, default=5000, help='глубина скана TG (def 5000)')
    ap.add_argument('--keep-auth-token', help='одноразово: oauth_token из браузера -> master_token')
    ap.add_argument('--keep-auth-app', help='одноразово: app-password -> master_token')
    ap.add_argument('--keep-email', default=KEEP_EMAIL_DEFAULT)
    ap.add_argument('--selftest', action='store_true', help='детерминированный verify-gate логики matcher')
    args = ap.parse_args()

    if args.selftest:
        sys.exit(run_selftest())

    # режим настройки Keep
    if args.keep_auth_token or args.keep_auth_app:
        try:
            if args.keep_auth_token:
                tok = keep_auth_with_token(args.keep_email, args.keep_auth_token)
            else:
                tok = keep_auth_with_app(args.keep_email, args.keep_auth_app)
            save_keep_token(args.keep_email, tok)
            print("OK: Keep настроен. Теперь note-search.py ищет и в заметках.")
        except Exception as e:
            print(f"FAIL keep-auth: {type(e).__name__}: {e}", file=sys.stderr)
            sys.exit(1)
        return

    if not args.terms:
        ap.print_help()
        sys.exit(0)

    matcher = build_matcher(args.terms, args.any)
    mode = 'OR' if args.any else 'AND'
    print(f"== Поиск [{mode}]: {' '.join(args.terms)} ==\n")

    do_tg = not args.keep_only
    do_keep = not args.tg_only

    if do_tg:
        hits, err = asyncio.run(search_tg(matcher, args.limit))
        print("### Telegram «Избранное»")
        if err:
            print(f"  ⚠️ {err}")
        elif not hits:
            print("  (нет совпадений)")
        else:
            for h in hits:
                print(f"  [{h['date']}] msg{h['id']}: {h['text']}")
        print()

    if do_keep:
        hits, err = search_keep(matcher)
        print("### Google Keep заметки")
        if err == 'NO_TOKEN':
            print("  ⚠️ Keep не настроен. Одноразовый шаг (бесплатно):")
            print("     1) Открой в браузере https://accounts.google.com/EmbeddedSetup")
            print("        войди как justtrance@gmail.com, в DevTools→Application→Cookies")
            print("        скопируй значение cookie 'oauth_token' (начинается с oauth2_4/...)")
            print("     2) note-search.py --keep-auth-token 'oauth2_4/...'")
            print("     ИЛИ через app-password: note-search.py --keep-auth-app 'xxxx xxxx xxxx xxxx'")
        elif err:
            print(f"  ⚠️ {err}")
        elif not hits:
            print("  (нет совпадений)")
        else:
            for h in hits:
                ttl = f" «{h['title']}»" if h['title'] else ''
                print(f"  [{h['date']}]{ttl}: {h['text']}")
        print()


if __name__ == '__main__':
    main()
