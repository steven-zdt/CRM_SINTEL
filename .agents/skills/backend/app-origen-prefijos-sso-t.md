# Skill: APP_ORIGEN_PREFIJOS — Single Source of Truth (SSoT)

**Category:** Backend Architecture / Contabilidad Integration  
**Complexity:** Intermediate  
**Audience:** Backend developers, data engineers, system designers

---

## Overview

`APP_ORIGEN_PREFIJOS` is the **centralized registry** of all accounting code prefixes (Plan de Cuentas / PUC) allowed for each business app. It lives in ONE place and is consumed everywhere:

```
Source of Truth
  ↓
apps/tenant/contabilidad/services/selectors.py:APP_ORIGEN_PREFIJOS
  ↓
All other apps read from here
```

---

## The Rule (Non-Negotiable)

> **All accounting code prefixes for ALL business apps MUST be obtained from `APP_ORIGEN_PREFIJOS` in `contabilidad/services/selectors.py`.**

❌ **Never hardcode prefixes** in source apps (facturas, gastos, inventario, etc.)  
❌ **Never store prefixes** in separate files or modules  
❌ **Never duplicate** the list across apps

✅ **Always import** from `contabilidad.services.selectors`  
✅ **Always validate** via `filtrar_cuentas_por_app_origen()`  
✅ **Always delegate** to Contabilidad for truth

---

## What Is APP_ORIGEN_PREFIJOS?

A Python dictionary mapping app names to lists of allowed PUC code prefixes:

```python
# apps/tenant/contabilidad/services/selectors.py
APP_ORIGEN_PREFIJOS: dict = {
    'facturas': [
        '130505', '130510', '1305',      # Cartera clientes
        '135515', '135517', '1355',      # Retenciones a favor
        '413505', '413510', '4135',      # Ingresos operacionales
        '4175', '418',                   # Devoluciones y descuentos
        '240805',                        # IVA generado
        '236505', '2365', '236805', '2368',  # Retenciones por pagar
    ],
    'clientes': [
        '1305', '130505',                # Cartera clientes
        '4135', '413505', '413510',      # Ingresos por ventas
        '1375',                          # Retenciones por cobrar
    ],
    'gastos': [
        '233505', '233550', '2335',      # Cuentas por pagar
        '236505', '2365',                # Retenciones practicadas
        '240810',                        # IVA descontable
        '510506', '5110', '5115', ...,   # Gastos administrativos (many)
        '51',                            # Gastos generales (prefijo genérico)
        '6',                             # Costos de venta
    ],
    'empleados': [
        '5105', '5110', '5115', '5120',  # Gastos de personal
        '51',                            # Gastos generales
        '2335', '25', '2370', '2590',    # Pasivos laborales
    ],
    'inventario': [
        '143505', '143510', '1435',      # Inventarios
        '613505', '613510', '6135',      # Costos de ventas
        '413505', '413510', '4135',      # Ingresos
        '51',                            # Depreciación
        '15',                            # Activos fijos
    ],
    'proveedores': [
        '2205', '220501', '220505',      # Proveedores nacionales
        '2335', '233505', '233550',      # Cuentas por pagar
        '2365', '236505', '2368',        # Retenciones practicadas
        '2805', '280505',                # Anticipos recibidos
    ],
}
```

**Key Principles:**
- **Per-app whitelist:** Each app only sees prefixes it's authorized to use
- **Security:** Prevents accidental cross-domain access to restricted accounts
- **Centralization:** Single point of update when adding new accounts
- **Auditability:** Changes are tracked in git history

---

## How to Access (Patterns)

### Pattern 1: Backend ViewSet — Filter by App Origin

```python
# In contabilidad/api/viewsets.py:CuentaContableViewSet

from apps.tenant.contabilidad.services.selectors import (
    filtrar_cuentas_por_app_origen,
    CuentaContableSelector
)

class CuentaContableViewSet(BaseTenantViewSet):
    def get_queryset(self):
        qs = CuentaContableSelector.get_qs_list()
        
        # Frontend sends: ?app_origen=inventario&codigo_prefix=51
        app_origen = self.request.query_params.get('app_origen', '').strip()
        if app_origen:
            # ← Automatically filters to allowed prefixes for that app
            qs = filtrar_cuentas_por_app_origen(qs, app_origen)
        
        codigo_prefix = self.request.query_params.get('codigo_prefix', '').strip()
        if codigo_prefix:
            qs = qs.filter(codigo__startswith=codigo_prefix)
        
        return qs
```

**Flow:**
1. Frontend sends `app_origen=inventario&codigo_prefix=51`
2. Backend calls `filtrar_cuentas_por_app_origen(qs, 'inventario')`
3. Filter applies: `codigo__startswith in ['143505', '143510', '1435', '613505', '6135', '4135', '51', '15']`
4. Then applies: `codigo__startswith='51'`
5. Returns matching accounts (5100, 5105, 5160, 5199, etc.)

---

### Pattern 2: Frontend JavaScript — Declare App Origin

```javascript
// In inventario/static/inventario/js/inventario.api.js

w.Sintel.Inventario.API = {
  searchCuentas: async (query, options = {}) => {
    const params = {
      search: query,
      app_origen: 'inventario',  // ← Declares which app is calling
      activa: 'true'
    };
    
    if (options.codigoPrefix) {
      params.codigo_prefix = options.codigoPrefix;  // e.g., '51'
    }
    
    // Backend resolves allowed prefixes automatically
    return w.http('GET', '/api/v1/contabilidad/cuentas-contables/', params);
  }
};
```

**Usage in a form:**
```javascript
// In activos_editor.js
w.Sintel.Inventario.Utils.setupCuentaAutocomplete({
  inputSelector: '#activo-cuenta-depreciacion-busqueda',
  resultsSelector: '#activo-cuenta-depreciacion-resultados',
  uuidSelector: '#activo-cuenta-depreciacion-uuid',
  codigoPrefix: '51'  // ← Request only code 51-based accounts
});
```

---

### Pattern 3: Backend Service — Direct Import

```python
# In gastos/services/business_service.py or extractores/

from apps.tenant.contabilidad.services.selectors import (
    APP_ORIGEN_PREFIJOS,
    filtrar_cuentas_por_app_origen,
    CuentaContableSelector
)

class ExtractorGastos:
    def __init__(self, empresa_id: int):
        self.empresa_id = empresa_id
    
    def extraer_cuentas_permitidas(self):
        # Get all cuentas allowed for 'gastos' app
        qs = CuentaContableSelector.get_qs_list(empresa_id=self.empresa_id)
        qs = filtrar_cuentas_por_app_origen(qs, 'gastos')
        return list(qs)
    
    def validar_cuenta_es_gasto(self, cuenta_codigo: str) -> bool:
        # Verify cuenta is in 'gastos' allowlist
        prefijos = APP_ORIGEN_PREFIJOS['gastos']
        return any(cuenta_codigo.startswith(p) for p in prefijos)
```

---

## Anatomy of APP_ORIGEN_PREFIJOS Structure

```python
APP_ORIGEN_PREFIJOS: dict = {
    'app_name': [
        # Specific codes (most common)
        '1305', '130505',
        
        # Specific codes with ranges/comments
        '2205', '220501', '220505',  # Only these 3
        
        # Generic prefixes (for flexibility)
        '51',     # ← Matches 5100, 5105, 5160, 5199, etc.
        '4',      # ← Matches 4000-4999 (all income)
        
        # Prefix ranges (implicit via startswith)
        '236',    # ← Matches 2360, 2365, 236505, etc.
    ]
}
```

---

## Update Workflow (Adding New Prefix)

### Scenario: Inventario needs Depreciation Codes

1. **Identify requirement:** Asset app wants to link to depreciation accounts (Código 51)

2. **Update APP_ORIGEN_PREFIJOS:**
   ```python
   # Before
   'inventario': [
       '143505', '143510', '1435',
       '613505', '613510', '6135',
       '413505', '413510', '4135',
       '15',  # Activos fijos
   ],
   
   # After
   'inventario': [
       '143505', '143510', '1435',
       '613505', '613510', '6135',
       '413505', '413510', '4135',
       '51',   # ← AGREGADO: Depreciación
       '15',   # Activos fijos
   ],
   ```

3. **Document why:**
   ```python
   # Gastos de personal / depreciación
   '51',
   ```

4. **Test in browser:**
   - Open "Nuevo Activo Fijo" form
   - Search "Cuenta de Depreciación" → type "51"
   - Verify accounts like 5100, 5105, 5160 appear

5. **Commit:**
   ```
   git commit -m "feat(contabilidad): Agregar prefijo 51 (depreciación) a inventario"
   ```

---

## Prohibited Patterns (❌ Never Do This)

### ❌ Pattern 1: Hardcoded in Source App

```python
# ❌ WRONG — in gastos/models.py or gastos/api/viewsets.py
GASTOS_PREFIJOS = ['5100', '5105', '5110', '5115', '5120', '5125', '5130', '5140']
GASTOS_PREFIJOS += ['51', '6']  # ← Scattered, not controlled

def buscar_cuentas_gastos():
    return CuentaContable.objects.filter(codigo__in=GASTOS_PREFIJOS)
```

**Why it's wrong:**
- Duplicates the source of truth
- Hard to maintain (change in 2 places)
- Different apps might have conflicting definitions
- Not auditable

---

### ❌ Pattern 2: Dynamic Calculation

```python
# ❌ WRONG — derived prefixes not tied to source
def get_permitidos(app):
    if app == 'gastos':
        # Derived from some other logic → mismatch risk
        return ['51', '52', '53', '54', '55']
    elif app == 'inventario':
        return ['14', '15', '61']  # ← Different on next run?
```

---

### ❌ Pattern 3: Separate Database Table

```python
# ❌ WRONG — AppPrefixes table (over-engineered)
class AppPrefixes(models.Model):
    app_name = models.CharField(max_length=50)
    codigo_prefix = models.CharField(max_length=10)
    description = models.TextField()

# Now every request hits the DB → overhead
prefixes = AppPrefixes.objects.filter(app_name='gastos').values_list('codigo_prefix')
```

---

### ❌ Pattern 4: Hardcoded in Tests/Fixtures

```python
# ❌ WRONG — seed data with assumptions
factories.CuentaFactory(codigo='5100', nombre='Gastos', app_origen='gastos')
factories.CuentaFactory(codigo='5105', nombre='Sueldos', app_origen='gastos')
# ← These app_origen fields don't exist; mismatch with APP_ORIGEN_PREFIJOS
```

---

## Audit Checklist

To verify your codebase follows this pattern:

```bash
# 1. Search for hardcoded PREFIJOS variables in source apps
grep -r "PREFIJOS\|CODIGO.*PREFIJO\|app_origen.*=" \
  --include="*.py" \
  apps/tenant/{facturas,clientes,gastos,empleados,inventario,proveedores} \
  | grep -v "contabilidad/services/selectors.py"

# 2. If you find matches → they should be removed and replaced with imports from selectors.py

# 3. Search for direct codigo__in lookups without using filtrar_cuentas_por_app_origen
grep -r "codigo__in\|codigo__startswith" \
  --include="*.py" \
  apps/tenant/{facturas,clientes,gastos,empleados,inventario,proveedores}/api/ \
  | grep -v "filtrar_cuentas_por_app_origen"

# 4. If found → refactor to use filtrar_cuentas_por_app_origen
```

---

## Migration Path (If Refactoring Existing Code)

**Scenario:** You find hardcoded prefixes in `gastos/api/viewsets.py`

**Before:**
```python
# gastos/api/viewsets.py
GASTOS_CODES = ['510506', '511005', '511505', '512010', '5110', '5115', '51', '6']

class GastoViewSet(BaseTenantViewSet):
    def get_queryset(self):
        qs = Gasto.objects.all()
        # Filter to allowed cuentas (hardcoded)
        return qs.filter(cuenta__codigo__in=GASTOS_CODES)
```

**After:**
```python
# gastos/api/viewsets.py
from apps.tenant.contabilidad.services.selectors import (
    filtrar_cuentas_por_app_origen,
    CuentaContableSelector
)

class GastoViewSet(BaseTenantViewSet):
    def get_queryset(self):
        qs = Gasto.objects.all()
        
        # Filter cuentas to allowed prefixes for gastos
        cuentas = CuentaContableSelector.get_qs_list()
        cuentas = filtrar_cuentas_por_app_origen(cuentas, 'gastos')
        cuenta_ids = list(cuentas.values_list('id', flat=True))
        
        return qs.filter(cuenta_id__in=cuenta_ids)
```

Or simpler if just validating:
```python
from apps.tenant.contabilidad.services.selectors import APP_ORIGEN_PREFIJOS

class GastoViewSet(BaseTenantViewSet):
    def validar_cuenta_es_permitida(self, codigo: str) -> bool:
        prefijos = APP_ORIGEN_PREFIJOS['gastos']
        return any(codigo.startswith(p) for p in prefijos)
```

---

## FAQ

**Q: Can I import APP_ORIGEN_PREFIJOS in my app?**  
A: Yes. Import `from apps.tenant.contabilidad.services.selectors import APP_ORIGEN_PREFIJOS` to read the list.

**Q: Can I modify APP_ORIGEN_PREFIJOS from other apps?**  
A: No. Only `contabilidad/services/selectors.py` owns this dictionary.

**Q: What if my app needs a code not in APP_ORIGEN_PREFIJOS?**  
A: Request it in an RFC or issue. Update APP_ORIGEN_PREFIJOS in `contabilidad/services/selectors.py` with documentation of why.

**Q: Do I hardcode the app_origen string in my app?**  
A: Yes. Your app knows its own name (e.g., `'inventario'`, `'gastos'`). Use it when calling the API or filtering.

**Q: What if another app uses the same prefixes as mine?**  
A: That's OK. Many apps might access Ingresos (4XXX) or Gastos (51XX). The purpose is security (prevent invalid codes), not exclusivity.

**Q: Performance: Is filtrar_cuentas_por_app_origen expensive?**  
A: No. It's a simple OR filter on prefixes. Use with `.only()` and indexing on `codigo` for fast lookups.

---

## References

- **AGENTS.md § 18.7:** Full governance + rules
- **CLAUDE.md:** Quick reference
- **selectors.py:** The actual dictionary
- **contabilidad/api/viewsets.py:CuentaContableViewSet.get_queryset():** Real-world example

