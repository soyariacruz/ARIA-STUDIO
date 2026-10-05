"""v209 · simulacro del trabajador de los Workflows, dentro del servidor y sin gastar: Claude y WaveSpeed se sustituyen por respuestas falsas.
Recorre el duelo entero: mundos → elegir → prompts → galería → generar el duelo → regenerar con nota → más imágenes → tu historia → montar.
Usa una carpeta de duelos temporal; no toca la del servidor de pruebas."""
import importlib.util, io, json, os, sys, tempfile, time
ENV = os.path.expanduser('~/.aria-studio/servidor-dev.env')
for ln in open(ENV, encoding='utf-8'):
    ln = ln.strip()
    if ln and not ln.startswith('#') and '=' in ln: k, v = ln.split('=', 1); os.environ[k.replace('export ', '').strip()] = os.path.expandvars(v.strip().strip('"').strip("'"))
sys.argv = ['puente.py', '8798']; os.chdir('/Users/maxromanenko/Desktop/XXX')
spec = importlib.util.spec_from_file_location('puente_sim', '/Volumes/home/🗄 Work/CLAUDE/Aria Mirror/puente.py'); P = importlib.util.module_from_spec(spec); spec.loader.exec_module(P)
from PIL import Image
tmp = tempfile.mkdtemp(prefix='liga_sim_'); P.LIGA_WEB = tmp
fallos = []
def ok(n, c, d=''):
    print(('  ✓ ' if c else '  ✕ ') + n + (' · ' + str(d)[:240] if d and not c else ''))
    if not c: fallos.append(n)
# --- falsos
llamadas = {'claude': 0, 'gen': 0}
def claude_falso(sistema, texto, max_tokens=16000):
    llamadas['claude'] += 1
    if '"mundos"' in texto:
        n = 1 if 'SOLO un mundo' in texto else 3
        return {'mundos': [{'id': f'mundo-{llamadas["claude"]}-{i}', 'emoji': '🌍', 'titulo': f'Mundo {i}', 'desc': 'desc', 'prompt_img': 'the woman in image 1 ...', 'secuencias': [{'id': f'm{i}-{k}', 'tono': '😂 Graciosa', 'titulo': f'H{k}', 'resumen': 'r'} for k in range(1, 7)]} for i in range(n)]}
    if '"prompts"' in texto:
        import re; n = int(re.search(r'Escribe (\d+) prompts', texto).group(1))
        return {'prompts': [{'test': (i % 18) + 1, 'escena': f'escena {i}', 'prompt': f'the woman in image 1, scene {i}'} for i in range(n)]}
    return {'prompt': 'reescrito: ' + texto[:40]}
def gen_falso(did, modelo_id, prompt, dest):
    llamadas['gen'] += 1
    if modelo_id not in P.LIGA_WS: raise RuntimeError('modelo no disponible')
    base = os.path.join(P.liga_dir(), did); img = dest + '.png'; fp = os.path.join(base, *img.split('/')); os.makedirs(os.path.dirname(fp), exist_ok=True)
    Image.new('RGB', (1080, 1920), (200, 80, 120)).save(fp); mini = os.path.dirname(dest) + '/mini/' + os.path.basename(dest) + '.jpg'; mp = os.path.join(base, *mini.split('/')); os.makedirs(os.path.dirname(mp), exist_ok=True); Image.new('RGB', (480, 853), (200, 80, 120)).save(mp)
    return img, mini, 1080, 1920, 0.14
P._liga_claude = claude_falso; P._liga_gen = gen_falso
did = 'sim-duelo'; os.makedirs(os.path.join(tmp, did))
Dd = {'id': did, 'titulo': 'A vs B', 'a': {'nombre': 'SEEDREAM 5.0 FLASH', 'modelo': 'seedream_5_0_flash', 'nuevo': True}, 'b': {'nombre': 'NANO BANANA PRO', 'modelo': 'nano_banana_pro'}, 'galeria_lado': 'b', 'nota_inicial': '', 'mundos': [], 'tests': P.LIGA_TESTS, 'prompts': [], 'galeria': {}, 'duelo': {}, 'carrusel': [], 'cierre': []}
json.dump(Dd, open(os.path.join(tmp, did, 'duelo.json'), 'w')); json.dump({}, open(os.path.join(tmp, did, 'max.json'), 'w'))
def lee(): return P._liga_lee(did, 'duelo.json')
def maxj(m): json.dump(m, open(os.path.join(tmp, did, 'max.json'), 'w'))
with P.como(P.ARIA_UID, P.ARIA_EMAIL, True):
    print('1) mundos'); P._liga_mundos(did); D1 = lee()
    ok('3 mundos con 6 historias y portada', len(D1['mundos']) == 3 and all(len(w['secuencias']) == 6 and w['img'] for w in D1['mundos']), D1.get('mundos'))
    ok('ya no pone «trabajando» y avisa', D1.get('trabajando') is None and 'mundos' in D1.get('aviso', ''), D1.get('aviso'))
    w0 = D1['mundos'][0]
    print('2) elegir y prompts (sin revisar)'); maxj({'mundo': w0['id'], 'secuencia': w0['secuencias'][0]['id'], 'listo': {'1': 'x'}})
    nuevos = P._liga_prompts(did); D2 = lee(); ok('30 prompts con su test', len(D2['prompts']) == 30 and D2['prompts'][0]['id'] == 'p01', len(D2['prompts']))
    ok('coste estimado de la galería', 'galería de 30' in D2.get('coste_estimado', ''), D2.get('coste_estimado'))
    print('3) galería'); P._liga_galeria(did); D3 = lee()
    ok('30 imágenes en la galería', len(D3['galeria']) == 30 and not D3.get('generando'), (len(D3['galeria']), D3.get('generando')))
    ok('coste acumulado', abs(D3.get('coste_usd', 0) - (3 + 30) * 0.14) < 0.01, D3.get('coste_usd'))
    print('4) peticiones')
    m = {'mundo': w0['id'], 'secuencia': w0['secuencias'][0]['id'], 'listo': {'1': 'x'}, 'fav': ['p01', 'p02', 'p03'], 'duelo': {'p02': {'nota': 'más luz'}}}
    P._liga_peticion(did, {'id': 'q1', 'tipo': 'generar', 'ref': 'duelo', 'pids': ['p01', 'p02', 'p03']}); D4 = lee()
    ok('generar el duelo: parejas completas', all(D4['duelo'][p].get('a') and D4['duelo'][p].get('b') for p in ('p01', 'p02', 'p03')), D4.get('duelo'))
    ok('respuesta «hecha»', D4['respuestas']['q1']['estado'] == 'hecha', D4['respuestas'].get('q1'))
    maxj(m); P._liga_peticion(did, {'id': 'q2', 'tipo': 'regenerar', 'ref': 'p02', 'lado': 'a', 'texto': 'Regenerar SEEDREAM: que se vea la noria'}); D5 = lee()
    ok('regenerar con nota', D5['respuestas']['q2']['estado'] == 'hecha', D5['respuestas'].get('q2'))
    P._liga_peticion(did, {'id': 'q3', 'tipo': 'mas', 'ref': 'galeria', 'n': 3}); D6 = lee()
    ok('3 imágenes más (p31-p33)', len(D6['prompts']) == 33 and all(f'p{k}' in D6['galeria'] for k in (31, 32, 33)), (len(D6['prompts']), sorted(D6['galeria'])[-3:]))
    P._liga_peticion(did, {'id': 'q4', 'tipo': 'secuencia', 'ref': w0['id'], 'texto': 'Aria pierde las gafas en la feria'}); D7 = lee()
    ok('tu historia, la primera de la lista', D7['mundos'][0]['secuencias'][0]['tono'] == '✍️ La tuya', D7['mundos'][0]['secuencias'][0])
    P._liga_peticion(did, {'id': 'q5', 'tipo': 'mundo', 'ref': w0['id'], 'texto': 'otro sitio'}); D8 = lee()
    ok('rehacer un mundo (los otros se quedan)', D8['mundos'][0]['id'] != w0['id'] and D8['mundos'][1]['id'] == D1['mundos'][1]['id'], [x['id'] for x in D8['mundos']])
    P._liga_peticion(did, {'id': 'q6', 'tipo': 'publicar', 'ref': 'notion'}); ok('publicar avisa de que lo hace Claude en el Mac', 'Claude' in lee()['respuestas']['q6']['texto'])
    print('5) el vigía dispara las tareas que tocan')
    did2 = 'sim-2'; os.makedirs(os.path.join(tmp, did2)); json.dump(dict(Dd, id=did2), open(os.path.join(tmp, did2, 'duelo.json'), 'w')); json.dump({}, open(os.path.join(tmp, did2, 'max.json'), 'w'))
    import threading; t = threading.Thread(target=P._liga_vigia, daemon=True); t.start()
    for _ in range(20):
        time.sleep(1)
        if P._liga_lee(did2, 'duelo.json').get('mundos'): break
    ok('un duelo nuevo recibe sus mundos solo', len(P._liga_lee(did2, 'duelo.json').get('mundos') or []) == 3)
    print('6) montar el carrusel con lo simulado')
    m['portada'] = 'mundo'; m['cierre_img'] = 'p01'; m['mundo'] = D8['mundos'][1]['id']; maxj(m)
    import subprocess
    r = subprocess.run([sys.executable, '/Users/maxromanenko/Desktop/XXX/aria-studio-web/servidor/liga/liga.py', 'montar', did], capture_output=True, text=True, env=dict(os.environ, ARIA_LIGA_BASE=tmp))
    ok('la copia del servidor (servidor/liga) monta', r.returncode == 0 and len(lee().get('carrusel') or []) >= 4, (r.returncode, r.stderr[-300:]))
print(f"llamadas falsas: Claude {llamadas['claude']} · imágenes {llamadas['gen']}")
print('fallos:', fallos or 'ninguno'); sys.exit(1 if fallos else 0)
