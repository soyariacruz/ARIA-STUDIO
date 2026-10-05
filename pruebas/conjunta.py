"""v223 · creación conjunta SIN copias (dentro del propio servidor, sin red y sin generar).
Luna crea con «Vera Demo» (personaje de Vera): la imagen se queda en la cuenta de Luna, dentro de su carpeta «🤝 Vera», y Vera la VE por la puerta de carpetas compartidas.
Vera puede importarla (copia suya, con su prompt). Si Luna la borra, Vera deja de verla; lo importado se queda.
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
LUNA = 'aaaaaaaa-0000-4000-8000-000000000001'; VERA = 'cccccccc-0000-4000-8000-000000000001'; TERCERO = 'dddddddd-0000-4000-8000-000000000199'
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
ll = os.path.join(U, LUNA, 'assets', 'live'); lv = os.path.join(U, VERA, 'assets', 'live'); os.makedirs(lv, exist_ok=True); antes_v = set(os.listdir(lv))
orig = next(f for f in sorted(os.listdir(ll)) if f.lower().endswith(('.jpg', '.png')) and '_' in f)
mio = 'prueba-conjunta_qwen-c0c0c0c0' + os.path.splitext(orig)[1]; rel = 'assets/live/' + mio
shutil.copyfile(os.path.join(ll, orig), os.path.join(ll, mio))
json.dump({'file': rel, 'prompt': 'PROMPT DE LUNA', 'canvasRef': 'assets/refs/x.jpg', 'compIds': {'vestidor': 'v1'}, 'model': 'Qwen', 'usd': 0.03, 'width': 10, 'height': 20}, open(os.path.join(ll, mio) + '.json', 'w'))
try:
    with P.como(LUNA, 'luna@prueba', False):
        P._conjunta({'model': 'qwen', 'prest': [[cV, 'vera-demo'], [cV, 'vera-demo'], ['c00000000000000', 'x'], [cL, 'luna-demo']]}, rel, RID)
    ok('no se copia nada a la cuenta de la dueña del personaje', set(os.listdir(lv)) == antes_v, set(os.listdir(lv)) - antes_v)
    mm = json.load(open(os.path.join(ll, mio) + '.json'))
    ok('la mía queda marcada como conjunta y conserva lo suyo', (mm.get('colab') or {}).get('con') == cV and mm['colab'].get('mia') is True and mm.get('prompt') == 'PROMPT DE LUNA', mm)
    cl = next((c for c in (carp(LUNA) or {}).get('carpetas', []) if c.get('colab') == cV), None)
    ok('entra en mi carpeta «🤝», compartida con la dueña', cl and rel in cl['items'] and cV in (cl.get('comp') or []) and cl['nombre'].startswith('🤝'), cl)
    kid = cl['id'] if cl else ''; ruta = f'assets/compartida/{cL}/{kid}/live/{mio}'
    with P.como(VERA, 'vera@prueba', False):
        ok('la dueña la ve por la puerta de carpetas compartidas', P.busca(ruta) == os.path.join(ll, mio), P.busca(ruta))
        L = P._comp_lista(P._com_lee(), cV); k = next((x for x in L if x['id'] == kid), None); ok('y le sale en su lista, como creada con sus personajes', k and k.get('conjunta') and k['n'] >= 1, L)
        n = P._comp_importa({'cid': cL, 'id': kid, 'files': [ruta]}); nuevos = sorted(set(os.listdir(lv)) - antes_v)
        ok('importar: una copia en SUS creaciones', n == 1 and any(f.startswith('importada_colab-') and not f.endswith('.json') for f in nuevos), (n, nuevos))
        mi = next((json.load(open(os.path.join(lv, f))) for f in nuevos if f.endswith('.json')), {})
        ok('la copia lleva el prompt y de quién viene, pero no sus referencias', mi.get('prompt') == 'PROMPT DE LUNA' and (mi.get('importada') or {}).get('de') == cL and mi.get('usd') == 0 and not any(x in mi for x in ('canvasRef', 'compIds')), mi)
        ok('importar dos veces no duplica', P._comp_importa({'cid': cL, 'id': kid, 'files': [ruta]}) == 0)
    with P.como(TERCERO, 't@prueba', False): ok('una tercera cuenta no la ve', P.busca(ruta) is None)
    os.remove(os.path.join(ll, mio))
    with P.como(VERA, 'vera@prueba', False): ok('si la creadora la borra, la dueña deja de verla', P.busca(ruta) is None)
    ok('lo que importó se queda', any(f.startswith('importada_colab-') for f in os.listdir(lv)))
finally:
    for fp in (os.path.join(ll, mio), os.path.join(ll, mio) + '.json'):
        if os.path.exists(fp): os.remove(fp)
    for f in set(os.listdir(lv)) - antes_v: os.remove(os.path.join(lv, f))
    for u in (LUNA, VERA):
        fp = os.path.join(U, u, 'carpetas.json')
        if antes[u] is None:
            if os.path.exists(fp): os.remove(fp)
        else: json.dump(antes[u], open(fp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('fallos:', fallos or 'ninguno'); sys.exit(1 if fallos else 0)
