"""v218 · carpetas de Mis creaciones (servidor de pruebas): crear, meter, sacar, renombrar, borrar; solo creaciones de la propia cuenta; cada cuenta ve solo las suyas.
No genera nada. Deja la cuenta como estaba (borra la carpeta de prueba)."""
import json, os, sys, urllib.request, urllib.error
B = 'http://127.0.0.1:8770'; DATOS = os.path.expanduser('~/.aria-studio/servidor-datos/usuarios')
def pide(uid, ruta, body=None):
    r = urllib.request.Request(B + ruta, data=json.dumps(body).encode() if body is not None else None, headers={'X-Dev-Uid': uid, 'Content-Type': 'application/json'})
    try: x = urllib.request.urlopen(r, timeout=30); return x.status, json.loads(x.read())
    except urllib.error.HTTPError as e: return e.code, json.loads(e.read() or b'{}')
fallos = []
def ok(n, c, d=''):
    print(('  ✓ ' if c else '  ✕ ') + n + (' · ' + str(d)[:200] if d and not c else ''))
    if not c: fallos.append(n)
def creaciones(uid):
    d = os.path.join(DATOS, uid, 'assets', 'live')
    return ['assets/live/' + f for f in sorted(os.listdir(d)) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')) and '_' in f] if os.path.isdir(d) else []
con = sorted(((len(creaciones(u)), u) for u in os.listdir(DATOS) if len(u) == 36), reverse=True)
if len(con) < 2 or con[0][0] < 2: print('hacen falta dos cuentas de prueba y una con 2 creaciones'); sys.exit(1)
YO = con[0][1]; mias = creaciones(YO)[:3]; OTRA = next(u for n, u in con if u != YO); ajenas = creaciones(OTRA)[:1]
print('cuenta', YO[:8], '·', len(mias), 'creaciones · otra', OTRA[:8])
st, d = pide(YO, '/api/carpetas'); antes = d.get('carpetas'); ok('listar', st == 200 and isinstance(antes, list), (st, d))
for c in antes or []:
    if c['nombre'].startswith('Prueba v218'): pide(YO, '/api/carpetas', {'accion': 'borrar', 'id': c['id']})
st, d = pide(YO, '/api/carpetas', {'accion': 'crear', 'nombre': '  Prueba   v218  ', 'files': mias[:2] + ['assets/live/no_existe.png', '../../secreto.json'] + ajenas})
c = next((x for x in d.get('carpetas') or [] if x['nombre'] == 'Prueba v218'), None)
ok('crear con creaciones (nombre limpio)', st == 200 and c is not None, (st, d))
ok('solo entran las creaciones de la cuenta que existen', c and sorted(c['items']) == sorted(mias[:2]), c)
cid = c['id'] if c else ''
st, d = pide(YO, '/api/carpetas', {'accion': 'crear', 'nombre': 'prueba V218'}); ok('nombre repetido, no', st == 400, (st, d))
st, d = pide(YO, '/api/carpetas', {'accion': 'crear', 'nombre': '   '}); ok('sin nombre, no', st == 400, (st, d))
st, d = pide(YO, '/api/carpetas', {'accion': 'meter', 'id': cid, 'files': [mias[0] + '?v=3', mias[-1]]}); c = next(x for x in d['carpetas'] if x['id'] == cid)
ok('meter no duplica (y quita el ?v=)', sorted(c['items']) == sorted(set(mias[:2] + [mias[-1]])), c)
st, d = pide(YO, '/api/carpetas', {'accion': 'sacar', 'id': cid, 'files': [mias[0]]}); c = next(x for x in d['carpetas'] if x['id'] == cid)
ok('sacar', mias[0] not in c['items'] and os.path.isfile(os.path.join(DATOS, YO, mias[0])), c)
st, d = pide(YO, '/api/carpetas', {'accion': 'renombrar', 'id': cid, 'nombre': 'Prueba v218 b'}); ok('renombrar', st == 200 and any(x['nombre'] == 'Prueba v218 b' for x in d['carpetas']), (st, d))
st, d = pide(OTRA, '/api/carpetas'); ok('otra cuenta no la ve', st == 200 and not any(x['id'] == cid for x in d['carpetas']), d)
st, d = pide(OTRA, '/api/carpetas', {'accion': 'meter', 'id': cid, 'files': ajenas}); ok('otra cuenta no puede tocarla', st == 400, (st, d))
st, d = pide(YO, '/api/carpetas', {'accion': 'borrar', 'id': cid}); ok('borrar la carpeta', st == 200 and not any(x['id'] == cid for x in d['carpetas']), (st, d))
ok('las creaciones siguen en su sitio', all(os.path.isfile(os.path.join(DATOS, YO, m)) for m in mias))
st, d = pide(YO, '/api/carpetas'); ok('queda como estaba', d.get('carpetas') == [x for x in antes if not x['nombre'].startswith('Prueba v218')], d)
print('fallos:', fallos or 'ninguno'); sys.exit(1 if fallos else 0)
