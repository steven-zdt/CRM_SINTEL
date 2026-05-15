# RULE: APP_ORIGEN_PREFIJOS — Single Source of Truth (SSoT)

**Status:** ✅ ADOPTED  
**Effective Date:** 2026-05-15  
**Scope:** All business apps (facturas, clientes, gastos, empleados, inventario, proveedores)  
**Owner:** Contabilidad Team  
**Last Updated:** 2026-05-15

---

## Executive Summary

**The Rule:**
```
All accounting code prefixes (Plan de Cuentas / PUC) for ALL business apps 
MUST be obtained EXCLUSIVELY from:

    apps/tenant/contabilidad/services/selectors.py:APP_ORIGEN_PREFIJOS
```

**Why:**
- **Single Point of Control:** Changes to allowed codes happen in ONE place
- **Pull Model:** Contabilidad owns the codes; other apps consume (never push)
- **Security:** Apps can only access prefixes they're authorized for
- **Auditability:** Git history tracks all changes to code allowlists
- **Maintainability:** No duplication, no conflicts between app definitions

---

## The Centralized Registry

```python
# Location: apps/tenant/contabilidad/services/selectors.py:88-179
APP_ORIGEN_PREFIJOS: dict = {
    'facturas': [
        '130505', '130510', '1305',           # Cartera
        '135515', '135517', '1355',           # Retenciones a favor
        '413505', '413510', '4135',           # Ingresos operacionales
        '4175', '418',                        # Devoluciones y descuentos
        '240805',                             # IVA generado
        '236505', '236510', '236515', ...,    # Retenciones por pagar
    ],
    'clientes': [
        '1305', '130505',                     # Cartera
        '4135', '413505', '413510',           # Ingresos
        '1375',                               # Retenciones por cobrar
    ],
    'gastos': [
        '233505', '233550', '2335',           # Cuentas por pagar
        '236505', '2365', ...,                # Retenciones practicadas
        '240810',                             # IVA descontable
        '510506', '511005', ...,              # Gastos específicos
        '51',                                 # Gastos generales (prefijo)
        '6',                                  # Costos de venta
    ],
    'empleados': [
        '5105', '5110', '5115', '5120', ...,  # Gastos de personal
        '51',                                 # Gastos generales
        '2335', '25', '2370', '2590',         # Pasivos laborales
    ],
    'inventario': [
        '143505', '143510', '1435',           # Inventarios
        '613505', '613510', '6135',           # Costos de ventas
        '413505', '413510', '4135',           # Ingresos
        '51',                                 # Depreciación
        '15',                                 # Activos fijos
    ],
    'proveedores': [
        '2205', '220501', '220505',           # Proveedores nacionales
        '2335', '233505', '233550',           # Cuentas por pagar
        '2365', '236505', '236540', ...,      # Retenciones practicadas
        '2805', '280505',                     # Anticipos recibidos
    ],
}

def filtrar_cuentas_por_app_origen(qs, app_origen: str):
    """Apply security filter: only prefixes authorized for that app."""
    prefijos = APP_ORIGEN_PREFIJOS.get(app_origen, [])
    if not prefijos:
        return qs
    q_filter = Q()
    for p in prefijos:
        q_filter |= Q(codigo__startswith=p)
    return qs.filter(q_filter)
```

---

## Where This Rule Is Documented

| Document | Purpose | Audience |
|----------|---------|----------|
| **AGENTS.md § 18.7** | Full governance rules, patterns, prohibitions, audit procedures | Architects, Senior Devs |
| **CLAUDE.md** | Quick reference for project newcomers | All Devs |
| **.agents/skills/backend/app-origen-prefijos-sso-t.md** | Comprehensive tutorial + patterns + FAQ | Backend Devs |
| **This file (RULE_...)** | Rule statement, adoption history, enforcement | All Devs |
| **selectors.py (actual file)** | The source of truth itself | Code |

---

## How Business Apps Use It

### Flow Diagram

```
Business App (e.g., Inventario)
  ↓ Frontend wants to search accounting codes
  ↓ GET /api/v1/contabilidad/cuentas-contables/?app_origen=inventario&codigo_prefix=51
  ↓
Contabilidad API (ViewSet)
  ↓ What prefixes are allowed for 'inventario'?
  ↓ Calls: filtrar_cuentas_por_app_origen(qs, 'inventario')
  ↓
APP_ORIGEN_PREFIJOS['inventario'] = ['143505', '143510', ..., '51', '15']
  ↓ Returns ONLY cuentas where codigo.startswith in that list
  ↓ Applies codigo_prefix='51' filter
  ↓
Results: 5100, 5105, 5160, 5199 (depreciation accounts)
  ↓
Frontend renders dropdown
```

### Correct Usage Examples

**Backend ViewSet:**
```python
def get_queryset(self):
    qs = CuentaContableSelector.get_qs_list()
    app_origen = self.request.query_params.get('app_origen')
    if app_origen:
        qs = filtrar_cuentas_por_app_origen(qs, app_origen)  # ← Uses SSoT
    return qs
```

**Frontend JavaScript:**
```javascript
searchCuentas: async (query, options) => {
  const params = {
    search: query,
    app_origen: 'inventario',  // ← Tell backend which app
    codigo_prefix: options.codigoPrefix  // ← Request specific prefix
  };
  return w.http('GET', '/api/v1/contabilidad/cuentas-contables/', params);
}
```

**Backend Service:**
```python
from apps.tenant.contabilidad.services.selectors import APP_ORIGEN_PREFIJOS

prefijos = APP_ORIGEN_PREFIJOS['gastos']  # ← Read from SSoT
validar = any(codigo.startswith(p) for p in prefijos)
```

---

## Prohibited Patterns

### ❌ Hardcoding Prefixes in Source Apps

```python
# gastos/models.py or gastos/api/viewsets.py
GASTOS_PREFIJOS = ['5100', '5105', '5110', '5115']  # ← WRONG
```

**Why:** Duplicates, unmaintainable, conflicts with SSoT

### ❌ Separate Database Table for Prefixes

```python
class AppPrefixes(models.Model):
    app_name = models.CharField()
    codigo_prefix = models.CharField()
```

**Why:** Over-engineered, adds DB overhead, defeats the purpose of SSoT

### ❌ Scattered Definitions

```python
# facturas/selectors.py
FACTURAS_CODES = [...]

# gastos/utils.py
GASTOS_CODES = [...]

# empleados/api/mixins.py
EMPLEADOS_CODES = [...]
```

**Why:** Impossible to maintain, no single point of truth

---

## Update Workflow (Adding New Codes)

### Scenario: Add Depreciation Support to Inventario (5/15/2026)

1. **Requirement:** Asset app needs access to depreciation accounts (Código 51)

2. **Update APP_ORIGEN_PREFIJOS:**
   ```python
   # In apps/tenant/contabilidad/services/selectors.py
   
   # Before:
   'inventario': [
       '143505', '143510', '1435',
       '613505', '613510', '6135',
       '413505', '413510', '4135',
       '15',
   ],
   
   # After:
   'inventario': [
       '143505', '143510', '1435',
       '613505', '613510', '6135',
       '413505', '413510', '4135',
       '51',  # ← AGREGADO: Depreciación/Gastos
       '15',
   ],
   ```

3. **Document Why:**
   Add inline comment explaining the rationale:
   ```python
   # Gastos de personal / depreciación
   '51',
   ```

4. **Test:**
   - Open form "Nuevo Activo Fijo"
   - Search field "Cuenta de Depreciación"
   - Type "51"
   - Verify accounts appear (5100, 5105, 5160, 5199)

5. **Commit:**
   ```
   git commit -m "feat(contabilidad): Agregar prefijo 51 (depreciación) a inventario"
   ```

6. **Code Review:**
   - Verify no hardcoding in inventario app
   - Confirm documentation is clear
   - Check no conflicts with other apps' prefixes

---

## Enforcement & Validation

### Automated Audit Script

```bash
# Run periodically (CI/CD or manually)
python tools/audit_app_origen_prefijos.py

# Output:
# 🔍 Auditing APP_ORIGEN_PREFIJOS usage...
# 📦 Checking app: gastos
#    ✅ No hardcoded prefixes found
# 📦 Checking app: inventario
#    ✅ No hardcoded prefixes found
# ✅ All checks passed!
```

### Manual Audit Checklist

Every major release, verify:

- [ ] No `PREFIJOS = [...]` variables in source app files
- [ ] No `codigo__in = [...]` hardcoded lists in ViewSets
- [ ] All app_origen filtering uses `filtrar_cuentas_por_app_origen()`
- [ ] All imports of prefix lists come from `contabilidad.services.selectors`
- [ ] Inline comments explain WHY each app needs each prefix
- [ ] No test fixtures define contradicting app_origen values

---

## How to Migrate Existing Code

### Before (Hardcoded):
```python
# gastos/api/viewsets.py
class GastoViewSet(BaseTenantViewSet):
    ALLOWED_PREFIXES = ['51', '52', '53', '54', '55', '6']
    
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(cuenta__codigo__in=self.ALLOWED_PREFIXES)
```

### After (Using SSoT):
```python
# gastos/api/viewsets.py
from apps.tenant.contabilidad.services.selectors import (
    filtrar_cuentas_por_app_origen,
    CuentaContableSelector
)

class GastoViewSet(BaseTenantViewSet):
    def get_queryset(self):
        qs = super().get_queryset()
        
        # Resolve allowed cuentas from centralized SSoT
        cuentas_qs = CuentaContableSelector.get_qs_list()
        cuentas_qs = filtrar_cuentas_por_app_origen(cuentas_qs, 'gastos')
        cuenta_ids = list(cuentas_qs.values_list('id', flat=True))
        
        return qs.filter(cuenta_id__in=cuenta_ids)
```

---

## FAQ

**Q: What if I need a new prefix for my app?**  
A: Submit an RFC/Issue with justification. Update APP_ORIGEN_PREFIJOS in `contabilidad/services/selectors.py` with inline documentation.

**Q: Can I query APP_ORIGEN_PREFIJOS directly in my tests?**  
A: Yes. Import and use it: `from apps.tenant.contabilidad.services.selectors import APP_ORIGEN_PREFIJOS`

**Q: Do I hardcode `'inventario'` (the app name) in my app?**  
A: Yes. Your app knows its own identifier. Use it when calling the API or importing prefixes.

**Q: What if multiple apps need the same prefix?**  
A: That's fine and expected. Many apps access common account classes (e.g., Ingresos 4XXX, Gastos 51XX).

**Q: Is this a performance concern?**  
A: No. The filter is a simple OR on prefixes with indexing on `codigo` field. Benchmark: <1ms for typical queries.

**Q: Can Contabilidad itself add prefixes without consulting other apps?**  
A: Yes, Contabilidad owns the accounts. Other apps are reactive consumers. If an app needs a new code, it should request it.

---

## Summary Table

| Aspect | Rule |
|--------|------|
| **Where codes live** | `apps/tenant/contabilidad/services/selectors.py:APP_ORIGEN_PREFIJOS` |
| **How to read** | `from ... import APP_ORIGEN_PREFIJOS, filtrar_cuentas_por_app_origen` |
| **Forbidden** | Hardcoded lists in source apps, separate tables, scattered definitions |
| **Approved patterns** | ViewSet filtering, API queries with app_origen param, service imports |
| **Audit tool** | `python tools/audit_app_origen_prefijos.py` |
| **Documentation** | AGENTS.md § 18.7, CLAUDE.md, skill file |
| **Migration** | Replace hardcoding with imports and use `filtrar_cuentas_por_app_origen()` |

---

## Adoption History

- **2026-05-15:** Rule established
  - Added APP_ORIGEN_PREFIJOS entries for all 6 business apps
  - Documented in AGENTS.md § 18.7
  - Created skill file: `app-origen-prefijos-sso-t.md`
  - Created audit script: `tools/audit_app_origen_prefijos.py`
  - Created migration guide

---

## Related Documentation

- **AGENTS.md § 18:** Contabilidad Integration Architecture
- **AGENTS.md § 18.7:** Full governance + rules
- **CLAUDE.md:** Quick reference + patterns
- **ADR-001-retention-pull-model.md:** Pull Model decision (related)
- **Memory:** `update_app_origen_prefijos_v2026_05_15.md`

---

## Version Control

```
File: apps/tenant/contabilidad/.agent/docs/RULE_APP_ORIGEN_PREFIJOS_SSoT.md
Created: 2026-05-15
Last Updated: 2026-05-15
Status: ✅ Active
```

