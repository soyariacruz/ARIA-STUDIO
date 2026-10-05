"""v237 · Fototeca de la comunidad (servidor de pruebas, por HTTP). Luna publica creaciones: cualquier cuenta las ve con su prompt, las importa y las puede denunciar
(desaparecen para todos). Lo oculto no se publica. No genera nada. Deja todo como estaba (quita la publicación, lo importado y la denuncia de prueba)."""
import json, os, sys, time, urllib.request, urllib.error
B = 'http://127.0.0.1:8770'; DATOS = os.path.expanduser('~/.aria-studio/servidor-datos')
LUNA = 'aaaaaaaa-0000-4000-8000-000000000001'; VERA = 'cccccccc-0000-4000-8000-000000000001'; TERCERO = 'dddddddd-0000-4000-8000-000000000199'
def pide(uid, ruta, body=None, crudo=False):
    r = urllib.request.Request(B + ruta, data=json.dumps(body).encode() if body is not None else None, headers={'X-Dev-Uid': uid, 'Content-Type': 'application/json'})
    try: x = urllib.request.urlopen(r, timeout=30); b = x.read(); return x.status, (len(b) if crudo else json.loads(b))
    except urllib.error.HTTPError as e: b = e.read(); return e.code, (0 if crudo else json.loads(b or b'{}'))
fallos = []
def ok(n, c, d=''):
    print(('  ✓ ' if c else '  ✕ ') + n + (' · ' + str(d)[:220] if d and not c else ''))
    if not c: fallos.append(n)
d = os.path.join(DATOS, 'usuarios', LUNA, 'assets', 'live'); mias = []
for fn in sorted(os.listdir(d)):
    if not fn.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')) or '_' not in fn: continue
    try: m = json.load(open(os.path.join(d, fn) + '.json'))
    except Exception: m = {}
    if not (m.get('hidden') or m.get('nsfw') or m.get('colab') or m.get('importada')): mias.append('assets/live/' + fn)
if len(mias) < 2: print('Luna necesita 2 creaciones publicables'); sys.exit(1)
cL = pide(LUNA, '/api/comunidad')[1]['yo']; a, b = mias[0], mias[1]; ra = f'assets/publica/{cL}/live/{os.path.basename(a)}'; rb = f'assets/publica/{cL}/live/{os.path.basename(b)}'
lista = lambda u, q='': pide(u, '/api/publicas?tipo=image' + q)[1].get('items') or []
antes_v = set(os.listdir(os.path.join(DATOS, 'usuarios', VERA, 'assets', 'live'))) if os.path.isdir(os.path.join(DATOS, 'usuarios', VERA, 'assets', 'live')) else set()
try:
    ok('sin publicar, nadie la ve', pide(VERA, '/' + ra, crudo=True)[0] == 404 and not any(x['f'] == ra for x in lista(VERA)))
    st, r = pide(LUNA, '/api/carpetas', {'accion': 'publicar_una', 'files': [a, b]}); k = next((c for c in r.get('carpetas') or [] if c.get('pubauto')), None); ok('publicar dos creaciones sueltas', st == 200 and k and set(k['items']) >= {a, b} and k.get('pub'), (st, k))
    L = lista(VERA); x = next((z for z in L if z['f'] == ra), None); ok('otra cuenta la ve en la Fototeca de la comunidad, con su prompt', x and x['cid'] == cL and 'prompt' in x and not x['mia'], L[:1])
    ok('la autora la ve marcada como suya', any(z['f'] == ra and z['mia'] for z in lista(LUNA)))
    ok('cualquier miembro, sin colaborar, también', any(z['f'] == ra for z in lista(TERCERO)) and pide(TERCERO, '/' + ra, crudo=True)[0] == 200)
    ok('filtro por creador', all(z['cid'] == cL for z in lista(VERA, '&cid=' + cL)) and not lista(VERA, '&cid=c00000000000000'))
    for malo in (f'/assets/publica/{cL}/live/../../../capa.json', f'/assets/publica/{cL}/live/{os.path.basename(mias[-1])}' if mias[-1] not in (a, b) else f'/assets/publica/{cL}/live/no.jpg', f'/assets/publica/{cL}/personajes/x.jpg', f'/assets/publica/{cL}/live/{os.path.basename(a)}.json'):
        ok('ruta rara o no publicada → 404: …' + malo[-30:], pide(VERA, malo, crudo=True)[0] == 404)
    st, r = pide(LUNA, '/api/ocultar', {'file': b, 'hidden': True}); ok('al ocultarla deja de estar publicada', not any(z['f'] == rb for z in lista(VERA)) and pide(VERA, '/' + rb, crudo=True)[0] == 404)
    pide(LUNA, '/api/ocultar', {'file': b, 'hidden': False})
    st, r = pide(VERA, '/api/carpetas', {'accion': 'importar_pub', 'files': [ra]}); ok('importarla a mis creaciones', st == 200 and r.get('n') == 1, (st, r))
    st, r = pide(LUNA, '/api/carpetas', {'accion': 'importar_pub', 'files': [ra]}); ok('la autora no importa lo suyo', st == 200 and r.get('n') == 0, (st, r))
    st, r = pide(TERCERO, '/api/comunidad', {'accion': 'denunciar', 'f': ra}); ok('denunciar', st == 200, (st, r))
    ok('desaparece para todos al momento', not any(z['f'] == ra for z in lista(VERA)) and pide(VERA, '/' + ra, crudo=True)[0] == 404 and not any(z['f'] == ra for z in lista(LUNA)))
    ok('lo importado se queda', any(f.startswith('importada_pub-') for f in os.listdir(os.path.join(DATOS, 'usuarios', VERA, 'assets', 'live'))))
    st, r = pide(LUNA, '/api/carpetas', {'accion': 'publicar_una', 'files': [b], 'on': False}); ok('quitar una de la comunidad', not any(z['f'] == rb for z in lista(VERA)))
finally:
    pide(LUNA, '/api/carpetas', {'accion': 'publicar_una', 'files': [a, b], 'on': False})
    for c in pide(LUNA, '/api/carpetas')[1]['carpetas']:
        if c.get('pubauto') and not c['items']: pide(LUNA, '/api/carpetas', {'accion': 'borrar', 'id': c['id']})
    lv = os.path.join(DATOS, 'usuarios', VERA, 'assets', 'live')
    for f in (set(os.listdir(lv)) - antes_v if os.path.isdir(lv) else []): os.remove(os.path.join(lv, f))
    fp = os.path.join(DATOS, 'comunidad.json'); dd = json.load(open(fp, encoding='utf-8'))   # la denuncia de prueba, fuera
    if isinstance(dd.get('den'), dict) and dd['den'].pop(ra[len('assets/publica/'):], None) is not None: json.dump(dd, open(fp, 'w', encoding='utf-8'), ensure_ascii=False)
print('fallos:', fallos or 'ninguno'); sys.exit(1 if fallos else 0)
