"""v213 · NSFW solo restringido con Aria (servidor de pruebas, sin gastar: la cuenta de prueba no tiene clave, así que lo que pasa el filtro falla después por la clave)."""
import json, sys, urllib.request, urllib.error
B = 'http://127.0.0.1:8770'; MI = 'dddddddd-0000-4000-8000-000000000199'; EQ = 'aaaaaaaa-0000-4000-8000-000000000001'
fallos = []
def pide(uid, body, h0=None, ruta='/api/generar'):
    h = {'X-Dev-Uid': uid, 'Content-Type': 'application/json', 'X-Dev-Casa': '0'}; h.update(h0 or {})
    r = urllib.request.Request(B + ruta, data=json.dumps(body).encode(), headers=h)
    try: x = urllib.request.urlopen(r, timeout=60); return x.status, json.loads(x.read())
    except urllib.error.HTTPError as e: return e.code, json.loads(e.read() or b'{}')
def ok(n, c, d=''):
    print(('  ✓ ' if c else '  ✕ ') + n + (' · ' + str(d)[:200] if d and not c else ''))
    if not c: fallos.append(n)
suyo = {'model': 'seedflash', 'prompt': 'a photo', 'meta': {'nsfw': True, 'chars': ['luna-demo']}, 'images': [{'path': 'assets/personajes/luna-demo/ficha360.jpg'}]}
con_aria = {'model': 'seedflash', 'prompt': 'a photo', 'meta': {'nsfw': True, 'chars': ['aria']}, 'images': [{'path': 'assets/perfil/ficha360.jpg'}]}
aria_sin_meta = {'model': 'seedflash', 'prompt': 'a photo', 'nsfw': True, 'images': [{'path': 'assets/perfil/ficha360.jpg'}]}
for quien, uid, h in (('miembro', MI, {}), ('equipo (Laura)', EQ, {'X-Dev-Interno': '1'})):
    st, r = pide(uid, suyo, h); ok(f'{quien}: NSFW con SU personaje pasa el filtro', 'NSFW' not in str(r.get('error')), (st, r))
    st, r = pide(uid, con_aria, h); ok(f'{quien}: NSFW con Aria, rechazado', st == 400 and 'Aria' in str(r.get('error')), (st, r))
    st, r = pide(uid, aria_sin_meta, h); ok(f'{quien}: aunque no lo diga la página (va su ficha)', st == 400 and 'Aria' in str(r.get('error')), (st, r))
st, r = pide(MI, {'mode': 'i2v', 'prompt': 'a video', 'nsfw': True, 'image': {'path': 'assets/perfil/ficha360.jpg'}}, ruta='/api/video'); ok('vídeo con Aria y NSFW, rechazado', st == 400 and 'Aria' in str(r.get('error')), (st, r))
print('fallos:', fallos or 'ninguno'); sys.exit(1 if fallos else 0)
