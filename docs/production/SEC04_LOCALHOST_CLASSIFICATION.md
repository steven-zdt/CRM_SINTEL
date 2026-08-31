# SEC-04 — Clasificación de ocurrencias de `localhost`/`127.0.0.1`

Fase 44 del plan de producción pedía clasificar individualmente cada
ocurrencia detectada por el check `SEC-04-localhost-leaks`, en vez de
dejarla como un WARN genérico sin revisar. Clasificación real ejecutada
2026-08-31 sobre las 65 ocurrencias detectadas en `apps/**/*.py` y
`apps/**/*.js` (excluyendo tests/migrations), leyendo el contexto real
de cada archivo — no por inferencia del nombre del archivo.

## Veredicto: **las 65 ocurrencias son legítimas**

Ninguna es una URL de desarrollo filtrada accidentalmente a un camino de
código que afecte producción. Se agrupan en 6 categorías:

### A — Fallback seguro vía `getattr(settings, ...)` (2 ocurrencias)

`apps/public/console/views.py:75,93`,
`apps/services/onboarding/empresa_service.py:608`

Patrón `getattr(settings, "TENANT_DOMAIN_BASE", "localhost")` — el
default solo se usa si el setting no está definido; en cualquier
entorno real, `TENANT_DOMAIN_BASE` está definido (`config/settings.py`,
vía `.env`). El check no los excluyó porque solo filtra líneas con
`getenv`/`os.environ` literal, no `getattr(settings,`.

### B — Comentarios y docstrings, sin efecto en runtime (~20 ocurrencias)

`apps/public/core/middleware.py:97,113,114`,
`apps/public/tenants/middleware_urlconf.py:11,105,168,169,192`,
`apps/public/tenants/api/viewsets.py:128`,
`apps/services/onboarding/empresa_service.py:28,35`,
`apps/public/impuestos/search/client.py:18`,
`apps/public/core/production_readiness/checks.py:139-168` (el propio
check, auto-referencial).

Texto explicativo o ejemplos de payload en docstrings. `client.py:18`
documenta el mismo default que ya implementa
`os.getenv("OPENSEARCH_HOST", "localhost")` en la línea 26 (correctamente
excluida por el check al contener `getenv`).

**Corregido de paso:** `viewsets.py:128` tenía un ejemplo de payload
desactualizado (`"owner_is_staff": true, # default: true`) que
contradecía el fix real de esta sesión (E2E-03, default cambiado a
`false`). Corregido a `false` con referencia a E2E-03.

### C — Código gateado por `settings.DEBUG`, inerte en producción (3 ocurrencias)

`apps/public/core/middleware.py:172,176,180`

Todo el bloque (líneas 171-183) vive dentro de `if settings.DEBUG:`
(confirmado leyendo el método completo, línea 154 y 171). Con
`DEBUG=False` (requisito ya exigido por `APP-01-debug`), esta rama
nunca se ejecuta — el header `Cross-Origin-Opener-Policy` permisivo
para `localhost`/`127.0.0.1` es exclusivamente de desarrollo.

### D — Whitelist de seguridad deliberada, en capas (8 ocurrencias)

`apps/public/tenants/middleware_urlconf.py:48,49,60,170,172,173,192,214`

`ALLOWED_PUBLIC_DOMAINS`/`DEV_DOMAIN_INDICATORS` son listas hardcodeadas
que SÍ incluyen `localhost`/`127.0.0.1` incondicionalmente (no
gateadas por `DEBUG`). Analizado en profundidad por ser el caso más
delicado: la validación llama `request.get_host()` (línea 99), que
**ya dispara la validación nativa de Django contra `ALLOWED_HOSTS`**
(env-configurable) antes de que este middleware compare contra su
propia whitelist — a diferencia de otro punto del código
(`middleware.py:177`) que sí lee `HTTP_HOST` directo de `META` para
evitar esa validación prematura por una razón distinta. Es decir: esta
whitelist es una **segunda capa de defensa**, no la única puerta.

Conclusión: **legítimo por diseño (defensa en profundidad, con logging
de seguridad explícito por capa)**, pero con una dependencia real: solo
es inofensivo si `ALLOWED_HOSTS` del entorno de destino EXCLUYE
`localhost`/`127.0.0.1` en producción real. Hoy, el `.env` de este
entorno (dev/pre-prod) SÍ los incluye — consistente con que `DEBUG=True`
sigue activo aquí (`APP-01-debug`, ya blocker). **No se modifica el
código de esta whitelist** — es el mismo tipo de decisión de
configuración de entorno de destino que `APP-01`/`APP-02`, no un bug de
código. Queda anotado aquí para que quien configure el `.env` de
producción real sepa que retirar `localhost`/`127.0.0.1` de
`ALLOWED_HOSTS` es lo que cierra esta capa por completo.

### E — Herramientas de desarrollo standalone (~28 ocurrencias)

`apps/public/tenants/management/commands/{create_public_tenant,
diagnostico_404,ensure_public_domain,ensure_public_domains,
ensure_tenant_dns,fix_dev_domains,setup_public_tenant,
show_tenant_hosts}.py`

Comandos de management diseñados explícitamente para inicializar/
diagnosticar un entorno de desarrollo local (nombres y `help=` lo dicen
literalmente). Nunca se invocan automáticamente en el camino de
servicio de requests — requieren ejecución manual deliberada por un
desarrollador. Que su default sea `localhost` es correcto para su
propósito, no una fuga.

### F — Health-check propio del framework de producción (1 ocurrencia)

`apps/public/core/production_readiness/checks.py:415`

`requests.get("http://localhost:8000/health")` — patrón estándar de
health-check ejecutado *desde dentro* del propio proceso/contenedor
(igual que un `HEALTHCHECK` de Docker), no una llamada externa. Correcto
sin importar el dominio público real del despliegue.

## Cambio en el check automatizado

`SEC-04-localhost-leaks` pasa de "WARN perpetuo sin salida posible" a
un check con **baseline**: 65 ocurrencias ya clasificadas y aceptadas
(2026-08-31). Si una corrida futura detecta **más** de 65, el check
señala explícitamente cuáles son nuevas (no reclasifica las 65 ya
conocidas) para revisión dirigida — evita tanto el falso PASS
permanente como el ruido de re-revisar lo mismo en cada corrida.
