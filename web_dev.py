"""ARIA STUDIO · servidor de desarrollo de la versión web (puerto 3000).

Enseña la misma app que el puente (:8767) pero en «modo web»: con la portada y el login de Google (cuenta.js).
Todo lo que recibe se lo pasa al puente, que tiene que estar arrancado. Solo escucha en este ordenador.
Cuando la web esté en Vercel, este papel lo harán sus funciones; esto es solo para desarrollar.
"""
import sys, http.client
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
PUENTE = ('127.0.0.1', 8767)
HOSTS = (f'localhost:{PORT}', f'127.0.0.1:{PORT}')
SALTO = {'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization', 'te', 'trailers', 'transfer-encoding', 'upgrade'}


class H(BaseHTTPRequestHandler):
    def _err(self, code, msg):
        b = msg.encode('utf-8')
        self.send_response(code); self.send_header('Content-Type', 'text/plain; charset=utf-8'); self.send_header('Content-Length', str(len(b))); self.end_headers()
        if self.command != 'HEAD': self.wfile.write(b)

    def _pasa(self):
        # la misma guarda que el puente: solo el propio navegador en localhost (ni otra web, ni un dominio que apunte a 127.0.0.1)
        if (self.headers.get('Host') or '').lower() not in HOSTS: return self._err(403, 'origen no permitido')
        origin = (self.headers.get('Origin') or '').lower()
        if origin and origin not in tuple('http://' + h for h in HOSTS): return self._err(403, 'origen no permitido')
        n = int(self.headers.get('Content-Length') or 0)
        body = self.rfile.read(n) if n else None
        hd = {k: v for k, v in self.headers.items() if k.lower() not in SALTO and k.lower() not in ('host', 'origin', 'referer')}
        hd['Host'] = f'{PUENTE[0]}:{PUENTE[1]}'
        if origin: hd['Origin'] = f'http://{PUENTE[0]}:{PUENTE[1]}'
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
    print(f'ARIA STUDIO web (desarrollo) en http://localhost:{PORT} → puente {PUENTE[0]}:{PUENTE[1]}', flush=True)
    ThreadingHTTPServer(('127.0.0.1', PORT), H).serve_forever()
