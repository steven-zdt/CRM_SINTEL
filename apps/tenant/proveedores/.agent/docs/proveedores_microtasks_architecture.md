# [ARCH] SINTEL v3.5.0 — Proveedores Module Microtasks Architecture

Este documento descompone el módulo de **Proveedores** en unidades atómicas de trabajo, alineadas con el patrón de Service Layer y la arquitectura Multi-Tenant de SINTEL.

## 1. Capa de Datos (Modelos y Persistencia)

### 1.1. Verificación de SintelTenantBaseModel [COMPLETED]
- [x] Asegurar que `Proveedor` herede de `SintelTenantBaseModel`.
- [x] Validar la existencia de `uuid` como Lookup Field.
- [x] Implementar constraint de unicidad: `empresa + tipo_documento + numero_documento`.

### 1.2. Integración con Catálogo NIIF [COMPLETED]
- [x] Validar `codigo_contable` contra `niif_proveedores_choices.py`.

## 2. Capa de Servicios (Business Logic & Selectors)

### 2.1. Selectors de Alto Rendimiento [COMPLETED]
- [x] Implementar `qs_list` con `.only(*LIST_FIELDS)`.
- [x] Implementar `qs_detail` con `.only(*DETAIL_FIELDS)`.
- [x] Búsqueda optimizada por `razon_social`, `documento` y `email`.

### 2.2. Lógica Financiera (SSoT) [COMPLETED]
- [x] Centralizar cálculo de `neto_gasto` en `ProveedorBusinessService`.
- [x] Implementar `obtener_configuracion_retenciones` basado en atributos del proveedor (Autorretenedor, Persona Natural/Jurídica).

### 2.3. Transaccionalidad Maestro-Detalle [COMPLETED]
- [x] Implementar `registrar_proveedor_con_contactos` con `@transaction.atomic`.

## 3. Capa de API (DRF & Gateway Directo)

### 3.1. Estandarización de ViewSet [COMPLETED]
- [x] Heredar de `BaseTenantViewSet` para inyección de `JWTAuthentication`.
- [x] Usar `ProveedorServiceMixin` para delegar lógica al Service Layer.
- [x] Endpoints HTMX para `render-offcanvas` (crear/editar/detalle).

### 3.2. Serialización Selectiva [COMPLETED]
- [x] Separar `ProveedorListSerializer` de `ProveedorDetailSerializer`.

## 4. Frontend & UI (Vanilla JS & HTMX)

### 4.1. Namespace Sintel.Proveedores [COMPLETED]
- [x] Implementar `proveedores.main.js`, `proveedores.api.js` y `proveedores.form.js`.
- [x] Integración con `TabulatorFactory`.

### 4.2. Resiliencia y Auto-Healing [COMPLETED]
- [x] Implementar inyección dinámica del contenedor de Offcanvas si no existe en el DOM.
- [x] Uso de `UIManager` para feedback de éxito y limpieza de backdrops.
