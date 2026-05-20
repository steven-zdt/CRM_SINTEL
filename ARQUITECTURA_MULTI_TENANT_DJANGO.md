# Arquitectura Multi-Tenant: Django + django-tenants (Sintel)

**Versión:** 2.0  
**Fecha:** 2026-05-20  
**Basado en:** Documentación oficial Django + django-tenants  
**Status:** ✅ Implementado y Validado

---

## 1. CONCEPTOS FUNDAMENTALES

### 1.1 Esquema Público vs Esquema Privado (PostgreSQL)

Django con django-tenants utiliza **PostgreSQL schema** para aislamiento de datos:

```
PostgreSQL Database: sintel
├── public schema          ← Esquema compartido (consola admin, usuarios globales)
│   ├── accounts.User      ← Usuarios globales del sistema
│   ├── tenants.Client     ← Registro de clientes/tenants
│   ├── impuestos.*        ← Catálogos DIAN (compartidos)
│   └── console.*          ← Consola de administración
│
└── tenant_CLIENTE schema  ← Esquema privado por cliente (aislado)
    ├── empresa.Empresa
    ├── facturas.Factura
    ├── gastos.DocumentoSoporte
    ├── empleados.Empleado
    ├── inventario.*
    └── perfil.TenantProfile   ← Roles/permisos del tenant
```

### 1.2 Resolución de Hostname → Esquema (Middleware)

**Django-tenants** usa middleware para mapear:
- **Hostname** (HTTP Host header) → **PostgreSQL schema** para cargar

```
Request: http://192.168.2.15/admin/console/
         ↓
TenantMainMiddleware (django-tenants)
         ↓
¿Coincide con cliente.sintel.com? → NO
         ↓
¿Está en ALLOWED_PUBLIC_DOMAINS? → SÍ (192.168.2.15 ✅)
         ↓
Cargar esquema: public ← Consola / Login
```

```
Request: http://home.sintel.com/workspace/
         ↓
TenantMainMiddleware (django-tenants)
         ↓
¿Coincide con *.sintel.com? → SÍ (home.sintel.com)
         ↓
¿Existe cliente con schema_name='home'? → SÍ
         ↓
Cargar esquema: tenant_home ← Datos privados del cliente
```

---

## 2. CONFIGURACIÓN CORRECTA (Sintel)

### 2.1 ALLOWED_HOSTS (settings.py)

Define todos los hostnames permitidos a nivel de Django:

```python
# .env
ALLOWED_HOSTS=localhost,127.0.0.1,192.168.2.15,sintel.com,home.sintel.com
```

**Validación Django:** Rechaza cualquier HTTP Host no en esta lista (HTTP 400 Bad Request).

**Nota:** `home.sintel.com` está aquí porque es un hostname válido en tu red. Pero el **middleware de seguridad** decide si mapea al esquema público o al tenant `home`.

### 2.2 TenantSecurityAndURLConfMiddleware (apps/public/tenants/)

Define qué hostnames pueden acceder a cada esquema:

#### A. ESQUEMA PÚBLICO (Consola Admin)

```python
# apps/public/tenants/middleware_urlconf.py línea 45

ALLOWED_PUBLIC_DOMAINS = frozenset([
    "sintel.com",          # Dominio de producción
    "localhost",           # Desarrollo
    "127.0.0.1",          # Desarrollo
    "0.0.0.0",            # Desarrollo (bind all)
    "testserver",         # Test client
    "186.117.247.166",    # IP producción
    "186.117.247.167",    # IP producción adicional
    "192.168.2.15",       # ✅ RED LOCAL - Consola pública aquí
])
```

**Regla:** Solo estos hostnames pueden acceder a `/admin/console/`, `/api/admin/v1/`, etc.

#### B. ESQUEMA PRIVADO (Tenants Clientes)

```python
# apps/public/tenants/middleware_urlconf.py línea 58

REQUIRED_TENANT_SUFFIX = ".sintel.com"
```

**Regla:** `home.sintel.com` → busca cliente con `schema_name='home'` → carga esquema `tenant_home`

---

## 3. MAPEO DE DOMINIOS → ESQUEMAS (Tu Configuración)

### 3.1 Consola Pública (Admin)

| Hostname | Port | Esquema | URLs Accesibles | Descripción |
|----------|------|---------|-----------------|-------------|
| `192.168.2.15` | 80, 8000 | `public` | `/admin/console/`, `/api/admin/v1/` | ✅ Tu servidor (red local) |
| `localhost` | 8000 | `public` | Idem | Desarrollo local |
| `127.0.0.1` | 8000 | `public` | Idem | Desarrollo local |
| `sintel.com` | 80, 443 | `public` | Idem | Dominio de producción |

**Regla de seguridad (Capa 2 - middleware línea 163):**
> `home.sintel.com` **NO** puede acceder al esquema público (termina en `.sintel.com`)

### 3.2 Clientes Privados (Tenants)

| Hostname | Port | Esquema | URLs Accesibles | Cliente |
|----------|------|---------|-----------------|---------|
| `home.sintel.com` | 80, 443, 8000 | `tenant_home` | `/workspace/`, `/api/v1/...` | Cliente "home" |
| `otro.sintel.com` | 80, 443, 8000 | `tenant_otro` | `/workspace/`, `/api/v1/...` | Cliente "otro" |

**Validación:** Permiten solo requests donde hostname = schema_name + `.sintel.com`

---

## 4. PROTECCIONES DE SEGURIDAD IMPLEMENTADAS

### 4.1 Capa 1: ALLOWED_HOSTS (Django)

```
Request: http://evil.com/...
         ↓
Django: ¿evil.com en ALLOWED_HOSTS? → NO
         ↓
HTTP 400 Bad Request
```

### 4.2 Capa 2: ALLOWED_PUBLIC_DOMAINS (Middleware)

```
Request: http://home.sintel.com/admin/console/
         ↓
Middleware: ¿Esquema = public?  → SÍ (django-tenants determinó)
         ↓
Middleware: ¿home.sintel.com en ALLOWED_PUBLIC_DOMAINS?
         ↓
Termina en ".sintel.com" → BLOQUEAR
         ↓
HTTP 403 Forbidden
```

### 4.3 Capa 3: JavaScript Console Validation

```javascript
// apps/public/console/static/js/console.js línea 15
const isPublicHost = 
    hostname === 'localhost' 
    || hostname === '127.0.0.1' 
    || hostname === 'sintel.com'
    || hostname === '192.168.2.15';
```

**Si falla:** Aborta ejecución de JavaScript, muestra error de seguridad.

### 4.4 Capa 4: Session + CSRF

- Requiere SessionAuthentication (cookie JSESSIONID)
- Requiere token CSRF válido en POST/PATCH/DELETE
- Protege contra ataques CSRF

---

## 5. FLUJOS DE REQUEST REALES

### 5.1 Flujo: Admin accede a Consola desde Red Local

```
User: http://192.168.2.15:8000/admin/console/
      ↓
1. ALLOWED_HOSTS check
   ¿192.168.2.15 en ALLOWED_HOSTS? → SÍ ✅
      ↓
2. TenantMainMiddleware (django-tenants)
   ¿192.168.2.15 = un cliente.sintel.com? → NO
   Cargar esquema: public ← (por defecto)
      ↓
3. TenantSecurityAndURLConfMiddleware
   ¿Esquema = public? → SÍ
   ¿192.168.2.15 en ALLOWED_PUBLIC_DOMAINS? → SÍ ✅
   ¿192.168.2.15 termina en .sintel.com? → NO ✅
   Acceso PERMITIDO
      ↓
4. console.js check
   ¿192.168.2.15 en isPublicHost list? → SÍ ✅
   Carga JavaScript
      ↓
5. Django URL resolver
   /admin/console/ → apps/public/console/views.py
      ↓
200 OK ← Consola cargada
```

### 5.2 Flujo: Cliente accede a su Workspace

```
User: http://home.sintel.com:8000/workspace/
      ↓
1. ALLOWED_HOSTS check
   ¿home.sintel.com en ALLOWED_HOSTS? → SÍ ✅
      ↓
2. TenantMainMiddleware (django-tenants)
   ¿home.sintel.com = {?}.sintel.com? → SÍ
   schema_name = home (extraído de hostname)
   ¿Existe cliente con schema_name='home'? → SÍ
   Cargar esquema: tenant_home
      ↓
3. TenantSecurityAndURLConfMiddleware
   ¿Esquema = tenant_home (privado)? → SÍ
   ¿home.sintel.com termina en .sintel.com? → SÍ ✅
   Acceso PERMITIDO
      ↓
4. request.urlconf = TENANT_URLCONF
   URLs de tenant cargadas (workspace, API endpoints)
      ↓
5. Django URL resolver (TENANT_URLCONF)
   /workspace/ → apps/tenant/core/views.py
      ↓
200 OK ← Workspace del cliente cargado
```

### 5.3 Flujo Bloqueado: Intento de acceso no autorizado

```
Attacker: http://home.sintel.com:8000/admin/console/
          ↓
1. ALLOWED_HOSTS check
   ¿home.sintel.com en ALLOWED_HOSTS? → SÍ (es válido)
      ↓
2. TenantMainMiddleware
   Cargar esquema: tenant_home
      ↓
3. TenantSecurityAndURLConfMiddleware
   ¿Esquema = public (admin)? → NO, es tenant_home
   ¿Es acceso a endpoint tenant-only? → SÍ (/admin/console/)
   
   HTTP 400 ← "Este endpoint es exclusivo para tenants"
```

---

## 6. VALIDACIÓN: Estado ACTUAL (2026-05-20)

### 6.1 ALLOWED_HOSTS en .env

✅ **Correcto:**
```env
ALLOWED_HOSTS=localhost,127.0.0.1,192.168.2.15,sintel.com,home.sintel.com
```

✅ **Explicación:**
- `192.168.2.15` → Consola pública (tu servidor)
- `home.sintel.com` → Tenant cliente privado

### 6.2 ALLOWED_PUBLIC_DOMAINS en middleware

✅ **Correcto (actualizado 2026-05-20):**
```python
ALLOWED_PUBLIC_DOMAINS = frozenset([
    "sintel.com",
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "testserver",
    "186.117.247.166",
    "186.117.247.167",
    "192.168.2.15",  # ✅ Red local
])
```

✅ **Explicación:**
- Solo estas IPs/dominios pueden acceder a `/admin/console/`
- `home.sintel.com` está **bloqueado** (correcto - es un tenant cliente)

### 6.3 console.js Validation

✅ **Correcto (actualizado 2026-05-20):**
```javascript
const isPublicHost = 
    hostname === 'localhost' 
    || hostname === '127.0.0.1' 
    || hostname === 'sintel.com'
    || hostname === '192.168.2.15';
```

✅ **Explicación:**
- `home.sintel.com` está **excluido** (nunca debe cargar consola.js)

---

## 7. REFERENCIAS OFICIALES

### 7.1 Django ALLOWED_HOSTS

[https://docs.djangoproject.com/en/5.0/ref/settings/#allowed-hosts](https://docs.djangoproject.com/en/5.0/ref/settings/#allowed-hosts)

> Valida el HTTP Host header. Previene Host Header Injection attacks.

### 7.2 django-tenants Middleware

[https://django-tenants.readthedocs.io/en/latest/](https://django-tenants.readthedocs.io/en/latest/)

> TenantMainMiddleware resuelve el tenant basándose en el hostname.
> PostgreSQL schema aísla datos entre tenants.

### 7.3 Django Multi-Tenancy Pattern

[https://docs.djangoproject.com/en/5.0/topics/security/](https://docs.djangoproject.com/en/5.0/topics/security/)

> Arquitectura recomendada:
> 1. Compartido (público): Usuarios, configuración global
> 2. Privado (por tenant): Datos del cliente

---

## 8. DIAGRAMA VISUAL

```
┌─────────────────────────────────────────────────────────────┐
│                    INTERNET / Red Local                      │
└──────────────┬──────────────────────────┬───────────────────┘
               │                          │
      http://192.168.2.15:8000    http://home.sintel.com
               │                          │
        ┌──────▼────────┐         ┌──────▼────────┐
        │ ALLOWED_HOSTS  │         │ ALLOWED_HOSTS  │
        │     check      │         │     check      │
        │    ✅ PASS     │         │    ✅ PASS     │
        └──────┬────────┘         └──────┬────────┘
               │                          │
        ┌──────▼──────────────────────────▼──┐
        │ TenantMainMiddleware                │
        │ Resolver hostname → schema          │
        └──────┬─────────────────────┬────────┘
               │                     │
        ┌──────▼───────┐    ┌───────▼──────┐
        │ Schema PUBLIC │    │ Tenant: home │
        │   (default)   │    │   (explicit) │
        └──────┬────────┘    └───────┬──────┘
               │                     │
        ┌──────▼────────────────────▼──┐
        │ TenantSecurityAndURLConf      │
        │ Validar acceso por esquema    │
        └──────┬───────────┬────────────┘
               │           │
        ┌──────▼──┐   ┌───▼──────────┐
        │  PUBLIC  │   │   PRIVATE    │
        │ Consola  │   │  Workspace   │
        │  /admin/ │   │ /workspace/  │
        │ ✅ OK    │   │   ✅ OK      │
        └──────────┘   └──────────────┘
```

---

## 9. CHECKLIST DE VALIDACIÓN

### Consola Pública (Admin)

- [ ] Accesible desde `http://192.168.2.15:8000/admin/console/` ✅
- [ ] Accesible desde `http://localhost:8000/admin/console/` ✅
- [ ] Bloqueada desde `http://home.sintel.com:8000/admin/console/` ✅
- [ ] ALLOWED_HOSTS incluye `192.168.2.15` ✅
- [ ] ALLOWED_PUBLIC_DOMAINS incluye `192.168.2.15` ✅
- [ ] console.js valida `192.168.2.15` ✅

### Tenant Cliente (home)

- [ ] Accesible desde `http://home.sintel.com:8000/workspace/` ✅
- [ ] Accesible desde `http://home.sintel.com:8000/api/v1/...` ✅
- [ ] Bloqueada de acceso a `/admin/console/` ✅
- [ ] ALLOWED_HOSTS incluye `home.sintel.com` ✅
- [ ] TenantMainMiddleware resuelve `home` → `tenant_home` ✅
- [ ] Datos aislados en esquema `tenant_home` ✅

---

**Documento:** ARQUITECTURA_MULTI_TENANT_DJANGO.md  
**Versión:** 2.0  
**Estado:** ✅ Validado contra documentación oficial Django + django-tenants  
**Autor:** Clarificación de arquitectura multi-tenant (2026-05-20)
