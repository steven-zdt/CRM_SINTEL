# [PORTAL] Auditoria y SSoT: Modulo Perfil (Gestion de Usuarios y Roles)

**Version:** 3.10.3
**Estado:** PRODUCTION READY
**Ubicacion:** `apps/tenant/perfil/`
**Ultima Auditoria:** 2026-08-21 (validacion de estado tras mision UX -- ver §"Cambios UX 2026-08-21" abajo; backend/API/modelos sin cambios desde v3.10.2, 2026-05-25)

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

## Cambios UX 2026-08-21 (mision de transformacion UX/UI)

Durante la mision de transformacion UX/UI de esta fecha se tocaron 2 puntos
puramente de presentacion en este modulo -- **cero cambios de backend, API,
modelos, permisos o logica de negocio**. Detalle completo en
`documentacion/ux/UX_MASTER_BASELINE.md` §"FASE Perfil"; resumen aqui:

### 1. Rotulo de navegacion corregido: "Mi perfil" -> "Usuarios y roles"

**Hallazgo:** el tab `#perfil` (enlazado desde el sidebar del workspace y desde
el dropdown de cuenta, ambos con el rotulo "Mi perfil"/"Perfil") **nunca
mostro un editor de datos personales del usuario autenticado** -- siempre
mostro la tabla completa de todos los perfiles del tenant con sus roles (ver
§"Responsabilidades Core" arriba, punto 2, RBAC), visible para cualquier
miembro (`permission_classes = [IsTenantMember]` en `PerfilViewSet`, no solo
ADMIN). El rotulo prometia una pantalla personal y entregaba gestion de todo
el equipo -- confusion real para cualquier usuario, no solo nuevos.

**No existe hoy, en ningun lugar del codebase, una pantalla separada de
"editar mi propio perfil"** distinta de esta tabla de gestion de usuarios.
Si en el futuro se decide construir una, este documento es el punto de
partida correcto (el modelo `TenantProfile` y el endpoint `GET
/api/v1/perfil/perfiles/me/` ya devuelven los datos del usuario actual, listo
para alimentar un formulario personal si se construye).

**Cambio aplicado (solo texto de navegacion, verificado que no toca
`href`/destino ni logica):**
- `apps/tenant/core/templates/tenant/core/workspace.html` -- link del sidebar.
- `apps/tenant/core/templates/tenant/partials/_header.html` -- link del
  dropdown de cuenta.
- `apps/tenant/core/static/core/js/workspace.js` -- mapa de titulos de
  `viewTitle` usado por `showTab()`.

### 2. Comentario de seguridad [SEC-A1] que se filtraba como texto visible (bug critico, ya corregido)

**Hallazgo:** `apps/tenant/perfil/templates/tenant/perfil/offcanvas_detalle_perfil.html`
tenia un comentario Django `{# ... #}` que abarcaba 2 lineas -- Django's
`{# #}` **no soporta comentarios multilinea** (limitacion documentada del
motor de templates: si el contenido cruza un salto de linea, el tokenizer no
lo reconoce como comentario y lo pasa como texto plano sin procesar). El
comentario en cuestion explicaba una decision de seguridad real:

> [SEC-A1] Sin `|safe`: `profile.cargo` es texto editable por el usuario; el
> placeholder "No definido" es el unico HTML literal y vive fuera del valor
> interpolado.

Esto se estaba renderizando literalmente en el offcanvas de detalle de
perfil, visible para cualquier usuario que lo abriera -- no era una falla de
la proteccion `|safe` en si (esa seguia funcionando correctamente en el
codigo), pero exponia texto de documentacion interna de seguridad en la UI de
produccion, ademas de verse como un bug visual.

**Cambio aplicado:** convertido a `{% comment %}...{% endcomment %}` (el tag
de Django que si soporta contenido multilinea correctamente) -- mismo texto,
solo cambia el delimitador, cero cambio de logica. El mismo patron de bug se
encontro y corrigio en otros 10 archivos de otras 8 apps del sistema en la
misma pasada (ver `UX_MASTER_BASELINE.md` para el listado completo).

### Verificacion realizada (2026-08-21)

- Ambos templates (`workspace.html`, `offcanvas_detalle_perfil.html`) y
  `_header.html` parsean sin error.
- Render real via Django test Client + `force_login()`: el sidebar y el
  dropdown de cuenta muestran "Usuarios y roles" (no "Mi perfil"/"Perfil"),
  ambos apuntando exactamente igual a `#perfil`.
- El guard SEG-5 (`destroy()` en `viewsets.py`, lineas ~248-255) se releyo
  directamente del codigo fuente en esta fecha -- coincide exactamente con lo
  documentado arriba, sin drift.
- No se ejecuto la suite de tests de Perfil en esta pasada (a peticion
  explicita del usuario, "no corras test") -- esta seccion documenta el
  estado del codigo verificado por lectura directa, no por corrida de tests.

---

## Proximos Pasos (MT-PRF)

Las tareas de evolucion tecnica se encuentran en [Arquitectura de Microtareas](docs/perfil_microtasks_architecture.md).

> **INVARIANTE CRITICO:** El sistema no permite que un tenant se quede sin administradores activos. Cualquier intento de degradar al ultimo `ADMIN`, auto-eliminarse, o borrar al admin primario resultara en un error de validacion de negocio (HTTP 400).
