"""ARIA STUDIO · Filmoteca ligera para la web (v290).

La Filmoteca original pesa 7,8 GB y nunca se subió (no cabía en Supabase gratis). Esto hace una copia LIGERA y la sube al disco
del servidor de Render, para que la web la sirva sin depender del Mac ni del NAS:
  · portadas (_poster.jpg)        → 480 px de ancho
  · vista previa (_lo.mp4)         → igual (ya es ligera)
  · vídeo (.mp4)                   → 540p H.264 1,3 Mbit/s, AAC 96k, listo para internet (+faststart)
  · imágenes de referencia (_refN) → 1280 px como mucho

Los originales del NAS no se tocan. La copia va a ~/.aria-studio/filmoteca_ligera y lo subido se apunta en .subido.json
(se puede cortar y volver a lanzar: sigue por donde iba).

Uso:  python3 filmoteca_ligera.py preparar     (hace la copia ligera)
      python3 filmoteca_ligera.py subir        (la sube; necesita ~/.claude/aria-servidor.env con ARIA_URL y ARIA_ADMIN — no los enseña)
      python3 filmoteca_ligera.py todo         (las dos cosas)
"""
import os, re, sys, json, base64, subprocess, urllib.request, urllib.error, time
from concurrent.futures import ThreadPoolExecutor

SRC = '/Volumes/home/🗄 Work/CLAUDE/Aria Mirror/assets/videoteca'
OUT = os.path.expanduser('~/.aria-studio/filmoteca_ligera')
APUNTE = os.path.join(OUT, '.subido.json')
os.makedirs(OUT, exist_ok=True)


def tipo(n):
    if n.endswith('_poster.jpg'): return 'poster'
    if n.endswith('_lo.mp4'): return 'lo'
    if n.endswith('.mp4'): return 'mp4'
    if re.search(r'_ref\d+\.jpg$', n): return 'ref'
    return None


def ff(*args):
    r = subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', *args], capture_output=True, text=True)
    return r.returncode == 0, r.stderr[-300:]


def uno(n):
    src, dst = os.path.join(SRC, n), os.path.join(OUT, n); t = tipo(n)
    if os.path.isfile(dst) and os.path.getsize(dst) > 0: return n, 'ya'
    tmp = dst + '.tmp' + os.path.splitext(n)[1]
    if t == 'poster': ok, e = ff('-i', src, '-vf', "scale='min(480,iw)':-2", '-q:v', '5', tmp)
    elif t == 'ref': ok, e = ff('-i', src, '-vf', "scale='if(gt(iw,ih),min(1280,iw),-2)':'if(gt(iw,ih),-2,min(1280,ih))'", '-q:v', '4', tmp)
    elif t == 'lo': import shutil; shutil.copyfile(src, tmp); ok, e = True, ''
    else:
        ok, e = ff('-i', src, '-vf', "scale='if(gt(iw,ih),-2,min(540,iw))':'if(gt(iw,ih),min(540,ih),-2)'", '-c:v', 'h264_videotoolbox', '-b:v', '1300k',
                   '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '96k', '-movflags', '+faststart', tmp)
        if not ok: ok, e = ff('-i', src, '-vf', "scale='if(gt(iw,ih),-2,min(540,iw))':'if(gt(iw,ih),min(540,ih),-2)'", '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '27',
                              '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '96k', '-movflags', '+faststart', tmp)
    if not ok:
        try: os.remove(tmp)
        except OSError: pass
        return n, 'ERROR ' + e
    os.replace(tmp, dst); return n, 'hecho'


def preparar():
    L = sorted([n for n in os.listdir(SRC) if tipo(n)], key=lambda n: ['poster', 'lo', 'mp4', 'ref'].index(tipo(n)))
    print(f'{len(L)} ficheros que preparar en {OUT}', flush=True); hechos = errores = 0; t0 = time.time()
    with ThreadPoolExecutor(3) as ex:
        for i, (n, r) in enumerate(ex.map(uno, L), 1):
            if r.startswith('ERROR'): errores += 1; print(n, r, flush=True)
            else: hechos += 1
            if i % 50 == 0: print(f'  {i}/{len(L)} · {int(time.time() - t0)} s', flush=True)
    peso = sum(os.path.getsize(os.path.join(OUT, n)) for n in os.listdir(OUT) if not n.startswith('.'))
    print(f'preparado: {hechos} bien, {errores} con error · la copia ligera pesa {peso / 1e9:.2f} GB', flush=True)


def env():
    E = {}
    for ln in open(os.path.expanduser('~/.claude/aria-servidor.env'), encoding='utf-8'):
        if '=' in ln and not ln.strip().startswith('#'): k, v = ln.split('=', 1); E[k.strip()] = v.strip().strip('"\'')
    return E


def subir():
    E = env(); url = E.get('ARIA_URL', '').rstrip('/'); adm = E.get('ARIA_ADMIN', '')
    if not url or not adm: sys.exit('Falta ARIA_URL o ARIA_ADMIN en ~/.claude/aria-servidor.env')
    try: ya = json.load(open(APUNTE))
    except Exception: ya = {}
    L = sorted([n for n in os.listdir(OUT) if tipo(n) and not '.tmp' in n], key=lambda n: ['poster', 'lo', 'mp4', 'ref'].index(tipo(n)))
    falta = [n for n in L if ya.get(n) != os.path.getsize(os.path.join(OUT, n))]
    print(f'{len(L)} ficheros · faltan por subir {len(falta)}', flush=True); t0 = time.time()

    def sube(n):
        data = open(os.path.join(OUT, n), 'rb').read(); body = json.dumps({'rel': 'assets/videoteca/' + n, 'data': base64.b64encode(data).decode()}).encode()
        for intento in range(4):
            try:
                rq = urllib.request.Request(url + '/api/admin/biblio', data=body, headers={'X-Admin': adm, 'Content-Type': 'application/json', 'User-Agent': 'aria-filmoteca'}, method='POST')
                with urllib.request.urlopen(rq, timeout=180) as r: j = json.loads(r.read() or b'{}')
                if j.get('ok') and j.get('tam') == len(data): return n, len(data)
            except Exception as e: err = str(e)[:120]
            time.sleep(3 * (intento + 1))
        return n, None

    hechos = 0
    with ThreadPoolExecutor(3) as ex:
        for i, (n, tam) in enumerate(ex.map(sube, falta), 1):
            if tam: ya[n] = tam; hechos += 1
            else: print('  ✕ no se pudo subir', n, flush=True)
            if i % 25 == 0:
                json.dump(ya, open(APUNTE, 'w')); print(f'  {i}/{len(falta)} · {int(time.time() - t0)} s', flush=True)
    json.dump(ya, open(APUNTE, 'w')); print(f'subidos {hechos} de {len(falta)}', flush=True)


if __name__ == '__main__':
    q = sys.argv[1] if len(sys.argv) > 1 else ''
    if q in ('preparar', 'todo'): preparar()
    if q in ('subir', 'todo'): subir()
    if q not in ('preparar', 'subir', 'todo'): print(__doc__)
