# Consola Admin en Red Local (192.168.2.15) — Setup Completo

**Status:** ✅ FUNCIONANDO  
**Fecha:** 2026-05-20  
**Verificado:** Dashboard + Empresas + Usuarios cargando correctamente

---

## Problema Original

Consola admin en `http://192.168.2.15:8000/admin/console/` no cargaba tablas. Errores:
- ❌ Tablas vacías (sin datos)
- ❌ `jwtAuth is not defined` en console.js
- ❌ `tenants_manager.js` bloqueaba acceso a 192.168.2.15
- ❌ Django ALLOWED_HOSTS rechazaba 192.168.2.15

---

## Solución — 4 Capas de Configuración

### Capa 1: ALLOWED_HOSTS (Django)

**Archivo:** `.env`

```env
# ANTES (INCORRECTO)
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,sintel.com

# DESPUÉS (CORRECTO)
ALLOWED_HOSTS=localhost,127.0.0.1,192.168.2.15,sintel.com,home.sintel.com
```

**Por qué:** Django rechaza cualquier HTTP Host Header no en ALLOWED_HOSTS con error `Host no permitido`.  
**Verificar:** `curl -I -H "Host: 192.168.2.15" http://localhost:8000` debe devolver 200, no 400.

---

### Capa 2: ALLOWED_PUBLIC_DOMAINS (Middleware)

**Archivo:** `apps/public/tenants/middleware_urlconf.py` (línea ~54)

```python
# ANTES (INCORRECTO)
ALLOWED_PUBLIC_DOMAINS = frozenset([
    "sintel.com",
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "testserver",
    "186.117.247.166",
    "186.117.247.167",
])

# DESPUÉS (CORRECTO)
ALLOWED_PUBLIC_DOMAINS = frozenset([
    "sintel.com",
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "testserver",
    "186.117.247.166",
    "186.117.247.167",
    "192.168.2.15",  # ✅ AGREGAR AQUÍ
])
```

**Por qué:** Middleware TenantSecurityAndURLConfMiddleware valida que solo estos dominios accedan a `/admin/console/`.  
**Verificar:** Sin esto, recibes 403 Forbidden "No tienes acceso a este recurso".

---

### Capa 3: JavaScript Hostname Validation (console.js)

**Archivo:** `apps/public/console/static/js/console.js` (línea ~15)

```javascript
// ANTES (INCORRECTO)
const isPublicHost = 
    hostname === 'localhost' 
    || hostname === '127.0.0.1' 
    || hostname === 'sintel.com';

// DESPUÉS (CORRECTO)
const isPublicHost = 
    hostname === 'localhost' 
    || hostname === '127.0.0.1' 
    || hostname === 'sintel.com'
    || hostname === '192.168.2.15';  // ✅ AGREGAR AQUÍ
```

**Por qué:** Script de consola valida hostname en cliente antes de cargar módulos. Si falla, muestra error de seguridad.  
**Efecto:** Sin esto, console.js no ejecuta y tablas no cargan datos.

---

### Capa 4: tenants_manager.js Hostname Validation

**Archivo:** `apps/public/console/static/js/tenants_manager.js` (línea ~15)

```javascript
// ANTES (INCORRECTO)
const isPublicHost = 
    hostname === 'localhost' 
    || hostname === '127.0.0.1' 
    || hostname === 'sintel.com';

// DESPUÉS (CORRECTO)
const isPublicHost = 
    hostname === 'localhost' 
    || hostname === '127.0.0.1' 
    || hostname === 'sintel.com'
    || hostname === '192.168.2.15';  // ✅ AGREGAR AQUÍ
```

**Por qué:** Script de gestión de tenants bloquea con `throw new Error("Tenants Manager no debe cargarse...")` si detecta dominio de tenant.  
**Efecto:** Sin esto, consola bloquea acceso con error de seguridad en línea 163 (require_tenant_membership).

---

### Capa 5: Script Loading Order (base.html)

**Archivo:** `apps/public/console/templates/console/base.html` (línea 64-70)

```html
<!-- ANTES (INCORRECTO) -->
<script src="{% static 'js/console.js' %}"></script>
<script src="{% static 'js/jwt-auth.js' %}"></script>
<script src="{% static 'js/http.js' %}"></script>

<!-- DESPUÉS (CORRECTO) -->
<script src="{% static 'js/jwt-auth.js' %}"></script>
<script src="{% static 'js/http.js' %}"></script>
<script src="{% static 'js/console.js' %}"></script>
```

**Por qué:** console.js usa `window.jwtAuth` y `window.http`. Si jwt-auth.js se carga después, `jwtAuth is not defined` en console.js.  
**Efecto:** Sin esto, tablas no cargan (API calls fallan con jwtAuth undefined).

---

## Docker Port Binding

**Archivo:** `docker-compose.yaml` (línea ~27-28)

```yaml
# ANTES (INCORRECTO)
ports:
  - "80:8000"
  - "8000:8000"

# DESPUÉS (CORRECTO)
ports:
  - "0.0.0.0:80:8000"
  - "0.0.0.0:8000:8000"
```

**Por qué:** Sin `0.0.0.0`, Docker solo escucha en localhost, no en la IP de red.  
**Efecto:** Requests desde otra máquina en la red no alcanzan el contenedor.

---

## Checklist Final — Antes de Decir "Funciona"

```bash
# 1. Limpiar caché del navegador
# F12 → Application/Storage → Clear All
# O Ctrl+Shift+Delete (Full Clear)

# 2. Verificar Django config
curl -s http://192.168.2.15:8000/health
# Debe responder 200 OK

# 3. Verificar middleware valida 192.168.2.15
curl -I http://192.168.2.15:8000/admin/console/
# Debe responder 200 o 302 (login), nunca 400 o 403

# 4. Verificar scripts cargan en orden correcto
# F12 → Network → XHR/Fetch → orden debe ser:
#   1. jwt-auth.js
#   2. http.js
#   3. console.js
#   4. tenants_manager.js

# 5. Acceder a consola (con sesión activa)
http://192.168.2.15:8000/admin/console/

# 6. Verificar tablas cargan datos
# Dashboard → debe mostrar período actual
# Empresas → debe mostrar 2 empresas (home, cliente)
# Usuarios → debe mostrar 3+ usuarios
```

---

## Errores Comunes (y Soluciones)

### Error: "Host no permitido en /"
**Causa:** 192.168.2.15 no en ALLOWED_HOSTS  
**Solución:** Agregar a `.env` ALLOWED_HOSTS

### Error: "403 Forbidden - No tienes acceso a este recurso"
**Causa:** 192.168.2.15 no en ALLOWED_PUBLIC_DOMAINS  
**Solución:** Agregar a middleware_urlconf.py

### Error: "Tenants Manager no debe cargarse en dominios de tenant"
**Causa:** tenants_manager.js bloquea 192.168.2.15  
**Solución:** Agregar a isPublicHost en tenants_manager.js

### Error: "jwtAuth is not defined"
**Causa:** console.js carga antes que jwt-auth.js  
**Solución:** Reordenar scripts en base.html (jwt-auth ANTES que console)

### Tablas vacías (sin datos)
**Causa:** Combinación de arriba: scripts no cargan, o console.js no ejecuta  
**Solución:** Limpiar caché del navegador + verificar F12 Console sin errores

---

## Arquitectura: Cómo Funciona

```
Request: http://192.168.2.15:8000/admin/console/
         ↓
    ALLOWED_HOSTS check (Django)
    ¿192.168.2.15 en ALLOWED_HOSTS? → SÍ ✅
         ↓
    TenantMainMiddleware (django-tenants)
    ¿Es {tenant}.sintel.com? → NO
    Cargar esquema: public ✅
         ↓
    TenantSecurityAndURLConfMiddleware
    ¿192.168.2.15 en ALLOWED_PUBLIC_DOMAINS? → SÍ ✅
    ¿/admin/console/ es endpoint público? → SÍ ✅
    Acceso PERMITIDO
         ↓
    HTML + scripts cargan
    jwt-auth.js (define window.jwtAuth)
    http.js (define window.http)
    console.js (usa jwtAuth + http)
    tenants_manager.js (valida isPublicHost)
         ↓
    JavaScript valida hostname en cliente
    ¿192.168.2.15 en isPublicHost? → SÍ ✅
    Tablas cargan datos vía API
         ↓
    200 OK ← Consola funciona
```

---

## Archivos Modificados

| Archivo | Línea | Cambio |
|---------|-------|--------|
| `.env` | — | DJANGO_ALLOWED_HOSTS → ALLOWED_HOSTS, agregar 192.168.2.15 |
| `apps/public/tenants/middleware_urlconf.py` | 54 | Agregar 192.168.2.15 a ALLOWED_PUBLIC_DOMAINS |
| `apps/public/console/static/js/console.js` | 15 | Agregar 192.168.2.15 a isPublicHost |
| `apps/public/console/static/js/tenants_manager.js` | 15 | Agregar 192.168.2.15 a isPublicHost |
| `apps/public/console/templates/console/base.html` | 64-70 | Reordenar scripts: jwt-auth → http → console |
| `docker-compose.yaml` | 27-28 | Cambiar ports a 0.0.0.0:PUERTO:8000 |

---

## Lecciones Aprendidas

### 1. **Multi-Tenant Security Layers**
No es suficiente ALLOWED_HOSTS. Hay **4 capas**:
1. Django ALLOWED_HOSTS (global)
2. Middleware ALLOWED_PUBLIC_DOMAINS (por dominio)
3. JavaScript isPublicHost validations (cliente)
4. Session + CSRF tokens (API calls)

Todas deben alinearse. Una rotura en cualquiera → request bloqueada.

### 2. **Script Dependency Management**
JavaScript tiene dependencias implícitas:
- console.js **depende de** window.jwtAuth (de jwt-auth.js)
- console.js **depende de** window.http (de http.js)

Si cargan en orden equivocado → `undefined is not defined` silenciosamente (logs en F12).

### 3. **"Tablas vacías" es síntoma de múltiples causas**
No significa que "falte datos en BD". Significa:
- Scripts no cargaron
- API call falló con 403/500
- JavaScript error silencioso en F12

**Siempre:** Abrir F12 Console antes de reportar "no funciona".

### 4. **Docker Port Binding es Invisible**
Sin `0.0.0.0`, servidor **responde** a curl en localhost pero **rechaza** desde otra máquina.
No hay error visible; simplemente "connection refused".

---

## Testing Walkthrough

### Test 1: Acceso desde CLI
```bash
# Desde otra máquina en la red 192.168.2.x
curl -I http://192.168.2.15:8000/health
# Respuesta: 200 OK

curl -I http://192.168.2.15:8000/admin/console/
# Respuesta: 200 o 302 (login), nunca 4xx
```

### Test 2: F12 Developer Tools
```
F12 → Network tab
Recargar http://192.168.2.15:8000/admin/console/
Verificar:
  ✅ status 200 para /admin/console/ (HTML)
  ✅ status 200 para jwt-auth.js, http.js, console.js
  ✅ NO errores en Console tab (rojo = problema)
```

### Test 3: Tabla Dashboard
```
Consola → Dashboard
Esperar 2-3 segundos
¿Aparece "Período Actual: 2026-05"?
  ✅ Sí → API calls funcionan
  ❌ No → F12 Console mostrar error de API
```

### Test 4: Tabla Empresas
```
Consola → Empresas
¿Aparecen "home" y "cliente" en tabla?
  ✅ Sí → Middleware valida dominio + query BD OK
  ❌ No → 403 Forbidden en API call (ver F12 Network)
```

### Test 5: Tabla Usuarios
```
Consola → Usuarios
¿Aparecen 3+ usuarios en tabla?
  ✅ Sí → Sistema completo funcionando
  ❌ No → Similar al Test 4, revisar F12 Network
```

---

## Referencia: Documentación Oficial

- **Django ALLOWED_HOSTS:** https://docs.djangoproject.com/en/5.0/ref/settings/#allowed-hosts
- **django-tenants Middleware:** https://django-tenants.readthedocs.io/en/latest/
- **ARQUITECTURA_MULTI_TENANT_DJANGO.md** (en raíz) — Detalles de capas de seguridad

---

## Resumen Rápido (TL;DR)

Para que consola funcione en `192.168.2.15:8000`:

1. ✅ `.env` — Agregar `192.168.2.15` a `ALLOWED_HOSTS`
2. ✅ `middleware_urlconf.py` — Agregar `192.168.2.15` a `ALLOWED_PUBLIC_DOMAINS`
3. ✅ `console.js` — Agregar `192.168.2.15` a `isPublicHost`
4. ✅ `tenants_manager.js` — Agregar `192.168.2.15` a `isPublicHost`
5. ✅ `base.html` — Reordenar scripts (jwt-auth → http → console)
6. ✅ `docker-compose.yaml` — Puertos a `0.0.0.0:PUERTO:8000`
7. ✅ Limpiar caché del navegador (F12 → Storage → Clear All)

Verificar: Dashboard, Empresas, Usuarios cargan tablas sin errores en F12.

---

**Documento:** CONSOLA_ADMIN_LOCALHOST_SETUP.md  
**Versión:** 1.0  
**Completado:** 2026-05-20  
**Status:** ✅ Probado y Funcional
