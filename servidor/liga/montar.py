"""AI League — monta el carrusel de un duelo con la plantilla de Canva (deducida del Nº280 y de la portada/cierre de IG).

Uso:  python3 montar.py "<carpeta del duelo>"

La carpeta del duelo lleva:
  montaje.json (o duelo.json)  {"a": "FLUX 3", "b": "NANO BANANA PRO", "portada": "portada", "cierre": "cierre",
                                "tests": {"01": "De lejos", "02": "Contraluz", …}}
               (portada/cierre = qué imagen cruda va de fondo; tests = la etiqueta «TEST 1 · DE LEJOS» de arriba)
  crudas/      01_a.png, 01_b.png, 02_a.png, 02_b.png …   (a = izquierda, b = derecha; vertical)
               01_a y 01_b son SIEMPRE el mismo prompt (y las mismas referencias) con los dos modelos.
Sale en  carrusel/:  00_portada.jpg · 01.jpg … 18.jpg · 99_cierre.jpg   (formato Instagram 4:5)
Un carrusel de Instagram admite 20: portada + 18 comparativas + cierre.

ALTA RESOLUCIÓN (Max, 2 oct 2026): se monta a S × 1080 × 1350 (S = 2 → 2160 × 2700) para que cada mitad salga a
1080 px de ancho y nada se pixele al ampliar. Todas las medidas del diseño están en «píxeles de 1080» y pasan por u().
JPEG calidad 95 (un PNG a este tamaño pesa ~9 MB por diapositiva).
"""
import sys, os, json, glob, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

S = 2                                   # escala: 1 = 1080 × 1350 · 2 = 2160 × 2700
def u(v): return int(round(v * S))      # de «píxeles de 1080» a píxeles reales
W, H = u(1080), u(1350)
F = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fuentes')
AMARILLO = (252, 220, 88)
ROSA = (252, 100, 196)
BLANCO = (255, 255, 255)
MANO = 'Kalam-Bold.ttf'


def montserrat(size, peso='Bold'):      # size ya en píxeles reales (pasar u(…))
    f = ImageFont.truetype(os.path.join(F, 'Montserrat.ttf'), size)
    f.set_variation_by_name(peso)
    return f


def mano(size):
    return ImageFont.truetype(os.path.join(F, MANO), size)


def cubrir(im, w, h):
    """Recorta al centro para llenar w×h sin deformar (como «rellenar» en Canva)."""
    im = im.convert('RGB')
    r = max(w / im.width, h / im.height)
    im = im.resize((math.ceil(im.width * r), math.ceil(im.height * r)), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))


def texto(base, xy, t, fuente, color, ancla='ms', sombra=10, opac=150, grosor=0):
    """Texto con la sombra suave que pone Canva (sombra y grosor en «píxeles de 1080»)."""
    capa = Image.new('RGBA', base.size, (0, 0, 0, 0))
    ImageDraw.Draw(capa).text(xy, t, font=fuente, fill=(0, 0, 0, opac), anchor=ancla, stroke_width=u(grosor))
    capa = capa.filter(ImageFilter.GaussianBlur(u(sombra)))
    base.alpha_composite(capa)
    ImageDraw.Draw(base).text(xy, t, font=fuente, fill=color, anchor=ancla, stroke_width=u(grosor), stroke_fill=color)


def degradado(base, desde, alto, maxima=170, curva=1.4):
    """Negro que sube desde abajo y se funde con la imagen (sin que se note un bloque). desde/alto en píxeles reales."""
    capa = Image.new('RGBA', base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    for y in range(desde, min(desde + alto, base.height)):
        a = int(maxima * ((y - desde) / alto) ** curva)
        d.line([(0, y), (base.width, y)], fill=(0, 0, 0, a))
    base.alpha_composite(capa)


def degradado_arriba(base, alto, maxima=150, curva=1.3):
    """El mismo degradado, pero bajando desde el borde de arriba (para la etiqueta del test)."""
    capa = Image.new('RGBA', base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    for y in range(alto):
        d.line([(0, y), (base.width, y)], fill=(0, 0, 0, int(maxima * (1 - y / alto) ** curva)))
    base.alpha_composite(capa)


def etiqueta_test(lienzo, numero, nombre):
    """«TEST 3 · CONTRALUZ» arriba y pequeño: el número en amarillo, el test en blanco."""
    degradado_arriba(lienzo, H // 8)
    f = montserrat(u(26), 'ExtraBold')
    t1, t2 = f'TEST {numero}', f' · {nombre.upper()}'
    x0 = W / 2 - (f.getlength(t1) + f.getlength(t2)) / 2
    texto(lienzo, (x0, u(82)), t1, f, AMARILLO, ancla='ls')
    texto(lienzo, (x0 + f.getlength(t1), u(82)), t2, f, BLANCO, ancla='ls')


def comparativa(a, b, nombre_a, nombre_b, numero=None, test=None):
    lienzo = Image.new('RGBA', (W, H))
    lienzo.paste(cubrir(a, W // 2, H), (0, 0))
    lienzo.paste(cubrir(b, W // 2, H), (W // 2, 0))
    degradado(lienzo, H - H // 5, H // 5, 175, 1.2)   # un quinto: solo por debajo de los nombres
    for cx, nombre in ((W // 4, nombre_a), (3 * W // 4, nombre_b)):
        rotulo(lienzo, cx, u(1250), nombre, W // 2 - u(48), u(33), 'Bold', BLANCO, u(26), abajo=False)
    if test:
        etiqueta_test(lienzo, numero, test)
    return lienzo


def logo_vs(base, cx, cy):
    """«VS» en cursiva gruesa con el corte en diagonal, como en la portada."""
    capa = Image.new('RGBA', (u(520), u(420)), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    f = montserrat(u(118), 'Black')
    d.text((u(237), u(178)), 'V', font=f, fill=BLANCO, anchor='mm')   # V arriba y S más baja, montadas, como en Canva
    d.text((u(296), u(222)), 'S', font=f, fill=BLANCO, anchor='mm')
    capa = capa.transform(capa.size, Image.AFFINE, (1, 0.3, -u(60), 0, 1, 0), Image.BICUBIC)  # cursiva
    # el corte: diagonal larga de abajo-izquierda a arriba-derecha que separa las letras
    p0, p1 = (u(158), u(366)), (u(354), u(36))
    hueco = Image.new('L', capa.size, 0)
    ImageDraw.Draw(hueco).line([p0, p1], fill=255, width=u(12))
    capa.putalpha(Image.composite(Image.new('L', capa.size, 0), capa.getchannel('A'), hueco))
    # la cuchilla blanca, fina y afilada en las puntas
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    n = math.hypot(dx, dy)
    nx, ny = -dy / n * u(7), dx / n * u(7)
    mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
    ImageDraw.Draw(capa).polygon([p0, (mx + nx, my + ny), p1, (mx - nx, my - ny)], fill=BLANCO)
    sombra = Image.new('RGBA', capa.size, (0, 0, 0, 0))
    sombra.putalpha(capa.getchannel('A').point(lambda v: v * 0.55).filter(ImageFilter.GaussianBlur(u(12))))
    x, y = cx - capa.width // 2, cy - capa.height // 2
    base.alpha_composite(sombra, (x, y))
    base.alpha_composite(capa, (x, y))


def rotulo(lienzo, cx, y, nombre, hueco, tam, peso, color, tam_min, abajo=True):
    """Nombre centrado en cx (todo en píxeles reales). Si no cabe en «hueco», baja de tamaño y, en último caso, va en dos líneas.
    abajo=True: la segunda línea va debajo (portada); False: la primera sube (comparativas, pegadas al borde)."""
    nombre = nombre.upper()
    for size in range(tam, tam_min - 1, -1):
        f = montserrat(size, peso)
        if f.getlength(nombre) <= hueco:
            texto(lienzo, (cx, y), nombre, f, color)
            return
    palabras = nombre.split()
    corte = min(range(1, len(palabras)), key=lambda i: abs(len(' '.join(palabras[:i])) - len(' '.join(palabras[i:]))))
    lineas = [' '.join(palabras[:corte]), ' '.join(palabras[corte:])]
    size = tam
    while size > u(18) and max(montserrat(size, peso).getlength(l) for l in lineas) > hueco:
        size -= 1
    f, salto = montserrat(size, peso), int(size * 1.15)
    y0 = y - salto // 2 if abajo else y - salto
    texto(lienzo, (cx, y0), lineas[0], f, color)
    texto(lienzo, (cx, y0 + salto), lineas[1], f, color)


def nombre_lateral(lienzo, centro_x, nombre):
    """Nombre amarillo centrado en su lado del «VS» (el VS es el centro de la portada). centro_x en «píxeles de 1080».
    Un nombre corto, que tiene sitio de sobra, crece un pelín (hasta 44) para que se vea bien quién pelea;
    uno largo (NANO BANANA PRO) se queda en 38 o baja hasta caber (Max, 2 oct 2026)."""
    hueco = u(2 * min(centro_x - 24, 456 - centro_x) if centro_x < 540 else 2 * min(1056 - centro_x, centro_x - 624))
    for size in range(44, 38, -1):
        f = montserrat(u(size), 'ExtraBold')
        if f.getlength(nombre.upper()) <= 0.8 * hueco:
            texto(lienzo, (u(centro_x), u(1064)), nombre.upper(), f, AMARILLO)
            return
    rotulo(lienzo, u(centro_x), u(1064), nombre, hueco, u(38), 'ExtraBold', AMARILLO, u(30))


def flecha_deslizar(base, cx, cy, ancho=64):
    """Flechita blanca hacia la derecha, centrada: «desliza para ver más» (todo en «píxeles de 1080»)."""
    capa = Image.new('RGBA', base.size, (0, 0, 0, 0))
    x0, x1, y = u(cx - ancho // 2), u(cx + ancho // 2), u(cy)
    for color, off, blur in (((0, 0, 0, 140), u(2), True), ((255, 255, 255, 255), 0, False)):
        c = Image.new('RGBA', base.size, (0, 0, 0, 0)); dc = ImageDraw.Draw(c)
        dc.line([(x0, y + off), (x1, y + off)], fill=color, width=u(5))
        dc.line([(x1 - u(16), y - u(13) + off), (x1, y + off), (x1 - u(16), y + u(13) + off)], fill=color, width=u(5), joint='curve')
        if blur:
            c = c.filter(ImageFilter.GaussianBlur(u(4)))
        capa.alpha_composite(c)
    base.alpha_composite(capa)


def portada(fondo, nombre_a, nombre_b):
    lienzo = cubrir(fondo, W, H).convert('RGBA')
    degradado(lienzo, u(700), u(650), 190)
    logo_vs(lienzo, u(540), u(1035))
    nombre_lateral(lienzo, 240, nombre_a)   # el VS es el centro; cada nombre, centrado en su lado
    nombre_lateral(lienzo, 840, nombre_b)
    texto(lienzo, (u(540), u(1255)), 'VOTA TU FAVORITO', montserrat(u(25), 'ExtraBold'), BLANCO)
    flecha_deslizar(lienzo, 540, 1294)
    return lienzo


def logo_instagram(base, cx, cy, lado=88):
    """Contorno del logo de Instagram con su degradado (cx, cy, lado en «píxeles de 1080»)."""
    lado = u(lado)
    g = Image.new('RGBA', (lado, lado))
    for y in range(lado):
        for x in range(lado):
            t = (x + (lado - y)) / (2 * lado)
            c = [(254, 218, 117), (250, 126, 30), (214, 41, 118), (150, 47, 191), (79, 91, 213)]
            i = min(int(t * 4), 3)
            k = t * 4 - i
            g.putpixel((x, y), tuple(int(c[i][j] + (c[i + 1][j] - c[i][j]) * k) for j in range(3)) + (255,))
    m = Image.new('L', (lado, lado), 0)
    d = ImageDraw.Draw(m)
    s = lado / 88
    d.rounded_rectangle([4 * s, 4 * s, 84 * s, 84 * s], radius=24 * s, outline=255, width=int(8 * s))
    d.ellipse([24 * s, 24 * s, 64 * s, 64 * s], outline=255, width=int(8 * s))
    d.ellipse([60 * s, 17 * s, 71 * s, 28 * s], fill=255)
    g.putalpha(m)
    base.alpha_composite(g, (u(cx) - lado // 2, u(cy) - lado // 2))


def flecha(base, desde, hasta, color=AMARILLO):
    """Flecha curva amarilla dibujada a mano (del logo de IG hacia el @), en «píxeles de 1080»."""
    d = ImageDraw.Draw(base)
    (x0, y0), (x1, y1) = (u(desde[0]), u(desde[1])), (u(hasta[0]), u(hasta[1]))
    cx, cy = x0 + u(10), y1 + u(10)
    pts = []
    for i in range(41):
        t = i / 40
        x = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t ** 2 * x1
        y = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t ** 2 * y1
        pts.append((x, y))
    d.line(pts, fill=color, width=u(5), joint='curve')
    ang = math.atan2(pts[-1][1] - pts[-4][1], pts[-1][0] - pts[-4][0])
    for da in (2.5, -2.5):
        d.line([(x1, y1), (x1 + u(22) * math.cos(ang + da), y1 + u(22) * math.sin(ang + da))], fill=color, width=u(5))


def cierre(fondo):
    lienzo = cubrir(fondo, W, H).convert('RGBA')
    degradado(lienzo, H - H // 3 - u(60), H // 3 + u(60), 245, 0.7)   # un tercio desde abajo, para que se lea el texto
    def ajustar(t, ancho):  # el tamaño que ocupa lo mismo que en la plantilla de Canva
        return mano(round(100 * u(ancho) / mano(100).getlength(t)))
    f1 = ajustar('Comenta: ARIA', 510)
    f2 = ajustar('y te mando los prompts', 600)
    f3 = ajustar('en mi instagram: @soy_aria_cruz', 604)
    t1, t2 = 'Comenta: ', 'ARIA'
    x0 = u(540) - (f1.getlength(t1) + f1.getlength(t2)) / 2
    texto(lienzo, (x0, u(1040)), t1, f1, BLANCO, ancla='ls', sombra=12, grosor=1)
    texto(lienzo, (x0 + f1.getlength(t1), u(1040)), t2, f1, AMARILLO, ancla='ls', sombra=12, grosor=1)
    texto(lienzo, (u(532), u(1100)), 'y te mando los prompts', f2, BLANCO, sombra=12, grosor=1)
    t3, t4 = 'en mi instagram: ', '@soy_aria_cruz'
    x0 = u(522) - (f3.getlength(t3) + f3.getlength(t4)) / 2
    texto(lienzo, (x0, u(1152)), t3, f3, BLANCO, ancla='ls', sombra=10, grosor=0)
    texto(lienzo, (x0 + f3.getlength(t3), u(1152)), t4, f3, ROSA, ancla='ls', sombra=10, grosor=0)
    logo_instagram(lienzo, 911, 1020)
    flecha(lienzo, (912, 1085), (850, 1140))
    return lienzo


def guardar(im, ruta):
    im.convert('RGB').save(ruta, quality=95, subsampling=0, optimize=True)


def main(carpeta):
    # en los duelos de Aria Studio, duelo.json es el estado del duelo: la config del montaje va en montaje.json (la escribe liga.py montar)
    nombre = 'montaje.json' if os.path.isfile(os.path.join(carpeta, 'montaje.json')) else 'duelo.json'
    cfg = json.load(open(os.path.join(carpeta, nombre), encoding='utf-8'))
    crudas = os.path.join(carpeta, 'crudas')
    def cruda(clave):
        return Image.open(glob.glob(os.path.join(crudas, clave + '.*'))[0])
    salida = os.path.join(carpeta, 'carrusel')
    os.makedirs(salida, exist_ok=True)
    nums = sorted({os.path.basename(p).split('_')[0] for p in glob.glob(os.path.join(crudas, '*_a.*'))})
    guardar(portada(cruda(cfg['portada']), cfg['a'], cfg['b']), os.path.join(salida, '00_portada.jpg'))
    tests = cfg.get('tests', {})
    for n in nums:
        guardar(comparativa(cruda(n + '_a'), cruda(n + '_b'), cfg['a'], cfg['b'], int(n), tests.get(n)), os.path.join(salida, f'{n}.jpg'))
    guardar(cierre(cruda(cfg['cierre'])), os.path.join(salida, '99_cierre.jpg'))
    print(json.dumps({'ok': True, 'carpeta': salida, 'diapositivas': len(nums) + 2, 'tamaño': f'{W}×{H}'}, ensure_ascii=False))


if __name__ == '__main__':
    main(sys.argv[1])
