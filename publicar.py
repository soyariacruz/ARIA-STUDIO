"""ARIA STUDIO · prepara la versión web a partir de la app local.

La app local (Aria Mirror, en el NAS) no se toca: de ella se GENERA la carpeta `public/`, que es lo que publica Vercel.
  · index.html  → el mismo, pero sin las etiquetas que cargan el catálogo y la app: eso lo hace cuenta.js tras el login.
  · app.js      → el script grande que en local va dentro de index.html.
  · el resto    → los módulos (.js) tal cual.
El catálogo (catalog.js, con los prompts) NO se copia aquí: va al almacén privado «catalogo» de Supabase.

Uso:  python3 publicar.py     (y después se sube con git)
"""
import os, shutil

SRC = '/Volumes/home/🗄 Work/CLAUDE/Aria Mirror'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'public')
MODS = ['feedback.js', 'personajes.js', 'complementos.js', 'fichas.js', 'fichas360.js']

s = open(os.path.join(SRC, 'index.html'), encoding='utf-8').read()
a = '<script src="catalog.js"></script>\n<script>\n'
b = '</script>\n' + '\n'.join(f'<script src="{m}"></script>' for m in MODS)
assert s.count(a) == 1 and s.count(b) == 1, (s.count(a), s.count(b))   # si cambia cómo carga la app en local, hay que revisar esto
i, j = s.index(a), s.index(b)
app = s[i + len(a):j]
# textos que solo son verdad en local (el puente, la carpeta, Notion): en la web dicen lo que pasa en la web.
# Cada uno tiene que seguir existiendo en la app local: si desaparece, el assert avisa para revisar la lista.
LOCAL_A_WEB = [
    ('Las claves se guardan en tu ordenador y no salen de él.', 'Las claves se guardan cifradas en tu cuenta de ARIA STUDIO y solo se usan para tus generaciones.'),
    ("'Hace falta el puente (python3 \"Aria Mirror/puente.py\")'", "'Conecta primero tu API'"),
    ("toast('Hace falta el puente')", "toast('Conecta primero tu API (arriba, «Conecta tu API»)')"),
    ('Puente apagado · abre «ARIA MIRROR.command»', 'Sin conexión con el servidor · recarga la página'),
    ('Sin el puente no hay generación ni Mis creaciones. Doble clic en ARIA MIRROR.command (carpeta Aria Mirror) y recarga.', 'No se ha podido conectar con el servidor de ARIA STUDIO. Recarga la página en un momento.'),
    ('Sin puente no se puede generar vídeo. Arranca <b>puente.py</b> y abre localhost:8767.', 'Para generar vídeo, conecta primero tu API.'),
    ("'sin respuesta del puente'", "'sin respuesta del servidor'"),
    ('el puente no encuentra esta petición', 'el servidor no encuentra esta petición'),
    ('Pégala en el puente y recarga. En la web pública será lo primero que se hace al entrar.', 'Conéctala arriba, en «Conecta tu API».'),
    ('falta la clave en ~/.claude/wavespeed.env', 'conecta tu clave en «Tus APIs»'),
    ('falta la clave en ~/.claude/byteplus.env', 'conecta tu clave en «Tus APIs»'),
    ('Se mueve a assets/papelera.', 'Deja de verse y se borra del todo a los 30 días.'),
    ('Se mueve a la papelera de la app y su ficha de Notion se archiva (se puede restaurar desde la papelera de Notion).', 'Deja de verse en tu Vestidor.'),
    ('Va a la papelera de la app.', 'Deja de verse y se borra del todo a los 30 días.'),
    ('Su carpeta pasa a la papelera de la app.', 'Deja de verse y se borra del todo a los 30 días.'),
    ('(Notion no respondió, se sube luego)', ''),
]
webs = {'app.js': app}
for m in MODS: webs[m] = open(os.path.join(SRC, m), encoding='utf-8').read()
for viejo, nuevo in LOCAL_A_WEB:
    assert sum(t.count(viejo) for t in webs.values()) >= 1, viejo
    for k in webs: webs[k] = webs[k].replace(viejo, nuevo)
html = s[:i] + s[j + len(b):]
assert '<script src="cuenta.js"></script>' in html and '<script src="catalog.js">' not in html

os.makedirs(OUT, exist_ok=True)
open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8').write(html)
for k, t in webs.items():
    open(os.path.join(OUT, k), 'w', encoding='utf-8').write(t)
shutil.copyfile(os.path.join(SRC, 'cuenta.js'), os.path.join(OUT, 'cuenta.js'))
# el servidor (Render) usa el mismo puente que la app local, arrancado con ARIA_SERVIDOR=1
SRV = os.path.join(os.path.dirname(OUT), 'servidor'); os.makedirs(SRV, exist_ok=True)
shutil.copyfile(os.path.join(SRC, 'puente.py'), os.path.join(SRV, 'puente.py'))
for f in sorted(os.listdir(OUT)):
    print(f'{os.path.getsize(os.path.join(OUT, f)) // 1024:>6} KB  {f}')
