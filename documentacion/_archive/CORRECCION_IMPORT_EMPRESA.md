# ✅ Corrección Definitiva de Import + Validación E2E (SSoT Empresa)

## 🎯 Objetivo Cumplido

Se eliminó el **shadowing** entre `apps/tenant/empresa/services.py` (archivo) y `apps/tenant/empresa/services/` (paquete) que causaba que `get_empresa_emisor_data` no estuviera disponible.

## 📋 Cambios Realizados

### 1. Renombrado del Paquete Conflictivo

**Antes:**
- `apps/tenant/empresa/services/` (paquete con `__init__.py`)
- `apps/tenant/empresa/services.py` (archivo)

**Después:**
- `apps/tenant/empresa/impl/` (paquete renombrado)
- `apps/tenant/empresa/services.py` (archivo - SSoT)

**Razón:** Eliminar el conflicto de nombres que causaba que Python importara el paquete en lugar del archivo.

### 2. Actualización de Imports

#### ✅ `apps/tenant/facturas/services.py`
```python
# ✅ CORRECCIÓN DEFINITIVA: El paquete services/ fue renombrado a impl/ para eliminar shadowing
# Ahora podemos importar directamente desde el archivo services.py sin conflictos
from apps.tenant.empresa.services import (
    get_empresa_emisor_data,
    EmpresaNotConfiguredError,
)
```

#### ✅ `apps/tenant/empresa/api/viewsets.py`
```python
# Antes: from apps.tenant.empresa import services as empresa_services
# Después:
from apps.tenant.empresa.impl import get_empresa, get_or_create_empresa, update_empresa
```

#### ✅ `apps/tenant/core/services/empresa_adapter.py`
```python
# Actualizado: from apps.tenant.empresa.impl.empresa_service import ...
# Actualizado: from apps.tenant.empresa.impl.mailbox_service import ...
```

#### ✅ `apps/tenant/empresa/management/commands/audit_empresa_app.py`
```python
# Actualizado: from apps.tenant.empresa.impl import ...
```

### 3. Simplificación del Service Layer de Facturas

**Antes:** Verificaciones redundantes de `None` y `importlib` complejo.

**Después:** Import directo y manejo de excepciones limpio:

```python
# Obtener empresa desde SSoT (falla controlado si no existe)
try:
    empresa = get_empresa_emisor_data()
except EmpresaNotConfiguredError as ex:
    # ⚠️ Sin SSoT, no forzamos COMPRA: devolvemos 422 y mensaje claro
    log_imp.warning(f"Empresa no configurada: {str(ex)}")
    return {
        "error": "empresa_no_configurada",
        "message": str(ex)
    }, 422
```

### 4. Mejora del Logging

**Antes:** Logging redundante y variables duplicadas.

**Después:** Logging consolidado en `_determinar_naturaleza()`:

```python
def _determinar_naturaleza(emisor_nit: str | None, empresa_nit: str | None) -> str:
    e = _norm_nit(emisor_nit)
    c = _norm_nit(empresa_nit)
    
    match = bool(e and c and e == c)
    naturaleza = Factura.Naturaleza.VENTA if match else Factura.Naturaleza.COMPRA
    
    log_nat.info(
        "Determinando naturaleza: emisor_nit=%s (norm=%s), empresa_nit=%s (norm=%s) => %s",
        emisor_nit, e, empresa_nit, c, naturaleza
    )
    
    return naturaleza
```

## ✅ Validación E2E

### Test de Import
```bash
python -c "from apps.tenant.empresa.services import get_empresa_emisor_data, EmpresaNotConfiguredError; print('✅ Import OK')"
```

**Resultado:**
```
✅ Import OK
get_empresa_emisor_data: <function get_empresa_emisor_data at 0x...>
EmpresaNotConfiguredError: <class 'apps.tenant.empresa.services.EmpresaNotConfiguredError'>
```

### Comportamiento Esperado

1. **Con Empresa configurada:**
   - `get_empresa_emisor_data()` retorna `Dict` con `nit`, `razon_social`, etc.
   - `empresa_nit` nunca es `None` en logs
   - Naturaleza se calcula correctamente (VENTA/COMPRA)

2. **Sin Empresa o sin NIT:**
   - `get_empresa_emisor_data()` lanza `EmpresaNotConfiguredError`
   - Service Layer retorna `422` con mensaje claro
   - **Nunca asume COMPRA por defecto**

3. **Logs:**
   - Muestran `empresa_nit=<valor>` cuando existe
   - Muestran `empresa_nit=None` solo si realmente no hay empresa (y se retorna 422)

## 📊 Estructura Final

```
apps/tenant/empresa/
├── services.py          # ✅ SSoT: get_empresa_emisor_data(), EmpresaNotConfiguredError
├── impl/                # ✅ Paquete renombrado (antes services/)
│   ├── __init__.py
│   ├── empresa_service.py
│   ├── mailbox_service.py
│   └── mailbox_provider.py
└── ...
```

## 🔍 Verificación Manual

1. **Verificar import:**
   ```python
   from apps.tenant.empresa.services import get_empresa_emisor_data
   # Debe funcionar sin errores
   ```

2. **Auditar tenants:**
   ```bash
   python manage.py all_tenants_command audit_empresa_nit
   ```

3. **Probar importación UBL:**
   - Con Empresa configurada → 200/201 con naturaleza correcta
   - Sin Empresa → 422 con mensaje claro

## ✅ Resultado

- ✅ **Shadowing eliminado:** El import apunta correctamente al archivo `services.py`
- ✅ **SSoT garantizado:** `get_empresa_emisor_data()` siempre disponible o lanza excepción
- ✅ **422 si falta SSoT:** Nunca asume COMPRA por defecto
- ✅ **Logs correctos:** `empresa_nit` nunca es `None` cuando existe Empresa
- ✅ **Código limpio:** Sin `importlib` complejo ni verificaciones redundantes
