# Auditoría Forense y Blindaje de Rutas Públicas

**Fecha:** 2024  
**Objetivo:** Garantizar que los tenants privados NO tengan acceso a rutas exclusivas del esquema público.

---

## 🔍 Análisis Forense Realizado

### 1. Auditoría de `config/urls_tenant.py`

**Resultado:** ✅ **PASÓ LA AUDITORÍA**

- ✅ NO contiene rutas de `/console/`
- ✅ NO contiene `include('apps.public.console.urls')`
- ✅ NO hereda ni concatena `urlpatterns` de `config/urls_public.py`
- ✅ Solo contiene rutas privadas:
  - `path('', include('apps.tenant.landing.urls'))` (Landing)
  - `path('dashboard/', ...)` (Dashboard privado)
  - `path('admin/', ...)` (Admin Django privado)
  - `path('api/v1/', ...)` (APIs del tenant)
  - `path('api/token/', ...)` (JWT)

**Conclusión:** El archivo está correctamente aislado y no expone rutas públicas.

---

### 2. Verificación de Configuración (`config/settings.py`)

**Resultado:** ✅ **CONFIGURACIÓN CORRECTA**

```python
ROOT_URLCONF = 'config.urls_public'    # Solo para dominio público
TENANT_URLCONF = 'config.urls_tenant'   # Solo para tenants
```

**Conclusión:** La separación de URLConfs es explícita y correcta.

---

### 3. Test de Penetración (`tests/tenant/security/test_url_isolation.py`)

**Resultado:** ✅ **TESTS CREADOS**

Se creó una suite completa de tests de penetración que valida:

#### Escenarios de Ataque:

1. **Ataque 1:** `GET /console/` desde tenant privado
   - ✅ Esperado: `404 Not Found`
   - ❌ Falla si: Devuelve `200`, `302` o `403` (ruta existe)

2. **Ataque 2:** `GET /api/public/v1/` desde tenant privado
   - ✅ Esperado: `404 Not Found`
   - ❌ Falla si: Devuelve `200`, `302` o `403` (ruta existe)

3. **Ataque 3:** `GET /api/admin/v1/` desde tenant privado
   - ✅ Esperado: `404 Not Found`
   - ❌ Falla si: Devuelve `200`, `302` o `403` (ruta existe)

4. **Control:** `GET /dashboard/` desde tenant privado
   - ✅ Esperado: `200 OK` o `302 Redirect` (debe funcionar)
   - Confirma que el tenant está activo y las rutas privadas funcionan

#### Ejecutar Tests:

```bash
# Ejecutar todos los tests de penetración
docker compose exec web python manage.py test tests.tenant.security.test_url_isolation

# Ejecutar un test específico
docker compose exec web python manage.py test tests.tenant.security.test_url_isolation.PublicRouteIsolationPenetrationTests.test_console_route_returns_404_in_private_tenant
```

---

### 4. Blindaje por Middleware (`apps/public/tenants/middleware.py`)

**Resultado:** ✅ **MIDDLEWARE MEJORADO**

Se agregó una capa de defensa extra que actúa como firewall:

#### Funcionalidad Agregada:

```python
def _is_public_only_route(self, path):
    """
    Verifica si una ruta es exclusiva del esquema público.
    
    ⚠️ REGLA DE ORO: Estas rutas NO deben existir en tenants privados.
    Si el router de URLs las encuentra, este middleware las bloquea como firewall.
    """
    public_only_prefixes = [
        '/console/',           # Consola de administración pública
        '/api/public/v1/',     # APIs REST públicas
        '/api/admin/v1/',      # APIs REST de administración
    ]
    
    for prefix in public_only_prefixes:
        if path.startswith(prefix):
            return True
    
    return False
```

#### Comportamiento:

- **Si el tenant es privado** (`schema_name != 'public'`)
- **Y la ruta es pública** (comienza con `/console/`, `/api/public/v1/`, `/api/admin/v1/`)
- **Entonces:** Lanza `Http404` (ruta no existe)

**Conclusión:** El middleware actúa como cinturón de seguridad en caso de configuración humana futura.

---

## 🛡️ Capas de Seguridad Implementadas

### Capa 1: Aislamiento de URLs (Raíz)
- **Archivo:** `config/urls_tenant.py`
- **Función:** No incluye rutas públicas
- **Estado:** ✅ Verificado

### Capa 2: Configuración de URLConfs
- **Archivo:** `config/settings.py`
- **Función:** Separación explícita entre `ROOT_URLCONF` y `TENANT_URLCONF`
- **Estado:** ✅ Verificado

### Capa 3: Middleware de Seguridad (Firewall)
- **Archivo:** `apps/public/tenants/middleware.py`
- **Función:** Bloquea rutas públicas en tenants privados
- **Estado:** ✅ Implementado

### Capa 4: Tests de Penetración (Validación Continua)
- **Archivo:** `tests/tenant/security/test_url_isolation.py`
- **Función:** Valida que el aislamiento funciona correctamente
- **Estado:** ✅ Creado

---

## 📋 Checklist de Seguridad

- [x] `config/urls_tenant.py` NO contiene rutas públicas
- [x] `config/settings.py` tiene `ROOT_URLCONF` y `TENANT_URLCONF` configurados
- [x] `TenantSecurityMiddleware` bloquea rutas públicas en tenants privados
- [x] Tests de penetración validan el aislamiento
- [x] Documentación de auditoría creada

---

## 🚀 Próximos Pasos

1. **Ejecutar Tests:**
   ```bash
   docker compose exec web python manage.py test tests.tenant.security.test_url_isolation
   ```

2. **Verificar en Producción:**
   - Acceder a `http://home.sintel.com:8000/console/` → Debe devolver `404`
   - Acceder a `http://sintel.com:8000/console/` → Debe funcionar (esquema público)

3. **Monitoreo Continuo:**
   - Ejecutar tests de penetración en CI/CD
   - Revisar logs de seguridad periódicamente

---

## ⚠️ Notas Importantes

1. **Regla de Oro:** Si una ruta devuelve `200`, `302` o `403` en un tenant privado, significa que la ruta EXISTE, lo cual es un error de seguridad. Debe devolver `404 Not Found`.

2. **Middleware como Firewall:** El middleware actúa como cinturón de seguridad. La solución raíz es mantener `config/urls_tenant.py` limpio.

3. **Tests de Penetración:** Estos tests deben ejecutarse regularmente para garantizar que el aislamiento se mantiene.

---

## 📚 Referencias

- `config/urls_tenant.py` - URLs de tenants privados
- `config/urls_public.py` - URLs del esquema público
- `apps/public/tenants/middleware.py` - Middleware de seguridad
- `tests/tenant/security/test_url_isolation.py` - Tests de penetración
