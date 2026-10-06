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
import os, shutil, re, sys, hmac, json, math, time, base64, hashlib, tarfile, mimetypes, threading, urllib.request, urllib.error, urllib.parse
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
try:   # v260: una imagen pequeña en bytes pero enorme en píxeles se comía la memoria y tumbaba la web para todos
    import warnings
    from PIL import Image as _PILI
    _PILI.MAX_IMAGE_PIXELS = 40_000_000; warnings.simplefilter('error', _PILI.DecompressionBombWarning)
except Exception: pass

RAIZ = os.path.dirname(os.path.abspath(__file__)); ROOT = RAIZ   # la carpeta del código y de la biblioteca común (ROOT = lo mismo; solo para lo que es de todos)
LIGA_DIR = os.path.join(ROOT, 'assets', 'liga')   # 🥊 Duelos de AI League (v123) · solo en local
LIGA_PY = '/Users/maxromanenko/Desktop/XXX/.claude/scripts/ai_league/liga.py'   # montaje del carrusel (v124)
LIGA_PY_SRV = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'liga', 'liga.py')   # en el servidor, la copia que va con él (con montar.py y sus fuentes)
# ---- «modo servidor» (ARIA_SERVIDOR=1): muchas cuentas a la vez; cada una con su casa, sus claves, sus trabajos y su capa sobre el catálogo común. Sin la variable NO cambia nada (un solo usuario, en local)
SERVIDOR = os.environ.get('ARIA_SERVIDOR') == '1'
HOST = (os.environ.get('ARIA_HOST') or '127.0.0.1') if SERVIDOR else '127.0.0.1'
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else int((SERVIDOR and os.environ.get('PORT')) or 8767)
DATOS = os.path.abspath(os.environ['ARIA_DATOS']) if SERVIDOR and os.environ.get('ARIA_DATOS') else ''   # usuarios/<uid>/ · biblioteca/ (copia de lo común) · jobs.jsonl · puente.log · feedback.jsonl
DEV = SERVIDOR and os.environ.get('ARIA_DEV') == '1' and HOST == '127.0.0.1'   # atajo de pruebas (cabecera X-Dev-Uid): solo existe si el servidor escucha en 127.0.0.1
SB_URL = (os.environ.get('SB_URL') or 'https://uhscbgidrloskdjbevkn.supabase.co').rstrip('/')
SB_KEY = os.environ.get('SB_KEY') or 'sb_publishable_GSO5Vqhr7Dg93egtKk_I2w_E_uScoNG'   # pública por diseño (es la del navegador); lo que protege los datos son las reglas de Supabase
BIBLIO_URL = (os.environ.get('ARIA_BIBLIOTECA') or 'https://uhscbgidrloskdjbevkn.supabase.co/storage/v1/object/public/assets/').rstrip('/') + '/'   # almacén público de la biblioteca común
BIBLIO_OK = tuple('assets/' + x for x in ('biblio/', 'vestidor/', 'hair/', 'expr/', 'movie/', 'cartoon/', 'photo/', 'crear/', 'conv/', 'videoteca/', 'perfil/', 'refs/', 'video/', 'personajes/_opciones/', 'muestras/'))   # lo que puede venir de la biblioteca común (+ personajes/_lienzo.jpg y lo de assets/live que usa el perfil común)
ORIGENES = tuple(o.strip().lower().rstrip('/') for o in (os.environ.get('ARIA_ORIGENES') or 'https://aria-studio-eta.vercel.app,https://studio.ariacruz.com,https://ariacruz.com,http://localhost:3000').split(',') if o.strip())
FETCH_HOSTS = tuple(h.strip().lower() for h in (os.environ.get('ARIA_FETCH_HOSTS') or ','.join([urllib.parse.urlsplit(SB_URL).hostname or '', '.wavespeed.ai', '.higgsfield.ai', '.cloudfront.net', '.bytepluses.com', '.volces.com'])).split(',') if h.strip())   # /api/fetch en servidor: host exacto o «.sufijo»; «*» = cualquier sitio público
MAX_CUERPO = 40 * 1024 * 1024    # tope de una petición en modo servidor
MAX_BIBLIO = 200 * 1024 * 1024   # tope de un fichero de la biblioteca común al copiarlo
KINDS = ('vestidor', 'hair', 'expr')   # las bibliotecas a las que una cuenta puede añadir lo suyo
_UUID = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')
VERSION = 326
_ctx = threading.local()   # la cuenta del hilo: la pone cada petición (y, a mano, cada hilo de fondo)
def uid(): return getattr(_ctx, 'uid', None)   # en local siempre None
DUENOS = tuple(e.strip().lower() for e in (os.environ.get('ARIA_DUENOS') or 'mix1994max@gmail.com').split(',') if e.strip())   # cuentas que pueden cambiar a Aria Cruz (en la web, la de Max)
ARIA_UID = (os.environ.get('ARIA_UID') or '1e9592c3-a0be-420a-ae93-77b0434bf471').strip().lower()   # la cuenta principal de Aria (soyariacruz@gmail.com): ahí vive la Aria de equipo
ARIA_PUBLICAN = DUENOS + tuple(e.strip().lower() for e in (os.environ.get('ARIA_PUBLICAN') or 'soyariacruz@gmail.com').split(',') if e.strip())   # quién pulsa «Publicar para todos»
NSFW_OK = tuple(e.strip().lower() for e in (os.environ.get('ARIA_NSFW') or 'mix1994max@gmail.com,soyariacruz@gmail.com').split(',') if e.strip())   # las ÚNICAS cuentas con NSFW en la web (Max, 5 oct 2026)
def nsfw_ok(): return (not SERVIDOR) or ((getattr(_ctx, 'email', '') or '').lower() in NSFW_OK and not getattr(_ctx, 'ver_miembro', False))   # NSFW CON ARIA CRUZ
def _con_aria(body):   # ¿sale Aria Cruz? (por lo que dice la página o porque va su ficha: assets/perfil/…)
    m = body.get('meta') or {}; chars = m.get('chars') if isinstance(m.get('chars'), list) else [m.get('char')]
    imgs = [i for i in (body.get('images') or []) + (body.get('refs') or []) + [body.get('image'), body.get('end')] if isinstance(i, dict)]
    if 'aria' in chars or 'Aria Cruz' in [m.get('charName')]: return True
    for i in imgs:   # v260: la ficha de Aria, sus fotos de la Fototeca / Filmoteca / perfil, o una creación tuya hecha con Aria
        p = str(i.get('path') or '').split('?')[0]
        if p.startswith(('assets/perfil/', 'assets/biblio/', 'assets/videoteca/', 'assets/base/', 'assets/aria/')): return True
        if p.startswith(('assets/live/', 'assets/video/')):
            try:
                mm = json.load(open(os.path.join(casa(), *p.split('/')) + '.json', encoding='utf-8'))
                if 'aria' in (mm.get('chars') or [mm.get('char')]) or mm.get('charName') == 'Aria Cruz': return True
            except Exception: pass
    return False
def aria_fija():   # para los miembros Aria es un personaje fijo: se ve y se usa, no se edita. La editan Max, el equipo (cuentas internas) y la propia cuenta de Aria
    return SERVIDOR and (getattr(_ctx, 'ver_miembro', False) or not ((getattr(_ctx, 'email', '') or '').lower() in DUENOS or getattr(_ctx, 'interno', False) or getattr(_ctx, 'uid', None) == ARIA_UID))
def _aria_casa():   # la carpeta de la Aria de equipo, para quien puede editarla (si no, None)
    if not SERVIDOR or not DATOS or aria_fija() or not re.fullmatch(r'[0-9a-f-]{36}', ARIA_UID): return None
    d = os.path.join(DATOS, 'usuarios', ARIA_UID); os.makedirs(d, mode=0o700, exist_ok=True); return d
def _pabs(rel):   # fichero de la ficha de Aria (assets/perfil/…): para el equipo, en la carpeta de la Aria de equipo
    return os.path.join(_aria_casa() or casa(), *rel.split('/'))
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
def audio_dir(): return _dir('assets', 'audio')   # v291: 🎙️ Crear audio
def pers_dir(): return _dir('assets', 'personajes')
def refs_dir(): return _dir('assets', 'refs')
def mini_dir(): return os.path.join(live_dir(), '.mini')
def papelera(): return _dir('assets', 'papelera')
def perfil_dir(*sub):   # la ficha de Aria: para el equipo, en la Aria de equipo (todos ven lo mismo)
    ac = _aria_casa()
    if not ac: return _dir('assets', 'perfil', *sub)
    d = os.path.join(ac, 'assets', 'perfil', *sub); os.makedirs(d, exist_ok=True); return d
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
    if rel.startswith('assets/publica/'): return None if propio else _publica(rel)   # v237: publicado en la comunidad
    if rel.startswith('assets/compartida/'): return None if propio else _compartida(rel)   # v220: una creación de otra cuenta, solo si está en una carpeta que me ha compartido
    if rel.startswith('assets/prestamo/'): return _prestado(rel) if getattr(_ctx, 'prestamo_ok', False) and not propio else None   # el personaje de otro creador: solo al generar, y solo con su permiso
    base = casa(); full = os.path.join(base, *rel.split('/'))
    if _dentro(base, full) and os.path.isfile(full): return full
    if not propio:
        fa = _aria_fich(rel)
        if fa: return fa
    return _biblio(rel) if SERVIDOR and not propio else None   # en local la biblioteca común ES la carpeta de siempre
def _aria_fich(rel):   # para el equipo: un fichero de la Aria de equipo (su ficha en assets/perfil, o una imagen de assets/live que su perfil nombra)
    ac = _aria_casa()
    if not ac or ac == casa() or not (rel.startswith('assets/perfil/') or (rel.startswith('assets/live/') and rel in _aria_refs(_aria_perfil()))): return None
    full = os.path.join(ac, *rel.split('/'))
    return full if _dentro(ac, full) and os.path.isfile(full) else None
def _aria_refs(P):   # las rutas assets/… que nombra un perfil
    out = set()
    def anda(x):
        if isinstance(x, str): out.update(p.split('?')[0] for p in x.split('|') if p.startswith('assets/'))
        elif isinstance(x, list): [anda(y) for y in x]
        elif isinstance(x, dict): [anda(y) for y in x.values()]
    anda(P); return out
_aria_l = threading.Lock()
def _aria_capa_fp(): return os.path.join(DATOS, 'usuarios', ARIA_UID, 'capa.json')
def _aria_perfil():   # el perfil de la Aria de equipo (None si nadie la ha cambiado aún: entonces vale la publicada)
    try: P = json.load(open(_aria_capa_fp(), encoding='utf-8')).get('perfil')
    except Exception: return None
    return P if isinstance(P, dict) else None
def _aria_perfil_guarda(P):   # alguien del equipo ha cambiado a Aria: a la capa de la cuenta de Aria (y las imágenes de su live que nombre, copiadas allí)
    ac = os.path.join(DATOS, 'usuarios', ARIA_UID)
    for rel in _aria_refs(P):
        if not rel.startswith('assets/live/'): continue
        dst = os.path.join(ac, *rel.split('/')); src = os.path.join(casa(), *rel.split('/'))
        if not os.path.isfile(dst) and _dentro(casa(), src) and os.path.isfile(src): os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copyfile(src, dst)
    with _aria_l:
        fp = _aria_capa_fp()
        try: capa = json.load(open(fp, encoding='utf-8'))
        except FileNotFoundError: capa = {'v': 1}
        capa['perfil'] = P; os.makedirs(os.path.dirname(fp), mode=0o700, exist_ok=True); tmp = f'{fp}.tmp{threading.get_ident()}'
        with os.fdopen(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), 'w', encoding='utf-8') as fh: json.dump(capa, fh, ensure_ascii=False); fh.flush(); os.fsync(fh.fileno())
        os.replace(tmp, fp)
    plog('Aria de equipo guardada por ' + (getattr(_ctx, 'email', '') or '?'))
def _sb_sube(bucket, ruta, data, ctype, cache):   # sube un fichero al almacén de Supabase (con la clave secreta del servidor; nunca sale de aquí)
    sec = os.environ.get('SUPABASE_SECRET') or ''
    rq = urllib.request.Request(SB_URL + f'/storage/v1/object/{bucket}/' + urllib.parse.quote(ruta), data=data, method='POST',
                                headers={'Authorization': 'Bearer ' + sec, 'apikey': sec, 'Content-Type': ctype, 'x-upsert': 'true', 'cache-control': 'max-age=' + cache, 'User-Agent': UA})
    with urllib.request.urlopen(rq, timeout=120) as r: return r.status
_ARIA_PUB = {}   # v323: la publicación en marcha (va en segundo plano: {'on', 'n', 'total', 'error'})
def _aria_publica(quien=''):   # la Aria de equipo → catálogo común. Ficheros cambiados con nombre nuevo (su huella): nada se pisa y la caché no estorba
    P = _aria_perfil()
    if not isinstance(P, dict): raise RuntimeError('No hay cambios de Aria que publicar')
    ensayo = bool(os.environ.get('ARIA_CATALOGO')) or not os.environ.get('SUPABASE_SECRET')   # servidor de pruebas: no se toca ni el catálogo de Max ni el almacén
    ac = os.path.join(DATOS, 'usuarios', ARIA_UID); mapa = {}; dest = os.path.join(DATOS, 'aria_ensayo') if ensayo else ''
    L = sorted(_aria_refs(P)); _ARIA_PUB.update(n=0, total=len(L))
    for rel in L:
        _ARIA_PUB['n'] = _ARIA_PUB.get('n', 0) + 1
        full = os.path.join(ac, *rel.split('/'))
        if not (_dentro(ac, full) and os.path.isfile(full)): continue   # lo que no está en la Aria de equipo ya está publicado
        data = open(full, 'rb').read(); ext = os.path.splitext(rel)[1].lower() or '.jpg'; nuevo = f'assets/perfil/web/{hashlib.sha1(data).hexdigest()[:16]}{ext}'
        if not ensayo and os.path.isfile(os.path.join(DATOS, 'biblioteca', *nuevo.split('/'))): mapa[rel] = nuevo; continue   # v323: ya subido en otra publicación (mismo contenido = mismo nombre): no se vuelve a subir
        if ensayo: fp = os.path.join(dest, *nuevo.split('/')); os.makedirs(os.path.dirname(fp), exist_ok=True); open(fp, 'wb').write(data)
        else: _sb_sube('assets', nuevo[len('assets/'):], data, mimetypes.guess_type(full)[0] or 'application/octet-stream', '31536000')
        bf = os.path.join(DATOS, 'biblioteca', *nuevo.split('/')); os.makedirs(os.path.dirname(bf), exist_ok=True); shutil.copyfile(full, bf)   # y ya en la copia local de la biblioteca del servidor
        mapa[rel] = nuevo
    def cambia(x):
        if isinstance(x, str): return '|'.join(mapa.get(p.split('?')[0], p) for p in x.split('|'))
        if isinstance(x, list): return [cambia(y) for y in x]
        if isinstance(x, dict): return {k: cambia(v) for k, v in x.items()}
        return x
    Pub = cambia(P); quien = quien or getattr(_ctx, 'email', '') or ''
    if ensayo: os.makedirs(dest, exist_ok=True); json.dump({'perfil': Pub}, open(os.path.join(dest, 'catalogo.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    else:
        sec = os.environ.get('SUPABASE_SECRET') or ''
        rq = urllib.request.Request(SB_URL + '/storage/v1/object/catalogo/catalog.js', headers={'Authorization': 'Bearer ' + sec, 'apikey': sec, 'User-Agent': UA})
        with urllib.request.urlopen(rq, timeout=60) as r: raw = r.read().decode('utf-8')
        cab, fin = raw[:raw.index('{')], raw[raw.rindex('}') + 1:]; C = json.loads(raw[raw.index('{'):raw.rindex('}') + 1])
        os.makedirs(os.path.join(DATOS, 'aria_copias'), exist_ok=True); open(os.path.join(DATOS, 'aria_copias', time.strftime('%Y%m%d-%H%M%S') + '_catalog.js'), 'w', encoding='utf-8').write(raw)   # el catálogo de antes, por si hay que volver atrás
        C['perfil'] = Pub; C['ariaWeb'] = {'t': time.strftime('%Y-%m-%d %H:%M'), 'por': quien}
        _sb_sube('catalogo', 'catalog.js', (cab + json.dumps(C, ensure_ascii=False) + fin).encode('utf-8'), 'application/javascript', '0')
        with _comun_l: _comun_c.clear()
    json.dump({'t': time.strftime('%Y-%m-%d %H:%M'), 'por': quien, 'borrador': P, 'ensayo': ensayo}, open(os.path.join(DATOS, 'aria_publicado.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    plog(f'Aria publicada para todos por {quien} · {len(mapa)} ficheros nuevos' + (' (ENSAYO)' if ensayo else ''))
    return {'ok': True, 'ficheros': len(mapa), 'ensayo': ensayo}
# ---- 🥊 WORKFLOWS EN LA WEB (v209): los Duelos de AI League para el equipo, sin depender del Mac de Max ----
LIGA_WEB = os.path.join(DATOS, 'liga') if SERVIDOR and DATOS else ''
ARIA_EMAIL = (os.environ.get('ARIA_EMAIL') or 'soyariacruz@gmail.com').strip().lower()
LIGA_LLM = os.environ.get('ARIA_LIGA_LLM') or 'claude-opus-5-5'   # quién escribe mundos, historias y prompts (clave de Claude de la cuenta de Aria)
LIGA_WS = {'nano_banana_pro': 'nbp', 'gpt_image_2_5': 'gptimg', 'seedream_v5_pro': 'seedream', 'seedream_5_0_flash': 'seedflash'}   # modelos de la página → WaveSpeed
LIGA_TESTS = [{'n': 1, 'nombre': 'De lejos', 'que': 'Cuerpo entero y pequeña en el encuadre: ¿se la reconoce?'}, {'n': 2, 'nombre': 'Contraluz', 'que': 'Luz fuerte detrás y la cara en penumbra, creíble'},
    {'n': 3, 'nombre': 'Comiendo de verdad', 'que': 'Boca, comida y manos a la vez sin deformarse'}, {'n': 4, 'nombre': 'Las gafas en apuros', 'que': 'Empañadas, con gotas o con reflejos, y siguen siendo las suyas'},
    {'n': 5, 'nombre': 'Texto en español', 'que': 'Una frase con tildes y ñ, legible y sin faltas'}, {'n': 6, 'nombre': 'De perfil y de espaldas', 'que': '¿Es la misma cara y la misma coleta fuera del plano frontal?'},
    {'n': 7, 'nombre': 'Casi a oscuras', 'que': 'Una sola fuente de luz pequeña y la piel aguanta'}, {'n': 8, 'nombre': 'UGC de verdad', 'que': 'Foto de móvil cualquiera, nada de estudio (el móvil nunca se ve)'},
    {'n': 9, 'nombre': 'Con más gente', 'que': 'Contacto con otras personas sin que se le contagie la cara'}, {'n': 10, 'nombre': 'Manos haciendo algo', 'que': 'Cinco dedos, bien colocados y agarrando de verdad'},
    {'n': 11, 'nombre': 'En movimiento', 'que': 'Pose dinámica con un cuerpo posible'}, {'n': 12, 'nombre': 'Ángulo extremo', 'que': 'Cenital o contrapicado sin romper proporciones'},
    {'n': 13, 'nombre': 'Emoción extrema', 'que': 'Llanto, carcajada o susto que sigue siendo Aria'}, {'n': 14, 'nombre': 'Agua y pelo mojado', 'que': 'Pelo empapado y piel mojada sin perder su coleta ni sus rasgos'},
    {'n': 15, 'nombre': 'Producto con etiqueta', 'que': 'Un objeto con marca o etiqueta legible en la mano'}, {'n': 16, 'nombre': 'Ropa con estampado', 'que': 'Un estampado complejo que se mantiene coherente'},
    {'n': 17, 'nombre': 'Reflejo en un espejo', 'que': 'El reflejo coincide con ella (sin móvil a la vista)'}, {'n': 18, 'nombre': 'Detalle de cerca', 'que': 'Primer plano de la cara: piel, ojos y gafas con detalle real'}]
LIGA_REGLAS = """Eres el guionista y director de fotografía de los «Duelos de AI League» de Aria Cruz, una influencer IA española de 24 años: coleta alta, gafas redondas metálicas finas, aros plateados, ojos verdes, cara reconocible. Cada duelo enfrenta dos generadores de imagen con LAS MISMAS situaciones difíciles dentro de un MUNDO con historia, y se publica como carrusel en Instagram y Skool.
Reglas de los prompts de imagen (en INGLÉS, largos, detallados y CREATIVOS; nada de imágenes genéricas de IA):
- Empiezan anclando a Aria a la referencia: «the woman in image 1» (su ficha 360) + MANDATORY: thin round metal glasses, silver hoop earrings, high ponytail, green eyes.
- Una idea concreta, un momento, un detalle que cuenta algo: quién hace la foto, dónde, qué pasa, luz, lente, textura (foto real, nada de estudio salvo que el test lo pida).
- Encuadre vertical 9:16 pensado para recortarse a media diapositiva: Aria Y lo que se pone a prueba en la franja central.
- Todo en positivo (sin «no…»), el texto que deba salir escrito va entre comillas. El móvil nunca se ve en la foto. Nada de desnudos ni contenido sexual.
- Cada prompt pone a prueba UN test de la batería; puede haber varios prompts del mismo test."""
_LIGA_CAT = {'t': 0, 'L': []}; _LIGA_CAT_L = threading.Lock()
LIGA_ELEGIDOS = [   # los generadores que el equipo usa en los duelos (en este orden, con su nombre limpio y su marca). Para añadir uno: su id del catálogo de WaveSpeed
    ('google/nano-banana-pro/edit', 'Nano Banana Pro', 'Google'), ('google/nano-banana-2/edit', 'Nano Banana 2', 'Google'),
    ('openai/gpt-image-2.5-sunburst/edit', 'GPT Image 2.5 Sunburst', 'OpenAI'), ('openai/gpt-image-2.5-flare/edit', 'GPT Image 2.5 Flare', 'OpenAI'), ('openai/gpt-image-2/edit', 'GPT Image 2', 'OpenAI'),
    ('bytedance/seedream-v5.0-pro/edit', 'Seedream 5.0 Pro', 'ByteDance'), ('bytedance/seedream-v5.0-lite/edit', 'Seedream 5.0 Lite', 'ByteDance'), ('bytedance/seedream-v5.0-flash/edit', 'Seedream 5.0 Flash', 'ByteDance'), ('bytedance/seedream-v4.5/edit', 'Seedream 4.5', 'ByteDance'),
    ('black-forest-labs/flux-3/image-edit', 'FLUX 3', 'Black Forest Labs'), ('wavespeed-ai/flux-2-max/edit', 'FLUX 2 Max', 'Black Forest Labs'), ('wavespeed-ai/flux-2-pro/edit', 'FLUX 2 Pro', 'Black Forest Labs'), ('wavespeed-ai/flux-2-flex/edit', 'FLUX 2 Flex', 'Black Forest Labs'),
    ('alibaba/qwen-image-3.0-pro/edit', 'Qwen Image 3.0 Pro', 'Alibaba'), ('alibaba/qwen-image-3.0/edit', 'Qwen Image 3.0', 'Alibaba'), ('wavespeed-ai/qwen-image-max/edit', 'Qwen Image Max', 'Alibaba'),
    ('x-ai/grok-imagine-image-v2.0/edit', 'Grok Imagine 2.0', 'xAI'), ('x-ai/grok-imagine-image-quality/edit', 'Grok Imagine Quality', 'xAI'),
    ('ideogram-ai/ideogram-character', 'Ideogram Character', 'Ideogram'),
    ('hf:mstudio', 'Marketing Studio', 'Higgsfield')]
_LIGA_FUERA = re.compile(r'lora|sequential|layer|genfill|fill|inpaint|blend|background|try-on|product-holding|multiple-angles|material|ic-light|pulid|redux|ai-instagram|ai-travel|patina|chrono|instant-character')
_LIGA_SABE = {'prompt', 'images', 'image', 'aspect_ratio', 'size', 'resolution', 'quality', 'output_format', 'num_images', 'seed', 'enable_base64_output', 'enable_sync_mode', 'enable_safety_checker', 'negative_prompt', 'guidance_scale', 'num_inference_steps', 'strength', 'variant', 'prompt_optimization_mode'}
def _liga_catalogo(forzar=False):   # los generadores de imagen con referencia que se pueden usar en un duelo: WaveSpeed (su catálogo, cada 6 h) + Higgsfield por API
    with _LIGA_CAT_L:
        if _LIGA_CAT['L'] and not forzar and time.time() - _LIGA_CAT['t'] < 6 * 3600: return _LIGA_CAT['L']
        L = []
        if load_ws():
            _ctx.ws_modo = 'propia'
            try:
                d = ws('GET', '/api/v3/models'); M0 = d.get('data') if isinstance(d.get('data'), list) else (d.get('data') or {}).get('items') or []
            except Exception as e: plog('liga catálogo ✕ ' + str(e)[:160]); M0 = []
            for m in M0:
                try: rs = m['api_schema']['api_schemas'][0]['request_schema']; p = rs.get('properties') or {}
                except Exception: continue
                mid = str(m.get('model_id') or '')
                if m.get('type') != 'image-to-image' or 'prompt' not in p or not ('images' in p or 'image' in p) or _LIGA_FUERA.search(mid) or not set(rs.get('required') or []) <= _LIGA_SABE: continue
                L.append({'id': mid, 'nombre': str(m.get('name') or mid), 'prov': 'ws', 'grupo': mid.split('/')[0], 'precio': float(m.get('base_price') or 0), 'p': p})
        if _hf_listo():
            for k in ('mstudio', 'grok', 'qwen'):
                if k in MODELS: L.append({'id': 'hf:' + k, 'nombre': MODELS[k]['name'] + ' (Higgsfield)', 'prov': 'hf', 'grupo': 'higgsfield', 'precio': float(MODELS[k]['usd']['high'])})
        orden = {i: (k, n, g) for k, (i, n, g) in enumerate(LIGA_ELEGIDOS)}
        L = sorted([dict(x, nombre=orden[x['id']][1], grupo=orden[x['id']][2]) for x in L if x['id'] in orden], key=lambda x: orden[x['id']][0])   # solo los elegidos, con su nombre limpio
        if L: _LIGA_CAT['L'] = L; _LIGA_CAT['t'] = time.time()
        return L
def _liga_cat_de(mid): return next((x for x in _LIGA_CAT['L'] or _liga_catalogo() if x['id'] == mid), None)
def _liga_payload(c, prompt, url):   # el cuerpo de la petición a partir de lo que pide el modelo (su esquema): 9:16, 2K y calidad alta si los tiene
    p = c['p']; b = {'prompt': prompt}
    if 'images' in p: b['images'] = [url]
    else: b['image'] = url
    en = lambda k: (p.get(k) or {}).get('enum') or []
    if 'aspect_ratio' in p and (not en('aspect_ratio') or '9:16' in en('aspect_ratio')): b['aspect_ratio'] = '9:16'
    if 'size' in p:
        op = en('size')
        if op:
            def ar(x):
                try: w, h = [int(v) for v in re.split(r'[*x×]', str(x))]; return abs(w / h - 9 / 16) + (0 if w * h >= 1500000 else 0.2)
                except Exception: return 9
            b['size'] = min(op, key=ar)
        elif (p['size'].get('type') == 'string'): b['size'] = '1152*2048'
    for k, pref in (('resolution', ('2k', '2K', '1.5k', '1k')), ('quality', ('high', 'hd')), ('output_format', ('jpeg', 'jpg'))):
        e = en(k)
        if e: b[k] = next((v for v in pref if v in e), e[0] if k != 'quality' else (p[k].get('default') or e[-1]))
    if 'num_images' in p: b['num_images'] = 1 if not en('num_images') or 1 in en('num_images') else min(en('num_images'))   # se usa la primera
    return b
def liga_dir(): return LIGA_WEB if SERVIDOR else LIGA_DIR
def liga_puede(): return (not SERVIDOR) or not aria_fija()   # en la web: solo el equipo
_liga_ll = threading.Lock(); _liga_cer = {}
def _liga_cerrojo(did):
    with _liga_ll: return _liga_cer.setdefault(did, threading.Lock())
def _liga_ok_id(did): return isinstance(did, str) and bool(re.fullmatch(r'[A-Za-z0-9_.-]+', did)) and not did.startswith(('.', '_')) and os.path.isfile(os.path.join(liga_dir(), did, 'duelo.json'))
def _liga_lee(did, fn):
    try: return json.load(open(os.path.join(liga_dir(), did, fn), encoding='utf-8'))
    except Exception: return {}
def _liga_cambia(did, fn):   # duelo.json: leer, cambiar y escribir de golpe, de uno en uno
    with _liga_cerrojo(did):
        fp = os.path.join(liga_dir(), did, 'duelo.json'); Dd = json.load(open(fp, encoding='utf-8')); fn(Dd)
        tmp = fp + f'.tmp{threading.get_ident()}'; json.dump(Dd, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1); os.replace(tmp, fp); return Dd
def _liga_claude(sistema, texto, max_tokens=16000):   # → el JSON que devuelve Claude
    k = _env('ANTHROPIC_API_KEY', 'anthropic.env')
    if not k: raise RuntimeError('Falta la clave de Claude en la cuenta de Aria («🔑 Mis APIs»)')
    body = {'model': LIGA_LLM, 'max_tokens': max_tokens, 'system': sistema, 'messages': [{'role': 'user', 'content': texto}]}
    rq = urllib.request.Request('https://api.anthropic.com/v1/messages', data=json.dumps(body).encode(), method='POST', headers={'x-api-key': k, 'anthropic-version': '2023-06-01', 'content-type': 'application/json', 'User-Agent': UA})
    try: r = json.loads(urllib.request.urlopen(rq, timeout=900).read())
    except urllib.error.HTTPError as e: raise RuntimeError(f'Claude respondió {e.code}: ' + e.read().decode('utf-8', 'replace')[:200])
    t = ''.join(b.get('text', '') for b in r.get('content') or [] if b.get('type') == 'text')
    try: return json.loads(t[t.index('{'):t.rindex('}') + 1])
    except Exception: raise RuntimeError('Claude no devolvió un JSON válido: ' + t[:160])
def _liga_gen(did, modelo_id, prompt, dest):   # una imagen 9:16 con la ficha de Aria como referencia → (img, mini, w, h, usd); dest = 'galeria/p01'
    ficha = str((_cat_load()[1].get('perfil') or {}).get('ficha') or 'assets/perfil/ficha360.jpg').split('?')[0]; url = None; precio = 0.0
    if str(modelo_id).startswith('hf:'):   # Higgsfield por API (clave de la cuenta de Aria)
        M = MODELS.get(modelo_id[3:])
        if not M or not _hf_listo(): raise RuntimeError('Falta la clave de Higgsfield en la cuenta de Aria («🔑 Mis APIs»)')
        res = api('POST', '/' + M['ep'], M['body'](prompt, [resolve_image({'path': ficha})], aspect_ok('9:16'), 'high')); rid = res.get('request_id'); precio = float(M['usd']['high'])
        for _ in range(240):
            time.sleep(4); st = api('GET', f'/requests/{rid}/status')
            if st.get('status') == 'completed': ims = st.get('images') or (st.get('output') or {}).get('images') or []; url = (ims[0].get('url') if ims and isinstance(ims[0], dict) else ims[0] if ims else None); break
            if st.get('status') in ('failed', 'nsfw', 'canceled'): raise RuntimeError('Higgsfield: ' + str(st.get('error') or st.get('status'))[:200])
    else:   # WaveSpeed: los de siempre o cualquiera de su catálogo
        if not load_ws(): raise RuntimeError('Falta la clave de WaveSpeed en la cuenta de Aria («🔑 Mis APIs»)')
        _ctx.ws_modo = 'propia'; ref = resolve_ws({'path': ficha}); mk = LIGA_WS.get(modelo_id)
        if mk: M = WS_MODELS[mk]; ep = M['ep']; payload = M['body'](prompt, [ref], aspect_ok('9:16'), 'high'); precio = float(M['usd']['high'])
        else:
            c = _liga_cat_de(modelo_id)
            if not c or c['prov'] != 'ws': raise RuntimeError(f'«{modelo_id}» no está en el catálogo de WaveSpeed')
            ep = c['id']; payload = _liga_payload(c, prompt, ref); precio = c['precio']
        r = ws('POST', '/api/v3/' + ep, payload); rid = (r.get('data') or {}).get('id')
        if not rid: raise RuntimeError('WaveSpeed no devolvió id: ' + json.dumps(r)[:160])
        for _ in range(240):
            time.sleep(4); w = ws('GET', f'/api/v3/predictions/{rid}/result').get('data') or {}
            if w.get('status') == 'completed': url = (w.get('outputs') or [None])[0]; break
            if w.get('status') == 'failed': raise RuntimeError('WaveSpeed: ' + str(w.get('error') or 'falló')[:200])
    if not url: raise RuntimeError('El generador no terminó a tiempo')
    data = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=300).read()
    from PIL import Image
    import io as _io
    ext = '.png' if url.lower().split('?')[0].endswith('.png') else '.jpg'; base = os.path.join(liga_dir(), did)
    img = dest + ext; fp = os.path.join(base, *img.split('/')); os.makedirs(os.path.dirname(fp), exist_ok=True); open(fp, 'wb').write(data)
    im = Image.open(_io.BytesIO(data)).convert('RGB'); w0, h0 = im.size; mini = os.path.dirname(dest) + '/mini/' + os.path.basename(dest) + '.jpg'
    mp = os.path.join(base, *mini.split('/')); os.makedirs(os.path.dirname(mp), exist_ok=True); im.thumbnail((480, 960)); im.save(mp, quality=86)
    return img, mini, w0, h0, precio
def _liga_suma(Dd, usd):   # coste acumulado del duelo
    Dd['coste_usd'] = round(float(Dd.get('coste_usd') or 0) + usd, 3); Dd['coste'] = f"${Dd['coste_usd']:.2f} en imágenes (WaveSpeed)"
def _liga_textos_de(M, tipos):   # comentarios del equipo de ciertos tipos (para dárselos a Claude)
    return [p.get('texto', '') for p in (M.get('peticiones') or []) if p.get('tipo') in tipos and p.get('texto')]
def _liga_mundos(did, solo=None, nota=''):   # 3 mundos con 6 historias y su portada (o rehacer uno)
    Dd = _liga_lee(did, 'duelo.json'); M = _liga_lee(did, 'max.json'); lado = Dd.get('galeria_lado') or 'b'; mod = Dd[lado].get('modelo')
    _liga_cambia(did, lambda x: x.update({'trabajando': {'paso': 1, 'texto': 'Claude está escribiendo los mundos y sus historias…'}}))
    guia = '\n'.join(filter(None, [Dd.get('nota_inicial') or '', *_liga_textos_de(M, ('nuevo',)), nota]))
    previos = [w.get('titulo') for w in Dd.get('mundos') or []]
    pide = f"Duelo: {Dd['a']['nombre']} contra {Dd['b']['nombre']}.\n{('Ideas del equipo: ' + guia) if guia else ''}\n{('Rehaz SOLO un mundo nuevo distinto de: ' + ', '.join(previos)) if solo else ''}\n" + \
           f"Propón {1 if solo else 3} MUNDO(S) muy distintos entre sí (lugares y situaciones reales y concretas, con mucha vida y detalle visual, preferiblemente en España). Para cada uno: id (minúsculas sin espacios), emoji, titulo, desc (2 frases en español), prompt_img (prompt en inglés para su PORTADA: Aria en ese mundo, siguiendo las reglas) y secuencias: 6 historias con id (<id>-1…), tono (emoji + palabra: 😂 Graciosa, 💛 Tierna, 🎡 Romántica, 🎆 Épica, 🕵️ Misteriosa, 🍻 Fiesta…), titulo y resumen (una frase).\n" + \
           'Responde SOLO con JSON: {"mundos": [...]}'
    W = _liga_claude(LIGA_REGLAS, pide).get('mundos') or []
    if not W: raise RuntimeError('Claude no propuso mundos')
    _liga_cambia(did, lambda x: x.update({'trabajando': {'paso': 1, 'texto': 'Generando la portada de cada mundo…'}}))
    hechos = []
    for w in W[:1 if solo else 3]:
        wid = re.sub(r'[^a-z0-9-]+', '-', str(w.get('id') or 'mundo').lower()).strip('-')[:30] or 'mundo'
        img, mini, _, _, usd = _liga_gen(did, mod, w.get('prompt_img') or w.get('desc', ''), 'mundos/' + wid)
        hechos.append({'id': wid, 'emoji': w.get('emoji', '🌍'), 'titulo': w.get('titulo', ''), 'modelo': Dd[lado].get('nombre'), 'desc': w.get('desc', ''), 'secuencias': w.get('secuencias') or [], 'img': img, 'mini': mini, 'v': str(int(time.time())), 'prompt_img': w.get('prompt_img', '')})
        _liga_cambia(did, lambda x, u=usd: _liga_suma(x, u))
    def pon(x):
        if solo: x['mundos'] = [hechos[0] if m.get('id') == solo else m for m in x.get('mundos') or []]
        else: x['mundos'] = hechos
        x['trabajando'] = None; x['aviso'] = 'Ya están los mundos: elige uno y su historia (o cuéntanos la tuya) y pulsa Siguiente.'; x['aviso_paso'] = 1
    _liga_cambia(did, pon)
def _liga_prompts(did, n=30, extra=False):   # los prompts de la galería a partir del mundo y la historia elegidos
    Dd = _liga_lee(did, 'duelo.json'); M = _liga_lee(did, 'max.json')
    w = next((x for x in Dd.get('mundos') or [] if x.get('id') == M.get('mundo')), None)
    if not w: raise RuntimeError('Elige primero un mundo')
    sq = next((x for x in w.get('secuencias') or [] if x.get('id') == M.get('secuencia')), None)
    tests = Dd.get('tests') or LIGA_TESTS; ya = Dd.get('prompts') or []
    _liga_cambia(did, lambda x: x.update({'trabajando': {'paso': 3 if extra else 2, 'texto': f'Claude está escribiendo {n} prompts…'}}))
    pide = f"Mundo: {w.get('titulo')} — {w.get('desc')}\nHistoria elegida: {(sq or {}).get('titulo', '')} — {(sq or {}).get('resumen', '')}\n" + \
           f"Batería de tests: {json.dumps([{'n': t['n'], 'nombre': t['nombre'], 'que': t['que']} for t in tests], ensure_ascii=False)}\n" + \
           (f"Ya hay estas escenas (no las repitas): {json.dumps([p.get('escena') for p in ya], ensure_ascii=False)}\n" if ya else '') + \
           f"Escribe {n} prompts que cuenten esa historia momento a momento, repartidos entre los tests (todos los tests al menos una vez si n ≥ 18). Para cada uno: test (número), escena (una frase en español) y prompt (inglés, largo y detallado, siguiendo las reglas).\n" + \
           'Responde SOLO con JSON: {"prompts": [{"test": 1, "escena": "...", "prompt": "..."}]}'
    P = _liga_claude(LIGA_REGLAS, pide, 20000).get('prompts') or []
    if not P: raise RuntimeError('Claude no escribió prompts')
    k0 = len(ya)
    nuevos = [{'id': f'p{k0 + i + 1:02d}', 'test': int(p.get('test') or 1), 'escena': p.get('escena', ''), 'prompt': p.get('prompt', '')} for i, p in enumerate(P[:n])]
    lado = Dd.get('galeria_lado') or 'b'; mo = Dd[lado].get('modelo'); c = _liga_cat_de(mo) if mo not in LIGA_WS else None
    usd = float(WS_MODELS.get(LIGA_WS.get(mo), {}).get('usd', {}).get('high', 0)) if mo in LIGA_WS else float((c or {}).get('precio') or 0.1)
    def pon(x):
        x['prompts'] = (x.get('prompts') or []) + nuevos; x['tests'] = x.get('tests') or tests; x['trabajando'] = None
        x['coste_estimado'] = f"galería de {len(x['prompts'])} imágenes con {x[lado]['nombre']} ≈ ${len(x['prompts']) * usd:.2f} (WaveSpeed)"
        if not extra: x['aviso'] = 'Prompts listos.' + (' Revísalos y pulsa Siguiente para generar la galería.' if M.get('revisar_prompts') else ' Generando la galería…'); x['aviso_paso'] = 2
    _liga_cambia(did, pon)
    return [p['id'] for p in nuevos]
def _liga_reescribe(prompt, nota):   # el mismo prompt con lo que pide el equipo
    return _liga_claude(LIGA_REGLAS, f"Prompt actual:\n{prompt}\n\nCambio que pide el equipo: {nota}\n\nReescribe el prompt aplicando el cambio y manteniendo las reglas. Responde SOLO con JSON: {{\"prompt\": \"...\"}}", 4000).get('prompt') or prompt
def _liga_prompt_de(Dd, M, pid):
    mp = M.get('prompts') if isinstance(M.get('prompts'), dict) else {}
    p = next((x for x in Dd.get('prompts') or [] if x.get('id') == pid), {})
    v = mp.get(pid); return (v.get('prompt') if isinstance(v, dict) else v) or p.get('prompt', '')
def _liga_galeria(did, pids=None):   # la galería con el modelo del lado de la galería (de 3 en 3)
    from concurrent.futures import ThreadPoolExecutor
    Dd = _liga_lee(did, 'duelo.json'); M = _liga_lee(did, 'max.json'); lado = Dd.get('galeria_lado') or 'b'; mod = Dd[lado].get('modelo')
    faltan = [p['id'] for p in Dd.get('prompts') or [] if p['id'] not in (Dd.get('galeria') or {}) and p['id'] not in (Dd.get('fallidas') or {}) and (pids is None or p['id'] in pids)]
    if not faltan: return
    _liga_cambia(did, lambda x: x.update({'generando': sorted(set(x.get('generando') or []) | set(faltan)), 'trabajando': {'paso': 3, 'texto': f'Generando la galería: {len(faltan)} imágenes con {Dd[lado]["nombre"]}…'}}))
    c = (getattr(_ctx, 'uid', None), getattr(_ctx, 'email', ''), getattr(_ctx, 'interno', False))
    def una(pid):
        with como(*c):
            try:
                img, mini, w0, h0, usd = _liga_gen(did, mod, _liga_prompt_de(Dd, M, pid), 'galeria/' + pid)
                def pon(x): x.setdefault('galeria', {})[pid] = {'img': img, 'mini': mini, 'w': w0, 'h': h0, 'v': str(int(time.time()))}; x['generando'] = [g for g in x.get('generando') or [] if g != pid]; _liga_suma(x, usd)
            except Exception as er:
                plog(f'liga {did} {pid} ✕ {er}')
                def pon(x, m=str(er)[:200]): x.setdefault('fallidas', {})[pid] = m; x['generando'] = [g for g in x.get('generando') or [] if g != pid]
            _liga_cambia(did, pon)
    with ThreadPoolExecutor(3) as ex: list(ex.map(una, faltan))
    def fin(x):
        x['trabajando'] = None; nf = len(x.get('fallidas') or {})
        x['aviso'] = f'Galería lista ({len(x.get("galeria") or {})} imágenes){" · " + str(nf) + " fallaron" if nf else ""}: marca tus favoritas, la portada y el cierre, y pulsa Siguiente.'; x['aviso_paso'] = 3
    _liga_cambia(did, fin)
def _liga_lado(Dd, pid, s, nota=''):   # genera (o rehace) un lado del duelo para un prompt
    M = _liga_lee(Dd['id'], 'max.json'); prompt = _liga_prompt_de(Dd, M, pid)
    dn = (M.get('duelo') or {}).get(pid); nota = nota or (dn.get('nota') if isinstance(dn, dict) else dn if isinstance(dn, str) else '') or ''
    if nota and nota.strip(): prompt = _liga_reescribe(prompt, nota.strip())
    gl = Dd.get('galeria_lado') or 'b'; carpeta = 'galeria' if s == gl else 'campeon'
    img, mini, _, _, usd = _liga_gen(Dd['id'], Dd[s].get('modelo'), prompt, f'{carpeta}/{pid}' + ('' if s != gl or not nota else f'-{int(time.time())}'))
    def pon(x):
        g = (x.get('galeria') or {}).get(pid) or {}; par = x.setdefault('duelo', {}).setdefault(pid, {})
        par.setdefault(gl, g.get('img')); par.setdefault(gl + '_mini', g.get('mini')); par[s] = img; par[s + '_mini'] = mini
        if s == gl: x.setdefault('galeria', {})[pid] = dict(g, img=img, mini=mini, v=str(int(time.time())))
        x['generando'] = [q for q in x.get('generando') or [] if q != pid]; _liga_suma(x, usd)
    _liga_cambia(Dd['id'], pon)
def _liga_responde(did, pid, estado, texto):
    _liga_cambia(did, lambda x: x.setdefault('respuestas', {}).update({pid: {'estado': estado, 'texto': texto, 't': time.strftime('%Y-%m-%d %H:%M:%S')}}))
def _liga_peticion(did, p):   # lo que pide el equipo desde la página
    tipo, ref, texto = p.get('tipo'), str(p.get('ref') or ''), str(p.get('texto') or '')
    _liga_responde(did, p['id'], 'trabajando', 'En ello…'); Dd = _liga_lee(did, 'duelo.json'); gl = Dd.get('galeria_lado') or 'b'; otro = 'a' if gl == 'b' else 'b'
    if tipo == 'generar':
        pids = [x for x in p.get('pids') or [] if isinstance(x, str)]
        _liga_cambia(did, lambda x: x.update({'generando': sorted(set(x.get('generando') or []) | set(pids)), 'trabajando': {'paso': 4, 'texto': f'Generando {len(pids)} con {Dd[otro]["nombre"]}…'}}))
        from concurrent.futures import ThreadPoolExecutor
        c = (getattr(_ctx, 'uid', None), getattr(_ctx, 'email', ''), getattr(_ctx, 'interno', False)); mal = []
        def una(pid):
            with como(*c):
                try: _liga_lado(_liga_lee(did, 'duelo.json'), pid, otro)
                except Exception as er: mal.append(pid); plog(f'liga {did} {pid} ✕ {er}'); _liga_cambia(did, lambda x: x.update({'generando': [q for q in x.get('generando') or [] if q != pid]}))
        with ThreadPoolExecutor(3) as ex: list(ex.map(una, pids))
        _liga_cambia(did, lambda x: x.update({'trabajando': None, 'aviso': f'Listas {len(pids) - len(mal)} parejas con {Dd[otro]["nombre"]}' + (f' ({len(mal)} fallaron: vuelve a pedirlas)' if mal else '') + '. Revisa títulos e imágenes y pulsa Siguiente para el carrusel.', 'aviso_paso': 4}))
        return _liga_responde(did, p['id'], 'hecha', f'Listas {len(pids) - len(mal)} de {len(pids)} con {Dd[otro]["nombre"]}.')
    if tipo in ('regenerar', 'imagen'):
        pid, _, s = ref.partition(':'); s = p.get('lado') or s or gl
        nota = texto.split(':', 1)[1].strip() if tipo == 'regenerar' and ':' in texto else texto
        _liga_cambia(did, lambda x: x.update({'generando': sorted(set(x.get('generando') or []) | {pid})}))
        _liga_lado(_liga_lee(did, 'duelo.json'), pid, s if s in ('a', 'b') else gl, nota)
        return _liga_responde(did, p['id'], 'hecha', 'Hecha de nuevo' + (' con tu nota.' if nota else '.'))
    if tipo == 'mas':
        n = max(1, min(int(p.get('n') or 3), 12)); nuevos = _liga_prompts(did, n, extra=True); _liga_galeria(did, nuevos)
        return _liga_responde(did, p['id'], 'hecha', f'{len(nuevos)} imágenes más en la galería.')
    if tipo == 'secuencia':
        def pon(x):
            for w in x.get('mundos') or []:
                if w.get('id') == ref: k = sum(1 for q in w.get('secuencias') or [] if '-tuya' in str(q.get('id'))) + 1; w.setdefault('secuencias', []).insert(0, {'id': f'{ref}-tuya{k}', 'tono': '✍️ La tuya', 'titulo': texto[:48], 'resumen': texto})
        _liga_cambia(did, pon); return _liga_responde(did, p['id'], 'hecha', 'Tu historia ya está en la lista: elígela.')
    if tipo == 'mundo':
        _liga_mundos(did, solo=ref, nota=texto); return _liga_responde(did, p['id'], 'hecha', 'Mundo rehecho con tu comentario.')
    if tipo == 'nuevo':
        if Dd.get('mundos'): _liga_mundos(did, nota=texto)
        return _liga_responde(did, p['id'], 'hecha', 'Tenido en cuenta para los mundos.')
    if tipo == 'publicar':
        return _liga_responde(did, p['id'], 'hecha', 'Publicar en Notion e Instagram lo hace de momento Claude desde el ordenador de Max: avísale. Mientras, descarga el carrusel en el paso Carrusel.')
    return _liga_responde(did, p['id'], 'hecha', 'Recibido.')
_LIGA_EN = set(); _LIGA_EN_L = threading.Lock()
_LIGA_FALLOS = {}
def _liga_tarea(did, clave, fn):   # una tarea a la vez por (duelo, clave), en su hilo y como la cuenta de Aria (sus claves)
    with _LIGA_EN_L:
        if (did, clave) in _LIGA_EN: return
        nf, tf = _LIGA_FALLOS.get((did, clave), (0, 0))
        if nf >= 3 or (nf and time.time() - tf < 60 * nf): return   # v260: tras un fallo espera; tras 3 seguidos, se para hasta reiniciar
        _LIGA_EN.add((did, clave))
    def corre():
        try:
            with como(ARIA_UID, ARIA_EMAIL, True): fn()
            _LIGA_FALLOS.pop((did, clave), None)
        except Exception as e:
            plog(f'liga {did} {clave} ✕ {e}'); nf = _LIGA_FALLOS.get((did, clave), (0, 0))[0] + 1; _LIGA_FALLOS[(did, clave)] = (nf, time.time())
            try:
                _liga_cambia(did, lambda x: x.update({'trabajando': None, 'aviso': '⚠️ ' + str(e)[:300], **({'error_' + clave: str(e)[:300]} if clave in ('mundos', 'prompts') else {})}))
                if clave.startswith('q'): _liga_responde(did, clave, 'error', '⚠️ ' + str(e)[:300])
            except Exception: pass
        finally:
            with _LIGA_EN_L: _LIGA_EN.discard((did, clave))
    threading.Thread(target=corre, daemon=True).start()
def _liga_vigia():   # el trabajador: mira los duelos cada pocos segundos y hace lo que toca
    while True:
        time.sleep(5)
        try:
            if not os.path.isdir(LIGA_WEB): continue
            for did in sorted(os.listdir(LIGA_WEB)):
                if not _liga_ok_id(did): continue
                Dd = _liga_lee(did, 'duelo.json'); M = _liga_lee(did, 'max.json'); listo = M.get('listo') or {}; resp = Dd.get('respuestas') or {}
                if not Dd.get('mundos') and not Dd.get('error_mundos'): _liga_tarea(did, 'mundos', lambda d=did: _liga_mundos(d)); continue
                if '1' in listo and M.get('secuencia') and not Dd.get('prompts') and not Dd.get('error_prompts'): _liga_tarea(did, 'prompts', lambda d=did: _liga_prompts(d)); continue
                if Dd.get('prompts') and ('2' in listo or ('1' in listo and not M.get('revisar_prompts'))):
                    if any(p['id'] not in (Dd.get('galeria') or {}) and p['id'] not in (Dd.get('fallidas') or {}) for p in Dd['prompts']): _liga_tarea(did, 'galeria', lambda d=did: _liga_galeria(d))
                for p in M.get('peticiones') or []:
                    if isinstance(p, dict) and p.get('id') and p['id'] not in resp: _liga_tarea(did, p['id'], lambda d=did, q=p: _liga_peticion(d, q))
        except Exception as e: plog('liga vigía ✕ ' + str(e)[:200])
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
def _sb_adm(metodo, path, body=None, prefer=''):   # v277: la lista de miembros con la clave secreta del servidor (solo para el panel 👥 Miembros del equipo)
    sec = os.environ.get('SUPABASE_SECRET') or ''
    if not sec: raise RuntimeError('falta SUPABASE_SECRET en el servidor')
    hd = {'apikey': sec, 'Authorization': 'Bearer ' + sec, 'Accept': 'application/json', 'User-Agent': UA}
    if body is not None: hd['Content-Type'] = 'application/json'
    if prefer: hd['Prefer'] = prefer
    rq = urllib.request.Request(SB_URL + path, data=None if body is None else json.dumps(body).encode(), headers=hd, method=metodo)
    with urllib.request.urlopen(rq, timeout=20) as r: raw = r.read(1 << 22)
    return json.loads(raw) if raw.strip() else None
def _mi_lista():
    try: L = _sb_adm('GET', '/rest/v1/miembros?select=email,interno,precio,alta&order=alta.desc')
    except urllib.error.HTTPError as e:
        if e.code != 400: raise
        L = _sb_adm('GET', '/rest/v1/miembros?select=email,interno,alta&order=alta.desc')
    return [{'email': str(m.get('email') or ''), 'interno': m.get('interno') is True, 'precio': m.get('precio'), 'alta': str(m.get('alta') or '')[:10]} for m in (L or []) if isinstance(m, dict)]
_VISTO = {}; _visto_l = threading.Lock(); _visto_g = [0.0, False]   # v280: uid → {email, t (última petición), primera, movil}
def _visto_fp(): return os.path.join(DATOS, 'visto.json')
def _visto_carga():
    if _visto_g[1]: return
    _visto_g[1] = True
    try: d = json.load(open(_visto_fp(), encoding='utf-8'))
    except Exception: d = {}
    if isinstance(d, dict): _VISTO.update({k: v for k, v in d.items() if isinstance(v, dict) and k not in _VISTO})
def _visto_pon(u, email, ua):
    if not SERVIDOR or not DATOS or not u: return
    ahora = time.time()
    with _visto_l:
        _visto_carga(); v = _VISTO.setdefault(u, {'primera': int(ahora)})
        v.update({'t': int(ahora), 'email': email, 'movil': bool(re.search(r'iPhone|iPad|Android|Mobile', ua or ''))})
        hoy = time.strftime('%Y-%m-%d', time.localtime(ahora))
        if v.get('dia') != hoy: v['dia'] = hoy; v['dias'] = int(v.get('dias') or 0) + 1   # v317: días distintos que ha entrado
        if ahora - _visto_g[0] < 60: return
        _visto_g[0] = ahora; d = json.loads(json.dumps(_VISTO))
    try:
        fp = _visto_fp(); open(fp + '.tmp', 'w', encoding='utf-8').write(json.dumps(d)); os.replace(fp + '.tmp', fp)
    except Exception as e: plog('visto ✕ ' + str(e)[:120])
_ADM_C = {}   # uid → (cuándo, datos de la cuenta) · se recalcula como mucho cada 2 min
def _adm_cuenta(u):
    c = _ADM_C.get(u)
    if c and time.time() - c[0] < 120: return c[1]
    b = os.path.join(DATOS, 'usuarios', u); mes = time.strftime('%Y-%m', time.gmtime()); n = 0; gasto = 0.0; ult = 0
    for sub in ('live', 'video'):
        dd = os.path.join(b, 'assets', sub)
        try: L = os.listdir(dd)
        except OSError: continue
        for x in L:
            if x.startswith('.') or not x.endswith('.json'): continue
            n += 1
            try:
                m = json.load(open(os.path.join(dd, x), encoding='utf-8')); t = float(m.get('t') or 0); ult = max(ult, t)
                if t and time.strftime('%Y-%m', time.gmtime(t)) == mes: gasto += float(m.get('usd') if m.get('usd') is not None else m.get('usd_est') or 0)
            except Exception: pass
    try: mo = json.load(open(os.path.join(b, 'monedero.json'), encoding='utf-8'))
    except Exception: mo = None   # v284: sin monedero todavía (no ha usado el saldo regalo): no se enseña «le queda 0 $»
    sin_mon = not isinstance(mo, dict); mo = {} if sin_mon else mo
    queda = (float(mo.get('resto') or 0) if mo.get('mes') == mes else 0.0) + float(mo.get('extra') or 0) + float(mo.get('bienvenida') or 0)
    regalo = sum(float(h.get('usd') or 0) for h in (mo.get('hist') or []) if isinstance(h, dict) and str(h.get('dia') or '').startswith(mes) and float(h.get('usd') or 0) > 0)
    try: pj = sum(1 for x in os.listdir(os.path.join(b, 'assets', 'personajes')) if not x.startswith(('.', '_')))
    except OSError: pj = 0
    try: clave = os.path.getsize(os.path.join(b, 'claves.env')) > 10
    except OSError: clave = False
    with como(u, '', False): esp = espacio(True)
    apis = []   # v315: qué APIs propias tiene conectadas (solo el nombre del servicio; las claves nunca salen)
    try:
        K = {}
        for ln in open(os.path.join(b, 'claves.env'), encoding='utf-8'):
            k_, _, v_ = ln.strip().partition('=')
            if k_ and v_.strip(): K[k_] = v_.strip()
        NOM = {'WS_API_KEY': 'WaveSpeed', 'ANTHROPIC_API_KEY': 'Claude', 'ARK_API_KEY': 'BytePlus', 'ELEVENLABS_API_KEY': 'ElevenLabs', 'HF_API_KEY': 'Higgsfield', 'HF_KEY': 'Higgsfield', 'HIGGSFIELD_KEY': 'Higgsfield'}
        apis = sorted({NOM.get(k_, k_.replace('_API_KEY', '').replace('_KEY', '').title()) for k_ in K if not k_.endswith('_OFF') and k_ + '_OFF' not in K})
    except OSError: pass
    r = {'apis': apis, 'creaciones': n, 'ultima': int(ult), 'gasto_mes': round(gasto, 4), 'regalo_mes': round(regalo, 4), 'queda_regalo': None if sin_mon else round(queda, 4), 'personajes': pj, 'clave': clave, 'espacio': esp}
    _ADM_C[u] = (time.time(), r); return r
_ADM_P = [0.0, None]
def _adm_panel():
    if _ADM_P[1] and time.time() - _ADM_P[0] < 20: return _ADM_P[1]
    L = _mi_lista(); por_mail = {m['email']: m for m in L}
    try: us = (_sb_adm('GET', '/auth/v1/admin/users?page=1&per_page=1000') or {}).get('users') or []
    except Exception as e: plog('admin: usuarios ✕ ' + str(e)[:120]); us = []
    auth = {str(x.get('email') or '').lower(): x for x in us if isinstance(x, dict) and x.get('email')}
    with _visto_l: _visto_carga(); vis = json.loads(json.dumps(_VISTO))
    uid_de = {str(v.get('email') or '').lower(): k for k, v in vis.items()}
    for e, a in auth.items(): uid_de.setdefault(e, str(a.get('id') or '').lower())
    d = _com_lee(); ahora = time.time(); filas = []; ig = _ign_lee()
    for e in sorted(set(por_mail) | set(auth)):
        m = por_mail.get(e) or {}; a = auth.get(e) or {}; u = uid_de.get(e) or ''
        v = vis.get(u) or {}; tiene = bool(u and _UUID.fullmatch(u) and os.path.isdir(os.path.join(DATOS, 'usuarios', u)))
        x = _adm_cuenta(u) if tiene else {}
        filas.append(dict({'email': e, 'acceso': e in por_mail, 'ignorado': e in ig and e not in por_mail, 'interno': bool(m.get('interno')), 'dueno': e in DUENOS, 'precio': m.get('precio'), 'alta': m.get('alta') or '',
                           'cid': _cid(u) if tiene else '', 'alias': str(d['alias'].get(_cid(u)) or '')[:40] if tiene else '',
                           'registro': str(a.get('created_at') or '')[:19], 'login': str(a.get('last_sign_in_at') or '')[:19],
                           'visto': int(v.get('t') or 0), 'dias': int(v.get('dias') or 0), 'primera': int(v.get('primera') or 0), 'online': bool(v.get('t') and ahora - v['t'] < 180), 'movil': bool(v.get('movil'))}, **x))
    try: du = shutil.disk_usage(DATOS); disco = {'usado': du.used, 'total': du.total}
    except Exception: disco = None
    res = {'filas': filas, 'disco': disco, 'cuota': CUOTA, 'bolsa': _bolsa_saldo(), 'casa_mes': round(_casa_global(), 4), 't': int(ahora),
           'resumen': {'miembros': sum(1 for r in filas if r['acceso']), 'equipo': sum(1 for r in filas if r['interno']), 'online': sum(1 for r in filas if r['online']),
                       'h24': sum(1 for r in filas if r['visto'] and ahora - r['visto'] < 86400), 'd7': sum(1 for r in filas if r['visto'] and ahora - r['visto'] < 7 * 86400),
                       'sin_acceso': sum(1 for r in filas if not r['acceso'] and not r.get('ignorado')), 'nunca': sum(1 for r in filas if r['acceso'] and not r['login']),
                       'creaciones': sum(r.get('creaciones') or 0 for r in filas), 'gasto_mes': round(sum(r.get('gasto_mes') or 0 for r in filas), 2)}}
    _ADM_P[0], _ADM_P[1] = time.time(), res; return res
def _ses_olvida(email):   # quien se quita de la lista deja de entrar ya, sin esperar a que caduque su sesión recordada
    with _ses_l:
        for k in [k for k, s in _ses.items() if isinstance(s[1], tuple) and s[1][1] == email]: del _ses[k]
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
    equipo = SERVIDOR and DATOS and not getattr(_ctx, 'ver_miembro', False) and (getattr(_ctx, 'interno', False) or (getattr(_ctx, 'email', '') or '').lower() in DUENOS) and getattr(_ctx, 'uid', None) != ARIA_UID
    for fp in ((_claves_fp(),) + ((os.path.join(DATOS, 'usuarios', ARIA_UID, 'claves.env'),) if equipo else ()) if SERVIDOR else (CLAVES, os.path.expanduser('~/.claude/' + home_file))):   # el equipo, si no tiene la suya, usa la de la cuenta de Aria
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
SIN_SALDO = 'Saldo regalo agotado. Se repone el día 1; para seguir ahora, conecta tu propia clave en «Mis APIs».'
_NSFW_RE = re.compile(r"\b(nsfw|topless|nipples?|areolas?|genitals?|genitalia|pubic|vagina|vulva|penis|no clothes|(?:is|are|she'?s|he'?s|fully|completely|totally|stark) naked|naked (?:woman|women|man|men|girl|boy|body|person|people|figure|torso|chest|skin)|(?:fully|completely|totally) nude|nude body|bare breasts?|no underwear|sexually explicit|explicit nud|desnud[oa]s?|sin ropa|sin nada de ropa|en pelotas|en bolas|pezon(?:es)?|pez[oó]n|sin sujetador|tetas al aire|pechos al aire|senos? desnudos?|genitales|sin bragas|en topless)", re.I)
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
_BOLSA_F = os.path.join(DATOS or RAIZ, 'bolsa.json'); _bolsa_l = threading.Lock(); _BOLSA_S = {'t': 0, 'v': None}
def _bolsa_lee():   # {aviso, camp:[{id,usd,nota,t}]}
    try: b = json.load(open(_BOLSA_F, encoding='utf-8'))
    except Exception: b = {}
    if not isinstance(b, dict): b = {}
    b.setdefault('aviso', 50.0); b.setdefault('camp', []); return b
def _bolsa_guarda(b):
    with _bolsa_l:
        with open(_BOLSA_F + '.tmp', 'w', encoding='utf-8') as f: json.dump(b, f, ensure_ascii=False)
        os.replace(_BOLSA_F + '.tmp', _BOLSA_F)
def _bolsa_saldo(fresco=False):   # el saldo de verdad de la cuenta de WaveSpeed de la casa (lo que Max recarga)
    if not fresco and time.time() - _BOLSA_S['t'] < 600: return _BOLSA_S['v']
    v = None
    try:
        if CASA_KEY:
            rq = urllib.request.Request('https://api.wavespeed.ai/api/v3/balance', headers={'Authorization': 'Bearer ' + CASA_KEY, 'User-Agent': UA})
            with urllib.request.urlopen(rq, timeout=20) as r: v = float(((json.loads(r.read() or b'{}')).get('data') or {}).get('balance'))
    except Exception as e: plog('bolsa: saldo ✕ ' + str(e)[:160])
    _BOLSA_S.update({'t': time.time(), 'v': v}); return v
def _bolsa_resumen():
    mes = time.strftime('%Y-%m', time.gmtime()); filas = []; comp = 0.0; d = _com_lee()
    for cid, u in _com_cuentas().items():
        try: m = json.load(open(os.path.join(DATOS, 'usuarios', u, 'monedero.json'), encoding='utf-8'))
        except Exception: continue
        if not isinstance(m, dict): continue
        queda = (float(m.get('resto') or 0) if m.get('mes') == mes else 0.0) + float(m.get('extra') or 0) + float(m.get('bienvenida') or 0); comp += queda
        gast = sum(float(h.get('usd') or 0) for h in (m.get('hist') or []) if isinstance(h, dict) and str(h.get('dia') or '').startswith(mes) and float(h.get('usd') or 0) > 0)
        filas.append({'cid': cid, 'alias': str(d['alias'].get(cid) or 'Creador sin nombre')[:40], 'gastado': round(gast, 4), 'queda': round(queda, 4), 'precio': m.get('precio'), 'n': sum(1 for h in (m.get('hist') or []) if isinstance(h, dict) and str(h.get('dia') or '').startswith(mes) and h.get('que') == 'imagen')})
    filas.sort(key=lambda x: -x['gastado']); b = _bolsa_lee()
    return {'saldo': _bolsa_saldo(), 'gastado': round(_casa_global(), 4), 'tope': CASA_TOPE, 'comprometido': round(comp, 4), 'aviso': b['aviso'], 'cuentas': len(filas), 'top': filas[:20], 'todas': filas, 'camp': b['camp'][-20:], 'pct': 10, 'bienvenida': BIENVENIDA}
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
    for c in _bolsa_lee().get('camp') or []:   # v269: campañas para todas las cuentas (una vez cada una)
        if isinstance(c, dict) and c.get('id') and c['id'] not in (m.get('camp') or []) and (not c.get('desde_alta') or int(m.get('alta') or 0) <= int(c.get('t') or 0)):
            m['extra'] = round(float(m.get('extra') or 0) + float(c.get('usd') or 0), 4); m.setdefault('camp', []).append(c['id']); m.setdefault('hist', []).append({'t': int(time.time()), 'dia': time.strftime('%Y-%m-%d', time.gmtime()), 'usd': -float(c.get('usd') or 0), 'que': 'regalo', 'nota': str(c.get('nota') or '')[:80]}); cambia = True
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
    saldo = max(0.0, round(float(m['resto']) + float(m.get('extra') or 0) + float(m['bienvenida']) - _casa_en_curso(), 4)); p = WS_MODELS[CASA_DEF]['usd']['std']
    return {'saldo': saldo, 'mensual': m['mensual'], 'resto': m['resto'], 'extra': float(m.get('extra') or 0), 'bienvenida': m['bienvenida'], 'mes': m['mes'], 'imagen': p, 'imagenes': int((saldo + 1e-6) // p), 'modelos': list(CASA_MODELOS), 'pausa': _casa_global() >= CASA_TOPE}
def casa_puede(usd):   # ¿llega el saldo regalo para esto? Si no, error claro
    if _casa_global() >= CASA_TOPE: plog(f'🎁 TOPE GLOBAL del saldo regalo alcanzado ({CASA_TOPE} $ este mes)'); raise RuntimeError('El saldo regalo está en pausa unos días. Mientras tanto puedes generar con tu propia clave en «Mis APIs».')
    c = casa_info()
    if not c: raise RuntimeError('WaveSpeed no está conectado: conéctalo en «Mis APIs»')
    if c['saldo'] + 1e-6 >= usd: return
    raise RuntimeError(SIN_SALDO if c['saldo'] < c['imagen'] else f"Tu saldo regalo (${c['saldo']:.2f}) no llega para esta imagen (${usd:.3f}). Prueba con {WS_MODELS[CASA_DEF]['name']} o conecta tu propia clave en «Mis APIs».")
def casa_cobra(usd, que, rid=None, modelo=None):   # descuenta del monedero (primero lo del mes, que caduca; luego la bienvenida) y lo apunta en su historial
    usd = round(float(usd or 0), 4)
    if usd <= 0: return
    with _cerrojo('mon'):
        m = _mon_lee(); H = m.setdefault('hist', [])
        if rid and any(h.get('rid') == rid for h in H): return   # ese trabajo ya se cobró
        a = min(float(m['resto']), usd); m['resto'] = round(float(m['resto']) - a, 4); x = min(float(m.get('extra') or 0), usd - a); m['extra'] = round(float(m.get('extra') or 0) - x, 4); m['bienvenida'] = round(max(0.0, float(m['bienvenida']) - (usd - a - x)), 4)   # v269: mes → regalos extra → bienvenida
        hoy = time.strftime('%Y-%m-%d', time.gmtime())
        if not rid and H and H[-1].get('que') == que and H[-1].get('dia') == hoy: H[-1]['usd'] = round(H[-1]['usd'] + usd, 4); H[-1]['n'] = H[-1].get('n', 1) + 1; H[-1]['t'] = int(time.time())   # las lecturas del día van en una sola línea
        else: H.append({'t': int(time.time()), 'dia': hoy, 'usd': usd, 'que': que, **({'rid': rid} if rid else {}), **({'modelo': modelo} if modelo else {})})
        m['hist'] = H[-400:]; _mon_guarda(m)
    _casa_global(usd)
def _casa_puerta(path, ctype=None):   # qué se puede pedir a WaveSpeed con la clave de la casa (solo POST): subir referencias, leer imágenes (se cobra) y generar con los modelos permitidos y con permiso
    if '/media/upload' in path:
        if not str(ctype or '').startswith('image/'): raise RuntimeError('Con el saldo regalo solo se pueden usar imágenes como referencia.')   # v260: nada de alojar otros ficheros en la cuenta de la casa
        return
    if '/any-llm' in path: casa_puede(LECTURA_USD); casa_cobra(LECTURA_USD, 'lectura'); return
    if getattr(_ctx, 'casa_ok', False) and any(path == '/api/v3/' + WS_MODELS[k]['ep'] for k in CASA_MODELOS): return
    if getattr(_ctx, 'casa_ok', False) and path == '/api/v3/' + UPSCALE_EP: return   # v266: ampliar a 4K también con el saldo regalo
    raise RuntimeError('Esto no entra en el saldo regalo: conecta tu propia clave en «Mis APIs».')
def ws(method, path, body=None, raw=None, ctype=None):
    modo = getattr(_ctx, 'ws_modo', None); k = '' if modo == 'casa' else load_ws()   # ws_modo: un trabajo se consulta con la misma clave con la que se lanzó
    if not k and modo != 'propia' and _casa_base():
        k = CASA_KEY
        if method == 'POST': _casa_puerta(path, ctype)
    if not k: raise RuntimeError('WaveSpeed no está conectado: conéctalo en «Mis APIs»' if SERVIDOR else 'falta WS_API_KEY en ~/.claude/wavespeed.env')
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
        if not p: raise RuntimeError('Ya no tienes permiso para crear con ese personaje (su creador lo ha retirado o lo ha ocultado). Quítalo de la imagen.' if str(img.get('path') or '').startswith('assets/prestamo/') else 'Esa imagen ya no está compartida contigo (su creador ha dejado de compartir la carpeta). Elige otra imagen a recrear.' if str(img.get('path') or '').startswith('assets/compartida/') else 'ruta no válida: ' + str(img.get('path', ''))[:200])
        data = open(p, 'rb').read(); ctype = mimetypes.guess_type(p)[0] or 'image/jpeg'
    if not ctype.startswith('image/'): return data, ctype
    return img_norm(data, ctype, img.get('crop'))
def ws_upload(data, ctype):
    if len(data) > 30 * 1024 * 1024: raise RuntimeError('Ese archivo pesa demasiado (máximo 30 MB).')   # v260
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
def unavailable(): return [] if (SERVIDOR or load_ws()) else UNAVAILABLE   # v260: en la web no salían repetidos con «próximamente»
UA = 'aria-mirror/1.0 (puente local; +https://higgsfield.ai)'   # Cloudflare devuelve 403 «error code: 1010» al User-Agent por defecto de Python
if not SERVIDOR:   # en local las carpetas de siempre existen desde el arranque; en servidor cada cuenta crea las suyas la primera vez (live_dir(), video_dir(), pers_dir(), refs_dir())
    for _d in ('live', 'video', 'personajes', 'refs'): os.makedirs(os.path.join(RAIZ, 'assets', _d), exist_ok=True)
# vídeo (docs pegadas por Max el 23 sep + dash.higgsfield.ai/models/<id>/llms.txt): precio por tokens = ceil(seg × ancho × alto × 24 / 1024); $0.014 / 1000 tokens (4K $0.008)
VIDEO_MODELS = {
    'i2v': {'ep': 'bytedance/seedance-2.0/image-to-video',     'name': 'Seedance 2.0 · imagen → vídeo'},
    'r2v': {'ep': 'bytedance/seedance-2.0/reference-to-video', 'name': 'Seedance 2.0 · con referencias (ficha 360)'},
}
V_ASPECTS = ['3:4', '9:16', '16:9', '1:1', '4:3', '21:9']
# v255 · los modelos de vídeo de WaveSpeed que se ofrecen (familia, nombre, base del id) · cada uno con sus modos: i2v (imagen inicial), t2v (texto + referencias), r2v
VID_CUR = [('Seedance', 'Seedance 2.0 Fast', 'bytedance/seedance-2.0-fast'), ('Seedance', 'Seedance 2.5', 'bytedance/seedance-2.5'),
           ('Kling', 'Kling 3.0 Omni Pro', 'kwaivgi/kling-video-o3-pro'), ('Kling', 'Kling 3.0 Omni', 'kwaivgi/kling-video-o3-std'), ('Kling', 'Kling 3.0 Pro', 'kwaivgi/kling-v3.0-pro'), ('Kling', 'Kling 3.0', 'kwaivgi/kling-v3.0-std'), ('Kling', 'Kling 2.6 Pro', 'kwaivgi/kling-v2.6-pro'),
           ('Veo', 'Veo 3.1', 'google/veo3.1'), ('Veo', 'Veo 3.1 Fast', 'google/veo3.1-fast'), ('Veo', 'Veo 3.1 Lite', 'google/veo3.1-lite'),
           ('Minimax', 'Hailuo 2.3 Pro', 'minimax/hailuo-2.3@pro'), ('Minimax', 'Hailuo 2.3', 'minimax/hailuo-2.3@standard'), ('Minimax', 'Minimax H3', 'minimax/h3'),
           ('Wan', 'Wan 3.0', 'alibaba/wan-3.0'), ('Grok', 'Grok Imagine 1.5', 'x-ai/grok-imagine-video-v1.5')]
_VCAT = {'t': 0, 'M': {}}; _VCAT_L = threading.Lock()
def _vcat(forzar=False):   # id → esquema y precio base, del catálogo de WaveSpeed (cada 6 h)
    with _VCAT_L:
        if _VCAT['M'] and not forzar and time.time() - _VCAT['t'] < 6 * 3600: return _VCAT['M']
        try: d = ws('GET', '/api/v3/models'); M0 = d.get('data') if isinstance(d.get('data'), list) else (d.get('data') or {}).get('items') or []
        except Exception as e: plog('catálogo de vídeo ✕ ' + str(e)[:160]); return _VCAT['M']
        M = {}
        for m in M0:
            try: rs = m['api_schema']['api_schemas'][0]['request_schema']
            except Exception: continue
            M[str(m.get('model_id') or '')] = {'p': rs.get('properties') or {}, 'req': rs.get('required') or [], 'usd': m.get('base_price') or m.get('price'), 'tipo': m.get('type')}
        if M: _VCAT['M'] = M; _VCAT['t'] = time.time()
        return _VCAT['M']
def _vmodos(base):   # {i2v|t2v|r2v: id} que existen en el catálogo para esa base
    M = _vcat(); b, var = (base.split('@') + [''])[:2]
    if var: C = {'i2v': f'{b}/i2v-{var}', 't2v': f'{b}/t2v-{var}'}
    else: C = {'i2v': f'{b}/image-to-video', 't2v': f'{b}/text-to-video', 'r2v': f'{b}/reference-to-video', 'se': f'{b}/start-end-to-video'}
    return {k: v for k, v in C.items() if v in M}
def _vinfo():   # lo que el panel necesita para cada modelo: modos, duraciones, resoluciones, formatos, audio, precio base
    out = []
    for fam, nom, base in VID_CUR:
        md = _vmodos(base)
        if not md: continue
        M = _vcat(); p = {}
        for k in ('i2v', 't2v', 'r2v'):
            if k in md: p = dict(M[md[k]]['p'], **p)
        pi = M[md['i2v']]['p'] if 'i2v' in md else {}; fin = 'se' in md or 'last_image' in pi or 'end_image' in pi
        en = lambda k: ((p.get(k) or {}).get('enum') or [])
        dur = en('duration') or ([x for x in range(int((p.get('duration') or {}).get('minimum') or 4), int((p.get('duration') or {}).get('maximum') or 10) + 1)] if 'duration' in p else [])
        dur = sorted(dur, key=lambda x: float(x))
        mx = lambda k: max([int(((M[v]['p'].get(k) or {}).get('maxItems')) or 0) for v in md.values()] + [0])
        maxi = {'img': max(mx('reference_images'), mx('images'), 1 if 'i2v' in md else 0), 'vid': mx('reference_videos'), 'aud': mx('reference_audios')}
        out.append({'id': base, 'fam': fam, 'nombre': nom, 'modos': sorted(k for k in md if k != 'se'), 'ini': 'i2v' in md, 'fin': fin, 'usd': min(float(M[v]['usd'] or 0) for v in md.values()), 'dur': dur, 'durDef': (p.get('duration') or {}).get('default'),
                    'res': en('resolution'), 'aspect': en('aspect_ratio'), 'audio': next((k for k in ('generate_audio', 'sound', 'audio') if (p.get(k) or {}).get('type') == 'boolean'), None), 'refs': 'r2v' in md or 'reference_images' in (M.get(md.get('t2v', ''), {}).get('p') or {}), 'max': maxi})
    return out
def _vpayload(mid, b, prompt):   # la petición para ese modelo, desde su esquema
    sch = _vcat()[mid]; p = sch['p']; en = lambda k: ((p.get(k) or {}).get('enum') or []); out = {'prompt': prompt}
    R = b.get('refs') or []; imgs = [r for r in by_kind(R, 'image')]; vids = by_kind(R, 'video'); auds = by_kind(R, 'audio')
    first = b.get('image') if isinstance(b.get('image'), dict) else (imgs[0] if imgs else None)
    if 'image' in p and first: out['image'] = resolve_ws(first)
    if isinstance(b.get('end'), dict) and 'image' in out:   # v259: imagen final
        for k in ('last_image', 'end_image'):
            if k in p: out[k] = resolve_ws(b['end']); break
    if 'images' in p and imgs: out['images'] = [resolve_ws(r) for r in imgs][:9]
    if 'reference_images' in p and imgs and 'image' not in out: out['reference_images'] = [resolve_ws(r) for r in imgs][:9]
    if 'reference_videos' in p and vids: out['reference_videos'] = [resolve_ws(r) for r in vids][:3]
    if 'reference_audios' in p and auds: out['reference_audios'] = [resolve_ws(r) for r in auds][:3]
    if 'duration' in p:
        d0 = int(b.get('duration') or 5); E = en('duration')
        if E: out['duration'] = min(E, key=lambda x: abs(int(x) - d0))
        else: lo, hi = (p['duration'].get('minimum') or 1), (p['duration'].get('maximum') or 60); out['duration'] = max(int(lo), min(int(hi), d0))
    if 'resolution' in p:
        E = en('resolution'); r0 = str(b.get('resolution') or '')
        out['resolution'] = r0 if (not E or r0 in E) else (p['resolution'].get('default') or (E[len(E) // 2] if E else r0))
    if 'aspect_ratio' in p and not ('image' in out and 'aspect_ratio' not in sch['req'] and b.get('aspect') in (None, '', 'auto')):
        E = en('aspect_ratio'); a0 = b.get('aspect') or '9:16'; out['aspect_ratio'] = a0 if (not E or a0 in E) else (p['aspect_ratio'].get('default') or E[0])
    for k in ('generate_audio', 'sound', 'audio'):
        if (p.get(k) or {}).get('type') == 'boolean': out[k] = bool(b.get('audio')) and not ('end_image' in out and mid.startswith('kwaivgi/kling-v2.6'))   # Kling 2.6: imagen final y sonido no van juntos
    if not mid.startswith('bytedance/'):   # Seedance entiende @Image1; los demás no
        if 'image' in out and not any(k in out for k in ('images', 'reference_images')): out['prompt'] = re.sub(r'@Image1\b', 'the input image', out['prompt'])
        elif mid.startswith('x-ai/'): out['prompt'] = re.sub(r'@Image(\d+)', lambda m_: '<IMAGE_%d>' % (int(m_.group(1)) - 1), out['prompt'])
        elif mid.startswith('alibaba/'): out['prompt'] = re.sub(r'@(Image|Video|Audio)(\d+)', lambda m_: '%s %s' % (m_.group(1), m_.group(2)), out['prompt'])
        else: out['prompt'] = re.sub(r'@(Image|Video|Audio)(\d+)', lambda m_: '%s %s' % (m_.group(1).lower(), m_.group(2)), out['prompt'])
    falta = [k for k in sch['req'] if k not in out]
    if falta: raise RuntimeError('a este modelo le falta: ' + ', '.join(falta) + (' (necesita una imagen de partida)' if 'image' in falta else ''))
    return out

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
    if not k: raise RuntimeError('BytePlus no está conectado: conéctalo en «Mis APIs»' if SERVIDOR else 'falta ARK_API_KEY en ~/.claude/byteplus.env')
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
    if not k: raise RuntimeError('Higgsfield no está conectado: conéctalo en «Mis APIs»')
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
        if isinstance(v, dict): v.setdefault('owner', uid()); v.setdefault('email', getattr(_ctx, 'email', '') or ''); v.setdefault('interno', bool(getattr(_ctx, 'interno', False)))
        if isinstance(v, dict) and getattr(_ctx, 'prest', None) and 'prest' not in v: v['prest'] = [list(p) for p in _ctx.prest]   # v219: creada con el personaje de otro creador → al terminar aparece también en su cuenta   # de quién es (None en local): solo su cuenta lo ve, lo cancela y lo recoge
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
ARIA_MIAS = ('complementos', 'fichas', 'accTipos')   # lo que un miembro puede añadirle a SU Aria (solo en su cuenta); lo demás de Aria es fijo
def _fusion(S, capa):   # lo que ve la cuenta = copia entera del común + su capa encima
    C = json.loads(S['txt'])
    if not aria_fija():
        P = _aria_perfil()
        if isinstance(P, dict): C['perfil'] = P
    elif isinstance(capa.get('aria'), dict):   # miembro: sus complementos y fichas de Aria, encima de la Aria de todos (lo suyo primero)
        A = capa['aria']; P = C.setdefault('perfil', {})
        for k in ARIA_MIAS:
            mias = [x for x in A.get(k) or [] if isinstance(x, dict)]; fuera = set(((A.get('ocultos') or {}).get(k)) or [])
            if not mias and not fuera: continue
            comun = [x for x in P.get(k) or [] if isinstance(x, dict)]; ids = {x.get('id') for x in comun}; cambio = {x.get('id'): x for x in mias if x.get('id') in ids}
            P[k] = [x for x in mias if x.get('id') not in ids] + [cambio.get(x.get('id'), x) for x in comun if x.get('id') not in fuera]
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
    if not aria_fija():   # Aria de equipo: el perfil va a la cuenta de Aria (si quien guarda es ella misma, a su propia capa)
        P0 = _aria_perfil(); P = C.get('perfil') or {}; cambia = P != (P0 if P0 is not None else S['perfil'])
        if uid() == ARIA_UID:
            if P0 is not None or cambia: capa['perfil'] = P
        elif cambia: _aria_perfil_guarda(P)
    else:   # miembro: de Aria solo se guarda lo suyo (lo que añade, lo que cambia y lo que quita de complementos y fichas); lo demás no se toca
        Sp = S['perfil'] or {}; Pc = C.get('perfil') or {}; A = {'ocultos': {}}
        for k in ARIA_MIAS:
            base = {x.get('id'): x for x in Sp.get(k) or [] if isinstance(x, dict)}; L = [x for x in Pc.get(k) or [] if isinstance(x, dict)]
            A[k] = [x for x in L if x.get('id') not in base or x != base[x.get('id')]]; A['ocultos'][k] = sorted(set(base) - {x.get('id') for x in L})
        if any(A[k] for k in ARIA_MIAS) or any(A['ocultos'].values()): capa['aria'] = A
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
        ('ark', 'BytePlus', 'ARK_API_KEY', 'byteplus.env', 'vídeo con Seedance'),
        ('claude', 'Claude (Anthropic)', 'ANTHROPIC_API_KEY', 'anthropic.env', 'escribir mundos, historias y prompts de los Workflows'),
        ('mg', 'Magnific', 'FREEPIK_API_KEY', 'freepik.env', 'mejorar y escalar imágenes (API de Freepik)'),   # v324
        ('el', 'ElevenLabs', 'ELEVENLABS_API_KEY', 'elevenlabs.env', 'voces y audio'),
        ('oai', 'ChatGPT (OpenAI)', 'OPENAI_API_KEY', 'openai.env', 'prompts e imágenes GPT'))
def _oai_ok(k):   # v324: comprueba una clave de OpenAI listando modelos (no gasta)
    rq = urllib.request.Request('https://api.openai.com/v1/models', headers={'Authorization': 'Bearer ' + k, 'User-Agent': UA}); urllib.request.urlopen(rq, timeout=30).read(); return True
def _el_ok(k):   # v324: ElevenLabs, listando sus modelos (no gasta)
    rq = urllib.request.Request('https://api.elevenlabs.io/v1/models', headers={'xi-api-key': k, 'User-Agent': UA}); urllib.request.urlopen(rq, timeout=30).read(); return True
def _mg_ok(k):   # v324: Magnific va por la API de Freepik; se comprueba con una búsqueda (no gasta)
    rq = urllib.request.Request('https://api.freepik.com/v1/resources?limit=1', headers={'x-freepik-api-key': k, 'Accept': 'application/json', 'User-Agent': UA}); urllib.request.urlopen(rq, timeout=30).read(); return True
def _claude_ok(k):   # comprueba una clave de Anthropic listando sus modelos (no genera ni cobra nada)
    rq = urllib.request.Request('https://api.anthropic.com/v1/models?limit=1', headers={'x-api-key': k, 'anthropic-version': '2023-06-01', 'User-Agent': UA})
    urllib.request.urlopen(rq, timeout=30).read(); return True
def _hf_ok(k):   # comprueba una clave de Higgsfield pidiendo un presupuesto (no genera ni cobra nada)
    M = MODELS['qwen']; rq = urllib.request.Request(BASE + '/estimate/' + M['ep'], data=json.dumps(M['body']('a photo', ['https://example.com/a.jpg'], '3:4', 'std')).encode(), method='POST')
    rq.add_header('Authorization', 'Key ' + k); rq.add_header('Content-Type', 'application/json'); rq.add_header('User-Agent', UA); urllib.request.urlopen(rq, timeout=30).read()
def _ark_ok(k):   # comprueba una clave de BytePlus pidiendo su lista de trabajos (no genera ni cobra nada)
    rq = urllib.request.Request(load_ark()[1] + '/api/v3/contents/generations/tasks?page_size=1'); rq.add_header('Authorization', 'Bearer ' + k); rq.add_header('User-Agent', UA)
    urllib.request.urlopen(rq, timeout=30).read()
def _de_quien(k):   # ¿de qué proveedor es esta clave? Se prueba con cada uno; None si ninguno la acepta
    if not re.fullmatch(r'[\x21-\x7e]{16,400}', k): return None
    duda = False
    for aid, prueba in ((('claude', _claude_ok),) if k.startswith('sk-ant-') else (('el', _el_ok),) if k.startswith('sk_') else (('oai', _oai_ok),) if k.startswith('sk-') else (('mg', _mg_ok),) if k.startswith('FPSX') else (('hf', _hf_ok),) if ':' in k else (('ws', _ws_saldo), ('ark', _ark_ok), ('el', _el_ok), ('mg', _mg_ok))):   # v324: + ElevenLabs, ChatGPT y Magnific
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
# ---- CARPETAS de Mis creaciones (v218): <casa>/carpetas.json → [{id, nombre, t, items: [ruta de la creación…]}]. Son referencias: nada se copia ni se borra.
CARP_MAX, CARP_ITEMS = 60, 3000
def _carp_fp(): return os.path.join(_dir(), 'carpetas.json')
def _carp_lee():
    try: L = json.load(open(_carp_fp(), encoding='utf-8')).get('carpetas') or []
    except Exception: L = []
    return [{'id': c['id'], 'nombre': str(c.get('nombre') or 'Carpeta')[:40], 't': c.get('t') or 0, 'items': [x for x in c.get('items') or [] if isinstance(x, str)], **({'colab': c['colab']} if isinstance(c.get('colab'), str) else {}), **({'padre': c['padre']} if isinstance(c.get('padre'), str) else {}), **({'pub': True} if c.get('pub') else {}), **({'pubauto': True} if c.get('pubauto') else {}), **({'comp': [x for x in c['comp'] if isinstance(x, str)]} if isinstance(c.get('comp'), list) and c['comp'] else {})} for c in L if isinstance(c, dict) and isinstance(c.get('id'), str)]
def _carp_haz(b):   # crear · renombrar · borrar · meter · sacar → la lista entera, ya guardada
    ac = str(b.get('accion') or ''); nombre = ' '.join(str(b.get('nombre') or '').split())[:40]
    files = list(dict.fromkeys(x.split('?')[0] for x in (b.get('files') or []) if isinstance(x, str)))[:CARP_ITEMS]
    aviso = None
    with _cerrojo('carp'):
        L = _carp_lee(); c = next((x for x in L if x['id'] == b.get('id')), None)
        if ac == 'publicar_una':   # v237: creaciones sueltas → carpeta automática «🌐 Publicadas» (se crea la primera vez)
            c = next((x for x in L if x.get('pubauto')), None)
            if not c: c = {'id': 'k' + hashlib.sha1(os.urandom(12)).hexdigest()[:12], 'nombre': '🌐 Publicadas', 't': int(time.time()), 'items': [], 'pub': True, 'pubauto': True}; L.append(c)
            c['pub'] = True; ac = 'meter' if b.get('on', True) else 'sacar'
        if ac == 'crear':
            if not nombre: raise ValueError('Ponle un nombre a la carpeta.')
            if any(x['nombre'].lower() == nombre.lower() for x in L): raise ValueError('Ya tienes una carpeta con ese nombre.')
            if len(L) >= CARP_MAX: raise ValueError(f'Has llegado al máximo de {CARP_MAX} carpetas.')
            c = {'id': 'k' + hashlib.sha1(os.urandom(12)).hexdigest()[:12], 'nombre': nombre, 't': int(time.time()), 'items': []}; L.append(c); ac = 'meter'
        elif not c: raise ValueError('Esa carpeta ya no existe.')
        if ac == 'renombrar':
            if not nombre: raise ValueError('Ponle un nombre a la carpeta.')
            if any(x is not c and x['nombre'].lower() == nombre.lower() for x in L): raise ValueError('Ya tienes una carpeta con ese nombre.')
            c['nombre'] = nombre
        elif ac == 'borrar':
            L.remove(c)
            for x in L:
                if x.get('padre') == c['id']: x.pop('padre', None)   # sus subcarpetas no se pierden: suben un nivel
        elif ac == 'publicar':   # v237: la carpeta entera, a la Fototeca/Filmoteca de la comunidad (on: false = retirarla)
            if c.get('colab'): raise ValueError('Lo creado con el personaje de otro creador no se puede publicar.')
            if b.get('on', True): c['pub'] = True
            else: c.pop('pub', None)
        elif ac == 'mover':   # v230: dentro de otra carpeta (un solo nivel) o fuera (padre vacío)
            pa = str(b.get('padre') or '')
            if not pa: c.pop('padre', None)
            else:
                p = next((x for x in L if x['id'] == pa), None)
                if not p or p is c: raise ValueError('Esa carpeta no existe.')
                if p.get('padre'): raise ValueError('Solo se puede un nivel: esa carpeta ya está dentro de otra.')
                if any(x.get('padre') == c['id'] for x in L): raise ValueError('Solo se puede un nivel: esta carpeta ya tiene carpetas dentro.')
                c['padre'] = pa
        elif ac == 'meter':
            ya = set(c['items']); nuevos = [x for x in files if x not in ya and _creacion(x)]   # solo creaciones DE LA CUENTA
            if len(c['items']) + len(nuevos) > CARP_ITEMS: raise ValueError(f'Una carpeta admite hasta {CARP_ITEMS} creaciones.')
            c['items'] = nuevos + c['items']
        elif ac == 'sacar': q = set(files); c['items'] = [x for x in c['items'] if x not in q]
        elif ac == 'compartir':   # v220: con un creador con el que colaboro (on: false = dejar de compartir)
            con = str(b.get('con') or ''); on = bool(b.get('on', True)); yo = _cid()
            if not SERVIDOR or con == yo or (con not in _com_cuentas() and not _demo_cid(con)): raise ValueError('Ese creador no existe.')
            if on and not _com_trato(_com_lee(), yo, con): raise ValueError('Solo puedes compartir carpetas con creadores con los que colaboras.')
            ya = con in (c.get('comp') or []); S = [x for x in c.get('comp') or [] if x != con] + ([con] if on else [])
            if S: c['comp'] = S[:50]
            else: c.pop('comp', None)
            if on != ya: aviso = (yo, con, on, c['nombre'], len(c['items']), c['id'])
        else: raise ValueError('acción desconocida')
        fp = _carp_fp(); tmp = f'{fp}.tmp{threading.get_ident()}'
        json.dump({'carpetas': L}, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1); os.replace(tmp, fp)
    _pub_reset()
    if aviso:   # se lo cuenta en su conversación (fuera del cerrojo de las carpetas)
        try:
            yo, con, on, nom, n, kid_ = aviso
            with _com_l:
                d = _com_lee(); d['msgs'].setdefault(_com_par(yo, con), []).append({'de': yo, 'x': (f'📁 He compartido contigo la carpeta «{nom}» ({n} {"creación" if n == 1 else "creaciones"}).' if on else f'He dejado de compartir la carpeta «{nom}».'), 't': time.time(), 'auto': True, **({'carp': {'cid': yo, 'id': kid_, 'nombre': nom, 'n': n}} if on else {})}); _com_guarda(d)
        except Exception as e: plog('compartir: aviso ✕ ' + str(e))
    return L
# ---- PUBLICADO EN LA COMUNIDAD (v237): lo que hay en carpetas con `pub`. Nunca lo oculto, lo NSFW ni lo creado con el personaje de otro. Lo denunciado desaparece.
_PUB = {'t': 0, 'L': []}; _PUB_L = threading.Lock()
def _pub_reset():
    with _PUB_L: _PUB['t'] = 0
def _pub_cuenta(u):   # {ruta: ficha} de lo que una cuenta tiene publicado
    base = os.path.join(DATOS, 'usuarios', u); out = {}
    try: L = json.load(open(os.path.join(base, 'carpetas.json'), encoding='utf-8')).get('carpetas') or []
    except Exception: return out
    for c in L:
        if not (isinstance(c, dict) and c.get('pub')) or c.get('colab'): continue
        for r in c.get('items') or []:
            P = r.split('/') if isinstance(r, str) else []
            if r in out or len(P) != 3 or P[0] != 'assets' or P[1] not in ('live', 'video') or P[2].startswith('.'): continue
            full = os.path.join(base, *P)
            if not (_dentro(base, full) and os.path.isfile(full)): continue
            try: m = json.load(open(full + '.json'))
            except Exception: continue   # v260: sin su ficha no se sabe si es oculta, NSFW o de colaboración → no se publica
            if m.get('hidden') or m.get('nsfw') or m.get('colab') or m.get('importada') or _es_nsfw(m.get('prompt')): continue
            out[r] = m
    return out
_EFX_L = threading.Lock()   # v300: ✨ Efectos — los vídeos de la Filmoteca que el equipo elige como efecto ({id: {nombre, t}})
def _efx_f(): return os.path.join(DATOS or ROOT, 'efectos.json')
def _efx_lee():
    try: E = json.load(open(_efx_f(), encoding='utf-8'))
    except Exception: E = {}
    return E if isinstance(E, dict) else {}
def _efx_guarda(E):
    tmp = _efx_f() + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as o: json.dump(E, o, ensure_ascii=False)
    os.replace(tmp, _efx_f())
def _vistos_fp(): return os.path.join(_dir(), 'vistos.json')   # v304: las ventanas de aviso que esta cuenta ya ha visto (no se repiten)
def _vistos():
    try: L = json.load(open(_vistos_fp(), encoding='utf-8'))
    except Exception: L = []
    return [x for x in L if isinstance(x, str)][:300] if isinstance(L, list) else []
def _clave_claude_casa():   # v320: la clave de Claude que paga la casa (la misma del montador)
    k = os.environ.get('ARIA_CLAUDE_CASA') or ''
    if not k and SERVIDOR and re.fullmatch(r'[0-9a-f-]{36}', ARIA_UID or ''):
        with como(ARIA_UID): k = _env('ANTHROPIC_API_KEY', 'anthropic.env')
    return k
def _encuadre_ia(src):   # v320 → (panel, cara) en fracciones (x0, y0, x1, y1) de la imagen, o None. Claude Haiku mira la ficha y dice dónde está la vista de frente
    k = _clave_claude_casa()
    if not k: return None
    try:
        from PIL import Image
        import io
        im = Image.open(src).convert('RGB'); im.thumbnail((1024, 1024)); bb = io.BytesIO(); im.save(bb, 'JPEG', quality=85)
        body = {'model': MONTAR_LLM, 'max_tokens': 300, 'messages': [{'role': 'user', 'content': [
            {'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/jpeg', 'data': base64.b64encode(bb.getvalue()).decode()}},
            {'type': 'text', 'text': 'This image is a character reference sheet (several panels of the same person) or a single photo. Find the panel where the person faces the camera (front view, head and shoulders if possible). Answer ONLY with JSON: {"panel":[x0,y0,x1,y1],"face":[x0,y0,x1,y1]} where panel is that whole panel and face is her face from the top of the hair to the chin, as fractions 0-1 of the full image width and height.'}]}]}
        rq = urllib.request.Request('https://api.anthropic.com/v1/messages', data=json.dumps(body).encode(), method='POST', headers={'x-api-key': k, 'anthropic-version': '2023-06-01', 'content-type': 'application/json', 'User-Agent': UA})
        r = json.loads(urllib.request.urlopen(rq, timeout=60).read()); t = ''.join(b.get('text', '') for b in r.get('content') or [] if b.get('type') == 'text')
        j = json.loads(t[t.index('{'):t.rindex('}') + 1]); P = [float(x) for x in j['panel']]; C_ = [float(x) for x in j['face']]
        u = r.get('usage') or {}; _montar_gasto((u.get('input_tokens', 0) * 1 + u.get('output_tokens', 0) * 5) / 1e6, 'encuadre')
        ok = lambda B: len(B) == 4 and 0 <= B[0] < B[2] <= 1.001 and 0 <= B[1] < B[3] <= 1.001
        return (P, C_) if ok(P) and ok(C_) else None
    except Exception as e: plog(f'encuadre IA ✕ {type(e).__name__}: {str(e)[:120]}'); return None
def _avatar_centrado(base, fp, grande=False):   # v312: la foto del influencer en la Comunidad, con la cara centrada. Se hace UNA vez; si su dueña cambia la foto después, se queda la suya
    if not SERVIDOR: return None
    mk = os.path.join(base, '.foto_ia.json' if grande else '.avatar_ia.json'); out = os.path.join(base, '.foto_ia.jpg' if grande else '.avatar_ia.jpg')   # v313: también la grande (3:4) · v320: encuadradas con IA (ficheros nuevos: se rehacen todas)
    try: mt = os.path.getmtime(fp)
    except OSError: return None
    try: j = json.load(open(mk, encoding='utf-8'))
    except Exception: j = None
    if isinstance(j, dict):
        if abs(float(j.get('mt') or 0) - mt) > 1: return None   # la ha cambiado después: la suya
        return out if j.get('ok') and os.path.isfile(out) else None
    ok = False
    try:
        import cv2
        from PIL import Image
        cc = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        for n in (('ficha360.jpg', 'ficha.jpg', 'importada.jpg') if grande else ('vista_frente.jpg', 'ficha360.jpg', 'ficha.jpg', os.path.basename(fp))):   # primero su vista de frente; si no, la ficha; si no, la propia foto (la grande, siempre de la ficha entera)
            src = os.path.join(base, n)
            if not os.path.isfile(src): continue
            img = cv2.imread(src)
            if img is None: continue
            g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY); H0, W0 = g.shape; px0, py0 = 0, 0
            ia = _encuadre_ia(src) if n != 'vista_frente.jpg' else None   # v320: la IA dice cuál es el panel de frente; todo se recorta DENTRO de ese panel
            if ia:
                (a0, b0, a1, b1), (c0, d0, c1, d1) = ia; px0, py0 = int(a0 * W0), int(b0 * H0); g = g[py0:int(b1 * H0), px0:int(a1 * W0)]; img = img[py0:int(b1 * H0), px0:int(a1 * W0)]
            H, W = g.shape
            fs = cc.detectMultiScale(g, scaleFactor=1.1, minNeighbors=5, minSize=(max(30, W // 12), max(30, W // 12)))
            if len(fs): x, y, w, h = max(fs, key=lambda f_: int(f_[2]) * int(f_[3]) * 1000 - (int(f_[0]) + int(f_[1])))   # la cara más grande (a igualdad, la de arriba a la izquierda: la de frente)
            elif ia: x, y, w, h = int(c0 * W0) - px0, int(d0 * H0) - py0, int((c1 - c0) * W0), int((d1 - d0) * H0)   # sin cara detectada: la que dice la IA
            else: continue
            if grande:   # de la cabeza a los hombros, en vertical 3:4, con la cara en el tercio de arriba
                y0 = int(max(0, y - h * 0.45)); al = int(min(max(w, h) * 2.6 * 4 / 3, H - y0)); an = int(min(al * 3 / 4, W)); al = int(an * 4 / 3); cx = x + w / 2   # si no cabe por abajo, se encoge (no sube: no coge el panel de arriba)
                x0 = int(min(max(0, cx - an / 2), W - an))
                im = Image.open(src).convert('RGB').crop((px0 + x0, py0 + y0, px0 + x0 + an, py0 + y0 + al)); im.thumbnail((640, 860)); im.save(out, quality=88); ok = True; break
            lado = int(min(max(w, h) * 1.7, W, H)); cx = x + w / 2; cy = y + h * 0.55
            x0 = int(min(max(0, cx - lado / 2), W - lado)); y0 = int(min(max(0, cy - lado / 2), H - lado))
            im = Image.open(src).convert('RGB').crop((px0 + x0, py0 + y0, px0 + x0 + lado, py0 + y0 + lado)); im.thumbnail((400, 400)); im.save(out, quality=88); ok = True; break
    except Exception as e: plog(f'avatar centrado ✕ {type(e).__name__}: {str(e)[:120]}')
    try:
        with open(mk, 'w', encoding='utf-8') as o: json.dump({'mt': mt, 'ok': ok}, o)
    except Exception: pass
    return out if ok else None
def _pub_lista():   # todo lo publicado por todas las cuentas, lo más nuevo primero (caché de 20 s; se vacía con cada cambio)
    if not SERVIDOR or not DATOS: return []
    with _PUB_L:
        if time.time() - _PUB['t'] < 20: return _PUB['L']
    d = _com_lee(); den = d.get('den') if isinstance(d.get('den'), dict) else {}; out = []
    for cid, u in _com_cuentas().items():
        pjs_ = None
        for r, m in _pub_cuenta(u).items():
            P = r.split('/'); k = f'{cid}/{P[1]}/{P[2]}'
            if k in den and _den_oculta(den[k]): continue
            e = m.get('escena') if isinstance(m.get('escena'), dict) else {}
            ch_ = [str(x) for x in (m.get('chars') if isinstance(m.get('chars'), list) else ([m['char']] if m.get('char') else []))]   # v303 · v317: los influencers que salen (para sus circulitos)
            if pjs_ is None: pjs_ = {p['pid']: p['nombre'] for p in _com_personajes(u)}
            pids_ = [x for x in ch_ if x == 'aria' or x in pjs_] or [k_ for k_, n_ in pjs_.items() if n_ and n_ in str(m.get('charName') or '')][:2]
            pid_ = pids_[0] if pids_ else ''
            out.append({'f': 'assets/publica/' + k, 'kind': 'video' if P[1] == 'video' else 'image', 'cid': cid, 'pid': pid_, 'pids': pids_[:2], 'comp': {k_: str(v_)[:80] for k_, v_ in (m.get('compIds') or {}).items() if k_ in ('vestidor', 'hair') and v_} if isinstance(m.get('compIds'), dict) else {}, 'hairCol': m.get('hairCol') if isinstance(m.get('hairCol'), dict) else None, 'subida': bool(m.get('subida')), 'alias': str(d['alias'].get(cid) or '')[:40], 'prompt': m['prompt'][:8000] if isinstance(m.get('prompt'), str) else '',
                        'escena': {q: e[q][:4000] for q in ('d', 'r', 'f') if isinstance(e.get(q), str)}, 'modelo': str(m.get('model') or '')[:60], 'personaje': str(m.get('charName') or '')[:80], 't': m.get('t') or 0, 'ancho': m.get('width'), 'alto': m.get('height')})
    out.sort(key=lambda x: -(x['t'] or 0))
    with _PUB_L: _PUB['t'] = time.time(); _PUB['L'] = out
    return out
def _publica(rel):   # 'assets/publica/<cid>/<live|video>/<fichero>' → el fichero real, solo si está publicado ahora mismo
    L = rel.split('/')
    if not SERVIDOR or len(L) != 5 or L[3] not in ('live', 'video') or L[4].startswith('.') or not any(x['f'] == rel for x in _pub_lista()): return None
    u = _com_cuentas().get(L[2])
    if not u: return None
    base = os.path.join(DATOS, 'usuarios', u); full = os.path.join(base, 'assets', L[3], L[4])
    return full if _dentro(base, full) and os.path.isfile(full) else None
def _pub_importa(b):   # traigo a MIS creaciones imágenes publicadas en la comunidad (copia, con su prompt) → cuántas
    n = 0; ld = live_dir(); yo = _cid(); P = {x['f']: x for x in _pub_lista()}
    for rel in [x.split('?')[0] for x in (b.get('files') or []) if isinstance(x, str)][:200]:
        x = P.get(rel); src = _publica(rel) if x else None
        if not src or x['kind'] != 'image' or x['cid'] == yo: continue
        ext = os.path.splitext(src)[1].lower(); fn = 'importada_pub-' + hashlib.sha1(rel.encode()).hexdigest()[:8] + ext; dst = os.path.join(ld, fn)
        if ext not in ('.png', '.jpg', '.jpeg', '.webp') or os.path.exists(dst): continue
        _peso.pop(uid(), None)
        if lleno(): raise ValueError(LLENO)
        shutil.copyfile(src, dst)
        meta = {'file': 'assets/live/' + fn, 'kind': 'image', 'item': 'importada', 'name': 'De ' + (x['alias'] or 'la comunidad'), 'usd': 0, 't': time.time(), 'importada': {'de': x['cid'], 'alias': x['alias'], 'comunidad': True}}
        if x.get('prompt'): meta['prompt'] = x['prompt']
        if x.get('escena'): meta['escena'] = x['escena']
        if x.get('modelo'): meta['model'] = x['modelo']
        json.dump(meta, open(dst + '.json', 'w'), ensure_ascii=False, indent=1); n += 1
    _peso.pop(uid(), None); return n
# ---- CARPETAS COMPARTIDAS (v220). La fuente de verdad es la lista `comp` de la carpeta en la casa de su dueña; además tiene que seguir habiendo colaboración.
def _com_trato(d, a, b): return any(x.get('estado') == 'aceptada' and {x.get('de'), x.get('para')} == {a, b} for x in d['sol'])   # ¿colaboran (en cualquier sentido)?
def _comp_carpetas(cid, d=None):   # las carpetas de la cuenta cid compartidas CONMIGO → (uid de su dueña, [carpetas]); nada si no colaboramos
    if not SERVIDOR or not DATOS or not isinstance(cid, str) or not re.fullmatch(r'c[0-9a-f]{14}', cid): return None, []
    yo = _cid()
    if cid == yo: return None, []
    tr = _com_trato(d if d is not None else _com_lee(), yo, cid); u = _com_cuentas().get(cid)
    if not u: return None, []
    try: L = json.load(open(os.path.join(DATOS, 'usuarios', u, 'carpetas.json'), encoding='utf-8')).get('carpetas') or []
    except Exception: return None, []
    return u, [c for c in L if isinstance(c, dict) and isinstance(c.get('id'), str) and isinstance(c.get('comp'), list) and yo in c['comp'] and (tr or c.get('colab') == yo)]   # lo creado con MI personaje lo sigo viendo aunque ya no colaboremos
def _comp_items(u, c):   # lo que hay de verdad en una carpeta compartida, como rutas 'assets/compartida/…' (lo que fue a la papelera no sale)
    base = os.path.join(DATOS, 'usuarios', u); out = []
    for r in c.get('items') or []:
        L = r.split('/') if isinstance(r, str) else []
        if len(L) != 3 or L[0] != 'assets' or L[1] not in ('live', 'video') or L[2].startswith('.'): continue
        full = os.path.join(base, *L)
        if _dentro(base, full) and os.path.isfile(full): out.append(L)
    return out
def _comp_ficha(u, L):   # de la ficha de una creación compartida, lo que viaja con ella: su prompt y su descripción de escena (nunca rutas ni referencias)
    try: m = json.load(open(os.path.join(DATOS, 'usuarios', u, *L) + '.json'))
    except Exception: return {}
    o = {}; e = m.get('escena') if isinstance(m.get('escena'), dict) else {}
    if isinstance(m.get('prompt'), str) and m['prompt'].strip(): o['prompt'] = m['prompt'][:8000]
    e = {k: e[k][:4000] for k in ('d', 'r', 'f') if isinstance(e.get(k), str) and e[k].strip()}
    if e: o['escena'] = e
    if m.get('model'): o['modelo'] = str(m['model'])[:60]   # v242: los mismos datos que se ven en una creación propia
    if m.get('charName'): o['personaje'] = str(m['charName'])[:80]
    for k_, q_ in (('t', 't'), ('ancho', 'width'), ('alto', 'height')):
        if isinstance(m.get(q_), (int, float)): o[k_] = m[q_]
    return o
def _compartida(rel):   # 'assets/compartida/<cid>/<carpeta>/<live|video>/<fichero>' → el fichero real en la casa de su dueña, o None. ÚNICA puerta a lo de otra cuenta.
    L = rel.split('/')
    if len(L) != 6 or L[4] not in ('live', 'video') or L[5].startswith('.'): return None
    u, cs = _comp_carpetas(L[2]); c = next((x for x in cs if x['id'] == L[3]), None)
    if not c or f'assets/{L[4]}/{L[5]}' not in (c.get('items') or []): return None
    base = os.path.join(DATOS, 'usuarios', u); full = os.path.join(base, 'assets', L[4], L[5])
    return full if _dentro(base, full) and os.path.isfile(full) else None
def _comp_lista(d, yo):   # para la Comunidad: las carpetas que me comparten los creadores con los que colaboro
    out = []
    for cid in sorted({(x.get('de') if x.get('para') == yo else x.get('para')) for x in d['sol'] if x.get('estado') in ('aceptada', 'terminada') and yo in (x.get('de'), x.get('para'))} - {yo, None}):
        u, cs = _comp_carpetas(cid, d)
        for c in cs: out.append({'cid': cid, 'id': c['id'], 'nombre': ('🤝 Creado con tus personajes' if c.get('colab') == yo else str(c.get('nombre') or 'Carpeta'))[:40], 'n': len(_comp_items(u, c)), 'alias': str(d['alias'].get(cid) or '')[:40], 'conjunta': c.get('colab') == yo})
    return out
def _mini_de(full):   # la miniatura (560 px) de una imagen de assets/live de cualquier cuenta; se hace la primera vez. Si no se puede, la propia imagen
    if os.sep + 'live' + os.sep not in full: return full
    mini = os.path.join(os.path.dirname(full), '.mini', os.path.basename(full) + '.jpg')
    if not os.path.isfile(mini):
        try:
            from PIL import Image
            os.makedirs(os.path.dirname(mini), exist_ok=True); im = Image.open(full).convert('RGB'); im.thumbnail((560, 560)); im.save(mini + '.tmp', 'JPEG', quality=80); os.replace(mini + '.tmp', mini)
        except Exception: return full
    return mini
def _favs_fp(): return os.path.join(_dir(), 'favs.json')
def _favs_lee():   # v239: mis favoritos de la Fototeca y la Filmoteca → {'biblio': [ids], 'videoteca': [ids]}
    try: d = json.load(open(_favs_fp(), encoding='utf-8'))
    except Exception: d = {}
    return {k: [x for x in (d.get(k) or []) if isinstance(x, str)][:5000] for k in ('biblio', 'videoteca')}
def _carp_auto(u, base, otro, alias, rel, comp=None):   # mete «rel» en la carpeta automática «🤝 <otro creador>» de la cuenta u (se crea la primera vez). No depende de la cuenta en curso.
    with _cerrojos_l: lk = _cerrojos.setdefault((u, 'carp'), threading.Lock())
    with lk:
        fp = os.path.join(base, 'carpetas.json')
        try: L = [c for c in json.load(open(fp, encoding='utf-8')).get('carpetas') or [] if isinstance(c, dict) and isinstance(c.get('id'), str)]
        except Exception: L = []
        c = next((x for x in L if x.get('colab') == otro), None)
        if not c: c = {'id': 'k' + hashlib.sha1(os.urandom(12)).hexdigest()[:12], 'nombre': ('🤝 ' + (alias or 'Colaboración'))[:40], 't': int(time.time()), 'items': [], 'colab': otro}; L.append(c)
        if rel not in (c.get('items') or []): c['items'] = [rel] + [x for x in c.get('items') or [] if isinstance(x, str)][:CARP_ITEMS - 1]
        if comp and comp not in (c.get('comp') or []): c['comp'] = [x for x in c.get('comp') or [] if isinstance(x, str)] + [comp]   # la dueña del personaje la ve
        tmp = f'{fp}.tmp{threading.get_ident()}'; json.dump({'carpetas': L}, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1); os.replace(tmp, fp)
def _conjunta(j, rel, rid):   # v223: la imagen creada con el personaje de otro creador se queda en la cuenta de quien la crea (su cuota) y entra en su carpeta «🤝 <dueña>», que la dueña del personaje VE (compartida con ella). Sin copias.
    pares = [p for p in (j.get('prest') or []) if isinstance(p, (list, tuple)) and len(p) == 2]
    if not SERVIDOR or not DATOS or not pares: return
    try:
        yo_u = uid(); d = _com_lee(); CU = _com_cuentas(); src = os.path.join(casa(), rel)
        if not os.path.isfile(src): return
        try: mia = json.load(open(src + '.json'))
        except Exception: mia = {}
        con = []; hechas = set()
        for cid, pid in pares:
            u = CU.get(cid)
            if not u or u == yo_u or not _pid_ok(pid): continue
            nombre = pid
            try: pj = json.load(open(os.path.join(DATOS, 'usuarios', u, 'assets', 'personajes', pid, 'personaje.json'), encoding='utf-8')); nombre = str(pj.get('nombre') or pj.get('name') or pid)[:60]
            except Exception: pass
            su_alias = str(d['alias'].get(cid) or '')[:40]; con.append({'con': cid, 'alias': su_alias, 'pid': pid, 'personaje': nombre})
            if cid not in hechas: hechas.add(cid); _carp_auto(yo_u, casa(), cid, su_alias, rel, comp=cid)
        if con:
            mia['colab'] = dict(con[0], mia=True, todos=con); json.dump(mia, open(src + '.json', 'w'), ensure_ascii=False, indent=1)
            plog(f'conjunta → carpeta compartida con {len(hechas)} cuenta(s) · {rel}')
    except Exception as e: plog('conjunta ✕ ' + str(e))
def _comp_importa(b):   # v223: traigo a MIS creaciones (copia, cuenta en mi espacio) imágenes de una carpeta que me comparten → cuántas
    cid, kid = str(b.get('cid') or ''), str(b.get('id') or ''); u, cs = _comp_carpetas(cid); c = next((x for x in cs if x['id'] == kid), None)
    if not c: raise ValueError('Esa carpeta ya no está compartida contigo.')
    quiero = {x.split('?')[0].split('/')[-1] for x in (b.get('files') or []) if isinstance(x, str)}; alias = str(_com_lee()['alias'].get(cid) or '')[:40]; n = 0; ld = live_dir()
    for L in _comp_items(u, c):
        if L[1] != 'live' or (quiero and L[2] not in quiero): continue
        ext = os.path.splitext(L[2])[1].lower(); fn = 'importada_colab-' + hashlib.sha1(f'{cid}|{L[2]}'.encode()).hexdigest()[:8] + ext; dst = os.path.join(ld, fn)
        if ext not in ('.png', '.jpg', '.jpeg', '.webp') or os.path.exists(dst): continue
        if n % 10 == 0:
            _peso.pop(uid(), None)
            if lleno(): raise ValueError(LLENO)
        src = os.path.join(DATOS, 'usuarios', u, *L); shutil.copyfile(src, dst)
        try: m0 = json.load(open(src + '.json'))
        except Exception: m0 = {}
        meta = dict(_comp_ficha(u, L), file='assets/live/' + fn, kind='image', item='importada', name='De ' + (alias or 'otro creador'), usd=0, t=time.time(), importada={'de': cid, 'alias': alias})
        for k in ('model', 'model_key', 'width', 'height'):
            if m0.get(k) is not None: meta[k] = m0[k]
        json.dump(meta, open(dst + '.json', 'w'), ensure_ascii=False, indent=1); n += 1
    _peso.pop(uid(), None); return n
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
    if status == 'completed' and not j.get('file') and j.get('kind') == 'audio' and time.time() - j.get('dl', 0) > 240:   # v291: 🎙️ el audio, a assets/audio
        aurl = (st.get('video') or {}).get('url')
        if aurl:
            j['dl'] = time.time(); data = urllib.request.urlopen(urllib.request.Request(aurl, headers={'User-Agent': UA}), timeout=300).read()
            ext = os.path.splitext(aurl.split('?')[0])[1].lower(); ext = ext if ext in ('.mp3', '.wav', '.ogg', '.opus', '.m4a', '.aac') else '.mp3'
            fn = f"{_safe_item(j['item'])}__{rid[:8]}{ext}"; open(os.path.join(audio_dir(), fn), 'wb').write(data); j['file'] = 'assets/audio/' + fn; write_meta(j, j['file'], rid, st); _job_done(rid)
    if status == 'completed' and not j.get('file') and j.get('kind') not in ('video', 'audio') and time.time() - j.get('dl', 0) > 240:
        imgs = st.get('images') or st.get('output', {}).get('images') or []
        if imgs:
            j['dl'] = time.time()
            url = imgs[0]['url'] if isinstance(imgs[0], dict) else imgs[0]
            data = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=300).read()
            ext = '.png' if url.lower().split('?')[0].endswith('.png') else '.jpg'
            fn = f"{_safe_item(j['item'])}_{j.get('model', 'qwen')}-{rid[:8]}{ext}"; open(os.path.join(live_dir(), fn), 'wb').write(data); j['file'] = 'assets/live/' + fn; write_meta(j, j['file'], rid, st); _conjunta(j, j['file'], rid); _job_done(rid)
            if (j.get('meta') or {}).get('estilo'):
                try: j['estilo'] = _add_estilo(j, os.path.join(live_dir(), fn))
                except Exception as e: plog('estilo nuevo ✕ ' + str(e))
            if (j.get('meta') or {}).get('nf'):
                try: j['nf_item'] = _nf_autosave(j)
                except Exception as e: plog('ficha nueva ✕ ' + str(e))
            if (j.get('meta') or {}).get('prenda'):
                try: j['prenda'] = add_prenda(j, os.path.join(live_dir(), fn)); j['file'] = j['prenda']['ficha']
                except Exception as e: plog('prenda ✕ ' + str(e))
    if status in ('failed', 'nsfw', 'canceled') and not j.get('failed') and status != 'canceled': fallida_apunta(j.get('meta'), st.get('error') or st.get('detail') or status, (j.get('meta') or {}).get('model') or j.get('model'))   # v270
    if status in ('failed', 'nsfw', 'canceled'): j['failed'] = True; _job_done(rid); out['error'] = st.get('error') or st.get('detail') or status; plog(f"{rid[:8]} {status} · {out['error']} · {j.get('item')}")
    if j.get('casa'):
        try: out['casa'] = casa_info()
        except Exception: pass
    out['file'] = j.get('file'); out['kind'] = j.get('kind', 'image'); out['prenda'] = j.get('prenda'); out['nf'] = j.get('nf_item'); out['estilo'] = j.get('estilo'); out['raw'] = {k: st.get(k) for k in ('status', 'request_id')}
    return 200, out
# ---- 🤝 COMUNIDAD (v195): el directorio de influencers IA de todas las cuentas, las solicitudes de colaboración y los mensajes.
#      Privacidad: de una cuenta solo se enseña su identificador opaco (`cid`, no reversible), el nombre de creador que ella ponga y sus personajes PÚBLICOS
#      (nombre, usuario, edad, descripción, Instagram, nicho y su avatar). Nunca el correo ni sus creaciones. Sus fichas solo las usa el servidor al generar, y solo para quien tiene una colaboración aceptada (v202).
COM_F = os.path.join(DATOS or RAIZ, 'comunidad.json'); _com_l = threading.Lock(); _COM_N = {}
def _cid(u='__yo__'):
    if u == '__yo__': u = uid()
    sal = SECRETO if isinstance(SECRETO, bytes) else str(SECRETO or '').encode()
    return 'c' + hashlib.sha256((str(u or 'local') + '|comunidad|').encode() + sal).hexdigest()[:14]
def _com_lee():
    try: d = json.load(open(COM_F, encoding='utf-8'))
    except Exception: d = {}
    if not isinstance(d, dict): d = {}
    for k, v in (('sol', []), ('msgs', {}), ('alias', {}), ('visto', {}), ('foto', {}), ('sig', {}), ('borr', {})):
        if not isinstance(d.get(k), type(v)): d[k] = v
    if any('demo-' in k for k in d['msgs']) or any(isinstance(x, dict) and 'demo-' in f"{x.get('de')}|{x.get('para')}" for x in d['sol']):   # v304: lo que quede de la demo, fuera
        d['msgs'] = {k: v for k, v in d['msgs'].items() if 'demo-' not in k}; d['sol'] = [x for x in d['sol'] if isinstance(x, dict) and 'demo-' not in f"{x.get('de')}|{x.get('para')}"]
    for k_ in list(d['sig']):
        if isinstance(d['sig'][k_], list) and any(str(x).startswith('demo-') for x in d['sig'][k_]): d['sig'][k_] = [x for x in d['sig'][k_] if not str(x).startswith('demo-')]
    ahora = time.time()
    for x in d['sol']:   # v223: un permiso con plazo se apaga solo al vencer (se ve terminado en cuanto se lee; se guarda con el siguiente cambio)
        if isinstance(x, dict) and x.get('estado') == 'aceptada' and isinstance(x.get('hasta'), (int, float)) and x['hasta'] < ahora: x['estado'] = 'terminada'; x['caducada'] = True; x['t2'] = x['hasta']
    return d
def _demo_cid(cid): return isinstance(cid, str) and cid.startswith('demo-') and not aria_fija() and any(c['cid'] == cid for c in COM_DEMO)   # un creador de ejemplo, y quien pregunta es del equipo
def _com_pjs(CU, cid): return [dict(p) for c in COM_DEMO if c['cid'] == cid for p in c['personajes']] if str(cid).startswith('demo-') else _com_personajes(CU[cid])
DEMO_HOLA = '👋 Soy un creador de ejemplo: solo lo ve el equipo. He aceptado tu solicitud automáticamente para que pruebes cómo funciona (mensajes, plazos, compartir carpetas). Con mis personajes no se puede generar.'
PLAZOS = {1: '24 horas', 7: '7 días', 30: '30 días'}
def _plazo(v):
    try: v = int(v)
    except Exception: return None
    return v if v in PLAZOS else None
def _sol_nsfw(x):   # ¿modo NSFW encendido en esta colaboración? Solo si lo han activado LOS DOS y no ha vencido su plazo
    return bool(x.get('estado') == 'aceptada' and x.get('nsfw_de') and x.get('nsfw_para') and not (isinstance(x.get('nsfw_hasta'), (int, float)) and x['nsfw_hasta'] < time.time()))
def _com_guarda(d):
    with open(COM_F + '.tmp', 'w', encoding='utf-8') as fh: json.dump(d, fh, ensure_ascii=False)
    os.replace(COM_F + '.tmp', COM_F)
def _com_cuentas():   # cid → uid de cada cuenta con carpeta (en local, una sola)
    if not SERVIDOR: return {_cid(None): None}
    try: L = os.listdir(os.path.join(DATOS, 'usuarios'))
    except OSError: L = []
    return {_cid(x): x for x in L if _UUID.fullmatch(x)}
def _com_personajes(u, con_ocultos=False):   # los personajes de una cuenta tal como se ven en la comunidad (los ocultos, solo para su dueña)
    out = []
    try:
        with como(u): pd = pers_dir()
        for d0 in sorted(os.listdir(pd)):
            fp = os.path.join(pd, d0, 'personaje.json')
            if d0.startswith(('_', '.')) or not os.path.isfile(fp): continue
            try: p = json.load(open(fp, encoding='utf-8'))
            except Exception: continue
            if not p.get('ficha360') or (p.get('privado') and not con_ocultos): continue   # solo personajes con su ficha; los ocultos no salen
            ig = p.get('ig') if isinstance(p.get('ig'), dict) else {}; url = str(ig.get('url') or '')
            try: t0 = min(os.path.getmtime(os.path.join(pd, d0, x)) for x in os.listdir(os.path.join(pd, d0))[:300])   # desde cuándo existe (su fichero más antiguo)
            except Exception: t0 = 0
            out.append({'pid': d0, 'nombre': str(p.get('nombre') or d0)[:60], 'usuario': str(p.get('usuario') or '')[:60], 'edad': p.get('edad') if isinstance(p.get('edad'), (int, float)) else None,
                        'bio': str(p.get('bio') or '')[:600], 'ig': url[:200] if url.startswith('https://') else '', 'nicho': [str(x)[:30] for x in p.get('nicho')[:6]] if isinstance(p.get('nicho'), list) else [],
                        'avatar': bool(p.get('avatar') or p.get('foto')), 'oculto': bool(p.get('privado')), 'abierto': bool(p.get('abierto')) and not p.get('privado'), 'igseg': str(p.get('igSeguidores') or ig.get('followers') or '')[:12], 'nuevo': bool(t0 and time.time() - t0 < 3 * 86400), 't': int(t0), 'orden': p.get('orden') if isinstance(p.get('orden'), int) else 999})
    except Exception as e: plog('comunidad: personajes ✕ ' + str(e))
    out.sort(key=lambda x: x['orden']); return out
COM_DEMO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'comunidad_demo')   # caras de los creadores de demo (recortes de rejillas ya generadas)
COM_DEMO = [   # creadores de DEMO para ver cómo queda la Comunidad con gente: solo los ve el equipo (nunca los miembros)
    {'cid': 'demo-nube', 'alias': 'Estudio Nube', 'demo': True, 'personajes': [
        {'pid': 'lia-moreno', 'nombre': 'Lía Moreno', 'usuario': '@lia.moreno', 'edad': 23, 'bio': 'Moda sostenible y cafés con encanto en Madrid.', 'avatar': True},
        {'pid': 'carla-vidal', 'nombre': 'Carla Vidal', 'usuario': '@carlavidal', 'edad': 24, 'bio': 'Viajes baratos y fotos de móvil sin filtro.', 'avatar': True}]},
    {'cid': 'demo-nora', 'alias': 'Nora Creative', 'demo': True, 'personajes': [
        {'pid': 'nora-blanc', 'nombre': 'Nora Blanc', 'usuario': '@nora.blanc', 'edad': 25, 'bio': 'Fitness, recetas rápidas y mucho humor.', 'avatar': True},
        {'pid': 'ruby-sanz', 'nombre': 'Ruby Sanz', 'usuario': '@rubysanz', 'edad': 22, 'bio': 'Pelirroja, música indie y vintage.', 'avatar': True}]},
    {'cid': 'demo-vera', 'alias': 'Vera Lys Studio', 'demo': True, 'personajes': [
        {'pid': 'vera-lys', 'nombre': 'Vera Lys', 'usuario': '@veralys', 'edad': 26, 'bio': 'Belleza y skincare, rutinas reales.', 'avatar': True}]},
    {'cid': 'demo-brisa', 'alias': 'Studio Brisa', 'demo': True, 'personajes': [{'pid': p, 'nombre': n, 'usuario': u, 'edad': e, 'bio': b, 'avatar': True} for p, n, u, e, b in (
        ('sofia-lumen', 'Sofía Lumen', '@sofialumen', 24, 'Comida callejera y viajes por Asia.'), ('paula-ortiz', 'Paula Ortiz', '@paulaortiz', 23, 'Selfies de espejo y outfits del día.'), ('iris-gomez', 'Iris Gómez', '@irisgomez', 22, 'Humor y caras raras.'))]},
    {'cid': 'demo-marta', 'alias': 'Marta & Co', 'demo': True, 'personajes': [{'pid': p, 'nombre': n, 'usuario': u, 'edad': e, 'bio': b, 'avatar': True} for p, n, u, e, b in (
        ('marta-sol', 'Marta Sol', '@martasol', 27, 'Ejecutiva de día, cine de noche.'), ('elena-brisa', 'Elena Brisa', '@elenabrisa', 21, 'Fantasía, cosplay y bosques.'), ('noa-ferrer', 'Noa Ferrer', '@noaferrer', 25, 'Nieve, montaña y aventura.'))]},
    {'cid': 'demo-noa', 'alias': 'Noa Creates', 'demo': True, 'personajes': [{'pid': p, 'nombre': n, 'usuario': u, 'edad': e, 'bio': b, 'avatar': True} for p, n, u, e, b in (
        ('julia-mar', 'Julia Mar', '@juliamar', 24, 'Skincare honesto.'), ('dani-rivas', 'Dani Rivas', '@danirivas', 26, 'Tecnología y noches de ordenador.'), ('alba-nieto', 'Alba Nieto', '@albanieto', 23, 'Moda minimal en blanco y negro.'),
        ('clara-voss', 'Clara Voss', '@claravoss', 25, 'Gaming y ciencia ficción.'), ('ines-palma', 'Inés Palma', '@inespalma', 22, 'Coches clásicos y road trips.'), ('zoe-marin', 'Zoe Marín', '@zoemarin', 24, 'Vida real, sin filtros.'))]}]
COM_DEMO = []   # v304: fuera la demo (Max, 6 oct): ni creadores ni mensajes de ejemplo
ARIA_CID = 'caria'   # Aria en la comunidad: no es una cuenta, es el personaje de muestra. Le manda a cada cuenta una solicitud de ejemplo y contesta con un mensaje fijo
ARIA_HOLA = '¡Hola! Soy Aria 💕 Ya puedes crear conmigo cuando quieras: elígeme en Crear imagen junto a tu personaje y salimos juntas.'
ARIA_RESP = '¡Genial! Conmigo puedes crear cuando quieras: elígeme en Crear imagen junto a tu personaje. 💕'
ARIA_RESP_V = '¡Genial! Conmigo puedes crear cuando quieras: elígeme en Crear imagen junto a tu personaje. (Soy el personaje de muestra: este chat es un ejemplo de cómo hablarás con otros creadores.)'
def _com_aria(d, yo):   # v304: Aria da permiso a cada cuenta para crear con ella (sin aceptar nada) y sigue a sus personajes; lo nuevo, con aviso en Mensajes → True si ha cambiado algo
    t = time.time(); cambio = False; M = d['msgs'].setdefault(_com_par(yo, ARIA_CID), [])
    s_ = next((x for x in d['sol'] if x.get('de') == ARIA_CID and x.get('para') == yo), None)
    if not s_: d['sol'].append({'id': 's' + hashlib.sha1(os.urandom(12)).hexdigest()[:12], 'de': ARIA_CID, 'para': yo, 'pid': 'aria', 'msg': ARIA_HOLA, 'estado': 'aceptada', 't': t, 't2': t, 'demo': True}); M.append({'de': ARIA_CID, 'x': ARIA_HOLA, 't': t}); cambio = True
    elif s_.get('estado') == 'pendiente': s_['estado'] = 'aceptada'; s_['t2'] = t; M.append({'de': ARIA_CID, 'x': ARIA_HOLA, 't': t}); cambio = True
    CU = {}
    try: CU = _com_cuentas(); pjs = _com_personajes(CU[yo]) if yo in CU else []
    except Exception: pjs = []
    L = d['sig'].setdefault(ARIA_CID, []); ac_ = next((c_ for c_, uu_ in (CU or {}).items() if uu_ == ARIA_UID), None) if 'CU' in dir() else None   # v320: y la cuenta de Aria (la de Max) también
    if ac_ and ac_ != yo:
        L2 = d['sig'].setdefault(ac_, [])
        for p in pjs:
            k2 = f"{yo}:{p.get('pid')}"
            if p.get('pid') and k2 not in L2: L2.append(k2); cambio = True
    for p in pjs:
        k = f"{yo}:{p.get('pid')}"
        if not p.get('pid') or k in L: continue
        L.append(k); cambio = True
        if p.get('nuevo'): M.append({'de': ARIA_CID, 'x': f"⭐ ¡Me encanta {p.get('nombre') or 'tu personaje'}! Ya le sigo. Cuando quieras, cread algo juntas.", 't': t + 0.5})   # solo los recién creados avisan; los de antes, en silencio
    if cambio: del M[:-500]; d['sig'][ARIA_CID] = L[-5000:]
    return cambio
def _com_par(a, b): return '|'.join(sorted([a, b]))
# ---- el «préstamo» (v202): con una colaboración ACEPTADA, quien la pidió puede crear con el personaje del otro creador.
#      Su ficha y su cuerpo solo los lee el servidor al generar; al navegador solo le llega su avatar. Nunca con NSFW. Un personaje oculto no se presta.
PREST_Q = {'ficha.jpg': ('ficha360',), 'cuerpo.jpg': ('cuerpo',), 'foto.jpg': ('avatar', 'foto', 'ficha360')}
PREST_K = ('genero', 'complexion', 'altura', 'pecho', 'cadera', 'ojos', 'ojosHex', 'peloNombre', 'peloHex', 'peloColor')   # lo que hace falta para describirlo en el prompt
def _com_permiso(d, yo, cid, pid):   # ¿la cuenta «yo» puede crear con el personaje pid de la cuenta cid? Solo si ELLA lo pidió (a ese personaje o a la cuenta entera) y se lo aceptaron
    return any(x.get('estado') == 'aceptada' and x.get('de') == yo and x.get('para') == cid and x.get('pid') in (None, pid) for x in d['sol'])
def _prestado_p(cid, pid, d=None):   # → (uid de su dueña, su personaje.json), o (None, None): sin permiso, oculto, sin ficha o inexistente
    if not SERVIDOR or not DATOS or not isinstance(cid, str) or not re.fullmatch(r'c[0-9a-f]{14}', cid) or not _pid_ok(pid): return None, None
    yo = _cid()
    if cid == yo or not _com_permiso(d if d is not None else _com_lee(), yo, cid, pid): return None, None
    u = _com_cuentas().get(cid)
    if not u: return None, None
    try: p = json.load(open(os.path.join(DATOS, 'usuarios', u, 'assets', 'personajes', pid, 'personaje.json'), encoding='utf-8'))
    except Exception: return None, None
    if not isinstance(p, dict) or not p.get('ficha360') or p.get('privado'): return None, None
    return u, p
def _prestado(rel):   # 'assets/prestamo/<cid>/<pid>/<ficha|cuerpo|foto>.jpg' → el fichero real en la casa de su dueña, o None
    L = rel.split('/')
    if len(L) != 5 or L[4] not in PREST_Q: return None
    u, p = _prestado_p(L[2], L[3])
    if not p: return None
    base = os.path.join(DATOS, 'usuarios', u)
    for k in PREST_Q[L[4]]:
        r = _rel_ok(p.get(k) or '')
        if not r or not r.startswith('assets/personajes/' + L[3] + '/'): continue
        full = os.path.join(base, *r.split('/'))
        if _dentro(base, full) and os.path.isfile(full): return full
    return None
def _prest_lista(d, yo):   # los personajes de otros creadores con los que esta cuenta puede crear, con lo justo para usarlos en Crear imagen
    out = []; CU = _com_cuentas()
    for x in d['sol']:
        cid = x.get('para')
        if x.get('estado') != 'aceptada' or x.get('de') != yo or cid not in CU: continue
        for q in _com_personajes(CU[cid]):
            if x.get('pid') not in (None, q['pid']) or any(o['cid'] == cid and o['pid'] == q['pid'] for o in out): continue
            u, p = _prestado_p(cid, q['pid'], d)
            if not p: continue
            pe = p.get('peinado') if isinstance(p.get('peinado'), dict) else {}
            o = {'cid': cid, 'pid': q['pid'], 'nombre': q['nombre'], 'nsfw': any(_sol_nsfw(z) for z in d['sol'] if z.get('de') == yo and z.get('para') == cid and z.get('pid') in (None, q['pid'])), 'creador': str(d['alias'].get(cid) or '')[:40], 'cuerpo': bool(p.get('cuerpo')), 'peinado': {'desc': str(pe.get('desc') or '')[:300], 'name': str(pe.get('name') or '')[:80]}}
            for k in PREST_K:
                v = p.get(k)
                if isinstance(v, str): o[k] = v[:80]
                elif isinstance(v, (int, float)) and not isinstance(v, bool): o[k] = v
            out.append(o)
    return out
def _prest_apunta(pares):   # se ha lanzado una imagen con el personaje de otro creador: se cuenta en su colaboración (su dueña ve cuántas)
    try:
        yo = _cid()
        with _com_l:
            d = _com_lee(); toca = False
            for cid, pid in pares:
                x = next((x for x in d['sol'] if x.get('estado') == 'aceptada' and x.get('de') == yo and x.get('para') == cid and x.get('pid') in (None, pid)), None)
                if x: x['usos'] = int(x.get('usos') or 0) + 1; x['uso_t'] = time.time(); toca = True
            if toca: _com_guarda(d)
    except Exception as e: plog('préstamo: contar ✕ ' + str(e))
def _com_tope(que, n):   # freno por cuenta y hora (solicitudes, mensajes)
    k = (uid() or 'local', que); ahora = time.time(); L = _COM_N.setdefault(k, []); L[:] = [t for t in L if ahora - t < 3600]
    if len(L) >= n: return False
    L.append(ahora); return True
def _pj_guarda(fp, P):   # v260: personaje.json de una vez (fichero temporal + cambio de nombre): nunca queda a medias
    tmp = f'{fp}.tmp{threading.get_ident()}'; json.dump(P, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1); os.replace(tmp, fp)
UPSCALE_EP = 'wavespeed-ai/image-upscaler'; UPSCALE_USD = 0.01   # v266: ampliar a 4K
_fall_l = threading.Lock()
def _fall_lee():   # las que no se han podido generar (últimas 24 h), en la casa de la cuenta
    try: L = json.load(open(os.path.join(casa(), 'fallidas.json'), encoding='utf-8'))
    except Exception: L = []
    ahora = time.time(); return [x for x in (L if isinstance(L, list) else []) if isinstance(x, dict) and ahora - float(x.get('t') or 0) < 86400]
def _fall_guarda(L):
    fp = os.path.join(casa(), 'fallidas.json'); os.makedirs(os.path.dirname(fp), exist_ok=True)
    with open(fp + '.tmp', 'w', encoding='utf-8') as f: json.dump(L[:30], f, ensure_ascii=False)
    os.replace(fp + '.tmp', fp)
def fallida_apunta(meta, err, modelo=''):   # v270: una generación que no ha salido → 24 h en gris en la galería de la cuenta, en todos sus dispositivos
    try:
        if re.search(r'saldo|cr[eé]dito|balance|insufficient|top.?up|no llega|conect|NSFW con Aria|no entra en el saldo|espacio|lleno|hacen falta', str(err), re.I): return   # sin saldo no es un fallo de la imagen
        m = meta if isinstance(meta, dict) else {}
        o = {'id': 'f' + hashlib.sha1(f'{time.time()}{err}'.encode()).hexdigest()[:10], 't': time.time() * 1000, 'tab': str(m.get('tab') or 'crear')[:20], 'name': str(m.get('name') or 'Creación')[:80], 'err': str(err)[:400], 'modelo': str(modelo or m.get('model') or '')[:60], 'thumb': ''}
        with _fall_l: L = _fall_lee(); L.insert(0, o); _fall_guarda(L)
    except Exception as e: plog('fallida ✕ ' + str(e)[:120])
_TOPES = {}; _TOPES_L = threading.Lock()
def _tope(que, n, seg):   # v260: como mucho n veces cada seg segundos por cuenta (en memoria)
    k = (uid(), que); ahora = time.time()
    with _TOPES_L:
        L = [t for t in _TOPES.get(k, []) if ahora - t < seg]
        if len(L) >= n: _TOPES[k] = L; return False
        L.append(ahora); _TOPES[k] = L
        if len(_TOPES) > 20000: _TOPES.clear()
    return True
def _den_oculta(v):   # v260: una creación denunciada se retira cuando la denuncian 3 cuentas distintas o alguien del equipo (las de antes, retiradas)
    if not isinstance(v, dict): return True
    if v.get('retirada') or isinstance(v.get('por'), str): return True
    return len(v.get('por') or []) >= 3
def _com_avisos(d, yo):
    n = sum(1 for x in d['sol'] if x.get('para') == yo and x.get('estado') == 'pendiente')
    try:
        if SERVIDOR and not aria_fija(): n += sum(1 for v in (d.get('den') or {}).values() if not (isinstance(v, dict) and v.get('vista')))   # v260: al equipo le llegan las denuncias por revisar
        if SERVIDOR and not aria_fija():
            sb = _bolsa_saldo()
            if sb is not None and sb < float(_bolsa_lee().get('aviso') or 0): n += 1   # v269: la bolsa del saldo regalo, por debajo del aviso
    except Exception: pass
    for k, M in d['msgs'].items():
        if yo in k.split('|'):
            otra = [c for c in k.split('|') if c != yo]; visto = (d['visto'].get(yo) or {}).get(otra[0] if otra else '', 0)
            n += sum(1 for m in M if m.get('de') != yo and m.get('t', 0) > visto)
    return n
ARIA_VOZ = os.environ.get('ARIA_VOZ_ELEVEN') or 'yM93hbw8Qtvdma2wCnJG'   # v291: la voz de Aria en ElevenLabs («Ivanna – Young & Casual»)
AUDIO_M = {   # clave → (endpoint de WaveSpeed, nombre, precio base $, modo)
    'el4': ('elevenlabs/eleven-v4', 'ElevenLabs v4', 0.08, 'voz'), 'el3': ('elevenlabs/eleven-v3', 'ElevenLabs v3 · más expresiva', 0.2, 'voz'),
    'seedtts': ('bytedance/seed-speech-tts-2.0', 'Seed Speech 2.0', 0.06, 'voz'), 'seedaudio': ('bytedance/seed-audio-1.0', 'Seed Audio 1.0', 0.3, 'ambiente'),
    'vchange': ('elevenlabs/voice-changer', 'ElevenLabs · cambiar voz', 0.004, 'cambiar'), 'mirelo': ('mirelo-ai/sfx-1.6/text-to-audio', 'Mirelo SFX 1.6 · con ambiente', 0.01, 'efecto'),
    'sonilo': ('sonilo/v1/text-to-sfx', 'Sonilo · el más barato', 0.002, 'efecto'), 'sfx': ('kwaivgi/kling-text-to-audio', 'Kling · efecto de sonido', 0.035, 'efecto')}   # v295: ElevenLabs SFX no está en WaveSpeed
def _audio_info():   # modelos, precios del catálogo y voces disponibles
    M = _vcat(); r = []
    for k, (ep, nom, usd, modo) in AUDIO_M.items():
        m = M.get(ep) or {}; r.append({'k': k, 'nombre': nom, 'modo': modo, 'usd': m.get('usd') if m.get('usd') is not None else usd, 'ok': bool(m) or not M})
    vel = (((M.get('elevenlabs/voice-changer') or {}).get('p') or {}).get('voice_id') or {}).get('enum') or []
    vse = (((M.get('bytedance/seed-speech-tts-2.0') or {}).get('p') or {}).get('voice') or {}).get('enum') or []
    return {'modelos': r, 'voces_el': vel, 'voces_seed': vse, 'aria_voz': ARIA_VOZ}
VOZ_ARIA = {'eleven': ARIA_VOZ, 'eleven_nombre': 'Ivanna (la voz de Aria)', 'preset': 'Alicia', 'seed': 'vivi_mixed_en_zh_ja_es_id',
            'desc': 'Chica joven española de 25 años, voz cálida, cercana y casual; habla rápido cuando se emociona y se ríe con facilidad.'}
def _voces_fp(): return os.path.join(casa(), 'voces.json')   # v292: la voz de cada personaje (en la casa de la cuenta, fuera de assets)
def _voces():
    try: d = json.load(open(_voces_fp(), encoding='utf-8'))
    except Exception: d = {}
    d = d if isinstance(d, dict) else {}
    d['aria'] = dict(VOZ_ARIA, **(d.get('aria') or {})); return d
def _audio_usd(k, texto='', seg=0):   # v293: lo que cuesta de verdad (tarifas de WaveSpeed, 6 oct 2026)
    n = len(texto or '')
    if k == 'el4': return round(0.08 * n / 1000, 4)
    if k == 'el3': return round(0.20 * n / 1000, 4)
    if k == 'seedtts': return 0.03 * max(1, math.ceil(n / 1000))
    if k == 'vchange': return round(0.004 * min(300, max(1, math.ceil(seg or 1))), 4)
    return AUDIO_M.get(k, ('', '', 0.0, ''))[2]
MUESTRA_TXT = ('Hola, ¿qué tal? Así suena mi voz. Te cuento un poco: me encanta grabar vídeos, probar cosas nuevas y contarte todo lo que descubro. '
               'Puedo hablar tranquila, emocionarme cuando algo me flipa o bajar la voz para contarte un secreto. ¿Te gusta cómo sueno?')   # v296: más larga, para entender bien la voz
_MU = {'en_marcha': False, 'hechas': 0, 'faltan': 0, 'error': ''}
def _mu_dir(modelo): d = os.path.join(DATOS or ROOT, 'biblioteca', 'assets', 'muestras', modelo) if SERVIDOR else os.path.join(ROOT, 'assets', 'muestras', modelo); os.makedirs(d, exist_ok=True); return d
def _muestras():   # {'el': {voz: ruta}, 'seed': {...}}
    out = {}
    for m in ('el', 'seed'):
        try: out[m] = {os.path.splitext(n)[0]: f'assets/muestras/{m}/{n}' for n in os.listdir(_mu_dir(m)) if n.endswith('.mp3')}
        except OSError: out[m] = {}
    return out
def _mu_genera(ctx_n, modelo, voces):   # en segundo plano, una a una, con la clave de quien lo pidió
    with como(*ctx_n):
        _ctx.ws_modo = 'propia'
        for v in voces:
            try:
                ep, payload = ('elevenlabs/eleven-v4', {'text': MUESTRA_TXT, 'voice_id': v, 'stability': .5, 'similarity': .75}) if modelo == 'el' else ('bytedance/seed-speech-tts-2.0', {'text': MUESTRA_TXT, 'voice': v})
                rid = (ws('POST', '/api/v3/' + ep, payload).get('data') or {}).get('id')
                for _ in range(60):
                    time.sleep(2); w = ws('GET', f'/api/v3/predictions/{rid}/result').get('data') or {}
                    if w.get('status') == 'completed' and w.get('outputs'):
                        data = urllib.request.urlopen(urllib.request.Request(w['outputs'][0], headers={'User-Agent': UA}), timeout=120).read()
                        fp = os.path.join(_mu_dir(modelo), re.sub(r'[^A-Za-z0-9_-]', '_', v) + '.mp3'); open(fp + '.tmp', 'wb').write(data); os.replace(fp + '.tmp', fp); _MU['hechas'] += 1; break
                    if w.get('status') == 'failed': _MU['error'] = str(w.get('error'))[:160]; break
            except Exception as e: _MU['error'] = str(e)[:160]
            _MU['faltan'] = max(0, _MU['faltan'] - 1)
    _MU['en_marcha'] = False; plog(f'🎙 muestras de voz {modelo}: {_MU["hechas"]} hechas' + (f' · último error: {_MU["error"]}' if _MU['error'] else ''))
PROMPTER_LLM = os.environ.get('ARIA_PROMPTER_LLM') or 'claude-sonnet-5-5'   # v297: el asistente de prompts (rápido y barato)
PROMPTER_SIS = {'audio': """Eres un experto en escribir prompts para Seed Audio 1.0 (ByteDance), un modelo que genera voz humana MUY natural y el ambiente sonoro a la vez.
Escribes UN prompt listo para pegar, con esta estructura exacta:
1) Una línea de cabecera: «<N>-sec <tipo de escena> scene, hyper-natural, casual, <idioma/acento en inglés>, organic acoustic environment.»
2) [AESTHETIC] con 4 viñetas «• Texture:», «• Environment:», «• Voice (Woman|Man):» (en español: edad, acento, tono, cero teatralidad) y «• Palette:» (sonidos del sitio).
3) [EXECUTION] con la secuencia: [AMBI] ambiente inicial -> [DIAL] Woman|Man (tono, idioma): "frase" -> [EVENT] respiración/pausa/risa... y la última frase termina en -> [TRANS] cómo se apaga.
4) [ETIQUETA: idioma y acento, una sola voz, sin narrador, sin música, duración exacta N.0s]
Reglas: las frases del diálogo, en el idioma que pida la persona (por defecto español de España) y tal cual si te las da; suena a persona real grabándose con el móvil, nunca a locutor; nada de música salvo que la pidan; la duración cuadra con lo que se dice (unas 2,5 palabras por segundo).
Responde SOLO con un JSON: {"prompt": "…", "nota": "una frase en español explicando qué has hecho"}"""}
def _prompter(tipo, pedido, ctx_txt=''):   # v297: el asistente de prompts, con la clave de Claude de la cuenta
    k = _env('ANTHROPIC_API_KEY', 'anthropic.env')
    if not k: raise RuntimeError('Falta tu clave de Claude en «Mis APIs».')
    body = {'model': PROMPTER_LLM, 'max_tokens': 2500, 'system': PROMPTER_SIS[tipo], 'messages': [{'role': 'user', 'content': (ctx_txt + '\n\n' if ctx_txt else '') + 'Lo que quiero: ' + pedido}]}
    rq = urllib.request.Request('https://api.anthropic.com/v1/messages', data=json.dumps(body).encode(), method='POST', headers={'x-api-key': k, 'anthropic-version': '2023-06-01', 'content-type': 'application/json', 'User-Agent': UA})
    try: r = json.loads(urllib.request.urlopen(rq, timeout=120).read())
    except urllib.error.HTTPError as e: raise RuntimeError(f'Claude respondió {e.code}: ' + e.read().decode('utf-8', 'replace')[:160])
    t = ''.join(b.get('text', '') for b in r.get('content') or [] if b.get('type') == 'text')
    try: j = json.loads(t[t.index('{'):t.rindex('}') + 1])
    except Exception: j = {'prompt': t.strip(), 'nota': ''}
    u = r.get('usage') or {}; j['usd'] = round((u.get('input_tokens', 0) * 3 + u.get('output_tokens', 0) * 15) / 1e6, 4); return j
MONTAR_LLM = os.environ.get('ARIA_MONTAR_LLM') or 'claude-haiku-4-5-20251001'   # v307: junta la idea del usuario con lo elegido en los presets (el modelo más barato de Claude)
MONTAR_TOPE = float(os.environ.get('ARIA_CLAUDE_TOPE') or 3)   # dólares al día, como mucho, que paga la casa por esto (luego, la clave de cada cuenta o se junta sin Claude)
MONTAR_SIS = """Eres el montador de prompts de ARIA STUDIO, una web española para crear imágenes con IA de un personaje (una influencer virtual).
Recibes dos cosas:
1) LA IDEA del usuario, con sus palabras (puede ser informal, corta o con faltas).
2) LO ELEGIDO: un prompt técnico que la web ha montado con lo que el usuario ha elegido (personaje, prenda, peinado, expresión, estilo, lugar, referencias @Image1, @Image2…).
Devuelves UN solo prompt final, EN ESPAÑOL, natural y claro, listo para un generador de imágenes:
- La idea del usuario manda en la escena, la acción, la pose, el ambiente, la luz y el encuadre. No inventes nada que la contradiga.
- El LUGAR y el FONDO los decide la idea: si LO ELEGIDO pide fondo de estudio, fondo liso (blanco o gris) o «plain backdrop» y la idea describe un sitio (un bar, una playa, una calle…), quita ese fondo y pon el sitio de la idea, con su luz. Si lo elegido pide plano entero para que se vea la ropa, mantenlo salvo que la idea pida otro plano.
- Las etiquetas se escriben SIEMPRE así, en inglés y pegadas: @Image1, @Image2… (nunca «@Imagen1», «imagen 1» ni «@image_1»).
- Conserva TODO lo técnico de lo elegido: cada etiqueta @ImageN EXACTAMENTE igual (mismo número, mismo formato), la identidad (misma cara, mismos rasgos), la prenda, el peinado, la expresión, el estilo y las restricciones (una sola foto, no un collage ni una hoja de personaje, sin texto ni logos…).
- Si chocan (por ejemplo, la idea habla de otra ropa y hay una prenda elegida), para lo elegido gana lo elegido, salvo que la idea lo pida claramente.
- Ignora lo que no describe la imagen (saludos, «gracias», comentarios).
- Respeta las palabras y los detalles de la idea: NO los cambies por sinónimos ni los resumas; como mucho corrige faltas, ordénalo y añade detalle que encaje. Si la idea es larga y detallada, tiene que estar entera en el prompt.
- Marca entre ⟦ y ⟧ lo que venga de LO ELEGIDO y entre ⟪ y ⟫ lo que venga de LA IDEA del usuario (aunque lo hayas ordenado o ampliado), para que la web los resalte con colores distintos. Todo el texto va dentro de una de las dos marcas.
- Sin listas, sin títulos, sin comillas alrededor, sin explicaciones: responde SOLO con el prompt. Máximo unos 1500 caracteres."""
MONTAR_SIS_V = """Eres el montador de prompts de VÍDEO de ARIA STUDIO (Seedance), una web española para crear vídeos con IA de un personaje (una influencer virtual).
Recibes dos cosas:
1) LA IDEA del usuario, con sus palabras (puede ser informal, corta o con faltas).
2) LO ELEGIDO: un prompt técnico por secciones (REFERENCIAS, PUNTO DE PARTIDA o INICIO, PERSONAJE, VESTUARIO, PEINADO, COMPLEMENTOS, FORMATO, CÁMARA, ESTILO, LUGAR, ACCIÓN con tiempos, TÉCNICO) montado con lo que el usuario ha elegido.
Devuelves UN solo prompt final, EN ESPAÑOL, con LAS MISMAS secciones y en el mismo orden:
- Mete la idea del usuario donde toca: sobre todo en ACCIÓN (reparte lo que pasa por tramos de tiempo 0:00–0:0X que sumen la duración), y en LUGAR, CÁMARA o ESTILO si la idea lo dice. Si dice frases, van entre comillas en ACCIÓN, en el idioma en que las escriba.
- Las etiquetas se escriben SIEMPRE así, en inglés y pegadas: @Image1, @Image2… (nunca «@Imagen1» ni «imagen 1»).
- Conserva TODO lo técnico: cada etiqueta @ImageN EXACTAMENTE igual, la duración, el formato, la identidad (su cara no cambia nunca), la ropa, el peinado, el punto de partida y el TÉCNICO.
- Si chocan, para lo elegido gana lo elegido, salvo que la idea lo pida claramente.
- Ignora lo que no describe el vídeo (saludos, «gracias», comentarios).
- Respeta las palabras y los detalles de la idea: NO los cambies por sinónimos ni los resumas; como mucho corrige faltas, ordénalo y añade detalle que encaje.
- Marca entre ⟦ y ⟧ lo que venga de LO ELEGIDO (los nombres de sección también) y entre ⟪ y ⟫ lo que venga de LA IDEA del usuario, para que la web los resalte con colores distintos.
- Sin explicaciones: responde SOLO con el prompt. Máximo unos 3500 caracteres."""
_MON_L = threading.Lock()
_ESC = {}   # v322: quién está escribiendo a quién ahora mismo ((de, para) → cuándo), solo en memoria
_VPRE = {}   # v314: precios exactos de WaveSpeed ya preguntados (6 h)
def _montar_gasto(usd=0.0, quien=None):   # lo que lleva hoy la clave de la casa → {'dia', 'usd', 'por': {cuenta: veces}}
    fp = os.path.join(DATOS or ROOT, 'claude_casa.json'); hoy = time.strftime('%Y-%m-%d')
    with _MON_L:
        try: g = json.load(open(fp, encoding='utf-8'))
        except Exception: g = {}
        if not isinstance(g, dict) or g.get('dia') != hoy: g = {'dia': hoy, 'usd': 0.0, 'por': {}}
        if quien:
            g['usd'] = round(float(g.get('usd') or 0) + usd, 5); g['por'][quien] = int(g['por'].get(quien, 0)) + 1
            tmp = fp + '.tmp'; open(tmp, 'w', encoding='utf-8').write(json.dumps(g)); os.replace(tmp, fp)
        return g
def _montar(idea, auto, tipo='imagen'):   # v307 → {'prompt', 'usd', 'casa'}: paga la casa (ARIA_CLAUDE_CASA o la clave de Claude de la cuenta de Aria) hasta el tope del día; si no, la clave de la cuenta
    idea = re.sub(r'@IMG(\d+)', r'@Image\1', idea or '', flags=re.I); auto = re.sub(r'@IMG(\d+)', r'@Image\1', auto or '', flags=re.I)   # v316: en la web se ven como @IMG1
    yo = uid() or 'local'; casa_ = False; g = _montar_gasto(); prov = 'claude'
    k = _env('ANTHROPIC_API_KEY', 'anthropic.env')   # v326: si el miembro tiene su Claude (o su ChatGPT), usa la suya; si no, paga la casa
    if not k:
        k = _env('OPENAI_API_KEY', 'openai.env'); prov = 'oai' if k else 'claude'
    if not k and float(g.get('usd') or 0) < MONTAR_TOPE and int(g['por'].get(yo, 0)) < 300:
        k = os.environ.get('ARIA_CLAUDE_CASA') or ''
        if not k and SERVIDOR and re.fullmatch(r'[0-9a-f-]{36}', ARIA_UID or ''):
            with como(ARIA_UID): k = _env('ANTHROPIC_API_KEY', 'anthropic.env')
        casa_ = bool(k)
    if not k: raise RuntimeError('sin_clave')
    msg = f"LA IDEA DEL USUARIO:\n{idea.strip() or '(no ha escrito nada: monta el prompt solo con lo elegido, en español)'}\n\nLO ELEGIDO:\n{auto.strip()}"
    vid = tipo == 'video'; tags = list(dict.fromkeys(re.findall(r'@Image\d+', auto)))
    def pide(extra=''):
        if prov == 'oai':   # v326: con ChatGPT (la clave del miembro)
            body = {'model': os.environ.get('ARIA_MONTAR_OAI') or 'gpt-5-mini', 'max_completion_tokens': 6000 if vid else 4000, 'messages': [{'role': 'system', 'content': MONTAR_SIS_V if vid else MONTAR_SIS}, {'role': 'user', 'content': msg + extra}]}
            rq = urllib.request.Request('https://api.openai.com/v1/chat/completions', data=json.dumps(body).encode(), method='POST', headers={'Authorization': 'Bearer ' + k, 'content-type': 'application/json', 'User-Agent': UA})
            try: r = json.loads(urllib.request.urlopen(rq, timeout=90).read())
            except urllib.error.HTTPError as e: raise RuntimeError(f'ChatGPT respondió {e.code}: ' + e.read().decode('utf-8', 'replace')[:160])
            t_ = (((r.get('choices') or [{}])[0].get('message') or {}).get('content') or '').strip().strip('"«»').strip()
            t_ = re.sub(r'(?:@\s*|(?<![\w@]))imag(?:e|en)[\s_]*(\d+)\b', r'@Image\1', t_, flags=re.I)
            u = r.get('usage') or {}; return t_, (u.get('prompt_tokens', 0) * 0.25 + u.get('completion_tokens', 0) * 2) / 1e6
        body = {'model': MONTAR_LLM, 'max_tokens': 2600 if vid else 1500, 'system': MONTAR_SIS_V if vid else MONTAR_SIS, 'messages': [{'role': 'user', 'content': msg + extra}]}
        rq = urllib.request.Request('https://api.anthropic.com/v1/messages', data=json.dumps(body).encode(), method='POST', headers={'x-api-key': k, 'anthropic-version': '2023-06-01', 'content-type': 'application/json', 'User-Agent': UA})
        try: r = json.loads(urllib.request.urlopen(rq, timeout=60).read())
        except urllib.error.HTTPError as e: raise RuntimeError(f'Claude respondió {e.code}: ' + e.read().decode('utf-8', 'replace')[:160])
        t_ = ''.join(b.get('text', '') for b in r.get('content') or [] if b.get('type') == 'text').strip().strip('"«»').strip()
        t_ = re.sub(r'(?:@\s*|(?<![\w@]))imag(?:e|en)[\s_]*(\d+)\b', r'@Image\1', t_, flags=re.I)   # v310: @Imagen1, @image_1, «imagen 1»… → @Image1
        u = r.get('usage') or {}; return t_, (u.get('input_tokens', 0) * 1 + u.get('output_tokens', 0) * 5) / 1e6
    t, usd = pide(); falta = [x for x in tags if x not in t]
    if t and falta:   # v310: una segunda vez, recordándole las etiquetas
        t2, u2 = pide(f"\n\nOJO: en el prompt tienen que salir TODAS estas etiquetas, escritas exactamente así: {', '.join(tags)}."); usd += u2; f2 = [x for x in tags if x not in t2]
        if t2 and len(f2) < len(falta): t, falta = t2, f2
    usd = round(usd, 5)
    if casa_: _montar_gasto(usd, yo)
    aviso = ''
    if not t: t = ('⟪' + idea.strip() + '⟫\n\n' if idea.strip() else '') + '⟦' + auto.strip() + '⟧'; aviso = 'Claude no ha respondido: se ha juntado tal cual'
    elif falta:   # solo lo que falta: la frase de lo elegido que nombra esa referencia
        fr = [next((x.strip() for x in re.split(r'(?<=[.!?])\s+|\n', auto) if g_ in x), f'Usa {g_} como referencia.') for g_ in falta]
        t += '\n⟦' + ' '.join(dict.fromkeys(fr)) + '⟧'; aviso = 'faltaba ' + ', '.join(falta)
    if aviso: plog(f'montar · {tipo} · {aviso}')
    t = re.sub(r'@Image(\d+)', r'@IMG\1', t)   # v316
    return {'prompt': t[:6000], 'usd': usd, 'casa': casa_, 'aviso': aviso}
def _audios():   # mis audios, lo último primero
    d = audio_dir(); out = []
    for n in os.listdir(d):
        if n.startswith('.') or n.endswith('.json'): continue
        try: m = json.load(open(os.path.join(d, n + '.json'), encoding='utf-8'))
        except Exception: m = {}
        out.append({'f': 'assets/audio/' + n, 'meta': m, 't': m.get('t') or os.path.getmtime(os.path.join(d, n))})
    out.sort(key=lambda x: -x['t']); return out[:500]
class _Trozo:   # v290: un trozo de un fichero (respuesta 206)
    def __init__(self, f, n): self.f, self.n = f, n
    def read(self, k=-1):
        if self.n <= 0: return b''
        k = self.n if k is None or k < 0 else min(k, self.n); d = self.f.read(k); self.n -= len(d); return d
    def close(self): self.f.close()
_AV = [0.0, None]
def _ign_fp(): return os.path.join(DATOS, 'adm_ignorados.json')
def _ign_lee():   # v292: correos que el equipo ha decidido ignorar (no cuentan en la burbuja)
    try: d = json.load(open(_ign_fp(), encoding='utf-8')); return set(x for x in d if isinstance(x, str))
    except Exception: return set()
def _ign_guarda(S):
    fp = _ign_fp(); open(fp + '.tmp', 'w', encoding='utf-8').write(json.dumps(sorted(S))); os.replace(fp + '.tmp', fp)
def _adm_avisos():   # v290: lo pendiente del equipo (la burbuja roja de ⚙️ Admin): quien entró con Google sin estar en la lista
    if _AV[1] is not None and time.time() - _AV[0] < 60: return _AV[1]
    L = {m['email'] for m in _mi_lista()}
    try: us = (_sb_adm('GET', '/auth/v1/admin/users?page=1&per_page=1000') or {}).get('users') or []
    except Exception: us = []
    ig = _ign_lee(); sin = sum(1 for x in us if isinstance(x, dict) and str(x.get('email') or '').lower() not in L and str(x.get('email') or '').lower() not in ig)
    r = {'sin_acceso': sin, 'total': sin}; _AV[0], _AV[1] = time.time(), r; return r
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
    def send_head(self):   # v290: con «Range», solo el trozo pedido (Safari y el iPhone lo necesitan para reproducir vídeo)
        rg = self.headers.get('Range') if self.command == 'GET' else None
        m = re.fullmatch(r'bytes=(\d*)-(\d*)', (rg or '').strip())
        if not m: return super().send_head()
        path = self.translate_path(self.path)
        if not os.path.isfile(path): return super().send_head()
        try: f = open(path, 'rb')
        except OSError: return super().send_head()
        st = os.fstat(f.fileno()); size = st.st_size; a, b = m.groups()
        if a == '': start = max(0, size - int(b or 0)); end = size - 1
        else: start = int(a); end = min(size - 1, int(b)) if b else size - 1
        if start >= size or start > end:
            f.close(); self.send_response(416); self.send_header('Content-Range', f'bytes */{size}'); self.send_header('Content-Length', '0'); self.end_headers(); return None
        self.send_response(206); self.send_header('Content-Type', self.guess_type(path)); self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Content-Range', f'bytes {start}-{end}/{size}'); self.send_header('Content-Length', str(end - start + 1)); self.send_header('Last-Modified', self.date_time_string(int(st.st_mtime))); self.end_headers()
        f.seek(start); return _Trozo(f, end - start + 1)
    def _subir_biblio(self):   # v290: la Filmoteca ligera al disco del servidor ($DATOS/biblioteca/assets/videoteca/…) — solo con la llave ARIA_ADMIN
        adm = os.environ.get('ARIA_ADMIN') or ''
        if len(adm) < 32 or not hmac.compare_digest((self.headers.get('X-Admin') or '').encode(), adm.encode()): return self._corta(404)
        n = int(self.headers.get('Content-Length') or 0)
        if n > 90_000_000: return self._json(413, {'error': 'demasiado grande'})
        try: body = json.loads(self.rfile.read(n) or b'{}')
        except Exception: return self._json(400, {'error': 'no es JSON'})
        rel = str(body.get('rel') or '')
        if not DATOS or not (re.fullmatch(r'assets/videoteca/[A-Za-z0-9_.-]+', rel) or re.fullmatch(r'assets/muestras/(el|seed)/[A-Za-z0-9_.-]+\.mp3', rel)) or '..' in rel: return self._json(400, {'error': 'ruta no válida'})   # v296: también las muestras de voz
        base = os.path.join(DATOS, 'biblioteca'); full = os.path.join(base, *rel.split('/'))
        if not _dentro(base, full): return self._json(400, {'error': 'ruta no válida'})
        if body.get('ver'): return self._json(200, {'ok': True, 'tam': os.path.getsize(full) if os.path.isfile(full) else 0})
        try: data = base64.b64decode(body.get('data') or '', validate=True)
        except Exception: return self._json(400, {'error': 'datos no válidos'})
        os.makedirs(os.path.dirname(full), exist_ok=True); tmp = f'{full}.tmp{threading.get_ident()}'
        with open(tmp, 'wb') as o: o.write(data)
        os.replace(tmp, full); _biblio_no.pop(rel, None); return self._json(200, {'ok': True, 'tam': len(data)})
    def _corta(self, code, msg='no'):   # respuesta de error (en HEAD, sin cuerpo)
        if self.command != 'HEAD': return self._json(code, {'error': msg})
        self.send_response(code); self.send_header('Content-Length', '0'); self.end_headers()
    def _pasa(self, fn):   # TODA petición (GET, POST y HEAD) entra por aquí: guarda de origen y, en servidor, tope de tamaño + sesión + cuenta del hilo
        self._cc = self._fijo = None; _ctx.lectura = 0; _ctx.prestamo_ok = False; _ctx.prest = None; _ctx.ver_miembro = False
        if not self._guard(): return self._corta(403, 'origen no permitido')
        if not SERVIDOR: return fn()
        if self.command == 'GET' and self.path.startswith('/api/admin/copia'): return self._copia()
        if self.command in ('GET', 'POST') and self.path.startswith('/api/admin/importar'): return self._importar()
        if self.command == 'POST' and self.path == '/api/admin/biblio': return self._subir_biblio()   # v290
        if self.command in ('GET', 'HEAD') and self.path == '/salud': return self._json(200, {'ok': True, 'v': VERSION}) if self.command == 'GET' else self._corta(200)   # el alojamiento pregunta aquí si el servidor está vivo (sin sesión, sin datos)
        if self.command == 'POST':
            try: n = int(self.headers.get('Content-Length') or 0)
            except ValueError: n = -1
            if n < 0 or n > MAX_CUERPO: self.close_connection = True; return self._corta(400 if n < 0 else 413, 'petición no válida' if n < 0 else 'petición demasiado grande')
        try: c = _quien(self)
        except _NoEntra as e: return self._corta(e.code, e.msg)
        try: _visto_pon(c[0], c[1], self.headers.get('User-Agent'))   # v280: para el panel ⚙️ Admin (quién está conectado)
        except Exception: pass
        if self.headers.get('X-Ver-Como') == 'miembro': c = (c[0], c[1], False)   # 👁 «Ver como miembro» (equipo): sin permisos de equipo
        with como(*c):
            _ctx.ver_miembro = self.headers.get('X-Ver-Como') == 'miembro'
            try: return fn()
            except Exception as e:
                plog(f'{self.command} {self.path[:80]} ✕ {type(e).__name__}: {e}')
                try: return self._corta(500, 'error interno')
                except Exception: return
    def _importar(self):   # v251 · volcar creaciones a UNA cuenta (solo con ARIA_ADMIN). GET ?uid= → qué tiene esa cuenta · POST {uid, file, data(b64), meta} → la guarda si no existe
        adm = os.environ.get('ARIA_ADMIN') or ''
        if len(adm) < 32 or not hmac.compare_digest((self.headers.get('X-Admin') or '').encode(), adm.encode()): return self._corta(404)
        if self.command == 'GET':
            u = (urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get('uid') or [''])[0]
            if not _UUID.fullmatch(u) or not os.path.isdir(os.path.join(DATOS, 'usuarios', u)): return self._json(404, {'error': 'esa cuenta no existe'})
            b = os.path.join(DATOS, 'usuarios', u); ld = os.path.join(b, 'assets', 'live'); pd = os.path.join(b, 'assets', 'personajes')
            return self._json(200, {'ok': True, 'personajes': sorted(x for x in os.listdir(pd) if not x.startswith(('.', '_'))) if os.path.isdir(pd) else [], 'live': sorted(x for x in os.listdir(ld) if not x.startswith('.') and not x.endswith('.json')) if os.path.isdir(ld) else []})
        n = int(self.headers.get('Content-Length') or 0)
        if n > 40_000_000: return self._json(413, {'error': 'demasiado grande'})
        try: body = json.loads(self.rfile.read(n) or b'{}')
        except Exception: return self._json(400, {'error': 'no es JSON'})
        u = str(body.get('uid') or ''); fn = os.path.basename(str(body.get('file') or ''))
        if not _UUID.fullmatch(u) or not os.path.isdir(os.path.join(DATOS, 'usuarios', u)): return self._json(404, {'error': 'esa cuenta no existe'})
        if not re.fullmatch(r'[A-Za-z0-9._-]{1,180}\.(png|jpe?g|webp)', fn, re.I): return self._json(400, {'error': 'nombre no válido'})
        ld = os.path.join(DATOS, 'usuarios', u, 'assets', 'live'); os.makedirs(ld, exist_ok=True); dst = os.path.join(ld, fn)
        if os.path.exists(dst): return self._json(200, {'ok': True, 'ya': True})
        try: data = base64.b64decode(str(body.get('data') or ''))
        except Exception: return self._json(400, {'error': 'imagen no válida'})
        if len(data) < 100: return self._json(400, {'error': 'imagen vacía'})
        open(dst + '.tmp', 'wb').write(data); os.replace(dst + '.tmp', dst)
        meta = body.get('meta') if isinstance(body.get('meta'), dict) else {}
        meta = dict(meta, file='assets/live/' + fn); meta.pop('hidden', None)
        json.dump(meta, open(dst + '.json', 'w'), ensure_ascii=False, indent=1); _peso.pop(u, None)
        return self._json(200, {'ok': True})
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
            self.send_response(204); self.send_header('Access-Control-Allow-Methods', 'GET, POST, HEAD, OPTIONS'); self.send_header('Access-Control-Allow-Headers', 'Authorization, Content-Type, X-Ver-Como'); self.send_header('Access-Control-Max-Age', '600'); self.send_header('Content-Length', '0'); self.end_headers()
    def translate_path(self, path): return getattr(self, '_fijo', None) or super().translate_path(path)   # en servidor el fichero ya viene resuelto por _estatico
    def list_directory(self, path): return super().list_directory(path) if not SERVIDOR else self.send_error(404)   # en servidor, nunca listados
    def _estatico(self, cabeza=False):   # modo servidor: solo /assets/… — primero la casa de la cuenta; si no está y es de la biblioteca común, al almacén público. Nada más (ni código, ni catálogo, ni registros, ni lo de otra cuenta)
        ruta = urllib.parse.unquote(urllib.parse.urlparse(self.path).path); rel = _rel_ok(ruta[1:]) if ruta.startswith('/assets/') else None
        if not rel: return self._corta(404)
        if rel.startswith('assets/liga/'):   # 🥊 Workflows: solo el equipo
            full = os.path.join(LIGA_WEB, *rel.split('/')[2:]) if LIGA_WEB else ''
            if not liga_puede() or not full or not _dentro(LIGA_WEB, full) or not os.path.isfile(full): return self._corta(404)
            self._cc = 'private, no-cache'; self._fijo = full; return super().do_HEAD() if cabeza else super().do_GET()
        fa = _aria_fich(rel) if not os.path.isfile(os.path.join(casa(), *rel.split('/'))) else None
        if fa: self._cc = 'private, no-cache'; self._fijo = fa; return super().do_HEAD() if cabeza else super().do_GET()
        if rel.startswith('assets/publica/'):   # v237: una creación publicada en la Fototeca/Filmoteca de la comunidad
            full = _publica(rel)
            if not full and not aria_fija():   # el equipo puede ver lo denunciado, para revisarlo
                L_ = rel.split('/'); u_ = _com_cuentas().get(L_[2]) if len(L_) == 5 else None
                if u_ and '/'.join(L_[2:]) in (_com_lee().get('den') or {}) and L_[3] in ('live', 'video') and not L_[4].startswith('.'):
                    c_ = os.path.join(DATOS, 'usuarios', u_, 'assets', L_[3], L_[4]); full = c_ if os.path.isfile(c_) else None
            if not full: return self._corta(404)
            if 'm=1' in (urllib.parse.urlparse(self.path).query or '') and '/live/' in full:   # v238: miniatura (560 px) si ya está hecha; si no, se hace ahora
                mini = os.path.join(os.path.dirname(full), '.mini', os.path.basename(full) + '.jpg')
                if not os.path.isfile(mini):
                    try:
                        from PIL import Image
                        os.makedirs(os.path.dirname(mini), exist_ok=True); im = Image.open(full).convert('RGB'); im.thumbnail((560, 560)); im.save(mini + '.tmp', 'JPEG', quality=80); os.replace(mini + '.tmp', mini)
                    except Exception: mini = None
                if mini: full = mini
            self._cc = 'private, max-age=600'; self._fijo = full
            return super().do_HEAD() if cabeza else super().do_GET()
        if rel.startswith('assets/compartida/'):   # v220: una creación de una carpeta que otro creador me ha compartido
            full = _compartida(rel)
            if not full: return self._corta(404)
            if 'm=1' in (urllib.parse.urlparse(self.path).query or ''): full = _mini_de(full)   # v239: miniatura
            self._cc = 'private, no-cache'; self._fijo = full
            return super().do_HEAD() if cabeza else super().do_GET()
        if rel.startswith('assets/prestamo/'):   # del personaje de otro creador, al navegador solo se le sirve el avatar (su ficha y su cuerpo los lee el servidor al generar)
            full = _prestado(rel) if rel.endswith('/foto.jpg') else None
            if not full: return self._corta(404)
            self._cc = 'private, no-cache'; self._fijo = full
            return super().do_HEAD() if cabeza else super().do_GET()
        base = casa(); full = os.path.join(base, *rel.split('/'))
        if _dentro(base, full) and os.path.isfile(full):
            self._cc = 'private, no-cache'; self._fijo = full
            return super().do_HEAD() if cabeza else super().do_GET()
        if _biblio_ok(rel) and DATOS:   # v298: si la biblioteca común está en el disco del servidor (Filmoteca ligera, muestras de voz), se sirve de ahí; antes se mandaba al almacén público, donde no están
            bb = os.path.join(DATOS, 'biblioteca'); bf = os.path.join(bb, *rel.split('/'))
            if _dentro(bb, bf) and os.path.isfile(bf):
                self._cc = 'private, max-age=86400'; self._fijo = bf
                return super().do_HEAD() if cabeza else super().do_GET()
        if _biblio_ok(rel):
            self._cc = 'private, max-age=3600'; self.send_response(302); self.send_header('Location', _biblio_url(rel)); self.send_header('Content-Length', '0'); self.end_headers(); return
        return self._corta(404)
    def _json(self, code, obj):
        pr = getattr(_ctx, 'prest', None); _ctx.prest = None; _ctx.prestamo_ok = False
        if pr and isinstance(obj, dict):   # con un personaje prestado no se devuelven las direcciones de las referencias subidas (entre ellas iría su ficha)
            obj = {k: v for k, v in obj.items() if k != 'image_urls'}
            if isinstance(obj.get('payload'), dict): obj['payload'] = {k: v for k, v in obj['payload'].items() if k not in ('image_urls', 'images', 'image_url')}
            if code == 200 and obj.get('request_id'): _prest_apunta(pr)
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
            if u.path == '/api/calendario': return self._json(404, {'error': 'no disponible en el servidor'})
            if u.path in ('/api/liga', '/api/liga/zip') and not liga_puede(): return self._json(403, {'error': 'Los Workflows son solo para el equipo'})   # Notion y los duelos son del ordenador de Max
            if u.path == '/api/catalogo': return self._json(200, _cat_load()[1])   # el catálogo que ve esta cuenta: el común + su capa
        if u.path == '/api/claves':   # estado de las APIs, sin enseñar nunca las claves
            A = _apis_estado(); w = A[0]
            return self._json(200, {'ok': True, 'apis': A, 'ws': w['on'], 'ws_fin': w['fin'], 'saldo': w['saldo'], 'casa': casa_info()})
        if u.path == '/api/aria/estado':   # Aria de equipo: ¿puedo editarla, puedo publicarla, hay cambios sin publicar?
            if aria_fija(): return self._json(200, {'ok': True, 'editor': False})
            P = _aria_perfil()
            try: pub = json.load(open(os.path.join(DATOS, 'aria_publicado.json'), encoding='utf-8'))
            except Exception: pub = {}
            return self._json(200, {'ok': True, 'editor': True, 'publica': (getattr(_ctx, 'email', '') or '').lower() in ARIA_PUBLICAN, 'pendiente': P is not None and P != pub.get('borrador'), 'publicado': pub.get('t'), 'por': pub.get('por', '').split('@')[0], 'publicando': {'n': _ARIA_PUB.get('n', 0), 'total': _ARIA_PUB.get('total', 0)} if _ARIA_PUB.get('on') else None, 'pub_error': _ARIA_PUB.get('error') or ''})   # v323
        if u.path == '/api/monedero':   # 🎁 el saldo regalo de la cuenta y su historial de gasto (lo más nuevo primero)
            c = casa_info()
            if not c and not _casa_base(): return self._json(200, {'ok': True, 'casa': None, 'hist': []})
            with _cerrojo('mon'): m = _mon_lee()
            return self._json(200, {'ok': True, 'casa': c, 'hist': [{k: h.get(k) for k in ('t', 'usd', 'que', 'modelo', 'n')} for h in reversed(m.get('hist') or [])][:200]})
        if u.path == '/api/ping':
            return self._json(200, {'ok': True, **({'espacio': {'usado': espacio(), 'tope': CUOTA}, 'aria_mia': not aria_fija(), 'nsfw': nsfw_ok()} if SERVIDOR else {}), 'model': MODEL, 'default': CASA_DEF if casa_on() else 'mstudio', 'models': model_list(), 'unavailable': unavailable(), 'ws': bool(load_ws()) or casa_on(), 'casa': casa_info(), 'aspects': ASPECTS, 'key': _hf_listo(), 'ark': bool(load_ark()[0]), 'ark_usd': ARK_USD, 'interno': bool(getattr(_ctx, 'interno', False)) if SERVIDOR else os.path.isfile(os.path.expanduser('~/.claude/notion.env')), **({'servidor': True} if SERVIDOR else {})})   # interno = el ordenador de Max: enseña «Workflows» (en la web alojada, solo las cuentas autorizadas)
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
        if u.path == '/api/comunidad':   # el directorio + lo mío (solicitudes, conversaciones, avisos)
            yo = _cid()
            with _com_l:
                d = _com_lee()
                if _com_aria(d, yo): _com_guarda(d)
            cuentas = []
            for cid, uu in _com_cuentas().items():
                pjs = _com_personajes(uu, cid == yo)
                if pjs or cid == yo: cuentas.append({'cid': cid, 'alias': str(d['alias'].get(cid) or '')[:40], 'yo': cid == yo, 'personajes': pjs, 'foto': int(d['foto'].get(cid) or 0)})
            cuentas.sort(key=lambda c: (not c['yo'], (c['alias'] or 'zzz').lower()))
            nsig = {}
            for L_ in d['sig'].values():
                for k_ in L_ if isinstance(L_, list) else []: nsig[k_] = nsig.get(k_, 0) + 1
            for c_ in cuentas:
                for p_ in c_['personajes']: p_['seguidores'] = nsig.get(f"{c_['cid']}:{p_['pid']}", 0)
            if not aria_fija(): cuentas += [dict(c, personajes=[dict(p) for p in c['personajes']]) for c in COM_DEMO]   # 👁 demo: solo el equipo
            chats = []
            for k, M in d['msgs'].items():
                par = k.split('|')
                if yo not in par or not M: continue
                otra = [c for c in par if c != yo]; otra = otra[0] if otra else yo; visto = (d['visto'].get(yo) or {}).get(otra, 0)
                b_ = (d['borr'].get(yo) or {}).get(otra, 0)   # v300: lo que eliminé de mi lado ya no se ve
                if b_: M = [m for m in M if m.get('t', 0) > b_]
                if not M: continue
                chats.append({'con': otra, 'ultimo': M[-1], 'sin_leer': sum(1 for m in M if m.get('de') != yo and m.get('t', 0) > visto)})
            chats.sort(key=lambda c: -c['ultimo'].get('t', 0))
            return self._json(200, {'ok': True, 'yo': yo, 'alias': str(d['alias'].get(yo) or ''), 'cuentas': cuentas, 'solicitudes': [x for x in d['sol'] if yo in (x.get('de'), x.get('para'))][-200:], 'soy_aria': uid() == ARIA_UID, 'escriben': [k_[0] for k_, t_ in list(_ESC.items()) if k_[1] == yo and time.time() - t_ < 7], 'chats': chats, 'borrados': (d['borr'].get(yo) or {}), 'avisos': _com_avisos(d, yo), 'denuncias': (0 if aria_fija() else sum(1 for v in (d.get('den') or {}).values() if not (isinstance(v, dict) and v.get('vista')))), 'siguiendo': [x for x in d['sig'].get(yo) or [] if isinstance(x, str)], 'carpetas': _comp_lista(d, yo), 'prestados': _prest_lista(d, yo)})
        if u.path == '/api/comunidad/avisos':   # (la solicitud de ejemplo de Aria nace aquí también: así el aviso sale sin haber abierto la comunidad)
            yo = _cid()
            with _com_l:
                d = _com_lee()
                if _com_aria(d, yo): _com_guarda(d)
            nuevos = 0   # v320: influencers nuevos de otros desde la última vez que entraste en la Comunidad
            try:
                desde = float((urllib.parse.parse_qs(u.query).get('desde') or ['0'])[0] or 0)
                if desde > 0:
                    for c_, uu_ in _com_cuentas().items():
                        if c_ != yo: nuevos += sum(1 for p in _com_personajes(uu_) if (p.get('t') or 0) > desde)
            except Exception: pass
            return self._json(200, {'ok': True, 'n': _com_avisos(d, yo), 'nuevos': nuevos})
        if u.path == '/api/comunidad/busca':   # v244: en cuáles de MIS conversaciones se ha dicho eso (el último mensaje que lo contiene)
            yo = _cid(); t = ' '.join(((urllib.parse.parse_qs(u.query).get('q') or [''])[0]).lower().split())[:80]; out = []
            if len(t) >= 2:
                D_ = _com_lee()
                for k, M in D_['msgs'].items():
                    par = k.split('|')
                    if yo not in par or not isinstance(M, list): continue
                    o_ = [c for c in par if c != yo]; b_ = (D_['borr'].get(yo) or {}).get(o_[0] if o_ else yo, 0)   # v300
                    hit = next((m for m in reversed(M) if isinstance(m, dict) and m.get('t', 0) > b_ and t in str(m.get('x') or '').lower()), None)
                    if hit: otra = [c for c in par if c != yo]; out.append({'con': otra[0] if otra else yo, 'x': str(hit.get('x') or '')[:160], 't': hit.get('t') or 0, 'mio': hit.get('de') == yo})
            return self._json(200, {'ok': True, 'q': t, 'hits': out})
        if u.path == '/api/comunidad/chat':   # la conversación con otra cuenta (y se da por leída)
            yo = _cid(); con = (q.get('con') or [''])[0]
            if not (con == ARIA_CID or re.fullmatch(r'c[0-9a-f]{14}', con) or _demo_cid(con)) or con == yo: return self._json(400, {'error': 'conversación no válida'})
            with _com_l:
                d = _com_lee(); M = d['msgs'].get(_com_par(yo, con)) or []
                if M and (d['visto'].get(yo) or {}).get(con, 0) < M[-1].get('t', 0): d['visto'].setdefault(yo, {})[con] = time.time(); _com_guarda(d)
            b_ = (d['borr'].get(yo) or {}).get(con, 0)   # v300
            return self._json(200, {'ok': True, 'mensajes': [m for m in M if m.get('t', 0) > b_][-300:], 'escribe': time.time() - _ESC.get((con, yo), 0) < 7})   # v322
        if u.path == '/api/comunidad/avatar':   # el avatar de un personaje PÚBLICO de otra cuenta (lo único suyo que se sirve)
            cid = (q.get('c') or [''])[0]; pid = (q.get('p') or [''])[0]; grande = (q.get('t') or [''])[0] == 'foto'
            if (q.get('t') or [''])[0] == 'creador':   # v229: la foto de un creador (la sube él; es pública dentro de la Comunidad)
                uu = _com_cuentas().get(cid, '__no__')
                if uu == '__no__': return self._corta(404)
                with como(uu): fp = os.path.join(casa(), 'assets', 'comunidad', 'creador.jpg')
                if not os.path.isfile(fp): return self._corta(404)
                b = open(fp, 'rb').read(); self.send_response(200); self.send_header('Content-Type', 'image/jpeg'); self.send_header('Content-Length', str(len(b))); self.send_header('Cache-Control', 'private, max-age=3600'); self.end_headers(); self.wfile.write(b); return
            if cid.startswith('demo-'):   # las caras de la demo (solo el equipo)
                fp = os.path.join(COM_DEMO_DIR, pid + '.jpg')
                if aria_fija() or not re.fullmatch(r'[a-z0-9-]+', pid) or not os.path.isfile(fp): return self._corta(404)
                b = open(fp, 'rb').read(); self.send_response(200); self.send_header('Content-Type', 'image/jpeg'); self.send_header('Content-Length', str(len(b))); self.send_header('Cache-Control', 'private, max-age=3600'); self.end_headers(); self.wfile.write(b); return
            uu = _com_cuentas().get(cid, '__no__')
            if uu == '__no__' or not _pid_ok(pid) or not any(x['pid'] == pid for x in _com_personajes(uu, cid == _cid())): return self._corta(404)
            with como(uu): base = os.path.join(pers_dir(), pid)
            fp = next((os.path.join(base, n) for n in (('vista_frente.jpg', 'avatar.jpg', 'foto.jpg') if grande else ('avatar.jpg', 'foto.jpg')) if os.path.isfile(os.path.join(base, n))), None)   # v230: en grande, su vista de frente o la foto de perfil que ha encuadrado su dueña (no la hoja entera)
            if not fp: return self._corta(404)
            if not grande: fp = _avatar_centrado(base, fp) or fp   # v312: con la cara centrada
            elif os.path.basename(fp) != 'vista_frente.jpg':   # v313: sin vista de frente, la grande también centrada (sacada de su ficha entera)
                c_ = _avatar_centrado(base, fp, True)
                if c_: b = open(c_, 'rb').read(); self.send_response(200); self.send_header('Content-Type', 'image/jpeg'); self.send_header('Content-Length', str(len(b))); self.send_header('Cache-Control', 'private, max-age=600'); self.end_headers(); self.wfile.write(b); return
            if grande:   # la foto de la ficha, en grande para la galería (copia de 640 px, hecha una vez)
                fg = os.path.join(base, '.galeria_640_' + os.path.basename(fp))
                if not os.path.isfile(fg) or os.path.getmtime(fg) < os.path.getmtime(fp):
                    try:
                        from PIL import Image
                        im = Image.open(fp).convert('RGB'); im.thumbnail((640, 1000)); im.save(fg, quality=86)
                    except Exception: fg = fp
                fp = fg
            b = open(fp, 'rb').read(); self.send_response(200); self.send_header('Content-Type', 'image/jpeg'); self.send_header('Content-Length', str(len(b))); self.send_header('Cache-Control', 'private, max-age=600'); self.end_headers(); self.wfile.write(b); return
        if u.path == '/api/carpetas': return self._json(200, {'carpetas': _carp_lee(), 'compartidas': _comp_lista(_com_lee(), _cid()) if SERVIDOR else [], 'favs': _favs_lee()})   # las mías · y las que me comparten (para la Fototeca)
        if u.path == '/api/video/modelos':   # v255: los modelos de vídeo de WaveSpeed que se ofrecen, con sus opciones
            try: return self._json(200, {'ok': True, 'modelos': _vinfo() if (load_ws() or _casa_base()) else []})
            except Exception as e: return self._json(200, {'ok': False, 'modelos': [], 'error': str(e)[:160]})
        if u.path == '/api/fallidas':   # v270
            try: return self._json(200, {'ok': True, 'items': _fall_lee()})
            except Exception: return self._json(200, {'ok': True, 'items': []})
        if u.path == '/api/audio':   # v291: 🎙️ modelos y voces + mis audios
            if SERVIDOR and aria_fija(): return self._json(403, {'error': 'Crear audio: próximamente'})
            try: return self._json(200, dict({'ok': True, 'audios': _audios(), 'muestras': _muestras(), 'mu': _MU}, **_audio_info()))
            except Exception as e: plog('audio ✕ ' + str(e)[:160]); return self._json(200, {'ok': False, 'error': 'No se ha podido abrir Crear audio.'})
        if u.path == '/api/voz':   # v292: la voz de cada personaje (de momento, solo el equipo)
            if SERVIDOR and aria_fija(): return self._json(403, {'error': 'próximamente'})
            return self._json(200, {'ok': True, 'voces': _voces()})
        if u.path == '/api/admin/avisos':   # v290: la burbuja roja de ⚙️ Admin
            if not SERVIDOR or aria_fija(): return self._json(200, {'ok': True, 'total': 0})
            try: return self._json(200, dict({'ok': True}, **_adm_avisos()))
            except Exception: return self._json(200, {'ok': True, 'total': 0})
        if u.path == '/api/admin/panel':   # v280: ⚙️ Admin (solo el equipo)
            if not SERVIDOR or aria_fija(): return self._json(403, {'error': 'solo el equipo'})
            if 'fresco' in q: _ADM_P[1] = None; _ADM_C.clear()
            try: return self._json(200, dict({'ok': True, 'yo_dueno': (getattr(_ctx, 'email', '') or '').lower() in DUENOS}, **_adm_panel()))
            except Exception as e: plog('admin ✕ ' + str(e)[:200]); return self._json(200, {'ok': False, 'error': 'No se ha podido leer el panel.'})
        if u.path == '/api/miembros':   # v277: 👥 la lista de miembros (solo el equipo)
            if not SERVIDOR or aria_fija(): return self._json(403, {'error': 'solo el equipo'})
            try: return self._json(200, {'ok': True, 'items': _mi_lista()})
            except Exception as e: plog('miembros ✕ ' + str(e)[:160]); return self._json(200, {'ok': False, 'error': 'No se ha podido leer la lista de miembros.'})
        if u.path == '/api/bolsa':   # v269: 🎁 la bolsa del saldo regalo (solo el equipo)
            if not SERVIDOR or aria_fija(): return self._json(403, {'error': 'solo el equipo'})
            if 'fresco' in q: _bolsa_saldo(True)
            return self._json(200, {'ok': True, **_bolsa_resumen()})
        if u.path == '/api/denuncias':   # v238: lo denunciado, para que el equipo lo revise (restaurar o dejarlo retirado)
            if aria_fija(): return self._json(403, {'error': 'solo el equipo'})
            d = _com_lee(); den = d.get('den') if isinstance(d.get('den'), dict) else {}; out = []
            for k, v in sorted(den.items(), key=lambda kv: -((kv[1] or {}).get('t') or 0)):
                P = k.split('/'); v = v if isinstance(v, dict) else {}
                out.append({'k': k, 'f': 'assets/publica/' + k, 'kind': 'video' if len(P) == 3 and P[1] == 'video' else 'image', 'autor': str(d['alias'].get(P[0]) or 'Creador sin nombre')[:40], 'por': str(d['alias'].get(v.get('por')) or 'Creador sin nombre')[:40], 't': v.get('t') or 0, 'vista': bool(v.get('vista'))})
            return self._json(200, {'ok': True, 'items': out})
        if u.path == '/api/vistos': return self._json(200, {'ok': True, 'vistos': _vistos()})   # v304
        if u.path == '/api/efectos': return self._json(200, {'ok': True, 'items': _efx_lee()})   # v300
        if u.path == '/api/publicas':   # v237: la Fototeca / Filmoteca de la comunidad (tipo=image|video · cid=un creador · sig=1 solo de quien sigo)
            q = urllib.parse.parse_qs(u.query); tipo = (q.get('tipo') or [''])[0]; de = (q.get('cid') or [''])[0]; yo = _cid(); L = _pub_lista()
            if tipo in ('image', 'video'): L = [x for x in L if x['kind'] == tipo]
            if de: L = [x for x in L if x['cid'] == de]
            if (q.get('sig') or [''])[0]: S = {str(k).split(':')[0] for k in _com_lee()['sig'].get(yo) or []}; L = [x for x in L if x['cid'] in S]
            return self._json(200, {'ok': True, 'n': len(L), 'items': [dict(x, mia=x['cid'] == yo) for x in L[:600]]})
        if u.path == '/api/compartida':   # v220: lo que hay en una carpeta que me han compartido
            q = urllib.parse.parse_qs(u.query); cid = (q.get('cid') or [''])[0]; kid = (q.get('id') or [''])[0]
            uu, cs = _comp_carpetas(cid); c = next((x for x in cs if x['id'] == kid), None)
            if not c: return self._json(404, {'error': 'Esa carpeta ya no está compartida contigo.'})
            return self._json(200, {'ok': True, 'nombre': str(c.get('nombre') or 'Carpeta')[:40], 'alias': str(_com_lee()['alias'].get(cid) or '')[:40], 'items': [dict(_comp_ficha(uu, L), f=f'assets/compartida/{cid}/{kid}/{L[1]}/{L[2]}', kind='video' if L[1] == 'video' else 'image') for L in _comp_items(uu, c)]})   # las carpetas de Mis creaciones de la cuenta
        if u.path == '/api/papelera':   # lo borrado de Mis creaciones que aún se puede recuperar (30 días), lo más reciente primero
            trash = papelera(); out = []; ahora = time.time(); deotro = set()
            for fn in os.listdir(trash):   # v294: los archivos de una prenda o ficha borrada van con ella, no sueltos
                if fn.endswith('.papel'):
                    try: deotro.update(tn for _r, tn in (json.load(open(os.path.join(trash, fn), encoding='utf-8')).get('files') or []))
                    except Exception: pass
            for fn in os.listdir(trash):
                fp = os.path.join(trash, fn)
                if fn.startswith('.') or fn.endswith('.json') or fn in deotro or not os.path.isfile(fp + '.json'): continue   # solo creaciones (llevan su ficha .json al lado)
                try: meta = json.load(open(fp + '.json', encoding='utf-8'))
                except Exception: meta = {}
                t = os.path.getmtime(fp); video = fn.lower().endswith('.mp4'); po = os.path.splitext(fn)[0] + '.jpg'
                aud = fn.lower().endswith(('.mp3', '.wav', '.ogg', '.m4a', '.opus'))
                out.append({'tipo': 'audio' if aud else 'creacion', 'file': fn, 'src': 'assets/papelera/' + fn, 'thumb': '' if aud else 'assets/papelera/' + (po if video and os.path.isfile(os.path.join(trash, po)) else fn), 'kind': 'audio' if aud else 'video' if video else 'image', 'name': str(meta.get('name') or fn)[:120], 't': int(t), 'dias': max(0, 30 - int((ahora - t) // 86400))})
            for fn in os.listdir(trash):   # v294: personajes (carpetas) y prendas/fichas (con su .papel)
                fp = os.path.join(trash, fn); t = os.path.getmtime(fp); dias = max(0, 30 - int((ahora - t) / 86400))
                if fn.startswith('personaje_') and os.path.isdir(fp):
                    try: P0 = json.load(open(os.path.join(fp, 'personaje.json'), encoding='utf-8'))
                    except Exception: P0 = {}
                    av = next((x for x in ('avatar.jpg', 'avatar.png', 'foto.jpg') if os.path.isfile(os.path.join(fp, x))), None)
                    out.append({'tipo': 'personaje', 'file': fn, 'name': str(P0.get('name') or fn.split('_')[1])[:80], 'thumb': f'assets/papelera/{fn}/{av}' if av else '', 'kind': 'image', 't': int(t), 'dias': dias})
                elif fn.endswith('.papel'):
                    try: P0 = json.load(open(fp, encoding='utf-8'))
                    except Exception: continue
                    out.append({'tipo': P0.get('tipo'), 'file': fn, 'name': str(P0.get('name') or fn)[:80], 'thumb': 'assets/papelera/' + P0['thumb'] if P0.get('thumb') else '', 'kind': 'image', 't': int(t), 'dias': dias})
            out.sort(key=lambda x: -x['t']); return self._json(200, {'ok': True, 'items': out[:800], 'dias': 30, 'caduca': bool(SERVIDOR)})
        if u.path == '/api/pendientes':   # trabajos de personajes que la página aún no ha recogido (si se recarga, no se pierden)
            out = [{'rid': rid, 'item': j.get('item'), 'meta': {k: (j.get('meta') or {}).get(k) for k in ('personaje', 'pjKind', 'name', 'pjEditor')}, 'file': j.get('file'), 'usd': j.get('usd'), 'kind': j.get('kind', 'image'), 'edad': round(time.time() - j['t0'], 1)}
                   for rid, j in list(jobs.items()) if j.get('owner') == uid() and not j.get('claimed') and not j.get('failed') and str((j.get('meta') or {}).get('personaje') or '_').strip()[:1] not in ('_', '')]
            return self._json(200, {'jobs': out})
        if u.path == '/api/estado': return self._json(*_estado((q.get('id') or [''])[0]))
        if u.path == '/api/liga/modelos':   # 🥊 generadores para «Nuevo duelo» (catálogo de WaveSpeed + Higgsfield por API, con las claves de la cuenta de Aria)
            if not liga_puede(): return self._json(403, {'error': 'Los Workflows son solo para el equipo'})
            with como(ARIA_UID, ARIA_EMAIL, True): L = _liga_catalogo()
            return self._json(200, {'ok': True, 'modelos': [{k: x[k] for k in ('id', 'nombre', 'prov', 'grupo', 'precio')} for x in L]})
        if u.path == '/api/liga/zip':   # 🥊 descarga del carrusel (o de todo el duelo) en un zip
            did = (q.get('id') or [''])[0]; carpeta = os.path.join(liga_dir(), did)
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
            os.makedirs(liga_dir(), exist_ok=True); out = []
            for d in sorted(os.listdir(liga_dir()), reverse=True):
                f = os.path.join(liga_dir(), d, 'duelo.json')
                if d.startswith('.') or not os.path.isfile(f): continue
                try: duelo = json.load(open(f, encoding='utf-8'))
                except Exception as e: duelo = {'id': d, 'titulo': d + ' (duelo.json roto)', 'error': str(e)}
                duelo['id'] = d; mf = os.path.join(liga_dir(), d, 'max.json')
                try: mx = json.load(open(mf, encoding='utf-8')) if os.path.isfile(mf) else {}
                except Exception: mx = {}
                out.append({'duelo': duelo, 'max': mx})
            return self._json(200, {'duelos': out})
        return self._estatico() if SERVIDOR else super().do_GET()
    def _post(self):
        if lleno() and self.path in ('/api/video', '/api/generar', '/api/personaje', '/api/feedback', '/api/ficha_combo', '/api/lugares', '/api/complementos', '/api/fichas_outfit', '/api/perfil', '/api/ficha_panel', '/api/fichas360') : return self._json(413, {'error': LLENO, 'lleno': True})   # v260: todo lo que guarda ficheros
        if SERVIDOR and self.path == '/api/feedback' and not _tope('feedback', 30, 86400): return self._json(429, {'error': 'Has mandado muchos comentarios hoy: gracias. Mañana puedes seguir.'})
        if SERVIDOR and self.path in ('/api/describir', '/api/personas_img', '/api/acc_cajas', '/api/pj_analizar') and not _tope('lectura', 120, 3600): return self._json(429, {'error': 'Demasiadas lecturas seguidas: espera unos minutos.'})
        if self.path in ('/api/perfil', '/api/ficha_panel', '/api/fichas360') and aria_fija(): return self._json(403, {'error': FIJA, 'fija': True})   # todo esto escribe en la ficha de Aria
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
                if not body['id']: return self._json(400, {'error': 'no reconozco esa clave. Funcionan las de WaveSpeed, Higgsfield (ID:SECRET), Magnific (Freepik), ElevenLabs, Claude y ChatGPT: revisa que esté copiada entera'})
            api_ = next((a for a in APIS if a[0] == body.get('id')), None)
            if not api_: return self._json(400, {'error': 'API desconocida'})
            aid, nombre, envn, homef, _para = api_
            if 'off' in body and not body.get('key'):
                _claves_set(envn + '_OFF', '1' if body.get('off') else ''); plog(f'{nombre} ' + ('desconectada' if body.get('off') else 'vuelta a conectar')); return self._json(200, {'ok': True, 'apis': _apis_estado()})
            k = str(body.get('key') or '').strip()
            if len(k) < 16 or ' ' in k or '\n' in k or (SERVIDOR and not re.fullmatch(r'[\x21-\x7e]{16,400}', k)): return self._json(400, {'error': 'eso no parece una clave'})
            try:
                if aid == 'ws': _ws_saldo(k)
                elif aid == 'claude': _claude_ok(k)
                elif aid == 'oai': _oai_ok(k)
                elif aid == 'el': _el_ok(k)
                elif aid == 'mg': _mg_ok(k)
                elif aid == 'hf':
                    if ':' not in k: return self._json(400, {'error': 'la clave de Higgsfield tiene la forma ID:SECRET'})
                    _hf_ok(k)
            except urllib.error.HTTPError as e: return self._json(400, {'error': f'{nombre} no acepta esa clave' if e.code in (401, 403) else f'{nombre} respondió {e.code}'})
            except Exception as e: return self._json(400, {'error': 'no se pudo comprobar: ' + str(e)[:80]})
            _claves_set(envn, k); _claves_set(envn + '_OFF', ''); plog(f'clave de {nombre} guardada desde la pantalla'); return self._json(200, {'ok': True, 'apis': _apis_estado()})
        if self.path == '/api/carpetas':   # crear · renombrar · borrar una carpeta · meter / sacar creaciones
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(n) or b'{}')
            try:
                if isinstance(body, dict) and body.get('accion') == 'importar': return self._json(200, {'ok': True, 'n': _comp_importa(body), 'carpetas': _carp_lee()})
                if isinstance(body, dict) and body.get('accion') == 'favlib':   # v239: ♥ en una imagen de la Fototeca o un vídeo de la Filmoteca
                    tab = body.get('tab'); iid = str(body.get('id') or '')[:300]
                    if tab not in ('biblio', 'videoteca') or not iid: return self._json(400, {'error': 'no válido'})
                    with _cerrojo('favs'):
                        F = _favs_lee(); F[tab] = [x for x in F[tab] if x != iid] + ([iid] if body.get('on', True) else [])
                        tmp = _favs_fp() + f'.tmp{threading.get_ident()}'; json.dump(F, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False); os.replace(tmp, _favs_fp())
                    return self._json(200, {'ok': True, 'favs': F, 'carpetas': _carp_lee()})
                if isinstance(body, dict) and body.get('accion') == 'importar_pub': return self._json(200, {'ok': True, 'n': _pub_importa(body), 'carpetas': _carp_lee()})
                return self._json(200, {'ok': True, 'carpetas': _carp_haz(body if isinstance(body, dict) else {})})
            except ValueError as e: return self._json(400, {'error': str(e)})
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
        if self.path == '/api/comunidad':   # nombre de creador · ocultar/enseñar un personaje · pedir, responder o terminar una colaboración · mandar un mensaje
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(n) or b'{}'); ac = body.get('accion'); yo = _cid(); CU = _com_cuentas()
            if ac == 'visible':   # el interruptor «público / oculto» de un personaje mío
                pid = body.get('pid', ''); fp = os.path.join(pers_dir(), pid, 'personaje.json') if _pid_ok(pid) else ''
                if not fp or not os.path.isfile(fp): return self._json(404, {'error': 'personaje no encontrado'})
                with _cerrojo('pj'):
                    p = json.load(open(fp, encoding='utf-8')); p['privado'] = not bool(body.get('publico')); json.dump(p, open(fp, 'w', encoding='utf-8'), ensure_ascii=False)
                return self._json(200, {'ok': True, 'oculto': p['privado']})
            if ac == 'igseg':   # v249: cuántos seguidores tiene en Instagram (lo escribe su dueño: «12K», «3.400»…)
                pid = body.get('pid', ''); fp = os.path.join(pers_dir(), pid, 'personaje.json') if _pid_ok(pid) else ''
                if not fp or not os.path.isfile(fp): return self._json(404, {'error': 'personaje no encontrado'})
                v = re.sub(r'[^0-9KkMm.,]', '', str(body.get('n') or ''))[:10].upper()
                with _cerrojo('pj'):
                    p = json.load(open(fp, encoding='utf-8')); p['igSeguidores'] = v; json.dump(p, open(fp, 'w', encoding='utf-8'), ensure_ascii=False)
                return self._json(200, {'ok': True, 'igseg': v})
            if ac == 'abierto':   # v223: «abierto a colaborar» en un personaje mío: quien lo pida entra directo (solo SFW)
                pid = body.get('pid', ''); fp = os.path.join(pers_dir(), pid, 'personaje.json') if _pid_ok(pid) else ''
                if not fp or not os.path.isfile(fp): return self._json(404, {'error': 'personaje no encontrado'})
                with _cerrojo('pj'):
                    p = json.load(open(fp, encoding='utf-8')); p['abierto'] = bool(body.get('on')); json.dump(p, open(fp, 'w', encoding='utf-8'), ensure_ascii=False)
                return self._json(200, {'ok': True, 'abierto': p['abierto']})
            with _com_l:
                d = _com_lee()
                if ac == 'foto':   # v229: mi foto de creador (cuadrada, 320 px). Sin `data` se quita
                    fp = os.path.join(_dir('assets', 'comunidad'), 'creador.jpg'); data = str(body.get('data') or '')
                    if not data:
                        if os.path.exists(fp): os.remove(fp)
                        d['foto'].pop(yo, None); _com_guarda(d); return self._json(200, {'ok': True, 'foto': 0})
                    if not data.startswith('data:image/') or len(data) > 12_000_000: return self._json(400, {'error': 'Esa imagen no vale: prueba con un JPG o PNG más pequeño.'})
                    try:
                        from PIL import Image; import io
                        im = Image.open(io.BytesIO(base64.b64decode(data.split(',', 1)[1]))).convert('RGB'); w, h = im.size; m = min(w, h)
                        im.crop(((w - m) // 2, (h - m) // 2, (w - m) // 2 + m, (h - m) // 2 + m)).resize((320, 320), Image.LANCZOS).save(fp, 'JPEG', quality=88)
                    except Exception: return self._json(400, {'error': 'No se ha podido leer esa imagen.'})
                    d['foto'][yo] = int(time.time()); _com_guarda(d); return self._json(200, {'ok': True, 'foto': d['foto'][yo]})
                if ac == 'denuncia':   # v238 (equipo): restaurar una creación denunciada, o dejarla retirada y darla por revisada
                    if aria_fija(): return self._json(403, {'error': 'solo el equipo'})
                    k = str(body.get('k') or ''); den = d.get('den') if isinstance(d.get('den'), dict) else {}
                    if k not in den: return self._json(404, {'error': 'esa denuncia ya no existe'})
                    if body.get('restaurar'): den.pop(k)
                    else: den[k] = dict(den[k] if isinstance(den[k], dict) else {}, vista=True, retirada=True)
                    d['den'] = den; _com_guarda(d); _pub_reset(); return self._json(200, {'ok': True})
                if ac == 'denunciar':   # v237: una creación publicada deja de verse para todos al instante (queda apuntado quién y cuándo, para revisarlo)
                    rel = str(body.get('f') or '').split('?')[0]
                    if not rel.startswith('assets/publica/') or not any(x['f'] == rel for x in _pub_lista()): return self._json(404, {'error': 'Esa creación ya no está publicada.'})
                    if not isinstance(d.get('den'), dict): d['den'] = {}
                    k = rel[len('assets/publica/'):]; v = d['den'].get(k); v = dict(v) if isinstance(v, dict) and isinstance(v.get('por'), list) else {'por': [], 't': int(time.time())}
                    if yo in v['por']: return self._json(200, {'ok': True, 'ya': True})
                    hoy = sum(1 for x in d['den'].values() if isinstance(x, dict) and isinstance(x.get('por'), list) and yo in x['por'] and time.time() - (x.get('ult') or x.get('t') or 0) < 86400)
                    if hoy >= 5: return self._json(429, {'error': 'Has denunciado varias creaciones hoy. El equipo ya lo está revisando: gracias.'})
                    v['por'].append(yo); v['ult'] = int(time.time()); v.pop('vista', None)
                    if not aria_fija(): v['retirada'] = True   # si denuncia alguien del equipo, se retira al momento
                    d['den'][k] = v; _com_guarda(d); _pub_reset(); plog(f'denuncia · {rel} · {len(v["por"])}'); return self._json(200, {'ok': True, 'retirada': _den_oculta(v)})
                if ac == 'visto':   # v237: marcar una conversación como leída / no leída
                    con = str(body.get('con') or ''); M = d['msgs'].get(_com_par(yo, con)) or []
                    if not M: return self._json(404, {'error': 'conversación no encontrada'})
                    if body.get('leido', True): d['visto'].setdefault(yo, {})[con] = time.time()
                    else: ult = next((m.get('t', 0) for m in reversed(M) if m.get('de') != yo), M[-1].get('t', 0)); d['visto'].setdefault(yo, {})[con] = ult - 0.001
                    _com_guarda(d); return self._json(200, {'ok': True})
                if ac == 'seguir':   # v235: sigo (o dejo de seguir) a un influencer. No da ningún permiso: solo lo tengo a mano. Su dueña ve cuántos le siguen, no quiénes.
                    k = f"{str(body.get('cid') or '')[:40]}:{str(body.get('pid') or '')[:80]}"; L = [x for x in d['sig'].get(yo) or [] if isinstance(x, str) and x != k]
                    if body.get('on', True) and re.fullmatch(r'[a-z0-9-]+:[A-Za-z0-9_.-]+', k): L.append(k)
                    d['sig'][yo] = L[-500:]; _com_guarda(d); return self._json(200, {'ok': True, 'siguiendo': d['sig'][yo]})
                if ac == 'escribe':   # v322: «escribiendo…» (dura unos segundos)
                    con = str(body.get('con') or '')[:40]
                    if con and con != yo:
                        if len(_ESC) > 5000: _ESC.clear()
                        _ESC[(yo, con)] = time.time()
                    return self._json(200, {'ok': True})
                if ac == 'borrar_chat':   # v300: eliminar una conversación de MI lado (como en WhatsApp): el otro la sigue teniendo; si vuelve a escribir, reaparece
                    con = str(body.get('con') or '')[:40]
                    if not con or con == yo: return self._json(400, {'error': 'conversación no válida'})
                    ah = time.time(); d['borr'].setdefault(yo, {})[con] = ah; d['visto'].setdefault(yo, {})[con] = ah; _com_guarda(d); return self._json(200, {'ok': True})
                if ac == 'alias':
                    d['alias'][yo] = re.sub(r'\s+', ' ', str(body.get('nombre') or '')).strip()[:40]; _com_guarda(d); return self._json(200, {'ok': True, 'alias': d['alias'][yo]})
                if ac == 'solicitar':
                    para = body.get('para', ''); pid = body.get('pid') or None; msg = str(body.get('msg') or '').strip()[:500]
                    if (para not in CU and not _demo_cid(para)) or para == yo: return self._json(400, {'error': 'esa cuenta no existe'})
                    if pid and not any(x['pid'] == pid for x in _com_pjs(CU, para)): return self._json(400, {'error': 'ese personaje ya no está público'})
                    if any(x for x in d['sol'] if {x.get('de'), x.get('para')} == {yo, para} and (x.get('pid') or None) == pid and x.get('estado') in ('pendiente', 'aceptada')): return self._json(400, {'error': 'ya hay una solicitud o una colaboración con ese personaje'})
                    if not _com_tope('sol', 20): return self._json(429, {'error': 'demasiadas solicitudes seguidas: prueba dentro de un rato'})
                    x = {'id': 's' + hashlib.sha1(os.urandom(12)).hexdigest()[:12], 'de': yo, 'para': para, 'pid': pid, 'msg': msg, 'estado': 'pendiente', 't': time.time()}; d['sol'].append(x)
                    if msg: d['msgs'].setdefault(_com_par(yo, para), []).append({'de': yo, 'x': msg, 't': time.time(), 'sol': x['id']})
                    PJ_ = _com_pjs(CU, para); ab = {q['pid'] for q in PJ_ if q.get('abierto')}
                    if _demo_cid(para):   # v228: un creador de ejemplo acepta solo, para poder probar el recorrido entero
                        x['estado'] = 'aceptada'; x['demo'] = True; x['t2'] = time.time(); d['msgs'].setdefault(_com_par(yo, para), []).append({'de': para, 'x': DEMO_HOLA, 't': time.time() + 0.01, 'auto': True}); _com_guarda(d); return self._json(200, {'ok': True, 'solicitud': x})
                    if (pid in ab) if pid else (bool(PJ_) and len(ab) == len(PJ_)):   # v223: personaje abierto a colaborar → entra directo, sin esperar (solo SFW: el NSFW siempre lo activan los dos a mano)
                        x['estado'] = 'aceptada'; x['abierta'] = True; x['t2'] = time.time(); nom = next((q['nombre'] for q in PJ_ if q['pid'] == pid), None) if pid else None
                        d['msgs'].setdefault(_com_par(yo, para), []).append({'de': yo, 'x': '🤝 He empezado a colaborar con ' + (nom or 'tus personajes') + ' (lo tienes abierto a colaborar). Puedes retirar el permiso cuando quieras, aquí arriba.', 't': time.time() + 0.01, 'auto': True})
                    _com_guarda(d); return self._json(200, {'ok': True, 'solicitud': x})
                if ac in ('responder', 'terminar'):
                    x = next((x for x in d['sol'] if x.get('id') == body.get('id') and yo in (x.get('de'), x.get('para'))), None)
                    if not x: return self._json(404, {'error': 'solicitud no encontrada'})
                    if ac == 'responder':
                        if x.get('para') != yo or x.get('estado') != 'pendiente': return self._json(400, {'error': 'esa solicitud no está esperando tu respuesta'})
                        x['estado'] = 'aceptada' if body.get('aceptar') else 'rechazada'; pz = _plazo(body.get('dias'))
                        if x['estado'] == 'aceptada' and pz: x['hasta'] = time.time() + pz * 86400
                        if x['estado'] == 'aceptada' and x.get('de') in CU:
                            nom = next((q['nombre'] for q in _com_personajes(CU.get(yo), True) if q['pid'] == x.get('pid')), None) if x.get('pid') else None
                            d['msgs'].setdefault(_com_par(yo, x['de']), []).append({'de': yo, 'x': '✅ Solicitud aceptada: ya puedes crear con ' + (nom or 'mis personajes') + '. Lo encontrarás en Crear imagen, al añadir una persona.' + (f' El permiso dura {PLAZOS[pz]}.' if pz else ''), 't': time.time(), 'auto': True})
                    else:
                        era = x.get('estado'); x['estado'] = 'cancelada' if era == 'pendiente' and x.get('de') == yo else 'terminada'   # cualquiera de las dos partes puede retirar el permiso
                        otra = x.get('para') if x.get('de') == yo else x.get('de')
                        if era == 'aceptada' and otra in CU: d['msgs'].setdefault(_com_par(yo, otra), []).append({'de': yo, 'x': 'He retirado el permiso: esta colaboración ha terminado.' if x.get('para') == yo else 'He dejado esta colaboración.', 't': time.time(), 'auto': True})
                    x['t2'] = time.time(); _com_guarda(d); return self._json(200, {'ok': True, 'solicitud': x})
                if ac in ('plazo', 'nsfw'):   # v223: cuánto dura el permiso (lo decide quien lo da) · el modo NSFW (lo tienen que activar los dos)
                    x = next((x for x in d['sol'] if x.get('id') == body.get('id') and yo in (x.get('de'), x.get('para')) and x.get('estado') == 'aceptada'), None)
                    if not x or ARIA_CID in (x.get('de'), x.get('para')): return self._json(404, {'error': 'colaboración no encontrada'})
                    otra = x.get('para') if x.get('de') == yo else x.get('de'); pz = _plazo(body.get('dias')); M = d['msgs'].setdefault(_com_par(yo, otra), [])
                    if ac == 'plazo':
                        if x.get('para') != yo: return self._json(403, {'error': 'El plazo lo decide quien da el permiso.'})
                        if pz: x['hasta'] = time.time() + pz * 86400
                        else: x.pop('hasta', None)
                        M.append({'de': yo, 'x': f'⏱ El permiso dura ahora {PLAZOS[pz]}.' if pz else '⏱ El permiso ya no tiene fecha de fin.', 't': time.time(), 'auto': True})
                    else:
                        antes = _sol_nsfw(x); on = bool(body.get('on')); mi_k = 'nsfw_de' if x.get('de') == yo else 'nsfw_para'; mi_antes = bool(x.get(mi_k)); x[mi_k] = on
                        if on and x.get('para') == yo:
                            if pz: x['nsfw_hasta'] = time.time() + pz * 86400
                            else: x.pop('nsfw_hasta', None)
                        if not on and isinstance(x.get('nsfw_hasta'), (int, float)) and x['nsfw_hasta'] < time.time(): x.pop('nsfw_hasta', None)
                        if on and isinstance(x.get('nsfw_hasta'), (int, float)) and x['nsfw_hasta'] < time.time(): x.pop('nsfw_hasta', None); x['nsfw_para'] = (x.get('para') == yo)   # vencido: quien da el permiso tiene que volver a activarlo
                        ahora_ = _sol_nsfw(x)
                        if ahora_ and not antes: M.append({'de': yo, 'x': '🔞 Modo NSFW activado en esta colaboración: lo habéis activado los dos.' + (f' Dura {PLAZOS[pz]}.' if pz and x.get('para') == yo else ''), 't': time.time(), 'auto': True})
                        elif antes and not ahora_: M.append({'de': yo, 'x': 'He desactivado el modo NSFW de esta colaboración.', 't': time.time(), 'auto': True})
                        elif on and not mi_antes: M.append({'de': yo, 'x': '🔞 He activado el modo NSFW por mi parte. Se enciende cuando lo actives tú también, aquí arriba.', 't': time.time(), 'auto': True})
                    _com_guarda(d); return self._json(200, {'ok': True, 'solicitud': x, 'nsfw': _sol_nsfw(x)})
                if ac == 'mensaje':
                    con = body.get('con', ''); txt = str(body.get('texto') or '').strip()[:2000]
                    if (con not in CU and con != ARIA_CID and not _demo_cid(con)) or con == yo or not txt: return self._json(400, {'error': 'mensaje no válido'})
                    if con != ARIA_CID and not _demo_cid(con) and not _com_personajes(CU[con]) and not any(x for x in d['sol'] if {x.get('de'), x.get('para')} == {yo, con} and x.get('estado') in ('pendiente', 'aceptada')): return self._json(403, {'error': 'para escribirle, primero pídele una colaboración'})
                    if not _com_tope('msg', 120): return self._json(429, {'error': 'demasiados mensajes seguidos: prueba dentro de un rato'})
                    M = d['msgs'].setdefault(_com_par(yo, con), []); M.append({'de': yo, 'x': txt, 't': time.time()})
                    if con == ARIA_CID and not any(m.get('x') in (ARIA_RESP, ARIA_RESP_V) for m in M): M.append({'de': ARIA_CID, 'x': ARIA_RESP, 't': time.time() + 1})
                    del M[:-500]; _com_guarda(d); return self._json(200, {'ok': True})
            return self._json(400, {'error': 'acción desconocida'})
        if self.path == '/api/video/precio':   # v314: el precio EXACTO de WaveSpeed para ese modelo, modo, duración, resolución, formato y audio (no genera ni cobra; con la clave de la cuenta)
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(min(n, 4000)) or b'{}')
            md = _vmodos(str(body.get('vm') or ''))
            if not md: return self._json(200, {'ok': False, 'error': 'modelo desconocido'})
            mid = md.get(str(body.get('mode') or '')) or md.get('i2v') or md.get('t2v') or next(iter(md.values())); p = _vcat()[mid]['p']; en = lambda k_: ((p.get(k_) or {}).get('enum') or [])
            inp = {'prompt': 'x'}
            if 'image' in p: inp['image'] = 'https://example.com/a.jpg'
            if 'duration' in p:
                d0 = int(body.get('duration') or 5); E = en('duration')
                inp['duration'] = min(E, key=lambda x: abs(int(x) - d0)) if E else d0
            if 'resolution' in p and body.get('resolution'): inp['resolution'] = str(body['resolution'])
            if 'aspect_ratio' in p and body.get('aspect'): inp['aspect_ratio'] = str(body['aspect'])
            for k_ in ('generate_audio', 'sound', 'audio'):
                if (p.get(k_) or {}).get('type') == 'boolean': inp[k_] = bool(body.get('audio')); break
            ck = json.dumps([mid, inp], sort_keys=True); c = _VPRE.get(ck)
            if c and time.time() - c[0] < 6 * 3600: return self._json(200, {'ok': True, 'usd': c[1], 'lista': c[2], 'mid': mid})
            try: dd = (ws('POST', '/api/v3/model/price', {'model_id': mid, 'inputs': inp}) or {}).get('data') or {}
            except Exception as e: return self._json(200, {'ok': False, 'error': str(e)[:160]})
            if dd.get('price') is None: return self._json(200, {'ok': False, 'error': 'sin precio'})
            lista = float(dd.get('price') or 0); usd = float(dd['discounted_price']) if dd.get('discounted_price') is not None else lista
            if len(_VPRE) > 3000: _VPRE.clear()
            _VPRE[ck] = (time.time(), usd, lista); return self._json(200, {'ok': True, 'usd': usd, 'lista': lista, 'mid': mid})
        if self.path == '/api/prompt/montar':   # v307: la idea del usuario + lo elegido → un solo prompt (Claude Haiku; lo paga la casa)
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(min(n, 60000)) or b'{}')
            idea = str(body.get('idea') or '')[:4000]; auto = str(body.get('auto') or '')[:9000]
            if not auto.strip(): return self._json(400, {'error': 'no hay nada que montar'})
            try: return self._json(200, dict(_montar(idea, auto, 'video' if body.get('tipo') == 'video' else 'imagen'), ok=True))
            except RuntimeError as e: return self._json(400, {'error': str(e)})
        if self.path == '/api/vistos':   # v304: apuntar que esta cuenta ya ha visto un aviso
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(min(n, 2000)) or b'{}'); k = str(body.get('k') or '')
            if not re.fullmatch(r'[a-z0-9_.-]{1,60}', k): return self._json(400, {'error': 'aviso no válido'})
            L = _vistos()
            if k not in L: L.append(k); fp = _vistos_fp(); open(fp + '.tmp', 'w', encoding='utf-8').write(json.dumps(L[-300:])); os.replace(fp + '.tmp', fp)
            return self._json(200, {'ok': True})
        if self.path == '/api/publicas/subir':   # v303: subir a la comunidad algo hecho FUERA de la web — solo con su archivo Y su prompt
            if not SERVIDOR or not DATOS: return self._json(400, {'error': 'Esto solo funciona en la web'})
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(n) or b'{}')
            kind = 'video' if body.get('kind') == 'video' else 'image'; prompt = str(body.get('prompt') or '').strip()[:8000]
            if len(prompt) < 20: return self._json(400, {'error': 'Escribe el prompt con el que se hizo (al menos una frase).'})
            if _es_nsfw(prompt): return self._json(400, {'error': 'En la comunidad no se publica contenido para adultos.'})
            m_ = re.match(r'data:([\w/+.-]+);base64,(.*)$', str(body.get('data') or ''), re.S)
            if not m_: return self._json(400, {'error': 'Falta el archivo'})
            mime = m_.group(1).lower(); ext = {'image/jpeg': '.jpg', 'image/png': '.png', 'image/webp': '.webp', 'video/mp4': '.mp4', 'video/quicktime': '.mov', 'video/webm': '.webm'}.get(mime)
            if not ext or (kind == 'video') != mime.startswith('video/'): return self._json(400, {'error': 'Formato no admitido: imágenes JPG, PNG o WEBP; vídeos MP4, MOV o WEBM.'})
            try: data = base64.b64decode(m_.group(2))
            except Exception: return self._json(400, {'error': 'El archivo ha llegado roto: prueba otra vez'})
            if len(data) > 29 * 1024 * 1024: return self._json(413, {'error': 'Es demasiado grande (máximo 28 MB)'})
            _peso.pop(uid(), None)
            if lleno(): return self._json(507, {'error': LLENO})
            dd = video_dir() if kind == 'video' else live_dir(); os.makedirs(dd, exist_ok=True); fn = 'subida-' + hashlib.sha1(data).hexdigest()[:12] + ext; dst = os.path.join(dd, fn); rel = f"assets/{'video' if kind == 'video' else 'live'}/{fn}"
            if not os.path.exists(dst):
                with open(dst, 'wb') as o: o.write(data)
            meta = {'file': rel, 'kind': kind, 'item': 'subida', 'name': 'Subida a la comunidad', 'usd': 0, 't': time.time(), 'prompt': prompt, 'subida': True}
            if body.get('modelo'): meta['model'] = str(body['modelo'])[:60]
            pid = str(body.get('pid') or '')[:80]
            if pid and re.fullmatch(r'[A-Za-z0-9_.-]+', pid): meta['chars'] = [pid]; meta['charName'] = str(body.get('personaje') or '')[:80]
            for k_, q_ in (('width', 'ancho'), ('height', 'alto')):
                try: meta[k_] = int(body.get(q_) or 0) or None
                except (TypeError, ValueError): pass
            with open(dst + '.json', 'w', encoding='utf-8') as o: json.dump(meta, o, ensure_ascii=False, indent=1)
            _carp_haz({'accion': 'publicar_una', 'files': [rel]}); _pub_reset(); _peso.pop(uid(), None); plog(f'subida a la comunidad · {rel}')
            return self._json(200, {'ok': True, 'f': rel})
        if self.path == '/api/efectos':   # v300: el equipo pone o quita un vídeo de ✨ Efectos (y le pone nombre)
            if not liga_puede(): return self._json(403, {'error': 'Solo el equipo puede elegir los efectos'})
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(n) or b'{}'); k = str(body.get('id') or '')
            if not re.fullmatch(r'[A-Za-z0-9_:.-]{1,60}', k): return self._json(400, {'error': 'vídeo no válido'})
            with _EFX_L:
                E = _efx_lee(); prev = E.get(k) if isinstance(E.get(k), dict) else {}
                if body.get('on', True): E[k] = {'nombre': re.sub(r'\s+', ' ', str(body.get('nombre') if body.get('nombre') is not None else prev.get('nombre') or '')).strip()[:60], 't': prev.get('t') or time.time()}
                else: E.pop(k, None)
                _efx_guarda(E)
            return self._json(200, {'ok': True, 'items': E})
        if self.path.startswith('/api/liga'):   # 🥊 Workflows · Duelos: crear, guardar lo que se elige, montar el carrusel (v209: recuperado y también en la web, solo el equipo)
            if not liga_puede(): return self._json(403, {'error': 'Los Workflows son solo para el equipo'})
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(n) or b'{}'); LD = liga_dir(); os.makedirs(LD, exist_ok=True)
            if self.path == '/api/liga/nuevo':
                a, b = body.get('a') or {}, body.get('b') or {}
                if not a.get('nombre') or not b.get('nombre') or a.get('modelo') == b.get('modelo'): return self._json(400, {'error': 'elige dos modelos distintos'})
                if SERVIDOR:
                    with como(ARIA_UID, ARIA_EMAIL, True): ids = {x['id'] for x in _liga_catalogo()} | set(LIGA_WS)
                    if a.get('modelo') not in ids or b.get('modelo') not in ids: return self._json(400, {'error': 'Ese generador no se puede usar desde la web (no está en el catálogo de WaveSpeed ni de Higgsfield)'})
                slug = lambda s0: re.sub(r'[^a-z0-9]+', '-', str(s0).lower()).strip('-')[:24] or 'modelo'
                base = time.strftime('%Y-%m-%d') + f"-{slug(a['nombre'])}-vs-{slug(b['nombre'])}"; did = base; k = 2
                while os.path.exists(os.path.join(LD, did)): did = f'{base}-{k}'; k += 1
                meses = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']; t = time.localtime()
                quien = 'el servidor' if SERVIDOR else 'Claude'
                duelo = {'id': did, 'titulo': f"{a['nombre']} vs {b['nombre']}", 'fecha': f'{t.tm_mday} {meses[t.tm_mon - 1]} {t.tm_year}', 'paso': 1,
                         'a': {'nombre': str(a['nombre'])[:40], 'modelo': str(a.get('modelo', ''))[:60], 'nuevo': True}, 'b': {'nombre': str(b['nombre'])[:40], 'modelo': str(b.get('modelo', ''))[:60]},
                         'nota_inicial': str(body.get('nota') or '')[:4000], 'creado': time.strftime('%Y-%m-%d %H:%M:%S'), 'por': getattr(_ctx, 'email', '') or '',
                         'galeria_lado': 'a' if a.get('modelo') in ('nano_banana_pro', 'google/nano-banana-pro/edit') else 'b',
                         'aviso': f'Duelo creado. {quien[0].upper() + quien[1:]} está preparando los mundos con su portada y sus historias; aparecen aquí solos.', 'aviso_paso': 1,
                         'trabajando': {'paso': 1, 'texto': 'Preparando los mundos con su portada y sus historias…'},
                         'mundos': [], 'tests': LIGA_TESTS if SERVIDOR else [], 'prompts': [], 'galeria': {}, 'duelo': {}, 'carrusel': [], 'cierre': []}
                os.makedirs(os.path.join(LD, did))
                json.dump(duelo, open(os.path.join(LD, did, 'duelo.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
                json.dump({}, open(os.path.join(LD, did, 'max.json'), 'w', encoding='utf-8'))
                plog(f'liga nuevo duelo {did}'); return self._json(200, {'ok': True, 'id': did})
            did = str(body.get('id') or '')
            if not _liga_ok_id(did): return self._json(400, {'error': 'duelo desconocido'})
            carpeta = os.path.join(LD, did)
            if self.path == '/api/liga/abrir':
                if SERVIDOR: return self._json(400, {'error': 'en la web, descarga el carrusel con el botón ⬇'})
                import subprocess
                destino = os.path.join(carpeta, 'carrusel') if os.path.isdir(os.path.join(carpeta, 'carrusel')) else carpeta
                subprocess.run(['open', destino]); return self._json(200, {'ok': True, 'ruta': destino})
            if self.path == '/api/liga/montar':
                import subprocess
                py = LIGA_PY_SRV if SERVIDOR and os.path.isfile(LIGA_PY_SRV) else LIGA_PY   # en el servidor de pruebas de este Mac, el de los scripts
                r = subprocess.run([sys.executable, py, 'montar', did], capture_output=True, text=True, timeout=900, env=dict(os.environ, ARIA_LIGA_BASE=LD))
                plog(f'liga montar {did} → {r.returncode}')
                if r.returncode: return self._json(500, {'error': (r.stderr or r.stdout or '')[-500:]})
                return self._json(200, {'ok': True, 'salida': r.stdout[-500:]})
            if self.path == '/api/liga':   # guarda lo que se elige (mundo, prompts, favoritas, portada, cierre, notas, «listo») en max.json
                mx = body.get('max') or {}
                if not isinstance(mx, dict): return self._json(400, {'error': 'max no es un objeto'})
                mx['actualizado'] = time.strftime('%Y-%m-%d %H:%M:%S'); mx['por'] = getattr(_ctx, 'email', '') or ''
                with _liga_cerrojo(did + ':max'):
                    tmp = os.path.join(carpeta, f'.max.json.tmp{threading.get_ident()}'); json.dump(mx, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1); os.replace(tmp, os.path.join(carpeta, 'max.json'))
                return self._json(200, {'ok': True})
            return self._json(404, {'error': 'no'})
        if self.path == '/api/aria/publicar':   # «Publicar para todos»: la Aria de equipo pasa a ser la que ven todos los miembros
            if aria_fija() or (getattr(_ctx, 'email', '') or '').lower() not in ARIA_PUBLICAN: return self._json(403, {'error': 'Publicar a Aria para todos solo lo puede hacer Max'})
            if _ARIA_PUB.get('on'): return self._json(200, {'ok': True, 'enMarcha': True})   # v323: ya se está publicando
            if _aria_perfil() is None: return self._json(400, {'error': 'No hay cambios de Aria que publicar'})
            quien_ = getattr(_ctx, 'email', '') or ''; _ARIA_PUB.clear(); _ARIA_PUB.update(on=True, n=0, total=0, t=time.time())
            def _pub_hilo():   # v323: en segundo plano (con muchos ficheros tardaba más que la conexión y se quedaba «Publicando…» para siempre)
                try: r_ = _aria_publica(quien_); _ARIA_PUB.update(on=False, hecho=r_, error='')
                except Exception as e: plog('Aria publicar ✕ ' + str(e)[:200]); _ARIA_PUB.update(on=False, error=str(e)[:300])
            threading.Thread(target=_pub_hilo, daemon=True).start()
            return self._json(200, {'ok': True, 'enMarcha': True})
        if self.path == '/api/papelera/borrar':   # v294: {file} o {todo:true} → se borra para siempre
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(min(n, 5000)) or b'{}'); trash = papelera(); import shutil
            L = os.listdir(trash) if body.get('todo') else [os.path.basename(str(body.get('file') or ''))]
            for fn in L:
                if not fn or fn.startswith('.'): continue
                fp = os.path.join(trash, fn)
                if not _dentro(trash, fp): continue
                try:
                    if os.path.isdir(fp): shutil.rmtree(fp)
                    elif os.path.isfile(fp):
                        if fn.endswith('.papel'):
                            try:
                                for _r, tn in json.load(open(fp, encoding='utf-8')).get('files') or []:
                                    if os.path.isfile(os.path.join(trash, tn)): os.remove(os.path.join(trash, tn))
                            except Exception: pass
                        os.remove(fp)
                        for extra in ('.json',):
                            if os.path.isfile(fp + extra): os.remove(fp + extra)
                        po = os.path.join(trash, os.path.splitext(fn)[0] + '.jpg')
                        if fn.lower().endswith('.mp4') and os.path.isfile(po): os.remove(po)
                except Exception as e: plog('papelera borrar ✕ ' + str(e)[:120])
            plog('papelera: borrado para siempre ' + ('TODO' if body.get('todo') else L[0])); return self._json(200, {'ok': True})
        if self.path == '/api/audio/borrar':   # v294: un audio a la papelera {f:'assets/audio/…'}
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(min(n, 5000)) or b'{}'); import shutil
            rel = _rel_ok(str(body.get('f') or '')); p = os.path.join(casa(), *rel.split('/')) if rel and rel.startswith('assets/audio/') else ''
            if not p or not _dentro(casa(), p) or not os.path.isfile(p): return self._json(404, {'error': 'Ese audio no está en tu cuenta.'})
            for extra in ('', '.json'):
                if os.path.isfile(p + extra): shutil.move(p + extra, os.path.join(papelera(), os.path.basename(p) + extra))
            return self._json(200, {'ok': True})
        if self.path == '/api/restaurar':   # saca una creación de la papelera y la devuelve a Mis creaciones
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(n) or b'{}'); fn = os.path.basename(str(body.get('file') or '')); import shutil
            trash = papelera(); src = os.path.join(trash, fn)
            if fn.startswith('personaje_') and os.path.isdir(src):   # v294: un personaje entero
                pid = fn.split('_')[1] if fn.count('_') >= 2 else ''; pid = '_'.join(fn.split('_')[1:-1]) or pid; dst = os.path.join(pers_dir(), pid)
                if not _pid_ok(pid) or os.path.exists(dst): return self._json(400, {'error': 'Ya hay un personaje con ese nombre.'})
                shutil.move(src, dst); plog('restaurar ← papelera personaje ' + pid); return self._json(200, {'ok': True, 'tipo': 'personaje'})
            if fn.endswith('.papel') and os.path.isfile(src):   # v294: una prenda o una ficha
                P0 = json.load(open(src, encoding='utf-8')); base = casa() if SERVIDOR else ROOT
                for rel, tn in P0.get('files') or []:
                    a, b = os.path.join(trash, tn), os.path.join(base, rel)
                    if os.path.isfile(a) and _dentro(base, b) and not os.path.exists(b): os.makedirs(os.path.dirname(b), exist_ok=True); shutil.move(a, b)
                if P0.get('tipo') == 'prenda':
                    with _cerrojo():
                        head, C = _cat_load(); it = P0.get('item') or {}
                        if it.get('id') and not any(v['id'] == it['id'] for v in C['vestidor']):
                            C['vestidor'].append(it)
                            for v in C['vestidor']:
                                if v['id'] in (P0.get('kids') or []): v['parent'] = it['id']
                            _cat_save(head, C)
                elif P0.get('tipo') == 'ficha':
                    pf = os.path.join(pers_dir(), str(P0.get('pid') or ''), 'personaje.json')
                    if not os.path.isfile(pf): return self._json(400, {'error': 'Su personaje ya no existe: restaura primero el personaje.'})
                    with _cerrojo():
                        PP = json.load(open(pf)); PP['fichas'] = (PP.get('fichas') or []) + [P0.get('item') or {}]; json.dump(PP, open(pf, 'w'), ensure_ascii=False, indent=1)
                os.remove(src); plog('restaurar ← papelera ' + fn); return self._json(200, {'ok': True, 'tipo': P0.get('tipo')})
            if fn.lower().endswith(('.mp3', '.wav', '.ogg', '.m4a', '.opus')) and os.path.isfile(src):   # v294: un audio
                for extra in ('', '.json'):
                    if os.path.isfile(src + extra): shutil.move(src + extra, os.path.join(audio_dir(), fn + extra))
                return self._json(200, {'ok': True, 'tipo': 'audio'})
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
            if 'igSeguidores' not in P:   # también lo escribe /api/comunidad: se conserva
                try:
                    v_ = json.load(open(os.path.join(d, 'personaje.json'), encoding='utf-8')).get('igSeguidores')
                    if v_: P['igSeguidores'] = v_
                except Exception: pass
            if 'abierto' not in P:   # «abierto a colaborar» también lo escribe /api/comunidad: se conserva
                try:
                    if json.load(open(os.path.join(d, 'personaje.json'), encoding='utf-8')).get('abierto'): P['abierto'] = True
                except Exception: pass
            if 'privado' not in P:   # «oculto en la Comunidad» lo escribe otra petición (/api/comunidad): si la copia que llega no lo trae, se conserva
                try:
                    if json.load(open(os.path.join(d, 'personaje.json'), encoding='utf-8')).get('privado'): P['privado'] = True
                except Exception:
                    if os.path.isfile(os.path.join(d, 'personaje.json')): P['privado'] = True   # v260: si no se puede leer, mejor oculto que público por error
            _pj_guarda(os.path.join(d, 'personaje.json'), P)
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
                trash = papelera(); movidos = []
                for k in ('img', 'thumb'):
                    fp = busca(it.get(k), propio=True)
                    if fp and _dentro(d, fp): shutil.move(fp, os.path.join(trash, pid + '_' + os.path.basename(fp))); movidos.append([os.path.relpath(fp, casa()), pid + '_' + os.path.basename(fp)])
                json.dump({'tipo': 'ficha', 'pid': pid, 'item': it, 'files': movidos, 'name': (it.get('nombre') or 'Ficha') + ' · ' + str(PP.get('name') or pid), 'thumb': movidos[0][1] if movidos else ''}, open(os.path.join(trash, f'ficha_{pid}_{int(time.time())}.papel'), 'w', encoding='utf-8'), ensure_ascii=False)   # v294
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
                            d = perfil_dir('cuerpos'); rel = f'assets/perfil/cuerpos/cuerpo-{stamp}.jpg'; base.save(_pabs(rel), quality=92)
                            it = {'id': 'cuerpo-' + stamp, 'nombre': body.get('nombre') or 'Ficha de cuerpo', 'img': rel, 't': time.strftime('%Y-%m-%d %H:%M')}; P.setdefault('cuerpos', []).insert(0, it)
                        else:
                            d = perfil_dir('fichas360'); rel = f'assets/perfil/fichas360/ficha-{stamp}.jpg'; base.save(_pabs(rel), quality=92)
                            it = {'id': 'ficha-' + stamp, 'nombre': body.get('nombre') or 'Ficha 360', 'img': rel, 't': time.strftime('%Y-%m-%d %H:%M')}; P.setdefault('fichas360', []).insert(0, it)
                    elif act == 'alt_add':   # guarda una vista generada en el historial de esa ficha (360 o cuerpo)
                        A = P.setdefault('alt', {}).setdefault(body.get('kind') or '360', {}).setdefault(body.get('view') or 'frente', [])
                        f = (body.get('file') or '').split('?')[0]
                        if f and f not in A: A.insert(0, f)
                        it = None
                    elif act == 'add_cuerpo':
                        d = perfil_dir('cuerpos'); rel = f'assets/perfil/cuerpos/cuerpo-{stamp}.jpg'; Image.open(_abs(body.get('panel'))).convert('RGB').save(_pabs(rel), quality=92)
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
        if self.path == '/api/fallidas':   # v270: {quitar:id}
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(n) or b'{}')
            with _fall_l: L = [x for x in _fall_lee() if x.get('id') != body.get('quitar')]; _fall_guarda(L)
            return self._json(200, {'ok': True, 'items': L})
        if self.path == '/api/voz':   # v292: {pid, eleven, eleven_nombre, preset, seed, desc}
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(min(n, 20000)) or b'{}')
            if SERVIDOR and aria_fija(): return self._json(403, {'error': 'próximamente'})
            pid = str(body.get('pid') or '')
            if not re.fullmatch(r'[A-Za-z0-9_-]{1,60}', pid): return self._json(400, {'error': 'personaje no válido'})
            d = _voces(); d.pop('aria', None) if pid != 'aria' else None
            try: d0 = json.load(open(_voces_fp(), encoding='utf-8'))
            except Exception: d0 = {}
            d0 = d0 if isinstance(d0, dict) else {}
            prev = d0.get(pid) if isinstance(d0.get(pid), dict) else (d.get(pid) if isinstance(d.get(pid), dict) else {})   # v304: lo que no llega, se conserva
            d0[pid] = {k: str((body.get(k) if k in body else prev.get(k)) or '').strip()[:600] for k in ('eleven', 'eleven_nombre', 'preset', 'seed', 'desc')}
            fp = _voces_fp(); open(fp + '.tmp', 'w', encoding='utf-8').write(json.dumps(d0, ensure_ascii=False)); os.replace(fp + '.tmp', fp)
            return self._json(200, {'ok': True, 'voces': _voces()})
        if self.path == '/api/prompter':   # v297: {tipo:'audio', pedido, contexto} → {prompt, nota, usd}
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(min(n, 40000)) or b'{}')
            if SERVIDOR and aria_fija(): return self._json(403, {'error': 'próximamente'})
            if not _tope('prompter', 60, 3600): return self._json(429, {'error': 'Muchas peticiones seguidas: espera un rato.'})
            tipo = body.get('tipo') if body.get('tipo') in PROMPTER_SIS else 'audio'; pedido = str(body.get('pedido') or '').strip()[:4000]
            if not pedido: return self._json(400, {'error': 'Cuéntale al asistente lo que quieres.'})
            try: return self._json(200, dict({'ok': True}, **_prompter(tipo, pedido, str(body.get('contexto') or '')[:2000])))
            except Exception as e: plog('prompter ✕ ' + str(e)[:160]); return self._json(400, {'error': str(e)})
        if self.path == '/api/audio/muestras':   # v293: {modelo:'el'|'seed'} → genera una muestra de cada voz que falte (una vez; el precio lo ve antes el equipo)
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(min(n, 5000)) or b'{}')
            if SERVIDOR and aria_fija(): return self._json(403, {'error': 'solo el equipo'})
            if casa_on(): return self._json(400, {'error': 'Hace falta tu propia clave de WaveSpeed.'})
            if _MU['en_marcha']: return self._json(200, {'ok': True, 'mu': _MU})
            modelo = 'seed' if body.get('modelo') == 'seed' else 'el'; I = _audio_info(); todas = [v for v in I['voces_seed'] if '_es' in v or v.endswith('es')] if modelo == 'seed' else I['voces_el'] + [ARIA_VOZ] + [x.get('eleven') for x in _voces().values() if isinstance(x, dict) and x.get('eleven')]; todas = list(dict.fromkeys(todas))   # v296: de Seed, solo las que hablan español; de ElevenLabs, + la de Aria y las de tus personajes
            ya = _muestras().get(modelo) or {}; faltan = [v for v in todas if re.sub(r'[^A-Za-z0-9_-]', '_', v) not in ya]
            if not faltan: return self._json(200, {'ok': True, 'mu': _MU, 'nada': True})
            _MU.update({'en_marcha': True, 'hechas': 0, 'faltan': len(faltan), 'error': ''})
            threading.Thread(target=_mu_genera, args=((uid(), getattr(_ctx, 'email', ''), getattr(_ctx, 'interno', False)), modelo, faltan), daemon=True).start()
            plog(f'🎙 muestras de voz {modelo}: {len(faltan)} en marcha'); return self._json(200, {'ok': True, 'mu': _MU})
        if self.path == '/api/audio':   # v291: 🎙️ generar un audio {modelo, texto, voz, direccion, estabilidad, similitud, velocidad, duracion, audio:{data|path}}
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(min(n, 30_000_000)) or b'{}')
            try:
                if SERVIDOR and aria_fija(): return self._json(403, {'error': 'Crear audio: próximamente'})
                if lleno(): return self._json(413, {'error': LLENO, 'lleno': True})
                if casa_on(): raise RuntimeError('El audio todavía no entra en el saldo regalo: conecta tu clave de WaveSpeed en «Mis APIs».')
                if not _tope('audio', 40, 3600): raise RuntimeError('Has generado muchos audios seguidos: espera un rato.')
                k = str(body.get('modelo') or '');
                if k not in AUDIO_M: raise RuntimeError('Ese modelo de audio no existe.')
                ep, nom, usd0, modo = AUDIO_M[k]; texto = str(body.get('texto') or '').strip()[:9000]; dire = str(body.get('direccion') or '').strip()[:1500]; voz = str(body.get('voz') or '').strip()[:80]
                num = lambda x, lo, hi, d: max(lo, min(hi, float(body.get(x) if body.get(x) not in (None, '') else d)))
                if k in ('el4', 'el3'):
                    if not texto: raise RuntimeError('Escribe lo que tiene que decir.')
                    payload = {'text': texto, 'voice_id': voz or ARIA_VOZ, 'stability': num('estabilidad', 0, 1, .5)}
                    if k == 'el4': payload['similarity'] = num('similitud', 0, 1, .75)
                elif k == 'seedtts':
                    if not texto: raise RuntimeError('Escribe lo que tiene que decir.')
                    payload = {'text': texto, 'speed': num('velocidad', .5, 2, 1)}
                    if voz: payload['voice'] = voz
                    if dire: payload['voice_instruction'] = dire
                elif k == 'seedaudio':   # v295: el prompt completo del asistente + referencia opcional: una imagen o hasta 3 audios (no las dos)
                    pf = str(body.get('prompt_final') or '').strip()[:6000]
                    if not (pf or texto or dire): raise RuntimeError('Escribe lo que dice y cómo suena la escena.')
                    payload = {'prompt': pf or (((dire + '. ') if dire else '') + (f'Dice: «{texto}»' if texto else '')), 'speed': num('velocidad', .5, 2, 1), 'output_format': 'mp3'}
                    ref = body.get('ref') or {}
                    if ref.get('tipo') == 'imagen' and (ref.get('data') or ref.get('path')):
                        payload['image'] = resolve_ws({'data': ref['data']} if ref.get('data') else {'path': ref['path']})
                    elif ref.get('tipo') == 'audio' and ref.get('audios'):
                        payload['audios'] = [resolve_ws({'kind': 'audio', 'data': a['data']} if a.get('data') else {'kind': 'audio', 'path': a['path']}) for a in ref['audios'][:3] if a.get('data') or a.get('path')]
                elif k == 'vchange':
                    a = body.get('audio') or {}
                    if not (a.get('data') or a.get('path')): raise RuntimeError('Sube el audio al que quieres cambiarle la voz.')
                    if a.get('data') and len(a['data']) > 28_000_000: raise RuntimeError('El audio es demasiado grande (máx. ~20 MB).')
                    payload = {'audio': resolve_ws({'kind': 'audio', 'data': a['data']} if a.get('data') else {'kind': 'audio', 'path': a['path']}), 'voice_id': voz or 'Alicia', 'remove_background_noise': bool(body.get('limpiar'))}
                elif k == 'mirelo':
                    if not texto: raise RuntimeError('Describe el sonido.')
                    payload = {'text_prompt': texto[:500], 'duration': round(num('duracion', 1, 10, 5), 1), 'ambience': bool(body.get('ambiente')), 'num_samples': 1}
                elif k == 'sonilo':
                    if not texto: raise RuntimeError('Describe el sonido.')
                    payload = {'prompt': texto[:500], 'duration': int(round(num('duracion', 1, 10, 5))), 'audio_format': 'mp3'}
                else:   # sfx (Kling)
                    if not texto: raise RuntimeError('Describe el sonido.')
                    payload = {'prompt': texto[:200], 'duration': round(num('duracion', 3, 10, 5), 1)}
                try: bal0 = float((ws('GET', '/api/v3/balance').get('data') or {}).get('balance'))
                except Exception: bal0 = None
                r = ws('POST', '/api/v3/' + ep, payload); rid = (r.get('data') or {}).get('id')
                if not rid: raise RuntimeError('WaveSpeed no devolvió id: ' + json.dumps(r)[:200])
                corto = re.sub(r'[^a-z0-9]+', '-', (texto or dire or nom).lower())[:40].strip('-') or 'audio'
                meta = {'name': (texto or dire or nom)[:80], 'tab': 'audio', 'model': nom, 'modo': modo, 'texto': texto, 'direccion': dire, 'voz': voz or (ARIA_VOZ if k in ('el4', 'el3') else '')}
                usd0 = _audio_usd(k, payload.get('text') or payload.get('prompt') or '', float(body.get('segundos') or 0))   # v293
                jobs[rid] = {'t0': time.time(), 'item': 'audio_' + corto, 'kind': 'audio', 'model': k, 'prov': 'ws', 'usd': usd0, 'bal0': bal0, 'casa': False, 'credits': None, 'meta': meta}
                return self._json(200, {'request_id': rid, 'usd': usd0})
            except Exception as e:
                plog('audio ✕ ' + str(e)[:200]); return self._json(400, {'error': str(e)})
        if self.path == '/api/admin/acciones':   # v280
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(min(n, 20000)) or b'{}')
            if not SERVIDOR or aria_fija(): return self._json(403, {'error': 'solo el equipo'})
            if not _tope('admin', 60, 3600): return self._json(429, {'error': 'Demasiados cambios seguidos: espera un rato.'})
            ac = body.get('accion'); e = str(body.get('email') or '').strip().lower(); quien = (getattr(_ctx, 'email', '') or '').lower()
            try:
                if ac in ('ignorar', 'no_ignorar'):   # v292: quien quiere entrar y no se le va a dar acceso: deja de contar en la burbuja
                    S = _ign_lee(); (S.add if ac == 'ignorar' else S.discard)(e); _ign_guarda(S); _AV[1] = None; _ADM_P[1] = None
                    return self._json(200, dict({'ok': True, 'yo_dueno': quien in DUENOS}, **_adm_panel()))
                L = {m['email']: m for m in _mi_lista()}
                if e not in L: return self._json(404, {'error': 'Ese correo no está en la lista de miembros: dale acceso primero.'})
                if ac == 'equipo':
                    if quien not in DUENOS: return self._json(403, {'error': 'Solo Max puede cambiar quién es del equipo.'})
                    if e in DUENOS: return self._json(400, {'error': 'Esa cuenta es la del dueño: siempre es del equipo.'})
                    _sb_adm('POST', '/rest/v1/miembros', [{'email': e, 'interno': bool(body.get('on'))}], 'resolution=merge-duplicates,return=minimal')
                elif ac == 'precio':
                    p = float(str(body.get('precio')).replace(',', '.'))
                    if not (0 <= p <= 5000): return self._json(400, {'error': 'El plan tiene que ser entre 0 y 5000 $.'})
                    _sb_adm('POST', '/rest/v1/miembros', [{'email': e, 'precio': p}], 'resolution=merge-duplicates,return=minimal')
                else: return self._json(400, {'error': 'acción desconocida'})
                _ses_olvida(e); _ADM_P[1] = None; plog(f'⚙️ admin: {quien} · {ac} · {e} · {body.get("on", body.get("precio"))}')
                return self._json(200, dict({'ok': True, 'yo_dueno': quien in DUENOS}, **_adm_panel()))
            except (ValueError, TypeError): return self._json(400, {'error': 'El plan tiene que ser un número.'})
            except Exception as ex: plog('admin acciones ✕ ' + str(ex)[:200]); return self._json(400, {'error': 'No se ha podido guardar el cambio.'})
        if self.path == '/api/miembros':   # v277: {accion:'alta', emails:'texto', precio?} · {accion:'baja', email} — solo el equipo; nunca toca las cuentas del equipo
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(min(n, 200000)) or b'{}')
            if not SERVIDOR or aria_fija(): return self._json(403, {'error': 'solo el equipo'})
            if not _tope('miembros', 60, 3600): return self._json(429, {'error': 'Demasiados cambios seguidos: espera un rato.'})
            ac = body.get('accion'); quien = getattr(_ctx, 'email', '')
            try:
                L = _mi_lista(); equipo = {m['email'] for m in L if m['interno']} | {e.lower() for e in DUENOS}; ya = {m['email'] for m in L}
                if ac == 'alta':
                    em = sorted({e.lower().strip('.') for e in re.findall(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', str(body.get('emails') or ''))})
                    if not em: return self._json(400, {'error': 'No veo ningún correo en lo que has pegado.'})
                    if len(em) > 300: return self._json(400, {'error': 'Como mucho 300 correos de una vez.'})
                    pr = body.get('precio'); pr = None if pr in (None, '') else float(str(pr).replace(',', '.'))
                    if pr is not None and not (0 <= pr <= 5000): return self._json(400, {'error': 'El plan tiene que ser entre 0 y 5000 $.'})
                    filas = [dict({'email': e}, **({'precio': pr} if pr is not None else {})) for e in em if e not in equipo]   # las del equipo no se tocan
                    if filas: _sb_adm('POST', '/rest/v1/miembros', filas, 'resolution=merge-duplicates,return=minimal')
                    _AV[1] = None; nuevos = [e for e in em if e not in ya]; plog(f'👥 miembros: {quien} da de alta {len(nuevos)} nuevos ({len(filas)} filas)')
                    return self._json(200, {'ok': True, 'nuevos': len(nuevos), 'actualizados': len(filas) - len(nuevos), 'equipo': len(em) - len(filas), 'items': _mi_lista()})
                if ac == 'baja':
                    e = str(body.get('email') or '').strip().lower()
                    if e in equipo: return self._json(400, {'error': 'Las cuentas del equipo no se quitan desde aquí.'})
                    if e not in ya: return self._json(404, {'error': 'Ese correo no está en la lista.'})
                    _sb_adm('DELETE', '/rest/v1/miembros?email=eq.' + urllib.parse.quote(e)); _ses_olvida(e); plog(f'👥 miembros: {quien} quita a {e}')
                    return self._json(200, {'ok': True, 'items': _mi_lista()})
                return self._json(400, {'error': 'acción desconocida'})
            except ValueError: return self._json(400, {'error': 'El plan tiene que ser un número (lo que paga en Skool).'})
            except Exception as e: plog('miembros ✕ ' + str(e)[:200]); return self._json(400, {'error': 'No se ha podido guardar el cambio.'})
        if self.path == '/api/bolsa':   # v269: regalar saldo (a una cuenta o a todas) y el aviso — solo el equipo
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(n) or b'{}')
            if not SERVIDOR or aria_fija(): return self._json(403, {'error': 'solo el equipo'})
            ac = body.get('accion')
            try:
                if ac == 'aviso':
                    b = _bolsa_lee(); b['aviso'] = max(0.0, min(10000.0, float(body.get('usd') or 0))); _bolsa_guarda(b); return self._json(200, {'ok': True, **_bolsa_resumen()})
                usd = round(float(body.get('usd') or 0), 2); nota = str(body.get('nota') or '')[:80]
                if not (0 < usd <= 50): return self._json(400, {'error': 'Entre 0,01 y 50 $ por regalo.'})
                if ac == 'regalar_todos':
                    b = _bolsa_lee(); b['camp'].append({'id': 'c' + hashlib.sha1(f'{time.time()}{usd}'.encode()).hexdigest()[:10], 'usd': usd, 'nota': nota, 't': int(time.time()), 'por': getattr(_ctx, 'email', '')}); _bolsa_guarda(b)
                    plog(f'🎁 bolsa: +{usd} $ para todas las cuentas · {nota}'); return self._json(200, {'ok': True, **_bolsa_resumen()})
                if ac == 'regalar':
                    u = _com_cuentas().get(str(body.get('cid') or ''))
                    if not u: return self._json(404, {'error': 'Esa cuenta no existe.'})
                    with como(u, '', False):
                        with _cerrojo('mon'):
                            m = _mon_lee(); m['extra'] = round(float(m.get('extra') or 0) + usd, 4); m.setdefault('hist', []).append({'t': int(time.time()), 'dia': time.strftime('%Y-%m-%d', time.gmtime()), 'usd': -usd, 'que': 'regalo', 'nota': nota}); _mon_guarda(m)
                    plog(f'🎁 bolsa: +{usd} $ para {body.get("cid")} · {nota}'); return self._json(200, {'ok': True, **_bolsa_resumen()})
                return self._json(400, {'error': 'acción desconocida'})
            except Exception as e:
                plog('bolsa ✕ ' + str(e)); return self._json(400, {'error': str(e)})
        if self.path == '/api/ampliar':   # v266: {f:'assets/live/…'} → la misma creación a 4K (una creación nueva, con su ficha)
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(n) or b'{}')
            try:
                if lleno(): return self._json(413, {'error': LLENO, 'lleno': True})
                rel = _rel_ok(str(body.get('f') or '')); p = os.path.join(casa(), *rel.split('/')) if rel else ''
                if not rel or not rel.startswith('assets/live/') or not _dentro(casa(), p) or not os.path.isfile(p): return self._json(404, {'error': 'Esa creación no está en tu cuenta.'})
                try: m0 = json.load(open(p + '.json', encoding='utf-8'))
                except Exception: m0 = {}
                regalo = casa_on()
                if regalo:
                    if m0.get('nsfw'): raise RuntimeError('El saldo regalo no vale para contenido NSFW.')
                    casa_puede(UPSCALE_USD)
                url = resolve_ws({'path': rel})
                try: bal0 = None if regalo else float((ws('GET', '/api/v3/balance').get('data') or {}).get('balance'))
                except Exception: bal0 = None
                payload = {'image': url, 'target_resolution': '4k', 'output_format': 'jpeg'}
                if regalo:
                    with _cerrojo('gen'):
                        casa_puede(UPSCALE_USD); _ctx.casa_ok = True
                        try: r = ws('POST', '/api/v3/' + UPSCALE_EP, payload)
                        finally: _ctx.casa_ok = False
                else: r = ws('POST', '/api/v3/' + UPSCALE_EP, payload)
                rid = (r.get('data') or {}).get('id')
                if not rid: raise RuntimeError('WaveSpeed no devolvió id: ' + json.dumps(r)[:200])
                base = os.path.basename(rel).rsplit('.', 1)[0][:60]
                meta = {k: m0[k] for k in ('char', 'chars', 'charName', 'comp', 'prompt', 'nsfw', 'hidden', 'aspect') if k in m0}
                meta.update({'name': (m0.get('name') or 'Creación') + ' · 4K', 'tab': 'creaciones', 'model': 'Ampliada a 4K', 'ampliada_de': rel, 'quality': '4K'})
                jobs[rid] = {'t0': time.time(), 'item': base + '_4k', 'kind': 'image', 'model': 'up4k', 'prov': 'ws', 'usd': UPSCALE_USD, 'bal0': bal0, 'casa': regalo, 'credits': None, 'meta': meta}
                return self._json(200, {'request_id': rid, 'usd': UPSCALE_USD, 'casa': casa_info() if regalo else None})
            except Exception as e:
                plog('ampliar ✕ ' + str(e)); return self._json(400, {'error': str(e)})
        if self.path == '/api/feedback':   # feedback de las secciones en desarrollo → base «💬 Feedback de ARIA STUDIO» de Notion (+ copia en assets/feedback)
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(n) or b'{}')
            texto = (body.get('texto') or '').strip(); audio = body.get('audio') or ''; arel = ''
            if isinstance(audio, str) and audio.startswith('data:audio/') and ',' in audio and len(audio) < 6 * 1024 * 1024:
                try:
                    cab, b64 = audio.split(',', 1); ext = 'm4a' if ('mp4' in cab or 'aac' in cab) else 'ogg' if 'ogg' in cab else 'webm'
                    ad = os.path.join(casa(), 'feedback_audio') if SERVIDOR else os.path.join(ROOT, 'assets', 'feedback'); os.makedirs(ad, exist_ok=True)
                    an = time.strftime('%Y%m%d-%H%M%S') + '.' + ext; open(os.path.join(ad, an), 'wb').write(base64.b64decode(b64)); arel = ('feedback_audio/' if SERVIDOR else 'assets/feedback/') + an
                except Exception as e: plog('feedback: audio ✕ ' + str(e))
            adj = []   # archivos adjuntos (v204): hasta 3, de 10 MB; en la cuenta, fuera de assets/ (no se sirven)
            for a in (body.get('archivos') or [])[:3]:
                try:
                    du = str(a.get('data') or ''); nom = re.sub(r'[^A-Za-z0-9._-]+', '_', str(a.get('nombre') or 'archivo')).strip('._')[-80:] or 'archivo'
                    if not du.startswith('data:') or ',' not in du: continue
                    raw = base64.b64decode(du.split(',', 1)[1])
                    if len(raw) > 10 * 1024 * 1024: continue
                    fd = os.path.join(casa(), 'feedback_archivos') if SERVIDOR else os.path.join(ROOT, 'assets', 'feedback', 'archivos'); os.makedirs(fd, exist_ok=True)
                    fn = time.strftime('%Y%m%d-%H%M%S') + '_' + nom; open(os.path.join(fd, fn), 'wb').write(raw); adj.append(('feedback_archivos/' if SERVIDOR else 'assets/feedback/archivos/') + fn)
                except Exception as e: plog('feedback: adjunto ✕ ' + str(e))
            if adj: texto = (texto + '\n\n' if texto else '') + 'Adjuntos: ' + ', '.join(x.split('/')[-1] for x in adj)
            if not texto and arel: texto = '(nota de voz sin transcribir: ' + arel + ')'
            if not texto: return self._json(400, {'error': 'el comentario está vacío'})
            rec = {'t': time.strftime('%Y-%m-%d %H:%M:%S'), 'texto': texto, 'tipo': body.get('tipo') or '💬 Comentario', 'via': body.get('via') or '⌨️ Escrito', 'seccion': (body.get('seccion') or '')[:300], 'contexto': (body.get('contexto') or '')[:1800], 'usuario': body.get('usuario') or 'Max (local)', **({'audio': arel} if arel else {}), **({'archivos': adj} if adj else {})}
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
            if act not in ('ensure', 'preview', 'save') and aria_fija(): return self._json(403, {'error': FIJA, 'fija': True})   # un miembro sí guarda fichas creadas en SU Aria
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
                        fa = f'assets/perfil/fichas360/ficha-{st}.jpg'; _cover(a, CW, CH, 0.2).save(_pabs(fa), quality=92); P['ficha'] = fa
                        for img_, k, stem in ((b, 'comboBody', 'cuerpo'), (c, 'comboSide', 'lado')):
                            if img_ is not None: fb = f'assets/perfil/combo/{stem}-{st}.jpg'; img_.save(_pabs(fb), quality=92); P[k] = fb
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
                        fp = os.path.join(pers_dir(), owner, 'personaje.json'); P = json.load(open(fp)); P['lugares'] = out; _pj_guarda(fp, P)
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
                    f = os.path.join(pers_dir(), owner, 'personaje.json'); P = json.load(open(f)); P['complementos'] = L; _pj_guarda(f, P)
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
                trash = papelera(); movidos = []
                for rel in (it.get('ficha'), it.get('card'), ((it.get('ficha') or '').split('?')[0] if SERVIDOR else (it.get('ficha') or '')) + '.json'):
                    full = (busca(rel, propio=True) or '') if SERVIDOR else os.path.join(ROOT, rel or '')   # en servidor solo se mueve lo que es de la cuenta: una prenda de la biblioteca común no se toca (queda oculta para ella)
                    if rel and os.path.isfile(full): shutil.move(full, os.path.join(trash, os.path.basename(full))); movidos.append([os.path.relpath(full, casa() if SERVIDOR else ROOT), os.path.basename(full)])
                json.dump({'tipo': 'prenda', 'item': it, 'kids': [k['id'] for k in kids], 'files': movidos, 'name': it.get('name') or pid, 'thumb': movidos[0][1] if movidos else ''}, open(os.path.join(trash, f'prenda_{pid}_{int(time.time())}.papel'), 'w', encoding='utf-8'), ensure_ascii=False)   # v294: para poder devolverla
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
        if self.path == '/api/fav':   # v230: marca/desmarca una creación como favorita en su ficha .json
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(n) or b'{}'); rel = body.get('file', '')
            full = _creacion(rel)
            if not full: return self._json(400, {'error': 'archivo no válido'})
            meta = {}
            if os.path.exists(full + '.json'):
                try: meta = json.load(open(full + '.json'))
                except Exception: meta = {}
            meta['fav'] = bool(body.get('fav')); meta.setdefault('file', rel)
            json.dump(meta, open(full + '.json', 'w'), ensure_ascii=False, indent=1); return self._json(200, {'ok': True, 'fav': meta['fav']})
        if self.path == '/api/ocultar':   # marca/desmarca una creación como oculta en su ficha .json
            n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(n) or b'{}'); rel = body.get('file', '')
            full = _creacion(rel)
            if not full: return self._json(400, {'error': 'archivo no válido'})
            meta = {}
            if os.path.exists(full + '.json'):
                try: meta = json.load(open(full + '.json'))
                except Exception: meta = {}
            meta['hidden'] = bool(body.get('hidden')); meta.setdefault('file', rel); _pub_reset()
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
        if not nsfw_ok() and _con_aria(body) and ((body.get('meta') or {}).get('nsfw') or body.get('nsfw') or _es_nsfw(body.get('prompt'))): return self._json(400, {'error': 'El contenido NSFW con Aria Cruz no está disponible en esta cuenta.'})
        prest = sorted({tuple(str(i.get('path')).split('?')[0].split('/')[2:4]) for i in (body.get('images') or []) if isinstance(i, dict) and str(i.get('path') or '').startswith('assets/prestamo/')})
        if prest and ((body.get('meta') or {}).get('nsfw') or body.get('nsfw') or _es_nsfw(body.get('prompt'))):   # v223: solo si en ESA colaboración el modo NSFW lo han activado los dos (y no ha vencido)
            d_ = _com_lee(); yo_ = _cid()
            if not all(len(p) == 2 and any(x.get('de') == yo_ and x.get('para') == p[0] and x.get('pid') in (None, p[1]) and _sol_nsfw(x) for x in d_['sol']) for p in prest): return self._json(400, {'error': 'Con ese personaje el modo NSFW no está activado: tenéis que activarlo los dos en vuestra conversación de la Comunidad.'})
        _ctx.prestamo_ok = bool(prest); _ctx.prest = [p for p in prest if len(p) == 2]
        save_inputs(body)
        try:
            AM = all_models(); regalo = casa_on(); mkey = body.get('model') if body.get('model') in AM else (CASA_DEF if regalo else 'qwen'); M = AM[mkey]
            if M.get('prov') == 'ws':
                usd = round(M['usd']['high' if body.get('quality') == 'high' else 'std'] + M.get('per', 0) * max(0, min(len(body.get('images', [])), M['refs']) - 1), 4)   # precio de tarifa con sus referencias
                if regalo:   # 🎁 paga el saldo regalo: nunca NSFW (la clave es la de la casa) y solo si le llega
                    if (body.get('meta') or {}).get('nsfw') or body.get('nsfw') or _es_nsfw(body.get('prompt')): raise RuntimeError('El saldo regalo no vale para contenido NSFW. Para eso, conecta tu propia clave en «Mis APIs».')
                    if mkey not in CASA_MODELOS: raise RuntimeError('Ese modelo no entra en el saldo regalo: conecta tu propia clave en «Mis APIs».')   # v260: antes de subir nada
                    casa_puede(usd)
                urls = [resolve_ws(i) for i in (body.get('images') or [])[:M['refs']]]
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
            if not _hf_listo(): raise RuntimeError('Higgsfield no está conectado: conéctalo en «Mis APIs»' if SERVIDOR else 'falta la clave ID:SECRET en ~/.claude/higgsfield.env')
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
            plog('generar ✕ ' + str(e)); fallida_apunta((locals().get('body') or {}).get('meta') if isinstance(locals().get('body'), dict) else None, str(e)); return self._json(400, {'error': str(e)})

    def do_video(self):   # {mode:i2v|r2v, prompt, image:{path|data}, refs:[{path}], duration, resolution, aspect, audio, item, usd}
        n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(n) or b'{}')
        if not nsfw_ok() and _con_aria(body) and ((body.get('meta') or {}).get('nsfw') or body.get('nsfw') or _es_nsfw(body.get('prompt'))): return self._json(400, {'error': 'El contenido NSFW con Aria Cruz no está disponible en esta cuenta.'})
        try:
            mode = body.get('mode') if body.get('mode') in VIDEO_MODELS else 'i2v'; M = VIDEO_MODELS[mode]
            if body.get('provider') in ('ws', 'wsg') and casa_on(): raise RuntimeError('El vídeo todavía no entra en el saldo regalo: conecta tu propia clave en «Mis APIs».')   # v260: antes de subir nada
            if body.get('provider') == 'ws':   # WaveSpeed: Seedance 2.0 (0,12 $/s a 480p; 720p ×2, 1080p ×5, 4K ×10)
                res = body.get('resolution') if body.get('resolution') in ('480p', '720p', '1080p', '4k') else '720p'; dur = max(4, min(15, int(body.get('duration') or 5)))
                prompt = (body.get('prompt') or '').strip() or 'Natural subtle motion, she breathes and blinks.'
                if mode == 'i2v':
                    ep = 'bytedance/seedance-2.0/image-to-video'; payload = {'prompt': prompt, 'image': resolve_ws(body['image']), 'duration': dur, 'resolution': res, 'generate_audio': bool(body.get('audio'))}
                    if isinstance(body.get('end'), dict): payload['last_image'] = resolve_ws(body['end'])
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
            if body.get('provider') == 'wsg':   # v255: cualquier modelo de la lista (Kling, Veo, Hailuo, Wan, Sora, Grok…) por WaveSpeed
                base = str(body.get('vm') or ''); md = _vmodos(base) if any(base == c[2] for c in VID_CUR) else {}
                if not md: raise RuntimeError('ese modelo de vídeo no está disponible ahora mismo')
                R = body.get('refs') or []; una = bool(body.get('image')) and mode == 'i2v'
                M_ = _vcat(); conref = 'r2v' in md or 'reference_images' in (M_.get(md.get('t2v', ''), {}).get('p') or {}); imgs_ = by_kind(R, 'image')
                if not una and imgs_ and not conref and 'i2v' in md: una = True; body['image'] = imgs_[0]   # sin referencias: la primera imagen, de inicio
                mid = md.get('i2v') if una and 'i2v' in md else md.get('r2v') if (R and 'r2v' in md) else md.get('t2v') or md.get('i2v')
                if una and isinstance(body.get('end'), dict) and 'se' in md: mid = md['se']
                payload = _vpayload(mid, body, (body.get('prompt') or '').strip() or 'Natural subtle motion.')
                try: bal0 = float((ws('GET', '/api/v3/balance').get('data') or {}).get('balance'))
                except Exception: bal0 = None
                r = ws('POST', '/api/v3/' + mid, payload); rid = (r.get('data') or {}).get('id')
                if not rid: raise RuntimeError('WaveSpeed no devolvió id: ' + json.dumps(r)[:200])
                jobs[rid] = {'t0': time.time(), 'item': body.get('item', 'video'), 'kind': 'video', 'model': mode, 'prov': 'ws', 'usd': body.get('usd'), 'bal0': bal0, 'credits': None, 'meta': body.get('meta') or {}}
                return self._json(200, {'request_id': rid, 'model': mid, 'usd': body.get('usd'), 'payload': {k: v for k, v in payload.items() if k not in ('image', 'images', 'reference_images', 'reference_videos', 'reference_audios')}})
            if body.get('provider') == 'ark':   # ByteDance directo: mismo formato de trabajo, otra API
                ver = body.get('vmodel') if body.get('vmodel') in ARK_MODELS else '2.0'; res = body.get('resolution') if body.get('resolution') in ARK_USD[ver] else '720p'
                dur = max(4, min(30 if ver == '2.5' else 15, int(body.get('duration') or 5)))
                prompt = (body.get('prompt') or '').strip() or 'Natural subtle motion, she breathes and blinks.'
                if mode == 'i2v':
                    content = [{'type': 'text', 'text': prompt}, {'type': 'image_url', 'image_url': {'url': data_uri(body['image'])}, 'role': 'first_frame'}]
                    if isinstance(body.get('end'), dict): content.append({'type': 'image_url', 'image_url': {'url': data_uri(body['end'])}, 'role': 'last_frame'})
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
            if not _hf_listo(): raise RuntimeError('Higgsfield no está conectado: conéctalo en «Mis APIs»' if SERVIDOR else 'falta la clave ID:SECRET en ~/.claude/higgsfield.env')
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
            plog('video ✕ ' + str(e)); fallida_apunta(dict((body.get('meta') or {}), tab='video') if isinstance(body, dict) else None, str(e)); return self._json(400, {'error': str(e)})

_vig_en = set(); _vig_sem = threading.BoundedSemaphore(8)
def _vigila_uno(rid, j):   # modo servidor: sin llamarse por HTTP — el estado se pide directamente, como la cuenta dueña del trabajo (hasta 8 a la vez)
    try:
        with como(j.get('owner'), j.get('email') or '', bool(j.get('interno'))): _estado(rid)
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
    if SERVIDOR and LIGA_WEB: os.makedirs(LIGA_WEB, exist_ok=True); threading.Thread(target=_liga_vigia, daemon=True).start()   # 🥊 Workflows en la web
    if SERVIDOR: print(f'ARIA STUDIO v{VERSION} · modo servidor en http://{HOST}:{PORT} · datos en {DATOS} · orígenes: {", ".join(ORIGENES)}' + (' · ATAJO DE PRUEBAS X-Dev-Uid ACTIVO' if DEV else '') + (f' · 🎁 saldo regalo ACTIVO (tope {CASA_TOPE:g} $/mes)' if CASA_KEY else ' · saldo regalo apagado (falta ARIA_CASA_WS)'), flush=True)
    else: print(f'ARIA MIRROR · puente en http://localhost:{PORT} · modelo {MODEL} · clave {"OK" if _hf_listo() else "FALTA (ID:SECRET)"}')
    ThreadingHTTPServer((HOST, PORT), H).serve_forever()
