"""v211-v212 · sin gastar: (1) el catálogo de generadores de los duelos, con una copia del catálogo real de WaveSpeed (solo leído), y cómo se arma la petición de cada uno;
(2) contra el servidor de pruebas: NSFW solo en las dos cuentas permitidas y «ver como miembro» quita los permisos del equipo."""
import importlib.util, json, os, sys, urllib.request, urllib.error
CAT = sys.argv[1] if len(sys.argv) > 1 else ''
fallos = []
def ok(n, c, d=''):
    print(('  ✓ ' if c else '  ✕ ') + n + (' · ' + str(d)[:240] if d and not c else ''))
    if not c: fallos.append(n)
if CAT:
    ENV = os.path.expanduser('~/.aria-studio/servidor-dev.env')
    for ln in open(ENV, encoding='utf-8'):
        ln = ln.strip()
        if ln and not ln.startswith('#') and '=' in ln: k, v = ln.split('=', 1); os.environ[k.replace('export ', '').strip()] = os.path.expandvars(v.strip().strip('"').strip("'"))
    sys.argv = ['puente.py', '8797']; os.chdir('/Users/maxromanenko/Desktop/XXX')
    spec = importlib.util.spec_from_file_location('puente_cat', '/Volumes/home/🗄 Work/CLAUDE/Aria Mirror/puente.py'); P = importlib.util.module_from_spec(spec); spec.loader.exec_module(P)
    datos = json.load(open(CAT)); P.load_ws = lambda: 'x'; P.ws = lambda m, path, body=None, **k: datos; P._hf_listo = lambda: True
    print('1) catálogo')
    L = P._liga_catalogo(True); ids = {x['id'] for x in L}
    ok(f'{len(L)} generadores', len(L) > 60, len(L))
    for want in ('black-forest-labs/flux-3/image-edit', 'google/nano-banana-pro/edit', 'openai/gpt-image-2.5-sunburst/edit', 'bytedance/seedream-v5.0-pro/edit', 'kwaivgi/kling-image-o3/edit', 'hf:mstudio'):
        ok('está ' + want, want in ids)
    for nowant in ('bria/virtual-try-on', 'wavespeed-ai/flux-2-dev/edit-lora', 'bytedance/seedream-v4.5/edit-sequential'):
        ok('no está ' + nowant, nowant not in ids)
    malos = []
    for c in L:
        if c['prov'] != 'ws': continue
        try:
            b = P._liga_payload(c, 'a prompt', 'https://x/y.jpg'); p = c['p']
            if 'aspect_ratio' in p and '9:16' in (p['aspect_ratio'].get('enum') or ['9:16']) and b.get('aspect_ratio') != '9:16': malos.append(c['id'] + ' sin 9:16')
            if not (b.get('images') or b.get('image')): malos.append(c['id'] + ' sin imagen')
            for k, v in b.items():
                e = (p.get(k) or {}).get('enum')
                if e and v not in e: malos.append(f"{c['id']} {k}={v} fuera de {e}")
        except Exception as e: malos.append(c['id'] + ' ✕ ' + str(e))
    ok('todas las peticiones bien formadas', not malos, malos[:6])
    fx = next(c for c in L if c['id'] == 'black-forest-labs/flux-3/image-edit'); print('     FLUX 3 →', json.dumps(P._liga_payload(fx, 'a prompt', 'https://x/y.jpg'))[:200])
else:
    B = 'http://127.0.0.1:8770'
    def pide(uid, ruta, body=None, h0=None):
        h = {'X-Dev-Uid': uid, 'Content-Type': 'application/json'}; h.update(h0 or {})
        r = urllib.request.Request(B + ruta, data=json.dumps(body).encode() if body is not None else None, headers=h)
        try: x = urllib.request.urlopen(r, timeout=60); return x.status, json.loads(x.read())
        except urllib.error.HTTPError as e: return e.code, json.loads(e.read() or b'{}')
    EQ = 'aaaaaaaa-0000-4000-8000-000000000001'; MI = 'dddddddd-0000-4000-8000-000000000199'
    print('2) NSFW y ver como miembro')
    for quien, uid, h in (('un miembro', MI, {}), ('el equipo (Laura)', EQ, {'X-Dev-Interno': '1'})):
        st, r = pide(uid, '/api/generar', {'model': 'seedflash', 'prompt': 'a photo', 'meta': {'nsfw': True}, 'images': [{'path': 'assets/perfil/ficha360.jpg'}]}, h); ok(f'{quien}: NSFW rechazado', st == 400 and 'NSFW' in str(r.get('error')), (st, r))
        st, r = pide(uid, '/api/generar', {'model': 'seedflash', 'prompt': 'she is naked on the beach', 'images': [{'path': 'assets/perfil/ficha360.jpg'}]}, h); ok(f'{quien}: también por el texto del prompt', st == 400 and 'NSFW' in str(r.get('error')), (st, r))
    st, r = pide(EQ, '/api/ping', None, {'X-Dev-Interno': '1'}); ok('ping del equipo: nsfw no', r.get('nsfw') is False and r.get('interno') is True, r)
    st, r = pide(EQ, '/api/aria/estado', None, {'X-Dev-Interno': '1'}); ok('el equipo edita a Aria', r.get('editor') is True, r)
    st, r = pide(EQ, '/api/aria/estado', None, {'X-Dev-Interno': '1', 'X-Ver-Como': 'miembro'}); ok('«ver como miembro»: ya no edita a Aria', r.get('editor') is False, r)
    st, r = pide(EQ, '/api/ping', None, {'X-Dev-Interno': '1', 'X-Ver-Como': 'miembro'}); ok('«ver como miembro»: no es interno', not r.get('interno'), r)
    st, r = pide(EQ, '/api/liga', None, {'X-Dev-Interno': '1', 'X-Ver-Como': 'miembro'}); ok('«ver como miembro»: sin Workflows', st == 403, st)
print('fallos:', fallos or 'ninguno'); sys.exit(1 if fallos else 0)
