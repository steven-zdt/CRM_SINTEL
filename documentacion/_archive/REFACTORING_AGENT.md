---
name: refactoring_agent
scope: SINTEL v2.61.x+
version: 3.5 (Unified)
---

# REFACTORING_AGENT.md (v3.5) — Directiva Maestra de ADN y UI Universal

Este documento es el **SSoT (Única Fuente de Verdad)** para la refactorización de aplicaciones dentro del ecosistema SINTEL. Define el estándar de oro para transformar módulos legacy en componentes modernos, seguros y desacoplados.

## 🛡️ Fase 0: Ingeniería Inversa y Mapeo de ADN (Obligatorio)
Antes de modificar cualquier archivo, el agente debe ejecutar un escaneo de 360° de la App legacy:
1.  **Model Discovery**: Identificar `ForeignKeys`, `OneToOneFields` y `Constraints` (ej. `unique_together`).
2.  **Lógica de Negocio Fantasma**: Extraer validaciones ocultas en `save()`, `clean()` o directamente en los `ViewSets` para migrarlas al `Business Service`.
3.  **Dependencias Cross-App**: Listar qué otras apps consumen datos de esta App para no romper el flujo del Tenant.
4.  **Auditoría de Querysets**: Identificar consultas `.all()` o `.filter()` que no usen `.only()` para optimizar con `LIST_FIELDS`.

## 🏗️ Fase 1: Estabilización del Modelo [CORE-DB]
1.  **Herencia SSoT**: Cambiar `models.Model` por `SintelTenantBaseModel` (importado de `apps.tenant.core.models`).
2.  **Aislamiento de Empresa**: Inyectar automáticamente la relación de empresa vía herencia.
3.  **No Emojis**: Verificación estricta de la **Regla 0** (Cero caracteres especiales en Python).

## ⚙️ Fase 2: Modularización Extrema de Servicios (Backend)
Se prohíbe el uso de un solo `services.py`. Estructura requerida en `apps/tenant/<app>/services/`:
- `selectors.py`: Consultas `GET` optimizadas. Define `LIST_FIELDS` y `DETAIL_FIELDS`.
- `crud_service.py`: Persistencia pura (Create/Update/Delete) envuelta en `@transaction.atomic`.
- `business_service.py`: Orquestación, validaciones semánticas y lógica de dominio.
- `services.py`: (Opcional) Capa de compatibilidad legacy (delegación).

## 🔑 Fase 3: Seguridad Dual-Auth y JWT Bridge
1.  **Double Semantic Verification (DSV)**: El ViewSet DEBE validar en `get_object()` que el ID pertenezca al tenant del usuario (`request.user.perfil.empresa`).
2.  **Auth Bridge**:
    - **Primario**: SessionAuth (Cookies + CSRF) para navegación y HTMX.
    - **Secundario**: JWT para componentes de datos (Tabulator).
    - **Inyección**: `TabulatorFactory` inyecta automáticamente `Authorization: Bearer` usando `window.jwtAuth.getValidAccessToken()`.
3.  **Endpoint SSoT**: `GET /api/v1/core/auth/from-session/` para obtener tokens JWT sin re-logueo.

## 🌐 Fase 4: Sincronización UI Universal (FSD)
Aislamiento total de assets (Feature-Sliced Design):
1.  **Ubicación de Assets**:
    - Templates: `apps/tenant/<app>/templates/<app>/`
    - Static JS: `apps/tenant/<app>/static/<app>/js/`
2.  **Integración Workspace**:
    - Actualizar `apps/tenant/core/templates/tenant/core/workspace.html` para incluir los partials y assets desde sus nuevas ubicaciones.
    - Evitar duplicidad de inclusiones.
3.  **HTMX Reactivity**: Uso de `HX-Trigger` para recargar tablas Tabulator tras mutaciones exitosas.

## 🧪 Fase 5: DOM Shield y JS Encapsulado
1.  **DOM Shield**: 
    - Remover atributos `name` de inputs visibles para prevenir envíos accidentales del navegador.
    - Captura manual de datos vía JS enviando JSON puro a la API.
2.  **Zero Trust UI**: Validar tipos y rangos en el frontend antes del despacho.

---

## 🔍 Checklist de Conformidad v3.5
- [ ] ¿Fase 0 (Mapeo ADN) documentada en `AUDITORIA_<APP>.md`?
- [ ] ¿Backend dividido en `selectors`, `crud` y `business`?
- [ ] ¿DSV implementado en todos los ViewSets?
- [ ] ¿Universal UI actualizado en `workspace.html`?
- [ ] ¿Assets migrados a la carpeta local de la App (FSD)?

---
*Referencia Maestra: AGENTS.md | SINTEL Agent Unified | SSoT Architecture*
