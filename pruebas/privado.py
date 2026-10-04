"""v201: «oculto en la Comunidad» sobrevive a que la página guarde el personaje con una copia vieja (sin la marca). Contra el servidor de pruebas (:8770)."""
import json, urllib.request
B = 'http://127.0.0.1:8770'
LUNA = 'aaaaaaaa-0000-4000-8000-000000000001'; VERA = 'cccccccc-0000-4000-8000-000000000001'

def api(uid, ruta, body=None):
    r = urllib.request.Request(B + ruta, data=json.dumps(body).encode() if body is not None else None, headers={'X-Dev-Uid': uid, 'Content-Type': 'application/json'})
    try: return json.loads(urllib.request.urlopen(r, timeout=20).read())
    except urllib.error.HTTPError as e: return {'http': e.code, 'cuerpo': e.read().decode()[:300]}

def nico(uid):   # cómo ve la cuenta `uid` a Nico Demo en la comunidad
    d = api(uid, '/api/comunidad')
    for c in d['cuentas']:
        for p in c['personajes']:
            if p['pid'] == 'nico-demo': return 'oculto' if p.get('oculto') else 'público'
    return 'no aparece'

L = api(LUNA, '/api/personajes'); P = next(p for p in L['items'] if p.get('id') == 'nico-demo')
vieja = {k: v for k, v in P.items() if k != 'privado'}   # la copia que tendría una página abierta antes de ocultarlo
print('antes        · su dueña lo ve:', nico(LUNA), '· otra cuenta:', nico(VERA))
print('ocultar      ·', api(LUNA, '/api/comunidad', {'accion': 'visible', 'pid': 'nico-demo', 'publico': False}))
print('oculto       · su dueña lo ve:', nico(LUNA), '· otra cuenta:', nico(VERA))
r = api(LUNA, '/api/personaje', {'p': vieja}); print('guardar con la copia vieja ·', 'ok' if r.get('ok') else r, '· privado en lo guardado:', (r.get('p') or {}).get('privado'))
print('tras guardar · su dueña lo ve:', nico(LUNA), '· otra cuenta:', nico(VERA))
print('publicar     ·', api(LUNA, '/api/comunidad', {'accion': 'visible', 'pid': 'nico-demo', 'publico': True}))
r = api(LUNA, '/api/personaje', {'p': vieja}); print('guardar otra vez ·', 'ok' if r.get('ok') else r)
print('final        · su dueña lo ve:', nico(LUNA), '· otra cuenta:', nico(VERA))
