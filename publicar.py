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
# textos que solo son verdad en local
LOCAL_A_WEB = [('Las claves se guardan en tu ordenador y no salen de él.', 'Las claves se guardan en tu cuenta de ARIA STUDIO y solo se usan para tus generaciones.')]
for viejo, nuevo in LOCAL_A_WEB:
    assert app.count(viejo) == 1, viejo
    app = app.replace(viejo, nuevo)
html = s[:i] + s[j + len(b):]
assert '<script src="cuenta.js"></script>' in html and '<script src="catalog.js">' not in html

os.makedirs(OUT, exist_ok=True)
open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8').write(html)
open(os.path.join(OUT, 'app.js'), 'w', encoding='utf-8').write(app)
for m in MODS + ['cuenta.js']:
    shutil.copyfile(os.path.join(SRC, m), os.path.join(OUT, m))
for f in sorted(os.listdir(OUT)):
    print(f'{os.path.getsize(os.path.join(OUT, f)) // 1024:>6} KB  {f}')
