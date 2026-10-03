"""ARIA STUDIO · copia de seguridad del servidor al NAS de Max.

Pide al servidor todo lo que las cuentas han creado o cambiado desde la última copia y lo guarda en el NAS,
con la misma forma que en el servidor (usuarios/<cuenta>/assets/…). Solo añade o actualiza: lo que un miembro
borre en la web se conserva aquí. Las claves de API viajan y se guardan cifradas (sin el secreto del servidor no sirven).

Necesita ~/.claude/aria-servidor.env con dos líneas:  ARIA_URL=https://…   y   ARIA_ADMIN=…  (la llave de administración)

Uso:  python3 copia.py            (pensado para una rutina diaria)
      python3 copia.py --env RUTA --destino CARPETA   (para pruebas)
"""
import os, sys, time, tarfile, urllib.request, urllib.error

DESTINO = '/Volumes/home/🗄 Work/CLAUDE/ARIA STUDIO · copias'


def arg(nombre, defecto):
    return sys.argv[sys.argv.index(nombre) + 1] if nombre in sys.argv else defecto


def main():
    envf, dest = os.path.expanduser(arg('--env', '~/.claude/aria-servidor.env')), arg('--destino', DESTINO)
    env = {}
    try:
        for ln in open(envf, encoding='utf-8'):
            if '=' in ln and not ln.lstrip().startswith('#'):
                k, v = ln.strip().split('=', 1); env[k.strip()] = v.strip().strip('"\'')
    except OSError:
        sys.exit(f'Falta {envf} (ARIA_URL y ARIA_ADMIN)')
    if not env.get('ARIA_URL') or not env.get('ARIA_ADMIN'): sys.exit(f'En {envf} faltan ARIA_URL o ARIA_ADMIN')
    if not os.path.isdir(os.path.dirname(dest)): sys.exit(f'No encuentro {os.path.dirname(dest)}: ¿está montado el NAS?')
    os.makedirs(dest, exist_ok=True)
    marca = os.path.join(dest, '.ultima')
    try: desde = open(marca).read().strip() or '0'
    except OSError: desde = '0'
    req = urllib.request.Request(env['ARIA_URL'].rstrip('/') + '/api/admin/copia?desde=' + desde, headers={'X-Admin': env['ARIA_ADMIN']})
    try:
        r = urllib.request.urlopen(req, timeout=600)
    except urllib.error.HTTPError as e:
        sys.exit(f'El servidor ha respondido {e.code}: revisa la dirección y la llave de administración')
    except OSError as e:
        sys.exit(f'No se ha podido conectar con el servidor: {e}')
    hasta, n, peso = r.headers.get('X-Copia-Hasta') or str(int(time.time())), 0, 0
    with tarfile.open(fileobj=r, mode='r|') as t:
        for m in t:
            if not m.isfile(): continue
            t.extract(m, dest, filter='data')   # 'data': ni rutas fuera de la carpeta, ni enlaces, ni permisos raros
            n += 1; peso += m.size
    open(marca, 'w').write(hasta)   # solo si todo ha ido bien: si se corta, la próxima vez se repite desde el mismo punto
    print(f'copia hecha: {n} ficheros ({peso / 1e6:.1f} MB) → {dest}')


if __name__ == '__main__':
    main()
