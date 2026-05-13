# CHECKLIST — 3 Blocker Fixes Requeridos

**Propósito:** Verificación de 15 minutos que confirme que los 3 blocker issues están CORREGIDOS  
**Estado:** 🔴 **PENDING**  
**ETA Corrección:** 3 horas total

---

## ✅ FIX 1: Migrar lookup_field a UUID

### Verificación Pre-Fix

```bash
# Confirmar problema
grep "lookup_field = 'pk'" apps/tenant/proveedores/api/viewsets.py
# Expected output: lookup_field = 'pk'  # Volver a PK...
```

### Pasos de Corrección

1. **Editar viewsets.py línea 29:**
   ```python
   # ANTES
   lookup_field = 'pk'
   
   # DESPUÉS
   lookup_field = 'uuid'
   ```

2. **Actualizar tests:**
   ```bash
   grep -n "pk=" apps/tenant/proveedores/tests/*.py
   # Reemplazar pk=1 por uuid=<uuid_value>
   ```

3. **Migración (si necesario):**
   ```bash
   python manage.py makemigrations proveedores
   python manage.py migrate proveedores
   ```

### Verificación Post-Fix

```bash
# ✅ Confirmar cambio
grep "lookup_field = 'uuid'" apps/tenant/proveedores/api/viewsets.py

# ✅ Ejecutar tests
make test-proveedores

# ✅ Verificar que GET /api/v1/proveedores/{uuid}/ funciona
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/proveedores/550e8400-e29b-41d4-a716-446655440000/
# Debe retornar JSON (no error 404)
```

### Status

- [ ] viewsets.py actualizado a uuid
- [ ] tests actualizados
- [ ] GET endpoint funciona con UUID
- [ ] tests pasan: `make test-proveedores`

---

## ✅ FIX 2: Unificar Namespace JavaScript

### Verificación Pre-Fix

```bash
# Confirmar problema
grep -n "w.Sintel.Proveedores" apps/tenant/proveedores/static/proveedores/js/proveedores.api.js
# Expected: Múltiples referencias a w.Sintel.Proveedores
```

### Pasos de Corrección

1. **Editar static/proveedores/js/proveedores.api.js línea 37-39:**

   ```javascript
   // ANTES
   w.Sintel = w.Sintel || {};
   w.Sintel.Proveedores = w.Sintel.Proveedores || {};
   w.Sintel.Proveedores.API = proveedoresAPI;
   
   // DESPUÉS
   w.AppProveedor = w.AppProveedor || {};
   w.AppProveedor.api = proveedoresAPI;
   w.AppProveedor.API = proveedoresAPI; // backward compat
   ```

2. **Actualizar referencias en templates:**
   ```bash
   grep -rn "Sintel.Proveedores" apps/tenant/proveedores/templates/
   # Reemplazar con AppProveedor.api
   ```

3. **Actualizar referencias en otros JS (si existen):**
   ```bash
   grep -rn "Sintel.Proveedores" apps/tenant/proveedores/static/
   # Reemplazar con AppProveedor.api
   ```

### Verificación Post-Fix

```bash
# ✅ Verificar namespace en JS
grep "w.AppProveedor.api" apps/tenant/proveedores/static/proveedores/js/proveedores.api.js

# ✅ Verificar que templates usan nuevo namespace
grep -n "AppProveedor" apps/tenant/proveedores/templates/tenant/proveedores/*.html

# ✅ Tests de funcionalidad (en browser):
# 1. Abrir DevTools Console
# 2. Ejecutar: window.AppProveedor.api.list()
# 3. Debe retornar promesa (no undefined/error)
```

### Status

- [ ] proveedores.api.js actualizado
- [ ] templates actualizados
- [ ] static JS actualizado (si hay)
- [ ] window.AppProveedor.api funciona en browser

---

## ✅ FIX 3: Verificar/Reparar ProveedorServiceMixin

### Verificación Pre-Fix

```bash
# Paso 1: ¿Existe api/mixins.py?
ls -la apps/tenant/proveedores/api/mixins.py
# Esperado: archivo debe existir

# Paso 2: ¿Existe la clase ProveedorServiceMixin?
grep -n "class ProveedorServiceMixin" apps/tenant/proveedores/api/mixins.py
# Esperado: debe encontrar la clase

# Paso 3: ¿Tiene los métodos necesarios?
grep -n "def.*proveedor" apps/tenant/proveedores/api/mixins.py
# Esperado: mínimo 3+ métodos
```

### Si Falla la Verificación Pre-Fix

**Opción A: Crear api/mixins.py (si falta completamente)**

```bash
# Crear desde plantilla clientes
cat > apps/tenant/proveedores/api/mixins.py << 'EOF'
"""
Mixins para inyección de servicios en ProveedorViewSet.
"""
from apps.tenant.proveedores.services.selectors import ProveedorSelector
from apps.tenant.proveedores.services.crud_service import ProveedorCRUDService
from apps.tenant.proveedores.services.business_service import ProveedorBusinessService

class ProveedorServiceMixin:
    """Inyecta servicios en ViewSet."""
    
    @property
    def proveedor_selector(self):
        return ProveedorSelector()
    
    @property
    def proveedor_crud(self):
        return ProveedorCRUDService()
    
    @property
    def proveedor_service(self):
        return ProveedorBusinessService()
EOF
```

**Opción B: Consolidar con services/api_mixins.py (si hay duplicidad)**

```bash
# Revisar services/api_mixins.py
cat apps/tenant/proveedores/services/api_mixins.py

# Si tiene lo mismo que api/mixins.py:
# 1. Eliminar api/mixins.py
# 2. Cambiar import en viewsets.py:
#    FROM: from .mixins import ProveedorServiceMixin
#    TO:   from .services.api_mixins import ProveedorServiceMixin
```

### Pasos de Corrección

1. **Elegir Opción A o B arriba**
2. **Ejecutar paso de corrección**
3. **Verificar que viewsets.py importa correctamente:**
   ```python
   # Línea 12 en viewsets.py
   from .mixins import ProveedorServiceMixin
   # O
   from .services.api_mixins import ProveedorServiceMixin
   ```

### Verificación Post-Fix

```bash
# ✅ Verificar que la clase existe
grep -n "class ProveedorServiceMixin" apps/tenant/proveedores/api/mixins.py

# ✅ Ejecutar tests para verificar inyección
make test-proveedores

# ✅ Manual check: GET endpoint debe funcionar
curl -X GET http://localhost:8000/api/v1/proveedores/ \
  -H "Authorization: Bearer $TOKEN"
# Debe retornar JSON lista, NO 500 error

# ✅ Verificar en logs que no hay ImportError
tail -f docker logs web | grep "ImportError"
# Debe estar vacío
```

### Status

- [ ] api/mixins.py existe O services/api_mixins.py consolidado
- [ ] ProveedorServiceMixin clase existe
- [ ] viewsets.py importa correctamente
- [ ] tests pasan sin ImportError
- [ ] GET /api/v1/proveedores/ funciona (200 OK)

---

## 🔴 CHECKLIST GLOBAL

```
BLOCKER FIX #1: UUID Migration
  ✅ viewsets.py línea 29: lookup_field = 'uuid'  [ ]
  ✅ tests actualizados                          [ ]
  ✅ tests pasan                                 [ ]

BLOCKER FIX #2: JS Namespace
  ✅ proveedores.api.js: window.AppProveedor.api [ ]
  ✅ templates actualizados                      [ ]
  ✅ window.AppProveedor.api funciona            [ ]

BLOCKER FIX #3: ServiceMixin
  ✅ api/mixins.py existe                        [ ]
  ✅ ProveedorServiceMixin clase existe          [ ]
  ✅ viewsets.py importa correctamente           [ ]
  ✅ GET /api/v1/proveedores/ retorna 200       [ ]

FINAL VERIFICATION:
  ✅ make test-proveedores PASS                  [ ]
  ✅ make audit PASS                             [ ]
  ✅ No hay errores 500 en logs                  [ ]
  ✅ Re-auditoría completada                     [ ]

RESULTADO: [ ] TODOS PASAN → APROBADO PARA MERGE
           [ ] ALGUNO FALLA → BLOCKER CONTINÚA
```

---

## ⏱️ Tiempo Estimado por Fix

| Fix | Componentes | ETA |
|---|---|---|
| **UUID** | viewsets + tests | 2h |
| **JS Namespace** | .js + templates | 30m |
| **ServiceMixin** | api/mixins.py + imports | 30m |
| **Total** | | **3h** |

---

## 🚀 Post-Fix Workflow

1. Completar 3 fixes arriba
2. Correr: `make test-proveedores`
3. Correr: `make audit`
4. Verificar que todos los checklists pasan
5. Solicitar re-auditoría: "Blocker fixes completados"
6. Después de re-auditoría: Aprobado para merge

---

**Estado Actual:** 🔴 **0/3 FIXES COMPLETADOS — BLOCKER ACTIVO**

**Próximo Paso:** Comience con FIX 1 (UUID Migration)
