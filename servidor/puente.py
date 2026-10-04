#!/usr/bin/env python3
"""ARIA MIRROR · puente local a la API de Higgsfield.

  python3 puente.py            → sirve la app en http://localhost:8767 y añade:
    GET  /api/ping             → {ok, model, models:[{key,name,ep,refs,usd}], key}
    POST /api/generar          → {prompt, images:[{data:"data:image/..;base64,.."}|{path:"assets/…"}], aspect, resolution, item, model:qwen|grok|mstudio|ideogram}
                                  sube las imágenes (URL prefirmada de Higgsfield), estima el coste y lanza la petición
    GET  /api/estado?id=…      → {status, file, usd, elapsed}  (cuando está completed descarga el resultado a assets/live/)
    GET  /api/live             → {files:{item: 'assets/live/…'}, all:[…], videos:{id: 'assets/video/…'}}  lo ya generado, para no repetir
    POST /api/video            → Seedance 2.0 image-to-video / reference-to-video → assets/video/<id>__<rid8>.mp4

La clave vive en ~/.claude/higgsfield.env como HF_API_KEY=ID:SECRET (nunca en la página).

Modo servidor (ARIA_SERVIDOR=1): el mismo puente para muchas cuentas. Cada una entra con su sesión de Supabase y tiene su casa
($ARIA_DATOS/usuarios/<uid>: sus carpetas, sus claves, su capa sobre el catálogo común) y sus trabajos. Sin la variable, todo sigue como siempre.
    GET  /api/catalogo         → el catálogo que ve la cuenta (el común + su capa)        · solo en modo servidor
"""
import os, re, sys, hmac, json, math, time, base64, hashlib, tarfile, mimetypes, threading, urllib.request, urllib.error, urllib.parse
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

RAIZ = os.path.dirname(os.path.abspath(__file__)); ROOT = RAIZ   # la carpeta del código y de la biblioteca común (ROOT = lo mismo; solo para lo que es de todos)
LIGA_DIR = os.path.join(ROOT, 'assets', 'liga')   # 🥊 Duelos de AI League (v123) · solo en local
LIGA_PY = '/Users/maxromanenko/Desktop/XXX/.claude/scripts/ai_league/liga.py'   # montaje del carrusel (v124)
# ---- «modo servidor» (ARIA_SERVIDOR=1): muchas cuentas a la vez; cada una con su casa, sus claves, sus trabajos y su capa sobre el catálogo común. Sin la variable NO cambia nada (un solo usuario, en local)
SERVIDOR = os.environ.get('ARIA_SERVIDOR') == '1'
HOST = (os.environ.get('ARIA_HOST') or '127.0.0.1') if SERVIDOR else '127.0.0.1'
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else int((SERVIDOR and os.environ.get('PORT')) or 8767)
DATOS = os.path.abspath(os.environ['ARIA_DATOS']) if SERVIDOR and os.environ.get('ARIA_DATOS') else ''   # usuarios/<uid>/ · biblioteca/ (copia de lo común) · jobs.jsonl · puente.log · feedback.jsonl
DEV = SERVIDOR and os.environ.get('ARIA_DEV') == '1' and HOST == '127.0.0.1'   # atajo de pruebas (cabecera X-Dev-Uid): solo existe si el servidor escucha en 127.0.0.1
SB_URL = (os.environ.get('SB_URL') or 'https://uhscbgidrloskdjbevkn.supabase.co').rstrip('/')
SB_KEY = os.environ.get('SB_KEY') or 'sb_publishable_GSO5Vqhr7Dg93egtKk_I2w_E_uScoNG'   # pública por diseño (es la del navegador); lo que protege los datos son las reglas de Supabase
BIBLIO_URL = (os.environ.get('ARIA_BIBLIOTECA') or 'https://uhscbgidrloskdjbevkn.supabase.co/storage/v1/object/public/assets/').rstrip('/') + '/'   # almacén público de la biblioteca común
BIBLIO_OK = tuple('assets/' + x for x in ('biblio/', 'vestidor/', 'hair/', 'expr/', 'movie/', 'cartoon/', 'photo/', 'crear/', 'conv/', 'videoteca/', 'perfil/', 'refs/', 'video/', 'personajes/_opciones/'))   # lo que puede venir de la biblioteca común (+ personajes/_lienzo.jpg y lo de assets/live que usa el perfil común)
ORIGENES = tuple(o.strip().lower().rstrip('/') for o in (os.environ.get('ARIA_ORIGENES') or 'https://aria-studio-eta.vercel.app,http://localhost:3000').split(',') if o.strip())
FETCH_HOSTS = tuple(h.strip().lower() for h in (os.environ.get('ARIA_FETCH_HOSTS') or ','.join([urllib.parse.urlsplit(SB_URL).hostname or '', '.wavespeed.ai', '.higgsfield.ai', '.cloudfront.net', '.bytepluses.com', '.volces.com'])).split(',') if h.strip())   # /api/fetch en servidor: host exacto o «.sufijo»; «*» = cualquier sitio público
MAX_CUERPO = 40 * 1024 * 1024    # tope de una petición en modo servidor
MAX_BIBLIO = 200 * 1024 * 1024   # tope de un fichero de la biblioteca común al copiarlo
KINDS = ('vestidor', 'hair', 'expr')   # las bibliotecas a las que una cuenta puede añadir lo suyo
_UUID = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')
VERSION = 188
_ctx = threading.local()   # la cuenta del hilo: la pone cada petición (y, a mano, cada hilo de fondo)
def uid(): return getattr(_ctx, 'uid', None)   # en local siempre None
DUENOS = tuple(e.strip().lower() for e in (os.environ.get('ARIA_DUENOS') or 'mix1994max@gmail.com').split(',') if e.strip())   # cuentas que pueden cambiar a Aria Cruz (en la web, la de Max)
def aria_fija(): return SERVIDOR and (getattr(_ctx, 'email', '') or '').lower() not in DUENOS   # para el resto de cuentas Aria es un personaje fijo: se ve y se usa, no se edita
FIJA = 'Aria Cruz es un personaje fijo: su ficha no se puede cambiar. Crea o edita tu propio personaje.'
class como:   # «with como(uid): …» → lo de dentro corre como esa cuenta
    def __init__(self, u, email='', interno=False): self.n = (u, email, interno)
    def __enter__(self): self.a = (getattr(_ctx, 'uid', None), getattr(_ctx, 'email', ''), getattr(_ctx, 'interno', False)); _ctx.uid, _ctx.email, _ctx.interno = self.n; _ctx.comun = None; _ctx.ws_modo = None; _ctx.casa_ok = False
    def __exit__(self, *a): _ctx.uid, _ctx.email, _ctx.interno = self.a; _ctx.comun = None; _ctx.ws_modo = None; _ctx.casa_ok = False
def casa():   # la carpeta de la cuenta: en local, la de siempre; en servidor, $ARIA_DATOS/usuarios/<uid> (con la misma forma: assets/live, assets/video, assets/personajes, assets/perfil…)
    if not SERVIDOR: return RAIZ
    u = uid()
    if not DATOS or not isinstance(u, str) or not _UUID.fullmatch(u): raise RuntimeError('sin cuenta')
    return os.path.join(DATOS, 'usuarios', u)
def _dir(*p):   # carpeta dentro de la casa; se crea la primera vez que hace falta
    d = os.path.join(casa(), *p); os.makedirs(d, exist_ok=True); return d
def live_dir(): return _dir('assets', 'live')
def video_dir(): return _dir('assets', 'video')
def pers_dir(): return _dir('assets', 'personajes')
def refs_dir(): return _dir('assets', 'refs')
def mini_dir(): return os.path.join(live_dir(), '.mini')
def papelera(): return _dir('assets', 'papelera')
def perfil_dir(*sub): return _dir('assets', 'perfil', *sub)
def mio(kind):   # (carpeta, prefijo en el catálogo) de lo que la cuenta AÑADE a una biblioteca: en local entra en la de siempre; en servidor se queda en su casa (assets/mio/<tipo>/)
    return (_dir('assets', 'mio', kind), f'assets/mio/{kind}/') if SERVIDOR else (_dir('assets', kind), f'assets/{kind}/')
_cerrojos = {}; _cerrojos_l = threading.Lock()
def _cerrojo(que='cat'):   # un cerrojo por cuenta (en local, uno solo, como siempre): el catálogo y los personaje.json no se pisan
    with _cerrojos_l: return _cerrojos.setdefault((uid(), que), threading.Lock())
def _pid_ok(pid):   # id de personaje: nunca puede salirse de assets/personajes de la cuenta
    if not isinstance(pid, str) or not pid or pid.startswith(('_', '.')) or '/' in pid: return False
    return bool(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,80}', pid)) if SERVIDOR else True
def _rel_ok(rel):   # ruta que manda el navegador → 'assets/…' limpia (sin ?v=), o None: ni absolutas, ni «..», ni NUL, ni nada fuera de assets/
    if not isinstance(rel, str): return None
    rel = rel.split('?')[0]
    if not rel or '\0' in rel or '\\' in rel or rel.startswith('/') or os.path.isabs(rel): return None
    L = [x for x in rel.split('/') if x not in ('', '.')]
    if len(L) < 2 or L[0] != 'assets' or '..' in L: return None
    return '/'.join(L)
def _dentro(base, full):   # full cae dentro de base (por carpetas, no por «empieza por»); en servidor, también después de resolver enlaces simbólicos
    try:
        b, f = os.path.abspath(base), os.path.abspath(full)
        if SERVIDOR: b, f = os.path.realpath(b), os.path.realpath(f)
        return f != b and os.path.commonpath([b, f]) == b
    except ValueError: return False
def busca(rel, propio=False):   # ÚNICA puerta para las rutas que manda el navegador: primero la casa de la cuenta; si no, la biblioteca común (propio=True: solo la casa). Devuelve el fichero real o None
    rel = _rel_ok(rel)
    if not rel: return None
    base = casa(); full = os.path.join(base, *rel.split('/'))
    if _dentro(base, full) and os.path.isfile(full): return full
    return _biblio(rel) if SERVIDOR and not propio else None   # en local la biblioteca común ES la carpeta de siempre
def _biblio_ok(rel):
    if rel.startswith(BIBLIO_OK) or rel == 'assets/personajes/_lienzo.jpg': return True
    try: return rel.startswith('assets/live/') and rel in _comun()['live']
    except Exception: return False
def _biblio_url(rel): return BIBLIO_URL + urllib.parse.quote(rel[len('assets/'):])
_biblio_no = {}   # ruta → cuándo dijo el almacén que no la tiene (no se le vuelve a preguntar en 5 min)
def _biblio(rel):   # fichero de la biblioteca común en la copia del servidor ($ARIA_DATOS/biblioteca); si falta, se baja una vez del almacén público
    if not DATOS or not _biblio_ok(rel): return None
    base = os.path.join(DATOS, 'biblioteca'); full = os.path.join(base, *rel.split('/'))
    if not _dentro(base, full): return None
    if os.path.isfile(full): return full
    if time.time() - _biblio_no.get(rel, 0) < 300: return None
    try:
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with urllib.request.urlopen(urllib.request.Request(_biblio_url(rel), headers={'User-Agent': UA}), timeout=120) as r: data = r.read(MAX_BIBLIO + 1)
        if len(data) > MAX_BIBLIO: raise RuntimeError('demasiado grande')
        tmp = f'{full}.tmp{threading.get_ident()}'; open(tmp, 'wb').write(data); os.replace(tmp, full); return full
    except Exception as e:
        if len(_biblio_no) > 5000: _biblio_no.clear()
        _biblio_no[rel] = time.time(); plog(f'biblioteca ✕ {rel} · {str(e)[:120]}'); return None
_comun_c = {}; _comun_l = threading.Lock()
def _comun():   # catálogo común, de SOLO lectura → {'txt': su JSON, 'ids': {tipo: ids}, 'padre': {prenda: parent}, 'perfil': …, 'live': rutas de assets/live que usa su perfil}
    with _comun_l:
        fp = os.environ.get('ARIA_CATALOGO'); now = time.time(); v = _comun_c.get('v')
        if fp:   # fichero local (catalog.json o catalog.js): se vuelve a leer solo cuando cambia
            sig = (os.path.getmtime(fp), os.path.getsize(fp))
            if v and _comun_c.get('sig') == sig: return v
            raw = open(fp, encoding='utf-8').read()
        else:   # almacén privado de Supabase (catalogo/catalog.js), como mucho una vez cada 5 minutos
            if v and now - _comun_c.get('t', 0) < 300: return v
            sec = os.environ.get('SUPABASE_SECRET') or ''
            try:
                if not sec: raise RuntimeError('falta ARIA_CATALOGO o SUPABASE_SECRET')
                rq = urllib.request.Request(SB_URL + '/storage/v1/object/catalogo/catalog.js', headers={'Authorization': 'Bearer ' + sec, 'apikey': sec, 'User-Agent': UA})
                with urllib.request.urlopen(rq, timeout=60) as r: raw = r.read().decode('utf-8')
            except Exception as e:
                plog('catálogo común ✕ ' + (str(e)[:200].replace(sec, '***') if sec else str(e)[:200]))   # la clave secreta nunca llega al registro
                if v: _comun_c['t'] = now - 240; return v   # sigue valiendo el anterior; se reintenta en un minuto
                raise RuntimeError('no se pudo leer el catálogo común')
            sig = hashlib.sha1(raw.encode()).hexdigest(); _comun_c['t'] = now
            if v and _comun_c.get('sig') == sig: return v
        txt = raw[raw.index('{'):raw.rindex('}') + 1]; C = json.loads(txt); live = set()
        def _anda(x):
            if isinstance(x, str):
                if x.startswith('assets/live/'): live.add(x.split('?')[0])
            elif isinstance(x, dict):
                for y in x.values(): _anda(y)
            elif isinstance(x, list):
                for y in x: _anda(y)
        _anda(C.get('perfil'))
        v = {'txt': txt, 'ids': {k: {x.get('id') for x in C.get(k) or [] if isinstance(x.get('id'), str)} for k in KINDS}, 'padre': {x['id']: x.get('parent') for x in C.get('vestidor') or [] if isinstance(x.get('id'), str)}, 'perfil': C.get('perfil') or {}, 'live': live}
        _comun_c.update(v=v, sig=sig); return v
# ---- sesión (modo servidor): token de Supabase → cuenta, y solo si está en la lista de miembros
class _NoEntra(Exception):
    def __init__(self, code, msg): super().__init__(msg); self.code, self.msg = code, msg
_ses = {}; _ses_l = threading.Lock(); _ses_v = [threading.Lock() for _ in range(16)]   # sha256(token) → (caduca, (uid, email, interno) | _NoEntra)
def _ses_pon(h, hasta, val):
    with _ses_l:
        if len(_ses) >= 2000:   # tamaño acotado: fuera lo caducado; si aun así no cabe, se vacía
            now = time.time()
            for k in [k for k, s in _ses.items() if s[0] <= now]: del _ses[k]
            if len(_ses) >= 2000: _ses.clear()
        _ses[h] = (hasta, val)
def _sb_get(path, token):
    rq = urllib.request.Request(SB_URL + path, headers={'apikey': SB_KEY, 'Authorization': 'Bearer ' + token, 'Accept': 'application/json', 'User-Agent': UA})
    with urllib.request.urlopen(rq, timeout=15) as r: return json.loads(r.read(1 << 20) or b'null')
_precio = {}   # uid → lo que paga en Skool ($/mes, o $/año si es ≥ 100): de ahí sale su saldo regalo de cada mes
def _miembros(token):   # la fila de quien pregunta; si la columna «precio» todavía no existe en Supabase, sin ella
    try: return _sb_get('/rest/v1/miembros?select=email,interno,precio', token)
    except urllib.error.HTTPError as e:
        if e.code != 400: raise
        return _sb_get('/rest/v1/miembros?select=email,interno', token)
def _sesion(token):   # token de acceso de Supabase → (uid, email, interno). Se recuerda 5 min como mucho (y nunca más allá de lo que dura el token)
    if not token or len(token) > 4096 or not re.fullmatch(r'[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+', token): raise _NoEntra(401, 'sesión no válida')
    h = hashlib.sha256(token.encode()).hexdigest()
    def _mira():
        with _ses_l: s = _ses.get(h)
        if not s or s[0] <= time.time(): return None
        if isinstance(s[1], _NoEntra): raise s[1]
        return s[1]
    r = _mira()
    if r: return r
    with _ses_v[int(h[:2], 16) % 16]:   # la misma sesión no se comprueba dos veces a la vez
        r = _mira()
        if r: return r
        now = time.time()
        try:
            try: mid = token.split('.')[1]; exp = float(json.loads(base64.urlsafe_b64decode(mid + '=' * (-len(mid) % 4))).get('exp') or 0)
            except Exception: exp = 0
            if exp and exp < now: raise _NoEntra(401, 'sesión caducada')
            try: us = _sb_get('/auth/v1/user', token)
            except urllib.error.HTTPError as e: raise _NoEntra(401 if e.code in (400, 401, 403, 404) else 503, 'sesión no válida' if e.code in (400, 401, 403, 404) else 'no se pudo comprobar la sesión')
            except Exception: raise _NoEntra(503, 'no se pudo comprobar la sesión')
            us = us if isinstance(us, dict) else {}; u = str(us.get('id') or '').lower(); email = str(us.get('email') or '').strip().lower()
            if not _UUID.fullmatch(u) or not email: raise _NoEntra(401, 'sesión no válida')
            try: filas = _miembros(token)   # las reglas de Supabase solo devuelven la fila de quien pregunta
            except urllib.error.HTTPError as e: raise _NoEntra(403 if e.code in (401, 403) else 503, 'esta cuenta no tiene acceso' if e.code in (401, 403) else 'no se pudo comprobar la lista de miembros')
            except Exception: raise _NoEntra(503, 'no se pudo comprobar la lista de miembros')
            fila = next((f for f in (filas if isinstance(filas, list) else []) if isinstance(f, dict) and str(f.get('email') or '').strip().lower() == email), None)   # por si las reglas devolvieran más filas: solo vale la suya
            if not fila: raise _NoEntra(403, 'esta cuenta no está en la lista de miembros')
            res = (u, email, fila.get('interno') is True)
            try: _precio[u] = float(fila.get('precio')) if fila.get('precio') is not None else 4.0
            except (TypeError, ValueError): _precio[u] = 4.0
        except _NoEntra as e:
            if e.code != 503: _ses_pon(h, now + 30, e)   # un token malo no se le pregunta a Supabase en cada petición
            raise
        _ses_pon(h, min(now + 300, exp) if exp else now + 300, res); return res
def _quien(h):   # petición → (uid, email, interno), o _NoEntra(401|403|503)
    if DEV and h.server.server_address[0] == '127.0.0.1' and h.client_address[0] == '127.0.0.1' and not any(h.headers.get(x) for x in ('X-Forwarded-For', 'Forwarded', 'X-Real-Ip')):
        d = (h.headers.get('X-Dev-Uid') or '').strip().lower()
        if d:
            if not _UUID.fullmatch(d): raise _NoEntra(401, 'X-Dev-Uid no válido')
            _ctx.sin_casa = h.headers.get('X-Dev-Casa') == '0'   # pruebas: esta petición, como si no hubiera clave de la casa
            try: _precio[d] = float(h.headers.get('X-Dev-Precio') or _precio.get(d, 4))
            except ValueError: pass
            return d, f'dev-{d[:8]}@dev.local', h.headers.get('X-Dev-Interno') == '1'
    a = h.headers.get('Authorization') or ''; tok = a[7:].strip() if a[:7].lower() == 'bearer ' else ''
    if not tok:
        for par in (h.headers.get('Cookie') or '').split(';'):
            k, _, v = par.strip().partition('=')
            if k == 'aria_token': tok = v.strip()
    if not tok: raise _NoEntra(401, 'falta la sesión')
    return _sesion(tok)
# ---- /api/fetch en modo servidor: solo https, solo sitios de la lista, nunca direcciones internas (tampoco por redirección)
def _host_ok(host): return '*' in FETCH_HOSTS or any(host == x or (x.startswith('.') and host.endswith(x)) for x in FETCH_HOSTS)
def _ip_publica(host):   # todas las direcciones del nombre tienen que ser públicas (ni privadas, ni loopback, ni link-local, ni reservadas) → devuelve una, y a ESA se conecta
    import socket, ipaddress
    ips = [i[4][0] for i in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)]
    if not ips: raise RuntimeError('sitio desconocido')
    for ip in ips:
        a = ipaddress.ip_address(ip.split('%')[0]); a = getattr(a, 'ipv4_mapped', None) or a
        if not a.is_global or a.is_multicast: raise RuntimeError('dirección no permitida')
    return ips[0]
def _fetch_seguro(url, tope=25 * 1024 * 1024):
    import http.client, socket, ssl
    for _ in range(4):   # las redirecciones se siguen a mano: cada salto pasa las mismas comprobaciones
        u = urllib.parse.urlsplit(url); host = (u.hostname or '').lower().rstrip('.')
        if u.scheme != 'https' or not host or u.username or u.password or u.port not in (None, 443): raise RuntimeError('url no permitida (solo https)')
        if not _host_ok(host): raise RuntimeError('ese sitio no está en la lista permitida: guarda la imagen y arrástrala desde tu ordenador')
        ip = _ip_publica(host)
        class _Con(http.client.HTTPSConnection):
            def connect(s): s.sock = ssl.create_default_context().wrap_socket(socket.create_connection((ip, 443), timeout=20), server_hostname=host)   # a la dirección ya comprobada (sin segunda resolución de nombres)
        c = _Con(host, 443, timeout=20)
        try:
            c.request('GET', urllib.parse.quote(u.path or '/', safe="/%:@!$&'()*+,;=~-._") + ('?' + urllib.parse.quote(u.query, safe="/%:@!$&'()*+,;=~-._?") if u.query else ''), headers={'User-Agent': 'Mozilla/5.0 (Macintosh) AppleWebKit/537.36 Chrome/120 Safari/537.36', 'Accept': 'image/*,*/*'})
            r = c.getresponse()
            if r.status in (301, 302, 303, 307, 308):
                if not r.getheader('Location'): raise RuntimeError('redirección sin destino')
                url = urllib.parse.urljoin(url, r.getheader('Location')); continue
            if r.status != 200: raise RuntimeError(f'el sitio respondió {r.status}')
            data = r.read(tope + 1)
            if len(data) > tope: raise RuntimeError('imagen demasiado grande')
            return data, (r.getheader('Content-Type') or 'image/jpeg').split(';')[0].strip()
        finally: c.close()
    raise RuntimeError('demasiadas redirecciones')
def _trae_url(url):   # una URL de internet → (bytes, tipo). En servidor, con todas las comprobaciones de _fetch_seguro
    if SERVIDOR: return _fetch_seguro(url)
    if not url.lower().startswith(('http://', 'https://')): raise RuntimeError('url no válida')
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh) AppleWebKit/537.36 Chrome/120 Safari/537.36', 'Accept': 'image/*,text/html,*/*'})
    with urllib.request.urlopen(req, timeout=30) as r: return r.read(25 * 1024 * 1024), r.headers.get('Content-Type', 'image/jpeg').split(';')[0]
def _fotos_key():   # la clave del buscador de fotos es de la plataforma (no de cada cuenta) → (proveedor, clave). Variables PEXELS_KEY o PIXABAY_KEY en el servidor; en local, ~/.claude/pexels.env o ~/.claude/pixabay.env
    for prov, var, fich in (('pexels', 'PEXELS_KEY', 'pexels.env'), ('pixabay', 'PIXABAY_KEY', 'pixabay.env')):
        k = (os.environ.get(var) or '').strip()
        if not k and not SERVIDOR:
            try:
                for line in open(os.path.expanduser('~/.claude/' + fich)):
                    if line.startswith(var + '='): k = line.strip().split('=', 1)[1].strip()
            except Exception: pass
        if k: return prov, k
    return None, ''
def _fotos_busca(prov, k, qq, pg):   # → lista de {id, thumb, img, autor, url, alt}
    if prov == 'pixabay':   # https://pixabay.com/api/docs/ · 100 búsquedas/minuto · pide guardar las búsquedas 24 h y no enlazar sus imágenes de forma permanente (aquí la elegida se descarga y se guarda)
        url = 'https://pixabay.com/api/?' + urllib.parse.urlencode({'key': k, 'q': qq, 'lang': 'es', 'image_type': 'photo', 'orientation': 'horizontal', 'safesearch': 'true', 'per_page': 30, 'page': pg})
        j = json.loads(urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 aria-studio'}), timeout=20).read())
        return [{'id': p.get('id'), 'thumb': p.get('webformatURL'), 'img': p.get('largeImageURL') or p.get('webformatURL'), 'autor': p.get('user') or '', 'url': p.get('pageURL') or '', 'alt': p.get('tags') or ''} for p in (j.get('hits') or []) if p.get('webformatURL')]
    rq = urllib.request.Request('https://api.pexels.com/v1/search?' + urllib.parse.urlencode({'query': qq, 'per_page': 30, 'page': pg, 'orientation': 'landscape', 'locale': 'es-ES'}), headers={'Authorization': k, 'User-Agent': 'Mozilla/5.0 aria-studio'})
    j = json.loads(urllib.request.urlopen(rq, timeout=20).read())
    return [{'id': p.get('id'), 'thumb': (p.get('src') or {}).get('medium'), 'img': (p.get('src') or {}).get('large2x') or (p.get('src') or {}).get('large'), 'autor': p.get('photographer') or '', 'url': p.get('url') or '', 'alt': p.get('alt') or ''} for p in (j.get('photos') or []) if (p.get('src') or {}).get('medium')]
_PEX = {}; _PEX_N = {}   # búsquedas ya hechas (un día) y búsquedas por cuenta en la última hora
BASE = 'https://api.higgsfield.ai'
MODEL = 'alibaba/qwen-image-3/edit'          # modelo por defecto (edición con 1-3 imágenes de referencia)
# Modelos de imagen de la API pública que aceptan una foto de entrada (docs.higgsfield.ai, 23 sep 2026). Precio = /estimate a 1k, 3:4.
ASPECTS = ['3:4', '1:1', '4:3', '9:16', '16:9', '2:3', '3:2']          # comunes a los 4 modelos
def aspect_ok(a): return a if a in ASPECTS else '3:4'
# q = 'std' | 'high' (calidad elegida en la app)
def _qwen(p, urls, ar, q):  return {'prompt': p, 'image_urls': urls[:3], 'resolution': '2k' if q == 'high' else '1k', 'aspect_ratio': ar, 'prompt_extend': False, 'enable_thinking': False}
def _grok(p, urls, ar, q):  return {'prompt': p, 'image_urls': urls[:10], 'resolution': '2k' if q == 'high' else '1k', 'aspect_ratio': ar, 'quality': 'medium'}
def _ideo(p, urls, ar, q):  return {'prompt': p[:2048], 'image_url': urls[0], 'aspect_ratio': ar, 'rendering_speed': 'QUALITY' if q == 'high' else 'DEFAULT'}   # image_weight hace fallar la petición (probado 23 sep)
def _mstu(p, urls, ar, q):  return {'prompt': p[:5000], 'image_urls': urls[:16], 'resolution': '1k', 'aspect_ratio': ar, 'quality': 'high' if q == 'high' else 'medium', 'enhance_prompt': False, 'moderation': 'auto'}
# ---- WaveSpeed AI (clave en ~/.claude/wavespeed.env como WS_API_KEY=wsk_live_…): trae los modelos que la API de Higgsfield no tiene
def _nbp(p, urls, ar, q):   return {'prompt': p, 'images': urls[:14], 'resolution': '2k' if q == 'high' else '1k', 'aspect_ratio': ar, 'output_format': 'jpeg'}
def _gpt(p, urls, ar, q):   return {'prompt': p, 'images': urls[:16], 'resolution': '2k' if q == 'high' else '1k', 'quality': 'high' if q == 'high' else 'medium', 'aspect_ratio': ar, 'output_format': 'jpeg'}
def _sdrm(p, urls, ar, q):  return {'prompt': p, 'images': urls[:10], 'resolution': '2k' if q == 'high' else '1.5k', 'aspect_ratio': ar, 'output_format': 'jpeg', 'prompt_optimization_mode': 'standard'}
def _sflash(p, urls, ar, q): return {'prompt': p, 'images': urls[:10], 'resolution': '2k' if q == 'high' else '1.5k', 'aspect_ratio': ar, 'output_format': 'jpeg'}
def _qwws(p, urls, ar, q):  return {'prompt': p, 'images': urls[:3], 'resolution': '2k' if q == 'high' else '1k', 'aspect_ratio': ar}
WS_MODELS = {   # precios de la página de cada modelo en wavespeed.ai (3 oct 2026): 'usd' = con UNA referencia; 'per' = recargo por cada referencia más
    'nbp':      {'ep': 'google/nano-banana-pro/edit',          'name': 'Nano Banana Pro',  'refs': 14, 'usd': {'std': 0.14,  'high': 0.14},  'per': 0,     'body': _nbp,  'nota': 'Google · por WaveSpeed · hasta 14 referencias · 1K y 2K cuestan lo mismo', 'high': '2k', 'prov': 'ws'},
    'gptimg':   {'ep': 'openai/gpt-image-2.5-sunburst/edit',   'name': 'GPT Image 2.5',    'refs': 16, 'usd': {'std': 0.039, 'high': 0.165}, 'per': 0.015, 'body': _gpt,  'nota': 'OpenAI · por WaveSpeed · hasta 16 referencias', 'high': '2k · calidad alta', 'prov': 'ws'},
    'seedream': {'ep': 'bytedance/seedream-v5.0-pro/edit',     'name': 'Seedream 5.0 Pro', 'refs': 10, 'usd': {'std': 0.045, 'high': 0.09},  'per': 0.003, 'body': _sdrm, 'nota': 'ByteDance · por WaveSpeed · hasta 10 referencias', 'high': '2k', 'std': '1.5k', 'prov': 'ws'},
    'seedflash': {'ep': 'bytedance/seedream-v5.0-flash/edit',  'name': 'Seedream 5.0 Flash', 'refs': 10, 'usd': {'std': 0.027, 'high': 0.027}, 'per': 0, 'body': _sflash, 'nota': 'ByteDance · por WaveSpeed · el más barato · hasta 10 referencias · precio fijo', 'high': '2k', 'std': '1.5k', 'prov': 'ws'},
    'qwenws':   {'ep': 'alibaba/qwen-image-3.0/edit',          'name': 'Qwen Image 3 · WaveSpeed', 'refs': 3, 'usd': {'std': 0.03, 'high': 0.03}, 'per': 0.003, 'body': _qwws, 'nota': 'el mismo Qwen Image 3, por WaveSpeed · 1-3 referencias · 1K y 2K cuestan lo mismo', 'high': '2k', 'prov': 'ws'},
}
CLAVES = os.path.expanduser('~/.aria-studio/claves.env')   # claves pegadas en la pantalla «Conecta tu API»: fuera de la carpeta de la app (ni se sirven ni viajan en un zip)
# ---- en servidor las claves de cada cuenta se guardan CIFRADAS: el secreto vive en el entorno del servidor (ARIA_SECRETO), no en el disco ni en las copias de seguridad
def _secreto():
    v = os.environ.get('ARIA_SECRETO') or ''
    if not v and os.environ.get('ARIA_SECRETO_FICHERO'):
        try: v = open(os.environ['ARIA_SECRETO_FICHERO']).read().strip()
        except Exception: v = ''
    return v.encode() if len(v) >= 32 else b''
SECRETO = _secreto() if SERVIDOR else b''
def _flujo(k, nonce, n):   # n bytes de relleno a partir de HMAC-SHA256 en modo contador
    out = b''; i = 0
    while len(out) < n: out += hmac.new(k, nonce + i.to_bytes(4, 'big'), hashlib.sha256).digest(); i += 1
    return out[:n]
def _cifra(v):   # «v1:» + base64(nonce 16 · texto cifrado · sello 32). Cifra y luego sella (si alguien toca el fichero, no descifra)
    if not SECRETO: raise RuntimeError('el servidor no tiene configurado el cifrado de claves (ARIA_SECRETO)')
    ke, km = hmac.new(SECRETO, b'cifra', hashlib.sha256).digest(), hmac.new(SECRETO, b'sella', hashlib.sha256).digest()
    nonce = os.urandom(16); p = v.encode(); ct = bytes(a ^ b for a, b in zip(p, _flujo(ke, nonce, len(p))))
    return 'v1:' + base64.urlsafe_b64encode(nonce + ct + hmac.new(km, nonce + ct, hashlib.sha256).digest()).decode()
def _descifra(v):   # '' si el sello no cuadra o no hay secreto
    try:
        if not SECRETO: return ''
        raw = base64.urlsafe_b64decode(v[3:]); nonce, ct, sello = raw[:16], raw[16:-32], raw[-32:]
        ke, km = hmac.new(SECRETO, b'cifra', hashlib.sha256).digest(), hmac.new(SECRETO, b'sella', hashlib.sha256).digest()
        if not hmac.compare_digest(sello, hmac.new(km, nonce + ct, hashlib.sha256).digest()): return ''
        return bytes(a ^ b for a, b in zip(ct, _flujo(ke, nonce, len(ct)))).decode()
    except Exception: return ''
# ---- tope de espacio por cuenta (solo servidor): lo que pesa su casa, papelera incluida
CUOTA = int(float(os.environ.get('ARIA_CUOTA_GB') or 3) * 1024 ** 3)
_peso = {}   # uid → (cuándo se midió, bytes)
def espacio(fresco=False):
    u = uid(); c = _peso.get(u)
    if c and not fresco and time.time() - c[0] < 60: return c[1]
    n = 0
    for d, _, fs in os.walk(casa()):
        for f in fs:
            try: n += os.path.getsize(os.path.join(d, f))
            except OSError: pass
    _peso[u] = (time.time(), n); return n
def lleno(): return SERVIDOR and espacio() >= CUOTA
LLENO = 'Has llenado tu espacio en ARIA STUDIO. Descarga y borra creaciones que ya no necesites para seguir generando.'
def _claves_fp(): return os.path.join(casa(), 'claves.env') if SERVIDOR else CLAVES   # en servidor: las de la cuenta, en su casa (fuera de assets/: no se sirven)
def _off(name):   # API desconectada desde la pantalla: la clave sigue en el ordenador, pero no se usa
    try: return any(l.strip() == name + '_OFF=1' for l in open(_claves_fp()))
    except Exception: return False
def _env(name, home_file, aunque_off=False):   # primero lo pegado en la pantalla; si no, los ficheros de ~/.claude (los de Max) — en servidor SOLO las de la cuenta, sin caer nunca a las de Max
    if not aunque_off and _off(name): return ''
    for fp in ((_claves_fp(),) if SERVIDOR else (CLAVES, os.path.expanduser('~/.claude/' + home_file))):
        try:
            for line in open(fp):
                if line.startswith(name + '='):
                    v = line.strip().split('=', 1)[1].strip()
                    if SERVIDOR and v and not name.endswith('_OFF'):
                        if v.startswith('v1:'): v = _descifra(v)
                        elif SECRETO: _claves_set(name, v)   # venía sin cifrar (de antes): se cifra ahora
                    if v: return v
        except Exception: pass
    return ''
def _claves_set(name, value):
    fp = _claves_fp(); os.makedirs(os.path.dirname(fp), mode=0o700, exist_ok=True); L = []
    if os.path.exists(fp): L = [x for x in open(fp).read().splitlines() if x.strip() and not x.startswith(name + '=')]
    if value: L.append(f'{name}={_cifra(value) if SERVIDOR and not name.endswith("_OFF") else value}')
    with os.fdopen(os.open(fp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), 'w') as f: f.write('\n'.join(L) + '\n')   # nace ya con 0600
    os.chmod(fp, 0o600)
def _ws_saldo(k):   # comprueba una clave de WaveSpeed pidiendo su saldo
    rq = urllib.request.Request('https://api.wavespeed.ai/api/v3/balance'); rq.add_header('Authorization', 'Bearer ' + k); rq.add_header('User-Agent', UA)
    return float((json.loads(urllib.request.urlopen(rq, timeout=30).read()).get('data') or {}).get('balance'))
def load_ws(): return _env('WS_API_KEY', 'wavespeed.env')
# ---- 🎁 SALDO REGALO (v184, solo en modo servidor). Quien no tiene su propia clave de WaveSpeed genera con la de la casa (variable ARIA_CASA_WS) y se le descuenta de su monedero:
#      1 $ de bienvenida (una vez, no caduca) + cada mes ≈10 % de lo que paga en Skool, redondeado hacia arriba a 0,50 $ (se repone el día 1 y no se acumula). Sin NSFW. Sin la variable, nada de esto existe.
def _casa_key():
    k = (os.environ.get('ARIA_CASA_WS') or '').strip()
    if not k and DEV:   # en el servidor de pruebas de este ordenador, la clave de Max hace de «clave de la casa»
        try:
            for line in open(os.path.expanduser('~/.claude/wavespeed.env')):
                if line.startswith('WS_API_KEY='): k = line.strip().split('=', 1)[1].strip()
        except Exception: pass
    return k
CASA_KEY = _casa_key() if SERVIDOR else ''
CASA_TOPE = float(os.environ.get('ARIA_CASA_TOPE') or 1000)   # $ al mes entre TODAS las cuentas: freno de seguridad, no recorta a nadie en condiciones normales
CASA_MODELOS = ('seedflash', 'gptimg', 'nbp'); CASA_DEF = 'seedflash'   # con el saldo regalo: el barato por defecto y los dos que traen su propio filtro; Seedream 5.0 Pro (sin filtro) queda fuera
BIENVENIDA = 1.0; LECTURA_USD = 0.002   # cada lectura de una imagen con IA (describir una foto, detectar personas…)
SIN_SALDO = 'Saldo regalo agotado. Se repone el día 1; para seguir ahora, conecta tu propia clave en «API en vivo».'
_NSFW_RE = re.compile(r"\b(nsfw|topless|nipples?|areolas?|genitals?|genitalia|pubic|vagina|vulva|penis|no clothes|(?:is|are|she'?s|he'?s|fully|completely|totally|stark) naked|naked (?:woman|women|man|men|girl|boy|body|person|people|figure|torso|chest|skin)|(?:fully|completely|totally) nude|nude body|bare breasts?|no underwear|sexually explicit|explicit nud)", re.I)
def _es_nsfw(prompt): return bool(_NSFW_RE.search(re.split(r'negative prompt\s*:', str(prompt or ''), flags=re.I)[0]))   # lo que va detrás de «Negative prompt:» es justo lo que NO se quiere en la imagen
_lect_l = threading.Lock()
def _lecturas(): 
    try: d = json.load(open(os.path.join(casa(), 'lecturas.json')))
    except Exception: d = {}
    return {'usd': float(d.get('usd') or 0), 'n': int(d.get('n') or 0)} if isinstance(d, dict) else {'usd': 0.0, 'n': 0}
def _lectura_apunta():   # una lectura de imagen con IA (≈0,002 $): al total de la cuenta y a la respuesta de esta petición
    try:
        _ctx.lectura = getattr(_ctx, 'lectura', 0) + LECTURA_USD
        with _lect_l:
            d = _lecturas(); d = {'usd': round(d['usd'] + LECTURA_USD, 4), 'n': d['n'] + 1}; fp = os.path.join(casa(), 'lecturas.json')
            with open(fp + '.tmp', 'w') as f: json.dump(d, f)
            os.replace(fp + '.tmp', fp)
    except Exception: pass
def _casa_base(): return bool(SERVIDOR and CASA_KEY and uid() and not getattr(_ctx, 'sin_casa', False))
def casa_on(): return _casa_base() and not load_ws()   # esta cuenta va con el saldo regalo (no tiene clave propia conectada)
def _regalo_mes(p):   # 4 → 0,50 · 5 → 0,50 · 6 → 1 · 19 → 2 · 49 → 5 · 296 al año → 2,50
    try: p = float(p)
    except (TypeError, ValueError): p = 4.0
    if p <= 0: return 0.0
    if p >= 100: p /= 12   # plan anual
    return math.ceil(round(p * 0.1 / 0.5, 6)) * 0.5
def _mon_fp(): return os.path.join(casa(), 'monedero.json')   # en la casa de la cuenta, fuera de assets/: no se sirve
def _mon_guarda(m):
    fp = _mon_fp(); os.makedirs(os.path.dirname(fp), mode=0o700, exist_ok=True)
    with os.fdopen(os.open(fp + '.tmp', os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), 'w') as f: json.dump(m, f, ensure_ascii=False)
    os.replace(fp + '.tmp', fp)
def _mon_lee():   # SIEMPRE con _cerrojo('mon') cogido. Da la bienvenida la primera vez y repone al cambiar de mes
    try: m = json.load(open(_mon_fp(), encoding='utf-8'))
    except Exception: m = {}
    if not isinstance(m, dict): m = {}
    mes = time.strftime('%Y-%m', time.gmtime()); cambia = False
    if 'bienvenida' not in m: m.update({'bienvenida': BIENVENIDA, 'alta': int(time.time())}); cambia = True
    p = _precio.get(uid(), m.get('precio', 4.0))
    if m.get('mes') != mes: r = _regalo_mes(p); m.update({'mes': mes, 'precio': p, 'mensual': r, 'resto': r}); cambia = True   # lo del mes pasado no se acumula
    elif p != m.get('precio'):   # ha cambiado de plan a mitad de mes: su regalo del mes pasa a ser el del plan nuevo, descontando lo ya gastado
        r = _regalo_mes(p); gastado = float(m.get('mensual', 0)) - float(m.get('resto', 0)); m.update({'precio': p, 'mensual': r, 'resto': max(0.0, round(r - gastado, 4))}); cambia = True
    if cambia: _mon_guarda(m)
    return m
def _casa_en_curso():   # lo que está generándose ahora mismo con la clave de la casa y aún no se ha cobrado: cuenta como gastado
    u = uid(); ahora = time.time()
    return sum(float(j.get('usd') or 0) for j in list(jobs.values()) if j.get('casa') and j.get('owner') == u and not j.get('cobrado') and not j.get('failed') and ahora - float(j.get('t0') or 0) < 3 * 3600)
_casa_l = threading.Lock()
def _casa_global(usd=0):   # lo gastado este mes con la clave de la casa entre todas las cuentas ($DATOS/casa.json)
    fp = os.path.join(DATOS, 'casa.json'); mes = time.strftime('%Y-%m', time.gmtime())
    with _casa_l:
        try: g = json.load(open(fp))
        except Exception: g = {}
        if not isinstance(g, dict) or g.get('mes') != mes: g = {'mes': mes, 'usd': 0.0, 'n': 0}
        if usd:
            g['usd'] = round(float(g.get('usd') or 0) + usd, 4); g['n'] = int(g.get('n') or 0) + 1
            with open(fp + '.tmp', 'w') as f: json.dump(g, f)
            os.replace(fp + '.tmp', fp)
        return float(g.get('usd') or 0)
def casa_info():   # el monedero tal como lo ve la web; None si la cuenta no va con el saldo regalo
    if not casa_on(): return None
    with _cerrojo('mon'): m = _mon_lee()
    saldo = max(0.0, round(float(m['resto']) + float(m['bienvenida']) - _casa_en_curso(), 4)); p = WS_MODELS[CASA_DEF]['usd']['std']
    return {'saldo': saldo, 'mensual': m['mensual'], 'resto': m['resto'], 'bienvenida': m['bienvenida'], 'mes': m['mes'], 'imagen': p, 'imagenes': int((saldo + 1e-6) // p), 'modelos': list(CASA_MODELOS), 'pausa': _casa_global() >= CASA_TOPE}
def casa_puede(usd):   # ¿llega el saldo regalo para esto? Si no, error claro
    if _casa_global() >= CASA_TOPE: plog(f'🎁 TOPE GLOBAL del saldo regalo alcanzado ({CASA_TOPE} $ este mes)'); raise RuntimeError('El saldo regalo está en pausa unos días. Mientras tanto puedes generar con tu propia clave en «API en vivo».')
    c = casa_info()
    if not c: raise RuntimeError('WaveSpeed no está conectado: conéctalo en «API en vivo»')
    if c['saldo'] + 1e-6 >= usd: return
    raise RuntimeError(SIN_SALDO if c['saldo'] < c['imagen'] else f"Tu saldo regalo (${c['saldo']:.2f}) no llega para esta imagen (${usd:.3f}). Prueba con {WS_MODELS[CASA_DEF]['name']} o conecta tu propia clave en «API en vivo».")
def casa_cobra(usd, que, rid=None, modelo=None):   # descuenta del monedero (primero lo del mes, que caduca; luego la bienvenida) y lo apunta en su historial
    usd = round(float(usd or 0), 4)
    if usd <= 0: return
    with _cerrojo('mon'):
        m = _mon_lee(); H = m.setdefault('hist', [])
        if rid and any(h.get('rid') == rid for h in H): return   # ese trabajo ya se cobró
        a = min(float(m['resto']), usd); m['resto'] = round(float(m['resto']) - a, 4); m['bienvenida'] = round(max(0.0, float(m['bienvenida']) - (usd - a)), 4)
        hoy = time.strftime('%Y-%m-%d', time.gmtime())
        if not rid and H and H[-1].get('que') == que and H[-1].get('dia') == hoy: H[-1]['usd'] = round(H[-1]['usd'] + usd, 4); H[-1]['n'] = H[-1].get('n', 1) + 1; H[-1]['t'] = int(time.time())   # las lecturas del día van en una sola línea
        else: H.append({'t': int(time.time()), 'dia': hoy, 'usd': usd, 'que': que, **({'rid': rid} if rid else {}), **({'modelo': modelo} if modelo else {})})
        m['hist'] = H[-400:]; _mon_guarda(m)
    _casa_global(usd)
def _casa_puerta(path):   # qué se puede pedir a WaveSpeed con la clave de la casa (solo POST): subir referencias, leer imágenes (se cobra) y generar con los modelos permitidos y con permiso
    if '/media/upload' in path: return
    if '/any-llm' in path: casa_puede(LECTURA_USD); casa_cobra(LECTURA_USD, 'lectura'); return
    if getattr(_ctx, 'casa_ok', False) and any(path == '/api/v3/' + WS_MODELS[k]['ep'] for k in CASA_MODELOS): return
    raise RuntimeError('Esto no entra en el saldo regalo: conecta tu propia clave en «API en vivo».')
def ws(method, path, body=None, raw=None, ctype=None):
    modo = getattr(_ctx, 'ws_modo', None); k = '' if modo == 'casa' else load_ws()   # ws_modo: un trabajo se consulta con la misma clave con la que se lanzó
    if not k and modo != 'propia' and _casa_base():
        k = CASA_KEY
        if method == 'POST': _casa_puerta(path)
    if not k: raise RuntimeError('WaveSpeed no está conectado: conéctalo en «API en vivo»' if SERVIDOR else 'falta WS_API_KEY en ~/.claude/wavespeed.env')
    req = urllib.request.Request('https://api.wavespeed.ai' + path, data=raw if raw is not None else (json.dumps(body).encode() if body is not None else None), method=method)
    req.add_header('Authorization', 'Bearer ' + k); req.add_header('Content-Type', ctype or 'application/json'); req.add_header('User-Agent', UA)
    try:
        with urllib.request.urlopen(req, timeout=180) as r: res = json.loads(r.read() or b'{}')
        if method == 'POST' and '/any-llm' in path: _lectura_apunta()
        return res
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'WaveSpeed {method} {path} → {e.code}: {e.read().decode()[:300]}')
_ws_uploads = {}   # (cuenta, sha1) → URL: lo subido con la clave de una cuenta no lo reutiliza otra
def img_norm(data, ctype='image/jpeg', crop=None):   # AVIF/HEIC/TIFF… → JPEG (Seedream y otros rechazan esos formatos); crop=[x0,y0,x1,y1] en fracciones recorta una vista de una ficha
    ok = data[:3] == b'\xff\xd8\xff' or data[:8] == b'\x89PNG\r\n\x1a\n' or (data[:4] == b'RIFF' and data[8:12] == b'WEBP')
    if ok and not crop: return data, ctype if ctype in ('image/jpeg', 'image/png', 'image/webp') else ('image/png' if data[:4] == b'\x89PNG' else 'image/webp' if data[:4] == b'RIFF' else 'image/jpeg')
    import io
    from PIL import Image
    im = Image.open(io.BytesIO(data)).convert('RGB')
    if crop:
        W, H = im.size; x0, y0, x1, y1 = [float(v) for v in crop]; im = im.crop((int(x0 * W), int(y0 * H), int(x1 * W), int(y1 * H)))
    b = io.BytesIO(); im.save(b, 'JPEG', quality=93); return b.getvalue(), 'image/jpeg'
def img_bytes(img):   # {data:dataURL} o {path:'assets/…'} (+ crop opcional) → (bytes, ctype) listos para subir
    if 'data' in img:
        head, b64 = img['data'].split(',', 1); ctype = head.split(':')[1].split(';')[0]; data = base64.b64decode(b64)
    else:
        p = busca(img.get('path'))   # solo la casa de la cuenta o la biblioteca común
        if not p: raise RuntimeError('ruta no válida: ' + str(img.get('path', ''))[:200])
        data = open(p, 'rb').read(); ctype = mimetypes.guess_type(p)[0] or 'image/jpeg'
    if not ctype.startswith('image/'): return data, ctype
    return img_norm(data, ctype, img.get('crop'))
def ws_upload(data, ctype):
    h = (uid(), hashlib.sha1(data).hexdigest())
    if h in _ws_uploads: return _ws_uploads[h]
    if len(_ws_uploads) > 4000: _ws_uploads.clear()
    ext = {'image/png': 'png', 'image/webp': 'webp', 'video/mp4': 'mp4', 'video/quicktime': 'mov', 'video/webm': 'webm', 'audio/mpeg': 'mp3', 'audio/wav': 'wav', 'audio/x-wav': 'wav', 'audio/mp4': 'm4a', 'audio/x-m4a': 'm4a'}.get(ctype, 'jpg')
    raw = b'--WSB\r\nContent-Disposition: form-data; name="file"; filename="a.' + ext.encode() + b'"\r\nContent-Type: ' + ctype.encode() + b'\r\n\r\n' + data + b'\r\n--WSB--\r\n'
    u = ws('POST', '/api/v3/media/upload/binary', raw=raw, ctype='multipart/form-data; boundary=WSB')
    _ws_uploads[h] = u['data']['download_url']; return _ws_uploads[h]
def resolve_ws(img):
    data, ctype = img_bytes(img); return ws_upload(data, ctype)
def by_kind(refs, kind): return [r for r in refs if (r.get('kind') or 'image') == kind]
MODELS = {   # precios = /estimate de Higgsfield a 3:4 (3 oct 2026): 'usd' = con UNA referencia; 'per' = recargo por cada referencia más
    'mstudio':  {'ep': 'marketing-studio/image',      'name': 'Marketing Studio Image 2.0', 'refs': 16, 'usd': {'std': 0.063, 'high': 0.181}, 'per': 0.013, 'body': _mstu, 'nota': 'de Higgsfield; hasta 16 referencias; el mejor con prendas y combinaciones', 'high': 'calidad alta'},
    'qwen':     {'ep': 'alibaba/qwen-image-3/edit',   'name': 'Qwen Image 3 · Higgsfield',  'refs': 3,  'usd': {'std': 0.040, 'high': 0.075}, 'per': 0,     'body': _qwen, 'nota': 'edición fiel con 1-3 referencias (el más fiel a Aria)', 'high': '2k'},
    'grok':     {'ep': 'xai/grok-imagine-image-2.0',  'name': 'Grok Image 2.0',             'refs': 10, 'usd': {'std': 0.070, 'high': 0.090}, 'per': 0.010, 'body': _grok, 'nota': 'hasta 10 referencias; algo más «retocado»', 'high': '2k'},
}
UNAVAILABLE = [   # lo que Max usa a diario y la API pública de Higgsfield NO ofrece (sondeado el 23 sep 2026)
    {'key': 'nano-banana-pro', 'name': 'Nano Banana Pro',  'why': 'próximamente'},
    {'key': 'gpt-image-2.5',   'name': 'GPT Image 2.5',    'why': 'próximamente'},
    {'key': 'seedream-5',      'name': 'Seedream 5',       'why': 'próximamente'},
]
def all_models(): return dict((MODELS if _hf_listo() else {}), **(WS_MODELS if load_ws() else ({k: WS_MODELS[k] for k in CASA_MODELOS} if casa_on() else {})))   # solo los modelos de los proveedores con clave
def model_list(): return [{'key': k, 'name': m['name'], 'ep': m['ep'], 'refs': m['refs'], 'usd': m['usd'], 'per': m.get('per', 0), 'nota': m['nota'], 'high': m['high'], 'std': m.get('std', '1k'), 'prov': m.get('prov', 'hf')} for k, m in all_models().items()]
def unavailable(): return [] if load_ws() else UNAVAILABLE
UA = 'aria-mirror/1.0 (puente local; +https://higgsfield.ai)'   # Cloudflare devuelve 403 «error code: 1010» al User-Agent por defecto de Python
if not SERVIDOR:   # en local las carpetas de siempre existen desde el arranque; en servidor cada cuenta crea las suyas la primera vez (live_dir(), video_dir(), pers_dir(), refs_dir())
    for _d in ('live', 'video', 'personajes', 'refs'): os.makedirs(os.path.join(RAIZ, 'assets', _d), exist_ok=True)
# vídeo (docs pegadas por Max el 23 sep + dash.higgsfield.ai/models/<id>/llms.txt): precio por tokens = ceil(seg × ancho × alto × 24 / 1024); $0.014 / 1000 tokens (4K $0.008)
VIDEO_MODELS = {
    'i2v': {'ep': 'bytedance/seedance-2.0/image-to-video',     'name': 'Seedance 2.0 · imagen → vídeo'},
    'r2v': {'ep': 'bytedance/seedance-2.0/reference-to-video', 'name': 'Seedance 2.0 · con referencias (ficha 360)'},
}
V_ASPECTS = ['3:4', '9:16', '16:9', '1:1', '4:3', '21:9']

def load_key(): return _env('HF_API_KEY', 'higgsfield.env')
def _hf_listo(): k = load_key(); return bool(k and ':' in k)   # ya no hay una KEY global: cada llamada mira la clave de la cuenta que la hace

# ---- ByteDance directo (BytePlus ModelArk): clave en ~/.claude/byteplus.env como ARK_API_KEY=ark-… (la misma cuenta de «Seedance Local»)
ARK_MODELS = {'2.0': 'dreamina-seedance-2-0-260128', '2.5': 'dreamina-seedance-2-5-260628'}
ARK_USD = {'2.0': {'480p': 0.07, '720p': 0.15, '1080p': 0.30, '4k': 0.78}, '2.5': {'480p': 0.10, '720p': 0.23, '1080p': 0.57}}   # $/segundo aprox. (docs BytePlus, ago 2026)
def load_ark():
    fp = os.path.expanduser('~/.claude/byteplus.env'); b = 'https://ark.ap-southeast.bytepluses.com'
    if SERVIDOR: return _env('ARK_API_KEY', 'byteplus.env'), (os.environ.get('ARK_BASE') or b)   # en servidor no se lee ~/.claude; la dirección la fija quien despliega (nunca la cuenta)
    if os.path.exists(fp):
        for line in open(fp):
            if line.startswith('ARK_BASE='): b = line.strip().split('=', 1)[1].strip()
    return _env('ARK_API_KEY', 'byteplus.env'), b
def ark(method, path, body=None):
    k, b = load_ark()
    if not k: raise RuntimeError('BytePlus no está conectado: conéctalo en «API en vivo»' if SERVIDOR else 'falta ARK_API_KEY en ~/.claude/byteplus.env')
    req = urllib.request.Request(b + path, data=json.dumps(body).encode() if body is not None else None, method=method)
    req.add_header('Authorization', 'Bearer ' + k); req.add_header('Content-Type', 'application/json'); req.add_header('User-Agent', UA)
    try:
        with urllib.request.urlopen(req, timeout=180) as r: return json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        txt = e.read().decode()[:300]
        if 'PrivacyInformation' in txt or 'real person' in txt: raise RuntimeError('ByteDance rechaza la imagen: su filtro anti-deepfake cree que es una persona real (pasa con todas las fotos realistas de Aria). Usa Higgsfield como proveedor para este vídeo.')
        raise RuntimeError(f'ByteDance {method} {path} → {e.code}: {txt}')
def data_uri(img):   # BytePlus acepta base64 → no hace falta subir nada a Higgsfield
    data, ctype = img_bytes(img)
    return 'data:' + ctype + ';base64,' + base64.b64encode(data).decode()
def api(method, path, body=None):
    k = load_key()   # se relee en cada llamada: cambiar la clave no exige reiniciar (y en servidor es la de la cuenta que llama)
    if not k: raise RuntimeError('Higgsfield no está conectado: conéctalo en «API en vivo»')
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode() if body is not None else None, method=method)
    req.add_header('Authorization', 'Key ' + k); req.add_header('Content-Type', 'application/json'); req.add_header('User-Agent', UA)
    try:
        with urllib.request.urlopen(req, timeout=180) as r: return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'{method} {path} → {e.code}: {e.read().decode()[:300]}')

_uploads = {}   # (cuenta, sha1) → (public_url, ts)  (las URL prefirmadas caducan en 1 h)
def upload_bytes(data, ctype):
    h = (uid(), hashlib.sha1(data).hexdigest())
    if h in _uploads and time.time() - _uploads[h][1] < 3000: return _uploads[h][0]
    if len(_uploads) > 4000: _uploads.clear()
    u = api('POST', '/files/generate-upload-url', {'content_type': ctype})
    req = urllib.request.Request(u['upload_url'], data=data, method='PUT')
    for k, v in (u.get('upload_headers') or {}).items(): req.add_header(k, v)
    req.add_header('User-Agent', UA)
    with urllib.request.urlopen(req, timeout=300) as r: r.read()
    _uploads[h] = (u['public_url'], time.time()); return u['public_url']

def resolve_image(img):
    data, ctype = img_bytes(img); return upload_bytes(data, ctype if ctype.startswith('image/') else 'image/jpeg')

JOBS_LOG = os.path.join(DATOS or RAIZ, 'jobs.jsonl') if SERVIDOR else os.path.join(ROOT, 'assets', 'jobs.jsonl')
class _Jobs(dict):   # cada trabajo se apunta en disco al crearse: un reinicio del puente ya no pierde generaciones pagadas
    def __setitem__(self, k, v):
        if isinstance(v, dict): v.setdefault('owner', uid())   # de quién es (None en local): solo su cuenta lo ve, lo cancela y lo recoge
        super().__setitem__(k, v)
        try:
            with open(JOBS_LOG, 'a') as f: f.write(json.dumps({'rid': k, 'job': v}, ensure_ascii=False, default=str) + '\n')
        except Exception: pass
def _job_done(rid):   # terminado (descargado o fallado): ya no hay que recuperarlo
    try:
        with open(JOBS_LOG, 'a') as f: f.write(json.dumps({'rid': rid, 'done': True}) + '\n')
    except Exception: pass
def _jobs_restore(hours=2):   # al arrancar: vuelven los trabajos lanzados en las últimas horas que no llegaron a descargarse
    try:
        if not os.path.exists(JOBS_LOG): return
        seen, done = {}, set()
        for line in open(JOBS_LOG):
            try: r = json.loads(line)
            except Exception: continue
            if r.get('done'): done.add(r.get('rid'))
            elif r.get('job'): seen[r.get('rid')] = r['job']
        vivos = {rid: j for rid, j in seen.items() if rid and rid not in done and time.time() - float(j.get('t0') or 0) < hours * 3600}
        if SERVIDOR: vivos = {rid: j for rid, j in vivos.items() if isinstance(j.get('owner'), str) and _UUID.fullmatch(j['owner'])}   # un trabajo sin dueño no es de nadie
        for rid, j in vivos.items(): dict.__setitem__(jobs, rid, j)
        with open(JOBS_LOG + '.tmp', 'w') as f:   # el registro se queda solo con lo que sigue vivo
            for rid, j in vivos.items(): f.write(json.dumps({'rid': rid, 'job': j}, ensure_ascii=False, default=str) + '\n')
        os.replace(JOBS_LOG + '.tmp', JOBS_LOG)
        if vivos: plog(f'{len(vivos)} trabajo(s) recuperados tras reiniciar el puente')
    except Exception as e: plog('jobs_restore ✕ ' + str(e))
jobs = _Jobs()
_ERR_N = {}   # errores de página recibidos por cuenta en la última hora (tope)
_PPL_F = os.path.join(DATOS or RAIZ, 'personas_cache.json')   # personas ya detectadas en cada imagen: la misma foto no se vuelve a leer (ni a pagar)
try: _PPL = json.load(open(_PPL_F, encoding='utf-8'))
except Exception: _PPL = {}
def _ppl_key(img):   # la Fototeca es la misma para todos; lo demás, de cada cuenta
    p = str((img or {}).get('path') or '').split('?')[0]
    if not p.startswith('assets/') or '..' in p: return None
    return p if p.startswith('assets/biblio/') else (uid() or '') + '|' + p
def _ppl_save():
    try:
        while len(_PPL) > 3000: _PPL.pop(next(iter(_PPL)))
        with open(_PPL_F + '.tmp', 'w', encoding='utf-8') as fh: json.dump(_PPL, fh, ensure_ascii=False)
        os.replace(_PPL_F + '.tmp', _PPL_F)
    except Exception: pass
def _mio(rid):   # el trabajo, solo si es de quien pregunta (en local todos son del único usuario)
    j = jobs.get(rid) if isinstance(rid, str) else None
    return j if j and j.get('owner') == uid() else None
_cache = {}
def plog(msg):
    try:
        if SERVIDOR: open(os.path.join(DATOS, 'puente.log'), 'a').write(time.strftime('%Y-%m-%d %H:%M:%S ') + (uid() or '-')[:8] + ' ' + str(msg)[:600].replace('\n', ' ').replace('\r', ' ') + '\n')   # un solo registro, fuera de las casas, con la cuenta delante
        else: open(os.path.join(ROOT, 'assets', 'puente.log'), 'a').write(time.strftime('%Y-%m-%d %H:%M:%S ') + str(msg)[:600] + '\n')
    except Exception: pass
def save_inputs(body):   # capturas e imágenes de internet (llegan como dataURL): copia en assets/refs/<sha1>.<ext> para poder verlas y recrear después
    try:
        if not isinstance(body.get('meta'), dict): body['meta'] = {}
        meta = body['meta']
        for i, im in enumerate(body.get('images') or []):
            du = im.get('data') if isinstance(im, dict) else None
            if not du or ',' not in du:
                p = str(im.get('path') or '').split('?')[0] if isinstance(im, dict) else ''
                if i == 0 and p.startswith('assets/refs/'): meta['canvasRef'] = p   # se recrea desde una imagen ya guardada: «Recrear» la vuelve a poner como imagen de partida
                continue
            head, b64 = du.split(',', 1); raw, ct = img_norm(base64.b64decode(b64), head.split(':')[1].split(';')[0])
            ext = 'png' if ct == 'image/png' else 'webp' if ct == 'image/webp' else 'jpg'
            rel = f"assets/refs/{hashlib.sha1(raw).hexdigest()[:16]}.{ext}"; full = os.path.join(refs_dir(), os.path.basename(rel))
            if not os.path.exists(full): open(full, 'wb').write(raw)
            if i == 0: meta['canvasRef'] = rel
            meta.setdefault('refFiles', []).append(rel)
    except Exception as e: plog('guardar referencias ✕ ' + str(e))
def write_meta(j, rel, rid, st):   # sidecar <archivo>.json con lo que Max quiere ver en «Mis creaciones»
    try:
        meta = dict(j.get('meta') or {})
        try:
            from PIL import Image; meta['width'], meta['height'] = Image.open(os.path.join(casa(), rel)).size
        except Exception: pass
        meta.update({'file': rel, 'kind': j.get('kind', 'image'), 'request_id': rid, 'usd': j.get('usd'), 'credits': j.get('credits'), 'ms': int((time.time() - j['t0']) * 1000), 't': time.time(), 'model_key': j.get('model')})
        json.dump(meta, open(os.path.join(casa(), rel) + '.json', 'w'), ensure_ascii=False, indent=1)
    except Exception: pass
def _seam_x(im):
    from PIL import ImageStat
    g = im.convert('L'); w, h = g.size; best = None
    bs = 99
    for x in range(int(w * 0.44), int(w * 0.66)):   # costura clara u oscura entre el panel frontal y las vistas pequeñas
        sd = ImageStat.Stat(g.crop((x, int(h * 0.05), x + 1, int(h * 0.95)))).stddev[0]
        if sd < 8 and (best is None or sd < bs - 1 or (abs(sd - bs) <= 1 and abs(x - w * 0.57) < abs(best - w * 0.57))): best = x; bs = sd
    return best
def card_from(ficha_path, card_path):   # misma lógica que recortar_cards.py: vista principal (izquierda) recortada a 2:3
    from PIL import Image
    im = Image.open(ficha_path).convert('RGB'); w, h = im.size; x = _seam_x(im)
    if x and x > w * 0.3: src = im.crop((0, 0, max(1, x - 2), h))
    elif w / h > 0.72: src = im.crop((0, 0, int(w * 0.555), h))
    else: src = im.crop((0, 0, int(w * 0.62), h))   # ficha 9:16 de 4 paneles: la vista frontal ocupa el 60 % izquierdo
    from PIL import ImageStat
    sw, sh = src.size; tw = sh // 2   # card 1:2: panel entero en vertical; lados recortados o rellenados con el color del borde
    if sw > tw + 2: x0 = (sw - tw) // 2; src = src.crop((x0, 0, x0 + tw, sh))
    elif sw < tw - 2:
        l = ImageStat.Stat(src.crop((0, 0, 4, sh))).mean; r = ImageStat.Stat(src.crop((sw - 4, 0, sw, sh))).mean; col = tuple(int((a + b) / 2) for a, b in zip(l, r))
        cv = Image.new('RGB', (tw, sh), col); cv.paste(src, ((tw - sw) // 2, 0)); src = cv
    src.resize((480, 960), Image.LANCZOS).save(card_path, quality=88)
def add_prenda(j, live_path):
    with _cerrojo(): return _add_prenda(j, live_path)
def _add_prenda(j, live_path):   # la ficha generada pasa a assets/vestidor/n<num>_ficha.jpg + card, y entra en catalog.js / catalog.json
    import shutil
    head, C = _cat_load()
    rep = (j.get('meta') or {}).get('replaces'); old = next((v for v in C['vestidor'] if v['id'] == rep), None) if rep else None
    if old: return _replace_prenda(j, live_path, C, head, old)
    num = max([int(v.get('num') or 0) for v in C['vestidor']] + [100000 if SERVIDOR else 0]) + 1   # en servidor las prendas propias empiezan en 100001: nunca chocan con las que lleguen a la biblioteca común
    vd, vr = mio('vestidor'); ficha = os.path.join(vd, f'n{num}_ficha.jpg'); card = os.path.join(vd, f'n{num}_card.jpg')
    from PIL import Image; Image.open(live_path).convert('RGB').save(ficha, quality=92); card_from(ficha, card)
    nm = (j.get('meta') or {}).get('name') or ''
    if not nm or re.match(r'Prenda Nº \d+$', nm): nm = f'Prenda Nº {num}'   # el número real lo pone el puente (evita choques en lotes)
    item = {'id': f'n{num}', 'name': nm, 'num': num, 'tags': list((j.get('meta') or {}).get('tags') or []), 'date': time.strftime('%Y-%m-%d'), 'card': f'{vr}n{num}_card.jpg', 'ficha': f'{vr}n{num}_ficha.jpg', 'looks': []}
    if (j.get('meta') or {}).get('parent'): item['parent'] = j['meta']['parent']   # variación de color de otra prenda
    C['vestidor'].append(item)
    _cat_save(head, C)
    meta = dict(j.get('meta') or {}); meta['name'] = item['name']; meta.update({'file': item['ficha'], 'kind': 'image', 'usd': j.get('usd'), 't': time.time(), 'model_key': j.get('model'), 'prenda': True, 'num': num})
    json.dump(meta, open(ficha + '.json', 'w'), ensure_ascii=False, indent=1)
    for extra in ('', '.json'):
        if os.path.exists(live_path + extra): os.remove(live_path + extra)
    plog(f'prenda nueva n{num} «{item["name"]}»')
    if SERVIDOR: return item   # Notion es solo del ordenador de Max
    try:   # también a la base Vestidor Virtual de Notion (mismo formato que las 425), en segundo plano
        import subprocess, threading
        def _up():
            r = subprocess.run([sys.executable, '/Users/maxromanenko/Desktop/XXX/.claude/scripts/aria_mirror/subir_prenda_notion.py', str(num), ficha, '--tags', json.dumps(item['tags'])], capture_output=True, text=True, timeout=300)
            if r.returncode == 0:
                try: meta2 = json.load(open(ficha + '.json')); meta2['notion'] = json.loads(r.stdout.strip().splitlines()[-1]); json.dump(meta2, open(ficha + '.json', 'w'), ensure_ascii=False, indent=1)
                except Exception: pass
                plog(f'prenda n{num} subida a Notion · ' + r.stdout.strip()[:120])
            else: plog(f'prenda n{num} Notion ✕ ' + (r.stderr or r.stdout)[-300:])
        threading.Thread(target=_up, daemon=True).start()
    except Exception as e: plog('prenda Notion ✕ ' + str(e))
    return item
def _replace_prenda(j, live_path, C, head, old):   # «Regenerar»: la ficha nueva ocupa el sitio de la antigua (mismo número, nombre, etiquetas y variaciones); la antigua va a la papelera y su página de Notion se sustituye
    import shutil
    from PIL import Image
    vd, vr = mio('vestidor')
    if SERVIDOR and old.get('id') in (getattr(_ctx, 'comun', None) or _comun())['ids']['vestidor']:   # prenda de la biblioteca común: NO se toca. Para esta cuenta se oculta y la nueva entra como propia, con su nombre, etiquetas y variaciones
        num = max([int(v.get('num') or 0) for v in C['vestidor']] + [100000]) + 1; ficha = os.path.join(vd, f'n{num}_ficha.jpg'); card = os.path.join(vd, f'n{num}_card.jpg')
        Image.open(live_path).convert('RGB').save(ficha, quality=92); card_from(ficha, card)
        item = {'id': f'n{num}', 'name': old.get('name') or f'Prenda Nº {num}', 'num': num, 'tags': list(old.get('tags') or []), 'date': time.strftime('%Y-%m-%d'), 'card': f'{vr}n{num}_card.jpg', 'ficha': f'{vr}n{num}_ficha.jpg', 'looks': [], 'sustituye': old['id']}
        if old.get('parent'): item['parent'] = old['parent']
        if old.get('fav'): item['fav'] = True
        for v in C['vestidor']:
            if v.get('parent') == old['id']: v['parent'] = item['id']
        C['vestidor'] = [v for v in C['vestidor'] if v['id'] != old['id']] + [item]; _cat_save(head, C)
        meta = dict(j.get('meta') or {}); meta['name'] = item['name']; meta.update({'file': item['ficha'], 'kind': 'image', 'usd': j.get('usd'), 't': time.time(), 'model_key': j.get('model'), 'prenda': True, 'num': num, 'regenerada': True})
        json.dump(meta, open(ficha + '.json', 'w'), ensure_ascii=False, indent=1)
        for extra in ('', '.json'):
            if os.path.exists(live_path + extra): os.remove(live_path + extra)
        plog(f'prenda {old["id"]} (común) regenerada como propia n{num}'); return item
    num = int(old['num']); ficha = os.path.join(vd, f'n{num}_ficha.jpg'); card = os.path.join(vd, f'n{num}_card.jpg')
    trash = papelera(); stamp = str(int(time.time())); old_notion = None
    try: old_notion = (json.load(open(ficha + '.json')).get('notion') or {}).get('page_id')
    except Exception: pass
    for f in (ficha, card, ficha + '.json'):
        if os.path.exists(f): shutil.move(f, os.path.join(trash, os.path.basename(f).replace('.jpg', f'_antes_{stamp}.jpg')))
    Image.open(live_path).convert('RGB').save(ficha, quality=92); card_from(ficha, card)
    v = f'?v={stamp}'; old['card'] = f'{vr}n{num}_card.jpg{v}'; old['ficha'] = f'{vr}n{num}_ficha.jpg{v}'
    _cat_save(head, C)
    meta = dict(j.get('meta') or {}); meta['name'] = old['name']; meta.update({'file': f'{vr}n{num}_ficha.jpg', 'kind': 'image', 'usd': j.get('usd'), 't': time.time(), 'model_key': j.get('model'), 'prenda': True, 'num': num, 'regenerada': True})
    json.dump(meta, open(ficha + '.json', 'w'), ensure_ascii=False, indent=1)
    for extra in ('', '.json'):
        if os.path.exists(live_path + extra): os.remove(live_path + extra)
    plog(f'prenda n{num} regenerada en su sitio')
    if SERVIDOR: return old   # Notion es solo del ordenador de Max
    try:
        import subprocess, threading
        def _up():
            if old_notion: subprocess.run([sys.executable, '/Users/maxromanenko/Desktop/XXX/.claude/scripts/aria_mirror/archivar_prenda_notion.py', str(num), old_notion], capture_output=True, text=True, timeout=120)
            r = subprocess.run([sys.executable, '/Users/maxromanenko/Desktop/XXX/.claude/scripts/aria_mirror/subir_prenda_notion.py', str(num), ficha, '--tags', json.dumps(old.get('tags') or [])], capture_output=True, text=True, timeout=300)
            if r.returncode == 0:
                try: m2 = json.load(open(ficha + '.json')); m2['notion'] = json.loads(r.stdout.strip().splitlines()[-1]); json.dump(m2, open(ficha + '.json', 'w'), ensure_ascii=False, indent=1)
                except Exception: pass
                plog(f'prenda n{num} regenerada · Notion sustituida')
            else: plog(f'prenda n{num} Notion ✕ ' + (r.stderr or r.stdout)[-300:])
        threading.Thread(target=_up, daemon=True).start()
    except Exception as e: plog('prenda Notion ✕ ' + str(e))
    return old
def _nf_autosave(j):   # «Nueva ficha»: al terminar se guarda sola en Fichas creadas (nada se pierde aunque se cierre la página)
    from PIL import Image
    nf = (j.get('meta') or {}).get('nf') or {}; rel = j.get('file')
    if not rel: return None
    owner = nf.get('owner')
    if not owner and aria_fija(): return None   # una ficha de Aria hecha por otra cuenta se queda en sus creaciones: no entra en la ficha de Aria
    if owner:   # ficha nueva de otro personaje: a su carpeta y a su personaje.json
        if not _pid_ok(owner) or '\\' in owner: return None
        d = os.path.join(pers_dir(), owner); pf = os.path.join(d, 'personaje.json')   # siempre dentro de la casa de la cuenta del trabajo
        if not os.path.isfile(pf): return None
        with _cerrojo():
            PP = json.load(open(pf)); A = PP.setdefault('fichasVers', [])
            if rel not in A: A.insert(0, rel)
            L = PP.setdefault('fichas', []); it = next((f for f in L if f.get('from') == rel), None)
            if not it:
                src = Image.open(os.path.join(casa(), rel)).convert('RGB'); nombre = nf.get('nombre') or 'Ficha nueva'
                fid = re.sub(r'[^a-z0-9]+', '-', nombre.lower()).strip('-')[:40] + '-' + str(int(time.time()))
                d2 = os.path.join(d, 'fichas'); os.makedirs(d2, exist_ok=True); src.save(os.path.join(d2, fid + '.jpg'), quality=92); th = src.copy(); th.thumbnail((900, 900)); th.save(os.path.join(d2, fid + '_t.jpg'), quality=85)
                it = {'id': fid, 'nombre': nombre, 'prendas': nf.get('prendas') or [], 'extras': nf.get('extras') or [], 'acc': nf.get('acc') or [], 'img': f'assets/personajes/{owner}/fichas/{fid}.jpg', 'thumb': f'assets/personajes/{owner}/fichas/{fid}_t.jpg',
                      'from': rel, 't': time.strftime('%Y-%m-%d %H:%M'), 'size': [src.width, src.height], 'modelo': (j.get('meta') or {}).get('model') or ''}
                L.insert(0, it)
            json.dump(PP, open(pf, 'w'), ensure_ascii=False, indent=1)
        plog(f'ficha nueva de {owner} guardada sola · ' + it['nombre']); return it
    with _cerrojo():
        head, C = _cat_load(); P = C['perfil']
        A = P.setdefault('alt', {}).setdefault('nueva', {}).setdefault('combo', [])
        if rel not in A: A.insert(0, rel)
        L = P.setdefault('fichas', []); it = next((f for f in L if f.get('from') == rel), None)
        if not it:
            src = Image.open(os.path.join(casa(), rel)).convert('RGB'); nombre = nf.get('nombre') or 'Ficha nueva'
            fid = re.sub(r'[^a-z0-9]+', '-', nombre.lower()).strip('-')[:40] + '-' + str(int(time.time()))
            d2 = perfil_dir('fichas'); src.save(os.path.join(d2, fid + '.jpg'), quality=92); th = src.copy(); th.thumbnail((900, 900)); th.save(os.path.join(d2, fid + '_t.jpg'), quality=85)
            it = {'id': fid, 'nombre': nombre, 'layout': 'combo', 'prendas': nf.get('prendas') or [], 'extras': nf.get('extras') or [], 'acc': nf.get('acc') or [], 'img': f'assets/perfil/fichas/{fid}.jpg', 'thumb': f'assets/perfil/fichas/{fid}_t.jpg',
                  'from': rel, 't': time.strftime('%Y-%m-%d %H:%M'), 'size': [src.width, src.height], 'modelo': (j.get('meta') or {}).get('model') or ''}
            L.insert(0, it)
        _cat_save(head, C)
    plog('ficha nueva guardada sola · ' + it['nombre']); return it
_ASK_FICHA = ('This image is the character reference sheet of ONE AI influencer: several views of the SAME person (usually front, side profile, three-quarter and back; sometimes also the full body). '
              'Describe THAT person and answer with ONLY a JSON object with these keys and allowed values: '
              '"genero": fem|masc|andro|nb; "edad": apparent age (number); "altura": estimated height in cm (number, 168 if you cannot tell); "cara": oval|redonda|corazon|angulosa|alargada; "ojos": negros|marrones|verdes|azules|grises|ambar|amarillos|violeta; '
              '"ojosForma": caidos|rasgados|almendra|redondos; "labios": finos|medios|carnosos|muy; "nariz": peq|recta|ancha|aguilena; "peloColor": negro|castano|rubio|pelirrojo|rosa|azul|verde (or null); '
              '"peloNombre": Spanish name of the hair color if none of those fits (else null); "peinado_es": short Spanish name of the hairstyle (max 5 words); "peinado_en": one English sentence describing the hairstyle precisely (length, cut, bangs, how it is tied); '
              '"piel": muyclara|clara|media|morena|oscura|ebano; "complexion": menuda|delgada|atletica|media|curvy|musculosa|grande; "pecho": peq|medio|grande|muy (or null for men); "cadera": estrecha|media|ancha|muy; "estilo": realista|cartoon; '
              '"pielDet": array of hoyuelos|tatuajes|cicatriz (only what is clearly visible); '
              '"accesorios": array (max 4) of the accessories the person wears in ALL the views (glasses, earrings, necklace, piercing, hat...), each one as {"tipo": gafas|gafassol|pendientes|collar|reloj|gorra|otro, "nombre": short Spanish name, "desc": precise English description such as "thin round metal glasses", "box_2d": [ymin, xmin, ymax, xmax] = the tight bounding box of that accessory in the view where it is seen biggest and clearest, normalized to 0-1000}; empty array if none; '
              '"layout": "2x2" if the image is a grid of exactly four panels (two rows, two columns), else "otro"; "frontal": [x0, y0, x1, y1] as fractions between 0 and 1 of the image area that contains the FRONT-facing head-and-shoulders view; '
              '"resumen": one short Spanish sentence describing the person.')
def _capa():   # la capa de la cuenta sobre el catálogo común (su casa/capa.json): perfil, lo propio de vestidor/hair/expr, favoritas, lo común que ha ocultado
    try: c = json.load(open(os.path.join(casa(), 'capa.json'), encoding='utf-8'))
    except FileNotFoundError: return {}
    except Exception as e: plog('capa ilegible ✕ ' + str(e)[:120]); raise RuntimeError('la capa de la cuenta está dañada')   # mejor parar que pisarla con una vacía
    return c if isinstance(c, dict) else {}
def _fusion(S, capa):   # lo que ve la cuenta = copia entera del común + su capa encima
    C = json.loads(S['txt'])
    if isinstance(capa.get('perfil'), dict) and not aria_fija(): C['perfil'] = capa['perfil']
    oc = capa.get('ocultos') or {}; fav = set(capa.get('fav') or []); padre = capa.get('padre') or {}
    for k in KINDS:
        fuera = set(oc.get(k) or []); L = [x for x in C.get(k) or [] if x.get('id') not in fuera]
        propios = [x for x in capa.get(k) or [] if isinstance(x, dict) and x.get('id') not in S['ids'][k]]
        if k != 'vestidor': C[k] = propios + L; continue   # peinados y expresiones propios van delante (como al crearlos)
        for v in L:   # favoritas y «variación de…» son de cada cuenta: las del común no cuentan
            v.pop('fav', None)
            if v.get('id') in fav: v['fav'] = True
            if v.get('id') in padre:
                if padre[v['id']]: v['parent'] = padre[v['id']]
                else: v.pop('parent', None)
        C[k] = L + propios
    return C
def _cat_load():   # (cabecera, catálogo): en local, catalog.js de siempre; en servidor, el común + la capa de la cuenta. TODA lectura del catálogo pasa por aquí
    if not SERVIDOR:
        cat = open(os.path.join(ROOT, 'catalog.js')).read(); return cat[:cat.index('{')], json.loads(cat[cat.index('{'):cat.rindex('}') + 1])
    S = _comun(); _ctx.comun = S   # la misma foto del común que usará _cat_save (si cambia entre medias, no se oculta nada por error)
    return 'window.CATALOG = ', _fusion(S, _capa())
def _capa_save(C):   # modo servidor: el catálogo común NO se escribe nunca; se calcula y se guarda la capa de la cuenta
    S = getattr(_ctx, 'comun', None) or _comun(); vieja = _capa(); capa = {'v': 1}
    if not aria_fija() and ('perfil' in vieja or C.get('perfil') != S['perfil']): capa['perfil'] = C.get('perfil') or {}   # el perfil entero, desde el primer cambio
    oc = {}
    for k in KINDS:
        L = [x for x in C.get(k) or [] if isinstance(x, dict)]; ids = S['ids'][k]; hay = {x.get('id') for x in L}
        capa[k] = [x for x in L if x.get('id') not in ids]   # lo propio = lo que no está en el común
        oc[k] = sorted((ids - hay) | {x for x in (vieja.get('ocultos') or {}).get(k) or [] if isinstance(x, str)})   # lo común que esta cuenta ha quitado (o sustituido)
    V = [x for x in C.get('vestidor') or [] if isinstance(x, dict) and x.get('id') in S['ids']['vestidor']]
    capa['ocultos'] = oc; capa['fav'] = [v['id'] for v in V if v.get('fav')]; capa['padre'] = {v['id']: v.get('parent') for v in V if v.get('parent') != S['padre'].get(v['id'])}
    fp = os.path.join(_dir(), 'capa.json'); tmp = f'{fp}.tmp{threading.get_ident()}'
    with os.fdopen(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), 'w', encoding='utf-8') as f: json.dump(capa, f, ensure_ascii=False); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, fp)
def _cat_save(head, C):   # escritura atómica del catálogo (temporal + cambio de golpe) y una copia por día (se guardan 7)
    import shutil
    if SERVIDOR: return _capa_save(C)
    try:
        cd = os.path.join(ROOT, 'assets', 'copias'); os.makedirs(cd, exist_ok=True); hoy = os.path.join(cd, 'catalog-' + time.strftime('%Y-%m-%d') + '.js'); cur = os.path.join(ROOT, 'catalog.js')
        if not os.path.exists(hoy) and os.path.exists(cur) and os.path.getsize(cur) > 1000:
            shutil.copy2(cur, hoy)
            for old in sorted(x for x in os.listdir(cd) if x.startswith('catalog-'))[:-7]: os.remove(os.path.join(cd, old))
    except Exception as e: plog('copia del catálogo ✕ ' + str(e))
    for name, data in (('catalog.js', head + json.dumps(C, ensure_ascii=False) + ';\n'), ('catalog.json', json.dumps(C, ensure_ascii=False))):
        fp = os.path.join(ROOT, name); tmp = fp + '.tmp'
        with open(tmp, 'w') as f: f.write(data); f.flush(); os.fsync(f.fileno())
        os.replace(tmp, fp)
def _safe_item(x):   # el nombre del elemento acaba en el nombre del archivo: nunca puede salirse de su carpeta
    return re.sub(r'[^A-Za-z0-9_.@:-]', '-', str(x or 'img')).strip('.')[:90] or 'img'
_ASK_ESTILO = {   # leer un peinado o una expresión de una foto cualquiera (dos líneas: nombre en español + descripción en inglés)
    'lugar': ('Look ONLY at the PLACE shown in this photo (ignore any person in it). Answer with EXACTLY three lines and nothing else. '
              'Line 1: a short name for the place in Spanish, 2-4 words (e.g. "Cocina luminosa", "Despacho de madera", "Azotea al atardecer"). '
              'Line 2: one English sentence, 25-50 words, describing the place so an AI image generator can reproduce it: what kind of place it is, its layout, furniture, materials, colours and light. Never mention people. '
              'Line 3: the single word Interior or Exterior.'),
    'escena': ('Describe this photo so an AI image generator can recreate THE SAME SCENE with a DIFFERENT person. Answer with EXACTLY four lines and nothing else. '
               'Line 1: a short title in Spanish, 2-5 words. '
               'Line 2: one English paragraph, 60-110 words: the place and background, time of day and lighting, camera distance, angle and framing, what she is doing and her exact pose, her expression and mood, props, and the photo style (phone snapshot, studio, film grain...). Start with the framing. Use "she" for the person. '
               'If SEVERAL people appear, use up to 160 words and describe EVERY one of them by position ("the person on the left", "the person in the middle", "the person on the right"): what each one is doing, the exact pose, and how they touch or look at each other; in that case never say whether each one is a man or a woman, always "the person on the ...". '
               'NEVER describe who the person is: no face, no eye color, no hair color or hairstyle, no skin tone, no age, no ethnicity, no body shape, no glasses, no earrings, no jewelry. '
               'If the image is not a real photograph of a real person (a toy, vinyl collectible, doll, figurine, plush, cartoon, 3D render, illustration), describe in Line 2 that medium too: materials, finish, proportions and the look of the whole image. '
               'Line 3: one English phrase, 8-30 words, with ONLY the clothing and shoes she wears (colors, fabrics, fit), never glasses, earrings, jewelry, hats or any other accessory; with several people, up to 60 words: the clothing of each one, by position. '
               'Line 4: the single word REAL if the main figure is a real photographed human; otherwise 3-10 English words naming exactly what kind of figure it is (e.g. "vinyl collectible toy figure with an oversized head", "3D cartoon character", "anime illustration").'),
    'hair': ('Look ONLY at the HAIRSTYLE of the person in this image (ignore the face, the clothes and the background). Answer with EXACTLY two lines and nothing else. '
             'Line 1: a short hairstyle name in Spanish, 2-5 words, like a salon catalog (e.g. "Trenza Francesa Lateral", "Moño Bajo Despeinado"). '
             'Line 2: one precise English sentence, 15-35 words, describing only the hairstyle so an AI image generator can reproduce it: length, cut, parting, bangs, texture and how it is tied or braided. Do not mention the hair color.'),
    'expr': ('Look ONLY at the FACIAL EXPRESSION and GESTURE of the person in this image (ignore who it is, the hair, the clothes and the background). Answer with EXACTLY two lines and nothing else. '
             'Line 1: a short name in Spanish, 2-4 words (e.g. "Guiño cómplice", "Sorpresa total"). '
             'Line 2: one precise English sentence, 15-35 words, describing only the expression and gesture so an AI image generator can reproduce it: eyes, eyebrows, mouth, head tilt, and the hands if they take part. '
             'Line 3: the same description as ONE Spanish sentence that starts with "La persona" and ends with ", fotografía hiperrealista". '
             'Line 4: the category, copied exactly from this list: Alegría & Variantes Positivas | Tristeza & variantes | Enojo & variantes | Miedo & sorpresa | Asco & Rechazo | Expresiones Sociales & de Personalidad | Expresiones Neutras & Cognitivas | Expresiones de Intensidad | Estado Físico | Gestos & Reacciones.'),
}
def _add_estilo(j, live_path):   # peinado o expresión creados soltando una foto en Crear imagen: la imagen pasa a su biblioteca y entra en el catálogo
    import unicodedata
    from PIL import Image
    es = (j.get('meta') or {}).get('estilo') or {}; kind = es.get('kind')
    if kind not in ('hair', 'expr'): return None
    with _cerrojo():
        head, C = _cat_load(); L = C.setdefault(kind, [])
        nombre = (es.get('nombre') or 'Nuevo').strip()[:60]
        base = re.sub(r'[^a-z0-9]+', '-', unicodedata.normalize('NFKD', nombre).encode('ascii', 'ignore').decode().lower()).strip('-') or 'nuevo'; base = ('mio-' + base) if SERVIDOR else base; sid, k = base, 2   # en servidor, id con prefijo: no choca con lo que llegue al común
        while any(x.get('id') == sid for x in L): sid = f'{base}-{k}'; k += 1
        d, dr = mio(kind)
        im = Image.open(live_path).convert('RGB'); im.save(os.path.join(d, sid + '.jpg'), quality=92); th = im.copy(); th.thumbnail((640, 640)); th.save(os.path.join(d, sid + '_t.jpg'), quality=85)
        it = {'id': sid, 'name': nombre, 'desc': es.get('desc') or '', 'files': {'main': f'{dr}{sid}.jpg', 'thumb': f'{dr}{sid}_t.jpg'}, 'date': time.strftime('%Y-%m-%d'), 'propio': True}
        TIPOS = ['Alegría & Variantes Positivas', 'Tristeza & variantes', 'Enojo & variantes', 'Miedo & sorpresa', 'Asco & Rechazo', 'Expresiones Sociales & de Personalidad', 'Expresiones Neutras & Cognitivas', 'Expresiones de Intensidad', 'Estado Físico', 'Gestos & Reacciones']
        if kind == 'hair': it['tags'] = []
        else: it['tipo'] = es.get('tipo') if es.get('tipo') in TIPOS else 'Gestos & Reacciones'
        L.insert(0, it); _cat_save(head, C)
    plog(f'{"peinado" if kind == "hair" else "expresión"} nuevo «{nombre}» ({sid})')
    script = '/Users/maxromanenko/Desktop/XXX/.claude/scripts/aria_mirror/subir_estilo_notion.py'
    if not SERVIDOR and os.path.isfile(script) and os.path.isfile(os.path.expanduser('~/.claude/notion.env')):   # solo en el ordenador de Max: también a su base de Notion, en segundo plano
        import subprocess, threading
        def _up():
            try:
                r = subprocess.run([sys.executable, script, kind, os.path.join(ROOT, it['files']['main']), nombre, it['desc']] + (['--tipo', it['tipo']] if kind == 'expr' else []), capture_output=True, text=True, timeout=300)
                if r.returncode != 0: plog(f'estilo {sid} Notion ✕ ' + (r.stderr or r.stdout)[-300:]); return
                pid = json.loads(r.stdout.strip().splitlines()[-1]).get('page_id')
                with _cerrojo():
                    head, C = _cat_load()
                    x = next((y for y in C.get(kind, []) if y.get('id') == sid), None)
                    if x: x['notion'] = pid; _cat_save(head, C)
                plog(f'estilo {sid} subido a Notion · {pid}')
            except Exception as e: plog(f'estilo {sid} Notion ✕ {e}')
        threading.Thread(target=_up, daemon=True).start()
    return it
APIS = (('ws', 'WaveSpeed', 'WS_API_KEY', 'wavespeed.env', 'Nano Banana Pro, GPT Image, Seedream y Qwen'),
        ('hf', 'Higgsfield', 'HF_API_KEY', 'higgsfield.env', 'Marketing Studio, Grok y Qwen'),
        ('ark', 'BytePlus', 'ARK_API_KEY', 'byteplus.env', 'vídeo con Seedance'))
def _hf_ok(k):   # comprueba una clave de Higgsfield pidiendo un presupuesto (no genera ni cobra nada)
    M = MODELS['qwen']; rq = urllib.request.Request(BASE + '/estimate/' + M['ep'], data=json.dumps(M['body']('a photo', ['https://example.com/a.jpg'], '3:4', 'std')).encode(), method='POST')
    rq.add_header('Authorization', 'Key ' + k); rq.add_header('Content-Type', 'application/json'); rq.add_header('User-Agent', UA); urllib.request.urlopen(rq, timeout=30).read()
def _ark_ok(k):   # comprueba una clave de BytePlus pidiendo su lista de trabajos (no genera ni cobra nada)
    rq = urllib.request.Request(load_ark()[1] + '/api/v3/contents/generations/tasks?page_size=1'); rq.add_header('Authorization', 'Bearer ' + k); rq.add_header('User-Agent', UA)
    urllib.request.urlopen(rq, timeout=30).read()
def _de_quien(k):   # ¿de qué proveedor es esta clave? Se prueba con cada uno; None si ninguno la acepta
    if not re.fullmatch(r'[\x21-\x7e]{16,400}', k): return None
    duda = False
    for aid, prueba in ((('hf', _hf_ok),) if ':' in k else (('ws', _ws_saldo), ('ark', _ark_ok))):
        for intento in (1, 2):   # «no la acepta» (401/403…) es un no; cualquier otro fallo (red, 5xx, tardanza) se reintenta una vez
            try: prueba(k); return aid
            except urllib.error.HTTPError as e:
                if e.code in (400, 401, 403, 404): break
                duda = True
            except Exception: duda = True
    return 'duda' if duda else None
def _apis_estado():   # qué APIs hay conectadas (nunca la clave: solo sus 4 últimos caracteres)
    out = []
    for aid, nombre, envn, homef, para in APIS:
        raw = _env(envn, homef, True); off = bool(raw) and _off(envn); a = {'id': aid, 'nombre': nombre, 'para': para, 'on': bool(raw) and not off, 'off': off, 'fin': raw[-4:] if raw else '', 'saldo': None}
        if aid == 'ws' and a['on']:
            try: a['saldo'] = _ws_saldo(raw)
            except Exception: a['error'] = 'WaveSpeed no acepta la clave guardada'
        out.append(a)
    return out
def _creacion(rel):   # una creación DE LA CUENTA (assets/live o assets/video) → su fichero, o None
    full = busca(rel, propio=True)
    return full if full and (_dentro(live_dir(), full) or _dentro(video_dir(), full)) else None
def poster_for(path):   # fotograma del vídeo para la galería (ffmpeg si está)
    out = os.path.splitext(path)[0] + '.jpg'
    if os.path.exists(out): return out
    try:
        import subprocess, shutil
        if not shutil.which('ffmpeg'): return None   # sin ffmpeg (p. ej. en el servidor) no hay carátula, y no pasa nada
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', '0.5', '-i', path, '-frames:v', '1', '-vf', 'scale=720:-2', out], timeout=60); return out if os.path.exists(out) else None
    except Exception: return None
def _mini_make(names, u=None):   # miniaturas de las creaciones (560 px) en segundo plano: la galería deja de cargar los originales enteros (hilo aparte → se le dice de qué cuenta)
    with como(u):
        busy = _cerrojo('mini')
        if not busy.acquire(blocking=False): return
        try:
            from PIL import Image
            ld, md = live_dir(), mini_dir(); os.makedirs(md, exist_ok=True)
            for fn in names:
                try:
                    src = os.path.join(ld, fn); dst = os.path.join(md, fn + '.jpg')
                    if os.path.exists(dst) or not os.path.exists(src): continue
                    im = Image.open(src).convert('RGB'); im.thumbnail((560, 560)); im.save(dst + '.tmp', 'JPEG', quality=80); os.replace(dst + '.tmp', dst)
                except Exception: pass
        finally: busy.release()
def creations():   # todo lo generado por la API, lo más nuevo primero, con su sidecar
    out = []; faltan = []; md = mini_dir()
    for d, kind, exts in ((live_dir(), 'image', ('.png', '.jpg', '.jpeg', '.webp')), (video_dir(), 'video', ('.mp4', '.mov', '.webm'))):
        for fn in os.listdir(d):
            if fn.startswith('.') or not fn.lower().endswith(exts) or os.path.splitext(fn)[0].endswith('_lo'): continue
            full = os.path.join(d, fn); rel = f"assets/{'live' if kind == 'image' else 'video'}/{fn}"; meta = {}
            if os.path.exists(full + '.json'):
                try: meta = json.load(open(full + '.json'))
                except Exception: meta = {}
            if not meta:
                base = os.path.splitext(fn)[0]
                if kind == 'video': meta = {'item': base.split('__')[0], 'source': 'assets/live/' + base.split('__')[0] + '.png', 'model_key': 'i2v', 'sin_ficha': True}
                else:
                    m = re.match(r'^(.*)_([a-z]+)-([0-9a-f]{8})$', base) or re.match(r'^(.*)_([0-9a-f]{8})$', base)
                    meta = {'item': m.group(1) if m else base, 'model_key': (m.group(2) if m and len(m.groups()) == 3 else 'qwen'), 'sin_ficha': True}
            meta.setdefault('t', os.path.getmtime(full))
            c = {'file': rel, 'kind': kind, 'meta': meta, 't': meta.get('t') or os.path.getmtime(full)}
            if kind == 'video':
                po = poster_for(full); c['poster'] = 'assets/video/' + os.path.basename(po) if po else None
            elif os.path.exists(os.path.join(md, fn + '.jpg')): c['thumb'] = 'assets/live/.mini/' + fn + '.jpg'
            else: faltan.append(fn)
            out.append(c)
    if faltan: threading.Thread(target=_mini_make, args=(faltan, uid()), daemon=True).start()
    out.sort(key=lambda c: -c['t']); return out
def _estado(rid):   # estado de un trabajo; si ha terminado, lo descarga a la casa de su dueño → (código, respuesta). Lo llaman /api/estado y el vigilante, siempre como la cuenta dueña
    j = _mio(rid)
    if not j: return 404, {'error': 'petición desconocida'}
    try:
        if j.get('prov') == 'ark':
            a = ark('GET', f'/api/v3/contents/generations/tasks/{rid}')
            st = {'status': {'succeeded': 'completed', 'failed': 'failed', 'cancelled': 'canceled', 'expired': 'failed'}.get(a.get('status'), 'in_progress'), 'request_id': rid,
                  'video': {'url': (a.get('content') or {}).get('video_url')}, 'error': (a.get('error') or {}).get('message') if a.get('error') else None, 'usage': a.get('usage')}
            if st['status'] == 'completed' and a.get('usage'): j['tokens'] = a['usage'].get('total_tokens')
        elif j.get('prov') == 'ws':
            if SERVIDOR: _ctx.ws_modo = 'casa' if j.get('casa') else 'propia'
            w = (ws('GET', f'/api/v3/predictions/{rid}/result').get('data') or {})
            outs = w.get('outputs') or []
            st = {'status': {'completed': 'completed', 'failed': 'failed'}.get(w.get('status'), 'in_progress'), 'request_id': rid, 'images': [{'url': u} for u in outs], 'video': {'url': outs[0] if outs else None}, 'error': w.get('error') or None}
            if w.get('status') == 'failed' and 'nsfw' in str(w.get('error', '')).lower(): st['status'] = 'nsfw'
            solapa = any(o is not j and o.get('owner') == j.get('owner') and o.get('prov') == 'ws' and o.get('t0', 0) < time.time() and (o.get('t_end') or time.time()) > j['t0'] for o in list(jobs.values()))   # con varias a la vez la diferencia de saldo mezcla costes → se queda el precio de tarifa
            if w.get('status') in ('completed', 'failed') and not j.get('t_end'): j['t_end'] = time.time()
            if w.get('status') == 'completed' and j.get('bal0') is not None and not j.get('file') and not solapa:   # coste real = lo que bajó el saldo (WaveSpeed no lo devuelve en el resultado)
                try:
                    bal1 = float((ws('GET', '/api/v3/balance').get('data') or {}).get('balance')); d = round(j['bal0'] - bal1, 4)
                    if 0 < d < 2: j['usd'] = d
                except Exception: pass
        else: st = api('GET', f'/requests/{rid}/status')
    except Exception as e:   # un 429/5xx o un corte de red al preguntar NO es un trabajo perdido: la web vuelve a preguntar
        plog(f'estado {rid[:8]} ✕ {e}'); return 503, {'error': str(e), 'retry': True}
    status = st.get('status'); out = {'status': status, 'usd': j.get('usd'), 'credits': j.get('credits'), 'model': j.get('model'), 'elapsed': round(time.time() - j['t0'], 1)}
    if j.get('casa') and status == 'completed' and not j.get('cobrado'):   # 🎁 se cobra al terminar (si falla, no se cobra nada)
        j['cobrado'] = True
        try: casa_cobra(j.get('usd'), 'imagen', rid, j.get('model'))
        except Exception as e: plog('saldo regalo: cobro ✕ ' + str(e))
    if status == 'completed' and not j.get('file') and j.get('kind') == 'video' and time.time() - j.get('dl', 0) > 900:
        vurl = (st.get('video') or {}).get('url')
        if vurl:
            j['dl'] = time.time()   # una sola descarga a la vez aunque pregunten la web y el vigilante
            data = urllib.request.urlopen(urllib.request.Request(vurl, headers={'User-Agent': UA}), timeout=600).read()
            fn = f"{_safe_item(j['item'])}__{rid[:8]}.mp4"; open(os.path.join(video_dir(), fn), 'wb').write(data); j['file'] = 'assets/video/' + fn; write_meta(j, j['file'], rid, st); _job_done(rid); poster_for(os.path.join(video_dir(), fn))
    if status == 'completed' and not j.get('file') and j.get('kind') != 'video' and time.time() - j.get('dl', 0) > 240:
        imgs = st.get('images') or st.get('output', {}).get('images') or []
        if imgs:
            j['dl'] = time.time()
            url = imgs[0]['url'] if isinstance(imgs[0], dict) else imgs[0]
            data = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=300).read()
            ext = '.png' if url.lower().split('?')[0].endswith('.png') else '.jpg'
            fn = f"{_safe_item(j['item'])}_{j.get('model', 'qwen')}-{rid[:8]}{ext}"; open(os.path.join(live_dir(), fn), 'wb').write(data); j['file'] = 'assets/live/' + fn; write_meta(j, j['file'], rid, st); _job_done(rid)
            if (j.get('meta') or {}).get('estilo'):
                try: j['estilo'] = _add_estilo(j, os.path.join(live_dir(), fn))
                except Exception as e: plog('estilo nuevo ✕ ' + str(e))
            if (j.get('meta') or {}).get('nf'):
                try: j['nf_item'] = _nf_autosave(j)
                except Exception as e: plog('ficha nueva ✕ ' + str(e))
            if (j.get('meta') or {}).get('prenda'):
                try: j['prenda'] = add_prenda(j, os.path.join(live_dir(), fn)); j['file'] = j['prenda']['ficha']
                except Exception as e: plog('prenda ✕ ' + str(e))
    if status in ('failed', 'nsfw', 'canceled'): j['failed'] = True; _job_done(rid); out['error'] = st.get('error') or st.get('detail') or status; plog(f"{rid[:8]} {status} · {out['error']} · {j.get('item')}")
    if j.get('casa'):
        try: out['casa'] = casa_info()
        except Exception: pass
    out['file'] = j.get('file'); out['kind'] = j.get('kind', 'image'); out['prenda'] = j.get('prenda'); out['nf'] = j.get('nf_item'); out['estilo'] = j.get('estilo'); out['raw'] = {k: st.get(k) for k in ('status', 'request_id')}
    return 200, out
class H(SimpleHTTPRequestHandler):
    timeout = 120 if SERVIDOR else None   # en servidor, una conexión que no dice nada se corta
    def __init__(self, *a, **k): super().__init__(*a, directory=ROOT, **k)
    def log_message(self, *a): pass
    def end_headers(self):
        self.send_header('Cache-Control', getattr(self, '_cc', None) or 'no-store')
        if SERVIDOR:
            self.send_header('X-Content-Type-Options', 'nosniff'); o = (getattr(self, 'headers', None) or {}).get('Origin') or ''
            if o and o.lower().rstrip('/') in ORIGENES:   # la web alojada llama desde otro dominio: solo a los orígenes de la lista
                self.send_header('Access-Control-Allow-Origin', o); self.send_header('Access-Control-Allow-Credentials', 'true'); self.send_header('Vary', 'Origin')
        super().end_headers()
    def _corta(self, code, msg='no'):   # respuesta de error (en HEAD, sin cuerpo)
        if self.command != 'HEAD': return self._json(code, {'error': msg})
        self.send_response(code); self.send_header('Content-Length', '0'); self.end_headers()
    def _pasa(self, fn):   # TODA petición (GET, POST y HEAD) entra por aquí: guarda de origen y, en servidor, tope de tamaño + sesión + cuenta del hilo
        self._cc = self._fijo = None; _ctx.lectura = 0
        if not self._guard(): return self._corta(403, 'origen no permitido')
        if not SERVIDOR: return fn()
        if self.command == 'GET' and self.path.startswith('/api/admin/copia'): return self._copia()
        if self.command in ('GET', 'HEAD') and self.path == '/salud': return self._json(200, {'ok': True, 'v': VERSION}) if self.command == 'GET' else self._corta(200)   # el alojamiento pregunta aquí si el servidor está vivo (sin sesión, sin datos)
        if self.command == 'POST':
            try: n = int(self.headers.get('Content-Length') or 0)
            except ValueError: n = -1
            if n < 0 or n > MAX_CUERPO: self.close_connection = True; return self._corta(400 if n < 0 else 413, 'petición no válida' if n < 0 else 'petición demasiado grande')
        try: c = _quien(self)
        except _NoEntra as e: return self._corta(e.code, e.msg)
        with como(*c):
            try: return fn()
            except Exception as e:
                plog(f'{self.command} {self.path[:80]} ✕ {type(e).__name__}: {e}')
                try: return self._corta(500, 'error interno')
                except Exception: return
    def _copia(self):   # copia de seguridad: un tar con todo lo de las cuentas cambiado desde «desde» (segundos). Solo con la llave de administración (ARIA_ADMIN, cabecera X-Admin); sin ella, como si no existiera
        adm = os.environ.get('ARIA_ADMIN') or ''
        if len(adm) < 32 or not hmac.compare_digest((self.headers.get('X-Admin') or '').encode(), adm.encode()): return self._corta(404)
        try: desde = float((urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get('desde') or ['0'])[0])
        except ValueError: desde = 0
        self.close_connection = True; self.send_response(200); self.send_header('Content-Type', 'application/x-tar'); self.send_header('X-Copia-Hasta', str(int(time.time()) - 5)); self.end_headers()
        with tarfile.open(fileobj=self.wfile, mode='w|') as t:
            for d, subs, fs in os.walk(os.path.join(DATOS, 'usuarios')):
                subs[:] = [x for x in subs if x != '.mini']   # las miniaturas se rehacen solas
                for f in fs:
                    fp = os.path.join(d, f)
                    try:
                        if os.path.getmtime(fp) > desde: t.add(fp, arcname=os.path.relpath(fp, DATOS), recursive=False)
                    except OSError: pass
            for f in ('jobs.jsonl', 'feedback.jsonl', 'errores.jsonl'):
                fp = os.path.join(DATOS, f)
                if os.path.isfile(fp) and os.path.getmtime(fp) > desde: t.add(fp, arcname=f)
    def do_GET(self): return self._pasa(self._get)
    def do_POST(self): return self._pasa(self._post)
    def do_HEAD(self): return self._pasa(self._head)   # antes HEAD se saltaba la guarda
    def _head(self): return self._estatico(True) if SERVIDOR else super().do_HEAD()
    if SERVIDOR:
        def do_OPTIONS(self):   # la pregunta previa del navegador (CORS) no lleva sesión; solo se contesta a los orígenes de la lista
            self._cc = None
            if not self._guard(): return self._corta(403, 'origen no permitido')
            self.send_response(204); self.send_header('Access-Control-Allow-Methods', 'GET, POST, HEAD, OPTIONS'); self.send_header('Access-Control-Allow-Headers', 'Authorization, Content-Type'); self.send_header('Access-Control-Max-Age', '600'); self.send_header('Content-Length', '0'); self.end_headers()
    def translate_path(self, path): return getattr(self, '_fijo', None) or super().translate_path(path)   # en servidor el fichero ya viene resuelto por _estatico
    def list_directory(self, path): return super().list_directory(path) if not SERVIDOR else self.send_error(404)   # en servidor, nunca listados
    def _estatico(self, cabeza=False):   # modo servidor: solo /assets/… — primero la casa de la cuenta; si no está y es de la biblioteca común, al almacén público. Nada más (ni código, ni catálogo, ni registros, ni lo de otra cuenta)
        ruta = urllib.parse.unquote(urllib.parse.urlparse(self.path).path); rel = _rel_ok(ruta[1:]) if ruta.startswith('/assets/') else None
        if not rel: return self._corta(404)
        base = casa(); full = os.path.join(base, *rel.split('/'))
        if _dentro(base, full) and os.path.isfile(full):
            self._cc = 'private, no-cache'; self._fijo = full
            return super().do_HEAD() if cabeza else super().do_GET()
        if _biblio_ok(rel):
            self._cc = 'private, max-age=3600'; self.send_response(302); self.send_header('Location', _biblio_url(rel)); self.send_header('Content-Length', '0'); self.end_headers(); return
        return self._corta(404)
    def _json(self, code, obj):
        lec = getattr(_ctx, 'lectura', 0)
        if lec and isinstance(obj, dict): obj = dict(obj, usd_lectura=round(lec, 4)); _ctx.lectura = 0   # lo que han costado las lecturas de imagen de esta petición
        b = json.dumps(obj, ensure_ascii=False).encode(); self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8'); self.send_header('Content-Length', str(len(b))); self.end_headers(); self.wfile.write(b)
    def _guard(self):   # solo el propio navegador en localhost: ni otra web (CSRF) ni un dominio que apunte a 127.0.0.1 (DNS rebinding)
        if SERVIDOR:   # en servidor no se exige localhost: el origen, si viene, tiene que estar en la lista (ARIA_ORIGENES), y los POST son siempre JSON
            origin = (self.headers.get('Origin') or '').lower().rstrip('/')
            if origin and origin not in ORIGENES: return False
            return not (self.command == 'POST' and 'application/json' not in (self.headers.get('Content-Type') or '').lower())
        hosts = (f'localhost:{PORT}', f'127.0.0.1:{PORT}', f'[::1]:{PORT}')
        if (self.headers.get('Host') or '').lower() not in hosts: return False
        origin = (self.headers.get('Origin') or '').lower()
        if origin and origin not in tuple('http://' + h for h in hosts): return False
        if self.command == 'POST' and 'application/json' not in (self.headers.get('Content-Type') or '').lower(): return False
        return True
    def _get(self):
        u = urllib.parse.urlparse(self.path); q = urllib.parse.parse_qs(u.query)
        if SERVIDOR:
            if u.path in ('/api/calendario', '/api/liga', '/api/liga/zip'): return self._json(404, {'error': 'no disponible en el servidor'})   # Notion y los duelos son del ordenador de Max
            if u.path == '/api/catalogo': return self._json(200, _cat_load()[1])   # el catálogo que ve esta cuenta: el común + su capa
        if u.path == '/api/claves':   # estado de las APIs, sin enseñar nunca las claves
            A = _apis_estado(); w = A[0]
            return self._json(200, {'ok': True, 'apis': A, 'ws': w['on'], 'ws_fin': w['fin'], 'saldo': w['saldo'], 'casa': casa_info()})
        if u.path == '/api/monedero':   # 🎁 el saldo regalo de la cuenta y su historial de gasto (lo más nuevo primero)
            c = casa_info()
            if not c and not _casa_base(): return self._json(200, {'ok': True, 'casa': None, 'hist': []})
            with _cerrojo('mon'): m = _mon_lee()
            return self._json(200, {'ok': True, 'casa': c, 'hist': [{k: h.get(k) for k in ('t', 'usd', 'que', 'modelo', 'n')} for h in reversed(m.get('hist') or [])][:200]})
        if u.path == '/api/ping':
            return self._json(200, {'ok': True, **({'espacio': {'usado': espacio(), 'tope': CUOTA}, 'aria_mia': not aria_fija()} if SERVIDOR else {}), 'model': MODEL, 'default': CASA_DEF if casa_on() else 'mstudio', 'models': model_list(), 'unavailable': unavailable(), 'ws': bool(load_ws()) or casa_on(), 'casa': casa_info(), 'aspects': ASPECTS, 'key': _hf_listo(), 'ark': bool(load_ark()[0]), 'ark_usd': ARK_USD, 'interno': bool(getattr(_ctx, 'interno', False)) if SERVIDOR else os.path.isfile(os.path.expanduser('~/.claude/notion.env')), **({'servidor': True} if SERVIDOR else {})})   # interno = el ordenador de Max: enseña «Workflows» (en la web alojada, solo las cuentas autorizadas)
        if u.path == '/api/live':   # lo ya generado por la API (assets/live/<item>_<rid>.ext) → la app lo enseña sin volver a generar
            files = {}; allf = []; ld, vd = live_dir(), video_dir()
            for fn in sorted(os.listdir(ld), key=lambda f: os.path.getmtime(os.path.join(ld, f))):
                if fn.startswith('.') or '_' not in fn or not fn.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')): continue   # las fichas .json no son imágenes
                files[fn.rsplit('_', 1)[0]] = 'assets/live/' + fn      # el más reciente de cada elemento gana
                allf.append('assets/live/' + fn)
            videos = {}
            for fn in sorted(os.listdir(vd), key=lambda f: os.path.getmtime(os.path.join(vd, f))):
                if fn.startswith('.') or '__' not in fn or not fn.lower().endswith(('.mp4', '.mov', '.webm')) or os.path.splitext(fn)[0].endswith('_lo'): continue
                videos[fn.split('__')[0]] = 'assets/video/' + fn        # el vídeo más reciente de cada imagen
            return self._json(200, {'files': files, 'n': len(files), 'all': allf[::-1], 'videos': videos, 'creations': creations(), 'lecturas': _lecturas()})
        if u.path == '/api/personajes':   # personajes creados en la app (assets/personajes/<id>/personaje.json)
            out = []; pd = pers_dir()   # solo los de la cuenta
            for d in sorted(os.listdir(pd)):
                f = os.path.join(pd, d, 'personaje.json')
                if not d.startswith(('_', '.')) and os.path.isfile(f):
                    try: out.append(json.load(open(f)))
                    except Exception as e: plog(f'personaje {d} ✕ {e}')
            out.sort(key=lambda p: (p.get('orden') if isinstance(p.get('orden'), int) else 999, p.get('creado') or ''))
            od = os.path.join(DATOS, 'biblioteca', 'assets', 'personajes', '_opciones', 'aria') if SERVIDOR else os.path.join(pd, '_opciones', 'aria')   # las tarjetas de opciones son de la biblioteca común (en servidor: lo que haya en su copia)
            tarj = sorted(x[:-4] for x in os.listdir(od) if x.endswith('.jpg')) if os.path.isdir(od) else []
            if SERVIDOR:   # un almacén no se puede listar: la lista viene en un índice que sube subir.py junto a las imágenes
                try: tarj = sorted(str(x) for x in json.load(open(_biblio('assets/personajes/_opciones/aria/index.json'), encoding='utf-8')) if isinstance(x, str))
                except Exception: pass
            return self._json(200, {'items': out, 'tarjetas': tarj})
        if u.path == '/api/calendario':   # Calendario de Instagram (Notion) del mes pedido: ?m=YYYY-MM
            m = (q.get('m') or [time.strftime('%Y-%m')])[0]
            try:
                import calendar as _cal, datetime as _dt
                y, mo = int(m[:4]), int(m[5:7]); first = f'{y:04d}-{mo:02d}-01'; last = f'{y:04d}-{mo:02d}-{_cal.monthrange(y, mo)[1]:02d}'
                ck = ('cal', m); now = time.time()
                if ck in _cache and now - _cache[ck][0] < 300: return self._json(200, _cache[ck][1])
                tok = ''
                for line in open(os.path.expanduser('~/.claude/notion.env')):
                    if line.startswith('NOTION_TOKEN='): tok = line.strip().split('=', 1)[1]
                if not tok: raise RuntimeError('falta NOTION_TOKEN en ~/.claude/notion.env')
                body = {'page_size': 100, 'filter': {'and': [{'property': 'Date', 'date': {'on_or_after': first}}, {'property': 'Date', 'date': {'on_or_before': last}}]}, 'sorts': [{'property': 'Date', 'direction': 'ascending'}]}
                rows = []
                while True:
                    req = urllib.request.Request('https://api.notion.com/v1/databases/2dfc9bc2-4cb1-80fc-bccd-fad5f7529cc8/query', data=json.dumps(body).encode(), method='POST')
                    req.add_header('Authorization', 'Bearer ' + tok); req.add_header('Notion-Version', '2022-06-28'); req.add_header('Content-Type', 'application/json')
                    with urllib.request.urlopen(req, timeout=60) as r: res = json.loads(r.read())
                    rows += res['results']
                    if not res.get('has_more'): break
                    body['start_cursor'] = res['next_cursor']
                def pv(p):
                    t = p['type']; v = p.get(t)
                    if t == 'title' or t == 'rich_text': return ''.join(x.get('plain_text', '') for x in (v or []))
                    if t == 'select': return (v or {}).get('name')
                    if t == 'multi_select': return [x['name'] for x in (v or [])]
                    if t == 'date': return (v or {}).get('start')
                    if t == 'checkbox': return bool(v)
                    if t == 'url': return v
                    if t == 'number': return v
                    return None
                items = []
                for r in rows:
                    P = r['properties']; g = lambda k: pv(P[k]) if k in P else None
                    items.append({'id': r['id'], 'name': g('Name') or '(sin título)', 'date': g('Date'), 'estado': g('Estado') or '', 'formato': g('Formato') or [], 'red': g('Red Social') or [], 'tags': g('Tags') or [], 'portada': g('Portada'), 'seleccion': g('Selección'), 'url': r.get('url'), 'canva': g('Canva'), 'ig': g('🔗 Link Instagram'), 'real': g('📅 Fecha real publicación'), 'likes': g('❤️ Likes'), 'cover': ((r.get('cover') or {}).get('file') or (r.get('cover') or {}).get('external') or {}).get('url')})
                out = {'m': m, 'items': items}; _cache[ck] = (now, out); return self._json(200, out)
            except Exception as e: return self._json(502, {'error': str(e)[:300]})
        if u.path == '/api/fetch':   # descarga una imagen de internet (arrastrada desde el navegador) y la devuelve en base64
            url = (q.get('url') or [''])[0]
            try:
                data, ctype = _trae_url(url)
                if not ctype.startswith('image/') and (ctype.startswith('text/html') or data[:400].lstrip().lower().startswith((b'<!doctype', b'<html'))):   # es una página: su imagen de portada (og:image)
                    import html as _h
                    P = data[:6000000]; m = re.search(rb'<meta[^>]+(?:property|name)=["\'](?:og:image(?::secure_url)?|twitter:image)["\'][^>]*content=["\']([^"\']+)["\']', P, re.I) or re.search(rb'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\'](?:og:image|twitter:image)["\']', P, re.I)
                    if not m: raise RuntimeError('en ese enlace no he encontrado ninguna imagen')
                    u2 = urllib.parse.urljoin(url, _h.unescape(m.group(1).decode('utf-8', 'replace'))); pm = re.match(r'^(https://i\.pinimg\.com/)(?:\d+x\d*(?:_RS)?)(/.+)$', u2)
                    ok = False
                    for c in ([pm.group(1) + 'originals' + pm.group(2)] if pm else []) + [u2]:   # Pinterest: primero el original
                        try:
                            data, ctype = _trae_url(c)
                            if ctype.startswith('image/'): ok = True; break
                        except Exception: continue
                    if not ok: raise RuntimeError('no he podido descargar la imagen de ese enlace')
                if not ctype.startswith('image/'):
                    try:
                        from PIL import Image; import io; Image.open(io.BytesIO(data)); ctype = 'image/jpeg'
                    except Exception: raise RuntimeError('eso no es una imagen')
                return self._json(200, {'data': 'data:' + ctype + ';base64,' + base64.b64encode(data).decode()})
            except Exception as e: return self._json(400, {'error': str(e)[:200]})
        if u.path == '/api/lugares_buscar':   # fotos de sitios para «Mis lugares» (Pexels o Pixabay: gratis y de uso libre). Devuelve miniatura, imagen grande, autor y enlace
            qq = (q.get('q') or [''])[0].strip()[:80]; prov, k = _fotos_key()
            try: pg = max(1, min(5, int((q.get('p') or ['1'])[0])))
            except Exception: pg = 1
            if not k: return self._json(200, {'ok': False, 'falta': True, 'error': 'el buscador de fotos todavía no está activado'})
            if len(qq) < 2: return self._json(400, {'error': 'escribe qué sitio buscas'})
            ck = qq.lower() + '|' + str(pg); hit = _PEX.get(ck)
            if hit and time.time() - hit[0] < 86400: return self._json(200, {'ok': True, 'prov': prov, 'fotos': hit[1]})
            quien = uid() or 'local'; ahora = time.time(); L = _PEX_N.setdefault(quien, []); L[:] = [t for t in L if ahora - t < 3600]
            if len(L) >= 40: return self._json(429, {'error': 'demasiadas búsquedas seguidas: prueba dentro de un rato'})
            L.append(ahora)
            try:
                fotos = _fotos_busca(prov, k, qq, pg)
            except urllib.error.HTTPError as e: return self._json(502, {'error': f'el buscador de fotos respondió {e.code}'})
            except Exception: return self._json(502, {'error': 'no se ha podido buscar ahora'})
            if len(_PEX) > 600: _PEX.clear()
            _PEX[ck] = (time.time(), fotos); return self._json(200, {'ok': True, 'prov': prov, 'fotos': fotos})
        if u.path == '/api/papelera':   # lo borrado de Mis creaciones que aún se puede recuperar (30 días), lo más reciente primero
            trash = papelera(); out = []; ahora = time.time()
            for fn in os.listdir(trash):
                fp = os.path.join(trash, fn)
                if fn.startswith('.') or fn.endswith('.json') or not os.path.isfile(fp + '.json'): continue   # solo creaciones (llevan su ficha .json al lado)
                try: meta = json.load(open(fp + '.json', encoding='utf-8'))
                except Exception: meta = {}
                t = os.path.getmtime(fp); video = fn.lower().endswith('.mp4'); po = os.path.splitext(fn)[0] + '.jpg'
                out.append({'file': fn, 'src': 'assets/papelera/' + fn, 'thumb': 'assets/papelera/' + (po if video and os.path.isfile(os.path.join(trash, po)) else fn), 'kind': 'video' if video else 'image', 'name': str(meta.get('name') or fn)[:120], 't': int(t), 'dias': max(0, 30 - int((ahora - t) // 86400))})
            out.sort(key=lambda x: -x['t']); return self._json(200, {'ok': True, 'items': out[:500], 'dias': 30, 'caduca': bool(SERVIDOR)})
        if u.path == '/api/pendientes':   # trabajos de personajes que la página aún no ha recogido (si se recarga, no se pierden)
            out = [{'rid': rid, 'item': j.get('item'), 'meta': {k: (j.get('meta') or {}).get(k) for k in ('personaje', 'pjKind', 'name')}, 'file': j.get('file'), 'usd': j.get('usd'), 'kind': j.get('kind', 'image'), 'edad': round(time.time() - j['t0'], 1)}
                   for rid, j in list(jobs.items()) if j.get('owner') == uid() and not j.get('claimed') and not j.get('failed') and str((j.get('meta') or {}).get('personaje') or '_').strip()[:1] not in ('_', '')]
            return self._json(200, {'jobs': out})
        if u.path == '/api/estado': return self._json(*_estado((q.get('id') or [''])[0]))
        if u.path == '/api/liga/zip':   # 🥊 descarga del carrusel (o de todo el duelo) en un zip
            did = (q.get('id') or [''])[0]; carpeta = os.path.join(LIGA_DIR, did)
            if not re.fullmatch(r'[A-Za-z0-9_.-]+', did) or did.startswith('.') or not os.path.isdir(carpeta): return self._json(400, {'error': 'duelo desconocido'})
            import io, zipfile
            todo = (q.get('todo') or [''])[0] == '1'; buf = io.BytesIO()
            with zipfile.ZipFile(buf, 'w', zipfile.ZIP_STORED) as z:
                for sub in (['mundos', 'galeria', 'campeon', 'carrusel'] if todo else ['carrusel']):
                    dd = os.path.join(carpeta, sub)
                    if not os.path.isdir(dd): continue
                    for fn in sorted(os.listdir(dd)):
                        fp = os.path.join(dd, fn)
                        if os.path.isfile(fp) and not fn.startswith('.'): z.write(fp, f'{sub}/{fn}' if todo else fn)
            data = buf.getvalue(); nombre = f"{did}-{'todo' if todo else 'carrusel'}.zip"
            self.send_response(200); self.send_header('Content-Type', 'application/zip'); self.send_header('Content-Disposition', f'attachment; filename="{nombre}"')
            self.send_header('Content-Length', str(len(data))); self.end_headers(); self.wfile.write(data); return
        if u.path == '/api/liga':   # 🥊 Duelos: lo que prepara Claude (duelo.json) + lo que elige Max (max.json), por carpeta de assets/liga
            os.makedirs(LIGA_DIR, exist_ok=True); out = []
            for d in sorted(os.listdir(LIGA_DIR), reverse=True):
                f = os.path.join(LIGA_DIR, d, 'duelo.json')
                if d.startswith('.') or not os.path.isfile(f): continue
                try: duelo = json.load(open(f, encoding='utf-8'))
                except Exception as e: duelo = {'id': d, 'titulo': d + ' (duelo.json roto)', 'error': str(e)}
                duelo['id'] = d; mf = os.path.join(LIGA_DIR, d, 'max.json')
                try: mx = json.load(open(mf, encoding='utf-8')) if os.path.isfile(mf) else {}
                except Exception: mx = {}
                out.append({'duelo': duelo, 'max': mx})
            return self._json(200, {'duelos': out})
        return self._estatico() if SERVIDOR else super().do_GET()
    def _post(self):
        if self.path in ('/api/video', '/api/generar', '/api/personaje') and lleno(): return self._json(413, {'error': LLENO, 'lleno': True})
        if self.path in ('/api/perfil', '/api/ficha_panel', '/api/fichas360', '/api/fichas_outfit') and aria_fija(): return self._json(403, {'error': FIJA, 'fija': True})   # todo esto escribe en la ficha de Aria
        if self.path == '/api/video': return self.do_video()
        if SERVIDOR and self.path == '/api/sesion':   # deja la sesión en una cookie HttpOnly para que las imágenes de la cuenta se puedan pedir con <img>; {salir:true} la borra
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(n) or b'{}'); a = self.headers.get('Authorization') or ''; tok = a[7:].strip() if a[:7].lower() == 'bearer ' else ''
            if body.get('salir'): ck = 'aria_token=; Path=/; HttpOnly; Secure; SameSite=None; Max-Age=0'
            elif tok and re.fullmatch(r'[A-Za-z0-9_.-]+', tok): ck = f'aria_token={tok}; Path=/; HttpOnly; Secure; SameSite=None; Max-Age=3600'
            else: return self._json(400, {'error': 'falta la sesión en Authorization'})
            b = b'{"ok": true}'; self.send_response(200); self.send_header('Set-Cookie', ck); self.send_header('Content-Type', 'application/json; charset=utf-8'); self.send_header('Content-Length', str(len(b))); self.end_headers(); self.wfile.write(b); return
        if self.path == '/api/claves':   # {id, key} comprueba y guarda una clave · {id, off:true|false} desconecta o vuelve a conectar una API
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(n) or b'{}')
            if 'ws' in body and 'id' not in body: body = {'id': 'ws', 'key': body.get('ws')} if body.get('ws') else {'id': 'ws', 'off': True}
            if body.get('id') == 'auto':   # la pantalla ya no pregunta de quién es la clave
                body['id'] = _de_quien(str(body.get('key') or '').strip())
                if body['id'] == 'duda': return self._json(400, {'error': 'el proveedor no ha respondido al comprobar la clave. No es que esté mal: vuelve a pulsar Conectar'})
                if not body['id']: return self._json(400, {'error': 'no reconozco esa clave. Hoy funcionan las de WaveSpeed, Higgsfield (con la forma ID:SECRET) y BytePlus: revisa que esté copiada entera'})
            api_ = next((a for a in APIS if a[0] == body.get('id')), None)
            if not api_: return self._json(400, {'error': 'API desconocida'})
            aid, nombre, envn, homef, _para = api_
            if 'off' in body and not body.get('key'):
                _claves_set(envn + '_OFF', '1' if body.get('off') else ''); plog(f'{nombre} ' + ('desconectada' if body.get('off') else 'vuelta a conectar')); return self._json(200, {'ok': True, 'apis': _apis_estado()})
            k = str(body.get('key') or '').strip()
            if len(k) < 16 or ' ' in k or '\n' in k or (SERVIDOR and not re.fullmatch(r'[\x21-\x7e]{16,400}', k)): return self._json(400, {'error': 'eso no parece una clave'})
            try:
                if aid == 'ws': _ws_saldo(k)
                elif aid == 'hf':
                    if ':' not in k: return self._json(400, {'error': 'la clave de Higgsfield tiene la forma ID:SECRET'})
                    _hf_ok(k)
            except urllib.error.HTTPError as e: return self._json(400, {'error': f'{nombre} no acepta esa clave' if e.code in (401, 403) else f'{nombre} respondió {e.code}'})
            except Exception as e: return self._json(400, {'error': 'no se pudo comprobar: ' + str(e)[:80]})
            _claves_set(envn, k); _claves_set(envn + '_OFF', ''); plog(f'clave de {nombre} guardada desde la pantalla'); return self._json(200, {'ok': True, 'apis': _apis_estado()})
        if self.path == '/api/borrar':   # mueve una creación (y su ficha/póster) a assets/papelera
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(n) or b'{}'); rel = body.get('file', '')
            full = _creacion(rel)
            if not full: return self._json(400, {'error': 'archivo no válido'})
            trash = papelera()
            import shutil
            for extra in ('', '.json'):
                if os.path.exists(full + extra): shutil.move(full + extra, os.path.join(trash, os.path.basename(full) + extra))
            po = os.path.splitext(full)[0] + '.jpg'
            if full.lower().endswith('.mp4') and os.path.exists(po): shutil.move(po, os.path.join(trash, os.path.basename(po)))
            for fn in os.listdir(trash):
                if fn.startswith(os.path.splitext(os.path.basename(full))[0]):
                    try: os.utime(os.path.join(trash, fn), None)
                    except OSError: pass
            plog('borrar → papelera ' + rel); return self._json(200, {'ok': True})
        if self.path == '/api/restaurar':   # saca una creación de la papelera y la devuelve a Mis creaciones
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(n) or b'{}'); fn = os.path.basename(str(body.get('file') or ''))
            trash = papelera(); src = os.path.join(trash, fn)
            if not fn or fn.startswith('.') or not os.path.isfile(src) or not os.path.isfile(src + '.json'): return self._json(400, {'error': 'no está en la papelera'})
            import shutil
            dest = video_dir() if fn.lower().endswith('.mp4') else live_dir()
            if os.path.exists(os.path.join(dest, fn)): return self._json(400, {'error': 'ya hay una creación con ese nombre'})
            if lleno(): return self._json(400, {'error': LLENO, 'lleno': True})
            for extra in ('', '.json'): shutil.move(src + extra, os.path.join(dest, fn + extra))
            po = os.path.splitext(fn)[0] + '.jpg'
            if fn.lower().endswith('.mp4') and os.path.isfile(os.path.join(trash, po)): shutil.move(os.path.join(trash, po), os.path.join(dest, po))
            plog('restaurar ← papelera ' + fn); return self._json(200, {'ok': True})
        if self.path == '/api/zip':   # varias creaciones seleccionadas → un zip
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(n) or b'{}'); files = body.get('files') or []
            import io, zipfile; buf = io.BytesIO(); z = zipfile.ZipFile(buf, 'w', zipfile.ZIP_STORED); k = 0
            for rel in files[:200]:
                full = _creacion(rel)
                if full: z.write(full, os.path.basename(full)); k += 1
            z.close()
            if not k: return self._json(400, {'error': 'nada que descargar'})
            data = buf.getvalue(); self.send_response(200); self.send_header('Content-Type', 'application/zip'); self.send_header('Content-Disposition', 'attachment; filename="aria-studio.zip"'); self.send_header('Content-Length', str(len(data))); self.end_headers(); self.wfile.write(data); return
        if self.path == '/api/personaje':   # guarda un personaje: datos + fotos subidas (dataURL) + archivos ya generados (copy)
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(n) or b'{}'); P = body.get('p') or {}
            import re as _re, shutil, io
            pid = P.get('id') or _re.sub(r'[^a-z0-9]+', '-', (P.get('nombre') or 'personaje').lower()).strip('-') or 'personaje'
            if not P.get('id'):
                base, k = pid, 2
                while os.path.exists(os.path.join(pers_dir(), pid)): pid = f'{base}-{k}'; k += 1
            if pid == 'aria' or not _pid_ok(pid): return self._json(400, {'error': 'id no válido'})
            d = os.path.join(pers_dir(), pid); os.makedirs(d, exist_ok=True); P['id'] = pid
            P.setdefault('creado', time.strftime('%Y-%m-%d %H:%M')); P['editado'] = time.strftime('%Y-%m-%d %H:%M')
            def _save(key, raw):
                from PIL import Image
                im = Image.open(io.BytesIO(raw)).convert('RGB'); fn = key + '.jpg'; im.save(os.path.join(d, fn), quality=92); P[key] = f'assets/personajes/{pid}/{fn}?v={int(time.time())}'
                if key == 'foto' or (key in ('retrato', 'vista_frente') and not P.get('foto')):   # avatar = cuadrado centrado arriba (la cara)
                    w, h = im.size; sz = min(w, int(h * 0.62)); x0 = (w - sz) // 2; y0 = max(0, int(h * 0.06))
                    im.crop((x0, y0, x0 + sz, y0 + sz)).resize((256, 256)).save(os.path.join(d, 'avatar.jpg'), quality=90); P['avatar'] = f'assets/personajes/{pid}/avatar.jpg?v={int(time.time())}'
            OKF = ('foto', 'ficha360', 'importada', 'retrato', 'vista_frente', 'vista_perfil', 'vista_tres', 'vista_espalda', 'cuerpo', 'peloRef', 'detImg', 'estiloRef', 'avatar', 'avatarSrc')
            okk = lambda k: k in OKF or bool(_re.fullmatch(r'inspo_\d{1,2}', k))
            for key, du in (body.get('files') or {}).items():
                if okk(key) and du and ',' in du: _save(key, base64.b64decode(du.split(',', 1)[1]))
            for key, rel in (body.get('copy') or {}).items():
                src = busca(rel)   # de la casa de la cuenta o de la biblioteca común
                if okk(key) and src: _save(key, open(src, 'rb').read())
            for key, spec in (body.get('crops') or {}).items():   # un recorte de una imagen (la cara elegida de una rejilla 3×3)
                if okk(key) and isinstance(spec, dict) and spec.get('path'): data, _ct = img_bytes({'path': spec['path'], 'crop': spec.get('crop')}); _save(key, data)
            if body.get('files') and any(_re.fullmatch(r'inspo_\d{1,2}', k) for k in body['files']): P['inspo'] = sorted([k for k in P if _re.fullmatch(r'inspo_\d{1,2}', k)], key=lambda k: int(k.split('_')[1]))
            json.dump(P, open(os.path.join(d, 'personaje.json'), 'w'), ensure_ascii=False, indent=1)
            plog(f'personaje guardado {pid}'); return self._json(200, {'ok': True, 'p': P})
        if self.path == '/api/personaje_ficha':   # une las 4 vistas aprobadas (frente, perfil, tres cuartos, espalda) en la ficha 360 2x2, como la de Aria
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(n) or b'{}'); pid = body.get('id', '')
            from PIL import Image
            if not _pid_ok(pid) or not os.path.isfile(os.path.join(pers_dir(), pid, 'personaje.json')): return self._json(404, {'error': 'personaje no encontrado'})
            d = os.path.join(pers_dir(), pid); f = os.path.join(d, 'personaje.json')
            P = json.load(open(f)); W, H = 800, 1200; out = Image.new('RGB', (W * 2, H * 2), (200, 198, 196))
            for i, k in enumerate(('frente', 'perfil', 'tres', 'espalda')):
                fp = os.path.join(d, f'vista_{k}.jpg')
                if not os.path.isfile(fp): return self._json(400, {'error': f'falta la vista {k}'})
                im = Image.open(fp).convert('RGB'); w, h = im.size
                if w / h > W / H: nw = int(h * W / H); im = im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
                else: nh = int(w * H / W); y0 = min(int((h - nh) * 0.2), h - nh); im = im.crop((0, y0, w, y0 + nh))
                out.paste(im.resize((W, H), Image.LANCZOS), ((i % 2) * W, (i // 2) * H))
            out.save(os.path.join(d, 'ficha360.jpg'), quality=92); P['ficha360'] = f'assets/personajes/{pid}/ficha360.jpg?v={int(time.time())}'; P['editado'] = time.strftime('%Y-%m-%d %H:%M')
            json.dump(P, open(f, 'w'), ensure_ascii=False, indent=1); plog(f'ficha 360 de {pid} montada'); return self._json(200, {'ok': True, 'p': P})
        if self.path == '/api/personajes_orden':   # {ids:[…]} el orden de «Mis personajes» (arrastrando)
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(n) or b'{}')
            with _cerrojo():
                for i, pid in enumerate(body.get('ids') or []):
                    pid = str(pid)
                    if not _pid_ok(pid): continue
                    pf = os.path.join(pers_dir(), pid, 'personaje.json')
                    if not os.path.isfile(pf): continue
                    PP = json.load(open(pf)); PP['orden'] = i; json.dump(PP, open(pf, 'w'), ensure_ascii=False, indent=1)
            return self._json(200, {'ok': True})
        if self.path == '/api/personaje_fichas':   # fichas creadas de un personaje: {id, action:'delete', fid}
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(n) or b'{}'); pid = str(body.get('id') or '')
            if not _pid_ok(pid) or not os.path.isfile(os.path.join(pers_dir(), pid, 'personaje.json')): return self._json(404, {'error': 'personaje no encontrado'})
            d = os.path.join(pers_dir(), pid); pf = os.path.join(d, 'personaje.json')
            import shutil
            with _cerrojo():
                PP = json.load(open(pf)); L = PP.get('fichas') or []; it = next((f for f in L if f.get('id') == body.get('fid')), None)
                if not it: return self._json(404, {'error': 'ficha no encontrada'})
                trash = papelera()
                for k in ('img', 'thumb'):
                    fp = busca(it.get(k), propio=True)
                    if fp and _dentro(d, fp): shutil.move(fp, os.path.join(trash, pid + '_' + os.path.basename(fp)))
                PP['fichas'] = [f for f in L if f is not it]; json.dump(PP, open(pf, 'w'), ensure_ascii=False, indent=1)
            plog(f'ficha de {pid} a la papelera · {it.get("nombre")}'); return self._json(200, {'ok': True})
        if self.path == '/api/personaje_combo':   # ficha principal del personaje: su 2x2 + su cuerpo de frente + su cuerpo de perfil (tercios de su ficha de cuerpo), 16:9 como la de Aria
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(n) or b'{}'); pid = body.get('id', '')
            from PIL import Image
            if not _pid_ok(pid) or not os.path.isfile(os.path.join(pers_dir(), pid, 'personaje.json')): return self._json(404, {'error': 'personaje no encontrado'})
            d = os.path.join(pers_dir(), pid); f = os.path.join(d, 'personaje.json')
            P = json.load(open(f))
            try:
                fa = busca(P.get('ficha360')); fc = busca(P.get('cuerpo'))   # lo que diga personaje.json también pasa por la puerta única
                if not fa or not fc: raise RuntimeError('faltan la ficha 360 o la ficha de cuerpo')
                CW, CH, GAP, BW, SW = 1600, 2400, 16, 1317, 1318; out = Image.new('RGB', (CW + GAP + BW + GAP + SW, CH), (200, 198, 196))
                def cover(im, W, H, yb):
                    w, h = im.size
                    if w / h > W / H: nw = int(h * W / H); im = im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
                    else: nh = int(w * H / W); y0 = min(int((h - nh) * yb), h - nh); im = im.crop((0, y0, w, y0 + nh))
                    return im.resize((W, H), Image.LANCZOS)
                out.paste(cover(Image.open(fa).convert('RGB'), CW, CH, 0.2), (0, 0)); b = Image.open(fc).convert('RGB'); w, h = b.size
                out.paste(cover(b.crop((0, 0, w // 3, h)), BW, CH, 0.0), (CW + GAP, 0)); out.paste(cover(b.crop((w // 3, 0, 2 * w // 3, h)), SW, CH, 0.0), (CW + GAP + BW + GAP, 0))
                out.save(os.path.join(d, 'combo.jpg'), quality=92); P['combo'] = f'assets/personajes/{pid}/combo.jpg?v={int(time.time())}'; P['editado'] = time.strftime('%Y-%m-%d %H:%M')
                json.dump(P, open(f, 'w'), ensure_ascii=False, indent=1)
            except Exception as e: return self._json(400, {'error': str(e)})
            plog(f'ficha principal de {pid} montada'); return self._json(200, {'ok': True, 'p': P})
        if self.path == '/api/pj_analizar':   # «desde tus fotos favoritas»: Gemini mira las fotos y rellena los rasgos comunes del personaje
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(n) or b'{}')
            try:
                urls = [resolve_ws({'data': du}) for du in (body.get('images') or [])[:8] if isinstance(du, str) and du.startswith('data:')]
                if not urls: raise RuntimeError('faltan las fotos')
                ask = _ASK_FICHA if body.get('modo') == 'ficha' else ('These photos show people the user likes as inspiration for a new AI influencer. Find the COMMON look (the average of all of them) and answer with ONLY a JSON object with these keys and allowed values: '
                       '"genero": fem|masc|andro|nb; "edad": number; "altura": number in cm; "cara": oval|redonda|corazon|angulosa|alargada; "ojos": negros|marrones|verdes|azules|grises|ambar|amarillos|violeta; '
                       '"ojosForma": caidos|rasgados|almendra|redondos; "labios": finos|medios|carnosos|muy; "nariz": peq|recta|ancha|aguilena; "peloColor": negro|castano|rubio|pelirrojo|rosa|azul|verde (or null); '
                       '"peloNombre": Spanish name of the hair color if none of those fits (else null); "piel": muyclara|clara|media|morena|oscura|ebano; "complexion": menuda|delgada|atletica|media|curvy|musculosa|grande; '
                       '"pecho": peq|medio|grande|muy (or null for men); "cadera": estrecha|media|ancha|muy; "estilo": realista|cartoon; "pielDet": array of hoyuelos|tatuajes|cicatriz (only if most photos show it); '
                       '"resumen": one short Spanish sentence describing the common look.')
                r = ws('POST', '/api/v3/wavespeed-ai/any-llm/vision', {'prompt': ask, 'images': urls, 'model': 'google/gemini-2.5-flash', 'temperature': 0.2, 'max_tokens': 1200, 'priority': 'latency'})
                rid = (r.get('data') or {}).get('id'); txt = ''
                for _ in range(50):
                    time.sleep(1.5); w = ws('GET', f'/api/v3/predictions/{rid}/result').get('data') or {}
                    if w.get('status') == 'completed': o = w.get('outputs') or []; txt = (o[0] if o else '') if isinstance(o, list) else str(o); break
                    if w.get('status') == 'failed': raise RuntimeError(w.get('error') or 'falló')
                m = re.search(r'\{.*\}', str(txt), re.S)
                if not m: raise RuntimeError('respuesta sin datos')
                data = json.loads(m.group(0))
            except Exception as e: return self._json(400, {'error': str(e)})
            plog('pj_analizar ok · ' + str(data.get('resumen', ''))[:80]); return self._json(200, {'ok': True, 'd': data})
        if self.path == '/api/ficha_panel':   # editor de las fichas principales: sustituir una vista (2x2 o 3 en fila), guardar un cuerpo nuevo o hacerlo principal
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(n) or b'{}'); act = body.get('action') or 'compose'
            import re as _re
            from PIL import Image
            def _abs(rel):
                fp = busca(rel)   # la casa de la cuenta o la biblioteca común; nada más
                if not fp: raise RuntimeError('no existe ' + str(rel)[:200])
                return fp
            def _cover(im, W, H):
                w, h = im.size
                if w / h > W / H: nw = int(h * W / H); im = im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
                else: nh = int(w * H / W); y0 = min(int((h - nh) * 0.15), h - nh); im = im.crop((0, y0, w, y0 + nh))
                return im.resize((W, H), Image.LANCZOS)
            try:
                with _cerrojo():
                    head, C = _cat_load(); P = C['perfil']; stamp = str(int(time.time()))
                    if act == 'compose':
                        base = Image.open(_abs(body.get('base'))).convert('RGB'); W, H = base.size; panel = Image.open(_abs(body.get('panel'))).convert('RGB'); i = int(body.get('index') or 0)
                        if body.get('layout') == '3x1': pw = W // 3; box = (i * pw, 0, (i + 1) * pw if i < 2 else W, H)
                        else: box = ((i % 2) * (W // 2), (i // 2) * (H // 2), (i % 2 + 1) * (W // 2) if i % 2 == 0 else W, (i // 2 + 1) * (H // 2) if i < 2 else H)
                        base.paste(_cover(panel, box[2] - box[0], box[3] - box[1]), box[:2])
                        if body.get('target') == 'cuerpo':
                            d = perfil_dir('cuerpos'); rel = f'assets/perfil/cuerpos/cuerpo-{stamp}.jpg'; base.save(os.path.join(casa(), rel), quality=92)
                            it = {'id': 'cuerpo-' + stamp, 'nombre': body.get('nombre') or 'Ficha de cuerpo', 'img': rel, 't': time.strftime('%Y-%m-%d %H:%M')}; P.setdefault('cuerpos', []).insert(0, it)
                        else:
                            d = perfil_dir('fichas360'); rel = f'assets/perfil/fichas360/ficha-{stamp}.jpg'; base.save(os.path.join(casa(), rel), quality=92)
                            it = {'id': 'ficha-' + stamp, 'nombre': body.get('nombre') or 'Ficha 360', 'img': rel, 't': time.strftime('%Y-%m-%d %H:%M')}; P.setdefault('fichas360', []).insert(0, it)
                    elif act == 'alt_add':   # guarda una vista generada en el historial de esa ficha (360 o cuerpo)
                        A = P.setdefault('alt', {}).setdefault(body.get('kind') or '360', {}).setdefault(body.get('view') or 'frente', [])
                        f = (body.get('file') or '').split('?')[0]
                        if f and f not in A: A.insert(0, f)
                        it = None
                    elif act == 'add_cuerpo':
                        d = perfil_dir('cuerpos'); rel = f'assets/perfil/cuerpos/cuerpo-{stamp}.jpg'; Image.open(_abs(body.get('panel'))).convert('RGB').save(os.path.join(casa(), rel), quality=92)
                        it = {'id': 'cuerpo-' + stamp, 'nombre': body.get('nombre') or 'Ficha de cuerpo nueva', 'img': rel, 't': time.strftime('%Y-%m-%d %H:%M')}; P.setdefault('cuerpos', []).insert(0, it)
                    elif act == 'principal_cuerpo':
                        L = P.setdefault('cuerpos', []); it = next((c for c in L if c['id'] == body.get('id')), None)
                        if not it: return self._json(404, {'error': 'ficha de cuerpo no encontrada'})
                        prev = P.get('cuerpo')
                        if prev and not any(c['img'].split('?')[0] == prev.split('?')[0] for c in L): L.append({'id': 'cuerpo-anterior-' + stamp, 'nombre': 'Ficha de cuerpo anterior', 'img': prev, 't': time.strftime('%Y-%m-%d %H:%M')})
                        P['cuerpo'] = it['img']
                    else: return self._json(400, {'error': 'acción desconocida'})
                    _cat_save(head, C)
            except Exception as e: return self._json(400, {'error': str(e)})
            plog(f'ficha_panel {act}'); return self._json(200, {'ok': True, 'item': it if act != 'principal_cuerpo' else None, 'perfil': {k: P.get(k) for k in ('ficha', 'cuerpo', 'fichas360', 'cuerpos', 'alt')}})
        if self.path == '/api/fichas360':   # fichas 360 extra de Aria: 4 vistas aprobadas → rejilla 2x2 de 1600x2400; también «hacer principal» y borrar
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(n) or b'{}'); act = body.get('action') or 'save'
            import re as _re, shutil
            from PIL import Image
            d = perfil_dir('fichas360')
            with _cerrojo():
                head, C = _cat_load(); L = C['perfil'].setdefault('fichas360', [])
                it = next((f for f in L if f['id'] == body.get('id')), None)
                if act == 'delete':
                    if not it: return self._json(404, {'error': 'ficha no encontrada'})
                    trash = papelera()
                    fp = busca(it['img'], propio=True)   # solo se mueve lo que es de la cuenta
                    if fp and it['img'].split('?')[0] != C['perfil']['ficha'].split('?')[0]: shutil.move(fp, os.path.join(trash, os.path.basename(fp)))
                    C['perfil']['fichas360'] = [f for f in L if f['id'] != it['id']]
                elif act == 'principal':
                    if not it: return self._json(404, {'error': 'ficha no encontrada'})
                    prev = C['perfil']['ficha']
                    if not any(f['img'].split('?')[0] == prev.split('?')[0] for f in L): L.append({'id': 'anterior-' + str(int(time.time())), 'nombre': 'Ficha 360 anterior', 'img': prev, 't': time.strftime('%Y-%m-%d %H:%M')})
                    C['perfil']['ficha'] = it['img']
                else:
                    W, H = 800, 1200; out = Image.new('RGB', (W * 2, H * 2), (200, 198, 196))
                    for i, k in enumerate(('frente', 'perfil', 'tres', 'espalda')):
                        fp = busca((body.get('vistas') or {}).get(k))
                        if not fp: return self._json(400, {'error': f'falta la vista {k}'})
                        im = Image.open(fp).convert('RGB'); w, h = im.size
                        if w / h > W / H: nw = int(h * W / H); im = im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
                        else: nh = int(w * H / W); y0 = min(int((h - nh) * 0.2), h - nh); im = im.crop((0, y0, w, y0 + nh))
                        out.paste(im.resize((W, H), Image.LANCZOS), ((i % 2) * W, (i // 2) * H))
                    fid = _re.sub(r'[^a-z0-9]+', '-', (body.get('nombre') or 'ficha').lower()).strip('-')[:40] + '-' + str(int(time.time()))
                    out.save(os.path.join(d, fid + '.jpg'), quality=92)
                    L.insert(0, {'id': fid, 'nombre': body.get('nombre') or 'Ficha 360', 'img': f'assets/perfil/fichas360/{fid}.jpg', 'prenda': body.get('prenda'), 'peinado': body.get('peinado'), 'notas': body.get('notas') or '', 't': time.strftime('%Y-%m-%d %H:%M')}); C['perfil']['fichas360'] = L
                _cat_save(head, C)
            plog(f'fichas 360: {act}'); return self._json(200, {'ok': True, 'list': C['perfil']['fichas360'], 'ficha': C['perfil']['ficha']})
        if self.path == '/api/pendientes':   # {claim: rid} → la página ya lo ha recogido
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(n) or b'{}')
            for rid in ([body.get('claim')] if body.get('claim') else []) + list(body.get('claims') or []):
                if _mio(rid): jobs[rid]['claimed'] = True
            return self._json(200, {'ok': True})
        if self.path == '/api/errores':   # lo que revienta en la página de alguien: una línea por error en errores.jsonl (baja con la copia de cada noche)
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(min(n, 20000)) or b'{}')
            try:
                quien = uid() or 'local'; ahora = time.time(); L = _ERR_N.setdefault(quien, []); L[:] = [t for t in L if ahora - t < 3600]
                if len(L) < 40 and isinstance(body, dict):
                    L.append(ahora); fp = os.path.join(DATOS or RAIZ, 'errores.jsonl')
                    if os.path.isfile(fp) and os.path.getsize(fp) > 3000000: os.replace(fp, fp + '.1')
                    reg = {'t': time.strftime('%Y-%m-%d %H:%M:%S'), 'cuenta': quien}
                    for k in ('tipo', 'msg', 'donde', 'pila', 'tab', 'web', 'ua', 'w', 'h', 'z'): 
                        if k in body: reg[k] = body[k] if not isinstance(body[k], str) else body[k][:1500]
                    with open(fp, 'a', encoding='utf-8') as fh: fh.write(json.dumps(reg, ensure_ascii=False) + '\n')
            except Exception: pass
            return self._json(200, {'ok': True})
        if self.path == '/api/feedback':   # feedback de las secciones en desarrollo → base «💬 Feedback de ARIA STUDIO» de Notion (+ copia en assets/feedback)
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(n) or b'{}')
            texto = (body.get('texto') or '').strip(); audio = body.get('audio') or ''; arel = ''
            if isinstance(audio, str) and audio.startswith('data:audio/') and ',' in audio and len(audio) < 6 * 1024 * 1024:
                try:
                    cab, b64 = audio.split(',', 1); ext = 'm4a' if ('mp4' in cab or 'aac' in cab) else 'ogg' if 'ogg' in cab else 'webm'
                    ad = os.path.join(casa(), 'feedback_audio') if SERVIDOR else os.path.join(ROOT, 'assets', 'feedback'); os.makedirs(ad, exist_ok=True)
                    an = time.strftime('%Y%m%d-%H%M%S') + '.' + ext; open(os.path.join(ad, an), 'wb').write(base64.b64decode(b64)); arel = ('feedback_audio/' if SERVIDOR else 'assets/feedback/') + an
                except Exception as e: plog('feedback: audio ✕ ' + str(e))
            if not texto and arel: texto = '(nota de voz sin transcribir: ' + arel + ')'
            if not texto: return self._json(400, {'error': 'el comentario está vacío'})
            rec = {'t': time.strftime('%Y-%m-%d %H:%M:%S'), 'texto': texto, 'tipo': body.get('tipo') or '💬 Comentario', 'via': body.get('via') or '⌨️ Escrito', 'seccion': (body.get('seccion') or '')[:300], 'contexto': (body.get('contexto') or '')[:1800], 'usuario': body.get('usuario') or 'Max (local)', **({'audio': arel} if arel else {})}
            if SERVIDOR:   # en servidor: al registro común, con el correo de la sesión (lo que diga el navegador en «usuario» no cuenta); sin Notion
                rec.update({'texto': texto[:6000], 'tipo': str(rec['tipo'])[:60], 'via': str(rec['via'])[:60], 'usuario': getattr(_ctx, 'email', ''), 'uid': uid()})
                open(os.path.join(DATOS, 'feedback.jsonl'), 'a').write(json.dumps(rec, ensure_ascii=False) + '\n'); return self._json(200, {'ok': True})
            d = os.path.join(ROOT, 'assets', 'feedback'); os.makedirs(d, exist_ok=True); open(os.path.join(d, 'feedback.jsonl'), 'a').write(json.dumps(rec, ensure_ascii=False) + '\n')
            try:
                tok = next((l.strip().split('=', 1)[1] for l in open(os.path.expanduser('~/.claude/notion.env')) if l.startswith('NOTION_TOKEN=')), None)
                if not tok: raise RuntimeError('sin token de Notion')
                rt = lambda s0: [{'text': {'content': s0[i:i + 1900]}} for i in range(0, min(len(s0), 5700), 1900)] or [{'text': {'content': ''}}]
                page = {'parent': {'database_id': '84c6d274bbb94895b8c8b94214e9026e'}, 'properties': {
                    'Comentario': {'title': [{'text': {'content': (texto[:120] + ('…' if len(texto) > 120 else ''))}}]}, 'Estado': {'select': {'name': '📥 Nuevo'}},
                    'Tipo': {'select': {'name': rec['tipo']}}, 'Vía': {'select': {'name': rec['via']}}, 'Sección': {'rich_text': rt(rec['seccion'])}, 'Usuario': {'rich_text': rt(rec['usuario'])}, 'Contexto': {'rich_text': rt(rec['contexto'])}},
                    'children': [{'object': 'block', 'type': 'paragraph', 'paragraph': {'rich_text': rt(texto)}}]}
                rq = urllib.request.Request('https://api.notion.com/v1/pages', data=json.dumps(page).encode(), method='POST', headers={'Authorization': 'Bearer ' + tok, 'Notion-Version': '2022-06-28', 'Content-Type': 'application/json'})
                res = json.loads(urllib.request.urlopen(rq, timeout=30).read()); plog('feedback → Notion · ' + texto[:60]); return self._json(200, {'ok': True, 'url': res.get('url')})
            except Exception as e:
                plog('feedback ✕ Notion: ' + str(e)[:200]); return self._json(200, {'ok': True, 'local': True, 'aviso': 'guardado en local; Notion no respondió'})
        if self.path == '/api/perfil':   # datos editables del perfil de Aria + sincronizar prompt base ↔ datos (Gemini 2.5 Flash por WaveSpeed, céntimos)
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(n) or b'{}'); act = body.get('action') or 'set'
            OK_KEYS = {'bio', 'basePrompt', 'name', 'handle', 'tagline', 'ig.url', 'ig.followers', 'ig.posts', 'datos.edad', 'datos.altura', 'datos.origen', 'datos.idiomas', 'datos.nacida', 'datos.rasgos', 'datos.personalidad', 'datos.voz'}
            def _load():
                return _cat_load()
            def _save(head, C): _cat_save(head, C)
            def _put(P, k, v):
                if '.' in k: a, b = k.split('.', 1); P.setdefault(a, {})[b] = v
                else: P[k] = v
            def _llm(prompt, mx=400):
                r = ws('POST', '/api/v3/wavespeed-ai/any-llm', {'prompt': prompt, 'model': 'google/gemini-2.5-flash', 'temperature': 0.2, 'max_tokens': mx, 'priority': 'latency'}); rid = (r.get('data') or {}).get('id')
                for _ in range(40):
                    time.sleep(1.2); w = ws('GET', f'/api/v3/predictions/{rid}/result').get('data') or {}
                    if w.get('status') == 'completed': o = w.get('outputs') or []; return str(o[0] if isinstance(o, list) and o else o).strip()
                    if w.get('status') == 'failed': raise RuntimeError(w.get('error') or 'falló')
                raise RuntimeError('sin respuesta')
            try:
                changed = []
                if act == 'set':
                    with _cerrojo():
                        head, C = _load(); P = C['perfil']
                        for k, v in (body.get('set') or {}).items():
                            if k in OK_KEYS: _put(P, k, v); changed.append(k)
                        _save(head, C)
                elif act == 'avatar':   # foto de perfil: el recorte (512x512) + la imagen de origen y su encuadre para poder volver a centrarla
                    import io
                    from PIL import Image
                    d = perfil_dir('avatar'); st = str(int(time.time()))
                    du = body.get('data') or ''
                    if ',' not in du: raise RuntimeError('falta la imagen')
                    im = Image.open(io.BytesIO(base64.b64decode(du.split(',', 1)[1]))).convert('RGB'); im = im.resize((512, 512), Image.LANCZOS); im.save(os.path.join(d, f'avatar-{st}.jpg'), quality=92)
                    src = body.get('src') or ''
                    if src.startswith('data:'):
                        sim = Image.open(io.BytesIO(base64.b64decode(src.split(',', 1)[1]))).convert('RGB'); sim.thumbnail((1600, 1600)); sim.save(os.path.join(d, f'origen-{st}.jpg'), quality=92); src = f'assets/perfil/avatar/origen-{st}.jpg'
                    with _cerrojo():
                        head, C = _load(); P = C['perfil']
                        if P.get('avatar'): P.setdefault('avatares', []).insert(0, P['avatar'])
                        P['avatar'] = f'assets/perfil/avatar/avatar-{st}.jpg'; P['avatarSrc'] = src.split('?')[0] if src else P.get('avatarSrc'); P['avatarCrop'] = body.get('crop'); changed.append('avatar')
                        for ch in (C.get('chars') or []):
                            if ch.get('id') == 'aria': ch['avatar'] = P['avatar']
                        _save(head, C)
                elif act == 'sync':
                    head, C = _load(); P = C['perfil']; D = P.get('datos') or {}; cur = {k: D.get(k) for k in ('edad', 'altura', 'origen', 'rasgos')}
                    if body.get('from') == 'prompt':   # el prompt base cambió → sus datos (edad, altura, origen, rasgos)
                        out = _llm('You maintain the character sheet of an AI influencer. Her current data (Spanish) as JSON: ' + json.dumps(cur, ensure_ascii=False) + '. Her base prompt (English) was just edited to: <<<' + (P.get('basePrompt') or '') + '>>>. '
                                   'Update ONLY what the new prompt changes or adds about her age, height, origin and physical traits (hair, eyes, glasses, earrings, skin, tattoos, makeup, swimwear…). Keep the Spanish wording and short tag style of the existing values; keep every value the prompt does not contradict exactly as it is. '
                                   'Answer with ONLY the JSON object with exactly these keys: edad, altura, origen, rasgos (a list of short Spanish tags).', 500)
                        m = re.search(r'\{.*\}', out, re.S); new = json.loads(m.group(0)) if m else {}
                        with _cerrojo():
                            head, C = _load(); P = C['perfil']; D = P.setdefault('datos', {})
                            for k in ('edad', 'altura', 'origen', 'rasgos'):
                                v = new.get(k)
                                if v and v != D.get(k) and (k != 'rasgos' or isinstance(v, list)): D[k] = v; changed.append('datos.' + k)
                            _save(head, C)
                    else:   # cambiaron sus datos → el prompt base se reescribe solo en lo necesario
                        out = _llm('Here is the base prompt (English) of an AI influencer: <<<' + (P.get('basePrompt') or '') + '>>>. Her data (Spanish) is now: ' + json.dumps(cur, ensure_ascii=False) + '. '
                                   'Rewrite the base prompt so it matches this data: change only what is needed, keep the same style, structure and length, keep every other sentence exactly as it is, write it in English. Answer with the prompt only.', 500)
                        out = out.strip().strip('<>').strip().strip('"').strip()
                        if out and out != P.get('basePrompt'):
                            with _cerrojo():
                                head, C = _load(); P = C['perfil']; P['basePrompt'] = out; changed.append('basePrompt'); _save(head, C)
                else: return self._json(400, {'error': 'acción desconocida'})
            except Exception as e: return self._json(400, {'error': str(e)})
            plog(f'perfil {act} · ' + ', '.join(changed)); return self._json(200, {'ok': True, 'changed': changed, 'perfil': {k: P.get(k) for k in ('name', 'handle', 'tagline', 'bio', 'basePrompt', 'datos', 'avatar', 'avatarSrc', 'avatarCrop', 'ig')}})
        if self.path == '/api/ficha_combo':   # ficha principal combinada: 2x2 de la cara + cuerpo entero de frente + cuerpo entero de perfil (del cuello a los pies), 4267x2400 (16:9)
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(n) or b'{}'); act = body.get('action') or 'ensure'
            if act not in ('ensure', 'preview') and aria_fija(): return self._json(403, {'error': FIJA, 'fija': True})
            import re as _re
            from PIL import Image, ImageStat
            CW, CH, GAP, BW, SW = 1600, 2400, 16, 1317, 1318; TW = CW + GAP + BW + GAP + SW; BG = (200, 198, 196); dd = perfil_dir('combo')
            def _abs(rel):
                fp = busca(rel)   # la casa de la cuenta o la biblioteca común; nada más
                if not fp: raise RuntimeError('no existe ' + str(rel)[:200])
                return fp
            def _cover(im, W, H, yb=0.15):
                w, h = im.size
                if w / h > W / H: nw = int(h * W / H); im = im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
                else: nh = int(w * H / W); y0 = min(int((h - nh) * yb), h - nh); im = im.crop((0, y0, w, y0 + nh))
                return im.resize((W, H), Image.LANCZOS)
            def _body_default(P, i, W):   # vista de su ficha de cuerpo: 0 = frente, 1 = perfil (tercios de la imagen), centrada en la figura
                im = Image.open(_abs(P.get('cuerpo'))).convert('RGB'); w, h = im.size; x0, x1 = w * i // 3, w * (i + 1) // 3
                g = im.crop((x0, 0, x1, h)).convert('L').resize(((x1 - x0) // 4, h // 4)); gw, gh = g.size; px = g.load(); bgv = sorted(px[x, 2] for x in range(gw))[gw // 2]
                cols = [x for x in range(gw) if sum(1 for y in range(0, gh, 2) if abs(px[x, y] - bgv) > 28) > gh * 0.04]
                cx = x0 + ((cols[0] + cols[-1]) / 2 * 4 if cols else (x1 - x0) / 2); nw = int(h * W / CH); l = int(max(x0, min(x1 - nw, cx - nw / 2))) if x1 - x0 >= nw else int(max(0, min(w - nw, cx - nw / 2)))
                return im.crop((l, 0, l + nw, h)).resize((W, CH), Image.LANCZOS)
            def _compose(ficha_rel, body_rel, side_rel, P):
                out = Image.new('RGB', (TW, CH), BG); out.paste(_cover(Image.open(_abs(ficha_rel)).convert('RGB'), CW, CH, 0.2), (0, 0))
                out.paste(_cover(Image.open(_abs(body_rel)).convert('RGB'), BW, CH, 0.0) if body_rel else _body_default(P, 0, BW), (CW + GAP, 0))
                out.paste(_cover(Image.open(_abs(side_rel)).convert('RGB'), SW, CH, 0.0) if side_rel else _body_default(P, 1, SW), (CW + GAP + BW + GAP, 0)); return out
            def _save(im, stem):
                fn = f'{stem}-{int(time.time() * 1000)}.jpg'; im.save(os.path.join(dd, fn), quality=92); th = im.copy(); th.thumbnail((1200, 1200)); th.save(os.path.join(dd, fn[:-4] + '_t.jpg'), quality=85)
                return 'assets/perfil/combo/' + fn, 'assets/perfil/combo/' + fn[:-4] + '_t.jpg'
            def _seam(g, lo, hi):
                w, h = g.size; best, bs = int(w * (lo + hi) / 2), 99
                for x in range(int(w * lo), int(w * hi)):
                    sd = ImageStat.Stat(g.crop((x, int(h * 0.03), x + 1, int(h * 0.97)))).stddev[0]
                    if sd < bs: best, bs = x, sd
                return best
            def _split(im):   # ficha combinada generada → (2x2, cuerpo de frente, cuerpo de perfil o None si es de las antiguas de 5 imágenes)
                g = im.convert('L'); w, h = g.size; gw = max(2, int(w * GAP / TW))
                if w / h < 1.55:   # antigua: 2x2 + un solo cuerpo
                    x1 = _seam(g, 0.46, 0.54); return im.crop((0, 0, x1, h)), im.crop((min(w - 2, x1 + gw), 0, w, h)), None
                x1 = _seam(g, 0.33, 0.42); x2 = _seam(g, 0.64, 0.73)
                return im.crop((0, 0, x1, h)), im.crop((min(w - 2, x1 + gw), 0, x2, h)), im.crop((min(w - 2, x2 + gw), 0, w, h))
            try:
                with _cerrojo():
                    head, C = _cat_load(); P = C['perfil']; out = {}
                    SIG = lambda: (P.get('ficha') or '') + '|' + (P.get('comboBody') or P.get('cuerpo') or '') + '|' + (P.get('comboSide') or P.get('cuerpo') or ''); changed = False
                    def _recompose(): P['combo'], P['comboThumb'] = _save(_compose(P['ficha'], P.get('comboBody'), P.get('comboSide'), P), 'principal'); P['comboSig'] = SIG()
                    if act == 'ensure':
                        if not (P.get('combo') and P.get('comboSig') == SIG() and busca(P['combo'])): _recompose(); changed = True
                    elif act == 'preview':   # para el editor: cómo quedaría con otra 2x2, otro cuerpo o otro perfil (no cambia nada)
                        rel, th = _save(_compose(body.get('ficha') or P['ficha'], body.get('body') or P.get('comboBody'), body.get('side') or P.get('comboSide'), P), 'preview'); out['preview'] = rel
                    elif act == 'set_body':   # el cuerpo de frente (which=front) o de perfil (which=side) de la principal pasa a ser otro; el anterior queda en su historial
                        k = 'comboSide' if body.get('which') == 'side' else 'comboBody'
                        im = Image.open(_abs(body.get('file'))).convert('RGB'); fn = f'{"lado" if k == "comboSide" else "cuerpo"}-{int(time.time())}.jpg'; im.save(os.path.join(dd, fn), quality=92)
                        if P.get(k): P.setdefault(k + 's', []).insert(0, P[k])
                        P[k] = 'assets/perfil/combo/' + fn; _recompose(); changed = True
                    elif act == 'save' and any(f.get('from') == body.get('file') for f in P.get('fichas') or []):
                        out['item'] = next(f for f in P['fichas'] if f.get('from') == body.get('file'))
                    elif act == 'save':   # ficha combinada generada de una vez → Fichas creadas
                        src = Image.open(_abs(body.get('file'))).convert('RGB'); fid = _re.sub(r'[^a-z0-9]+', '-', (body.get('nombre') or 'ficha').lower()).strip('-')[:40] + '-' + str(int(time.time()))
                        d2 = perfil_dir('fichas'); src.save(os.path.join(d2, fid + '.jpg'), quality=92); th = src.copy(); th.thumbnail((900, 900)); th.save(os.path.join(d2, fid + '_t.jpg'), quality=85)
                        it = {'id': fid, 'nombre': body.get('nombre') or 'Ficha', 'layout': 'combo', 'prendas': body.get('prendas') or [], 'extras': body.get('extras') or [], 'acc': body.get('acc') or [], 'img': f'assets/perfil/fichas/{fid}.jpg', 'thumb': f'assets/perfil/fichas/{fid}_t.jpg', 'from': body.get('file'), 't': body.get('t') or time.strftime('%Y-%m-%d %H:%M'), 'size': [src.width, src.height], 'modelo': body.get('modelo') or ''}
                        P.setdefault('fichas', []).insert(0, it); out['item'] = it; changed = True
                    elif act == 'principal':   # una ficha combinada pasa a ser la principal: su 2x2 → ficha 360 de toda la app; sus cuerpos → los de la principal
                        L = P.setdefault('fichas', []); it = next((f for f in L if f['id'] == body.get('id')), None)
                        if not it: return self._json(404, {'error': 'ficha no encontrada'})
                        if P.get('combo') and not any(f.get('img', '').split('?')[0] == P['combo'].split('?')[0] for f in L):   # la principal de ahora no se pierde
                            L.append({'id': 'principal-anterior-' + str(int(time.time())), 'nombre': 'Ficha principal anterior', 'layout': 'combo', 'img': P['combo'], 'thumb': P.get('comboThumb') or P['combo'], 'vistas': P['ficha'], 'cuerpo': P.get('comboBody') or '', 'lado': P.get('comboSide') or '', 'default_body': not P.get('comboBody'), 'default_side': not P.get('comboSide'), 't': time.strftime('%Y-%m-%d %H:%M')})
                        if it.get('vistas') and busca(it['vistas']):
                            a = Image.open(_abs(it['vistas'])).convert('RGB'); b = Image.open(_abs(it['cuerpo'])).convert('RGB') if it.get('cuerpo') else None; c = Image.open(_abs(it['lado'])).convert('RGB') if it.get('lado') else None
                        else: a, b, c = _split(Image.open(_abs(it['img'])).convert('RGB'))
                        d3 = perfil_dir('fichas360'); st = str(int(time.time()))
                        fa = f'assets/perfil/fichas360/ficha-{st}.jpg'; _cover(a, CW, CH, 0.2).save(os.path.join(casa(), fa), quality=92); P['ficha'] = fa
                        for img_, k, stem in ((b, 'comboBody', 'cuerpo'), (c, 'comboSide', 'lado')):
                            if img_ is not None: fb = f'assets/perfil/combo/{stem}-{st}.jpg'; img_.save(os.path.join(casa(), fb), quality=92); P[k] = fb
                            else: P.pop(k, None)
                        if it.get('vistas') or (it.get('size') and it['size'][0] / it['size'][1] < 1.55): _recompose()   # las antiguas se recomponen al formato nuevo
                        else: P['combo'], P['comboThumb'] = it['img'], it.get('thumb') or it['img']; P['comboSig'] = SIG()
                        changed = True
                    elif act == 'delete':
                        L = P.setdefault('fichas', []); it = next((f for f in L if f['id'] == body.get('id')), None)
                        if not it: return self._json(404, {'error': 'ficha no encontrada'})
                        P['fichas'] = [f for f in L if f['id'] != it['id']]; changed = True
                    else: return self._json(400, {'error': 'acción desconocida'})
                    if changed: _cat_save(head, C)
            except Exception as e: return self._json(400, {'error': str(e)})
            plog(f'ficha_combo {act}'); out.update({'ok': True, 'perfil': {k: P.get(k) for k in ('ficha', 'cuerpo', 'combo', 'comboThumb', 'comboSig', 'comboBody', 'comboBodys', 'comboSide', 'comboSides', 'fichas', 'fichas360', 'cuerpos', 'alt')}}); return self._json(200, out)
        if self.path == '/api/fichas_outfit':   # fichas para vídeo: las 4 vistas con la ropa elegida + el cuerpo entero a la derecha, en una sola imagen
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(n) or b'{}'); act = body.get('action') or 'save'
            import re as _re, shutil
            from PIL import Image
            d = perfil_dir('fichas')
            with _cerrojo():
                head, C = _cat_load(); L = C['perfil'].setdefault('fichas', [])
                if act == 'delete':
                    fid = body.get('id'); it = next((f for f in L if f['id'] == fid), None)
                    if not it: return self._json(404, {'error': 'ficha no encontrada'})
                    trash = papelera()
                    for k in ('img', 'thumb'):
                        fp = busca(it.get(k), propio=True)   # solo se mueve lo que es de la cuenta
                        if fp: shutil.move(fp, os.path.join(trash, os.path.basename(fp)))
                    C['perfil']['fichas'] = [f for f in L if f['id'] != fid]
                else:
                    src = {}
                    for k in ('vistas', 'cuerpo'):
                        fp = busca(body.get(k))
                        if not fp: return self._json(400, {'error': f'falta la imagen {k}'})
                        src[k] = Image.open(fp).convert('RGB')
                    H = 2400; a = src['vistas']; a = a.resize((round(a.width * H / a.height), H), Image.LANCZOS); b2 = src['cuerpo']; b2 = b2.resize((round(b2.width * H / b2.height), H), Image.LANCZOS)
                    gap = 16; out = Image.new('RGB', (a.width + gap + b2.width, H), (200, 198, 196)); out.paste(a, (0, 0)); out.paste(b2, (a.width + gap, 0))
                    fid = _re.sub(r'[^a-z0-9]+', '-', (body.get('nombre') or 'ficha').lower()).strip('-')[:40] + '-' + str(int(time.time()))
                    out.save(os.path.join(d, fid + '.jpg'), quality=92); th = out.copy(); th.thumbnail((720, 720)); th.save(os.path.join(d, fid + '_t.jpg'), quality=85)
                    it = {'id': fid, 'nombre': body.get('nombre') or 'Ficha', 'prendas': body.get('prendas') or [], 'extras': body.get('extras') or [], 'notas': body.get('notas') or '', 'img': f'assets/perfil/fichas/{fid}.jpg', 'thumb': f'assets/perfil/fichas/{fid}_t.jpg', 'vistas': body.get('vistas'), 'cuerpo': body.get('cuerpo'), 't': time.strftime('%Y-%m-%d %H:%M'), 'size': [out.width, out.height]}
                    L.insert(0, it); C['perfil']['fichas'] = L
                _cat_save(head, C)
            plog(f'fichas para vídeo: {act}'); return self._json(200, {'ok': True, 'list': C['perfil']['fichas']})
        if self.path == '/api/personas_img':   # quién sale en una imagen: una caja y una frase por persona, para repartir personajes («¿Quién es quién?»)
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(n) or b'{}')
            try:
                img = body['image'] if isinstance(body.get('image'), dict) else {'path': body.get('image')}
                pt = body.get('punto') if isinstance(body.get('punto'), list) and len(body.get('punto')) == 2 and all(isinstance(v, (int, float)) for v in body.get('punto')) else None
                ck = None if pt else _ppl_key(img)
                if ck and _PPL.get(ck): plog('personas_img · ya leída'); return self._json(200, {'ok': True, 'people': _PPL[ck], 'cache': True})
                url = resolve_ws(img)
                ask = ((f'Look at the person located at the point that is {round(float(pt[0]) * 100)}% of the image width from the left edge and {round(float(pt[1]) * 100)}% of the image height from the top edge: the person whose body covers that point or is closest to it. Answer with ONLY a JSON array with exactly ONE element (that person) and nothing else. ' if pt else
                        'Detect every clearly visible person in this image (maximum 6), ordered from left to right. Skip tiny far-away people in the background (smaller than about one eighth of the image height). Answer with ONLY a JSON array and nothing else. ') +
                       ('Each element is an object with three keys: "box": [x0, y0, x1, y1] as fractions between 0 and 1 of the image width and height, covering the whole visible body of that person; '
                       '"desc": a short English phrase that identifies that person unambiguously by position and look, starting with "the", for example "the woman on the left with long blonde hair and a red dress"; '
                       '"es": that same phrase translated into natural Spanish, for example "la mujer de la izquierda, de pelo largo rubio y vestido rojo".'))
                r = ws('POST', '/api/v3/wavespeed-ai/any-llm/vision', {'prompt': ask, 'images': [url], 'model': 'google/gemini-2.5-flash', 'temperature': 0.1, 'max_tokens': 1200, 'priority': 'latency'})
                rid = (r.get('data') or {}).get('id'); txt = ''
                for _ in range(50):
                    time.sleep(1.5); w = ws('GET', f'/api/v3/predictions/{rid}/result').get('data') or {}
                    if w.get('status') == 'completed': o = w.get('outputs') or []; txt = (o[0] if o else '') if isinstance(o, list) else str(o); break
                    if w.get('status') == 'failed': raise RuntimeError(w.get('error') or 'falló')
                m = re.search(r'\[.*\]', str(txt), re.S)
                if not m: raise RuntimeError('respuesta sin datos')
                people = []
                for q in json.loads(m.group(0))[:6]:
                    b = q.get('box') if isinstance(q, dict) else None
                    if not (isinstance(b, list) and len(b) == 4 and all(isinstance(v, (int, float)) for v in b)): continue
                    if max(b) > 1.5: b = [v / 1000.0 for v in b]   # algunos modelos contestan de 0 a 1000
                    x0, y0, x1, y1 = [max(0.0, min(1.0, float(v))) for v in b]
                    if x1 - x0 < 0.03 or y1 - y0 < 0.03: continue
                    people.append({'box': [round(x0, 4), round(y0, 4), round(x1, 4), round(y1, 4)], 'desc': str(q.get('desc') or 'the person').strip()[:160], 'es': str(q.get('es') or '').strip()[:180]})
                people.sort(key=lambda z: z['box'][0])
                if ck and people: _PPL[ck] = people; _ppl_save()
            except Exception as e: return self._json(400, {'error': str(e)})
            plog(f'personas_img ok · {len(people)} persona(s)'); return self._json(200, {'ok': True, 'people': people, 'person': (people[0] if pt and people else None)})
        if self.path == '/api/lugares':   # lugares de un personaje (su casa, su despacho…): {owner:'aria'|id, list:[{id,name,tags,desc,img,thumb}], files:{id: dataURL}}
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(n) or b'{}'); owner = body.get('owner') or 'aria'
            L = [x for x in (body.get('list') or []) if isinstance(x, dict)][:80]; files = body.get('files') or {}
            if owner == 'aria' and aria_fija(): return self._json(403, {'error': FIJA, 'fija': True})
            import io
            from PIL import Image
            try:
                with _cerrojo():
                    if owner == 'aria': d = perfil_dir('lugares'); relb = 'assets/perfil/lugares/'
                    else:
                        if not _pid_ok(owner) or not os.path.isdir(os.path.join(pers_dir(), owner)): return self._json(404, {'error': 'personaje no encontrado'})
                        d = os.path.join(pers_dir(), owner, 'lugares'); relb = f'assets/personajes/{owner}/lugares/'
                    os.makedirs(d, exist_ok=True); stamp = int(time.time()); out = []
                    for c in L:
                        cid = re.sub(r'[^a-z0-9-]+', '-', str(c.get('id') or 'lugar').lower()).strip('-')[:40] or 'lugar'
                        it = {'id': cid, 'name': str(c.get('name') or 'Lugar')[:60], 'desc': str(c.get('desc') or '')[:600], 'tags': [str(t)[:20] for t in (c.get('tags') or []) if isinstance(t, str)][:4], 'img': c.get('img'), 'thumb': c.get('thumb')}
                        du = files.get(cid)
                        if isinstance(du, str) and ',' in du:
                            im = Image.open(io.BytesIO(base64.b64decode(du.split(',', 1)[1]))).convert('RGB'); im.thumbnail((2000, 2000)); im.save(os.path.join(d, cid + '.jpg'), quality=90)
                            th = im.copy(); th.thumbnail((720, 720)); th.save(os.path.join(d, cid + '_t.jpg'), quality=85)
                            it['img'] = relb + cid + '.jpg' + f'?v={stamp}'; it['thumb'] = relb + cid + '_t.jpg' + f'?v={stamp}'
                        if not (isinstance(it['img'], str) and it['img'].split('?')[0].startswith(relb)): continue   # solo imágenes de su propia carpeta
                        out.append(it)
                    vivos = {x['id'] for x in out}
                    for fn in os.listdir(d):   # lo quitado se borra de su carpeta
                        if fn.endswith('.jpg') and fn.replace('_t.jpg', '').replace('.jpg', '') not in vivos:
                            try: os.remove(os.path.join(d, fn))
                            except OSError: pass
                    if owner == 'aria':
                        head, C = _cat_load(); C['perfil']['lugares'] = out
                        _cat_save(head, C)
                    else:
                        fp = os.path.join(pers_dir(), owner, 'personaje.json'); P = json.load(open(fp)); P['lugares'] = out; json.dump(P, open(fp, 'w'), ensure_ascii=False, indent=1)
            except Exception as e: return self._json(400, {'error': str(e)})
            plog(f'lugares de {owner}: {len(out)}'); return self._json(200, {'ok': True, 'list': out})
        if self.path == '/api/acc_cajas':   # dónde está cada complemento en la ficha del personaje, para recortar de ahí su portada
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(n) or b'{}')
            try:
                img = body['image'] if isinstance(body.get('image'), dict) else {'path': body.get('image')}
                items = [x for x in (body.get('items') or []) if isinstance(x, dict) and x.get('id')][:8]
                if not items: raise RuntimeError('faltan los complementos')
                url = resolve_ws(img)
                ask = ('This image is the reference sheet of ONE character (several views of the same person). Find each of these accessories on the person: '
                       + '; '.join(f'{i + 1}) {str(x.get("nombre") or "")[:40]} ({str(x.get("desc") or "")[:160]})' for i, x in enumerate(items))
                       + '. Answer with ONLY a JSON array and nothing else: one object per accessory that is clearly visible, as {"n": its number, "box_2d": [ymin, xmin, ymax, xmax]}, '
                       'where box_2d is the tight bounding box of that accessory in the view where it is seen biggest and clearest (prefer a close-up of the face for glasses, earrings and necklaces), normalized to 0-1000. Skip the ones you cannot see.')
                r = ws('POST', '/api/v3/wavespeed-ai/any-llm/vision', {'prompt': ask, 'images': [url], 'model': 'google/gemini-2.5-flash', 'temperature': 0.1, 'max_tokens': 700, 'priority': 'latency'})
                rid = (r.get('data') or {}).get('id'); txt = ''
                for _ in range(50):
                    time.sleep(1.5); w = ws('GET', f'/api/v3/predictions/{rid}/result').get('data') or {}
                    if w.get('status') == 'completed': o = w.get('outputs') or []; txt = (o[0] if o else '') if isinstance(o, list) else str(o); break
                    if w.get('status') == 'failed': raise RuntimeError(w.get('error') or 'falló')
                m = re.search(r'\[.*\]', str(txt), re.S)
                if not m: raise RuntimeError('respuesta sin datos')
                cajas = {}
                for q in json.loads(m.group(0)):
                    b = q.get('box_2d') if isinstance(q, dict) else None
                    try: k = int(q.get('n')) - 1
                    except Exception: continue
                    if not (0 <= k < len(items)) or not (isinstance(b, list) and len(b) == 4 and all(isinstance(v, (int, float)) for v in b)): continue
                    if max(b) > 1.5: b = [v / 1000.0 for v in b]
                    y0, x0, y1, x1 = [max(0.0, min(1.0, float(v))) for v in b]   # el lector contesta [ymin, xmin, ymax, xmax]
                    if x1 - x0 < 0.005 or y1 - y0 < 0.005: continue
                    cajas[items[k]['id']] = [round(x0, 4), round(y0, 4), round(x1, 4), round(y1, 4)]
            except Exception as e: return self._json(400, {'error': str(e)})
            plog(f'acc_cajas ok · {len(cajas)} de {len(items)}'); return self._json(200, {'ok': True, 'cajas': cajas})
        if self.path == '/api/describir':   # descripción profesional de un objeto para el prompt (lee la foto con Gemini 2.5 Flash por WaveSpeed)
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(n) or b'{}')
            try:
                url = resolve_ws(body['image'] if isinstance(body.get('image'), dict) else {'path': body.get('image')})
                ask = _ASK_ESTILO[body.get('modo')] if body.get('modo') in _ASK_ESTILO else ('Look ONLY at the main object in this image' + (' ("' + body['nombre'] + '", type: ' + (body.get('tipo') or 'accessory') + ')' if body.get('nombre') else ' (type: ' + (body.get('tipo') or 'accessory') + ')') + '. Answer with EXACTLY two lines and nothing else. '
                       'Line 1: a short product name in Spanish, 2-5 words, like a shop label (e.g. "Bolso de lona verde", "iPhone 17 Pro naranja"). '
                       'Line 2: a precise English prompt fragment for an AI image generator so it can reproduce the object exactly: one line, 15-35 words, starting with an article (a/an), no full sentences, no people, no background, no brand guesses unless a logo is clearly visible; mention shape, material, color and finish, size and distinctive details.')
                r = ws('POST', '/api/v3/wavespeed-ai/any-llm/vision', {'prompt': ask, 'images': [url], 'model': 'google/gemini-2.5-flash', 'temperature': 0.2, 'max_tokens': 480 if body.get('modo') == 'escena' else 260, 'priority': 'latency'})
                rid = (r.get('data') or {}).get('id'); txt = ''
                for _ in range(40):
                    time.sleep(1.5); w = ws('GET', f'/api/v3/predictions/{rid}/result').get('data') or {}
                    if w.get('status') == 'completed': o = w.get('outputs') or []; txt = (o[0] if o else '') if isinstance(o, list) else str(o); break
                    if w.get('status') == 'failed': raise RuntimeError(w.get('error') or 'falló')
                lines = [re.sub(r'^\s*(line\s*\d\s*[:.-]|\d[.):]|[-*•])\s*', '', x, flags=re.I).strip().strip('"«»').strip() for x in str(txt).strip().splitlines() if x.strip()]
                nombre = lines[0] if len(lines) > 1 else ''; txt = ' '.join(lines[1:]) if len(lines) > 1 else (lines[0] if lines else '')
                if not txt: raise RuntimeError('sin respuesta')
                extra = []
                if body.get('modo') in _ASK_ESTILO and len(lines) > 2: txt = lines[1]; extra = lines[2:]   # expresión: línea 3 = prompt en español, línea 4 = categoría
                ref = None
                if body.get('modo') == 'escena' and isinstance(body.get('image'), dict) and ',' in str(body['image'].get('data') or ''):   # la foto leída se guarda en sus referencias: así «Recrear» puede volver a ponerla aunque no se haya enviado al generador
                    head, b64 = body['image']['data'].split(',', 1); raw, ct = img_norm(base64.b64decode(b64), head.split(':')[1].split(';')[0])
                    ref = f"assets/refs/{hashlib.sha1(raw).hexdigest()[:16]}.{'png' if ct == 'image/png' else 'webp' if ct == 'image/webp' else 'jpg'}"; full = os.path.join(refs_dir(), os.path.basename(ref))
                    if not os.path.exists(full): open(full, 'wb').write(raw)
                plog('describir ok · ' + nombre + ' · ' + txt[:80]); return self._json(200, {'ok': True, 'desc': txt, 'nombre': nombre, 'extra': extra, 'ref': ref})
            except Exception as e: return self._json(400, {'error': str(e)})
        if self.path == '/api/ig':   # seguidores y publicaciones de un perfil PÚBLICO de Instagram: lo que su propia página enseña en la vista previa del enlace (sin iniciar sesión)
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(n) or b'{}')
            m = re.search(r'instagram\.com/([A-Za-z0-9._]{1,30})/?', str(body.get('url') or ''))
            if not m or m.group(1).lower() in ('p', 'reel', 'reels', 'explore', 'stories', 'accounts', 'tv'): return self._json(400, {'error': 'pon el enlace del perfil: https://www.instagram.com/usuario/'})
            try:
                rq = urllib.request.Request(f'https://www.instagram.com/{m.group(1)}/', headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15', 'Accept-Language': 'en-US,en;q=0.9'})
                html = urllib.request.urlopen(rq, timeout=20).read(2000000).decode('utf-8', 'replace')
                d = re.search(r'og:description"\s+content="([^"]*)"', html); t = d.group(1) if d else ''
                fo = re.search(r'([\d.,]+\s?[KMB]?)\s+Followers', t, re.I); po = re.search(r'([\d.,]+\s?[KMB]?)\s+Posts', t, re.I)
                if not fo: return self._json(404, {'error': 'Instagram no ha dado los datos de ese perfil (¿es privado o no existe?). Puedes escribirlos a mano'})
                return self._json(200, {'ok': True, 'user': m.group(1), 'followers': fo.group(1).replace(' ', ''), 'posts': po.group(1).replace(' ', '') if po else ''})
            except Exception as e: return self._json(502, {'error': 'no se ha podido leer Instagram ahora. Puedes escribirlos a mano'})
        if self.path == '/api/complementos':   # complementos de un personaje: {owner:'aria'|id, list:[{id,nombre,tipo,regla,desc,img}], files:{id: dataURL}}
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(n) or b'{}'); owner = body.get('owner') or 'aria'; L = body.get('list') or []
            if owner == 'aria' and aria_fija(): return self._json(403, {'error': FIJA, 'fija': True})
            if body.get('tipos') is not None and not L:   # solo actualizar los tipos propios
                with _cerrojo():
                    head, C = _cat_load(); C['perfil']['accTipos'] = body['tipos']
                    _cat_save(head, C)
                return self._json(200, {'ok': True, 'tipos': body['tipos']})
            import io, re as _re
            from PIL import Image
            with _cerrojo():
                if owner == 'aria': d = perfil_dir('complementos'); relb = 'assets/perfil/complementos/'
                else:
                    if not _pid_ok(owner) or not os.path.isdir(os.path.join(pers_dir(), owner)): return self._json(404, {'error': 'personaje no encontrado'})
                    d = os.path.join(pers_dir(), owner, 'complementos'); relb = f'assets/personajes/{owner}/complementos/'
                os.makedirs(d, exist_ok=True)
                stamp = int(time.time())
                for c in L:
                    c['id'] = _re.sub(r'[^a-z0-9-]+', '-', (c.get('id') or c.get('nombre') or 'complemento').lower()).strip('-') or 'complemento'
                    du = (body.get('files') or {}).get(c['id'])
                    if du and ',' in du:   # foto original nueva
                        im = Image.open(io.BytesIO(base64.b64decode(du.split(',', 1)[1]))).convert('RGB'); im.thumbnail((1400, 1400)); fn = c['id'] + '.jpg'; im.save(os.path.join(d, fn), quality=92); c['foto'] = relb + fn + f'?v={stamp}'
                    elif not c.get('foto'): c['foto'] = c.get('cover') or (c.get('img') if c.get('img') and c.get('img') != c.get('fichaProd') else None)
                    hist = [x for x in (c.get('fichas') or []) if x] or ([c['fichaProd']] if c.get('fichaProd') else [])
                    cps = (body.get('copy') or {}).get(c['id']) or []; cps = [cps] if isinstance(cps, str) else cps; mp = {}
                    for i, cp in enumerate(cps):   # fichas de producto generadas (assets/live) → a su carpeta y a su colección
                        src = busca(cp)
                        if src:
                            fn = f"{c['id']}_ficha_{stamp}_{i}.jpg"; Image.open(src).convert('RGB').save(os.path.join(d, fn), quality=92); mp[cp.split('?')[0]] = relb + fn; hist.append(relb + fn)
                    c['fichas'] = hist
                    sel = (body.get('sel') or {}).get(c['id']) or {}
                    res = lambda v: c.get('foto') if v in (None, '', '__foto__') else mp.get(v.split('?')[0], v)
                    if 'ref' in sel: c['img'] = res(sel['ref'])
                    elif du and ',' in du and (not c.get('img') or c.get('img') not in hist): c['img'] = c['foto']
                    if 'cover' in sel: c['portada'] = res(sel['cover'])
                    c['cover'] = c.get('foto'); c['fichaProd'] = c['img'] if c.get('img') in hist else None
                    tu = (body.get('files') or {}).get(c['id'] + '__thumb')   # miniatura recortada en el editor (solo para ver)
                    if tu and ',' in tu:
                        im = Image.open(io.BytesIO(base64.b64decode(tu.split(',', 1)[1]))).convert('RGB'); im.thumbnail((480, 480)); fn = c['id'] + '_mini.jpg'; im.save(os.path.join(d, fn), quality=90); c['thumb'] = relb + fn + f'?v={stamp}'
                if owner == 'aria':
                    head, C = _cat_load(); C['perfil']['complementos'] = L
                    _cat_save(head, C)
                else:
                    f = os.path.join(pers_dir(), owner, 'personaje.json'); P = json.load(open(f)); P['complementos'] = L; json.dump(P, open(f, 'w'), ensure_ascii=False, indent=1)
            plog(f'complementos de {owner}: {len(L)}'); return self._json(200, {'ok': True, 'list': L})
        if self.path == '/api/personaje_borrar':   # mueve la carpeta del personaje a la papelera de la app
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(n) or b'{}'); pid = body.get('id', '')
            import shutil
            if not _pid_ok(pid) or not os.path.isdir(os.path.join(pers_dir(), pid)): return self._json(404, {'error': 'personaje no encontrado'})
            d = os.path.join(pers_dir(), pid)
            trash = papelera(); shutil.move(d, os.path.join(trash, 'personaje_' + pid + '_' + str(int(time.time()))))
            plog(f'personaje {pid} → papelera'); return self._json(200, {'ok': True})
        if self.path == '/api/prenda_fav':   # marca/desmarca una prenda como favorita en el catálogo
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(n) or b'{}'); pid = body.get('id', '')
            with _cerrojo():
                head, C = _cat_load()
                it = next((v for v in C['vestidor'] if v['id'] == pid), None)
                if not it: return self._json(404, {'error': 'prenda no encontrada'})
                if body.get('fav'): it['fav'] = True
                else: it.pop('fav', None)
                _cat_save(head, C)
            plog(f"prenda {pid} favorita={bool(body.get('fav'))}"); return self._json(200, {'ok': True})
        if self.path == '/api/borrar_prenda':   # quita una prenda del catálogo y mueve sus archivos a la papelera (Notion no se toca)
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(n) or b'{}'); pid = body.get('id', '')
            import shutil
            with _cerrojo():
                head, C = _cat_load()
                it = next((v for v in C['vestidor'] if v['id'] == pid), None)
                if not it: return self._json(404, {'error': 'prenda no encontrada'})
                kids = [v for v in C['vestidor'] if v.get('parent') == pid]
                if kids:   # la primera variación pasa a ser la prenda original
                    nuevo = kids[0]; nuevo.pop('parent', None)
                    for k in kids[1:]: k['parent'] = nuevo['id']
                C['vestidor'] = [v for v in C['vestidor'] if v['id'] != pid]
                trash = papelera()
                for rel in (it.get('ficha'), it.get('card'), ((it.get('ficha') or '').split('?')[0] if SERVIDOR else (it.get('ficha') or '')) + '.json'):
                    full = (busca(rel, propio=True) or '') if SERVIDOR else os.path.join(ROOT, rel or '')   # en servidor solo se mueve lo que es de la cuenta: una prenda de la biblioteca común no se toca (queda oculta para ella)
                    if rel and os.path.isfile(full): shutil.move(full, os.path.join(trash, os.path.basename(full)))
                _cat_save(head, C)
            if SERVIDOR: plog(f'prenda borrada {pid}'); return self._json(200, {'ok': True, 'promoted': kids[0]['id'] if kids else None})   # Notion es solo del ordenador de Max
            try:   # archivar también su ficha en Notion (en segundo plano; reversible desde la papelera de Notion)
                import subprocess
                npid = ''
                try: npid = ((json.load(open(os.path.join(ROOT, 'assets', 'papelera', os.path.basename(it.get('ficha', '')) + '.json'))).get('notion') or {}).get('page_id')) or ''
                except Exception: pass
                def _arch():
                    r = subprocess.run([sys.executable, '/Users/maxromanenko/Desktop/XXX/.claude/scripts/aria_mirror/archivar_prenda_notion.py', str(it.get('num'))] + ([npid] if npid else []), capture_output=True, text=True, timeout=120)
                    plog(f'prenda {pid} Notion archivada · ' + (r.stdout.strip() or r.stderr[-200:]))
                threading.Thread(target=_arch, daemon=True).start()
            except Exception as e: plog('archivar Notion ✕ ' + str(e))
            plog(f'prenda borrada {pid} → papelera'); return self._json(200, {'ok': True, 'promoted': kids[0]['id'] if kids else None})
        if self.path == '/api/ocultar':   # marca/desmarca una creación como oculta en su ficha .json
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(n) or b'{}'); rel = body.get('file', '')
            full = _creacion(rel)
            if not full: return self._json(400, {'error': 'archivo no válido'})
            meta = {}
            if os.path.exists(full + '.json'):
                try: meta = json.load(open(full + '.json'))
                except Exception: meta = {}
            meta['hidden'] = bool(body.get('hidden')); meta.setdefault('file', rel)
            json.dump(meta, open(full + '.json', 'w'), ensure_ascii=False, indent=1); return self._json(200, {'ok': True, 'hidden': meta['hidden']})
        if self.path == '/api/cancelar':
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(n) or b'{}'); rid = body.get('id', '')
            j = _mio(rid)
            if SERVIDOR and not j: return self._json(404, {'error': 'petición desconocida'})   # solo los trabajos de la cuenta
            if j and j.get('prov') == 'ark':
                try: ark('DELETE', f'/api/v3/contents/generations/tasks/{rid}'); r = {'ok': True}
                except RuntimeError as e: return self._json(400, {'error': 'ByteDance no deja cancelar una tarea que ya está corriendo: ' + str(e)[:120]})
                j['canceled'] = True; return self._json(200, {'ok': True, 'raw': r})
            if j and j.get('prov') == 'ws': j['canceled'] = True; return self._json(200, {'ok': True, 'raw': 'WaveSpeed no cancela: se ignora el resultado'})
            try: r = api('PUT', f'/requests/{rid}/cancel')
            except RuntimeError:
                try: r = api('POST', f'/requests/{rid}/cancel')
                except RuntimeError as e: plog('cancelar ✕ ' + str(e)); return self._json(400, {'error': str(e)})
            j = _mio(rid);
            if j: j['canceled'] = True
            return self._json(200, {'ok': True, 'raw': r})
        if self.path != '/api/generar': return self._json(404, {'error': 'no'})
        n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(n) or b'{}')
        save_inputs(body)
        try:
            AM = all_models(); regalo = casa_on(); mkey = body.get('model') if body.get('model') in AM else (CASA_DEF if regalo else 'qwen'); M = AM[mkey]
            if M.get('prov') == 'ws':
                usd = round(M['usd']['high' if body.get('quality') == 'high' else 'std'] + M.get('per', 0) * max(0, min(len(body.get('images', [])), M['refs']) - 1), 4)   # precio de tarifa con sus referencias
                if regalo:   # 🎁 paga el saldo regalo: nunca NSFW (la clave es la de la casa) y solo si le llega
                    if (body.get('meta') or {}).get('nsfw') or body.get('nsfw') or _es_nsfw(body.get('prompt')): raise RuntimeError('El saldo regalo no vale para contenido NSFW. Para eso, conecta tu propia clave en «API en vivo».')
                    casa_puede(usd)
                urls = [resolve_ws(i) for i in body.get('images', [])][:M['refs']]
                if not urls: raise RuntimeError('hacen falta imágenes de referencia')
                payload = M['body'](body.get('prompt', ''), urls, aspect_ok(body.get('aspect')), 'high' if body.get('quality') == 'high' else 'std')
                bal0 = None
                if regalo:
                    if 'seedream' in M['ep']: payload['enable_safety_checker'] = True
                    with _cerrojo('gen'):   # de una en una: dos peticiones a la vez no pueden gastar el mismo saldo
                        casa_puede(usd); _ctx.casa_ok = True
                        try: r = ws('POST', '/api/v3/' + M['ep'], payload)
                        finally: _ctx.casa_ok = False
                        rid = (r.get('data') or {}).get('id')
                        if not rid: raise RuntimeError('WaveSpeed no devolvió id: ' + json.dumps(r)[:200])
                        jobs[rid] = {'t0': time.time(), 'item': body.get('item', 'img'), 'model': mkey, 'prov': 'ws', 'usd': usd, 'bal0': None, 'casa': True, 'credits': None, 'meta': body.get('meta') or {}}
                    return self._json(200, {'request_id': rid, 'usd': usd, 'credits': None, 'model': M['ep'], 'model_key': mkey, 'image_urls': urls, 'casa': casa_info(), 'payload': {k: v for k, v in payload.items() if k != 'images'}})
                try: bal0 = float((ws('GET', '/api/v3/balance').get('data') or {}).get('balance'))
                except Exception: bal0 = None
                r = ws('POST', '/api/v3/' + M['ep'], payload); rid = (r.get('data') or {}).get('id')
                if not rid: raise RuntimeError('WaveSpeed no devolvió id: ' + json.dumps(r)[:200])
                jobs[rid] = {'t0': time.time(), 'item': body.get('item', 'img'), 'model': mkey, 'prov': 'ws', 'usd': usd, 'bal0': bal0, 'credits': None, 'meta': body.get('meta') or {}}
                return self._json(200, {'request_id': rid, 'usd': usd, 'credits': None, 'model': M['ep'], 'model_key': mkey, 'image_urls': urls, 'payload': {k: v for k, v in payload.items() if k != 'images'}})
            if not _hf_listo(): raise RuntimeError('Higgsfield no está conectado: conéctalo en «API en vivo»' if SERVIDOR else 'falta la clave ID:SECRET en ~/.claude/higgsfield.env')
            urls = [resolve_image(i) for i in body.get('images', [])][:M['refs']]
            if not urls: raise RuntimeError('hacen falta imágenes de referencia')
            payload = M['body'](body.get('prompt', ''), urls, aspect_ok(body.get('aspect')), 'high' if body.get('quality') == 'high' else 'std')
            est = {}
            try: est = api('POST', f"/estimate/{M['ep']}", payload)
            except RuntimeError: pass
            res = api('POST', '/' + M['ep'], payload)
            rid = res.get('request_id'); jobs[rid] = {'t0': time.time(), 'item': body.get('item', 'img'), 'model': mkey, 'usd': est.get('usd'), 'credits': est.get('credits'), 'meta': body.get('meta') or {}}
            return self._json(200, {'request_id': rid, 'usd': est.get('usd'), 'credits': est.get('credits'), 'model': M['ep'], 'model_key': mkey, 'status_url': res.get('status_url'), 'image_urls': urls, 'payload': {k: v for k, v in payload.items() if k not in ('image_urls', 'image_url')}})
        except Exception as e:
            plog('generar ✕ ' + str(e)); return self._json(400, {'error': str(e)})

    def do_video(self):   # {mode:i2v|r2v, prompt, image:{path|data}, refs:[{path}], duration, resolution, aspect, audio, item, usd}
        n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(n) or b'{}')
        try:
            mode = body.get('mode') if body.get('mode') in VIDEO_MODELS else 'i2v'; M = VIDEO_MODELS[mode]
            if body.get('provider') == 'ws':   # WaveSpeed: Seedance 2.0 (0,12 $/s a 480p; 720p ×2, 1080p ×5, 4K ×10)
                res = body.get('resolution') if body.get('resolution') in ('480p', '720p', '1080p', '4k') else '720p'; dur = max(4, min(15, int(body.get('duration') or 5)))
                prompt = (body.get('prompt') or '').strip() or 'Natural subtle motion, she breathes and blinks.'
                if mode == 'i2v': ep = 'bytedance/seedance-2.0/image-to-video'; payload = {'prompt': prompt, 'image': resolve_ws(body['image']), 'duration': dur, 'resolution': res, 'generate_audio': bool(body.get('audio'))}
                else:
                    R = body.get('refs') or []; ep = 'bytedance/seedance-2.0/text-to-video'
                    payload = {'prompt': prompt, 'duration': dur, 'resolution': res, 'aspect_ratio': body.get('aspect') if body.get('aspect') in V_ASPECTS else '3:4', 'generate_audio': bool(body.get('audio'))}
                    if by_kind(R, 'image'): payload['reference_images'] = [resolve_ws(r) for r in by_kind(R, 'image')][:9]
                    if by_kind(R, 'video'): payload['reference_videos'] = [resolve_ws(r) for r in by_kind(R, 'video')][:3]
                    if by_kind(R, 'audio'): payload['reference_audios'] = [resolve_ws(r) for r in by_kind(R, 'audio')][:3]
                try: bal0 = float((ws('GET', '/api/v3/balance').get('data') or {}).get('balance'))
                except Exception: bal0 = None
                r = ws('POST', '/api/v3/' + ep, payload); rid = (r.get('data') or {}).get('id')
                if not rid: raise RuntimeError('WaveSpeed no devolvió id: ' + json.dumps(r)[:200])
                jobs[rid] = {'t0': time.time(), 'item': body.get('item', 'video'), 'kind': 'video', 'model': mode, 'prov': 'ws', 'usd': body.get('usd'), 'bal0': bal0, 'credits': None, 'meta': body.get('meta') or {}}
                return self._json(200, {'request_id': rid, 'model': ep, 'usd': body.get('usd'), 'payload': {k: v for k, v in payload.items() if k not in ('image', 'reference_images')}})
            if body.get('provider') == 'ark':   # ByteDance directo: mismo formato de trabajo, otra API
                ver = body.get('vmodel') if body.get('vmodel') in ARK_MODELS else '2.0'; res = body.get('resolution') if body.get('resolution') in ARK_USD[ver] else '720p'
                dur = max(4, min(30 if ver == '2.5' else 15, int(body.get('duration') or 5)))
                prompt = (body.get('prompt') or '').strip() or 'Natural subtle motion, she breathes and blinks.'
                if mode == 'i2v': content = [{'type': 'text', 'text': prompt}, {'type': 'image_url', 'image_url': {'url': data_uri(body['image'])}, 'role': 'first_frame'}]
                else:
                    R = body.get('refs') or []; content = [{'type': 'text', 'text': prompt}]
                    content += [{'type': 'image_url', 'image_url': {'url': data_uri(r)}, 'role': 'reference_image'} for r in by_kind(R, 'image')[:9]]
                    content += [{'type': 'video_url', 'video_url': {'url': data_uri(r)}, 'role': 'reference_video'} for r in by_kind(R, 'video')[:3]]
                    content += [{'type': 'audio_url', 'audio_url': {'url': data_uri(r)}, 'role': 'reference_audio'} for r in by_kind(R, 'audio')[:3]]
                payload = {'model': ARK_MODELS[ver], 'content': content, 'duration': dur, 'resolution': res, 'generate_audio': bool(body.get('audio')), 'watermark': False}
                if mode == 'r2v': payload['ratio'] = body.get('aspect') if body.get('aspect') in V_ASPECTS else '3:4'
                else: payload['ratio'] = 'adaptive'
                r = ark('POST', '/api/v3/contents/generations/tasks', payload); rid = r.get('id')
                jobs[rid] = {'t0': time.time(), 'item': body.get('item', 'video'), 'kind': 'video', 'model': mode, 'prov': 'ark', 'usd': body.get('usd'), 'credits': None, 'meta': body.get('meta') or {}}
                return self._json(200, {'request_id': rid, 'model': ARK_MODELS[ver], 'usd': body.get('usd'), 'payload': {k: v for k, v in payload.items() if k != 'content'}})
            if not _hf_listo(): raise RuntimeError('Higgsfield no está conectado: conéctalo en «API en vivo»' if SERVIDOR else 'falta la clave ID:SECRET en ~/.claude/higgsfield.env')
            R = body.get('refs') or []
            if mode == 'r2v' and (by_kind(R, 'video') or by_kind(R, 'audio')): raise RuntimeError('Higgsfield solo admite imágenes como referencia: quita los vídeos/audios del pool o cambia a WaveSpeed')
            img = resolve_image(body['image']); refs = [resolve_image(r) for r in by_kind(R, 'image') if (r.get('path'), r.get('data')) != (body['image'].get('path'), body['image'].get('data'))][:8]
            dur = max(4, min(15, int(body.get('duration') or 5))); res = body.get('resolution') if body.get('resolution') in ('480p', '720p', '1080p', '4k') else '720p'
            prompt = (body.get('prompt') or '').strip() or 'Natural subtle motion, she breathes and blinks.'
            if mode == 'i2v': payload = {'prompt': prompt, 'image_url': img, 'duration': dur, 'resolution': res, 'generate_audio': bool(body.get('audio'))}
            else: payload = {'prompt': prompt, 'image_urls': ([img] + refs)[:9], 'duration': dur, 'resolution': res, 'aspect_ratio': body.get('aspect') if body.get('aspect') in V_ASPECTS else '3:4', 'generate_audio': bool(body.get('audio'))}
            res_ = api('POST', '/' + M['ep'], payload)
            rid = res_.get('request_id'); jobs[rid] = {'t0': time.time(), 'item': body.get('item', 'video'), 'kind': 'video', 'model': mode, 'usd': body.get('usd'), 'credits': None, 'meta': body.get('meta') or {}}
            return self._json(200, {'request_id': rid, 'model': M['ep'], 'usd': body.get('usd'), 'status_url': res_.get('status_url'), 'payload': {k: v for k, v in payload.items() if k not in ('image_url', 'image_urls')}})
        except Exception as e:
            plog('video ✕ ' + str(e)); return self._json(400, {'error': str(e)})

_vig_en = set(); _vig_sem = threading.BoundedSemaphore(8)
def _vigila_uno(rid, j):   # modo servidor: sin llamarse por HTTP — el estado se pide directamente, como la cuenta dueña del trabajo (hasta 8 a la vez)
    try:
        with como(j.get('owner')): _estado(rid)
    except Exception: pass
    finally: _vig_en.discard(rid); _vig_sem.release()
_papelera_t = [0.0]
def _vacia_papeleras():   # lo borrado se puede recuperar 30 días; después deja de ocupar
    if time.time() - _papelera_t[0] < 3600: return
    _papelera_t[0] = time.time(); viejo = time.time() - 30 * 86400
    try: cuentas = os.listdir(os.path.join(DATOS, 'usuarios'))
    except OSError: return
    for u in cuentas:
        for d, _, fs in os.walk(os.path.join(DATOS, 'usuarios', u, 'assets', 'papelera'), topdown=False):
            for f in fs:
                fp = os.path.join(d, f)
                try:
                    if os.path.getmtime(fp) < viejo: os.remove(fp)
                except OSError: pass
            try: os.rmdir(d)   # solo si quedó vacía
            except OSError: pass
def _vigilante():   # cada 8 s: los trabajos de personajes sin recoger se descargan solos (llamando a /api/estado del propio puente)
    while True:
        time.sleep(8)
        if SERVIDOR:
            try: _vacia_papeleras()
            except Exception: pass
        for rid, j in list(jobs.items()):
            try:
                pers = str((j.get('meta') or {}).get('personaje') or '_')
                edad = time.time() - float(j.get('t0') or 0)   # desde la v122 recoge TODO lo que termina (también creaciones y vídeos), aunque la página esté cerrada
                if SERVIDOR and edad > 24 * 3600: dict.pop(jobs, rid, None); continue   # en servidor la lista de trabajos no crece sin fin
                if j.get('file') or j.get('failed') or edad > 3 * 3600 or edad < 25: continue
                if SERVIDOR:
                    if rid in _vig_en or not _vig_sem.acquire(blocking=False): continue
                    _vig_en.add(rid); threading.Thread(target=_vigila_uno, args=(rid, j), daemon=True).start()
                else: urllib.request.urlopen(f'http://127.0.0.1:{PORT}/api/estado?id={rid}', timeout=120).read()
            except Exception: pass
if __name__ == '__main__':
    if SERVIDOR:   # nada de esto toca la carpeta del código ni su assets/
        if not DATOS: sys.exit('modo servidor: falta ARIA_DATOS (la carpeta de datos de las cuentas)')
        os.makedirs(os.path.join(DATOS, 'usuarios'), mode=0o700, exist_ok=True)
        if not SECRETO: print('AVISO: falta ARIA_SECRETO (32+ caracteres): no se podrán guardar claves de API', flush=True)
        if os.environ.get('ARIA_DEV') == '1' and not DEV: print('ARIA_DEV se ignora: el servidor no escucha en 127.0.0.1', flush=True)
    _jobs_restore(); threading.Thread(target=_vigilante, daemon=True).start()
    if SERVIDOR: print(f'ARIA STUDIO v{VERSION} · modo servidor en http://{HOST}:{PORT} · datos en {DATOS} · orígenes: {", ".join(ORIGENES)}' + (' · ATAJO DE PRUEBAS X-Dev-Uid ACTIVO' if DEV else '') + (f' · 🎁 saldo regalo ACTIVO (tope {CASA_TOPE:g} $/mes)' if CASA_KEY else ' · saldo regalo apagado (falta ARIA_CASA_WS)'), flush=True)
    else: print(f'ARIA MIRROR · puente en http://localhost:{PORT} · modelo {MODEL} · clave {"OK" if _hf_listo() else "FALTA (ID:SECRET)"}')
    ThreadingHTTPServer((HOST, PORT), H).serve_forever()
