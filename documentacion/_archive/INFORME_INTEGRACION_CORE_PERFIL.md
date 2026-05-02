# Informe Técnico: Relación y Procesamiento Core vs Perfil (v2.61.4)

Este documento describe la arquitectura de integración entre el núcleo del sistema (`apps/tenant/core`) y el módulo de perfil (`apps/tenant/perfil`), detallando cómo se orquestan los datos y las vistas.

---

## 1. Integración en el Backend (Capa de Datos)

La relación en el backend se rige por el principio de **Composición y Orquestación**, donde Core actúa como el agregador de información para el usuario.

### 1.1 Registro de Rutas API
En `config/api_urls.py`, el dominio de perfil se registra de forma independiente pero contenida:
```python
urlpatterns.append(path('perfil/', include('apps.tenant.perfil.api.urls')))
```
Esto permite que el frontend consuma `/api/v1/perfil/perfiles/me/` directamente.

### 1.2 Snapshot Dashboard (Core API)
El `DashboardSectionsViewSet` en `core` incluye el perfil en su payload principal:
1. Core llama a `get_perfil_snapshot(user)` en `apps/tenant/core/services/perfil.py`.
2. Este servicio consulta el modelo `TenantProfile` (Only READ) para extraer: `id`, `cargo`, `departamento`, `telefono_corporativo` y `foto`.
3. El resultado se inyecta en la sección `"perfil"` del JSON de retorno de `/api/v1/core/dashboard/sections/`.

---

## 2. Integración en el Frontend (Capa de Presentación)

SINTEL utiliza un patrón de **Workspace Centralizado (Shell)**.

### 2.1 Inyección de Estructura (Templates)
El archivo `workspace.html` (Core) reserva un espacio físico para el perfil:
```html
<section id="tab-perfil" class="workspace-tab" style="display: none;">
    {% include 'tenant/perfil/partials/list.html' %}
    {% include 'tenant/perfil/partials/modals.html' %}
</section>
```

### 2.2 Carga de Lógica (Assets)
Core delega la lógica de negocio al módulo de perfil mediante la inclusión de sus assets en el pie del workspace:
*   `perfil.api.js`: Define `window.perfilAPI` (consumo de endpoints específicos).
*   `perfil.ui.js`: Define `window.perfilUI` (manipulación del DOM para perfil).
*   `perfil.page.js`: Orquesta el ciclo de vida del módulo cuando el hash cambia a `#perfil`.

---

## 3. Flujo de Procesamiento de Vistas

Cuando un usuario navega a la sección de Perfil:
1. **Hash Change**: El navegador detecta el cambio a `#perfil`.
2. **Tab Switch**: El orquestador de `workspace.js` oculta las otras secciones y muestra `#tab-perfil`.
3. **Data Fetch**:
   - `core` ya tiene un snapshot básico (del login/dashboard).
   - `perfil.page.js` realiza una llamada secundaria a `/api/v1/perfil/perfiles/me/` para obtener los datos extendidos y configuraciones JSON.
4. **Rendering**:
   - El DOM se actualiza usando los contenedores definidos en `tenant/perfil/partials/list.html`.
   - Si se requiere edición, se activa `tenant/perfil/partials/modals.html`, el cual envía un `PATCH` a la API de perfil.

---

## 4. Conclusión

La relación es de **Acoplamiento Débil en Ejecución y Fuerte en Composición**. Core provee el cascarón (Workspace) y la identidad basal, mientras que Perfil provee su propia API CRUD y su lógica UI específica, cumpliendo con la arquitectura **Feature-Sliced Design (FSD)** de SINTEL v2.61.4.

**Estado de Integración**: ✅ **Sincronizado**
