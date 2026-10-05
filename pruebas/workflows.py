"""v209 · Workflows (Duelos) en la web, contra el servidor de pruebas (:8770). No genera ni gasta: en pruebas la cuenta de Aria no tiene claves, así que
el trabajador se para con «Falta la clave…» (eso también se comprueba). El montaje del carrusel sí se prueba de verdad, con la copia de un duelo real
en DATOS/liga/prueba-flux3-vs-gpt (cópiala antes desde el NAS sin crudas ni carrusel)."""
import json, sys, time, urllib.request, urllib.error
B = 'http://127.0.0.1:8770'
EQUIPO = 'aaaaaaaa-0000-4000-8000-000000000001'; MIEMBRO = 'dddddddd-0000-4000-8000-000000000199'
fallos = []

def pide(uid, ruta, body=None, interno=False):
    h = {'X-Dev-Uid': uid, 'Content-Type': 'application/json'}
    if interno: h['X-Dev-Interno'] = '1'
    r = urllib.request.Request(B + ruta, data=json.dumps(body).encode() if body is not None else None, headers=h)
    try:
        x = urllib.request.urlopen(r, timeout=900); return x.status, x.read(), x.headers.get('Content-Type', '')
    except urllib.error.HTTPError as e: return e.code, e.read(), ''

def js(*a, **k):
    st, b, _ = pide(*a, **k)
    try: return st, json.loads(b)
    except Exception: return st, {'_crudo': b[:200]}

def ok(n, c, d=''):
    print(('  ✓ ' if c else '  ✕ ') + n + (' · ' + str(d)[:240] if d and not c else ''))
    if not c: fallos.append(n)

print('1) quién entra')
st, r = js(MIEMBRO, '/api/liga'); ok('un miembro no ve los Workflows', st == 403, (st, r))
st, r = js(MIEMBRO, '/api/liga/nuevo', {'a': {'nombre': 'X', 'modelo': 'nano_banana_pro'}, 'b': {'nombre': 'Y', 'modelo': 'gpt_image_2_5'}}); ok('ni crea duelos', st == 403, st)
st, b, ct = pide(MIEMBRO, '/assets/liga/prueba-flux3-vs-gpt/galeria/mini/p01.jpg'); ok('ni ve sus imágenes', st == 404, st)
st, r = js(EQUIPO, '/api/liga', interno=True); ids = [x['duelo']['id'] for x in r.get('duelos', [])]; ok('el equipo ve la lista de duelos', st == 200 and 'prueba-flux3-vs-gpt' in ids, (st, ids))
st, b, ct = pide(EQUIPO, '/assets/liga/prueba-flux3-vs-gpt/galeria/mini/p01.jpg', interno=True); ok('y sus imágenes', st == 200 and ct.startswith('image/'), (st, ct))
st, b, ct = pide(EQUIPO, '/assets/liga/prueba-flux3-vs-gpt/../../usuarios/x', interno=True); ok('nada fuera de la carpeta de los duelos', st == 404, st)
print('2) guardar y montar')
M = [x for x in r['duelos'] if x['duelo']['id'] == 'prueba-flux3-vs-gpt'][0]['max']
st, g = js(EQUIPO, '/api/liga', {'id': 'prueba-flux3-vs-gpt', 'max': M}, interno=True); ok('guardar lo elegido (la ruta que se perdió en la v136)', st == 200 and g.get('ok'), (st, g))
t0 = time.time(); st, m = js(EQUIPO, '/api/liga/montar', {'id': 'prueba-flux3-vs-gpt'}, interno=True); ok(f'montar el carrusel en el servidor ({time.time() - t0:.0f} s)', st == 200 and m.get('ok'), (st, m))
st, r = js(EQUIPO, '/api/liga', interno=True); Dd = [x for x in r['duelos'] if x['duelo']['id'] == 'prueba-flux3-vs-gpt'][0]['duelo']; ok('el carrusel queda apuntado', len(Dd.get('carrusel') or []) >= 10, len(Dd.get('carrusel') or []))
st, b, ct = pide(EQUIPO, '/api/liga/zip?id=prueba-flux3-vs-gpt', interno=True); ok('se descarga en zip', st == 200 and len(b) > 100000, (st, len(b)))
print('3) duelo nuevo: el trabajador se pone en marcha')
st, r = js(EQUIPO, '/api/liga/nuevo', {'a': {'nombre': 'FLUX 3', 'modelo': 'flux_3_image'}, 'b': {'nombre': 'NANO BANANA PRO', 'modelo': 'nano_banana_pro'}}, interno=True); ok('en la web no deja un modelo que no se puede generar', st == 400, (st, r))
st, r = js(EQUIPO, '/api/liga/nuevo', {'a': {'nombre': 'SEEDREAM 5.0 FLASH', 'modelo': 'seedream_5_0_flash'}, 'b': {'nombre': 'NANO BANANA PRO', 'modelo': 'nano_banana_pro'}, 'nota': 'prueba'}, interno=True); did = r.get('id'); ok('crea el duelo', st == 200 and did, (st, r))
aviso = ''
for _ in range(10):
    time.sleep(2); st, r = js(EQUIPO, '/api/liga', interno=True); Dn = [x for x in r['duelos'] if x['duelo']['id'] == did][0]['duelo']; aviso = Dn.get('aviso', '')
    if 'Falta la clave' in aviso: break
ok('el trabajador lo coge y, sin claves en pruebas, lo dice claro', 'Falta la clave de Claude' in aviso, aviso)
print('fallos:', fallos or 'ninguno'); print('duelo de prueba creado:', did); sys.exit(1 if fallos else 0)
