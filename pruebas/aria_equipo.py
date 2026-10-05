"""v205 · Aria de equipo, contra el servidor de pruebas (:8770). No genera ni gasta nada; «Publicar» en pruebas es un ensayo (DATOS/aria_ensayo).
Cuentas: dos del equipo (cabecera X-Dev-Interno: 1), un miembro normal y la que hace de Max para publicar (dev-cccccccc@dev.local, puesta en ARIA_PUBLICAN del servidor de pruebas).
Al terminar deja el perfil de la Aria de equipo como estaba."""
import json, os, sys, urllib.request, urllib.error
B = 'http://127.0.0.1:8770'
LAURA = 'aaaaaaaa-0000-4000-8000-000000000001'; MAX = 'cccccccc-0000-4000-8000-000000000001'; MIEMBRO = 'dddddddd-0000-4000-8000-000000000199'
fallos = []

def pide(uid, ruta, body=None, interno=False):
    h = {'X-Dev-Uid': uid, 'Content-Type': 'application/json'}
    if interno: h['X-Dev-Interno'] = '1'
    r = urllib.request.Request(B + ruta, data=json.dumps(body).encode() if body is not None else None, headers=h)
    try:
        x = urllib.request.urlopen(r, timeout=60); b = x.read(); return x.status, b
    except urllib.error.HTTPError as e: return e.code, e.read()

def js(uid, ruta, body=None, interno=False):
    st, b = pide(uid, ruta, body, interno)
    try: return st, json.loads(b)
    except Exception: return st, {'_crudo': b[:120]}

def bio(uid, interno=False):
    st, b = pide(uid, '/api/catalogo', None, interno)
    t = b.decode('utf-8'); C = json.loads(t[t.index('{'):t.rindex('}') + 1]); return C['perfil'].get('bio')

def ok(n, c, d=''):
    print(('  ✓ ' if c else '  ✕ ') + n + (' · ' + str(d)[:200] if d and not c else ''))
    if not c: fallos.append(n)

original = bio(LAURA, True); nueva = 'Bio de prueba de la Aria de equipo'
print('1) editar')
st, r = js(LAURA, '/api/perfil', {'action': 'set', 'set': {'bio': nueva}}, True); ok('Laura (equipo) cambia la bio de Aria', st == 200, (st, r))
ok('Max (equipo) ve el cambio de Laura', bio(MAX, True) == nueva, bio(MAX, True))
ok('un miembro sigue viendo la Aria publicada', bio(MIEMBRO) != nueva)
st, r = js(MIEMBRO, '/api/perfil', {'action': 'set', 'set': {'bio': 'hackeo'}}); ok('un miembro no puede cambiar a Aria', st == 403, (st, r))
print('2) estado y publicar')
st, e = js(LAURA, '/api/aria/estado', None, True); ok('Laura ve «cambios sin publicar» y no puede publicar', e.get('editor') and e.get('pendiente') and not e.get('publica'), e)
st, r = js(LAURA, '/api/aria/publicar', {}, True); ok('Laura no puede publicar', st == 403, (st, r))
st, r = js(MIEMBRO, '/api/aria/estado'); ok('el miembro no es editor', r.get('editor') is False, r)
st, r = js(MAX, '/api/aria/publicar', {}, True); ok('Max publica (ensayo en pruebas)', st == 200 and r.get('ok') and r.get('ensayo'), (st, r))
st, e = js(MAX, '/api/aria/estado', None, True); ok('después: «publicada», sin cambios pendientes', e.get('pendiente') is False and e.get('publicado'), e)
print('3) volver a dejarlo como estaba')
st, r = js(LAURA, '/api/perfil', {'action': 'set', 'set': {'bio': original}}, True); ok('bio original restaurada', st == 200 and bio(MAX, True) == original)
print('fallos:', fallos or 'ninguno'); sys.exit(1 if fallos else 0)
