"""v210 · cada miembro personaliza SU Aria (servidor de pruebas, sin generar): un complemento con foto y quitar una ficha creada de las de todos.
Lo ve solo ese miembro; otro miembro y el equipo siguen viendo la Aria de todos. Al final se deja como estaba."""
import base64, io, json, sys, urllib.request, urllib.error
B = 'http://127.0.0.1:8770'
YO = 'dddddddd-0000-4000-8000-000000000199'; OTRO = 'aaaaaaaa-0000-4000-8000-000000000001'; EQUIPO = 'cccccccc-0000-4000-8000-000000000001'
fallos = []
def pide(uid, ruta, body=None, interno=False):
    h = {'X-Dev-Uid': uid, 'Content-Type': 'application/json'}
    if interno: h['X-Dev-Interno'] = '1'
    r = urllib.request.Request(B + ruta, data=json.dumps(body).encode() if body is not None else None, headers=h)
    try:
        x = urllib.request.urlopen(r, timeout=60); return x.status, x.read()
    except urllib.error.HTTPError as e: return e.code, e.read()
def perfil(uid, interno=False):
    st, b = pide(uid, '/api/catalogo', None, interno); t = b.decode('utf-8'); return json.loads(t[t.index('{'):t.rindex('}') + 1])['perfil']
def ok(n, c, d=''):
    print(('  ✓ ' if c else '  ✕ ') + n + (' · ' + str(d)[:200] if d and not c else ''))
    if not c: fallos.append(n)
from PIL import Image
buf = io.BytesIO(); Image.new('RGB', (64, 64), (40, 120, 230)).save(buf, 'JPEG'); du = 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode()
antes = perfil(YO).get('complementos') or []; fichas0 = perfil(YO).get('fichas') or []
st, b = pide(YO, '/api/complementos', {'owner': 'aria', 'list': [{'id': 'mi-collar', 'nombre': 'Mi collar', 'tipo': 'collar', 'regla': 'si sale', 'desc': 'collar de prueba'}] + antes, 'files': {'mi-collar': du}})
ok('un miembro añade un complemento a SU Aria', st == 200, (st, b[:200]))
mio = next((c for c in perfil(YO).get('complementos') or [] if c.get('id') == 'mi-collar'), None); ok('lo ve él, el primero de la lista', bool(mio) and (perfil(YO).get('complementos') or [{}])[0].get('id') == 'mi-collar', mio)
st, b = pide(YO, '/' + mio['img'].split('?')[0]) if mio else (0, b''); ok('y su foto', st == 200 and len(b) > 300, st)
ok('otro miembro no lo ve', not any(c.get('id') == 'mi-collar' for c in perfil(OTRO).get('complementos') or []))
ok('el equipo (la Aria de todos) tampoco', not any(c.get('id') == 'mi-collar' for c in perfil(EQUIPO, True).get('complementos') or []))
st, b = pide(OTRO, '/' + mio['img'].split('?')[0]) if mio else (0, b''); ok('ni puede abrir su foto', st != 200 or len(b) < 300, st)
if fichas0:
    fid = fichas0[0]['id']; st, b = pide(YO, '/api/fichas_outfit', {'action': 'delete', 'id': fid}); ok('quitar una ficha creada de las de todos (solo para él)', st == 200, (st, b[:200]))
    ok('a él ya no le sale', not any(x.get('id') == fid for x in perfil(YO).get('fichas') or []))
    ok('a los demás sí', any(x.get('id') == fid for x in perfil(OTRO).get('fichas') or []))
st, b = pide(YO, '/api/perfil', {'action': 'set', 'set': {'bio': 'hackeo'}}); ok('lo esencial de Aria sigue fijo (perfil)', st == 403, st)
st, b = pide(YO, '/api/ficha_combo', {'action': 'principal', 'id': 'x'}); ok('y su ficha principal', st == 403, st)
# dejarlo como estaba: sin capa «aria» en esa cuenta
st, b = pide(YO, '/api/complementos', {'owner': 'aria', 'list': antes});
import os
cp = os.path.expanduser(f'~/.aria-studio/servidor-datos/usuarios/{YO}/capa.json')
try:
    c = json.load(open(cp, encoding='utf-8')); c.pop('aria', None); json.dump(c, open(cp, 'w', encoding='utf-8'), ensure_ascii=False)
except FileNotFoundError: pass
ok('limpio al terminar', not any(c.get('id') == 'mi-collar' for c in perfil(YO).get('complementos') or []) and len(perfil(YO).get('fichas') or []) == len(fichas0))
print('fallos:', fallos or 'ninguno'); sys.exit(1 if fallos else 0)
