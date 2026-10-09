#!/usr/bin/env python3
"""ARIA STUDIO · publicación programada (de madrugada, cuando nadie genera).

  python3 publicar_noche.py            → genera public/, comprueba, commit + push, espera a Render, verifica y activa lo pendiente
  python3 publicar_noche.py --consola correo@x.com   → además activa la consola de desarrollador a ese miembro (ruta admin, llave ARIA_ADMIN)

Escribe un registro en publicaciones.log (sin claves). Sale con código 0 si todo quedó en vivo y verificado.
"""
import os, re, sys, json, time, subprocess, urllib.request
W = os.path.dirname(os.path.abspath(__file__)); os.chdir(W)
LOG = os.path.join(W, 'publicaciones.log')
def log(t):
    ln = time.strftime('%Y-%m-%d %H:%M:%S') + ' ' + t; print(ln, flush=True)
    with open(LOG, 'a', encoding='utf-8') as f: f.write(ln + '\n')
def sh(cmd, **kw):
    r = subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True, text=True, **kw)
    if r.returncode: raise SystemExit(log(f'✕ {cmd if isinstance(cmd, str) else " ".join(cmd)} → {(r.stderr or r.stdout).strip()[-400:]}') or 1)
    return r.stdout
def salud():
    try: return json.loads(urllib.request.urlopen('https://aria-studio.onrender.com/salud', timeout=15).read()).get('v')
    except Exception: return None
def rv_en_marcha():   # v463: Motion control generándose (el push reinicia Render y lo mataría)
    try: return int(json.loads(urllib.request.urlopen('https://aria-studio.onrender.com/salud', timeout=15).read()).get('rv') or 0)
    except Exception: return 0
PU = os.path.join(W, 'servidor', 'puente.py'); FU = '/Volumes/home/🗄 Work/CLAUDE/Aria Mirror/puente.py'
ver = int(re.search(r'^VERSION = (\d+)', open(FU, encoding='utf-8').read(), re.M).group(1))
log(f'— publicación programada · v{ver} (en vivo ahora: v{salud()})')
if salud() == ver: log('ya está en vivo esa versión: nada que publicar'); sys.exit(0)
sh('python3 publicar.py'); sh('node --check public/app.js'); sh('node --check public/personajes.js'); sh('node --check public/fichas360.js'); sh('node --check public/cuenta.js'); sh('python3 -m py_compile servidor/puente.py')
sueltos = [f for f in os.listdir('public') if f.startswith('_')]
if sueltos: raise SystemExit(log('✕ hay ficheros de prueba en public/: ' + ', '.join(sueltos)) or 1)
cambios = sh('git status --short').strip()
if not cambios and salud() != ver:
    log('sin cambios en git pero Render no está en la versión: se lanza un despliegue a mano'); sh('python3 render_deploys.py lanzar')
elif cambios:
    t_rv = time.time()
    while rv_en_marcha() and time.time() - t_rv < 30 * 60: log(f'hay {rv_en_marcha()} Motion control en marcha: se espera antes de publicar'); time.sleep(30)
    if rv_en_marcha(): raise SystemExit(log('✕ sigue habiendo un Motion control en marcha tras 30 min: no se publica') or 1)
    msg = f'v{ver}: publicación programada de madrugada\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>'
    sh('git add -A'); sh(['git', 'commit', '-q', '-m', msg])
    for i in range(4):
        r = subprocess.run('git push -q origin main', shell=True, capture_output=True, text=True)
        if not r.returncode: break
        log(f'push ✕ (intento {i + 1}): {r.stderr.strip()[-200:]}'); time.sleep(10)
    else: raise SystemExit(log('✕ no se pudo hacer push') or 1)
    log('push hecho: ' + sh('git log --oneline -1').strip())
t0 = time.time(); lanzado = False
while time.time() - t0 < 25 * 60:
    v = salud()
    if v == ver: break
    if not lanzado and time.time() - t0 > 7 * 60:
        log('Render no ha cogido el push en 7 min: se lanza el despliegue a mano'); subprocess.run('python3 render_deploys.py lanzar', shell=True); lanzado = True
    time.sleep(15)
else: raise SystemExit(log(f'✕ Render sigue sin responder v{ver} tras 25 min (responde v{salud()})') or 1)
log(f'Render en vivo: v{ver} tras {int(time.time() - t0)} s')
try:
    js = urllib.request.urlopen('https://studio.ariacruz.com/app.js', timeout=30).read().decode('utf-8', 'replace')
    log('Vercel: app.js ' + ('con rvControls ✓' if 'rvControls' in js else 'SIN la marca nueva ✕ (puede tardar un minuto más)'))
except Exception as e: log('Vercel: no se pudo leer app.js: ' + str(e)[:120])
if '--consola' in sys.argv:
    correo = sys.argv[sys.argv.index('--consola') + 1]
    E = {}
    for ln in open(os.path.expanduser('~/.claude/aria-servidor.env'), encoding='utf-8'):
        if '=' in ln and not ln.startswith('#'): k, v = ln.strip().split('=', 1); E[k] = v.strip().strip('"\'')
    rq = urllib.request.Request(E['ARIA_URL'].rstrip('/') + '/api/admin/consola', data=json.dumps({'email': correo, 'on': True}).encode(), headers={'X-Admin': E['ARIA_ADMIN'], 'Content-Type': 'application/json'})
    try: log(f'consola para {correo}: ' + urllib.request.urlopen(rq, timeout=30).read().decode()[:120])
    except Exception as e: log(f'consola para {correo} ✕ ' + str(e)[:160])
log('— fin, todo en vivo')
