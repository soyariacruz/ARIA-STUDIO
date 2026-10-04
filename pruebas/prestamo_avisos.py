"""v202 · avisos automáticos del préstamo (servidor de pruebas): al aceptar, quien pidió recibe un mensaje y ya puede crear; al retirar el permiso, se le avisa y deja de poder."""
import json, urllib.request, urllib.error
B = 'http://127.0.0.1:8770'
LUNA = 'aaaaaaaa-0000-4000-8000-000000000001'; VERA = 'cccccccc-0000-4000-8000-000000000001'

def js(uid, ruta, body=None):
    r = urllib.request.Request(B + ruta, data=json.dumps(body).encode() if body is not None else None, headers={'X-Dev-Uid': uid, 'Content-Type': 'application/json'})
    try: return json.loads(urllib.request.urlopen(r, timeout=30).read())
    except urllib.error.HTTPError as e: return {'http': e.code, 'cuerpo': e.read().decode()[:200]}

def foto(uid, cid, pid):
    r = urllib.request.Request(f'{B}/assets/prestamo/{cid}/{pid}/foto.jpg', headers={'X-Dev-Uid': uid})
    try: return urllib.request.urlopen(r, timeout=30).status
    except urllib.error.HTTPError as e: return e.code

dV = js(VERA, '/api/comunidad'); dL = js(LUNA, '/api/comunidad'); cL = dL['yo']; cV = dV['yo']
print('Vera · avisos:', dV['avisos'], '· puede crear con:', [p['nombre'] for p in dV.get('prestados', [])])
ch = js(VERA, f'/api/comunidad/chat?con={cL}')['mensajes']
print('Vera · último mensaje de Luna:', next((m['x'] for m in reversed(ch) if m['de'] == cL), None))
print('Vera · avatar de Luna Demo:', foto(VERA, cL, 'luna-demo'), '· de Nico Demo (no pedido):', foto(VERA, cL, 'nico-demo'))
x = next(s for s in dL['solicitudes'] if s['de'] == cV and s['para'] == cL and s['estado'] == 'aceptada')
print('Luna retira el permiso:', js(LUNA, '/api/comunidad', {'accion': 'terminar', 'id': x['id']}).get('solicitud', {}).get('estado'))
dV = js(VERA, '/api/comunidad')
print('Vera · puede crear con:', [p['nombre'] for p in dV.get('prestados', [])], '· avatar de Luna Demo:', foto(VERA, cL, 'luna-demo'))
ch = js(VERA, f'/api/comunidad/chat?con={cL}')['mensajes']
print('Vera · último mensaje de Luna:', next((m['x'] for m in reversed(ch) if m['de'] == cL), None))
