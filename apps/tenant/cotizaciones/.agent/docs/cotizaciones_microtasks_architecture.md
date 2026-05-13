# 📂 Arquitectura de Microtareas: Módulo Cotizaciones

**Versión:** 3.5.0
**Estado:** ✅ PRODUCTION READY
**SSoT Portal:** [AUDITORIA_FLUJO_COMPLETO.md](file:///c:/Users/Administrator/Documents/crm_sintel/apps/tenant/cotizaciones/AUDITORIA_FLUJO_COMPLETO.md)

---

## 🏗️ Mapa de Responsabilidades

El módulo de cotizaciones se descompone en los siguientes dominios de responsabilidad:

| Grupo | Código | Responsabilidad |
| :--- | :--- | :--- |
| **Infraestructura** | `MT-COT-INF` | Modelos, Migraciones y Base de Datos (SintelTenantBaseModel). |
| **Seguridad** | `MT-COT-SEC` | Doble Verificación Semántica (DSV) y prevención IDOR. |
| **API & Gateway** | `MT-COT-API` | Endpoints DRF, Serializers y Gateway Directo. |
| **Frontend UI** | `MT-COT-UI` | Módulos JS (FSD), Tabulator y Offcanvas HTMX. |
| **Orquestación** | `MT-COT-ORQ` | Cálculos SSoT, Pipeline de PDF y Sincronización. |

---

## 🛠️ Microtareas Atómicas

### [MT-COT-INF] Infraestructura y Modelos
- [x] **MT-COT-INF-001**: Implementación de `SintelTenantBaseModel` en todos los modelos (Cotizacion, Item, Producto, Servicio).
- [x] **MT-COT-INF-002**: Definición de `UniqueConstraint` para `numero_cotizacion` por empresa y perfil.
- [x] **MT-COT-INF-003**: Configuración de `SET_NULL` en FKs críticas (Cliente, Configuracion) para garantizar resiliencia ante fallos en otros módulos.
- [ ] **MT-COT-INF-004**: Migración de `lookup_field` a UUID para modelos auxiliares (`Producto`, `Servicio`).

### [MT-COT-SEC] Seguridad y Protección de Datos
- [x] **MT-COT-SEC-001**: Implementación de `SintelDSVMixin` en todos los ViewSets.
- [x] **MT-COT-SEC-002**: Validación de pertenencia de `empresa_id` en `CotizacionService.crear_preforma`.
- [x] **MT-COT-SEC-003**: Protección contra IDOR en endpoints de edición y eliminación mediante filtrado por tenant.
- [ ] **MT-COT-SEC-004**: Refactorización de `CotizacionSerializer.__init__` para asegurar filtrado de FKs incluso sin objeto `request`.

### [MT-COT-API] API Layer y Gateway Directo
- [x] **MT-COT-API-001**: Exposición de endpoints RESTful bajo `/api/v1/cotizaciones/`.
- [x] **MT-COT-API-002**: Implementación de `StandardResultsSetPagination` para listados masivos.
- [x] **MT-COT-API-003**: Creación de endpoints `render-offcanvas/*` para inyección de UI Shells vía HTMX.
- [x] **MT-COT-API-004**: Endpoint de estadísticas rápidas (`/estadisticas/`) para el Dashboard.

### [MT-COT-UI] Frontend y Experiencia de Usuario
- [x] **MT-COT-UI-001**: Modularización de JS en namespace `window.Sintel.Cotizaciones` (FSD).
- [x] **MT-COT-UI-002**: Implementación de `TabulatorFactory` con Dual-Auth (JWT + CSRF).
- [x] **MT-COT-UI-003**: Aplicación del patrón "DOM Shield" en formularios para prevenir inyección de datos huérfanos.
- [x] **MT-COT-UI-004**: Orquestador `main.js` con soporte para el patrón `tab-activated`.

### [MT-COT-ORQ] Orquestación y Lógica de Negocio
- [x] **MT-COT-ORQ-001**: Motor de cálculos financieros SSoT (AIU, IVA, Totales).
- [x] **MT-COT-ORQ-002**: Generación thread-safe de códigos únicos mediante `select_for_update`.
- [x] **MT-COT-ORQ-003**: Pipeline de exportación a PDF profesional sincronizado con la persistencia.
- [ ] **MT-COT-ORQ-004**: Optimización de `_sync_items` para reducir el N+1 de recálculos de totales.

---

## 📈 Roadmap de Mejoras Técnicas

1.  **Asincronía (MT-COT-ORQ-005)**: Migrar la generación de PDF a un proceso en segundo plano (Celery) o `transaction.on_commit`.
2.  **Unificación de Cálculos (MT-COT-ORQ-006)**: Eliminar la duplicación de fórmulas entre el `PDFExportService` y `CotizacionService`.
3.  **Auditoría de Acciones**: Implementar logging detallado de cambios de estado (BORRADOR -> ENVIADA -> ACEPTADA).

---

## 🔗 Navegación
- [⬅️ Volver al Portal](file:///c:/Users/Administrator/Documents/crm_sintel/apps/tenant/cotizaciones/AUDITORIA_FLUJO_COMPLETO.md)
- [🗺️ Mapas de Flujo](file:///c:/Users/Administrator/Documents/crm_sintel/apps/tenant/cotizaciones/docs/cotizaciones_flow_map.md)
- [🧠 Lógica de Negocio](file:///c:/Users/Administrator/Documents/crm_sintel/apps/tenant/cotizaciones/docs/cotizaciones_business_logic.md)
