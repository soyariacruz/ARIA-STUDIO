"""Actúa como la cuenta de pruebas «Vera Studio» contra el servidor de pruebas (:8770): acepta lo que le pidió Luna, le escribe y le pide a su vez colaboración.
Uso: python3 com_vera.py [ver|acepta|pide|mensaje|limpia]"""
import json, sys, urllib.request
B = 'http://127.0.0.1:8770'
VERA = 'cccccccc-0000-4000-8000-000000000001'

def api(uid, ruta, body=None):
    r = urllib.request.Request(B + ruta, data=json.dumps(body).encode() if body is not None else None, headers={'X-Dev-Uid': uid, 'Content-Type': 'application/json'})
    try:
        return json.loads(urllib.request.urlopen(r, timeout=20).read())
    except urllib.error.HTTPError as e:
        return {'http': e.code, 'cuerpo': e.read().decode()[:300]}

que = sys.argv[1] if len(sys.argv) > 1 else 'ver'
d = api(VERA, '/api/comunidad'); yo = d['yo']
luna = next(c for c in d['cuentas'] if c.get('alias') == 'Estudio Luna')
if que == 'ver':
    print('yo', yo, d.get('alias'), '· avisos', d.get('avisos'))
    for x in d['solicitudes']: print('  sol', x['id'], x['de'], '→', x['para'], x.get('pid'), x['estado'])
    for c in d['chats']: print('  chat', c['con'], 'sin leer', c['sin_leer'], '·', c['ultimo']['x'][:60])
elif que == 'acepta':
    for x in d['solicitudes']:
        if x['para'] == yo and x['estado'] == 'pendiente' and x['de'] == luna['cid']:
            print('acepta', x['id'], api(VERA, '/api/comunidad', {'accion': 'responder', 'id': x['id'], 'aceptar': True}))
elif que == 'pide':
    print(api(VERA, '/api/comunidad', {'accion': 'solicitar', 'para': luna['cid'], 'pid': luna['personajes'][0]['pid'], 'msg': 'Me encantaría hacer una sesión con Luna en la playa'}))
elif que == 'mensaje':
    print(api(VERA, '/api/comunidad', {'accion': 'mensaje', 'con': luna['cid'], 'texto': ' '.join(sys.argv[2:]) or '¡Hola! Aceptada. ¿Qué te apetece crear?'}))
elif que == 'limpia':   # deja a Vera sin colaboraciones vivas con Luna
    for x in d['solicitudes']:
        if luna['cid'] in (x['de'], x['para']) and x['estado'] in ('pendiente', 'aceptada'):
            print('termina', x['id'], api(VERA, '/api/comunidad', {'accion': 'terminar', 'id': x['id']}))
