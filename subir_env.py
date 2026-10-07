#!/usr/bin/env python3
"""Sube parámetros de ~/.aria-studio/claves.env a las variables de entorno del servicio de Render (aria-studio).

Lo ejecuta Max (el fichero es suyo):   python3 subir_env.py            → sube solo ARIA_WFSN y ARIA_WFSNBUTTON
                                       python3 subir_env.py ARIA_X ARIA_Y → sube esas líneas
                                       python3 subir_env.py --todas    → sube todas las líneas ARIA_* del fichero
Hace falta una clave de la API de Render (render.com → Account Settings → API Keys): o en el fichero, línea RENDER_API_KEY=…, o como variable RENDER_API_KEY.
Al cambiar una variable, Render reinicia el servicio solo (≈40 s). Nunca imprime los valores: solo los nombres.
"""
import json, os, sys, urllib.request, urllib.error

FICHERO = os.path.expanduser('~/.aria-studio/claves.env')
SERVICIO = os.environ.get('RENDER_SERVICE') or 'aria-studio'
POR_DEFECTO = ['ARIA_WFSN', 'ARIA_WFSNBUTTON']

def lee_env(fp):
    d = {}
    try:
        for ln in open(fp, encoding='utf-8'):
            ln = ln.strip()
            if not ln or ln.startswith('#') or '=' not in ln: continue
            k, v = ln.split('=', 1); d[k.strip()] = v.strip().strip('"\'')
    except OSError: sys.exit(f'No encuentro {fp}')
    return d

def api(clave, metodo, ruta, cuerpo=None):
    rq = urllib.request.Request('https://api.render.com/v1' + ruta, data=None if cuerpo is None else json.dumps(cuerpo).encode(), method=metodo,
                                headers={'Authorization': 'Bearer ' + clave, 'Accept': 'application/json', 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(rq, timeout=30) as r: return json.loads(r.read() or b'null')
    except urllib.error.HTTPError as e: sys.exit(f'Render respondió {e.code} en {metodo} {ruta}: {e.read().decode("utf-8", "replace")[:300]}')

def main():
    env = lee_env(FICHERO)
    clave = os.environ.get('RENDER_API_KEY') or env.get('RENDER_API_KEY')
    if not clave: sys.exit('Falta la clave de la API de Render: línea RENDER_API_KEY=… en claves.env o variable RENDER_API_KEY')
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if '--todas' in sys.argv: nombres = [k for k in env if k.startswith('ARIA_')]
    else: nombres = args or POR_DEFECTO
    faltan = [n for n in nombres if n not in env]
    if faltan: print('No están en el fichero (se saltan):', ', '.join(faltan))
    nombres = [n for n in nombres if n in env]
    if not nombres: sys.exit('Nada que subir.')
    servicios = api(clave, 'GET', f'/services?name={SERVICIO}&limit=20') or []
    sid = next((s['service']['id'] for s in servicios if isinstance(s, dict) and s.get('service', {}).get('name') == SERVICIO), None)
    if not sid: sys.exit(f'No encuentro el servicio «{SERVICIO}» en Render (¿la clave es de la cuenta correcta?)')
    for n in nombres:
        api(clave, 'PUT', f'/services/{sid}/env-vars/{n}', {'value': env[n]})
        print(f'✓ {n} → Render ({len(env[n])} caracteres)')
    dep = api(clave, 'POST', f'/services/{sid}/deploys', {}) or {}   # cambiar variables por la API no redespliega solo: se pide aquí
    print(f'Hecho. Despliegue pedido a Render ({dep.get("id", "?")}); en 1–2 min la web usa los valores nuevos.')

if __name__ == '__main__': main()
