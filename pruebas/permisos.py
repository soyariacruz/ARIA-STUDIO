"""v223 · plazo del permiso, modo NSFW de los dos y «abierto a colaborar» (servidor de pruebas, por HTTP). No genera nada:
la única llamada a /api/generar es una que el servidor rechaza antes de enviarla. Deja las colaboraciones como estaban
(quedan avisos automáticos en las conversaciones de prueba)."""
import json, sys, time, urllib.request, urllib.error
B = 'http://127.0.0.1:8770'
LUNA = 'aaaaaaaa-0000-4000-8000-000000000001'; VERA = 'cccccccc-0000-4000-8000-000000000001'; TERCERO = 'dddddddd-0000-4000-8000-000000000199'
def pide(uid, ruta, body=None):
    r = urllib.request.Request(B + ruta, data=json.dumps(body).encode() if body is not None else None, headers={'X-Dev-Uid': uid, 'Content-Type': 'application/json'})
    try: x = urllib.request.urlopen(r, timeout=30); return x.status, json.loads(x.read())
    except urllib.error.HTTPError as e: return e.code, json.loads(e.read() or b'{}')
fallos = []
def ok(n, c, d=''):
    print(('  ✓ ' if c else '  ✕ ') + n + (' · ' + str(d)[:240] if d and not c else ''))
    if not c: fallos.append(n)
com = lambda u: pide(u, '/api/comunidad')[1]
cL = com(LUNA)['yo']; cV = com(VERA)['yo']; cT = com(TERCERO)['yo']
x = next((s for s in com(LUNA)['solicitudes'] if s['de'] == cL and s['para'] == cV and s['estado'] == 'aceptada'), None)
if not x: print('hace falta la colaboración aceptada Luna → Vera'); sys.exit(1)
sid = x['id']; sol = lambda u=LUNA: next(s for s in com(u)['solicitudes'] if s['id'] == sid); prest = lambda: next((p for p in com(LUNA)['prestados'] if p['cid'] == cV), {})
try:
    # ---- plazo
    st, r = pide(LUNA, '/api/comunidad', {'accion': 'plazo', 'id': sid, 'dias': 7}); ok('el plazo no lo pone quien recibe el permiso', st == 403, (st, r))
    st, r = pide(VERA, '/api/comunidad', {'accion': 'plazo', 'id': sid, 'dias': 7}); h = sol().get('hasta') or 0; ok('quien da el permiso pone 7 días', st == 200 and abs(h - time.time() - 7 * 86400) < 120, (st, h))
    st, r = pide(VERA, '/api/comunidad', {'accion': 'plazo', 'id': sid, 'dias': 5}); ok('un plazo que no existe = sin fecha de fin', st == 200 and 'hasta' not in sol(), sol())
    # ---- NSFW: apagado por defecto, solo con los dos
    ok('por defecto, apagado', not prest().get('nsfw'), prest())
    st, r = pide(LUNA, '/api/generar', {'item': 'x', 'model': 'qwen', 'prompt': 'x', 'nsfw': True, 'meta': {'nsfw': True}, 'images': [{'path': f'assets/prestamo/{cV}/vera-demo/ficha.jpg'}]}); ok('generar NSFW con su personaje, apagado → rechazado', st == 400 and 'los dos' in r.get('error', ''), (st, r))
    st, r = pide(LUNA, '/api/comunidad', {'accion': 'nsfw', 'id': sid, 'on': True}); ok('lo activa solo una parte → sigue apagado', st == 200 and not r.get('nsfw') and not prest().get('nsfw'), (st, r))
    st, r = pide(TERCERO, '/api/comunidad', {'accion': 'nsfw', 'id': sid, 'on': True}); ok('un tercero no puede tocarlo', st == 404, (st, r))
    st, r = pide(VERA, '/api/comunidad', {'accion': 'nsfw', 'id': sid, 'on': True, 'dias': 1}); s = sol(); ok('lo activan los dos → encendido, con su plazo de 24 h', st == 200 and r.get('nsfw') and prest().get('nsfw') and abs((s.get('nsfw_hasta') or 0) - time.time() - 86400) < 120, (st, r, s))
    st, r = pide(LUNA, '/api/comunidad', {'accion': 'nsfw', 'id': sid, 'on': False}); ok('cualquiera lo apaga', st == 200 and not r.get('nsfw') and not prest().get('nsfw'), (st, r))
    st, m = pide(VERA, f'/api/comunidad/chat?con={cL}'); ok('queda dicho en la conversación', any('NSFW' in z.get('x', '') and z.get('auto') for z in m.get('mensajes') or []))
    # ---- abierto a colaborar
    st, r = pide(VERA, '/api/comunidad', {'accion': 'abierto', 'pid': 'vera-demo', 'on': True}); pj = next(p for c in com(TERCERO)['cuentas'] if c['cid'] == cV for p in c['personajes'] if p['pid'] == 'vera-demo'); ok('marcar un personaje como abierto', st == 200 and pj.get('abierto'), (st, pj))
    for s0 in com(TERCERO)['solicitudes']:
        if {s0['de'], s0['para']} == {cT, cV} and s0['estado'] in ('pendiente', 'aceptada'): pide(TERCERO, '/api/comunidad', {'accion': 'terminar', 'id': s0['id']})
    st, r = pide(TERCERO, '/api/comunidad', {'accion': 'solicitar', 'para': cV, 'pid': 'vera-demo', 'msg': ''}); s1 = r.get('solicitud') or {}; ok('quien lo pide entra directo', st == 200 and s1.get('estado') == 'aceptada' and s1.get('abierta'), (st, r))
    ok('y ya lo tiene para crear, en SFW', any(p['cid'] == cV and p['pid'] == 'vera-demo' and not p.get('nsfw') for p in com(TERCERO)['prestados']), com(TERCERO)['prestados'])
    st, m = pide(VERA, f'/api/comunidad/chat?con={cT}'); ok('a la dueña le llega el aviso', any('abierto a colaborar' in z.get('x', '') for z in m.get('mensajes') or []), m)
    if s1.get('id'): pide(VERA, '/api/comunidad', {'accion': 'terminar', 'id': s1['id']})
    ok('la dueña puede retirar el permiso', not any(p['cid'] == cV for p in com(TERCERO)['prestados']))
finally:
    pide(VERA, '/api/comunidad', {'accion': 'abierto', 'pid': 'vera-demo', 'on': False}); pide(VERA, '/api/comunidad', {'accion': 'nsfw', 'id': sid, 'on': False}); pide(LUNA, '/api/comunidad', {'accion': 'nsfw', 'id': sid, 'on': False}); pide(VERA, '/api/comunidad', {'accion': 'plazo', 'id': sid, 'dias': 0})
s = sol(); ok('queda como estaba', s['estado'] == 'aceptada' and not s.get('hasta') and not s.get('nsfw_de') and not s.get('nsfw_para'), s)
print('fallos:', fallos or 'ninguno'); sys.exit(1 if fallos else 0)
