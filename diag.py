"""ARIA STUDIO · diagnóstico de Supabase: ¿existe la tabla de miembros, quién hay, y qué ve una cuenta sin permisos?
No enseña la clave secreta ni los correos enteros."""
import os, json, urllib.request, urllib.error

SB = 'https://uhscbgidrloskdjbevkn.supabase.co'
PUB = 'sb_publishable_GSO5Vqhr7Dg93egtKk_I2w_E_uScoNG'


def secreto():
    for ln in open(os.path.expanduser('~/.claude/supabase.env'), encoding='utf-8'):
        if ln.strip().startswith('SUPABASE_SECRET='): return ln.split('=', 1)[1].strip().strip('"\'')


def pide(path, key):
    req = urllib.request.Request(SB + path, headers={'apikey': key, 'Authorization': 'Bearer ' + key})
    try:
        with urllib.request.urlopen(req, timeout=30) as r: return r.status, r.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', 'replace')


def tapa(e):
    u, _, d = (e or '').partition('@')
    return (u[:2] + '…@' + d) if d else '?'


st, out = pide('/rest/v1/miembros?select=email,interno', secreto())
print('con la clave secreta:', st, end=' · ')
try:
    rows = json.loads(out)
    print([(tapa(r['email']), r['interno']) for r in rows] if isinstance(rows, list) else rows)
except ValueError:
    print(out[:300])
st, out = pide('/rest/v1/miembros?select=email', PUB)
print('con la clave pública (sin sesión):', st, '·', out[:300])
st, out = pide('/auth/v1/admin/users?per_page=20', secreto())
try:
    us = json.loads(out).get('users', [])
    print('cuentas que han entrado:', [tapa(u.get('email')) for u in us])
except ValueError:
    print('cuentas:', st, out[:200])
