# 🔒 Seguridad del Ámbito Público (v2.29)

**Fecha:** 2026-01-30  
**Versión:** v2.29  
**Estado:** ✅ **IMPLEMENTADO Y VERIFICADO**

---

## 🎯 Objetivo

Implementar múltiples capas de seguridad para proteger el ámbito público (`schema='public'`) de accesos no autorizados y garantizar el aislamiento correcto entre tenants.

---

## ✅ Capas de Seguridad Implementadas

### 1. Whitelist Estricta de Dominios

**Configuración:**
```python
ALLOWED_PUBLIC_DOMAINS = frozenset([
    'sintel.net.co',      # Dominio de producción
    'localhost',       # Desarrollo local
    '127.0.0.1',       # Desarrollo local (IP)
    '0.0.0.0',         # Desarrollo local (bind all)
])
```

**Validación:**
- ✅ Solo permite acceso desde dominios explícitamente permitidos
- ✅ Bloquea cualquier otro dominio intentando acceder al público
- ✅ Logging de seguridad para auditoría

### 2. Bloqueo de Subdominios

**Protección:**
- ✅ Bloquea subdominios intentando acceder al esquema público
- ✅ Ejemplo: `cliente.sintel.net.co` NO puede acceder al público
- ✅ Ejemplo: `test.localhost` NO puede acceder al público (solo `localhost` exacto)

**Código:**
```python
# CAPA 2: Bloquear subdominios intentando acceder al público
if host.endswith(self.REQUIRED_TENANT_SUFFIX):
    # Bloquear acceso
    return False
```

### 3. Validación de Subdominios de Localhost

**Protección:**
- ✅ Solo permite `localhost` exacto (no subdominios)
- ✅ Bloquea `test.localhost`, `cliente.localhost`, etc.
- ✅ Previene confusión entre desarrollo y producción

**Código:**
```python
# CAPA 3: Validar que no sea un subdominio de localhost
if host != 'localhost' and 'localhost' in host:
    # Bloquear acceso
    return False
```

### 4. Protección contra Host Header Attacks

**Validaciones:**
- ✅ Normalización de host (elimina puerto, convierte a minúsculas)
- ✅ Validación de formato básico
- ✅ Manejo de excepciones `DisallowedHost`
- ✅ Logging de intentos de ataque

**Código:**
```python
def _normalize_host(self, request):
    """Normaliza y valida el host de la request."""
    try:
        host = request.get_host().split(':')[0].lower().strip()
        # Validaciones adicionales...
        return host
    except DisallowedHost:
        # Logging de seguridad
        raise
```

### 5. Logging de Seguridad

**Características:**
- ✅ Logger dedicado: `security.tenants`
- ✅ Registra todos los intentos de acceso no autorizado
- ✅ Incluye IP del cliente, path, host, tenant
- ✅ Diferentes niveles según severidad (warning, error, critical)

**Ejemplo de Log:**
```
🚨 BLOQUEO PÚBLICO (Capa 1 - Whitelist): 
Host 'cliente.sintel.net.co' no está en ALLOWED_PUBLIC_DOMAINS | 
Tenant: public | 
Path: /console/ | 
IP: 192.168.1.100
```

---

## 📋 Validaciones por Tipo de Tenant

### Ámbito Público (`schema='public'`)

**Validaciones:**
1. ✅ Host debe estar en `ALLOWED_PUBLIC_DOMAINS`
2. ✅ Host NO debe terminar en `.sintel.net.co` (subdominio)
3. ✅ Host NO debe ser subdominio de `localhost`
4. ✅ Establece `request.urlconf = ROOT_URLCONF`

**Bloqueo:**
- ❌ `cliente.sintel.net.co` → 404
- ❌ `test.localhost` → 404
- ❌ `cualquier-dominio.com` → 404
- ✅ `sintel.net.co` → Permitido
- ✅ `localhost` → Permitido (desarrollo)

### Ámbito Privado (`schema != 'public'`)

**Validaciones:**
1. ✅ Host debe terminar en `.sintel.net.co` (producción) O
2. ✅ Host debe contener indicador de desarrollo (`localhost`, `127.0.0.1`)
3. ✅ Establece `request.urlconf = TENANT_URLCONF`

**Bloqueo:**
- ❌ `sintel.net.co` → 403 (dominio público no puede acceder a tenant privado)
- ❌ `cualquier-dominio.com` → 403
- ✅ `cliente.sintel.net.co` → Permitido
- ✅ `cliente.localhost` → Permitido (desarrollo)

---

## 🔒 Garantías de Seguridad

### 1. Aislamiento Total
- ✅ El ámbito público solo es accesible desde dominios explícitamente permitidos
- ✅ Los tenants privados solo son accesibles desde sus dominios correspondientes
- ✅ No hay posibilidad de acceso cruzado entre ámbitos

### 2. Protección contra Ataques
- ✅ Host Header Attacks: Normalización y validación estricta
- ✅ Subdomain Hijacking: Bloqueo de subdominios en ámbito público
- ✅ Domain Confusion: Validación estricta de sintaxis

### 3. Auditoría Completa
- ✅ Todos los intentos de acceso no autorizado se registran
- ✅ Logging incluye contexto completo (IP, path, host, tenant)
- ✅ Diferentes niveles de logging según severidad

---

## 📚 Archivos Modificados

1. ✅ `apps/public/tenants/middleware_urlconf.py` - Implementación de capas de seguridad
2. ✅ `config/settings.py` - Actualizado nombre de clase en MIDDLEWARE
3. ✅ `documentacion/SEGURIDAD_AMBITO_PUBLICO_v2.29.md` - Documentación nueva

---

## 🧪 Casos de Prueba

### Caso 1: Acceso Público desde Dominio Permitido
```
Request: GET http://sintel.net.co/console/
Resultado: ✅ Permitido (ROOT_URLCONF)
```

### Caso 2: Acceso Público desde Subdominio
```
Request: GET http://cliente.sintel.net.co/console/
Resultado: ❌ 404 (Bloqueado - Capa 2)
```

### Caso 3: Acceso Público desde Dominio No Permitido
```
Request: GET http://cualquier-dominio.com/console/
Resultado: ❌ 404 (Bloqueado - Capa 1)
```

### Caso 4: Acceso Privado desde Dominio Correcto
```
Request: GET http://cliente.sintel.net.co/dashboard/
Resultado: ✅ Permitido (TENANT_URLCONF)
```

### Caso 5: Acceso Privado desde Dominio Público
```
Request: GET http://sintel.net.co/dashboard/
Resultado: ❌ 403 (Bloqueado - dominio público no puede acceder a tenant privado)
```

---

## ✅ Estado Final

- ✅ **Múltiples capas de seguridad**: Whitelist, bloqueo de subdominios, validación de localhost
- ✅ **Protección contra ataques**: Host Header Attacks, Subdomain Hijacking
- ✅ **Logging completo**: Auditoría de todos los intentos de acceso
- ✅ **Validación estricta**: Dominios permitidos y sintaxis correcta
- ✅ **Aislamiento garantizado**: No hay posibilidad de acceso cruzado

---

**Fecha:** 2026-01-30  
**Versión:** v2.29  
**Estado:** ✅ **IMPLEMENTADO Y VERIFICADO**
