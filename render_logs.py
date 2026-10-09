"""Enseña las últimas líneas del registro del servidor en Render que contengan un texto (por defecto 'ig ').

Uso: python3 render_logs.py [texto] [--n=200]
La clave se lee de ~/.aria-studio/claves.env (RENDER_API_KEY=…) o de la variable RENDER_API_KEY; nunca se imprime.
"""
import json, os, sys, urllib.parse, urllib.request
from subir_env import lee_env, api, FICHERO, SERVICIO

def main():
    env = lee_env(FICHERO); clave = os.environ.get('RENDER_API_KEY') or env.get('RENDER_API_KEY')
    if not clave: sys.exit('Falta RENDER_API_KEY')
    texto = next((a for a in sys.argv[1:] if not a.startswith('--')), 'ig ')
    n = int(next((a.split('=', 1)[1] for a in sys.argv[1:] if a.startswith('--n=')), '200'))
    servicios = api(clave, 'GET', f'/services?name={SERVICIO}&limit=20') or []
    s = next((x['service'] for x in servicios if isinstance(x, dict) and x.get('service', {}).get('name') == SERVICIO), None)
    if not s: sys.exit('servicio no encontrado')
    q = urllib.parse.urlencode({'ownerId': s['ownerId'], 'resource': s['id'], 'limit': n, 'text': texto})
    r = api(clave, 'GET', '/logs?' + q) or {}
    for l in r.get('logs') or []:
        print((l.get('timestamp') or '')[11:19], (l.get('message') or '').strip()[:300])

if __name__ == '__main__': main()
