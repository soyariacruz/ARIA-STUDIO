"""🥊 Duelos de AI League — herramientas de Claude para la carpeta de cada duelo (Aria Studio › assets/liga/<id>/).

  python3 liga.py bajar <id> <spec.json>    descarga imágenes: spec = [{"url": "...", "dest": "galeria/p01.png", "mini": true}, …]
                                            (la miniatura va a <carpeta>/mini/<nombre>.jpg, 480 px de ancho)
  python3 liga.py set <id> <cambios.json>   mezcla cambios en duelo.json (dicts se mezclan; listas y valores se sustituyen)
  python3 liga.py max <id>                  enseña lo que ha elegido Max (max.json), en corto
  python3 liga.py montar <id>               monta el carrusel con montar.py a partir de duelo.json + max.json

Las URLs de Higgsfield caducan: bajar siempre en el momento.
"""
import os, sys, json, time, shutil, urllib.request
from PIL import Image
BASE = os.environ.get('ARIA_LIGA_BASE') or '/Users/maxromanenko/Desktop/XXX/Aria Mirror/assets/liga'   # en el servidor de la web: ARIA_LIGA_BASE
UA = {'User-Agent': 'aria-studio/1.0'}


def carpeta(did):
    d = os.path.join(BASE, did)
    if not os.path.isfile(os.path.join(d, 'duelo.json')):
        sys.exit(f'No existe el duelo {did}')
    return d


def leer(d, f):
    p = os.path.join(d, f)
    return json.load(open(p, encoding='utf-8')) if os.path.isfile(p) else {}


def escribir(d, f, obj):
    tmp = os.path.join(d, '.' + f + '.tmp')
    json.dump(obj, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    os.replace(tmp, os.path.join(d, f))


def mezclar(a, b):
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(a.get(k), dict):
            mezclar(a[k], v)
        else:
            a[k] = v
    return a


def bajar(did, spec):
    d = carpeta(did); out = []
    for it in json.load(open(spec, encoding='utf-8')):
        dest = os.path.join(d, it['dest']); os.makedirs(os.path.dirname(dest), exist_ok=True)
        with urllib.request.urlopen(urllib.request.Request(it['url'], headers=UA), timeout=120) as r, open(dest, 'wb') as f:
            shutil.copyfileobj(r, f)
        res = {'dest': it['dest']}
        if it.get('mini'):
            im = Image.open(dest).convert('RGB'); res['w'], res['h'] = im.size
            im.thumbnail((480, 2000))
            rel = os.path.join(os.path.dirname(it['dest']), 'mini', os.path.splitext(os.path.basename(it['dest']))[0] + '.jpg')
            os.makedirs(os.path.join(d, os.path.dirname(rel)), exist_ok=True)
            im.save(os.path.join(d, rel), quality=84); res['mini'] = rel
        res['job'] = it.get('job'); res['para'] = it.get('galeria') or it.get('campeon') or it.get('regen'); res['lado'] = it.get('lado')
        res['tipo'] = 'galeria' if it.get('galeria') else 'campeon' if it.get('campeon') else 'regen' if it.get('regen') else None
        out.append(res)
    # «galeria»: pid → entra en la galería (modelo de D.galeria_lado) · «campeon»: pid → el OTRO lado del duelo (la página lo enseña sola)
    # el carrusel siempre pone «a» a la izquierda y «b» a la derecha; desde el 2 oct la galería va con Nano Banana Pro (galeria_lado 'b')
    if any(r['tipo'] for r in out):
        D = leer(d, 'duelo.json'); gl = D.get('galeria_lado') or 'a'; ot = 'b' if gl == 'a' else 'a'
        for r in out:
            if r['tipo'] == 'galeria':
                D.setdefault('galeria', {})[r['para']] = {'img': r['dest'], 'mini': r.get('mini'), 'w': r.get('w'), 'h': r.get('h'), 'job': r.get('job')}
            elif r['tipo'] == 'campeon':
                g0 = D.get('galeria', {}).get(r['para'], {})
                D.setdefault('duelo', {})[r['para']] = {gl: g0.get('img'), gl + '_mini': g0.get('mini'), ot: r['dest'], ot + '_mini': r.get('mini'), 'job_' + ot: r.get('job')}
            elif r['tipo'] == 'regen':   # «↻ Regenerar» (paso Duelo): la nueva pasa a ser la del par; la de antes queda en variantes (sale en «⇄»)
                pid, s = r['para'], r['lado']; par = D.setdefault('duelo', {}).setdefault(pid, {})
                if par.get(s):
                    D.setdefault('variantes', {}).setdefault(pid, {}).setdefault(s, []).append({'img': par[s], 'mini': par.get(s + '_mini')})
                par[s], par[s + '_mini'], par['job_' + s] = r['dest'], r.get('mini'), r.get('job')
                if s == gl and pid in (D.get('galeria') or {}):
                    D['galeria'][pid].update({'img': r['dest'], 'mini': r.get('mini'), 'w': r.get('w'), 'h': r.get('h'), 'job': r.get('job')})
        escribir(d, 'duelo.json', D)
    print(json.dumps([{k: v for k, v in r.items() if v} for r in out], ensure_ascii=False))


def main():
    acc, did = sys.argv[1], sys.argv[2]
    if acc == 'bajar':
        bajar(did, sys.argv[3])
    elif acc == 'set':
        d = carpeta(did); duelo = mezclar(leer(d, 'duelo.json'), json.load(open(sys.argv[3], encoding='utf-8')))
        escribir(d, 'duelo.json', duelo); print('duelo.json actualizado:', ', '.join(json.load(open(sys.argv[3], encoding='utf-8')).keys()))
    elif acc == 'max':
        m = leer(carpeta(did), 'max.json')
        pr = m.get('prompts', {})
        print(json.dumps({'mundo': m.get('mundo'), 'secuencia': m.get('secuencia'), 'alt': {k: {s: o.get('img') for s, o in v.items()} for k, v in (m.get('alt') or {}).items()}, 'listo': list((m.get('listo') or {}).keys()),
                          'prompts_ok': [k for k, v in pr.items() if v.get('ok') is True],
                          'prompts_fuera': [k for k, v in pr.items() if v.get('ok') is False],
                          'notas_prompts': {k: v['nota'] for k, v in pr.items() if v.get('nota')},
                          'fav': m.get('fav'), 'portada': m.get('portada'), 'cierre': m.get('cierre_img'),
                          'notas': {k: v for k, v in m.items() if k.startswith('nota') and v},
                          'duelo_notas': {k: v.get('nota') for k, v in (m.get('duelo') or {}).items() if v.get('nota')},
                          'titulos': m.get('titulos'), 'ficha_img': m.get('ficha_img'),
                          # comentarios que Max manda desde la página (mundos, imágenes) y que Claude aún no ha contestado (duelo.json › respuestas)
                          'peticiones_pendientes': [p for p in (m.get('peticiones') or []) if p.get('id') not in (leer(carpeta(did), 'duelo.json').get('respuestas') or {})],
                          'actualizado': m.get('actualizado')}, ensure_ascii=False, indent=1))
    elif acc == 'montar':
        d = carpeta(did); D = leer(d, 'duelo.json'); M = leer(d, 'max.json')
        P = {p['id']: p for p in D.get('prompts', [])}
        fav = sorted(M.get('fav') or [], key=lambda i: (P.get(i, {}).get('test', 99), i))
        # solo entran las parejas completas (una favorita nueva espera a que se genere su otro lado en el paso Duelo)
        fav = [pid for pid in fav if (D.get('duelo') or {}).get(pid, {}).get('a') and D['duelo'][pid].get('b')]
        cr = os.path.join(d, 'crudas'); shutil.rmtree(cr, ignore_errors=True); os.makedirs(cr)
        tests = {t['n']: t['nombre'] for t in D.get('tests', [])}; etiquetas = {}; titulos = M.get('titulos') or {}; alt = M.get('alt') or {}
        for k, pid in enumerate(fav, 1):
            par = D['duelo'][pid]; n = f'{k:02d}'
            for s in ('a', 'b'):   # «⇄» en el paso Duelo: Max puede cambiar la imagen de un lado por otra del mismo test (max.json › alt)
                f = ((alt.get(pid) or {}).get(s) or {}).get('img') or par[s]
                shutil.copy(os.path.join(d, f), os.path.join(cr, f'{n}_{s}' + os.path.splitext(f)[1]))
            etiquetas[n] = (titulos.get(pid) or '').strip() or tests.get(P[pid]['test'], '')   # el título que Max escribió en la página manda
        for clave, pid in (('portada', M.get('portada')), ('cierre', M.get('cierre_img'))):
            if pid == 'mundo':   # la portada del mundo elegido en el paso 1
                src = next(w['img'] for w in D['mundos'] if w['id'] == M.get('mundo'))
            elif ':' in pid:     # 'pNN:a|b' = imagen del otro modelo (pestaña de modelo en la galería)
                p0, s = pid.split(':'); src = D['duelo'][p0][s]
            else:
                src = D['galeria'][pid]['img']
            shutil.copy(os.path.join(d, src), os.path.join(cr, clave + os.path.splitext(src)[1]))
        json.dump({'a': D['a']['nombre'], 'b': D['b']['nombre'], 'portada': 'portada', 'cierre': 'cierre', 'tests': etiquetas},
                  open(os.path.join(d, 'montaje.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        # montar las diapositivas y apuntar el resultado en duelo.json (la página lo enseña en el paso 5)
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import montar as plantilla
        sal = os.path.join(d, 'carrusel'); shutil.rmtree(sal, ignore_errors=True)
        plantilla.main(d)
        D = leer(d, 'duelo.json')
        D['carrusel'] = ['carrusel/' + f for f in sorted(os.listdir(sal)) if f.endswith(('.png', '.jpg'))]
        D['titulos_montados'] = {pid: etiquetas[f'{k:02d}'] for k, pid in enumerate(fav, 1)}
        D['alt_montado'] = alt   # la página compara con max.json › alt y vuelve a montar si Max cambia una imagen
        D['roles_montados'] = [M.get('portada'), M.get('cierre_img')]   # ídem con la portada y el cierre
        D['montado'] = time.strftime('%Y-%m-%d %H:%M:%S')
        escribir(d, 'duelo.json', D)
        print(json.dumps({'parejas': len(fav), 'tests': etiquetas, 'diapositivas': len(D['carrusel'])}, ensure_ascii=False))


if __name__ == '__main__':
    main()
