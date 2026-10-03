"""ARIA STUDIO · sube a Supabase lo que la web necesita y no puede ir en el repositorio.

  · el catálogo (catalog.js, con los prompts)  → almacén PRIVADO «catalogo» (solo lo leen los miembros con sesión)
  · las imágenes de la biblioteca                → almacén público «assets» (misma ruta que en local, sin el «assets/» delante)

No se suben: los originales (`full/`), las miniaturas internas, los vídeos, ni nada personal de Max
(sus creaciones, sus personajes, la papelera, las copias, los duelos).

La clave secreta de Supabase se lee de ~/.claude/supabase.env (línea SUPABASE_SECRET=…). Nunca se escribe ni se enseña.
Solo sube lo nuevo o lo cambiado (apunta lo subido en .subido.json).

Uso:
  python3 subir.py --ver       cuenta qué subiría y cuánto pesa, sin subir nada (no necesita la clave)
  python3 subir.py catalogo    solo el catálogo
  python3 subir.py imagenes    solo las imágenes
  python3 subir.py             las dos cosas
"""
import os, sys, json, mimetypes, urllib.request, urllib.parse, urllib.error
from concurrent.futures import ThreadPoolExecutor

SRC = '/Volumes/home/🗄 Work/CLAUDE/Aria Mirror'
SB = 'https://uhscbgidrloskdjbevkn.supabase.co'
AQUI = os.path.dirname(os.path.abspath(__file__))
APUNTE = os.path.join(AQUI, '.subido.json')
CARPETAS = ['hair', 'expr', 'cartoon', 'movie', 'photo', 'vestidor', 'biblio', 'perfil', 'crear', 'refs', 'conv', 'video']
if '--filmoteca' in sys.argv: CARPETAS.append('videoteca')   # sus imágenes pesan 1,1 GB: no caben en el plan gratis de Supabase (1 GB)
FUERA = {'full', 'generadas'}          # subcarpetas que no se suben
IMG = ('.jpg', '.jpeg', '.png', '.webp', '.gif')


def clave():
    try:
        for ln in open(os.path.expanduser('~/.claude/supabase.env'), encoding='utf-8'):
            if ln.strip().startswith('SUPABASE_SECRET='):
                return ln.split('=', 1)[1].strip().strip('"\'')
    except OSError:
        pass
    sys.exit('Falta la clave: ~/.claude/supabase.env con la línea SUPABASE_SECRET=…')


def pide(method, path, body=None, headers=None, key=None):
    h = {'apikey': key, 'Authorization': 'Bearer ' + key}
    h.update(headers or {})
    req = urllib.request.Request(SB + path, data=body, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def sube(bucket, ruta, fichero, key, cache='3600'):
    ct = mimetypes.guess_type(fichero)[0] or 'application/octet-stream'
    with open(fichero, 'rb') as f:
        body = f.read()
    st, out = pide('POST', f'/storage/v1/object/{bucket}/' + urllib.parse.quote(ruta), body,
                   {'Content-Type': ct, 'x-upsert': 'true', 'cache-control': 'max-age=' + cache}, key)
    return st, out[:200].decode('utf-8', 'replace')


def imagenes():
    """[(ruta en el almacén, fichero en disco, tamaño, fecha)] de todo lo que la web enseña."""
    out = []
    for c in CARPETAS:
        base = os.path.join(SRC, 'assets', c)
        for d, subs, files in os.walk(base):
            subs[:] = [s for s in subs if s not in FUERA and not s.startswith('.')]
            for fn in files:
                if fn.startswith('.') or not fn.lower().endswith(IMG): continue
                fp = os.path.join(d, fn)
                st = os.stat(fp)
                out.append((os.path.relpath(fp, os.path.join(SRC, 'assets')), fp, st.st_size, int(st.st_mtime)))
    # y lo que el catálogo nombra fuera de esas carpetas o que no es imagen (las fichas de Aria en live/, el vídeo de su perfil…)
    ya, refs = {i[0] for i in out}, set()

    def walk(v):
        if isinstance(v, str):
            refs.update(p.split('?')[0] for p in v.split('|') if p.startswith('assets/'))
        elif isinstance(v, list):
            for x in v: walk(x)
        elif isinstance(v, dict):
            for x in v.values(): walk(x)
    walk(json.load(open(os.path.join(SRC, 'catalog.json'), encoding='utf-8')))
    for r in sorted(refs):
        ruta = r[len('assets/'):]
        if ruta in ya or (ruta.startswith('videoteca/') and 'videoteca' not in CARPETAS): continue
        fp = os.path.join(SRC, r)
        if os.path.isfile(fp):
            st = os.stat(fp); out.append((ruta, fp, st.st_size, int(st.st_mtime)))
    return out


def main():
    args = sys.argv[1:]
    ver = '--ver' in args
    que = [a for a in args if not a.startswith('--')] or ['catalogo', 'imagenes']
    ims = imagenes() if 'imagenes' in que else []
    if ver:
        por = {}
        for ruta, _, size, _ in ims:
            k = ruta.split('/')[0]; n, s = por.get(k, (0, 0)); por[k] = (n + 1, s + size)
        for k, (n, s) in sorted(por.items(), key=lambda x: x[1][1]):
            print(f'{s / 1e6:8.1f} MB  {n:5d}  {k}')
        print(f'{sum(i[2] for i in ims) / 1e6:8.1f} MB  {len(ims):5d}  TOTAL imágenes')
        print(f'{os.path.getsize(os.path.join(SRC, "catalog.js")) / 1e6:8.1f} MB         catálogo')
        raros = [i[0] for i in ims if not i[0].isascii()]
        if raros: print(f'OJO: {len(raros)} nombres con tildes o símbolos (Supabase puede rechazarlos), p. ej. {raros[:3]}')
        return
    key = clave()
    try: hecho = json.load(open(APUNTE, encoding='utf-8'))
    except (OSError, ValueError): hecho = {}

    if 'catalogo' in que:
        st, out = sube('catalogo', 'catalog.js', os.path.join(SRC, 'catalog.js'), key, cache='0')
        print('catálogo:', 'subido' if st == 200 else f'ERROR {st} {out}')

    if ims:
        st, out = pide('POST', '/storage/v1/bucket', json.dumps({'id': 'assets', 'name': 'assets', 'public': True}).encode(), {'Content-Type': 'application/json'}, key)
        if st not in (200, 201) and b'already exists' not in out and st != 409:
            sys.exit(f'No se ha podido crear el almacén «assets»: {st} {out[:200]!r}')
        faltan = [i for i in ims if hecho.get(i[0]) != [i[2], i[3]]]
        print(f'imágenes: {len(ims)} en total, {len(faltan)} por subir ({sum(i[2] for i in faltan) / 1e6:.0f} MB)', flush=True)
        errores = []

        def una(i):
            ruta, fp, size, mt = i
            for _ in range(3):
                try:
                    st, out = sube('assets', ruta, fp, key, cache='31536000')
                except Exception as e:   # red: se reintenta
                    st, out = 0, str(e)
                if st == 200: return ruta, [size, mt], None
            return ruta, None, f'{st} {out}'

        with ThreadPoolExecutor(8) as ex:
            for n, (ruta, val, err) in enumerate(ex.map(una, faltan), 1):
                if err: errores.append((ruta, err))
                else: hecho[ruta] = val
                if n % 100 == 0 or n == len(faltan):
                    json.dump(hecho, open(APUNTE, 'w', encoding='utf-8'))
                    print(f'  {n}/{len(faltan)} · errores {len(errores)}', flush=True)
        for ruta, err in errores[:10]: print('  ERROR', ruta, err)
        print('imágenes: LISTO' if not errores else f'imágenes: {len(errores)} con error (vuelve a lanzarlo para reintentar)')


if __name__ == '__main__':
    main()
