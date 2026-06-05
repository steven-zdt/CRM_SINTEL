# [PORTAL] Auditoria y SSoT: Modulo Perfil (Gestion de Usuarios y Roles)

**Version:** 3.10.2
**Estado:** PRODUCTION READY
**Ubicacion:** `apps/tenant/perfil/`
**Ultima Auditoria:** 2026-05-25

---

## Documentacion Especializada (SSoT)

| Documento | Descripcion |
| :--- | :--- |
| [Arquitectura y Microtareas](docs/perfil_microtasks_architecture.md) | Desglose atomico de responsabilidades y tareas tecnicas (MT-PRF). |
| [Mapas de Flujo](docs/perfil_flow_map.md) | Ciclo de vida de la invitacion, auto-elevacion de privilegios y gestion de roles. |
| [Logica de Negocio](docs/perfil_business_logic.md) | SSoT de jerarquia de roles, proteccion de ultimo administrador e integracion cross-schema. |

---

## Responsabilidades Core

El modulo de **Perfil** centraliza el acceso y la identidad dentro del tenant.

1.  **Membresia Tenant**: Vinculacion de usuarios globales (`public.User`) con la empresa activa mediante el modelo `TenantProfile`.
2.  **RBAC (Role-Based Access Control)**: Definicion y aplicacion de roles (`ADMIN`, `OPERADOR`, `VISOR`) que rigen los permisos en todos los ViewSets del tenant.
3.  **Sistema de Invitaciones**: Flujo de creacion de usuarios "on-the-fly" para emails no registrados en la plataforma global.
4.  **Auto-Elevacion (SSoT Identity)**: Garantia de privilegios administrativos para el propietario legal de la empresa (`owner_email`).
5.  **Seguridad Zero-Trust**: Validacion continua de pertenencia al tenant y proteccion contra degradacion accidental de administradores.
6.  **Sincronizacion Perfil <-> Empresa (Sedes, Areas y Departamentos)**: Vinculacion dinamica de sedes y areas pertenecientes a la app `empresa` con el perfil del usuario, controlando su asignacion multiple (Many-to-Many).
7.  **[SEG-5] Guard Anti-Auto-Eliminacion**: Proteccion en 3 capas que impide que cualquier usuario elimine su propio perfil o el del administrador primario del tenant.

---

## Stack Tecnologico (Alineacion v3.10.2)

- **Backend**: Django DRF (PerfilViewSet con Dual-Auth JWT/Session).
- **Service Layer**: Estructura modular (`Selectors`, `Business`, `CRUD`).
- **Bridge**: Interaccion con el esquema publico para validacion de membresia primaria.
- **Frontend**: Vanilla JS (Namespace `window.Sintel.Perfil`) con modulos FSD y scripts de comportamiento en templates.
- **UI**: Tabulator para gestion de colaboradores y Bootstrap Offcanvas para creacion y edicion de perfiles.

---

## Estructura de Servicios y APIs

### Servicios Principales
- `PerfilSelector`: Consultas optimizadas con `.only()` de campos de perfil y usuario, cargando relaciones con select_related y prefetch_related para evitar consultas N+1.
- `PerfilBusinessService`: Orquestador de invitaciones, validacion de roles, auto-elevacion y Doble Verificacion Semantica (DSV).
- `PerfilCRUDService`: Persistencia atomica de perfiles y actualizacion de metadatos (incluyendo sedes y areas).

### Endpoints Estrategicos

| Metodo | URL | Acceso | Descripcion |
|--------|-----|--------|-------------|
| `GET` | `/api/v1/perfil/perfiles/me/` | Cualquier rol | Perfil + permissions_context del usuario actual (Fast Path). |
| `GET` | `/api/v1/perfil/perfiles/` | Cualquier rol | Lista todos los perfiles del tenant (paginado). |
| `POST` | `/api/v1/perfil/perfiles/` | ADMIN | Crea usuario global + perfil (idempotente por email). |
| `PATCH` | `/api/v1/perfil/perfiles/{uuid}/` | ADMIN | Actualiza perfil y asignaciones organizacionales. |
| `DELETE` | `/api/v1/perfil/perfiles/{uuid}/` | ADMIN | Elimina perfil. Bloqueado si es auto-eliminacion o primary admin. |
| `PATCH` | `/api/v1/perfil/perfiles/{uuid}/assign-rol/` | ADMIN | Asigna rol al perfil via endpoint dedicado (DSV). |
| `GET` | `/api/v1/perfil/perfiles/render-offcanvas/crear/` | ADMIN | Fragmento HTML Offcanvas de creacion (HTMX). |
| `GET` | `/api/v1/perfil/perfiles/{uuid}/render-offcanvas/editar/` | ADMIN | Fragmento HTML Offcanvas de edicion (HTMX). |
| `GET` | `/api/v1/perfil/perfiles/{uuid}/render-offcanvas/detalle/` | Cualquier rol | Fragmento HTML Offcanvas de detalle (HTMX). |

---

## [SEG-5] Guard Anti-Auto-Eliminacion (v3.10.2)

Implementacion en 3 capas para evitar que un administrador elimine su propio perfil o el del propietario primario del tenant.

### Capa 1: ViewSet `destroy()` — Guard principal

`apps/tenant/perfil/api/viewsets.py` — metodo `destroy()`:

```python
# Guard 1: prohibir auto-eliminacion
if target_profile.user_id == request.user.id:
    return Response({"error": "No puedes eliminar tu propio perfil de usuario."}, status=400)

# Guard 2: prohibir eliminar al administrador primario del tenant
if self.perfil_service._is_tenant_primary_admin(target_profile.user):
    return Response({"error": "No se puede eliminar al administrador primario del tenant."}, status=400)
```

Usa `target_profile.user_id` (FK raw, sin hit a DB adicional) y `_is_tenant_primary_admin()` (ya existia en `PerfilBusinessService`, valida contra `Empresa.owner_email` Tier-1 y TenantMembership Tier-2).

### Capa 2: `permissions_context` — exponer `user_id` al frontend

`apps/tenant/perfil/api/permissions.py` — `get_permissions_context()`:

Retorna `'user_id': perfil.user_id` junto al resto de flags. El endpoint `/me/` expone esto bajo `permissions_context.user_id` para uso en la UI sin llamada extra.

### Capa 3: Frontend — boton eliminar invisible para fila propia

`apps/tenant/perfil/static/perfil/js/perfil.page.js`:

```javascript
// En loadRequestorContext():
requestorContext.user_id = myProfile.user_id || null;

// En getColumns() formatter de acciones:
var isSelf = requestorContext.user_id != null && data.user_id != null
  && Number(data.user_id) === Number(requestorContext.user_id);
var canDelete = actions.includes('delete') && !isSelf;
```

El boton "Eliminar" no se renderiza para la propia fila del usuario autenticado.

### Tabla de comportamiento

| Escenario | Backend | Frontend |
|-----------|---------|----------|
| ADMIN intenta borrar su propia fila | HTTP 400 | Boton no aparece |
| ADMIN intenta borrar al owner/primary admin | HTTP 400 | Boton visible, rechazado |
| ADMIN borra a otro usuario no-owner | HTTP 204 OK | Boton visible y funcional |

---

## Sincronizacion Perfil <-> Empresa (Detalles de Implementacion)

Para garantizar la integridad y coherencia de datos entre el modulo `perfil` y `empresa`, se implemento la siguiente logica de sincronizacion dinamica:

### 1. Filtrado Dinamico en la UI (DOM Shield)
En el formulario de **Nuevo Usuario + Perfil** (`offcanvas_crear_perfil.html`), se introdujo un script de filtrado en el cliente para ocultar y deshabilitar opciones no pertenecientes a la empresa seleccionada:
- **Sedes y Areas**: Se asocian mediante el atributo `data-empresa`. Al cambiar la empresa, solo se muestran las sedes de esa empresa. Al seleccionar una sede, el selector de areas filtra aquellas vinculadas a la sede mediante `data-sede`.
- **Departamentos**: Los departamentos tambien provienen de la app `empresa` y se filtran dinamicamente mediante el atributo `data-empresa="{{ dept.empresa_id }}"` en el selector.
- **Campos Ocultos**: Para respetar la regla de proteccion DOM Shield, los selectores visibles no contienen atributos `name`. En su lugar, listeners de JS actualizan inputs ocultos (`<input type="hidden">`) que viajan de forma segura al backend con los UUIDs reales.

### 2. Optimizacion del Backend (Zero Waste)
Los endpoints de renderizado del `offcanvas` en `viewsets.py` (`render_offcanvas_crear` y `render_offcanvas_editar`) utilizan consultas altamente optimizadas:
- Se limitan los campos consultados en la base de datos utilizando `.only('uuid', 'nombre')` en `Departamento`, `Sede` y `Area`.
- Se restringen las consultas de departamentos a la empresa activa (`empresa=empresa`) para aislamiento SaaS Multi-Tenant absoluto.

---

## Proximos Pasos (MT-PRF)

Las tareas de evolucion tecnica se encuentran en [Arquitectura de Microtareas](docs/perfil_microtasks_architecture.md).

> **INVARIANTE CRITICO:** El sistema no permite que un tenant se quede sin administradores activos. Cualquier intento de degradar al ultimo `ADMIN`, auto-eliminarse, o borrar al admin primario resultara en un error de validacion de negocio (HTTP 400).
