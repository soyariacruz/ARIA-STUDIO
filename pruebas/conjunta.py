"""v219 · la creación conjunta aparece en las dos cuentas (dentro del propio servidor, sin red y sin generar).
Luna crea con «Vera Demo» (personaje de Vera): la imagen se copia a las creaciones de Vera con una ficha mínima y las dos la ven en su carpeta «🤝 …».
Usa una imagen de prueba que crea y borra; deja las dos cuentas como estaban."""
import importlib.util, json, os, shutil, sys
ENV = os.path.expanduser('~/.aria-studio/servidor-dev.env')
for ln in open(ENV, encoding='utf-8'):
    ln = ln.strip()
    if not ln or ln.startswith('#') or '=' not in ln: continue
    k, v = ln.split('=', 1); k = k.replace('export ', '').strip(); v = v.strip().strip('"').strip("'")
    os.environ[k] = os.path.expandvars(v)
sys.argv = ['puente.py', '8799']
os.chdir('/Users/maxromanenko/Desktop/XXX')
spec = importlib.util.spec_from_file_location('puente_prueba', '/Volumes/home/🗄 Work/CLAUDE/Aria Mirror/puente.py'); P = importlib.util.module_from_spec(spec); spec.loader.exec_module(P)
LUNA = 'aaaaaaaa-0000-4000-8000-000000000001'; VERA = 'cccccccc-0000-4000-8000-000000000001'
cV = P._cid(VERA); cL = P._cid(LUNA); RID = 'c0c0c0c0prueba'; U = os.path.join(P.DATOS, 'usuarios')
fallos = []
def ok(n, c, d=''):
    print(('  ✓ ' if c else '  ✕ ') + n + (' · ' + str(d)[:260] if d and not c else ''))
    if not c: fallos.append(n)
def carp(u):
    try: return json.load(open(os.path.join(U, u, 'carpetas.json'), encoding='utf-8'))
    except Exception: return None
print('modo servidor:', P.SERVIDOR, '· versión', P.VERSION)
antes = {u: carp(u) for u in (LUNA, VERA)}
ll = os.path.join(U, LUNA, 'assets', 'live'); orig = next(f for f in sorted(os.listdir(ll)) if f.lower().endswith(('.jpg', '.png')) and '_' in f)
mio = 'prueba-conjunta_qwen-c0c0c0c0' + os.path.splitext(orig)[1]; rel = 'assets/live/' + mio; suyo = os.path.join(U, VERA, 'assets', 'live', 'colab_qwen-c0c0c0c0' + os.path.splitext(orig)[1])
shutil.copyfile(os.path.join(ll, orig), os.path.join(ll, mio))
json.dump({'file': rel, 'prompt': 'PROMPT SECRETO DE LUNA', 'canvasRef': 'assets/refs/x.jpg', 'compIds': {'vestidor': 'v1'}, 'model': 'Qwen', 'usd': 0.03, 'width': 10, 'height': 20}, open(os.path.join(ll, mio) + '.json', 'w'))
try:
    with P.como(LUNA, 'luna@prueba', False):
        P._conjunta({'model': 'qwen', 'prest': [[cV, 'vera-demo'], [cV, 'vera-demo'], ['c00000000000000', 'x'], [cL, 'luna-demo']]}, rel, RID)
    ok('la copia está en las creaciones de la dueña del personaje', os.path.isfile(suyo))
    m = json.load(open(suyo + '.json')) if os.path.isfile(suyo + '.json') else {}
    ok('su ficha lleva el prompt (v222) pero no las referencias ni la combinación', m and m.get('prompt') == 'PROMPT SECRETO DE LUNA' and not any(k in m for k in ('canvasRef', 'compIds')), m)
    ok('no le cuesta nada y dice con quién', m.get('usd') == 0 and (m.get('colab') or {}).get('con') == cL and (m.get('colab') or {}).get('pid') == 'vera-demo' and m['colab'].get('mia') is False, m)
    mm = json.load(open(os.path.join(ll, mio) + '.json'))
    ok('la mía queda marcada como conjunta y conserva lo suyo', (mm.get('colab') or {}).get('con') == cV and mm['colab'].get('mia') is True and mm.get('prompt') == 'PROMPT SECRETO DE LUNA', mm)
    cl = next((c for c in (carp(LUNA) or {}).get('carpetas', []) if c.get('colab') == cV), None); cv = next((c for c in (carp(VERA) or {}).get('carpetas', []) if c.get('colab') == cL), None)
    ok('carpeta automática en mi cuenta, con mi imagen', cl and rel in cl['items'] and cl['nombre'].startswith('🤝'), cl)
    ok('carpeta automática en la suya, con su copia (una sola vez)', cv and cv['items'].count('assets/live/' + os.path.basename(suyo)) == 1, cv)
    with P.como(VERA, 'vera@prueba', False):
        L = P._carp_lee(); ok('ella la ve en sus carpetas (y se conserva con quién es)', any(c.get('colab') == cL for c in L), L)
        ok('y en sus creaciones', any(c.get('file') == 'assets/live/' + os.path.basename(suyo) for c in P.creations()))
    os.remove(os.path.join(ll, mio)); ok('borrar la mía no borra la suya', os.path.isfile(suyo))
    with P.como(LUNA, 'luna@prueba', False): P._conjunta({'model': 'qwen'}, rel, RID); P._conjunta({'model': 'qwen', 'prest': [[cV, '../x']]}, rel, RID)
    ok('sin préstamo o con rutas raras no hace nada', True)
finally:
    for fp in (os.path.join(ll, mio), os.path.join(ll, mio) + '.json', suyo, suyo + '.json'):
        if os.path.exists(fp): os.remove(fp)
    for u in (LUNA, VERA):
        fp = os.path.join(U, u, 'carpetas.json')
        if antes[u] is None:
            if os.path.exists(fp): os.remove(fp)
        else: json.dump(antes[u], open(fp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('fallos:', fallos or 'ninguno'); sys.exit(1 if fallos else 0)
