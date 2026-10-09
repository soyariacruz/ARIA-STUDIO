#!/usr/bin/env python3
"""Los últimos eventos del servidor en Render (reinicios, falta de memoria, despliegues): python3 render_eventos.py [n]. Lee la clave en ejecución; no la imprime."""
import sys, json
from subir_env import lee_env, api, FICHERO, SERVICIO
k = lee_env(FICHERO).get('RENDER_API_KEY')
if not k: raise SystemExit('falta RENDER_API_KEY en claves.env')
S = [s for s in api(k, 'GET', '/services?limit=20') if (s.get('service') or {}).get('name') == SERVICIO]
sid = S[0]['service']['id']; n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
for e in api(k, 'GET', f'/services/{sid}/events?limit={n}') or []:
    e = e.get('event') or e; d = e.get('details') or {}
    print((e.get('timestamp') or '')[:19], '|', e.get('type'), '|', json.dumps({k_: v for k_, v in d.items() if k_ in ('reason', 'memoryLimit', 'memoryUsage', 'deployStatus', 'trigger', 'nonZeroExit', 'oomKilled', 'exitCode', 'failed', 'message')}, ensure_ascii=False)[:200])
