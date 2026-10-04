"""v202 · el préstamo, contra el servidor de pruebas (:8770). No lanza ninguna generación: las peticiones a /api/generar están hechas para fallar ANTES de enviarse al proveedor.
Cuentas de prueba: Luna (pidió colaboración a Vera, aceptada, cuenta entera), Vera (dueña de «Vera Demo»), Tercero (sin ninguna colaboración)."""
import json, sys, urllib.request, urllib.error
B = 'http://127.0.0.1:8770'
LUNA = 'aaaaaaaa-0000-4000-8000-000000000001'; VERA = 'cccccccc-0000-4000-8000-000000000001'; TERCERO = 'dddddddd-0000-4000-8000-000000000199'
fallos = []

def pide(uid, ruta, body=None, casa=True):
    h = {'X-Dev-Uid': uid, 'Content-Type': 'application/json'}
    if not casa: h['X-Dev-Casa'] = '0'
    r = urllib.request.Request(B + ruta, data=json.dumps(body).encode() if body is not None else None, headers=h)
    try:
        x = urllib.request.urlopen(r, timeout=30); return x.status, x.read(), x.headers.get('Content-Type', '')
    except urllib.error.HTTPError as e: return e.code, e.read(), e.headers.get('Content-Type', '')

def js(uid, ruta, body=None, casa=True):
    st, b, _ = pide(uid, ruta, body, casa)
    try: return st, json.loads(b)
    except Exception: return st, {'_crudo': b[:200].decode('utf-8', 'replace')}

def ok(nombre, cond, detalle=''):
    print(('  ✓ ' if cond else '  ✕ ') + nombre + (' · ' + str(detalle) if detalle and not cond else ''))
    if not cond: fallos.append(nombre)

st, dL = js(LUNA, '/api/comunidad'); st2, dV = js(VERA, '/api/comunidad'); st3, dT = js(TERCERO, '/api/comunidad')
cV = dV['yo']; cL = dL['yo']
print('1) qué ve cada cuenta')
pl = dL.get('prestados') or []
ok('Luna puede crear con Vera Demo', any(p['cid'] == cV and p['pid'] == 'vera-demo' for p in pl), pl)
ok('lo prestado trae nombre y creador, sin rutas', all(set(p) <= {'cid', 'pid', 'nombre', 'creador', 'cuerpo', 'peinado', 'genero', 'complexion', 'altura', 'pecho', 'cadera', 'ojos', 'ojosHex', 'peloNombre', 'peloHex', 'peloColor'} for p in pl), [sorted(p) for p in pl])
ok('Vera no tiene nada prestado (ella no ha pedido nada que le hayan aceptado)', not (dV.get('prestados') or []), dV.get('prestados'))
ok('el tercero no tiene nada prestado', not (dT.get('prestados') or []), dT.get('prestados'))
crudo = json.dumps([dL, dV, dT])
ok('ninguna respuesta lleva un uid ni un correo', not any(x in crudo for x in (LUNA, VERA, TERCERO, '@dev.local', '@example')), '')

print('2) lo que se sirve al navegador')
base = f'/assets/prestamo/{cV}/vera-demo/'
st, b, ct = pide(LUNA, base + 'foto.jpg'); ok('Luna ve el avatar de Vera Demo', st == 200 and ct.startswith('image/') and len(b) > 500, (st, ct, len(b)))
for fn in ('ficha.jpg', 'cuerpo.jpg', 'personaje.json', 'ficha360.jpg', 'foto.jpg/..', '../vera-demo/foto.jpg'):
    st, b, ct = pide(LUNA, base + fn); ok(f'Luna NO puede bajarse {fn}', st in (400, 403, 404) and not ct.startswith('image/'), (st, ct))
st, b, ct = pide(TERCERO, base + 'foto.jpg'); ok('el tercero no ve nada de Vera por esta vía', st == 404, st)
st, b, ct = pide(VERA, f'/assets/prestamo/{cL}/luna-demo/foto.jpg'); ok('Vera (solicitud suya aún pendiente) no ve nada de Luna', st == 404, st)
st, b, ct = pide(LUNA, f'/assets/prestamo/{cL}/luna-demo/foto.jpg'); ok('una cuenta no se «presta» a sí misma', st == 404, st)
st, b, ct = pide(LUNA, f'/assets/prestamo/{cV}/no-existe/foto.jpg'); ok('personaje inexistente → 404', st == 404, st)
st, b, ct = pide(LUNA, '/assets/prestamo/c00000000000000/vera-demo/foto.jpg'); ok('creador inexistente → 404', st == 404, st)

print('3) al generar (sin llegar a enviar nada al proveedor)')
lent = {'path': f'assets/prestamo/{cV}/vera-demo/ficha.jpg'}; malo = {'path': 'assets/live/no-existe-para-la-prueba.jpg'}
st, r = js(LUNA, '/api/generar', {'model': 'seedflash', 'prompt': 'two women, nsfw', 'images': [lent, malo]})
ok('con NSFW en el prompt se rechaza', st == 400 and 'NSFW' in str(r.get('error')), (st, r))
st, r = js(LUNA, '/api/generar', {'model': 'seedflash', 'prompt': 'two women smiling', 'meta': {'nsfw': True}, 'images': [lent, malo]})
ok('con la marca NSFW se rechaza', st == 400 and 'NSFW' in str(r.get('error')), (st, r))
st, r = js(LUNA, '/api/generar', {'model': 'seedflash', 'prompt': 'two women smiling', 'images': [lent, malo]})
e = str(r.get('error')); ok('Luna: la ficha prestada se resuelve (falla después, por la clave o por la otra ruta)', st >= 400 and 'permiso' not in e and 'request_id' not in r, (st, e[:160]))
print('     → el servidor dijo:', e[:120])
st, r = js(TERCERO, '/api/generar', {'model': 'seedflash', 'prompt': 'two women smiling', 'images': [lent, malo]})
e = str(r.get('error')); ok('el tercero: la ficha NO se resuelve', st >= 400 and 'permiso' in e, (st, e[:160]))
# fuera de /api/generar la ruta prestada no vale: ni para copiarla a un personaje propio ni como recorte
st, r = js(LUNA, '/api/personaje', {'p': {'id': 'prueba-robo', 'nombre': 'Prueba Robo'}, 'copy': {'ficha360': lent['path']}})
robado = (r.get('p') or {}).get('ficha360'); ok('no se puede copiar la ficha prestada a un personaje propio', not robado, r)
st, r = js(LUNA, '/api/personaje', {'p': {'id': 'prueba-robo', 'nombre': 'Prueba Robo'}, 'crops': {'foto': {'path': lent['path']}}})
ok('ni usarla como recorte', st >= 400 or not (r.get('p') or {}).get('foto'), (st, str(r)[:160]))
js(LUNA, '/api/personaje_borrar', {'id': 'prueba-robo'})   # el personaje de la prueba, fuera

print('4) ocultar o retirar corta el préstamo')
js(VERA, '/api/comunidad', {'accion': 'visible', 'pid': 'vera-demo', 'publico': False})
st, b, ct = pide(LUNA, base + 'foto.jpg'); st2, d2 = js(LUNA, '/api/comunidad')
ok('personaje oculto → deja de servirse y sale de «prestados»', st == 404 and not (d2.get('prestados') or []), (st, d2.get('prestados')))
js(VERA, '/api/comunidad', {'accion': 'visible', 'pid': 'vera-demo', 'publico': True})
st, b, ct = pide(LUNA, base + 'foto.jpg'); ok('al volver a hacerlo público, vuelve', st == 200, st)
print('fallos:', fallos or 'ninguno')
sys.exit(1 if fallos else 0)
