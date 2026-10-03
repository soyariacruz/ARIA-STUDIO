"""ARIA STUDIO · servidor de desarrollo de la versión web (puerto 3000).

Sirve la carpeta `public/` (la que publica Vercel; se genera con publicar.py) y todo lo demás —/api, /assets, el catálogo—
se lo pasa al puente local (:8767), que tiene que estar arrancado. Solo escucha en este ordenador.
Cuando la web tenga su propio servidor, ese papel lo harán las funciones de Vercel y el almacén de Supabase.
"""
import os, sys, mimetypes, http.client, urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
SERVIDOR = 'servidor' in sys.argv   # `python3 web_dev.py 3000 servidor`: detrás no está el puente local sino el de varias cuentas (:8770), como en la web publicada
PUENTE = ('127.0.0.1', 8770 if SERVIDOR else 8767)
DEV_UID = next((a[4:] for a in sys.argv if a.startswith('dev=')), '')   # `dev=<uuid>`: pruebas sin login contra un puente arrancado con ARIA_DEV=1 (solo en este ordenador)
SIN_API = 'sin-api' in sys.argv   # `python3 web_dev.py 3000 sin-api`: /api responde 404, para ver la web como se ve publicada
PUBLIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'public')
HOSTS = (f'localhost:{PORT}', f'127.0.0.1:{PORT}')
SALTO = {'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization', 'te', 'trailers', 'transfer-encoding', 'upgrade'}


class H(BaseHTTPRequestHandler):
    def _err(self, code, msg):
        b = msg.encode('utf-8')
        self.send_response(code); self.send_header('Content-Type', 'text/plain; charset=utf-8'); self.send_header('Content-Length', str(len(b))); self.end_headers()
        if self.command != 'HEAD': self.wfile.write(b)

    def _public(self):   # un fichero de public/ (sin subcarpetas ni salirse de ella)
        if self.command == 'POST': return False
        name = urllib.parse.unquote(urllib.parse.urlparse(self.path).path).lstrip('/') or 'index.html'
        fp = os.path.realpath(os.path.join(PUBLIC, name))
        if os.path.dirname(fp) != os.path.realpath(PUBLIC) or not os.path.isfile(fp): return False
        b = open(fp, 'rb').read()
        ct = mimetypes.guess_type(fp)[0] or 'application/octet-stream'
        if ct.startswith('text/') or ct.endswith('javascript'): ct += '; charset=utf-8'
        self.send_response(200); self.send_header('Content-Type', ct); self.send_header('Content-Length', str(len(b))); self.send_header('Cache-Control', 'no-store'); self.end_headers()
        if self.command != 'HEAD': self.wfile.write(b)
        return True

    def _pasa(self):
        # la misma guarda que el puente: solo el propio navegador en localhost (ni otra web, ni un dominio que apunte a 127.0.0.1)
        if (self.headers.get('Host') or '').lower() not in HOSTS: return self._err(403, 'origen no permitido')
        origin = (self.headers.get('Origin') or '').lower()
        if origin and origin not in tuple('http://' + h for h in HOSTS): return self._err(403, 'origen no permitido')
        if self._public(): return
        if SIN_API and self.path.startswith('/api/'): return self._err(404, 'The page could not be found')   # como en Vercel mientras no haya funciones
        n = int(self.headers.get('Content-Length') or 0)
        body = self.rfile.read(n) if n else None
        hd = {k: v for k, v in self.headers.items() if k.lower() not in SALTO and k.lower() not in ('host', 'origin', 'referer')}
        hd['Host'] = f'{PUENTE[0]}:{PUENTE[1]}'
        if DEV_UID: hd['X-Dev-Uid'] = DEV_UID
        if origin: hd['Origin'] = origin if SERVIDOR else f'http://{PUENTE[0]}:{PUENTE[1]}'   # el puente local solo acepta su propio origen; el de varias cuentas, los de su lista
        c = http.client.HTTPConnection(*PUENTE, timeout=600)
        try:
            c.request(self.command, self.path, body=body, headers=hd)
            r = c.getresponse()
        except OSError:
            c.close()
            return self._err(502, 'El puente no está arrancado (puerto 8767).')
        try:
            self.send_response(r.status)
            for k, v in r.getheaders():
                if k.lower() not in SALTO and k.lower() not in ('server', 'date'): self.send_header(k, v)
            self.end_headers()
            while True:
                b = r.read(65536)
                if not b: break
                self.wfile.write(b)
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            c.close()

    do_GET = do_POST = do_HEAD = _pasa

    def log_request(self, code='-', size='-'):
        pass   # solo se escriben los errores


if __name__ == '__main__':
    print(f'ARIA STUDIO web (desarrollo) en http://localhost:{PORT} → public/ + puente {PUENTE[0]}:{PUENTE[1]}', flush=True)
    ThreadingHTTPServer(('127.0.0.1', PORT), H).serve_forever()
