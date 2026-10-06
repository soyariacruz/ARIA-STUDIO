"""ARIA STUDIO · sube las muestras de voz (assets/muestras/el|seed/*.mp3, hechas con el puente local) al disco del servidor,
para que todo el mundo pueda escuchar las voces en Crear audio. Necesita ~/.claude/aria-servidor.env (ARIA_URL, ARIA_ADMIN). No los enseña."""
import os, json, base64, urllib.request
SRC = '/Volumes/home/🗄 Work/CLAUDE/Aria Mirror/assets/muestras'
E = {}
for ln in open(os.path.expanduser('~/.claude/aria-servidor.env'), encoding='utf-8'):
    if '=' in ln and not ln.strip().startswith('#'): k, v = ln.split('=', 1); E[k.strip()] = v.strip().strip('"\'')
url, adm = E['ARIA_URL'].rstrip('/'), E['ARIA_ADMIN']
ok = mal = 0
for m in ('el', 'seed'):
    d = os.path.join(SRC, m)
    for n in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if not n.endswith('.mp3'): continue
        data = open(os.path.join(d, n), 'rb').read()
        rq = urllib.request.Request(url + '/api/admin/biblio', data=json.dumps({'rel': f'assets/muestras/{m}/{n}', 'data': base64.b64encode(data).decode()}).encode(), headers={'X-Admin': adm, 'Content-Type': 'application/json', 'User-Agent': 'aria-muestras'}, method='POST')
        try:
            with urllib.request.urlopen(rq, timeout=60) as r: j = json.loads(r.read())
            if j.get('ok') and j.get('tam') == len(data): ok += 1
            else: mal += 1; print('✕', m, n, j)
        except Exception as e: mal += 1; print('✕', m, n, str(e)[:100])
print(f'subidas {ok} · fallos {mal}')
