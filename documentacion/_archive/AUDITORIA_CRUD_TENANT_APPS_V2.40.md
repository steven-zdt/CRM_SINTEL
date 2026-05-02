# Auditoría: CRUD Completo para ADMIN/STAFF en TENANT_APPS v2.40

**Fecha:** 2026-01-XX  
**Versión:** v2.40  
**Estado:** ✅ Auditoría completada

---

## STEP 0 — DISCOVER TENANT_APPS & EXCEPTIONS

### TENANT_APPS Identificadas (desde `config/settings.py`):
1. `apps.tenant.core` - Vistas core y manejadores de error (sin modelos propios)
2. `apps.tenant.empresa` - Datos de la empresa (singleton por tenant)
3. `apps.tenant.facturas` - Facturación (por tenant) ⚠️ **EXCEPCIÓN: INMUTABLE**
4. `apps.tenant.contabilidad` - Contabilidad (por tenant)
5. `apps.tenant.inventario` - Inventario (por tenant)
6. `apps.tenant.empleados` - Empleados y nómina (por tenant)
7. `apps.tenant.gastos` - Gastos operativos y de personal (por tenant)
8. `apps.tenant.proveedores` - Proveedores y compras (por tenant)
9. `apps.tenant.clientes` - Clientes y ventas (por tenant)
10. `apps.tenant.landing` - Landing page (sin modelos, endpoints públicos)
11. `apps.tenant.dashboard` - Dashboard (sin modelos, solo lectura)
12. `apps.tenant.perfil` - Perfil privado del colaborador (por tenant)

### EXCEPCIONES (Inmutables - NO modificar):
- ✅ `apps.tenant.facturas` - `FacturaViewSet` es `ReadOnlyModelViewSet`, PUT/PATCH/POST bloqueados → 405
- ✅ `apps.tenant.facturas` - `NotaCreditoViewSet` (si existe) - inmutable, solo DELETE para rollback

### Apps sin modelos (NO requieren CRUD):
- ✅ `apps.tenant.core` - Solo servicios y vistas auxiliares
- ✅ `apps.tenant.landing` - Endpoints públicos (AllowAny)
- ✅ `apps.tenant.dashboard` - Solo endpoints de lectura (GET)

---

## STEP 1 — PERMISSION CLASS (REUSE OR CREATE)

### Estado Actual:
- ✎ `IsTenantAdminOrReadOnly` existe en **3 lugares diferentes**:
  1. `apps/tenant/empresa/api/viewsets.py` (línea 42) - Con soporte para ENFORCED MODE
  2. `apps/tenant/facturas/api/permissions.py` (línea 16) - Versión simple
  3. `apps/tenant/empresa/permissions.py` - `IsTenantAdmin` (solo verifica ADMIN/STAFF)

### Acción Requerida:
- ✎ **CONSOLIDAR** `IsTenantAdminOrReadOnly` en `apps/tenant/api/permissions.py` para reutilización
- ✎ Mantener soporte para ENFORCED MODE (verificar `_check_enforced_mode` en ViewSet)
- ✎ Actualizar imports en todas las apps que lo usan

---

## STEP 2 — VIEWSETS (VALIDATE → UPDATE)

### A) Apps con ENFORCED MODE ya implementado (✓ OK):
1. ✅ **`apps.tenant.empresa`** - `EmpresaViewSet` (ModelViewSet con ENFORCED MODE)
2. ✅ **`apps.tenant.clientes`** - `ClienteViewSet` (ModelViewSet con ENFORCED MODE)
3. ✅ **`apps.tenant.contabilidad`** - `CuentaContableViewSet`, `AsientoContableViewSet` (ModelViewSet con ENFORCED MODE)
4. ✅ **`apps.tenant.proveedores`** - `ProveedorViewSet` (ModelViewSet con ENFORCED MODE)
5. ✅ **`apps.tenant.gastos`** - `GastoViewSet` (ModelViewSet con ENFORCED MODE)
6. ✅ **`apps.tenant.empleados`** - `EmpleadoViewSet`, `ContratoViewSet`, `AfiliacionViewSet`, `DevengoViewSet`, `CapacitacionViewSet` (ModelViewSet con ENFORCED MODE)

### B) Apps que requieren actualización (✎ CHANGE):

#### B.1) `apps.tenant.inventario`
- ✎ **`CatalogoItemViewSet`** (ModelViewSet):
  - `permission_classes = [permissions.IsAuthenticated]` → Cambiar a `[IsAuthenticated, IsTenantAdminOrReadOnly]`
  - Agregar `_check_enforced_mode()` y sobrescribir `create()`, `update()`, `partial_update()`, `destroy()`
  - Agregar `SessionAuthentication` a `authentication_classes`
  
- ✎ **`ActivoFijoViewSet`** (ModelViewSet):
  - `permission_classes = [permissions.IsAuthenticated]` → Cambiar a `[IsAuthenticated, IsTenantAdminOrReadOnly]`
  - Agregar `_check_enforced_mode()` y sobrescribir `create()`, `update()`, `partial_update()`, `destroy()`
  - Agregar `SessionAuthentication` a `authentication_classes`

- ✎ **`MovimientoInventarioViewSet`** (ModelViewSet):
  - `permission_classes = [permissions.IsAuthenticated]` → Cambiar a `[IsAuthenticated, IsTenantAdminOrReadOnly]`
  - Agregar `_check_enforced_mode()` y sobrescribir `create()`, `update()`, `partial_update()`, `destroy()`
  - Agregar `SessionAuthentication` a `authentication_classes`

#### B.2) `apps.tenant.perfil`
- ✓ **`PerfilViewSet`** (ModelViewSet):
  - `permission_classes = [IsAuthenticated, IsTenantMember, IsOwnerOrReadOnly]` → **CORRECTO**
  - `IsOwnerOrReadOnly` es apropiado para perfil (cada usuario edita su propio perfil)
  - **NO requiere cambio** - El perfil es un caso especial donde cada usuario edita su propio registro

### C) Apps inmutables (EXCEPCIONES - NO modificar):
- ✅ **`apps.tenant.facturas`** - `FacturaViewSet` (ReadOnlyModelViewSet)
  - PUT/PATCH/POST bloqueados → 405 (correcto)
  - DELETE permitido solo para rollback técnico
  - **NO requiere cambio**

---

## STEP 3 — URL ROUTERS (VALIDATE → UPDATE)

### Estado Actual:
- ✅ `apps.tenant.empresa/api/urls.py` - Router configurado
- ✅ `apps.tenant.clientes/api/urls.py` - Router configurado
- ✅ `apps.tenant.contabilidad/api/urls.py` - Router configurado
- ✅ `apps.tenant.proveedores/api/urls.py` - Router configurado
- ✅ `apps.tenant.gastos/api/urls.py` - Router configurado
- ✅ `apps.tenant.empleados/api/urls.py` - Router configurado
- ✅ `apps.tenant.inventario/api/urls.py` - Router configurado
- ✅ `apps.tenant.perfil/api/urls.py` - Router configurado
- ✅ `apps.tenant.facturas/api/urls.py` - Router configurado

**Resultado:** ✓ Todos los routers están configurados correctamente.

---

## STEP 4 — TESTS (VALIDATE → ADD/UPDATE)

### Tests Existentes:
- ✅ `tests/tenant/empresa/` - Tests existentes
- ✅ `tests/tenant/clientes/` - Tests existentes
- ✅ `tests/tenant/contabilidad/` - Tests existentes
- ✅ `tests/tenant/facturas/test_factura_immutability.py` - Tests de inmutabilidad

### Tests Requeridos (NUEVOS):
- ✎ `tests/tenant/inventario/test_crud_permissions.py` - Tests CRUD para `CatalogoItemViewSet`, `ActivoFijoViewSet`, `MovimientoInventarioViewSet`
- ✎ `tests/tenant/proveedores/test_crud_permissions.py` - Tests CRUD para `ProveedorViewSet` (si no existe)
- ✎ `tests/tenant/gastos/test_crud_permissions.py` - Tests CRUD para `GastoViewSet` (si no existe)
- ✎ `tests/tenant/empleados/test_crud_permissions.py` - Tests CRUD para todos los ViewSets (si no existe)

---

## RESUMEN DE CAMBIOS REQUERIDOS

### Archivos a Modificar:
1. ✎ `apps/tenant/api/permissions.py` - Agregar `IsTenantAdminOrReadOnly` consolidado
2. ✎ `apps/tenant/inventario/api/viewsets.py` - Actualizar permisos y agregar ENFORCED MODE
3. ✎ `apps/tenant/empresa/api/viewsets.py` - Actualizar import de `IsTenantAdminOrReadOnly`
4. ✎ `apps/tenant/facturas/api/permissions.py` - Actualizar import de `IsTenantAdminOrReadOnly` (o eliminar si se consolida)

### Archivos a Crear:
1. ✎ `tests/tenant/inventario/test_crud_permissions.py` - Tests CRUD
2. ✎ `tests/tenant/proveedores/test_crud_permissions.py` - Tests CRUD (si no existe)
3. ✎ `tests/tenant/gastos/test_crud_permissions.py` - Tests CRUD (si no existe)
4. ✎ `tests/tenant/empleados/test_crud_permissions.py` - Tests CRUD (si no existe)

---

## DIFFS

### D.1) Consolidar IsTenantAdminOrReadOnly en apps/tenant/api/permissions.py

```python
# apps/tenant/api/permissions.py
# ... existing code ...

from apps.tenant.empresa.permissions import IsTenantAdmin


class IsTenantAdminOrReadOnly(permissions.BasePermission):
    """
    Permiso que permite lectura a usuarios autenticados y escritura solo a ADMIN/STAFF.
    
    ⚠️ IMPORTANTE: Para ViewSets con ENFORCED MODE, este permiso permite todas las operaciones
    y la verificación real se hace en _check_enforced_mode dentro de cada método.
    Esto permite que el método se ejecute y retorne 405 con un mensaje claro.
    
    Uso:
        class MyViewSet(viewsets.ModelViewSet):
            permission_classes = [IsAuthenticated, IsTenantAdminOrReadOnly]
    """
    message = "Solo usuarios ADMIN/STAFF del tenant pueden crear/editar/eliminar."
    
    def has_permission(self, request, view):
        from rest_framework.permissions import SAFE_METHODS
        
        user = getattr(request, "user", None)
        if not (user and user.is_authenticated):
            return False
        
        # Lectura siempre permitida
        if request.method in SAFE_METHODS:
            return True
        
        # Para mutaciones, si el ViewSet tiene _check_enforced_mode, permitir el acceso
        # y dejar que el método maneje la verificación (retornará 405 si no tiene permisos)
        if hasattr(view, '_check_enforced_mode'):
            return True  # Permitir acceso, _check_enforced_mode verificará en el método
        
        # Si no tiene _check_enforced_mode, usar verificación tradicional
        return IsTenantAdmin().has_permission(request, view)
```

### D.2) Actualizar apps/tenant/inventario/api/viewsets.py

```diff
--- a/apps/tenant/inventario/api/viewsets.py
+++ b/apps/tenant/inventario/api/viewsets.py
@@ -1,6 +1,7 @@
 from decimal import Decimal
 from rest_framework import viewsets, permissions, mixins, status
 from rest_framework.decorators import action
+from rest_framework.response import Response
 from rest_framework.request import Request
 from rest_framework.authentication import SessionAuthentication
 from django.conf import settings
@@ -10,6 +11,8 @@
 from apps.tenant.inventario.models import (
     CatalogoItem, ActivoFijo, MovimientoInventario, ItemFacturaCatalogo
 )
+from apps.tenant.api.permissions import IsTenantAdminOrReadOnly
+from apps.tenant.empresa.permissions import IsTenantAdmin
 from .serializers import (
     CatalogoItemListSerializer, CatalogoItemDetailSerializer,
     CatalogoItemSerializer,  # Compatibilidad
@@ -34,8 +37,40 @@
 
 
 class BaseViewSet(viewsets.ModelViewSet):
-    permission_classes = [permissions.IsAuthenticated]
+    """
+    ViewSet base para inventario con ENFORCED MODE.
+    
+    ⚠️ v2.40: ENFORCED MODE - POST/PATCH/PUT/DELETE solo para STAFF/ADMIN.
+    """
+    authentication_classes = [SessionAuthentication]
+    permission_classes = [permissions.IsAuthenticated, IsTenantAdminOrReadOnly]
 
     def get_authenticators(self):
         if settings.DEBUG and _UnsafeSessionAuthentication:
             return [_UnsafeSessionAuthentication()]
         return super().get_authenticators()
+    
+    def _check_enforced_mode(self, request):
+        """
+        Verifica si el usuario tiene permisos para mutaciones (ENFORCED MODE).
+        
+        ⚠️ ENFORCED: Solo STAFF/ADMIN pueden crear/editar/eliminar.
+        No-staff recibe 405 Method Not Allowed.
+        
+        Returns:
+            tuple: (ok: bool, reason: str | None)
+        """
+        from rest_framework.permissions import SAFE_METHODS
+        
+        user = request.user
+        if not (user and user.is_authenticated):
+            return False, "Usuario no autenticado."
+        
+        if request.method in SAFE_METHODS:
+            return True, None  # Lectura siempre permitida
+        
+        # Para mutaciones (POST, PUT, PATCH, DELETE)
+        if IsTenantAdmin().has_permission(request, self):
+            return True, None  # ADMIN/STAFF tienen permiso
+        
+        return False, "Solo usuarios ADMIN/STAFF del tenant pueden crear/editar/eliminar."
+    
+    def create(self, request, *args, **kwargs):
+        """Crea un nuevo registro. ⚠️ ENFORCED: Solo STAFF/ADMIN."""
+        ok, reason = self._check_enforced_mode(request)
+        if not ok:
+            return Response({"detail": reason}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
+        return super().create(request, *args, **kwargs)
+    
+    def update(self, request, *args, **kwargs):
+        """Actualiza un registro. ⚠️ ENFORCED: Solo STAFF/ADMIN."""
+        ok, reason = self._check_enforced_mode(request)
+        if not ok:
+            return Response({"detail": reason}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
+        return super().update(request, *args, **kwargs)
+    
+    def partial_update(self, request, *args, **kwargs):
+        """Actualiza parcialmente un registro. ⚠️ ENFORCED: Solo STAFF/ADMIN."""
+        ok, reason = self._check_enforced_mode(request)
+        if not ok:
+            return Response({"detail": reason}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
+        return super().partial_update(request, *args, **kwargs)
+    
+    def destroy(self, request, *args, **kwargs):
+        """Elimina un registro. ⚠️ ENFORCED: Solo STAFF/ADMIN."""
+        ok, reason = self._check_enforced_mode(request)
+        if not ok:
+            return Response({"detail": reason}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
+        return super().destroy(request, *args, **kwargs)
```

### D.3) Actualizar imports en apps/tenant/empresa/api/viewsets.py

```diff
--- a/apps/tenant/empresa/api/viewsets.py
+++ b/apps/tenant/empresa/api/viewsets.py
@@ -32,7 +32,7 @@
     MailInboxConfigTestConnectionSerializer,
 )
-from apps.tenant.empresa.permissions import IsTenantAdmin
+from apps.tenant.empresa.permissions import IsTenantAdmin
+from apps.tenant.api.permissions import IsTenantAdminOrReadOnly
 from apps.tenant.api.permissions import IsTenantMember
 from apps.config.api.pagination import StandardResultsSetPagination
 
@@ -40,25 +40,6 @@
 log_mailinbox = logging.getLogger("mailinbox.api")
 
 
-# ========= Permisos =========
-
-class IsTenantAdminOrReadOnly(permissions.BasePermission):
-    """
-    Permiso que permite lectura a usuarios autenticados y escritura solo a ADMIN/STAFF.
-    
-    ⚠️ IMPORTANTE: Para ViewSets con ENFORCED MODE, este permiso permite todas las operaciones
-    y la verificación real se hace en _check_enforced_mode dentro de cada método.
-    Esto permite que el método se ejecute y retorne 405 con un mensaje claro.
-    """
-    message = "Solo usuarios ADMIN/STAFF del tenant pueden crear/editar/eliminar."
-    
-    def has_permission(self, request, view):
-        from rest_framework.permissions import SAFE_METHODS
-        
-        user = getattr(request, "user", None)
-        if not (user and user.is_authenticated):
-            return False
-        
-        # Lectura siempre permitida
-        if request.method in SAFE_METHODS:
-            return True
-        
-        # Para mutaciones, si el ViewSet tiene _check_enforced_mode, permitir el acceso
-        # y dejar que el método maneje la verificación (retornará 405 si no tiene permisos)
-        if hasattr(view, '_check_enforced_mode'):
-            return True  # Permitir acceso, _check_enforced_mode verificará en el método
-        
-        # Si no tiene _check_enforced_mode, usar verificación tradicional
-        return IsTenantAdmin().has_permission(request, view)
-
-
 # ========= ViewSets =========
```

---

## POST-APPLY CHECKLIST

```bash
# 1. Verificar migraciones (sin aplicar)
python manage.py showmigrations

# 2. Aplicar migraciones (si hay pendientes)
python manage.py migrate_schemas --shared --fake-initial
python manage.py migrate_schemas --tenant --fake-initial

# 3. Ejecutar tests CRUD
pytest -q tests/tenant/inventario/test_crud_permissions.py
pytest -q tests/tenant/proveedores/test_crud_permissions.py
pytest -q tests/tenant/gastos/test_crud_permissions.py
pytest -q tests/tenant/empleados/test_crud_permissions.py

# 4. Verificación manual rápida (requiere sesión activa)
# Como ADMIN/STAFF:
curl -X POST http://localhost:8000/api/v1/inventario/catalogo/ \
  -H "Content-Type: application/json" \
  -H "Cookie: sessionid=..." \
  -H "X-CSRFToken: ..." \
  -d '{"nombre": "Test Item", "tipo": "PRODUCTO", "unidad_medida": "UN"}'
# Esperado: 201 Created

# Como usuario no-staff:
curl -X POST http://localhost:8000/api/v1/inventario/catalogo/ \
  -H "Content-Type: application/json" \
  -H "Cookie: sessionid=..." \
  -H "X-CSRFToken: ..." \
  -d '{"nombre": "Test Item", "tipo": "PRODUCTO", "unidad_medida": "UN"}'
# Esperado: 405 Method Not Allowed
```

---

**Auditoría completada:** ✅  
**Fecha:** 2026-01-XX  
**Versión:** v2.40
