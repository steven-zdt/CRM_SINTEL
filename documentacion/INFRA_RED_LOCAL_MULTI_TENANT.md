# Infraestructura Red Local — Acceso Multi-Tenant desde cualquier maquina

**Estado:** IMPLEMENTADO  
**Fecha:** 2026-06-15  
**Servidor:** `192.168.2.15` (Windows Server 2022 Datacenter)  
**Ultima revision:** Auditoria django-tenants v3.10.5 — 2026-06-15

---

## Objetivo

Que cualquier maquina conectada a la red local privada pueda acceder a los tenants de Sintel usando sus subdominios (`https://home.sintel.net.co`, `https://cliente.sintel.net.co`, etc.) sin ninguna configuracion adicional por maquina cliente.

---

## Arquitectura completa (todas las capas)

```
Maquina cliente (cualquier PC de la red)
        |
        |  DNS query: home.sintel.net.co ?
        v
+-------------------------------------+
|  Router (DHCP)                      |
|  DNS primario   → 192.168.2.15      |
|  DNS secundario → 8.8.8.8           |
+-------------------------------------+
        |
        |  DNS: 192.168.2.15  (wildcard *.sintel.net.co)
        v
+-------------------------------------+
|  192.168.2.15 — Windows Server 2022 |
|  ---------------------------------  |
|  Windows DNS Server                 |
|  Zona: sintel.net.co                   |
|    *   → 192.168.2.15               |
|    @   → 192.168.2.15               |
|    home, cliente, etc. → mismo IP   |
|  ---------------------------------  |
|  Windows Firewall (inbound abierto) |
|    TCP 80  ← 192.168.0.0/16         |
|    TCP 443 ← 192.168.0.0/16         |
|    ICMP    ← 192.168.0.0/16         |
|    Any     ← 192.168.2.15           |
+-------------------------------------+
        |
        |  HTTPS request → puerto 443
        v
+-------------------------------------+
|  Docker: nginx                      |
|  Escucha: 0.0.0.0:80 / 0.0.0.0:443 |
|  server_name _ (catch-all)          |
|  SSL cert: CN=*.sintel.net.co          |
|    SAN: *.sintel.net.co, sintel.net.co,   |
|         192.168.2.15, localhost     |
|  HTTP → 301 redirect → HTTPS        |
|  Proxy → web:8000                   |
+-------------------------------------+
        |
        |  proxy_pass http://web:8000
        v
+-------------------------------------+
|  Docker: web (Django/Gunicorn)      |
|  ALLOWED_HOSTS: ['.sintel.net.co', ...]|
|  CSRF_TRUSTED_ORIGINS:              |
|    ['https://.sintel.net.co', ...]     |
|  TENANT_DOMAIN_BASE: sintel.net.co     |
|  django-tenants middleware:         |
|    host → schema_name → DB schema   |
|                                     |
|  MIDDLEWARE (orden critico):        |
|    SecurityMiddleware               |
|    WhiteNoiseMiddleware             |
|    CorsMiddleware                   |
|    SessionMiddleware                |
|    ValidateALLOWED_HOSTSMiddleware  |
|    ForceNoPortMiddleware  ← normaliza HTTP_HOST
|    TenantMainMiddleware   ← resuelve tenant
|    SintelExceptionMiddleware        |
|    TenantSecurityMiddleware         |
|    ... resto del stack              |
+-------------------------------------+
        |
        |  queries al esquema aislado
        v
+-------------------------------------+
|  Docker: db (PostgreSQL 15)         |
|  Backend: django_tenants.           |
|           postgresql_backend        |
|  Router: TenantSyncRouter           |
|  Esquema public: SHARED_APPS        |
|  Esquema <tenant>: TENANT_APPS      |
+-------------------------------------+
```

---

## Estado de cada capa

| Capa | Componente | Configuracion clave | Estado |
|---|---|---|---|
| DNS | Windows DNS Server | Zona `sintel.net.co`, `* A 192.168.2.15` | OK |
| DNS distribucion | Router DHCP | DNS primario = `192.168.2.15` | OK |
| DNS contenedores | docker-compose dns | `192.168.2.15, 8.8.8.8` | OK |
| Firewall HTTP | Windows Firewall | TCP 80 inbound `192.168.0.0/16` | OK |
| Firewall HTTPS | Windows Firewall | TCP 443 inbound `192.168.0.0/16` | OK |
| Firewall ICMP | Windows Firewall | ICMPv4 type 8 `192.168.0.0/16` | OK |
| Firewall general | Windows Firewall | Any protocol `192.168.2.15` in/out | OK |
| Web server | Nginx (Docker) | Puerto 80 HTTP directo + Puerto 443 HTTPS | OK |
| SSL persistente | Docker volume `nginx_certs` | Cert sobrevive `docker compose build` | OK |
| SSL | Certificado auto-firmado | `CN=*.sintel.net.co`, SAN `*.sintel.net.co` | OK |
| App server | Django ALLOWED_HOSTS | `.sintel.net.co` (wildcard con punto inicial) | OK |
| App CSRF | Django CSRF_TRUSTED_ORIGINS | `https://.sintel.net.co` | OK |
| Multi-tenant | django-tenants | `TENANT_DOMAIN_BASE = sintel.net.co` | OK |
| Sessions tenant | django.contrib.sessions | En SHARED_APPS Y TENANT_APPS (auditoria) | OK |
| Middleware orden | ForceNoPortMiddleware | Normaliza puerto ANTES de TenantMainMiddleware | OK |

---

## Reglas de firewall creadas (persistentes)

```powershell
# Ping desde red local
New-NetFirewallRule -DisplayName "SINTEL - Permitir Ping ICMPv4 Entrada (Red Local)" `
    -Direction Inbound -Protocol ICMPv4 -IcmpType 8 `
    -RemoteAddress 192.168.0.0/16 -Action Allow -Enabled True -Profile Any

# HTTP
New-NetFirewallRule -DisplayName "SINTEL Web HTTP (80) - Red Local" `
    -Direction Inbound -Protocol TCP -LocalPort 80 `
    -RemoteAddress 192.168.0.0/16 -Action Allow -Enabled True -Profile Any

# HTTPS
New-NetFirewallRule -DisplayName "SINTEL Web HTTPS (443) - Red Local" `
    -Direction Inbound -Protocol TCP -LocalPort 443 `
    -RemoteAddress 192.168.0.0/16 -Action Allow -Enabled True -Profile Any

# Trafico general hacia/desde el servidor
New-NetFirewallRule -DisplayName "SINTEL Dev Server 192.168.2.15 - Entrada" `
    -Direction Inbound -RemoteAddress 192.168.2.15 -Action Allow -Protocol Any -Enabled True -Profile Any

New-NetFirewallRule -DisplayName "SINTEL Dev Server 192.168.2.15 - Salida" `
    -Direction Outbound -RemoteAddress 192.168.2.15 -Action Allow -Protocol Any -Enabled True -Profile Any
```

Verificar con:
```powershell
Get-NetFirewallRule | Where-Object { $_.DisplayName -like "*SINTEL*" } |
    Select-Object DisplayName, Direction, Action, Enabled | Format-Table -AutoSize
```

---

## Zona DNS sintel.net.co — registros actuales

| Hostname | Tipo | IP | Proposito |
|---|---|---|---|
| `@` | A | `192.168.2.15` | Raiz `sintel.net.co` → consola admin / onboarding |
| `*` | A | `192.168.2.15` | Wildcard — todos los subdominios |
| `home` | A | `192.168.2.15` | Tenant "home" (workspace empresa) |
| `cliente` | A | `192.168.2.15` | Tenant demo "cliente" |
| `empresademo` | A | `192.168.2.15` | Tenant demo "empresademo" |

> Los registros especificos (`home`, `cliente`, etc.) son redundantes con el wildcard `*`, pero se mantienen para claridad. Nuevos tenants funcionan automaticamente con el wildcard sin agregar registros DNS.

---

## Aprovisionamiento automatico de tenant (flujo completo — zero config)

El aprovisionamiento es completamente automatico en las 4 capas:

| Paso | Componente | Automatico? |
|---|---|---|
| Schema PostgreSQL | django-tenants `auto_create_schema=True` | auto |
| Domain record (DB) | `empresa_service._build_primary_domain()` → `<schema>.sintel.net.co` | auto |
| DNS externo | Wildcard `* A 192.168.2.15` en Windows DNS | auto (wildcard) |
| DNS interno (contenedores) | `dns: [192.168.2.15]` en docker-compose | auto (wildcard) |
| Nginx routing | `server_name _` catch-all | auto |
| SSL cert | Wildcard `*.sintel.net.co` ya cubre el subdominio | auto |
| Sessions aisladas | `django.contrib.sessions` en TENANT_APPS (auditoria 2026-06-15) | auto |

**Flujo estandar:**
1. Crear la empresa desde la consola: `https://sintel.net.co/console/`
2. El schema PostgreSQL se migra automaticamente (`auto_create_schema=True`)
3. El Domain record `nuevotenant.sintel.net.co` se crea en la DB
4. El wildcard DNS resuelve el subdominio — sin tocar Windows DNS Server
5. Nginx y Django aceptan la peticion sin cambios
6. La tarea Celery `provision_tenant_certificates_task` verifica cobertura wildcard (log "wildcard_covered")

**No se requiere ningun cambio en DNS, Nginx, Docker ni Django.**

---

## Verificacion desde una maquina cliente

```cmd
# 1. Confirmar que usa el DNS correcto
nslookup sintel.net.co
# Respuesta esperada: Address: 192.168.2.15

# 2. Probar un tenant arbitrario (wildcard)
nslookup cualquiernombre.sintel.net.co
# Respuesta esperada: Address: 192.168.2.15

# 3. Abrir en el navegador — usar HTTP para evitar advertencias de certificado
# http://sintel.net.co              → consola admin / onboarding
# http://home.sintel.net.co         → login tenant "home"
# http://cliente.sintel.net.co      → login tenant cliente
# https://...                    → mismas URLs con SSL (requiere cert instalado)
```

Si `nslookup` no devuelve `192.168.2.15`, verificar:
- Que el router tenga DNS primario = `192.168.2.15`
- Ejecutar `ipconfig /release && ipconfig /renew` en la maquina cliente

---

## Certificado SSL — Persistencia entre rebuilds

El cert vive en el volumen Docker `crm_sintel_nginx_certs`. El entrypoint del contenedor nginx solo genera el cert si no existe:

```
Primera vez:     docker compose build nginx → imagen sin cert
                 docker compose up nginx → entrypoint genera cert → guarda en volumen
Rebuild:         docker compose build nginx → imagen sin cert
                 docker compose up nginx → entrypoint lee cert del volumen → mismo fingerprint
```

**Si necesitas forzar un nuevo cert** (cambio de IP, expiracion, etc.):
```powershell
docker compose down nginx
docker volume rm crm_sintel_nginx_certs
docker compose up -d nginx  # genera cert nuevo
# Redistribuir sintel.crt a los clientes
```

**Exportar el cert actual para instalar en clientes:**
```powershell
docker compose cp nginx:/etc/nginx/certs/sintel.crt C:\sintel.crt
```

---

## Certificado SSL auto-firmado — aceptar en clientes

El certificado es auto-firmado. La primera vez que un navegador accede a `*.sintel.net.co` desde una maquina cliente, mostrara advertencia de seguridad.

**Opciones para evitar la advertencia:**

### Opcion A — Aceptar excepcion en el navegador (rapido)
Clic en "Avanzado" → "Continuar a home.sintel.net.co (no seguro)"

### Opcion B — Instalar el certificado como confiable (permanente)
Exportar `sintel.crt` desde el servidor y en cada cliente:

```cmd
# Windows — instalar como CA de confianza
certutil -addstore "Root" sintel.crt

# O via MMC: certlm.msc → Entidades emisoras raiz de confianza → Importar
```

### Exportar el certificado desde el servidor
```powershell
docker compose cp nginx:/etc/nginx/certs/sintel.crt C:\sintel.crt
# Compartir sintel.crt via carpeta de red o USB
```

---

## Configuracion del router — referencia rapida

```
Router admin (tipicamente 192.168.2.1 o 192.168.1.1)
  → LAN / DHCP Settings
    → Primary DNS:   192.168.2.15
    → Secondary DNS: 8.8.8.8
  → Guardar / Aplicar
```

Tras guardar: en cada PC cliente ejecutar `ipconfig /renew` o reconectar la red.

---

## Notas de auditoria django-tenants — 2026-06-15

Cambios aplicados al stack que afectan esta infraestructura:

| Correccion | Archivo | Detalle |
|---|---|---|
| `sessions` en `TENANT_APPS` | `config/settings.py` | Evita session leaking entre esquema public y schemas tenant al navegar subdominios |
| Desviacion middleware documentada | `config/settings.py` | `ForceNoPortMiddleware` DEBE ir antes de `TenantMainMiddleware` para normalizar `HTTP_HOST` (ej: `sintel.net.co:8000` → `sintel.net.co`) |
| Duplicados `TENANT_MODEL` eliminados | `config/settings.py` | Una sola declaracion SSoT (linea 246) |
| `RelaxedJWTAuthentication` fix | `apps/tenant/api/base.py` | Captura solo `InvalidToken, TokenError` en DEBUG; no enmascara errores de red/infra |
| App `bancos` documentada | `documentacion/arquitectura_general.md` | 14 apps tenant activas (antes 13) |

**Impacto en red local:** La correccion de `sessions` en `TENANT_APPS` garantiza que una sesion iniciada en `sintel.net.co` (esquema public) y luego navegada a `home.sintel.net.co` (esquema tenant) no cause perdida de sesion ni cross-schema session leaking.

---

## Troubleshooting — "el navegador no conecta y no hay actividad en el log del contenedor" (2026-08-05)

**Sintoma:** `http://home.sintel.net.co:8000/` (o cualquier subdominio) no carga en el navegador,
y `docker compose logs web` no muestra NINGUNA linea nueva al recargar la pagina. Sin embargo,
probar el mismo request desde dentro del contenedor (`curl -H "Host: home.sintel.net.co" ...`) o
desde Windows contra `127.0.0.1:8000` con el header `Host` explicito SI funciona (200 OK).

**Diagnostico:** si no hay NINGUNA actividad en el log, la request nunca llego a Docker — el
problema esta 100% en la resolucion DNS del lado del cliente (navegador/SO), no en
nginx/Django/Docker. No pierdas tiempo revisando middleware, ALLOWED_HOSTS o el tenant en la
base de datos si el sintoma es "cero actividad en el log": eso siempre apunta a que el
`Host:` header nunca salio de la maquina cliente.

### Causa raiz mas comun: sintaxis invertida en el archivo hosts de Windows

El archivo `C:\Windows\System32\drivers\etc\hosts` mapea **IP → hostname**, NO
hostname → hostname. Un error facil de cometer (y que ya paso una vez en este proyecto) es
escribir:

```
# INCORRECTO — "localhost" no es una IP, Windows ignora silenciosamente esta linea
localhost       home.sintel.net.co
localhost       sintel.net.co
```

Windows no reporta ningun error al parsear una linea invalida como esta — simplemente la
ignora, y la resolucion cae de vuelta al DNS publico real (que para `home.sintel.net.co`
devuelve `NXDOMAIN`, ya que el wildcard de Cloudflare/DNS publico documentado mas arriba en
este archivo aun no esta activo en el entorno de desarrollo actual). El sintoma exacto es
`Invoke-WebRequest`/el navegador reportando "no se puede resolver el nombre remoto".

**Formato correcto** (IP primero, hostname despues):

```
127.0.0.1	sintel.net.co
127.0.0.1	home.sintel.net.co
127.0.0.1	cliente.sintel.net.co
```

Tras corregir: `ipconfig /flushdns` y volver a probar.

### IP del servidor local: verificar, no asumir

Este documento (y varios archivos de config: `.env`, `docker-compose.yaml` `extra_hosts`,
`config/settings.py` `ALLOWED_HOSTS`/`_dev_hosts`, `ensure_tenant_dns.py` `SERVER_IP` default)
asumen `192.168.2.15` como IP fija del servidor de desarrollo. **Esta IP puede quedar
desactualizada** si el DHCP de la red reasigna una IP distinta a la maquina (confirmado en esta
sesion: la IP real de la interfaz Ethernet resulto ser `192.168.2.200`, no `.15`). Antes de
depurar problemas de conectividad de red asumiendo que `192.168.2.15` es correcta, verificar
con:

```powershell
Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" }
```

Si la IP real difiere de `192.168.2.15` en los archivos de configuracion, actualizarla en todos
los lugares listados arriba (no solo uno) para evitar inconsistencias entre lo que resuelve el
navegador del cliente y lo que usan los contenedores internamente.

### Alternativa mas simple para una sola maquina de desarrollo: hosts file en vez de Windows DNS Server

Todo lo demas en este documento (Windows DNS Server, wildcard `* A 192.168.2.15`, DHCP
distribuyendo ese DNS a toda la red) es la configuracion completa para que **cualquier maquina
de la red local** acceda a los tenants sin configuracion individual. Si solo estas
desarrollando desde una unica maquina (sin necesidad de que otras PCs de la red accedan), es
mas simple usar el archivo hosts local de esa maquina (formato de arriba) apuntando a
`127.0.0.1` — evita depender de un DNS Server separado y de que la IP del servidor se mantenga
estable. Es el enfoque usado en esta sesion de troubleshooting.

---

## Relacion con otras configuraciones

- **ADR-002** (`docs/ADR-002-public-schema-api-dual-registration.md`): los endpoints llamados desde paginas estaticas en `home.sintel.net.co` deben estar registrados tanto en `urls_public.py` como en `urls_tenant.py`.
- **CONSOLA_ADMIN_LOCALHOST_SETUP.md**: guia original de configuracion de la consola en IP local.
- **ARQUITECTURA_MULTI_TENANT_DJANGO.md**: capas de seguridad del sistema multi-tenant.
- **arquitectura_general.md** v3.10.5: inventario de apps actualizado con `bancos` (14 apps tenant).
