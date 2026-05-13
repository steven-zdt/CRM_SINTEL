# [PORTAL] Auditoría y SSoT: Módulo Proveedores (Gestión de Acreedores)

**Versión:** 3.6.1 (Backend/API + UI/UX Premium + Delete Seguro)  
**Estado:** ✅ PRODUCTION READY (Premium Redesign + Hard Delete Cascada)  
**Ubicación:** `apps/tenant/proveedores/`  
**Última Auditoría:** 2026-05-11  
**Última Actualización (Código):** 2026-05-11 (v3.6.1: UI Premium v3.6 + Hard Delete Cascada)

---

## 📑 Documentación Especializada (SSoT)

| Documento | Descripción | Version | Estado |
| :--- | :--- | :--- | :--- |
| [✅ Estado Actual v3.6.0](ESTADO_ACTUAL_v360.md) | Layout premium, formulario reorganizado, headers con badges | v3.6.0 | ✅ READY |
| [✅ Delete Seguro v3.6.1](DELETE_SEGURO_v360.md) | Hard delete con cascada automática, on_delete=CASCADE | v3.6.1 | ✅ READY |
| [🔒 Garantía de Seguridad DSV](GARANTIA_SEGURIDAD_DSV.md) | Double Semantic Verification (IDOR prevention) | v3.5.0 | ✅ READY |
| [📂 Arquitectura y Microtareas](docs/proveedores_microtasks_architecture.md) | Desglose atómico de responsabilidades | v3.5.0 | ✅ |
| [🗺️ Mapas de Flujo](docs/proveedores_flow_map.md) | Diagramas Mermaid de ciclo de vida | v3.5.0 | ✅ |
| [🧠 Lógica de Negocio](docs/proveedores_business_logic.md) | Reglas, validaciones y cálculos | v3.5.0 | ✅ |

---

## 🎯 Responsabilidades Core

El módulo de **Proveedores** gestiona el directorio y relaciones con acreedores bajo conformidad fiscal colombiana.

1. **Gestión de Identidad Fiscal:** Almacenamiento de identificación legal (NIT, CC, etc.) con SSoT por empresa
2. **Normativa Tributaria:** Campos obligatorios colombianos (régimen, CIIU, responsable IVA, gran contribuyente, autoretenedor)
3. **Validación por Tenant:** Cada empresa tiene su propio catálogo de proveedores (aislamiento via empresa_id)
4. **Bancarización:** Información de cuenta para transferencias y pagos
5. **Mapeo Contable:** Vínculo a cuentas por pagar (Clase 2, Nivel-6 NIIF) para integración contable
6. **UUID Lookup Field (AGENTS.md §14):** Prevención de enumeration attacks
7. **Double Semantic Verification (AGENTS.md §13):** Protección IDOR en todas las mutaciones
8. **CSS/JS Isolation (AGENTS.md §22/§23):** Aislamiento de estilos y scripts por app
9. **Hard Delete Cascada (v3.6.1):** Eliminación segura de proveedor + documentos soporte

---

## 📌 Cambios Recientes (v3.6.1 - 2026-05-11)

### ✅ UI/UX Premium Redesign v3.6.0

**Propósito:** Optimizar distribución horizontal, mejorar jerarquía visual, presentación premium

**Cambios Implementados:**
- ✅ **Flexbox Footer:** Offcanvas usa `d-flex flex-column`, body `flex-grow-1 overflow-y-auto`, footer `flex-shrink-0` (siempre visible)
- ✅ **Headers Premium:** Badge de color por sección + icono + `fw-semibold`
- ✅ **Distribución Horizontal Optimizada:**
  - Tipo Persona (col-3) | Tipo Doc (col-3) | Número (col-4) | DV (col-2)
  - Razón Social (col-7) | Comercial (col-5)
  - Email (col-5) | Teléfono (col-4) | Estado (col-3)
  - Plazo (col-2 + "días") | Banco (col-4) | Tipo (col-3) | Número (col-3)
- ✅ **Switches Alineados:** Fila única, flexbox, h-100 uniforme
- ✅ **Panel Retenciones:** 3 cards col-md-4, bg-success-subtle
- ✅ **HTML Bug Fix:** Tag `<div>` roto en "Agente Retenedor" corregido

**Archivo Modificado:** `offcanvas_form.html` (v3.6 - 403 líneas optimizadas)

**Estado:** ✅ IMPLEMENTADO Y VALIDADO

---

### ✅ Hard Delete con Cascada Automática v3.6.1

**Problema:** Error `Cannot delete some instances of model 'Proveedor'` cuando hay `DocumentoSoporte` asociados

**Solución:**
- ✅ Cambio: `on_delete=models.PROTECT` → `on_delete=models.CASCADE`
- ✅ Migración: `apps/tenant/gastos/migrations/0012_alter_documentosoporte_proveedor.py`
- ✅ Business Service: `eliminar_proveedor()` hace hard delete directo (CASCADE automático)

**Comportamiento:**
- Proveedor activo → Error: "Márquelo como inactivo primero"
- Proveedor inactivo sin gastos → ✅ Hard delete (eliminado físicamente)
- Proveedor inactivo con gastos → ✅ Hard delete + CASCADE (elimina DocumentoSoporte asociados)

**Resultado:** Proveedor se elimina **completamente de la BD** con cascada automática

**Estado:** ✅ IMPLEMENTADO Y PROBADO

---

### ✅ CSS/JS Isolation (AGENTS.md §22/§23)

**Propósito:** Prevenir estilos y scripts cross-app

**Implementación:**
- ✅ **CSS-ISOLATION (§22):** Templates de proveedores NO cargan CSS de otras apps
- ✅ **JS-ISOLATION (§23):** Namespace `window.Sintel.Proveedores` aislado, sin llamadas cross-app
- ✅ **Compliance:** Solo Bootstrap CDN + helpers en `core/static/core/js/`

**Resultado:** App proveedores es propiedad exclusiva, cero dependencias cross-app

**Estado:** ✅ IMPLEMENTADO

---

### ✅ UUID Lookup Field (AGENTS.md §14)

- **Propósito:** Cumplir AGENTS.md §14 - UUID como lookup field, no PK secuencial
- **Implementación:** 
  - Modelo: `Proveedor.uuid = UUIDField(unique=True, db_index=True)`
  - Migración: `0002_add_uuid_to_proveedor.py` (población segura con gen_random_uuid)
  - ViewSet: Hereda `lookup_field="uuid"` de BaseTenantViewSet
- **Beneficio:** Imposible enumeration attacks
- **Estado:** ✅ IMPLEMENTADO Y VALIDADO

---

### ✅ Service Layer Verificado (AGENTS.md §1)

- ✅ `selectors.py`: LIST_FIELDS, DETAIL_FIELDS (SSoT), QuerySets con `.only()`
- ✅ `crud_service.py`: Persistencia atómica (@transaction.atomic)
- ✅ `business_service.py`: Lógica de negocio + DSV + eliminación cascada
- ✅ `api_mixins.py`: ProveedorServiceMixin
- ✅ `services/__init__.py`: Reexportaciones limpias
- **Estado:** ✅ ARQUITECTURA CORRECTA

---

## 🛠️ Stack Tecnológico (v3.6.1)

```
Backend
├─ Django DRF (REST API)
├─ django-tenants (Multi-tenant PostgreSQL)
├─ Service Layer (selectors + crud + business)
└─ Hard Delete + CASCADE (DB-level cascada automática)

Frontend
├─ Vanilla JS ES6+ (Namespace: window.Sintel.Proveedores)
├─ Tabulator.js (Grid/tabla)
├─ Bootstrap 5.3.2 (UI Premium v3.6)
├─ HTMX (Server-driven fragments)
└─ Flexbox Footer (siempre visible)

Storage
├─ PostgreSQL (Multi-tenant via django-tenants)
├─ SintelTenantBaseModel (empresa_id obligatorio)
└─ CASCADE FK DocumentoSoporte → Proveedor
```

---

## 🏗️ Estructura de Servicios y APIs

### Servicios Principales

| Servicio | Responsabilidad | Patrón |
|---|---|---|
| `ProveedorSelector` | QuerySets optimizados con `.only()` / `.defer()` | @staticmethod |
| `ProveedorCRUDService` | Persistencia transactional (@transaction.atomic) | @staticmethod |
| `ProveedorBusinessService` | Lógica de negocio + DSV + validaciones + delete cascada | @staticmethod |
| `ProveedorServiceMixin` | Inyección de servicios en ViewSet | @property |

### Endpoints Estratégicos

| Endpoint | Método | Responsabilidad | Nota |
|---|---|---|---|
| `/api/v1/proveedores/` | GET | Listar proveedores filtrados por empresa_id | Zero Waste: `.only()` |
| `/api/v1/proveedores/` | POST | Crear proveedor (con DSV) | Service Layer |
| `/api/v1/proveedores/{uuid}/` | PATCH | Actualizar proveedor (con DSV) | UUID Lookup |
| `/api/v1/proveedores/{uuid}/` | DELETE | Eliminar proveedor (hard delete + CASCADE) | v3.6.1 |
| `/api/v1/proveedores/{uuid}/` | GET | Detalle de proveedor (con DSV) | IsTenantMember |

---

## 🚀 Validación de Compliance AGENTS.md v3.6.1

### ✅ §1 (Service Layer)
- [x] `selectors.py` con LIST_FIELDS, DETAIL_FIELDS (SSoT)
- [x] `crud_service.py` con @transaction.atomic
- [x] `business_service.py` con reglas de negocio
- [x] `api_mixins.py` con ProveedorServiceMixin
- [x] `__init__.py` con reexportaciones

### ✅ §4 (Zero Waste - .only())
- [x] Todos los QuerySets usan `.only()` / `.defer()`
- [x] Selectors definen LIST_FIELDS, DETAIL_FIELDS
- [x] No hay `.all()` sin `.only()`

### ✅ §5 (CRUD E2E)
- [x] ViewSet → ServiceMixin → business_service → crud_service (unidireccional)
- [x] Frontend captura payload → POST/PATCH/DELETE → Response → DOM update
- [x] Delete cascada con eliminación física

### ✅ §6 (FSD - Feature-Sliced)
- [x] Templates en `templates/tenant/proveedores/` (prefijo tenant/)
- [x] JS en `static/proveedores/js/`
- [x] Namespace: `window.Sintel.Proveedores`

### ✅ §13 (IDOR Prevention)
- [x] ViewSet + BusinessService ejecutan DSV
- [x] Selector filtra por empresa_id en toda query
- [x] IsTenantMember permission obligatorio
- [x] resolve_tenant_empresa() en todos los endpoints

### ✅ §14 (UUID Lookup)
- [x] `lookup_field = "uuid"` (heredado de BaseTenantViewSet)
- [x] Modelo tiene `uuid = UUIDField(unique=True)`
- [x] Migración aplicada con población segura

### ✅ §17 (Bridge Isolation)
- [x] NO hay imports directos de `apps.public`
- [x] Usa bridge: `apps.tenant.core.services.membership`
- [x] Completo aislamiento cross-schema

### ✅ §22 (CSS-Isolation)
- [x] Templates NO cargan CSS de otras apps
- [x] Solo Bootstrap CDN + core global
- [x] Cero cross-app stylesheets

### ✅ §23 (JS-Isolation)
- [x] Namespace `window.Sintel.Proveedores` aislado
- [x] Cero llamadas a `window.Sintel.<OtraApp>`
- [x] Cero imports de JS de otras apps

---

## 📋 Modelo de Datos (v3.6.1)

### Proveedor

```
Campos UUID/Lookup:
├─ uuid: UUIDField (unique, db_index)
└─ id: BigAutoField (PK interno)

Campos Identificación (SSoT):
├─ tipo_documento: NIT | CC | CE | PA
├─ numero_documento: Sin dígito verificador
├─ digito_verificacion: (opcional)
└─ Constraint: UNIQUE(empresa, tipo_documento, numero_documento)

Campos Contexto (Normativa Colombia):
├─ razon_social: Nombre legal
├─ nombre_comercial: (opcional)
├─ regimen_tributario: SIMPLE | ORDINARIO | NO_RESP
├─ actividad_economica_ciiu: Código CIIU
├─ responsable_iva: Boolean
├─ gran_contribuyente: Boolean
├─ autoretenedor: Boolean
├─ es_retenedor: Boolean
├─ aplica_retefuente: Boolean
├─ aplica_reteica: Boolean
├─ aplica_reteiva: Boolean

Campos Comerciales:
├─ plazo_pago_dias: Crédito default (30)
├─ banco: Nombre del banco
├─ tipo_cuenta: AHORROS | CORRIENTE
├─ numero_cuenta: Número de cuenta bancaria
├─ email_contacto: Email principal
└─ telefono_contacto: Teléfono principal

Mapeo Contable:
├─ codigo_contable: Subcuenta nivel-6 (Clase 2, Pasivos NIIF)
└─ Link a CuentaContable via NIIF

Auditoría (Heredada):
├─ empresa: FK (SSoT, PROTECT)
├─ created_at: Timestamp creación
├─ updated_at: Timestamp última actualización
└─ activo: Boolean (requerido para eliminar)
```

### DocumentoSoporte (FK a Proveedor)

```
Relación:
├─ proveedor: FK a Proveedor (on_delete=CASCADE) ⭐ v3.6.1
│  └─ Cuando se elimina Proveedor, se eliminan automáticamente sus DocumentoSoporte
└─ empresa: FK a Empresa (on_delete=PROTECT)

Impacto del Cambio CASCADE:
├─ Antes: PROTECT bloqueaba eliminación de Proveedor
├─ Ahora: Hard delete automático de Proveedor + DocumentoSoporte en cascada
└─ Efecto: Usuario ve eliminación exitosa, datos se limpian completamente
```

---

## 🔒 Protección IDOR (Double Semantic Verification)

**7 Capas de Validación:**

1. **Frontend:** Formulario HTMX sin editores inline
2. **Network:** POST/PATCH/DELETE con campos permitidos
3. **ViewSet:** IsTenantMember + resolve_tenant_empresa()
4. **BusinessService:** DSV (empresa_id match)
5. **Serializer:** Validaciones de tipos
6. **ORM:** SintelTenantBaseModel + constraints
7. **Database:** UNIQUE + FK PROTECT/CASCADE

---

## 🧪 Validación de Flujos Críticos

### ✅ Crear Proveedor
```
POST /api/v1/proveedores/
├─ 1. ViewSet.create() → ProveedorServiceMixin
├─ 2. business_service.crear_proveedor() → DSV
├─ 3. business_service._sanitize_retenciones()
├─ 4. crud_service.create() → @transaction.atomic
├─ 5. Response 201 + JSON
└─ 6. Frontend: Tabulator.replaceData() ✅
```

### ✅ Actualizar Proveedor
```
PATCH /api/v1/proveedores/{uuid}/
├─ 1. ViewSet.update() → get_object() (UUID lookup)
├─ 2. business_service.actualizar_proveedor() → DSV
├─ 3. crud_service.update() → @transaction.atomic
├─ 4. Response 200 + JSON
└─ 5. Frontend: Tabulator.replaceData() ✅
```

### ✅ Eliminar Proveedor (v3.6.1)
```
DELETE /api/v1/proveedores/{uuid}/
├─ 1. ViewSet.destroy() → get_object() (UUID lookup)
├─ 2. business_service.eliminar_proveedor()
│   ├─ Validar: activo == False (error si True)
│   └─ Hard delete: cascade automático a DocumentoSoporte
├─ 3. Django CASCADE: Elimina DocumentoSoporte asociados
├─ 4. Response 204 No Content
└─ 5. Frontend: Tabulator.replaceData() ✅
       "Proveedor eliminado completamente de la BD"
```

---

## 📊 Flujo de Eliminación Segura (v3.6.1)

```
Usuario marca "Acme Corp" inactivo (PATCH activo=False)
        ↓
Usuario confirma eliminar (click botón DELETE)
        ↓
ViewSet.destroy() → ProveedorViewSet
        ↓
business_service.eliminar_proveedor()
├─ Validar: ¿activo == True?
│   ├─ SÍ → Error: "Márquelo como inactivo primero"
│   └─ NO → Continuar
├─ crud_service.delete(proveedor)
│   └─ Django: DELETE FROM tenant_proveedores_proveedor WHERE uuid=xxx
├─ CASCADE Automático
│   └─ Django: DELETE FROM tenant_gastos_documentosoporte WHERE proveedor_id=xxx (12 registros)
└─ Response: 204 No Content
        ↓
Frontend: "Proveedor eliminado"
        ↓
Tabulator: ✅ Transformación exitosa
        ↓
"Acme Corp" desaparece completamente del listado
```

---

## 📁 Estructura Física

```
apps/tenant/proveedores/
├── models.py
│   ├─ Proveedor (uuid, campos tributarios, cascada listos)
│   └─ Retenciones (es_retenedor, aplica_*, porcentajes)
├── api/
│   ├─ viewsets.py (destroy con cascade automático)
│   ├─ serializers.py
│   ├─ permissions.py
│   └─ urls.py
├── services/
│   ├─ __init__.py (reexportaciones)
│   ├─ selectors.py (LIST_FIELDS, DETAIL_FIELDS)
│   ├─ crud_service.py (@transaction.atomic)
│   ├─ business_service.py (DSV, eliminar_proveedor con cascade)
│   └─ api_mixins.py
├── templates/tenant/proveedores/
│   ├─ offcanvas_form.html (v3.6 premium, flexbox footer)
│   ├─ proveedores_list.html
│   └─ assets_proveedores.html
├── static/proveedores/js/
│   ├─ proveedores.api.js
│   ├─ proveedores_main.js (Tabulator)
│   └─ proveedores_form.js (HTMX, retenciones)
├── migrations/
│   ├─ 0001_initial.py
│   ├─ 0002_add_uuid_to_proveedor.py (v3.5)
│   └─ 0003_add_retenciones_fields.py (v3.5)
│   └─ 0012_alter_documentosoporte_proveedor.py (v3.6.1 CASCADE)
└── .agent/ (SSoT Documentation)
    ├─ README.md (portal entrada)
    ├─ ESTADO_ACTUAL_v360.md (layout premium)
    ├─ DELETE_SEGURO_v360.md (hard delete cascada)
    ├─ GARANTIA_SEGURIDAD_DSV.md
    ├─ AUDITORIA_FLUJO_PROVEEDORES.md (este archivo)
    └─ docs/ (flow maps, business logic, microtasks)
```

---

## 🚨 Migraciones Requeridas (v3.6.1)

```bash
# Aplicar migración de cascada
python manage.py migrate_schemas --tenant

# Resultado:
# ✅ tenant_gastos: 0012_alter_documentosoporte_proveedor.py aplicada
# ✅ on_delete=PROTECT → on_delete=CASCADE
# ✅ Hard delete ahora funciona con cascada automática
```

---

## 🔗 Referencias Cruzadas

| Tema | Documento | Status |
|------|-----------|--------|
| Estado actual v3.6 | [ESTADO_ACTUAL_v360.md](ESTADO_ACTUAL_v360.md) | ✅ |
| Delete seguro v3.6.1 | [DELETE_SEGURO_v360.md](DELETE_SEGURO_v360.md) | ✅ |
| Seguridad DSV | [GARANTIA_SEGURIDAD_DSV.md](GARANTIA_SEGURIDAD_DSV.md) | ✅ |
| Flujo Mermaid | [docs/proveedores_flow_map.md](docs/proveedores_flow_map.md) | ✅ |
| Lógica negocio | [docs/proveedores_business_logic.md](docs/proveedores_business_logic.md) | ✅ |

---

**Última Actualización:** 2026-05-11  
**Auditor:** Claude Code  
**Status:** ✅ **V3.6.1 PRODUCTION READY**

Cambios de esta versión:
- ✅ UI Premium v3.6 (flexbox footer, headers badges, layout optimizado)
- ✅ Hard Delete + CASCADE v3.6.1 (eliminación física con cascada automática)
- ✅ CSS/JS Isolation (AGENTS.md §22/§23)
- ✅ Documentación actualizada y alineada
