"""ARIA STUDIO · todo el feedback en una hoja de cálculo, listo para analizarlo y decidir.

Junta el feedback de la web (la última copia del servidor, hecha con copia.py) y el de la app local,
transcribe las notas de voz y los audios adjuntos (Whisper, en este ordenador), saca el texto de los
adjuntos (PDF, texto, Word…) y lo deja todo en «Feedback ARIA STUDIO.xlsx», en la carpeta de las copias.
Las transcripciones se guardan para no repetirlas.

Uso (con el Python que trae openpyxl):
  python3 copia.py
  .claude/scripts/notion_rest/xlsenv/bin/python aria-studio-web/feedback_informe.py
"""
import json, os, subprocess, sys

COPIAS = '/Volumes/home/🗄 Work/CLAUDE/ARIA STUDIO · copias'
LOCAL = '/Volumes/home/🗄 Work/CLAUDE/Aria Mirror/assets/feedback'
CACHE = os.path.join(COPIAS, 'feedback_textos')
SALIDA = os.path.join(COPIAS, 'Feedback ARIA STUDIO.xlsx')
AUDIO = ('.m4a', '.mp3', '.wav', '.ogg', '.webm', '.aac', '.mp4', '.mov')
TEXTO = ('.txt', '.md', '.csv', '.json', '.log')
WORD = ('.doc', '.docx', '.rtf', '.html', '.htm', '.odt')
WHISPER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'feedback_whisper.py')

try:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
except ImportError:
    sys.exit('Hace falta openpyxl: ejecútalo con .claude/scripts/notion_rest/xlsenv/bin/python')


def lee_registro(fp, origen):
    out = []
    if not os.path.isfile(fp): return out
    for ln in open(fp, encoding='utf-8'):
        try: r = json.loads(ln)
        except ValueError: continue
        r['_origen'] = origen; out.append(r)
    return out


def ruta_real(r, rel):   # dónde está el fichero en este ordenador
    if r['_origen'] == 'web': return os.path.join(COPIAS, 'usuarios', r.get('uid') or '', rel)
    return os.path.join(os.path.dirname(os.path.dirname(LOCAL)), rel.split('assets/', 1)[-1]) if rel.startswith('assets/') else os.path.join(LOCAL, rel)


def texto_de(fp):   # el texto de un fichero (con caché); '' si no se puede
    if not os.path.isfile(fp): return '(no está en la copia: ejecuta antes copia.py)'
    os.makedirs(CACHE, exist_ok=True)
    c = os.path.join(CACHE, os.path.basename(fp) + '.txt')
    if os.path.isfile(c): return open(c, encoding='utf-8').read()
    ext = os.path.splitext(fp)[1].lower(); t = ''
    try:
        if ext in TEXTO: t = open(fp, encoding='utf-8', errors='replace').read()
        elif ext in AUDIO: t = subprocess.run(['/usr/bin/python3', WHISPER, fp], capture_output=True, text=True, timeout=1800).stdout.strip()
        elif ext == '.pdf':
            js = "ObjC.import('PDFKit'); var d = $.PDFDocument.alloc.initWithURL($.NSURL.fileURLWithPath(" + json.dumps(fp) + ")); d ? ObjC.unwrap(d.string) : ''"
            t = subprocess.run(['osascript', '-l', 'JavaScript', '-e', js], capture_output=True, text=True, timeout=120).stdout.strip()
        elif ext in WORD: t = subprocess.run(['textutil', '-convert', 'txt', '-stdout', fp], capture_output=True, text=True, timeout=120).stdout.strip()
        else: t = '(tipo de archivo sin lectura automática: ábrelo a mano)'
    except Exception as e: t = f'(no se pudo leer: {e})'
    if t and not t.startswith('('): open(c, 'w', encoding='utf-8').write(t)
    return t


filas = lee_registro(os.path.join(COPIAS, 'feedback.jsonl'), 'web') + lee_registro(os.path.join(LOCAL, 'feedback.jsonl'), 'local')
filas.sort(key=lambda r: r.get('t', ''), reverse=True)
wb = Workbook(); ws = wb.active; ws.title = 'Feedback'
CAB = ['Fecha', 'Quién', 'Dónde', 'Tipo', 'Vía', 'Comentario', 'Nota de voz (transcrita)', 'Adjuntos', 'Texto de los adjuntos', 'Contexto', 'Decisión', 'Estado']
ws.append(CAB)
for r in filas:
    voz = texto_de(ruta_real(r, r['audio'])) if r.get('audio') else ''
    adj = r.get('archivos') or []
    txt_adj = '\n\n'.join(f'— {os.path.basename(a)} —\n{texto_de(ruta_real(r, a))}' for a in adj)
    ws.append([r.get('t', ''), r.get('usuario', ''), r.get('seccion', ''), r.get('tipo', ''), r.get('via', ''), r.get('texto', ''), voz,
               '\n'.join(os.path.basename(a) for a in adj), txt_adj[:32000], r.get('contexto', ''), '', ''])
for c in ws[1]: c.font = Font(bold=True, color='FFFFFF'); c.fill = PatternFill('solid', fgColor='E91E63')
for col, w in zip('ABCDEFGHIJKL', (17, 26, 16, 16, 14, 60, 60, 26, 60, 50, 30, 14)): ws.column_dimensions[col].width = w
for fila in ws.iter_rows(min_row=2):
    for c in fila: c.alignment = Alignment(wrap_text=True, vertical='top')
ws.freeze_panes = 'A2'; ws.auto_filter.ref = ws.dimensions
wb.save(SALIDA)
print(f'{len(filas)} comentarios → {SALIDA}')
