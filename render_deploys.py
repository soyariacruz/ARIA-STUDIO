#!/usr/bin/env python3
"""Los últimos despliegues del servidor en Render (estado y commit), y si hace falta lanza uno: python3 render_deploys.py [lanzar]. Lee la clave en ejecución; no la imprime."""
import sys, time
from subir_env import lee_env, api, FICHERO, SERVICIO
k = lee_env(FICHERO).get('RENDER_API_KEY')
if not k: raise SystemExit('falta RENDER_API_KEY en claves.env')
S = [s for s in api(k, 'GET', '/services?limit=20') if (s.get('service') or {}).get('name') == SERVICIO]
if not S: raise SystemExit('servicio no encontrado')
sid = S[0]['service']['id']
if 'lanzar' in sys.argv:
    d = api(k, 'POST', f'/services/{sid}/deploys', {'clearCache': 'do_not_clear'}); print('lanzado:', d.get('id'), d.get('status')); time.sleep(2)
for d in api(k, 'GET', f'/services/{sid}/deploys?limit=4'):
    d = d.get('deploy') or d; c = d.get('commit') or {}
    print(d.get('status'), '|', (d.get('createdAt') or '')[:19], '|', (c.get('id') or '')[:7], '|', (c.get('message') or '').split('\n')[0][:70])
