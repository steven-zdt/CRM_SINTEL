# APP_ORIGEN_PREFIJOS — Visual Quick Start

**Rule Status:** ✅ ACTIVE (2026-05-15)  
**Enforcement:** Automatic audit + Code review  
**Documentation Level:** 🎓 Foundation (read this first)

---

## The Big Picture

```
┌─────────────────────────────────────────────────────────────┐
│                    SINGLE SOURCE OF TRUTH                   │
│                                                             │
│  apps/tenant/contabilidad/services/selectors.py            │
│  ================================================           │
│  APP_ORIGEN_PREFIJOS = {                                    │
│    'facturas': [...],                                       │
│    'clientes': [...],                                       │
│    'gastos': [...],                                         │
│    'empleados': [...],                                      │
│    'inventario': [...],                                     │
│    'proveedores': [...],                                    │
│  }                                                           │
│                                                             │
└────────────────────────────┬────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ↓                   ↓                   ↓
   ┌─────────┐        ┌──────────┐       ┌─────────┐
   │ Facturas│        │  Gastos  │       │Inventar.│
   │ (reads) │        │ (reads)  │       │ (reads) │
   └─────────┘        └──────────┘       └─────────┘
   
All other apps CONSUME from Contabilidad
None of them DEFINE their own codes
```

---

## The Rule in 10 Seconds

| ✅ DO | ❌ DON'T |
|-------|----------|
| Import from SSoT | Hardcode prefixes |
| `from contabilidad.services.selectors import APP_ORIGEN_PREFIJOS` | `MY_PREFIXES = ['51', '52']` |
| Use `filtrar_cuentas_por_app_origen(qs, 'gastos')` | `qs.filter(codigo__in=[...])` |
| Call API with `app_origen=inventario` | Assume codes in frontend |
| Add new codes to `APP_ORIGEN_PREFIJOS` centrally | Scatter definitions |

---

## 6 Business Apps at a Glance

### FACTURAS (Ventas)
```python
'facturas': [
    # Cartera clientes
    '1305', '130505',
    # Retenciones a favor
    '135515', '135517', '1355',
    # Ingresos operacionales
    '413505', '413510', '4135',
    # Devoluciones y descuentos
    '4175', '418',  # ← Added 2026-05-15
    # IVA generado
    '240805',
    # Retenciones por pagar
    '236505', '236510', '236515', '236525', '236540', '2365',
    '236805', '2368',
]
```
**Purpose:** Ingresos + retenciones + devoluciones  
**Count:** 15 códigos

---

### CLIENTES (Deudores)
```python
'clientes': [
    # Cartera
    '1305', '130505',
    # Ingresos por ventas ← Added 2026-05-15
    '4135', '413505', '413510',
    # Retenciones por cobrar ← Added 2026-05-15
    '1375',
]
```
**Purpose:** Cartera + vinculación a ingresos  
**Count:** 7 códigos (compacto)

---

### GASTOS (Operacionales)
```python
'gastos': [
    # Cuentas por pagar
    '233505', '233550', '233595', '2335',
    # Retenciones practicadas
    '236505', '236510', '236515', '236525', '236540', '2365',
    '236805', '2368',
    # IVA descontable
    '240810',
    # Gastos específicos (many codes)
    '510506', '511005', '511505', '512010',
    '513505', '513520', '513525', '513530', '513535',
    '514510', '514525', '519525', '519530',
    '5110', '5115', '5120', '5130', '5135', '5140', '5145', '5150', '5155', '5195', '5199',
    # Gastos generales (prefijo genérico) ← Added 2026-05-15
    '51',
    # Costos de venta ← Added 2026-05-15
    '6',
]
```
**Purpose:** Cuentas por pagar + gastos administrativos  
**Count:** 30+ códigos

---

### EMPLEADOS (Nómina)
```python
'empleados': [
    # Gastos de personal
    '5105', '5110', '5115', '5120', '5125', '5130', '5140',
    '510506', '510527', '510530', '510533', '510536', '510539', '510568', '510570',
    # Gastos generales (prefijo genérico) ← Added 2026-05-15
    '51',
    # Nómina por pagar
    '2335', '233505', '233550', '233595',
    # Obligaciones laborales
    '25',
    # Retenciones de nómina
    '2370', '2375', '2380',
    # Seguridad social
    '2590',
]
```
**Purpose:** Nómina + pasivos laborales + retenciones  
**Count:** 25+ códigos

---

### INVENTARIO (Activos e Inventarios)
```python
'inventario': [
    # Inventarios
    '143505', '143510', '1435',
    # Costos de ventas
    '613505', '613510', '6135',
    # Ingresos (salida de inventario)
    '413505', '413510', '4135',
    # Depreciación ← Added 2026-05-15 (FIX_DEPRECIACION_ACCOUNT_SEARCH)
    '51',
    # Activos fijos
    '15',
]
```
**Purpose:** Inventarios + costos + activos fijos + depreciación  
**Count:** 11 códigos

---

### PROVEEDORES (Acreedores)
```python
'proveedores': [
    # Proveedores nacionales
    '2205', '220501', '220505',
    # Cuentas por pagar
    '2335', '233505', '233550', '233595',
    # Retenciones practicadas ← Added 2026-05-15
    '2365', '236505', '236510', '236515', '236525', '236540',
    '236805', '2368',
    # Anticipos recibidos ← Added 2026-05-15
    '2805', '280505',
]
```
**Purpose:** Proveedores + retenciones + anticipos  
**Count:** 17 códigos

---

## How the APIs Use It

### Scenario 1: Asset Form Searches for Depreciation

```
User opens "Nuevo Activo Fijo"
  ↓
Clicks field "Cuenta de Depreciación"
  ↓
Starts typing "51"
  ↓
Frontend JavaScript (activos_editor.js):
  setupCuentaAutocomplete({
    codigoPrefix: '51'  ← Request code 51 accounts
  })
  ↓
Calls inventario.api.js:searchCuentas('51', {codigoPrefix: '51'})
  ↓
HTTP Request:
  GET /api/v1/contabilidad/cuentas-contables/
      ?search=51
      &app_origen=inventario    ← Tell backend which app
      &codigo_prefix=51
      &activa=true
  ↓
Backend (contabilidad/api/viewsets.py:CuentaContableViewSet):
  1. Gets all cuentas
  2. Filters by app_origen:
     filtrar_cuentas_por_app_origen(qs, 'inventario')
     ↓
     Allows only: ['143505', '143510', '1435', '613505',
                   '6135', '413505', '413510', '4135', '51', '15']
  3. Filters by codigo_prefix:
     qs.filter(codigo__startswith='51')
     ↓
     Result: 5100, 5105, 5110, 5160, 5199...
  ↓
Returns JSON:
  [
    {codigo: '5100', nombre: 'Gastos de personal', ...},
    {codigo: '5105', nombre: 'Sueldos y salarios', ...},
    ...
  ]
  ↓
Frontend renders dropdown
  ↓
User selects "5160 - Depreciación"
```

---

## Where Everything Lives

### Documentation
```
CLAUDE.md
  └─ Quick reference + patterns

AGENTS.md
  └─ § 18.7 [CRITICAL] APP_ORIGEN_PREFIJOS
     ├─ 18.7.1 Estructura centralizada
     ├─ 18.7.2 Patrones autorizados (3 ejemplos)
     ├─ 18.7.3 Prohibiciones estrictas
     ├─ 18.7.4 Actualización de prefijos
     ├─ 18.7.5 Auditoría periódica
     └─ 18.7.6 Resumen

.agents/skills/backend/app-origen-prefijos-sso-t.md
  └─ Tutorial completo + FAQ

apps/tenant/contabilidad/.agent/docs/
  ├─ RULE_APP_ORIGEN_PREFIJOS_SSoT.md (governance)
  ├─ UPDATE_APP_ORIGEN_PREFIJOS_v2026_05_15.md (changes)
  └─ FIX_DEPRECIACION_ACCOUNT_SEARCH.md (first fix)

tools/
  └─ audit_app_origen_prefijos.py (enforcement script)

memory/
  └─ rule_app_origen_prefijos_sso-t.md (for future reference)
```

### Code
```
apps/tenant/contabilidad/services/selectors.py
  ├─ APP_ORIGEN_PREFIJOS (lines 88-179)
  └─ filtrar_cuentas_por_app_origen(qs, app_origen)

apps/tenant/contabilidad/api/viewsets.py
  └─ CuentaContableViewSet.get_queryset()
     └─ Uses filtrar_cuentas_por_app_origen()

All other apps (inventario, gastos, etc.)
  └─ Import from contabilidad.services.selectors
```

---

## Audit & Enforcement

### Run Audit Script
```bash
python tools/audit_app_origen_prefijos.py
# Output: ✅ All checks passed! APP_ORIGEN_PREFIJOS is properly centralized.

# Or check specific app
python tools/audit_app_origen_prefijos.py --app=gastos

# Verbose output
python tools/audit_app_origen_prefijos.py --verbose
```

### Manual Code Review Checklist
- [ ] No `PREFIJOS = [...]` variables in source app files
- [ ] No hardcoded `codigo__in = [...]` in ViewSets
- [ ] All filtering uses `filtrar_cuentas_por_app_origen()`
- [ ] All imports from `contabilidad.services.selectors`
- [ ] Inline comments explain WHY each app needs codes
- [ ] No test fixtures contradict APP_ORIGEN_PREFIJOS

---

## Timeline & Status

| Date | Event | Status |
|------|-------|--------|
| 2026-05-15 | Fix: Add '51' to inventario (depreciation) | ✅ Done |
| 2026-05-15 | Update: Add codes to all 5 other apps | ✅ Done |
| 2026-05-15 | Rule: Establish APP_ORIGEN_PREFIJOS as SSoT | ✅ Done |
| 2026-05-15 | Document: AGENTS.md § 18.7 + skill file | ✅ Done |
| 2026-05-15 | Audit: Create enforcement script | ✅ Done |
| TBD | Migration: Refactor any hardcoded code | ⏳ As needed |
| TBD | Enforcement: Add pre-commit hook | ⏳ Future |

---

## Key Takeaways

1. **Contabilidad owns the Chart of Accounts** — APP_ORIGEN_PREFIJOS is the single source of truth
2. **No hardcoding** — All apps import from `contabilidad.services.selectors`
3. **Pull Model** — Other apps read from Contabilidad (never push data)
4. **Automatic enforcement** — Audit script detects violations
5. **Clear documentation** — Rules in AGENTS.md § 18.7, patterns in skill file
6. **One update process** — Add new codes only in APP_ORIGEN_PREFIJOS, with documentation

---

## Next Steps

1. ✅ **Read** this document (you're here!)
2. ✅ **Understand** the rule (no hardcoding, use SSoT)
3. 📖 **Study** AGENTS.md § 18.7 for full details
4. 📖 **Review** .agents/skills/backend/app-origen-prefijos-sso-t.md for patterns
5. 🧪 **Test** with `python tools/audit_app_origen_prefijos.py`
6. 📝 **Code Review:** Check your changes follow the rule

---

## Links

- **AGENTS.md § 18.7:** [Full governance rules](../AGENTS.md#187-critical-app_origen_prefijos--single-source-of-truth-sso-t)
- **CLAUDE.md:** [Quick reference](../CLAUDE.md#puc-code-linking--app_origen_prefijos-single-source-of-truth)
- **Skill file:** [app-origen-prefijos-sso-t.md](.agents/skills/backend/app-origen-prefijos-sso-t.md)
- **Audit tool:** [audit_app_origen_prefijos.py](tools/audit_app_origen_prefijos.py)
- **Memory:** [rule_app_origen_prefijos_sso-t.md](.claude/projects/*/memory/rule_app_origen_prefijos_sso-t.md)

