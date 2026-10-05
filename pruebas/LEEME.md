# Pruebas del servidor (Comunidad y préstamo)

Se pasan contra el **servidor de pruebas** (`aria-servidor-dev`, puerto 8770), nunca contra el publicado.
Ninguna lanza una generación ni gasta saldo: las llamadas a `/api/generar` están hechas para fallar justo antes de enviarse al proveedor.

| Fichero | Qué comprueba |
| --- | --- |
| `prestamo_http.py` | Quién ve y usa qué: el avatar del personaje prestado sí, su ficha no; sin permiso, nada; con NSFW se rechaza; no se puede copiar a un personaje propio; ocultar corta el préstamo |
| `prestamo_avisos.py` | Aviso automático en el chat al aceptar una solicitud y al retirar un permiso |
| `prestamo_servidor.py` | Dentro del propio servidor (sin red): la puerta de rutas `assets/prestamo/…` y el contador de imágenes creadas |
| `privado.py` | «Oculto en la Comunidad» sobrevive a que la página guarde el personaje con una copia vieja |
| `carpetas.py` | Carpetas de Mis creaciones: crear, meter, sacar, renombrar, borrar; solo entran creaciones de la propia cuenta; otra cuenta ni las ve ni las toca |
| `como_vera.py` | Actuar como la segunda cuenta de prueba: `ver`, `acepta`, `pide`, `mensaje`, `limpia` |

Cuentas de prueba (solo existen en este ordenador): Luna `aaaaaaaa-…-0001` (con «Luna Demo» y «Nico Demo»), Vera `cccccccc-…-0001` (con «Vera Demo») y una cuenta sin nada `dddddddd-…-0199`.

Para que `prestamo_http.py` pase, Luna tiene que tener aceptada una colaboración con la cuenta de Vera (`como_vera.py acepta` después de pedirla desde la web de pruebas).
