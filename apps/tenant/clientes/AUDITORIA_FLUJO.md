# 🔍 Auditoría de Flujo - Módulo Clientes (Backend & Frontend) v2.61.5

**Última Actualización:** 2026-03-16
**Estado:** ✅ **IMPLEMENTACIÓN MAESTRO-DETALLE (CLIENTES ↔ CONTACTOS) FINALIZADA Y VALIDADA**

---

## 1. Visión General
El módulo de Clientes en SINTEL (v2.61.5) gestiona la información legal y comercial de los clientes bajo una arquitectura multi-tenant, implementando ahora una estructura **Maestro-Detalle** que permite la gestión de múltiples contactos por cliente con persistencia atómica.

## 2. Cambios Críticos (v2.61.5)

### 2.1. Backend (DRF)
- **Integración Maestro-Detalle:** `ContactoClienteViewSet` actualizado para heredar de `BaseTenantViewSet`.
- **Zero Trust:** 
  - `ContactoClienteSerializer` integra `NormalizationMixin`.
  - Validación estricta de pertenencia al `empresa_id` del tenant en todas las operaciones (`perform_create`, `perform_update`).
- **Seguridad y Normalización:**
  - `ClienteDetailSerializer` y `ContactoClienteSerializer` usan `NormalizationMixin` para limpiar entradas (strip).
  - Implementación de `get_empresa()` segura en `ClienteViewSet`.
- **Integración con Front:** Soporte para creación/edición de contactos anidados en el payload de `ClienteViewSet` (`create`, `update`, `partial_update`).

### 2.2. Frontend & Presentación de Errores
- **Error Boundary Pattern:** Migración de `SintelFeedback` a `window.UIManager` en todos los flujos de contactos (Offcanvas).
- **Inyección de Errores:** Errores de validación (ej: `unknown_document_type`, duplicados) ahora son inyectados dinámicamente en `#contacto-form-feedback` dentro del offcanvas, evitando alertas flotantes intrusivas.
- **UI:** Integración completa en `list.html` con estados de carga (`loadingContactos`) y deshabilitado de botones durante operaciones.

---

## 3. Flujo de Operaciones Maestro-Detalle

### 3.1. CRUD de Contactos
1. **Frontend:** El offcanvas (HTMX) captura los datos del formulario de contactos.
2. **API:** `POST/PATCH /api/v1/clientes/contactos/` recibe el payload.
3. **Serialización:** `ContactoClienteSerializer` valida normalizando datos.
4. **Persistencia:** Si el cliente tiene contactos, se ejecuta el reemplazo total (o creación) garantizando integridad transaccional mediante `transaction.atomic` en `actualizar_cliente()`.

### 3.2. Manejo de Errores (UI)
- Cualquier error de validación (servidor o base de datos) es capturado y estructurado en un objeto JSON (`ui_feedback`).
- `UIManager` parsea este objeto y lo renderiza en el contenedor local (`.alert-danger`) del offcanvas, cumpliendo con la arquitectura de Error Boundary.

---

## 4. Checklist de Verificación (v2.61.5)

- [x] **Zero Trust:** `ContactoClienteViewSet` filtra correctamente por `empresa_id`.
- [x] **Normalization:** `NormalizationMixin` activo en todos los serializers críticos.
- [x] **UI/UX:** Errores de ingestión y validación inyectados localmente en offcanvas.
- [x] **Atómico:** Creación/Edición Maestro-Detalle garantizada por `transaction.atomic`.
- [x] **Estándar:** Uso de `TabulatorFactory` y `UIManager`.

---

## 5. Referencias
- `apps/tenant/clientes/api/viewsets.py`
- `apps/tenant/clientes/api/serializers.py`
- `apps/tenant/clientes/services.py`
- `apps/services/document_ingest/ingest_service.py`
- `apps/tenant/core/static/core/js/lib/ui-manager.js`
