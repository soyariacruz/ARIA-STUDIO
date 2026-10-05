"""v205 · Aria de equipo con ficheros (servidor de pruebas, sin generar): Laura añade un complemento con foto a Aria;
Max lo ve y puede abrir la foto; un miembro no; publicar (ensayo) la sube con nombre nuevo. Al final, la lista de complementos vuelve a la de antes."""
import base64, io, json, os, sys, urllib.request, urllib.error
B = 'http://127.0.0.1:8770'
LAURA = 'aaaaaaaa-0000-4000-8000-000000000001'; MAX = 'cccccccc-0000-4000-8000-000000000001'; MIEMBRO = 'dddddddd-0000-4000-8000-000000000199'
ENSAYO = os.path.expanduser('~/.aria-studio/servidor-datos/aria_ensayo')
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
buf = io.BytesIO(); Image.new('RGB', (64, 64), (230, 40, 120)).save(buf, 'JPEG'); du = 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode()
antes = perfil(LAURA, True).get('complementos') or []
nuevo = {'id': 'prueba-equipo', 'nombre': 'Prueba equipo', 'tipo': 'accesorio', 'regla': 'si sale', 'desc': 'complemento de prueba'}
st, b = pide(LAURA, '/api/complementos', {'owner': 'aria', 'list': antes + [nuevo], 'files': {'prueba-equipo': du}}, True); ok('Laura añade un complemento con foto a Aria', st == 200, (st, b[:200]))
c = next((x for x in perfil(MAX, True).get('complementos') or [] if x.get('id') == 'prueba-equipo'), None); ok('Max lo ve', bool(c and c.get('img')), c)
img = (c or {}).get('img', '').split('?')[0]
st, b = pide(MAX, '/' + img, None, True); ok('Max abre la foto', st == 200 and len(b) > 300, (st, len(b)))
st, b = pide(MIEMBRO, '/' + img); ok('un miembro no la abre (no está publicada)', st != 200 or len(b) < 300, st)
st, b = pide(MAX, '/api/aria/publicar', {}, True); r = json.loads(b); ok('publicar (ensayo) sube la foto con nombre nuevo', st == 200 and r.get('ficheros', 0) >= 1, r)
pub = json.load(open(os.path.join(ENSAYO, 'catalogo.json'), encoding='utf-8'))['perfil']
cp = next((x for x in pub.get('complementos') or [] if x.get('id') == 'prueba-equipo'), {}); ok('en lo publicado la foto va a assets/perfil/web/', str(cp.get('img', '')).startswith('assets/perfil/web/'), cp.get('img'))
ok('y el fichero está', os.path.isfile(os.path.join(ENSAYO, *str(cp.get('img', 'x')).split('/'))))
st, b = pide(LAURA, '/api/complementos', {'owner': 'aria', 'list': antes}, True); ok('lista de complementos de antes, restaurada', st == 200 and not any(x.get('id') == 'prueba-equipo' for x in perfil(MAX, True).get('complementos') or []), b[:200])
print('fallos:', fallos or 'ninguno'); sys.exit(1 if fallos else 0)
