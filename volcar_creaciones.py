"""ARIA STUDIO · vuelca las creaciones LOCALES de Max (las que no están ocultas) a su cuenta de la web.

Petición de Max (5 oct 2026), una sola vez, para rellenar la web y hacer una demo. Las ocultas se quedan en local.
No sube variaciones de color, peinados de prueba, fichas de producto ni vídeos. No pisa nada que ya exista en la web.

Necesita ~/.claude/aria-servidor.env (ARIA_URL=…, ARIA_ADMIN=…), la misma llave que la copia de seguridad. No la enseña.

Uso:  python3 volcar_creaciones.py UID --ver     cuenta qué subiría (y qué personajes tiene esa cuenta), sin subir nada
      python3 volcar_creaciones.py UID           sube
"""
import os, sys, json, base64, urllib.request, urllib.error

SRC = '/Volumes/home/🗄 Work/CLAUDE/Aria Mirror/assets/live'
ENV = os.path.expanduser('~/.claude/aria-servidor.env')
AUX = ('variaciones_', 'pelo_', 'personaje_', 'ficha_producto', 'prenda_')

def env():
    d = {}
    for ln in open(ENV, encoding='utf-8'):
        ln = ln.strip()
        if '=' in ln and not ln.startswith('#'):
            k, v = ln.split('=', 1); d[k.replace('export ', '').strip()] = v.strip().strip('"').strip("'")
    return d

def pide(url, adm, body=None):
    r = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, headers={'X-Admin': adm, 'Content-Type': 'application/json'})
    try: x = urllib.request.urlopen(r, timeout=120); return x.status, json.loads(x.read())
    except urllib.error.HTTPError as e: return e.code, {'error': e.read()[:200].decode('utf-8', 'ignore')}

def lista():
    out = []
    for fn in sorted(os.listdir(SRC), key=lambda f: os.path.getmtime(os.path.join(SRC, f))):
        if fn.startswith('.') or not fn.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')) or fn.startswith(AUX): continue
        try: m = json.load(open(os.path.join(SRC, fn) + '.json'))
        except Exception: m = {}
        if m.get('hidden') or m.get('hairVar') or m.get('variaciones'): continue
        out.append((fn, m))
    return out

if __name__ == '__main__':
    if len(sys.argv) < 2: print(__doc__); sys.exit(1)
    uid = sys.argv[1]; E = env(); url = E.get('ARIA_URL', '').rstrip('/'); adm = E.get('ARIA_ADMIN', '')
    if not url or not adm: print('Falta ARIA_URL o ARIA_ADMIN en', ENV); sys.exit(1)
    st, r = pide(f'{url}/api/admin/importar?uid={uid}', adm)
    if st != 200: print('La cuenta no responde:', st, r); sys.exit(1)
    ya = set(r.get('live') or []); L = lista(); nuevas = [x for x in L if x[0] not in ya]
    print(f'Cuenta {uid[:8]}… · personajes: {", ".join(r.get("personajes") or []) or "ninguno"} · ya tiene {len(ya)} archivos')
    print(f'Locales para subir: {len(L)} · nuevas: {len(nuevas)} · {round(sum(os.path.getsize(os.path.join(SRC, f)) for f, _ in nuevas) / 1e6)} MB')
    if '--ver' in sys.argv: sys.exit(0)
    ok = mal = 0
    for i, (fn, m) in enumerate(nuevas, 1):
        data = base64.b64encode(open(os.path.join(SRC, fn), 'rb').read()).decode()
        st, r = pide(f'{url}/api/admin/importar', adm, {'uid': uid, 'file': fn, 'data': data, 'meta': m})
        if st == 200 and r.get('ok'): ok += 1
        else: mal += 1; print('  ✕', fn, st, r)
        if i % 20 == 0: print(f'  … {i}/{len(nuevas)}')
    print(f'Hecho: {ok} subidas · {mal} fallos')
