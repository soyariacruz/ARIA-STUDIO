"""ARIA STUDIO · apunta (o quita) un correo en la lista de miembros de Supabase.

  python3 alta.py correo@gmail.com            → miembro normal
  python3 alta.py correo@gmail.com --interno  → además ve «Workflows» (equipo)
  python3 alta.py correo@gmail.com --baja     → deja de tener acceso (sus datos no se borran)
  python3 alta.py correo@gmail.com --precio 19 → lo que paga en Skool ($/mes; 296 = el anual): de ahí sale su saldo regalo de cada mes (sin esto, 4 $)
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


args = [a for i, a in enumerate(sys.argv[1:], 1) if not a.startswith('--') and sys.argv[i - 1] != '--precio']
if args:
    email = args[0].strip().lower()
    if not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', email): sys.exit('Eso no parece un correo')
    if '--baja' in sys.argv:
        st, out = pide('DELETE', '/rest/v1/miembros?email=eq.' + urllib.parse.quote(email))
        print('baja:', email, '→', 'hecha' if st in (200, 204) else f'ERROR {st} {out[:200]}')
    else:
        fila = {'email': email}
        if '--interno' in sys.argv: fila['interno'] = True
        if '--precio' in sys.argv:
            try: fila['precio'] = float(sys.argv[sys.argv.index('--precio') + 1].replace(',', '.'))
            except (IndexError, ValueError): sys.exit('Después de --precio va lo que paga en Skool, por ejemplo: --precio 19')
        st, out = pide('POST', '/rest/v1/miembros', fila, {'Prefer': 'resolution=merge-duplicates,return=minimal'})
        if st == 400 and 'precio' in out: sys.exit('Falta la columna «precio» en la tabla miembros de Supabase. En Supabase → SQL Editor:  alter table public.miembros add column if not exists precio numeric not null default 4;')
        print('alta:', email, '→', 'hecha' if st in (200, 201, 204) else f'ERROR {st} {out[:200]}')
st, out = pide('GET', '/rest/v1/miembros?select=*&order=alta')
if st == 200:
    for m in json.loads(out): print(f"  {m['email']}{'  · interno' if m['interno'] else ''}  · desde {m['alta'][:10]}" + (f"  · paga {m['precio']:g} $" if m.get('precio') is not None else ''))
else:
    print('no se pudo leer la lista:', st, out[:200])
