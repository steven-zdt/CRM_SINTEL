# CORE — Lógica de Negocio y Reglas SSoT

**Version:** 3.5.0
**App:** `apps/tenant/core/`

---

## 📂 Navegación de Documentación
- [🏗️ Arquitectura de Microtareas](core_microtasks_architecture.md)
- [🗺️ Mapa de Flujos y Secuencias](core_flow_map.md)
- [🏠 Portal de Auditoría](../AUDITORIA_FLUJO_CORE.md)

---

## 1. Reglas del Modelo Base (SSoT de Persistencia)

`SintelTenantBaseModel` es el cimiento de integridad de datos.

- **Herencia Obligatoria**: Todo modelo dentro del esquema tenant DEBE heredar de esta clase.
- **Guardia de Empresa**: El método `save()` lanza un `ValueError` si `empresa_id` es nulo. No se permiten registros huérfanos.
- **Aislamiento por Registro**: Aunque el esquema PostgreSQL provee aislamiento físico, el campo `empresa` provee aislamiento lógico y auditoría (created_at/updated_at).

## 2. El Puente de Membresía (Membership Bridge)

Core es el único módulo autorizado para realizar saltos de esquema (`cross-schema queries`) de forma controlada.

- **Context Manager Safe**: Todas las consultas al esquema `public` desde el contexto `tenant` deben usar el wrapper de `membership.py`.
- **Double-Check de Acceso**: Antes de procesar cualquier mutación, Core valida que el `request.user` tenga una membresía activa en el tenant actual, independientemente de su estado de sesión global.

## 3. Orquestación del Workspace (The Composer)

Core no "posee" los datos de negocio, los **proyecta**.

- **Adapters Stateless**: Los adapters en `services/` traducen los modelos de dominio (Facturas, Contabilidad) a un formato optimizado para el Workspace central.
- **Link Discovery**: Core es la autoridad sobre las URLs del sistema. El frontend consume `/api/v1/core/links/` para conocer los endpoints válidos, evitando hardcoding de rutas.
- **Branding SSoT**: Los colores, logos y favicons se resuelven dinámicamente. Si un tenant no tiene configuración propia, Core aplica los valores por defecto del sistema (SSoT Visual).

## 4. Política de Error Handling

- **Zero Leakage**: `SintelExceptionMiddleware` captura errores 500 y los transforma en respuestas JSON controladas. Nunca se expone el Traceback de Django al cliente en producción.
- **API First**: Todos los endpoints bajo `/api/v1/` retornan JSON, incluso en errores de sistema, permitiendo que la UI (`UIManager`) maneje el feedback de forma elegante.

## 5. Idempotencia en la Ingesta

- **Pipeline Registry**: El `document_router` garantiza que un documento (ej. un XML de factura) no se procese dos veces si el materializador de dominio implementa correctamente la validación de idempotencia (ej. vía UUID o prefijo+número).

---
**Última actualización:** 2026-05-09
