"""v220 · compartir una carpeta (servidor de pruebas, por HTTP). Luna comparte una carpeta con Vera (colaboran):
Vera ve SOLO lo que hay en esa carpeta; una tercera cuenta, nada; al dejar de compartir se corta al instante.
No genera nada. Borra la carpeta de prueba al acabar (quedan dos avisos automáticos en la conversación de prueba)."""
import json, os, sys, urllib.request, urllib.error
B = 'http://127.0.0.1:8770'; DATOS = os.path.expanduser('~/.aria-studio/servidor-datos/usuarios')
LUNA = 'aaaaaaaa-0000-4000-8000-000000000001'; VERA = 'cccccccc-0000-4000-8000-000000000001'; TERCERO = 'dddddddd-0000-4000-8000-000000000199'
def pide(uid, ruta, body=None, crudo=False):
    r = urllib.request.Request(B + ruta, data=json.dumps(body).encode() if body is not None else None, headers={'X-Dev-Uid': uid, 'Content-Type': 'application/json'})
    try: x = urllib.request.urlopen(r, timeout=30); b = x.read(); return x.status, (len(b) if crudo else json.loads(b))
    except urllib.error.HTTPError as e: b = e.read(); return e.code, (0 if crudo else json.loads(b or b'{}'))
fallos = []
def ok(n, c, d=''):
    print(('  ✓ ' if c else '  ✕ ') + n + (' · ' + str(d)[:220] if d and not c else ''))
    if not c: fallos.append(n)
d = os.path.join(DATOS, LUNA, 'assets', 'live'); mias = ['assets/live/' + f for f in sorted(os.listdir(d)) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')) and '_' in f]
if len(mias) < 3: print('Luna necesita 3 creaciones'); sys.exit(1)
cL = pide(LUNA, '/api/comunidad')[1]['yo']; cV = pide(VERA, '/api/comunidad')[1]['yo']; cT = pide(TERCERO, '/api/comunidad')[1]['yo']
for c in pide(LUNA, '/api/carpetas')[1]['carpetas']:
    if c['nombre'].startswith('Prueba v220'): pide(LUNA, '/api/carpetas', {'accion': 'borrar', 'id': c['id']})
st, r = pide(LUNA, '/api/carpetas', {'accion': 'crear', 'nombre': 'Prueba v220', 'files': mias[:2]}); kid = next(c['id'] for c in r['carpetas'] if c['nombre'] == 'Prueba v220')
url = lambda f: f'/assets/compartida/{cL}/{kid}/live/{os.path.basename(f)}'
try:
    ok('sin compartir, la otra cuenta no ve el fichero', pide(VERA, url(mias[0]), crudo=True)[0] == 404)
    st, r = pide(LUNA, '/api/carpetas', {'accion': 'compartir', 'id': kid, 'con': cT}); ok('no se comparte con quien no colaboras', st == 400, (st, r))
    st, r = pide(LUNA, '/api/carpetas', {'accion': 'compartir', 'id': kid, 'con': 'c00000000000000'}); ok('ni con un creador inventado', st == 400, (st, r))
    st, r = pide(LUNA, '/api/carpetas', {'accion': 'compartir', 'id': kid, 'con': cV}); c = next(x for x in r['carpetas'] if x['id'] == kid); ok('compartir con quien colaboras', st == 200 and c.get('comp') == [cV], (st, c))
    st, r = pide(VERA, '/api/comunidad'); k = next((x for x in r.get('carpetas') or [] if x['id'] == kid), None); ok('le aparece en la Comunidad con su número', k and k['cid'] == cL and k['n'] == 2, r.get('carpetas'))
    st, r = pide(VERA, f'/api/compartida?cid={cL}&id={kid}'); ok('la lista trae las 2 creaciones', st == 200 and len(r.get('items') or []) == 2, (st, r))
    st, n = pide(VERA, url(mias[0]), crudo=True); ok('el fichero de la carpeta se le sirve', st == 200 and n == os.path.getsize(os.path.join(DATOS, LUNA, mias[0])), (st, n))
    ok('otro fichero de Luna que NO está en la carpeta, no', pide(VERA, url(mias[2]), crudo=True)[0] == 404)
    for malo in (f'/assets/compartida/{cL}/{kid}/live/../../../capa.json', f'/assets/compartida/{cL}/{kid}/personajes/x.jpg', f'/assets/compartida/{cL}/{kid}/live/', f'/assets/compartida/{cL}/k000000000000/live/{os.path.basename(mias[0])}', f'/assets/compartida/{cL}/{kid}/live/{os.path.basename(mias[0])}.json'):
        ok('ruta rara → 404: …' + malo[-34:], pide(VERA, malo, crudo=True)[0] == 404)
    ok('una tercera cuenta no ve el fichero', pide(TERCERO, url(mias[0]), crudo=True)[0] == 404)
    ok('ni la lista', pide(TERCERO, f'/api/compartida?cid={cL}&id={kid}')[0] == 404)
    ok('la propia dueña no entra por esa puerta (usa la suya)', pide(LUNA, url(mias[0]), crudo=True)[0] == 404)
    st, m = pide(VERA, f'/api/comunidad/chat?con={cL}'); ok('aviso automático en la conversación', any('Prueba v220' in x.get('x', '') and x.get('auto') for x in m.get('mensajes') or []), m)
    st, r = pide(LUNA, '/api/carpetas', {'accion': 'sacar', 'id': kid, 'files': [mias[0]]}); ok('al sacarla de la carpeta deja de verla', pide(VERA, url(mias[0]), crudo=True)[0] == 404 and pide(VERA, url(mias[1]), crudo=True)[0] == 200)
    st, r = pide(LUNA, '/api/carpetas', {'accion': 'compartir', 'id': kid, 'con': cV, 'on': False}); c = next(x for x in r['carpetas'] if x['id'] == kid); ok('dejar de compartir', st == 200 and not c.get('comp'), c)
    ok('se corta al instante', pide(VERA, url(mias[1]), crudo=True)[0] == 404 and pide(VERA, f'/api/compartida?cid={cL}&id={kid}')[0] == 404)
    ok('y desaparece de su Comunidad', not any(x['id'] == kid for x in pide(VERA, '/api/comunidad')[1].get('carpetas') or []))
finally:
    pide(LUNA, '/api/carpetas', {'accion': 'borrar', 'id': kid})
print('fallos:', fallos or 'ninguno'); sys.exit(1 if fallos else 0)
