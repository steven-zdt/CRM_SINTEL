# [PORTAL] Auditoría: Módulo Clientes (Gestión de Clientes/Ventas)

**Versión:** 3.5.0 (Backend/API) + v3.5.0 (Frontend/UX)  
**Estado:** ✅ PRODUCTION READY (Blocker issues CORREGIDOS)  
**Ubicación:** `apps/tenant/clientes/`  
**Última Auditoría:** 2026-05-11
**Última Actualización (Código):** 2026-05-11 (Retention Architecture + UI v3.5.0)

---

## 📑 Documentación Especializada (SSoT)

| Documento | Descripción | Estado |
| :--- | :--- | :--- |
| [✅ Estado Actual v3.5.0](ESTADO_ACTUAL_v350.md) | Estado: UUID lookup, DSV, blocker fixes. | ✅ |
| [🔒 Garantía de Seguridad DSV](GARANTIA_SEGURIDAD_DSV.md) | IDOR Prevention. | ✅ |
| [📂 Arquitectura](docs/clientes_microtasks_architecture.md) | Microtareas. | ✅ |
| [🗺️ Mapas de Flujo](docs/clientes_flow_map.md) | Diagramas Mermaid. | ✅ |
| [🧠 Lógica de Negocio](docs/clientes_business_logic.md) | Reglas. | ✅ |

---

## 🎯 Responsabilidades Core

Gestión de clientes y contactos para ventas.

1. Gestión de identidad legal con SSoT por empresa
2. Normativa tributaria colombiana
3. Validación por tenant (aislamiento empresa_id)
4. Contactos relacionados (modelo ContactoCliente)
5. UUID lookup field (AGENTS.md §14) ⭐
6. Double Semantic Verification (AGENTS.md §13) ⭐

---

## 📌 Cambios v3.5.0

### ✅ UUID Lookup Field
- Cliente.uuid + ContactoCliente.uuid = UUIDField(unique=True)
- Migración: 0002_add_uuid_fields.py (población segura)
- ViewSets: lookup_field removido, hereda uuid

### ✅ DSV Implementation
- resolve_tenant_empresa() + IsTenantMember
- BusinessService: empresa_id validation
- Selector: empresa_id filtering

### ✅ Service Layer
- Selectors, CRUD, Business services
- ServiceMixins inyectados en ViewSets
- Reexportaciones en __init__.py

### ✅ Estandarización UI v3.5.0 (Horizontal Expansion & UI Fixes)
- **Horizontal Expansion**: Offcanvas forms expanded to `800px` via `.offcanvas-xl`.
- **Layout Multi-columna**: Reorganización de campos de identificación, contacto y personas de contacto a 3 columnas (`col-md-4`).
- **UI Fixes (Hotfix v3.5.1)**:
    - Eliminación de transparencia en contenedores mediante `bg-white` y `bg-light`.
    - Estandarización de cabeceras (`offcanvas-header bg-light border-bottom`).
    - Optimización de densidad en sección de Retenciones (layout 3 columnas `col-md-4`).
- **Data Density**: Optimización de espacio para mejorar la legibilidad en resoluciones de escritorio.

### ✅ Arquitectura de Retenciones v3.5.0
- **Propósito**: Capturar información de agentes retenedores según estatuto colombiano.
- **Campos**: `es_retenedor`, `aplica_retefuente`, `aplica_reteica`, `aplica_reteiva` y sus porcentajes respectivos.
- **Lógica**: Toggle dinámico en JS para mostrar/ocultar configuración de retenciones.
- **Estado**: ✅ IMPLEMENTADO

---

## ✅ Compliance AGENTS.md v3.5.0

- [x] §1 Service Layer
- [x] §4.5 Zero Waste (.only())
- [x] §5 CRUD E2E
- [x] §6 FSD
- [x] §13 IDOR Prevention
- [x] §14 UUID Lookup
- [x] §17 Bridge Isolation

**7/7 ✅ COMPLIANCE**

---

**Última Actualización:** 2026-05-11  
**Auditor:** Claude Code  
**Status:** ✅ **V3.5.0 PRODUCTION READY**
