"""v216 · escribir a un creador sin haberle pedido antes una colaboración (servidor de pruebas): sí si tiene personajes públicos; no si no tiene ninguno."""
import json, sys, urllib.request, urllib.error
B = 'http://127.0.0.1:8770'; YO = 'dddddddd-0000-4000-8000-000000000199'; LUNA = 'aaaaaaaa-0000-4000-8000-000000000001'
def pide(uid, ruta, body=None):
    r = urllib.request.Request(B + ruta, data=json.dumps(body).encode() if body is not None else None, headers={'X-Dev-Uid': uid, 'Content-Type': 'application/json'})
    try: x = urllib.request.urlopen(r, timeout=30); return x.status, json.loads(x.read())
    except urllib.error.HTTPError as e: return e.code, json.loads(e.read() or b'{}')
fallos = []
def ok(n, c, d=''):
    print(('  ✓ ' if c else '  ✕ ') + n + (' · ' + str(d)[:200] if d and not c else ''))
    if not c: fallos.append(n)
st, d = pide(YO, '/api/comunidad'); cl = next(c['cid'] for c in d['cuentas'] if c.get('alias') == 'Estudio Luna')
st, r = pide(YO, '/api/comunidad', {'accion': 'mensaje', 'con': cl, 'texto': 'Hola, me encanta Luna. ¿Hablamos?'}); ok('escribir sin solicitud previa a un creador con personajes públicos', st == 200 and r.get('ok'), (st, r))
st, m = pide(LUNA, f"/api/comunidad/chat?con={d['yo']}"); ok('le llega', any('me encanta Luna' in x.get('x', '') for x in m.get('mensajes') or []), m)
st, r = pide(YO, '/api/comunidad', {'accion': 'mensaje', 'con': 'demo-nube', 'texto': 'hola'}); ok('a un creador de demo, no', st == 400, (st, r))
print('fallos:', fallos or 'ninguno'); sys.exit(1 if fallos else 0)
