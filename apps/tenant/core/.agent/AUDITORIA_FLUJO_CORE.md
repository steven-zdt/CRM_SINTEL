# CORE — Portal de Auditoría y Flujos (SSoT)

**Version:** 3.5.0
**App:** `apps/tenant/core/`
**Responsabilidad:** Orquestación, Identidad, Seguridad Transversal y Composición de Workspace.

---


## 📑 Documentación Especializada (SSoT)

> [!NOTE]
> La documentación se ha fragmentado para garantizar la mantenibilidad y claridad siguiendo el estándar SINTEL v3.5.0.

| Documento | Descripción |
| :--- | :--- |
| [📂 Arquitectura y Microtareas](docs/core_microtasks_architecture.md) | Desglose atómico de responsabilidades y tareas técnicas. |
| [🗺️ Mapas de Flujo](docs/core_flow_map.md) | Diagramas Mermaid de ciclo de vida y procesos. |
| [🧠 Lógica de Negocio](docs/core_business_logic.md) | SSoT de reglas, validaciones y cálculos. |
| [🛠️ Habilidades y Scripts](skills/) | Repositorio de scripts especializados y automatizaciones del módulo. |

---

## 📂 Documentación Especializada
- [🏗️ Arquitectura de Microtareas](docs/core_microtasks_architecture.md)
- [🗺️ Mapa de Flujos y Secuencias](docs/core_flow_map.md)
- [⚖️ Lógica de Negocio y Reglas SSoT](docs/core_business_logic.md)

---

## 1. Propósito Arquitectónico

`core` es el **SNC (Sistema Nervioso Central)** del tenant. Actúa como el compositor de la interfaz de usuario (Workspace) y el guardián de la integridad de datos mediante el modelo base y los middlewares de seguridad.

### Pilares Fundamentales:
1. **Identidad y Acceso**: Gestión centralizada de Login (Dual-Auth), Registro y Activación.
2. **Aislamiento Multi-Tenant**: Implementación de `SintelTenantBaseModel` y guardias de membresía.
3. **Composición de UI**: Proyección de datos de múltiples dominios en un Workspace unificado.
4. **Ingesta de Documentos**: Pipeline universal (`document_router`) para materialización de DTOs.

## 2. Mapa de Componentes Críticos

### 2.1 Backend (Service Layer & API)
- **Models**: `SintelTenantBaseModel` (SSoT de Persistencia).
- **Middleware**: `SintelExceptionMiddleware` (Normalización de Errores) y `MembershipGuard`.
- **Services**: `auth_service.py`, `membership.py`, `orchestration.py`.
- **API**: ViewSets de composición (`CoreLinksViewSet`, `DashboardSectionsViewSet`).

### 2.2 Frontend (Workspace Shell)
- **Template**: `templates/tenant/core/workspace.html` (Contenedor principal).
- **JS Core**: `static/core/js/main.js` (Orquestador de UI) y `lib/http.js` (Cliente API con CSRF).

## 3. Estado de la Auditoría

| Dimensión | Estado | Notas |
|---|---|---|
| **Aislamiento** | ✅ Protegido | Validado vía `SintelTenantBaseModel` y `MembershipGuard`. |
| **Ruteo** | ✅ Estandarizado | `urls_tenant.py` y `api_urls.py` sincronizados. |
| **Auth** | ✅ Dual-Auth | JWT + Session funcionando correctamente. |
| **Documentación** | ✅ v3.5.0 | Todos los flujos y microtareas documentados en `docs/`. |

## 4. Próximos Pasos de Evolución
- Refinar los adaptadores de inventario y facturas para mayor resiliencia.
- Implementar observabilidad detallada en el `document_router` para trazabilidad de ingesta.

---
**Última actualización:** 2026-05-09
**Responsable:** Antigravity Agent

