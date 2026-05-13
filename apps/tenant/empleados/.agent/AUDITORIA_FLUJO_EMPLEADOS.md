# [PORTAL] Auditoría y SSoT: Módulo Empleados

**Versión:** 3.6.1  
**Estado:** ⚠️ CORRECCIONES CRITICAS PENDIENTES → ✅ POST-AUDIT READY  
**Ubicación:** `apps/tenant/empleados/`  
**Última Auditoría:** 2026-05-11 (Auditoría Automatizada AGENTS.md v3.6.1)  
**Auditor:** Claude Code (plan procedural alineado con AGENTS.md)

---

## 📑 Documentación Especializada (SSoT)

| Documento | Descripción | Estado |
| :--- | :--- | :--- |
| [📋 Este archivo](AUDITORIA_FLUJO_EMPLEADOS.md) | Portal SSoT + Resultados de Auditoría AGENTS.md | ✅ ACTUALIZADO |
| [📂 Arquitectura y Microtareas](docs/empleados_microtasks_architecture.md) | Desglose atómico de responsabilidades | ✅ |
| [🗺️ Mapas de Flujo](docs/empleados_flow_map.md) | Diagramas Mermaid del ciclo de vida laboral | ✅ |
| [🧠 Lógica de Negocio](docs/empleados_business_logic.md) | SSoT de cálculos proporcionales y validaciones | ✅ |

---

## 🎯 Responsabilidades Core

1. **Ciclo de Vida Laboral**: Gestión secuencial Empleado → Contrato ACTIVO → Devengo (inmutable)
2. **Motor de Cálculo Proporcional**: Devengos y deducciones basados en días laborados (SSoT service layer)
3. **Nómina Multitanda**: Múltiples pagos en mismo periodo con validación solapamiento (máx. 31 días)
4. **Aislamiento Zero Trust**: `empresa_id` verificado en todas las capas (DSV)
5. **Integración Contable (Pull Model)**: `ExtractorNomina` en contabilidad extrae `Devengo` — empleados nunca importa contabilidad
6. **UI Reactiva**: Tabulator Factory + HTMX Offcanvas sin recargas completas

---

## 🔬 PLAN DE AUDITORÍA PROCEDIMENTAL (AGENTS.md v3.6.1)

Auditoría automatizada verificando cada pilar arquitectónico. Ejecutada: 2026-05-11.

---

### CHECK §0 — Cero Caracteres Especiales en Python

**Método:** `grep -rn "[^\x00-\x7F]" apps/tenant/empleados/**/*.py`

| Resultado | Detalle |
|-----------|---------|
| ✅ PASS | Sin emojis ni caracteres multibyte en archivos `.py` core |
| ✅ PASS | `models.py`, `services/`, `api/` en ASCII puro |

---

### CHECK §1 — Service Layer Architecture

**Método:** `ls apps/tenant/empleados/services/`

| Archivo | Estado | Nota |
|---------|--------|------|
| `services/__init__.py` | ✅ OK | Re-exporta correctamente |
| `services/selectors.py` | ✅ OK | QuerySets optimizados con `.only()` |
| `services/crud_service.py` | ✅ OK | `@transaction.atomic` en mutaciones |
| `services/business_service.py` | ✅ OK | Lógica de negocio + DSV |
| `services/api_mixins.py` | ✅ OK | Inyección de dependencias en ViewSet |
| `services/devengo_service.py` | ⚠️ DEUDA | Fuera del patrón FSD (ver §DEUDA-01) |
| `services/empleado_service.py` | ⚠️ DEUDA | Fuera del patrón FSD (ver §DEUDA-01) |
| `services/__init__new.py` | ⚠️ DEUDA | Archivo de transición activo (ver §DEUDA-01) |
| `services_legacy.py` (raíz) | ⚠️ DEUDA | Contiene `anular_devengo_service` en uso (ver §DEUDA-01) |
| `services_facade.py` (raíz) | ⚠️ DEUDA | Fachada de compatibilidad activa (ver §DEUDA-01) |

**Veredito:** ✅ Core Service Layer funcional. ⚠️ Deuda técnica documentada (no bloquea producción).

---

### CHECK §4 — Zero Waste Queries

**Método:** grep `.all()` sin `.only()`, verificar LIST_FIELDS/DETAIL_FIELDS

| Resultado | Detalle |
|-----------|---------|
| ✅ PASS | `selectors.py`: `EMPLEADO_LIST_FIELDS`, `CONTRATO_LIST_FIELDS`, `DEVENGO_LIST_FIELDS` definidos |
| ✅ PASS | Todos los QuerySets usan `.only()` |
| ✅ PASS | Sin `.all()` sin filtro en services core |
| ✅ PASS | `.select_related('empleado')` en DevengoSelector (evita N+1) |

---

### CHECK §5 — CRUD E2E Unidireccional

**Método:** Traza ViewSet → ServiceMixin → business → crud

| Flujo | Estado |
|-------|--------|
| ViewSet delega a ServiceMixin | ✅ OK |
| ServiceMixin invoca business_service | ✅ OK |
| business_service delega a crud_service | ✅ OK |
| crud_service usa `@transaction.atomic` | ✅ OK |
| Response JSON → Tabulator.replaceData() | ✅ OK |

---

### CHECK §6/§7 — Feature-Sliced Design

**Método:** Verificar rutas de templates, JS namespace

| Aspecto | Resultado | Detalle |
|---------|-----------|---------|
| Templates path | ✅ PASS | `templates/tenant/empleados/` (prefijo correcto) |
| JS namespace | ✅ PASS | `window.Sintel.Empleados` aislado |
| JS cross-namespace | ✅ PASS | Sin referencias a `window.Sintel.<OtraApp>` |
| Templates duplicados | ⚠️ WARN | `list.html` y `empleados_list.html` coexisten — verificar cuál es canónico |

---

### CHECK §13 — Seguridad IDOR / DSV

**Método:** grep `empresa_id`, `IsTenantMember`, `resolve_tenant_empresa`

| Aspecto | Resultado | Detalle |
|---------|-----------|---------|
| `empresa_id` en selectors | ✅ PASS | Todos los QuerySets filtran por `empresa_id` |
| `IsTenantMember` en ViewSets | ✅ PASS | Los 3 ViewSets (Empleado, Contrato, Devengo) |
| `IsTenantAdminOrReadOnly` | ✅ PASS | Presente en los 3 ViewSets |
| DSV en business_service | ✅ PASS | `get_empresa_id()` via `SintelDSVMixin` |

---

### CHECK §14 — UUID Lookup Field ❌ CRÍTICO

**Método:** grep `UUIDField` en models.py; grep `lookup_field` en viewsets.py

| Modelo | UUID Field | Estado |
|--------|-----------|--------|
| `Empleado` | No existe | ❌ FAIL |
| `Contrato` | No existe | ❌ FAIL |
| `Devengo` | No existe | ❌ FAIL |

| ViewSet | lookup_field | Estado |
|---------|-------------|--------|
| `EmpleadoViewSet` | `'id'` (línea 56-57) | ❌ FAIL |
| `ContratoViewSet` | `'id'` (línea 471-472) | ❌ FAIL |
| `DevengoViewSet` | `'id'` (línea 840-841) | ❌ FAIL |

**Impacto:** PKs secuenciales expuestos en URLs (`/api/v1/empleados/1/`, `/api/v1/contratos/2/`) → enumeration attack vector.

**Corrección Requerida:** Migración 3-step (nullable → gen_random_uuid → unique) + remoción de `lookup_field='id'`.

---

### CHECK §17 — Bridge Isolation

**Método:** grep `from apps.public` en empleados

| Resultado | Detalle |
|-----------|---------|
| ✅ PASS | Sin imports directos de `apps.public` en código producción |
| ✅ PASS | Aislamiento cross-schema completo |

---

### CHECK §18 — Integración Contable (Pull Model)

**Método:** grep contabilidad en empleados; revisar ExtractorNomina

| Aspecto | Resultado | Detalle |
|---------|-----------|---------|
| empleados → contabilidad (import) | ✅ PASS | Cero imports de contabilidad en empleados |
| ExtractorNomina → Devengo (import) | ✅ PASS | `from apps.tenant.empleados.models import Devengo` |
| Idempotencia | ✅ PASS | Lookup por `documento_origen_id` + `app_label='empleados'` |
| Cuadratura DEBE/HABER | ✅ PASS | DEBE: sueldos, auxilio, otros; HABER: salud, pensión, préstamos, neto_pagar |
| Campos mapeados correctamente | ✅ PASS | `prestamos` (Devengo) ↔ `nomina.prestamos` (Extractor) |
| Campo `descuentos_operativos` | ✅ PASS | En modelo y en extractor |
| `anulado=False` como filtro | ✅ PASS | Solo devengos vigentes se contabilizan |
| `.select_related('empleado').only()` | ✅ PASS | Zero Waste en ExtractorNomina |

---

### CHECK §22/§23 — CSS/JS Isolation

**Método:** grep cross-app static refs en templates y JS

| Aspecto | Resultado | Detalle |
|---------|-----------|---------|
| CSS cross-app en templates | ✅ PASS | Sin `{% static 'facturas/...' %}` ni similares |
| JS cross-app en templates | ✅ PASS | Sin `<script src>` de otra app |
| Namespace JS ajeno | ✅ PASS | Sin llamadas a `window.Sintel.<OtraApp>` |

---

### CHECK — SintelTenantBaseModel

**Método:** grep herencia en models.py

| Modelo | Herencia | Estado |
|--------|----------|--------|
| `Empleado` | `SintelTenantBaseModel` | ✅ OK |
| `Contrato` | `SintelTenantBaseModel` | ✅ OK |
| `Devengo` | `SintelTenantBaseModel` | ✅ OK |

---

## 📊 RESUMEN EJECUTIVO DE AUDITORÍA

| Pilar AGENTS.md | Check | Resultado |
|----------------|-------|-----------|
| §0 No emojis Python | Sin caracteres multibyte | ✅ PASS |
| §1 Service Layer | Core files completos | ✅ PASS |
| §1 Archivos extra | 5 archivos fuera del patrón | ⚠️ DEUDA |
| §4 Zero Waste | `.only()` en todos los selectors | ✅ PASS |
| §5 CRUD E2E | Flujo unidireccional correcto | ✅ PASS |
| §6/§7 FSD | Templates y namespace correctos | ✅ PASS |
| §13 DSV/IDOR | empresa_id + IsTenantMember en todo | ✅ PASS |
| §14 UUID Lookup | **FALTA en 3 modelos y 3 ViewSets** | ❌ CRÍTICO |
| §17 Bridge | Sin imports apps.public | ✅ PASS |
| §18 Pull Model | empleados no importa contabilidad | ✅ PASS |
| §18 ExtractorNomina | Idempotente, cuadrado, campos OK | ✅ PASS |
| §22 CSS Isolation | Sin cross-app CSS | ✅ PASS |
| §23 JS Isolation | Sin cross-app JS | ✅ PASS |
| SintelTenantBaseModel | Los 3 modelos heredan correctamente | ✅ PASS |

**Score: 12/14 PASS — 1 CRÍTICO — 1 DEUDA**

---

## ❌ ISSUE CRÍTICO: §14 UUID Lookup Field

### Descripción

Los modelos `Empleado`, `Contrato` y `Devengo` NO tienen campo `uuid`. Los ViewSets usan `lookup_field='id'`, exponiendo PKs secuenciales en todas las URLs de la API:

```
GET /api/v1/empleados/1/      ← enumerable
GET /api/v1/empleados/2/      ← enumerable
GET /api/v1/contratos/5/      ← enumerable
```

### Solución Aplicada

1. **Modelo `models.py`**: Agregar `uuid = UUIDField(...)` a los 3 modelos
2. **Migración `0002_add_uuid_fields.py`**: 3-step segura (nullable → SQL populate → unique)
3. **ViewSets**: Remover `lookup_field='id'` y `lookup_url_kwarg='id'` de los 3 ViewSets

**Estado:** ✅ CORREGIDO en esta auditoría

---

## ⚠️ DEUDA TÉCNICA §DEUDA-01: Archivos de Transición Legacy

### Archivos Involucrados

| Archivo | Razón de Existencia | Usado Por |
|---------|---------------------|-----------|
| `services_legacy.py` | Contiene `anular_devengo_service()` — función core no migrada | `services/__init__.py`, `dashboard/` |
| `services_facade.py` | Fachada de compatibilidad | Sin consumidores directos (safe to clean) |
| `services/__init__new.py` | Archivo de transición activo | No debe usarse en nuevos imports |
| `services/devengo_service.py` | `upsert_devengo()` — usado en tests | `tests/test_devengos_api_and_service.py` |
| `services/empleado_service.py` | `upsert_empleado()` — función específica | Sin consumidores identificados |

### Riesgo

- **Bajo riesgo en producción**: La función `anular_devengo_service` en `services_legacy.py` sigue funcionando
- **Riesgo de mantenimiento**: Dos rutas de importación para la misma funcionalidad crea confusión
- **Acción recomendada**: Migrar `anular_devengo_service` al `business_service.py` canónico y limpiar legacy — **requiere autorización explícita del usuario**

### Regla AGENTS.md §1

> "Queda PROHIBIDO crear nuevos archivos `.py` fuera de la estructura de Service Layer establecida. Cualquier otro archivo nuevo requiere autorización explícita."

**Estado:** ⚠️ PENDIENTE AUTORIZACIÓN — No se toca sin aprobación

---

## 🔒 Flujo de Integración Contable (§18 Pull Model)

```
apps/tenant/empleados/
  models.py: Devengo
    ├─ salario_base, auxilio_transporte, otros_devengos  → DEBE
    ├─ salud_empleado, pension_empleado, prestamos        → HABER
    ├─ descuentos_operativos                              → HABER
    ├─ neto_pagar                                         → HABER (pasivo)
    └─ anulado=False (filtro para contabilizar)
          ↓
   [PULL — contabilidad extrae, empleados NO importa contabilidad]
          ↓
apps/tenant/contabilidad/
  integracion/extractores/nomina.py: ExtractorNomina
    ├─ extraer_pendientes(): filtra Devengo (anulado=False ∧ no contabilizado)
    ├─ _mapear_a_dto(): Devengo → TransaccionEconomica(NOMINA_PAGO)
    ├─ Idempotencia: lookup por documento_origen_id
    └─ Cuadratura: TOTAL_DEBE == TOTAL_HABER (neto_pagar balancea)
          ↓
  AsientoContable
    ├─ documento_origen_app = 'empleados'
    ├─ documento_origen_modelo = 'Devengo'
    └─ documento_origen_id = devengo.id
```

---

## 📁 Estructura Física

```
apps/tenant/empleados/
├── models.py                         ✅ UUID AGREGADO (post-audit v3.6.1)
├── choices.py                        ✅
├── admin.py                          ✅
├── apps.py                           ✅ label: tenant_empleados
├── services_legacy.py                ⚠️ DEUDA (no tocar sin autorización)
├── services_facade.py                ⚠️ DEUDA (no tocar sin autorización)
├── services/
│   ├── __init__.py                   ✅
│   ├── __init__new.py                ⚠️ DEUDA
│   ├── selectors.py                  ✅ LIST_FIELDS, DETAIL_FIELDS, .only()
│   ├── crud_service.py               ✅ @transaction.atomic
│   ├── business_service.py           ✅ DSV + lógica de negocio
│   ├── api_mixins.py                 ✅ Inyección de servicios
│   ├── devengo_service.py            ⚠️ DEUDA
│   └── empleado_service.py           ⚠️ DEUDA
├── api/
│   ├── viewsets.py                   ✅ lookup_field CORREGIDO (post-audit)
│   ├── serializers.py                ✅
│   └── urls.py                       ✅
├── migrations/
│   ├── 0001_initial.py               ✅
│   └── 0002_add_uuid_fields.py       ✅ NUEVA (post-audit v3.6.1)
├── templates/tenant/empleados/       ✅ FSD correcto
├── static/empleados/js/              ✅ window.Sintel.Empleados
└── .agent/
    ├── AUDITORIA_FLUJO_EMPLEADOS.md  ✅ Este archivo
    └── docs/
```

---

## 🚨 Migraciones Requeridas (Post-Audit)

```bash
# Aplicar migración UUID
python manage.py migrate_schemas

# Resultado esperado:
# ✅ tenant_empleados: 0002_add_uuid_fields.py aplicada
# ✅ Empleado, Contrato, Devengo tienen UUID único
# ✅ ViewSets usan lookup_field="uuid" (heredado de BaseTenantViewSet)
```

---

**Última Actualización:** 2026-05-11  
**Auditor:** Claude Code (Automatizado + Procedimental)  
**Status:** ✅ **AUDITADO — §14 CORREGIDO — DEUDA TÉCNICA DOCUMENTADA**
