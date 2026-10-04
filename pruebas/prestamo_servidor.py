"""v202 · prueba de las funciones del préstamo dentro del propio servidor (sin red, sin generar): el contador de usos y la puerta de rutas.
Carga el mismo entorno que el servidor de pruebas (lee su fichero de entorno sin enseñarlo) e importa puente.py como módulo."""
import importlib.util, json, os, sys
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
cV = P._cid(VERA); cL = P._cid(LUNA); rel = f'assets/prestamo/{cV}/vera-demo/ficha.jpg'
fallos = []
def ok(n, c, d=''):
    print(('  ✓ ' if c else '  ✕ ') + n + (' · ' + str(d) if d and not c else ''))
    if not c: fallos.append(n)
def usos():
    d = P._com_lee(); x = next(x for x in d['sol'] if x.get('de') == cL and x.get('para') == cV and x.get('estado') == 'aceptada'); return int(x.get('usos') or 0)

print('modo servidor:', P.SERVIDOR, '· versión', P.VERSION)
with P.como(LUNA, 'luna@prueba', False):
    P._ctx.prestamo_ok = False; ok('fuera de una generación la ruta prestada no se resuelve', P.busca(rel) is None)
    P._ctx.prestamo_ok = True; full = P.busca(rel)
    ok('dentro de una generación se resuelve, y cae en la casa de su dueña', bool(full) and (os.sep + VERA + os.sep) in full and os.path.isfile(full), full)
    ok('con propio=True (solo lo mío) no se resuelve', P.busca(rel, True) is None)
    ok('el cuerpo, si no lo tiene, no se inventa', P.busca(f'assets/prestamo/{cV}/vera-demo/cuerpo.jpg') is None or os.path.isfile(P.busca(f'assets/prestamo/{cV}/vera-demo/cuerpo.jpg')))
    for malo in (f'assets/prestamo/{cV}/vera-demo/personaje.json', f'assets/prestamo/{cV}/vera-demo/../vera-demo/ficha.jpg', f'assets/prestamo/{cV}/vera-demo', f'assets/prestamo/{cV}/vera-demo/x/ficha.jpg', f'assets/prestamo/{cV}/.vera/ficha.jpg', f'assets/prestamo/{cL}/luna-demo/ficha.jpg'):
        ok('ruta rara → nada: ' + malo.split('prestamo/')[1][16:], P.busca(malo) is None, P.busca(malo))
    P._ctx.prestamo_ok = False
    a = usos(); P._prest_apunta([(cV, 'vera-demo')]); b = usos(); ok('una imagen lanzada suma 1 al contador de la colaboración', b == a + 1, (a, b))
    P._prest_apunta([(cV, 'no-existe-ese'), ('c00000000000000', 'x')]); c = usos(); ok('la cuenta entera cubre a cualquier personaje suyo; un creador inventado no suma', c == b + 1, (b, c))
    d = P._com_lee(); x = next(x for x in d['sol'] if x.get('de') == cL and x.get('para') == cV and x.get('estado') == 'aceptada'); x['usos'] = a; x.pop('uso_t', None)   # se deja como estaba
    with P._com_l: P._com_guarda(d)
with P.como(TERCERO, 'tercero@prueba', False):
    P._ctx.prestamo_ok = True; ok('otra cuenta, aun dentro de una generación, no la resuelve', P.busca(rel) is None); P._ctx.prestamo_ok = False
    a = usos(); P._prest_apunta([(cV, 'vera-demo')]); ok('ni suma en el contador de otros', usos() == a)
print('fallos:', fallos or 'ninguno')
