"""ARIA STUDIO · apunta (o quita) un correo en la lista de miembros de Supabase.

  python3 alta.py correo@gmail.com            → miembro normal
  python3 alta.py correo@gmail.com --interno  → además ve «Workflows» (equipo)
  python3 alta.py correo@gmail.com --baja     → deja de tener acceso (sus datos no se borran)
  python3 alta.py                             → lista quién tiene acceso

La clave secreta se lee de ~/.claude/supabase.env; no se enseña. Además, mientras la app de Google esté en pruebas,
Max tiene que añadir el correo en Google Cloud → Audience → Test users.
"""
import os, re, sys, json, urllib.request, urllib.error, urllib.parse

SB = 'https://uhscbgidrloskdjbevkn.supabase.co'


def secreto():
    for ln in open(os.path.expanduser('~/.claude/supabase.env'), encoding='utf-8'):
        if ln.strip().startswith('SUPABASE_SECRET='): return ln.split('=', 1)[1].strip().strip('"\'')
    sys.exit('Falta SUPABASE_SECRET en ~/.claude/supabase.env')


def pide(method, path, body=None, extra=None):
    k = secreto(); h = {'apikey': k, 'Authorization': 'Bearer ' + k, 'Content-Type': 'application/json'}
    h.update(extra or {})
    req = urllib.request.Request(SB + path, data=json.dumps(body).encode() if body is not None else None, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=30) as r: return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


args = [a for a in sys.argv[1:] if not a.startswith('--')]
if args:
    email = args[0].strip().lower()
    if not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', email): sys.exit('Eso no parece un correo')
    if '--baja' in sys.argv:
        st, out = pide('DELETE', '/rest/v1/miembros?email=eq.' + urllib.parse.quote(email))
        print('baja:', email, '→', 'hecha' if st in (200, 204) else f'ERROR {st} {out[:200]}')
    else:
        st, out = pide('POST', '/rest/v1/miembros', {'email': email, 'interno': '--interno' in sys.argv}, {'Prefer': 'resolution=merge-duplicates,return=minimal'})
        print('alta:', email, '→', 'hecha' if st in (200, 201, 204) else f'ERROR {st} {out[:200]}')
st, out = pide('GET', '/rest/v1/miembros?select=email,interno,alta&order=alta')
if st == 200:
    for m in json.loads(out): print(f"  {m['email']}{'  · interno' if m['interno'] else ''}  · desde {m['alta'][:10]}")
else:
    print('no se pudo leer la lista:', st, out[:200])
