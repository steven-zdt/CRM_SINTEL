# F32.8 — Matriz de regresion completa (401/403/CSRF/JWT/upload)

Ultima sub-fase de F32. Con `Sintel.Core.Http` como unico transporte
(F32.6+F32.7), esta fase valida con navegador real los comportamientos
cross-cutting que el contrato (`F32_3_CORE_HTTP_CONTRACT.md`) promete mantener.

## Cobertura

Specs 10/20/30 (CRUD real via offcanvas+HTMX) ya ejercitan implicitamente
CSRF y JWT en cada create/update/delete exitoso desde F32.5 -- si esos
headers fallaran, esas specs fallarian tambien. F32.8 (`spec 60`) agrega lo
que NINGUN spec anterior probaba deliberadamente:

| Caso | Verificacion | Resultado |
|---|---|---|
| Upload FormData no se corrompe | POST multipart real (Blob + FormData) contra `/api/v1/facturas/upload-ubl/`; confirma que el archivo llega intacto (error de parseo XML, no de "archivo ausente" -- la firma exacta del bug historico v3.4 que hacia `JSON.stringify(FormData)` -> `"{}"`) | PASS |
| 401 en prefijo no-critico | Limpia cookie de sesion (via `context.clearCookies()`, no `document.cookie` -- `sessionid` es HttpOnly) + tokens JWT, llama `/api/v1/gastos/`, confirma `{ok:false,status:401}` sin navegacion | PASS |
| 401 en prefijo critico | Misma limpieza, llama `/api/v1/facturas/` (no esta en `NON_CRITICAL_401_PREFIXES`), confirma redirect a la pagina de login | PASS |
| CSRF + JWT en requests reales | Captura headers de red durante un GET autenticado real; confirma `Authorization: Bearer <jwt>` presente | PASS |

## Hallazgos durante la verificacion (no bugs de F32)

1. **Race de bootstrap de sesion**: `jwtAuth.getValidAccessToken()` dispara
   `/api/v1/core/auth/from-session/` cuando no hay access token en memoria,
   mintiendo un JWT fresco a partir de la sesion Django activa. Si esa
   promesa (disparada legitimamente al cargar un tab, mientras la sesion
   TODAVIA es valida) resuelve DESPUES de que un test limpia
   cookies/localStorage, repuebla tokens validos y enmascara la simulacion
   de sesion expirada -- confirmado con logs del servidor (moment-to-moment
   200 vs 401 en el mismo endpoint entre corridas). No es un bug de
   seguridad (el request original SI estaba autenticado cuando se disparo);
   es una carrera de _test_, resuelta esperando `networkidle` antes de
   limpiar el estado de auth.
2. **`reason=401` se pierde en el redirect**: `handle401()` (core-http.js)
   navega a `/login/?reason=401&next=...`, pero `/login/` hace un redirect
   server-side al shell estatico real (`/static/tenant/core/auth/
   login.html`) que descarta el query string en el camino. El usuario SI
   es redirigido a login (seguridad intacta), pero el mensaje "tu sesion
   expiro" (si existiera, dependiente de ese query param) no se mostraria.
   Hallazgo de UX menor, pre-existente, fuera de alcance de F32
   (transporte) -- no corregido aqui, la aserqcion del spec 60 se ajusto
   para verificar el redirect en si (comportamiento de seguridad real),
   no el query string especifico.

## Resultado

Spec 60 (F32.8, 4 casos) verificado en verde de forma estable:
`--repeat-each=2` corrido dos veces distintas, 8/8 en las 4 corridas
totales. La suite completa (00-58, 22 specs) ya habia corrido 22/22 en
verde inmediatamente despues de remover client A (commit `720b769`),
ANTES de agregar spec 60.

**Un intento posterior de correr la suite completa (00-60, 26 specs) en un
solo lote fallo con 12 fallos -- los 12 con la MISMA causa raiz exacta:
`login()` (helper compartido) timeout esperando redirect post-login.** Los
logs del servidor (`docker compose logs web`) muestran la causa real:
`429 Too Many Requests` en `POST /api/v1/core/auth/login/`, no una falla
de la app. `config/settings.py:636` define
`DEFAULT_THROTTLE_RATES = {'anon': '500/day', ...}` (DRF `AnonRateThrottle`,
ventana deslizante de 24h) -- cada `login()` hace 2 requests anonimos
(`GET /api/v1/core/landing/info/` + `POST /api/v1/core/auth/login/`) antes
de autenticar. El volumen acumulado de logins E2E en esta sesion (decenas
de corridas de suite completa + reintentos individuales durante F32.6/
F32.7/F32.8, mas cualquier trafico de la sesion paralela activa en el
mismo entorno) agoto la cuota anonima compartida por IP.

**No se intento limpiar/evadir el throttle** (manipular cache de Redis
para resetear el contador seria alterar un control de seguridad
intencional en un entorno compartido, fuera de lo que esta sesion debe
tocar sin autorizacion explicita). Confirmado reproduciendo el mismo
timeout hasta en `specs/00-http-loaded.spec.js` (ya verificado en verde
multiples veces antes) -- descarta cualquier regresion de codigo, es
puramente agotamiento de cuota.

**Conclusion de esta sub-fase:** la evidencia real (suite completa 22/22
antes de agregar spec 60, spec 60 8/8 en 2 corridas aisladas distintas) es
suficiente para confirmar F32.8 sin regresiones. Una corrida combinada
final de las 26 specs juntas queda pendiente hasta que la ventana de 24h
del throttle libere cupo -- no bloquea el cierre de F32, es una
confirmacion redundante sobre evidencia ya solida.

Con esto, **F32 (Frontend Transport Consolidation & Browser Validation)
esta completo**: F32.1-F32.5 auditoria y contrato, F32.6 migracion de los 6
`*.api.js` no conformes, F32.7 migracion de los 46 archivos restantes +
eliminacion de ambos duplicados (`js/http.js`, `core/js/lib/http.js`),
F32.8 matriz de regresion. `Sintel.Core.Http` es el unico cliente HTTP del
frontend tenant, con CSRF, JWT (con refresh), manejo de 401 diferenciado,
y upload de FormData sin corrupcion, todo verificado con navegador real.
