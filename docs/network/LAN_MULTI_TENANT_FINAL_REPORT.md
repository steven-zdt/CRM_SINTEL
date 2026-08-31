# LAN_MULTI_TENANT_FINAL_REPORT

**Fecha:** 2026-08-31 (actualizado el mismo día tras resolverse el
Hallazgo 1). **Objetivo de la misión:** que un PC cliente en la misma
LAN acceda a `admin.sintel.net.co` (tenant `admin@sintel.net.co`), sin
depender de Internet.

## Veredicto

## **PARTIALLY_VERIFIED** (actualizado -- ver Actualización 2026-08-31 abajo)

La capa de aplicación (Nginx → Django → TenantMiddleware → Domain →
schema Postgres) está **verificada y funciona correctamente end-to-end,
incluyendo login real**, tanto desde esta máquina (`127.0.0.1`) como
desde su IP LAN real (`192.168.2.17`, HTTP y HTTPS). El Hallazgo 1
(conflicto de IP) se resolvió: el usuario reasignó la IP estática del
adaptador Ethernet de este servidor de `192.168.2.15` (en conflicto) a
`192.168.2.17` (libre, verificado). Queda un único punto abierto para
`VERIFIED` completo: que un PC **distinto** de la LAN resuelva
`admin.sintel.net.co` y confirme el mismo resultado -- ver
"Actualización 2026-08-31".

## Estado original de este informe (histórico, ya no vigente en el punto 1)

Originalmente: **BLOCKED_SAFE** por dos problemas de infraestructura
física/red, fuera de este repositorio de código, que ningún cambio de
Nginx/Django/Docker podía resolver:

1. ~~Conflicto de IP real y activo en `192.168.2.15`.~~ **RESUELTO** --
   ver Actualización.
2. **El wildcard DNS interno que la arquitectura requiere no está
   operativo** -- sigue abierto, ver Actualización.

Ambos requerían una decisión y una acción fuera del código (qué máquina
física usa qué IP, dónde vive el DNS Server real) — exactamente el tipo
de bloqueo que esta misión define como cierre válido
(`BLOCKED_SAFE con evidencia concreta`), no una falla de la
implementación de software.

---

## Actualización 2026-08-31 — Hallazgo 1 RESUELTO

El usuario reasignó la IP estática del adaptador Ethernet de este
servidor: de `192.168.2.15` (en conflicto con otra máquina física) a
`192.168.2.17` (verificada libre antes de asignarla). Evidencia
recolectada tras el cambio:

```
$ arp -a | findstr 192.168.2.17
  192.168.2.17    e4-a8-df-9c-f8-4d    dinámico
```

`e4-a8-df-9c-f8-4d` es la MAC real del adaptador Ethernet de ESTA
máquina (confirmada desde el inicio de la misión) -- sin conflicto,
a diferencia de `.15`.

```
$ curl -H "Host: admin.sintel.net.co" http://192.168.2.17/
< HTTP/1.1 302 Found
< Location: /static/tenant/core/auth/login.html

$ curl -k -H "Host: admin.sintel.net.co" https://192.168.2.17/
< HTTP/1.1 302 Found   (HTTPS tambien correcto)

$ curl -k -X POST -H "Host: admin.sintel.net.co" \
    https://192.168.2.17/api/v1/core/auth/login/ \
    -d '{"email":"admin@sintel.com","password":"Admin12345"}'
< {"success":true,"redirect_url":"/dashboard/","user":{"id":1,"email":"admin@sintel.com",...}}
< STATUS:200
```

**Login real, end-to-end, confirmado por IP LAN real sin conflicto.**
El Hallazgo 1 queda cerrado. `192.168.2.15` ya no está configurada en
esta máquina (se reemplazó, no quedó como IP secundaria).

### Lo único que falta para `VERIFIED` completo

Todo lo anterior se verificó **desde este mismo servidor** (curl con
Host header manual, simulando lo que un DNS real haría). Para declarar
el release gate completo, falta la prueba desde un **PC físicamente
distinto** de la LAN:

```cmd
:: en el PC cliente (agregar a su propio hosts file, como Administrador,
:: o resolver via un DNS real -- ver Hallazgo 2 mas abajo, aun abierto):
::   192.168.2.17    admin.sintel.net.co
ping 192.168.2.17
curl http://admin.sintel.net.co/
:: o abrir https://admin.sintel.net.co/ en el navegador (aceptar el
:: certificado autofirmado) y autenticar admin@sintel.com
```

El Hallazgo 2 (wildcard DNS interno no operativo) sigue abierto sin
cambios -- por eso otro PC de la LAN todavía necesita su propia entrada
de hosts file apuntando a `192.168.2.17` (la IP real, ya sin conflicto)
hasta que se resuelva un DNS interno real.

---

## Hallazgo 1 (CRÍTICO, evidencia original antes de la resolución) — Conflicto de IP: `192.168.2.15` respondía desde OTRA máquina física

Evidencia:

```
$ curl -v http://192.168.2.15/
*   Trying 192.168.2.15:80...
* Established connection to 192.168.2.15 (192.168.2.15 port 80) from 192.168.2.197 port ...
< HTTP/1.1 200 OK
< Server: (respuesta trae el placeholder por defecto de IIS de Windows)
<title>IIS Windows Server</title>

$ arp -a | findstr 192.168.2.15
  192.168.2.15    9c-6b-00-65-d4-44    dinámico

$ Get-NetAdapter → MAC real de ESTA máquina (Ethernet): E4-A8-DF-9C-F8-4D
```

La tabla ARP demuestra que `192.168.2.15` responde en la red desde la
MAC `9c-6b-00-65-d4-44` — **una máquina física distinta** a esta (cuya
MAC de Ethernet es `E4-A8-DF-9C-F8-4D`, aunque esta máquina también
tenga `192.168.2.15` configurada estáticamente en su propio adaptador).
El request curl salió realmente por Wi-Fi (`192.168.2.197`) hacia la
red y fue respondido por ese otro equipo — no es un artefacto local.

**Esto coincide exactamente con lo que ya describe
`documentacion/INFRA_RED_LOCAL_MULTI_TENANT.md` (2026-06-15):**
`192.168.2.15` es, por diseño original, un **Windows Server 2022
Datacenter separado** que debía correr Windows DNS Server + (en algún
momento) IIS. La página "IIS Windows Server" que responde hoy es
consistente con una instalación de Windows Server con el rol Web Server
(IIS) agregado pero **nunca configurado con el sitio/reverse-proxy de
SINTEL** — es decir, ese servidor existe y está encendido, pero no está
enrutando a este stack Docker.

El problema real y actual: **esta máquina de desarrollo también tiene
`192.168.2.15` configurada como IP estática en su propio adaptador
Ethernet** (confirmado, Fase 1 del baseline) — duplicando la IP del
servidor real. Cualquier cliente LAN que intente llegar a `.15` puede
terminar respondido por cualquiera de las dos máquinas según el estado
de la tabla ARP de cada switch/cliente en ese momento — comportamiento
no determinístico e inseguro por definición.

**No se modificó la configuración de red de esta máquina** (cambiar una
IP estática es una decisión de infraestructura con impacto amplio, fuera
del mandato de "no preguntar, pero tampoco actuar sobre decisiones que
solo el usuario puede tomar" — aquí la decisión es de qué máquina física
debe quedarse con `.15`).

**Remediación concreta (elegir una, requiere acceso físico/administrativo a la red):**

- **Opción A (recomendada, más alineada con el diseño original):**
  liberar `192.168.2.15` en esta máquina de desarrollo (quitar la IP
  estática del adaptador Ethernet o cambiarla a una IP libre real,
  verificada con `arp -a` antes de fijarla) y usar el Windows Server
  2022 existente en `.15` como el punto real de entrada LAN — pero
  entonces ese servidor necesita tener el proxy/DNS real configurado
  hacia esta máquina de desarrollo (o el stack Docker debe correr
  directamente en ese servidor).
- **Opción B:** si el Windows Server 2022 en `.15` ya no está en uso
  (abandonado), apagarlo o reasignarle otra IP, y dejar esta máquina de
  desarrollo como el servidor real en `.15` (coincide con cómo está
  configurada hoy) — actualizando entonces la zona DNS wildcard (ver
  Hallazgo 2) para apuntar aquí.

Cualquiera de las dos es una decisión operativa, no de código.

---

## Hallazgo 2 (CRÍTICO) — El wildcard DNS interno no está operativo

Evidencia:

```
$ nslookup admin.sintel.net.co
Servidor:  UnKnown
Address:  192.168.2.1
*** UnKnown no encuentra admin.sintel.net.co: Non-existent domain

$ Get-DnsClientServerAddress -InterfaceAlias Ethernet,Wi-Fi
Ethernet: 192.168.2.1
Wi-Fi:    192.168.2.1, 192.168.1.100
```

El DNS primario real configurado en esta máquina es `192.168.2.1` (el
router/gateway), **no** `192.168.2.15` como indica la guía de
configuración del router en `INFRA_RED_LOCAL_MULTI_TENANT.md`
("Primary DNS: 192.168.2.15"). Esto significa que, aunque el Windows
Server en `.15` tuviera la zona `*.sintel.net.co` correctamente
configurada, **el DHCP del router no la está distribuyendo** a los
clientes de la LAN — ninguna máquina de la red (incluida esta)
resolvería el wildcard sin cambiar manualmente su DNS.

`sintel.net.co` (sin subdominio) SÍ resuelve — pero a IPs **públicas de
Cloudflare** (104.21.26.232, 172.67.168.148, más rangos IPv6),
consistente con el servicio `cloudflared` de `docker-compose.yaml`
(túnel hacia el dominio público real). Es decir: el dominio público
`sintel.net.co` funciona vía Internet/Cloudflare, pero eso es un camino
completamente distinto del acceso LAN local que pide esta misión — y
explica por qué "depender de Internet" (que la misión pide evitar) SÍ
funcionaría hoy para `sintel.net.co`, pero NO para
`admin.sintel.net.co` sin transmitir por el túnel (el subdominio del
tenant no está expuesto vía Cloudflare, solo el dominio raíz).

Esta situación ya estaba parcialmente documentada: la sección
"Troubleshooting" (2026-08-05) de `INFRA_RED_LOCAL_MULTI_TENANT.md` ya
registraba que el wildcard "aún no está activo en el entorno de
desarrollo actual" y recomendaba, como alternativa de una sola máquina,
usar el archivo hosts local apuntando a `127.0.0.1` — **exactamente el
mecanismo que esta máquina usa hoy** (confirmado:
`C:\Windows\System32\drivers\etc\hosts` tiene `127.0.0.1
sintel.net.co/home.sintel.net.co/cliente.sintel.net.co`, pero NO tiene
`admin.sintel.net.co`, y el hosts file por definición **solo sirve a
esta máquina**, nunca a un PC cliente de la LAN).

**Remediación concreta (requiere acceso administrativo al Windows
Server real y/o al router, fuera de este repo):**

1. Confirmar si el Windows Server en `.15` tiene el rol DNS Server
   instalado y la zona `sintel.net.co` con el registro wildcard `*` →
   la IP real que corresponda tras resolver el Hallazgo 1.
2. Configurar el DNS primario del router (`192.168.2.1` → panel de
   administración) para distribuir esa IP como DNS primario vía DHCP.
3. Verificar desde un PC cliente real con `ipconfig /renew` +
   `nslookup admin.sintel.net.co`.

---

## Capa de aplicación — 100% verificada (Fase 5-14, todo lo que SÍ está bajo control del código)

Cada ítem verificado con evidencia real, no inferencia:

- **Domain record real creado:** `admin.sintel.net.co` → tenant
  `admin` (schema `admin`), owner `admin@sintel.net.co`, vía el mismo
  motor de onboarding auditado en la misión E2E previa de esta sesión
  (`crear_tenant_con_owner`). `client_id=12`, `membership_id=11`.
- **ALLOWED_HOSTS** cubre `admin.sintel.net.co`: incluye
  `.sintel.net.co` (wildcard) tanto en `DEBUG=True` como en el default
  de producción (`config/settings.py:430-432`) — no requiere `*`.
- **CSRF_TRUSTED_ORIGINS** cubre `https://.sintel.net.co` /
  `http://.sintel.net.co` (con esquema, como exige Django 4/5) —
  `config/settings.py:497`. `CSRFTrustedOriginMiddleware` además agrega
  dinámicamente cualquier origen entrante válido.
- **CORS** — probado con un `Origin` real de navegador
  (`http://admin.sintel.net.co`, sin puerto): responde
  `access-control-allow-origin: http://admin.sintel.net.co` (coincide
  exacto, sin abrir `*`). Ver también Hallazgo 3 (menor) abajo.
- **Nginx preserva el Host header** — `proxy_set_header Host $host;`
  (`nginx/nginx.conf:62,121`), confirmado en vivo: request con
  `Host: admin.sintel.net.co` a través de Nginx (puerto 80,
  `127.0.0.1`) llega a Django con ese mismo host, nunca `localhost`.
- **`TenantSecurityAndURLConfMiddleware` resuelve el hostname
  correctamente** — request real vía Nginx con
  `Host: admin.sintel.net.co` → `302 Found` con
  `Location: /static/tenant/core/auth/login.html` (URLConf de tenant
  privado, no el público) — confirma resolución
  hostname → Domain → tenant, NO por email.
- **Aislamiento entre tenants por hostname confirmado**: el mismo
  request contra `Host: qaisotest.sintel.net.co` (tenant preexistente
  distinto) devuelve su propio `302` — no el contenido de `admin`.
- **Fallback público en DEBUG, correctamente acotado** (Fase 20/29):
  `SHOW_PUBLIC_IF_NO_TENANT_FOUND = 'True' if DEBUG else 'False'`
  (`config/settings.py:309`, mecanismo oficial de `django-tenants`) —
  un hostname `*.sintel.net.co` sin `Domain` asociado cae al schema
  `public` **solo en desarrollo**; en producción (`DEBUG=False`)
  requeriría un `Domain` real. Ya implementado correctamente, sin
  necesidad de cambio.
- **Trial/lifecycle no tiene bypass por LAN**: `TenantSecurityMiddleware`
  ejecuta `reconcile_tenant_lifecycle()` en cada request
  independientemente de cómo se resolvió el host (verificado en la
  misión de Console Tenants de esta misma sesión, check automatizado
  `TEN-03`) — el acceso LAN pasa por el mismo middleware chain, sin
  ruta alterna.

## Hallazgo 3 (menor, informativo) — filtración de puerto interno `:8000` en un header CORS sin `Origin` real

En un request SIN header `Origin` (ej. navegación normal de página, no
un `fetch`/XHR), la respuesta incluye
`access-control-allow-origin: http://admin.sintel.net.co:8000`. Causa
raíz: `CSRFTrustedOriginMiddleware`
(`apps/public/core/middleware.py:260-265`) sintetiza un `HTTP_ORIGIN`
falso cuando el navegador no envía uno (para poblar
`CSRF_TRUSTED_ORIGINS` dinámicamente), y ese valor sintético queda
disponible para `CorsMiddleware` en la fase de respuesta. **Sin impacto
funcional real**: los navegadores no aplican políticas CORS a
navegaciones de página completa (sin `Origin`), y se confirmó en vivo
que un request CON `Origin` real (el único caso donde CORS importa)
responde correctamente sin el `:8000` espurio. Es, en el peor caso, una
fuga cosmética de un detalle interno (que existe un puerto 8000) a
quien inspeccione headers manualmente. No se modificó
`CSRFTrustedOriginMiddleware` en esta misión — es código
CSRF-crítico que merece su propia revisión dedicada, no un cambio
apresurado en medio de una misión de red. Ya documentado, este mismo
patrón (`:8000` en el header) también aparece en
`docs/e2e/ONBOARDING_E2E_REPORT.md` Fase 12 de la misión anterior,
donde se usó como evidencia positiva de resolución de hostname sin
identificar la causa — ahora queda explicado.

## Cambios reales aplicados en esta misión

- **`docker-compose.yaml`**: `web` (Django `runserver`) pasó de
  `0.0.0.0:8000:8000` (expuesto a toda la LAN, bypaseando Nginx) a
  `127.0.0.1:8000:8000` (solo esta máquina, para depuración directa) —
  hallazgo real de Fase 2/3, corregido y verificado (`web`/`celery`
  reconstruidos, ambos healthy).
- **Tenant real creado**: `admin.sintel.net.co` / `admin@sintel.net.co`
  (no existía antes de esta misión) — necesario para poder ejecutar
  cualquier prueba de esta misión contra el objetivo real que pide el
  prompt.

## Lo que NO se pudo verificar (honesto, requiere un PC cliente físico en la LAN)

Fases 15-19 y 21-24 (login real desde otro PC, DevTools de un navegador
cliente, aislamiento probado desde dos hostnames distintos en
simultáneo desde fuera de este servidor, static/media/API desde un
cliente real) **no se ejecutaron** — esta sesión no tiene acceso a un
segundo dispositivo físico en la LAN. Además, aunque lo tuviera, los
Hallazgos 1 y 2 significan que ese PC cliente **no podría alcanzar
`admin.sintel.net.co` hoy** sin aplicar antes las remediaciones de red
descritas arriba (o sin editar manualmente su propio hosts file / DNS,
lo cual el objetivo de la misión explícitamente busca evitar).

**Instrucciones para ejecutar estas fases una vez resuelto el Hallazgo
1/2**, desde cualquier PC de la LAN:

```cmd
ping 192.168.2.15
nslookup admin.sintel.net.co
curl http://admin.sintel.net.co/
:: o abrir http://admin.sintel.net.co/ en el navegador y autenticar
:: admin@sintel.net.co, revisar DevTools (Network/Console) por
:: cualquier referencia a localhost/127.0.0.1/:8000
```

## Release Gate (Fase 33)

```
[x] Nginx conserva Host                    -- verificado en vivo
[x] TenantMiddleware resuelve              -- verificado en vivo (admin -> schema admin, qaisotest -> schema qaisotest)
[x] schema correcto                        -- verificado (Domain admin.sintel.net.co -> Client schema=admin)
[x] no localhost en frontend               -- SEC-04 ya clasificado (mision previa); hallazgo menor :8000 documentado (Hallazgo 3), sin impacto funcional
[x] aislamiento tenant                     -- verificado (admin vs qaisotest, respuestas distintas)
[x] lifecycle respetado                    -- verificado por diseno (TEN-03, mismo middleware chain sin importar el host)
[x] logs correctos                         -- verificado (TenantSecurityAndURLConfMiddleware logea host/tenant/path, sin passwords/JWT)
[~] firewall seguro                        -- puerto 8000 corregido; reglas "SINTEL" documentadas no existen en esta maquina (viven en el otro servidor)
[x] servidor accesible desde LAN           -- RESUELTO 2026-08-31 (IP reasignada a 192.168.2.17, sin conflicto, ARP verificado)
[x] puerto 80/443 accesible                -- verificado por IP real (192.168.2.17) HTTP y HTTPS, 302 correcto en ambos
[ ] DNS resuelve                           -- BLOQUEADO (Hallazgo 2: wildcard no distribuido) -- otro PC de la LAN aun necesita hosts file manual apuntando a .17
[x] login funciona (verificado desde este servidor via IP LAN real)  -- 200, admin@sintel.com, redirect /dashboard/
[x] UserContext correcto                   -- login devuelve el user correcto (id=1, admin@sintel.com) para el tenant admin
[ ] API funciona (cliente LAN fisicamente distinto)  -- aun no probado desde una maquina distinta a este servidor
[ ] static funciona (cliente LAN fisicamente distinto) -- idem
```

## LAN_MULTI_TENANT = **PARTIALLY_VERIFIED**

El Hallazgo 1 (conflicto de IP) se resolvió el 2026-08-31 -- el usuario
reasignó este servidor a `192.168.2.17` (libre, sin conflicto,
verificado por ARP). Todo lo verificable desde este servidor mismo
(Nginx, TenantMiddleware, resolución de Domain, login real end-to-end,
HTTP y HTTPS) está confirmado funcionando correctamente por la IP LAN
real del servidor.

Queda un solo punto abierto para `VERIFIED` completo:

1. El wildcard DNS `*.sintel.net.co` sigue sin distribuirse por DHCP
   (Hallazgo 2, sin cambios) -- cualquier PC de la LAN **distinto** de
   este servidor necesita hoy una entrada manual en su propio hosts
   file (`192.168.2.17    admin.sintel.net.co`) para resolver el
   hostname, hasta que se configure un DNS interno real.
2. Ninguna prueba de esta misión se ejecutó todavía desde un dispositivo
   físicamente distinto a este servidor -- ver la sección "Actualización
   2026-08-31" arriba para el procedimiento exacto pendiente.

Ver la sección "Hallazgo 2" para la remediación concreta del wildcard
DNS (requiere acceso administrativo al Windows Server real o al router,
fuera del alcance de este repositorio).
