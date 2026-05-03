# AUDITORIA DE FLUJO COMPLETO - Módulo Clientes SINTEL v3.6

**Última Actualización:** 2026-05-03
**Estado:** SPRINT 5 COMPLETADO — Columna Encargado, estandarización REST endpoints, tabla Directorio Contactos con View/Edit/Delete, sub-tabs Bootstrap independientes.

---

## 1. Resumen Ejecutivo

El módulo de Clientes gestiona la información legal, comercial y de contacto de los clientes bajo una arquitectura **Feature-Sliced Design (FSD)** multi-tenant. Cada cliente puede tener múltiples contactos (`ContactoCliente`) que se persisten de forma atómica en la misma transacción del maestro. Un contacto marcado como `is_principal=True` es el **Encargado** visible en la tabla principal de clientes.

**Principios aplicados:**
- **Modular Service Layer (v3.5):** Descomposición en `selectors.py` (lectura), `crud_service.py` (escritura) y `business_service.py` (lógica y orquestación).
- **Double Semantic Verification (DSV):** Validación forzada en `get_object()` para garantizar aislamiento estricto por tenant.
- **Aislamiento FSD (Assets):** Templates y Scripts JS residen localmente en la app `clientes`, eliminando dependencias del monolito `core`.
- **Zero Waste Queries:** Prefetch de contactos principales filtrado por `is_principal=True` para evitar N+1.
- **Dual-Auth Bridge:** Soporte para SessionAuth y JWT (vía `TabulatorFactory`).

---

## 2. Estructura de Directorios (FSD)

```
apps/tenant/clientes/
    AUDITORIA_FLUJO_CLIENTES.md         <- Este archivo (SSoT)
    models.py                           <- Herencia SintelTenantBaseModel
    api/
        viewsets.py                     <- DSV en get_object(), Prefetch encargado
        serializers.py                  <- NormalizationMixin + campo encargado
        mixins.py                       <- ClienteServiceMixin, ContactoServiceMixin
        urls.py                         <- Router: contactos antes de ''
    services/
        selectors.py                    <- Zero Waste Queries (.only)
        crud_service.py                 <- Atomic Mutations
        business_service.py             <- Business Flow Orchestration
    templates/
        tenant/clientes/
            clientes_list.html          <- Dos sub-tabs Bootstrap (v2.62)
            contactos_list.html         <- Template auxiliar (no usado en workspace)
            offcanvas_crear_cliente.html
            offcanvas_editar_cliente.html   <- onsubmit="return false;" (v2.62)
            offcanvas_detalle_cliente.html
            assets_clientes.html
        tenant/contactos/
            offcanvas_crear_contacto_cliente.html
            offcanvas_editar_contacto_cliente.html
            offcanvas_detalle_contacto_cliente.html   <- id="offcanvas-contacto-cliente"
            list_contacto_cliente.html
            assets_contactos.html
    static/clientes/js/
        clientes.api.js                 <- window.clientesAPI + window.contactosAPI
        clientes.utils.js
        clientes.list.js                <- Tabulator + two sub-tabs (v2.62)
        clientes.editor.js              <- DOM Shield implementado
        clientes.detalle.js
        clientes.contactos.js
        contactos/
            contacto_cliente_api.js
            contacto_cliente_utils.js
            contacto_cliente_form.js
            contacto_cliente_main.js
```

---

## 3. Modelos (Anémicos)

### 3.1. `Cliente`

Hereda de `SintelTenantBaseModel`, que inyecta automáticamente el FK `empresa` y garantiza el aislamiento por esquema sin declararlo explícitamente en el modelo.

**Campos principales:**

| Campo | Tipo | Notas |
|---|---|---|
| `tipo_persona` | CharField | `NATURAL` / `JURIDICA` |
| `tipo_documento` | CharField | NIT, CC, CE, PA |
| `numero_documento` | CharField | Validado sin puntos ni guiones |
| `razon_social` | CharField | Nombre legal |
| `nombre_comercial` | CharField | Opcional |
| `regimen_tributario` | CharField | `SIMPLE`, `ORDINARIO`, `NO_RESP` |
| `email` | EmailField | Opcional |
| `telefono` | CharField | Normalizado |
| `direccion` | TextField | Opcional |
| `ciudad` | CharField | Opcional |
| `activo` | BooleanField | Default `True`; debe estar `False` para poder eliminar |
| `observaciones` | TextField | Opcional |

**Constraints e índices:**
```
UNIQUE: (empresa_id, tipo_documento, numero_documento)  -- uniq_doc_cliente_empresa
INDEX:  (empresa_id, activo)
INDEX:  (numero_documento)
```

### 3.2. `ContactoCliente`

Hereda de `SintelTenantBaseModel`. FK a `Cliente` con `CASCADE` y `related_name='contactos'`.

**Campos principales:**

| Campo | Tipo | Notas |
|---|---|---|
| `cliente` | FK(Cliente) | CASCADE, related_name='contactos' |
| `nombre_completo` | CharField | Requerido |
| `cargo` | CharField | Opcional |
| `email` | EmailField | Requerido; único por cliente |
| `telefono` | CharField | Opcional |
| `activo` | BooleanField | Default `True` |
| `is_principal` | BooleanField | Default `False`; marca al Encargado visible en tabla |

**Constraints e índices:**
```
UNIQUE: (cliente_id, email)                -- uniq_contacto_cliente_email
INDEX:  (cliente_id, activo)
INDEX:  (cliente_id, is_principal)
```

**Ordering:** `["-is_principal", "nombre_completo"]` — el encargado siempre aparece primero.

---

## 4. Service Layer

### 4.1. `ClienteBusinessService` — `services/business_service.py`

SSoT absoluta para toda lógica de negocio. Inyectado en `ClienteViewSet` vía `ClienteServiceMixin`.

#### Métodos de consulta

| Método | Descripción |
|---|---|
| `get_cliente_list(empresa_id, search=None)` | Lista con filtro Q sobre razón social, documento, email, nombre comercial |
| `qs_detail(empresa_id, pk)` | Retorna instancia o `None` (no lanza excepción) |
| `get_contactos_queryset(empresa_id, cliente_id=None)` | ContactoCliente con `select_related("cliente")` |

#### Operaciones de escritura

Todos los métodos están decorados con `@transaction.atomic`.

**`registrar_cliente_completo(empresa_id, data, contactos_raw=None)`**

Flujo unificado para create y update:
1. Busca cliente existente por `(empresa_id, tipo_documento, numero_documento)`.
2. Si no existe: `Cliente.objects.create(empresa_id=empresa_id, **data)`.
3. Si existe: actualiza campos via `setattr` + `cliente.save()`.
4. Si `contactos_raw` es lista: elimina contactos anteriores y recrea (replace all).
5. Retorna cliente refrescado.

**`delete_cliente(cliente)`** — `crud_service.py`

1. Si `cliente.activo == True`: `ValidationError({"error": "active_record"})`.
2. `cliente.delete()`.

Regla de negocio: **cliente activo no se puede eliminar directamente**. La UI ejecuta PATCH `{activo: false}` previo (two-step delete).

### 4.2. Selectores — `services/selectors.py`

`ClienteSelector.get_cliente_list()` devuelve el queryset base para el endpoint `list`. Incluye el Prefetch de encargado para que el serializer no genere N+1.

---

## 5. API — ViewSets y URLs

### 5.1. Router (orden crítico)

**Archivo:** `apps/tenant/clientes/api/urls.py`

```python
router.register(r'contactos', ContactoClienteViewSet, basename='contactocliente')
router.register(r'', ClienteViewSet, basename='cliente')
```

El prefijo `contactos` debe registrarse **antes** que el prefijo vacío `''`. Si se invierte, DRF interpreta `"contactos"` como un PK numérico.

### 5.2. `ClienteViewSet`

Hereda de `ClienteServiceMixin, BaseTenantViewSet`.

**Endpoints REST estándar:**

| Método | URL | Acción | Descripción |
|---|---|---|---|
| GET | `/api/v1/clientes/` | `list` | Lista paginada para Tabulator (incluye campo `encargado`) |
| POST | `/api/v1/clientes/` | `create` | Crear cliente con contactos anidados |
| GET | `/api/v1/clientes/{id}/` | `retrieve` | Detalle |
| PUT | `/api/v1/clientes/{id}/` | `update` | Actualización completa |
| PATCH | `/api/v1/clientes/{id}/` | `partial_update` | Actualización parcial (usado para desactivar antes de eliminar) |
| DELETE | `/api/v1/clientes/{id}/` | `destroy` | Eliminación física (solo si `activo=False`) |

**Endpoints HTMX (render-offcanvas):**

| Método | URL | Detail | Descripción |
|---|---|---|---|
| GET | `/api/v1/clientes/render-offcanvas/crear/` | `False` | HTML offcanvas creación |
| GET | `/api/v1/clientes/{id}/render-offcanvas/editar/` | `True` | HTML offcanvas edición |
| GET | `/api/v1/clientes/{id}/render-offcanvas/detalle/` | `True` | HTML offcanvas detalle read-only ✅ v2.62 |
| GET | `/api/v1/clientes/offcanvas/` | `False` | Endpoint legacy unificado (crear o editar por `?id=`) |

> **v2.62 breaking change:** `render_offcanvas_detalle` pasó de `detail=False` con query param `?id=` a `detail=True` con URL kwarg `/{id}/`. El frontend `viewCliente(id)` fue actualizado en consecuencia.

### 5.3. `get_queryset` — Prefetch de Encargado (v2.62)

```python
def get_queryset(self):
    empresa = self.get_empresa()
    if not empresa:
        return Cliente.objects.none()

    contactos_qs = ContactoCliente.objects.filter(is_principal=True).only(
        'id', 'cliente_id', 'nombre_completo', 'email'
    )
    prefetch = Prefetch('contactos', queryset=contactos_qs, to_attr='contactos_prefetched')

    return Cliente.objects.filter(empresa_id=empresa.id).only(...).prefetch_related(prefetch)
```

El Prefetch filtra **únicamente** los contactos `is_principal=True` (1 por cliente) y los asigna al atributo `contactos_prefetched`. El serializer accede a este atributo sin generar queries adicionales.

### 5.4. Resolución de empresa — `get_empresa()`

Cadena de fallback de 4 niveles en `resolve_tenant_empresa(request, view_instance)`:

```
1. view_instance.__dict__['tenant_empresa']  (cached_property, evita recursión)
2. request.tenant.empresa                    (middleware multi-tenant)
3. request.tenant_empresa                    (compatibilidad legacy)
4. Empresa.objects.first()                   (singleton del esquema actual)
   -> ProgrammingError -> None               (esquema sin migraciones tenant)
```

### 5.5. `ContactoClienteViewSet`

Hereda de `ContactoClienteServiceMixin, BaseTenantViewSet`. `lookup_field = 'id'`.

**Endpoints HTMX:**

| Método | URL | Detail | Descripción |
|---|---|---|---|
| GET | `/api/v1/clientes/contactos/render-offcanvas/crear/` | `False` | HTML creación contacto |
| GET | `/api/v1/clientes/contactos/{id}/render-offcanvas/editar/` | `True` | HTML edición contacto |
| GET | `/api/v1/clientes/contactos/{id}/render-offcanvas/detalle/` | `True` | HTML detalle contacto read-only ✅ v2.62 |

> **v2.62:** El endpoint `render_offcanvas_detalle` de contactos aún usa `detail=False` con `?id=` — es independiente del cambio aplicado a `ClienteViewSet`.

---

## 6. Serializers

**Archivo:** `apps/tenant/clientes/api/serializers.py`

### 6.1. `ClienteListSerializer` (v2.62)

Solo lectura. Usado exclusivamente en el endpoint `list`. Incluye:

- Campos computados con sufijo `_display` para Tabulator (ej. `tipo_persona_display`).
- **Campo `encargado` (nuevo v2.62):** `SerializerMethodField` que retorna `{nombre, email}` del contacto `is_principal` o `None`.

```python
encargado = serializers.SerializerMethodField()

def get_encargado(self, obj):
    principal = obj.contactos_prefetched[0] if (
        hasattr(obj, 'contactos_prefetched') and obj.contactos_prefetched
    ) else None
    if principal:
        return {'nombre': principal.nombre_completo, 'email': principal.email}
    return None
```

Depende del Prefetch `contactos_prefetched` definido en `get_queryset()`. Sin Prefetch, el campo retorna `None` (no genera query de fallback).

### 6.2. `ContactoClienteSerializer(NormalizationMixin, ModelSerializer)`

- `id = IntegerField(required=False, allow_null=True)` — declarado explícitamente para que DRF incluya el ID en `validated_data`.
- `validate()`: verifica que el cliente pertenezca al tenant, valida unicidad `(cliente, email)` en update.

### 6.3. `ClienteDetailSerializer(NormalizationMixin, ModelSerializer)`

- Usado para create, update y partial_update.
- `validate()`: normaliza `numero_documento`, valida unicidad de documento excluyendo instancia actual.

### 6.4. `NormalizationMixin`

Importado desde `apps/tenant/api/utils.py`. Provee `normalize_data()`, `normalize_phone()`, `normalize_document_number()`.

---

## 7. Frontend — Módulos JS

### 7.1. `clientes.list.js` — Orquestador Tabulator (v2.62)

**Namespace:** `window.AppCliente`, `window.ClientesListModule`

**Estado del módulo:**
```javascript
const state = {
    clientesLoaded: false, clientesLoading: false,
    contactosLoaded: false, contactosLoading: false,
    clientesTable: null, contactosTable: null
};
```

#### Columnas tabla Clientes — `TABLE_COLUMNS.clientes`

| Columna | Field | Notas |
|---|---|---|
| Razón Social | `razon_social` | widthGrow: 2 |
| Documento | `numero_documento` | |
| Email | `email` | |
| Teléfono | `telefono` | |
| Ciudad | `ciudad` | |
| **Encargado** ✅ v2.62 | `encargado` | Formatter: `<strong>nombre</strong><br><span>email</span>` o `—` |
| Acciones | — | Ver → Editar → Eliminar |

#### Columnas tabla Contactos — `TABLE_COLUMNS.contactos`

| Columna | Field | Notas |
|---|---|---|
| Nombre | `nombre_completo` | widthGrow: 2 |
| Email | `email` | |
| Teléfono | `telefono` | |
| Cargo | `cargo` | Fallback `—` |
| Estado | `activo` | Badge success/danger |
| Acciones | — | **Ver** ✅ v2.62 → Editar → Eliminar |

#### Acciones tabla Clientes — orden VER → EDITAR → ELIMINAR

```javascript
cellClick: (e, cell) => handleCellAction(e, cell, 'clientes')
// case 'view'   -> viewCliente(id)
// case 'edit'   -> editCliente(id)
// case 'delete' -> deleteCliente(rowData)  [rowData completo para two-step]
```

#### Acciones tabla Contactos — orden VER → EDITAR → ELIMINAR (v2.62)

```javascript
cellClick: (e, cell) => handleCellAction(e, cell, 'contactos')
// case 'view'   -> viewContacto(id)     [nuevo v2.62]
// case 'edit'   -> editContacto(id)
// case 'delete' -> deleteContacto(id)
```

#### URLs de offcanvas (v2.62)

| Función | URL generada | Cambio |
|---|---|---|
| `editCliente(id)` | `/api/v1/clientes/${id}/render-offcanvas/editar/` | Sin cambio |
| `viewCliente(id)` | `/api/v1/clientes/${id}/render-offcanvas/detalle/` | ✅ Antes: `?id=${id}` |
| `viewContacto(id)` | `/api/v1/clientes/contactos/${id}/render-offcanvas/detalle/` | ✅ Nuevo v2.62 |
| `editContacto(id)` | `/api/v1/clientes/contactos/gestor-offcanvas/?id=${id}` | Sin cambio |

#### Apertura de offcanvas — `htmx:afterSettle` (v2.62)

Patrón refactorizado a helper reutilizable:

```javascript
const showOffcanvas = (containerId, offcanvasId) => {
    if (target && target.id === containerId) {
        requestAnimationFrame(() => requestAnimationFrame(() => {
            const el = d.getElementById(offcanvasId);
            if (el) waitForBootstrap(() => bootstrap.Offcanvas.getOrCreateInstance(el).show());
        }));
    }
};
showOffcanvas('offcanvas-container-clientes', 'offcanvas-cliente');
showOffcanvas('offcanvas-container-contactos', 'offcanvas-contacto-cliente');
```

#### Carga lazy de tablas — eventos (v2.62)

| Evento | Origen | Acción |
|---|---|---|
| `tab-activated` con `tabName='clientes'` | workspace.js | `loadClientesTable()` |
| `tab-shown` con `tabName='clientes'` | workspace.js | `loadClientesTable()` |
| `shown.bs.tab` con target `#tab-pane-contactos` | Bootstrap | `loadContactosTable()` (lazy al primer clic) |
| `DOMContentLoaded` | Browser | `loadClientesTable()` si `#tab-clientes` visible |

### 7.2. `clientes.editor.js` — Formulario Maestro-Detalle

**Estrategia de payload (Zero Trust):** No se usa `FormData`. Cada campo se extrae manualmente:

```javascript
const getText = (selector) => (form.querySelector(selector)?.value || '').trim();
const getBool = (selector) => form.querySelector(selector)?.checked ?? false;
```

DOM Shield en contactos: el ID del contacto se lee desde `data-contacto-id` en `.contacto-item`, nunca de un `<input name>`. Se convierte con `parseInt(rawId, 10) || null` — `null` para contactos nuevos.

**`formatApiError(val)`:** Función recursiva que previene `[object Object]` cuando DRF retorna errores anidados en contactos.

**Discriminador create/update:** Verifica `#cliente-id` value para distinguir POST (vacío) de PATCH (con ID).

### 7.3. `clientes.api.js` — Capa de datos

Expone `window.clientesAPI` y `window.contactosAPI` (Object.freeze). Alias bajo `window.AppCliente.api` y `window.AppCliente.contactosApi`. Métodos: `list`, `get`, `create`, `update`, `delete`.

---

## 8. Templates HTMX

**Ruta base:** `apps/tenant/clientes/templates/tenant/`

### Clientes

| Template | URL que lo carga | Contenedor destino | Offcanvas ID |
|---|---|---|---|
| `clientes/offcanvas_crear_cliente.html` | `GET render-offcanvas/crear/` | `#offcanvas-container-clientes` | `offcanvas-cliente` |
| `clientes/offcanvas_editar_cliente.html` | `GET {id}/render-offcanvas/editar/` | `#offcanvas-container-clientes` | `offcanvas-cliente` |
| `clientes/offcanvas_detalle_cliente.html` | `GET {id}/render-offcanvas/detalle/` ✅ v2.62 | `#offcanvas-container-clientes` | `offcanvas-cliente-detalle` |

> **v2.62:** `offcanvas_editar_cliente.html` ahora tiene `onsubmit="return false;"` en el `<form>`, alineado con el template de creación.

### Contactos

| Template | URL que lo carga | Contenedor destino | Offcanvas ID |
|---|---|---|---|
| `contactos/offcanvas_crear_contacto_cliente.html` | `GET contactos/render-offcanvas/crear/` | `#offcanvas-container-contactos` | — |
| `contactos/offcanvas_editar_contacto_cliente.html` | `GET contactos/{id}/render-offcanvas/editar/` | `#offcanvas-container-contactos` | — |
| `contactos/offcanvas_detalle_contacto_cliente.html` | `GET contactos/{id}/render-offcanvas/detalle/` ✅ v2.62 | `#offcanvas-container-contactos` | `offcanvas-contacto-cliente` |

### Layout principal

| Template | Contenido |
|---|---|
| `clientes/clientes_list.html` | Dos sub-tabs Bootstrap: Directorio de Clientes + Directorio de Contactos. Ambos offcanvas containers al final. |
| `clientes/assets_clientes.html` | Carga JS en orden: `clientes.api.js` → `clientes.utils.js` → `clientes.list.js` → `clientes.editor.js` → `clientes.detalle.js` → `clientes.contactos.js` |
| `contactos/assets_contactos.html` | Carga `contacto_cliente_api.js`, `utils.js`, `form.js`, `main.js` |

---

## 9. Estructura Workspace

**Archivo:** `apps/tenant/core/templates/tenant/core/workspace.html`

```
Sidebar nav:
  ...
  [Clientes]   data-tab="clientes"   -> section#tab-clientes
  [Proveedores] ...
  ...

section#tab-clientes:
  {% include 'tenant/clientes/clientes_list.html' %}
  |
  +-- Bootstrap nav-tabs
      |-- "Directorio de Clientes"  (activo por defecto)  -> #tab-pane-clientes
      |-- "Directorio de Contactos"                        -> #tab-pane-contactos
```

El sub-tab de Contactos carga su tabla **lazy** al primer clic (evento `shown.bs.tab`).

---

## 10. Patrones Críticos

### 10.1. Obligatorios

| Patrón | Ubicación | Estado |
|---|---|---|
| `table.destroy()` antes de re-inicializar Tabulator | `clientes.list.js:load*Table` | ✅ |
| `UIManager.handleError()` para notificaciones globales | `clientes.list.js:showError` | ✅ |
| `formatApiError()` recursivo para errores anidados | `clientes.editor.js` | ✅ |
| `parseInt(rawId, 10) \|\| null` para IDs de contacto | `clientes.editor.js` | ✅ |
| `@transaction.atomic` en todos los métodos de escritura | `crud_service.py`, `business_service.py` | ✅ |
| Zero Waste: `.only(*FIELDS)` en todas las queries | `viewsets.py`, `selectors.py` | ✅ |
| Prefetch `contactos_prefetched` filtrado por `is_principal=True` | `viewsets.py:get_queryset` | ✅ v2.62 |
| DSV en `get_object()` (tenant check) | `viewsets.py` | ✅ |
| Router order: `contactos` antes de `''` | `api/urls.py` | ✅ |
| `onsubmit="return false;"` en ambos forms (crear y editar) | offcanvas_*.html | ✅ v2.62 |

### 10.2. Antipatrones resueltos

| Antipatrón | Consecuencia | Resolución |
|---|---|---|
| `render_offcanvas_detalle` con `detail=False, ?id=` | Inconsistencia con editar; fragilidad en routing | `detail=True`, URL kwarg `/{id}/` (v2.62) |
| Sin columna "Encargado" en tabla | Usuario no ve quién gestiona el cliente | SerializerMethodField + Prefetch is_principal (v2.62) |
| Sin botón "Ver" en tabla de contactos | Solo edit+delete disponibles | Agregado view button, `viewContacto()`, handler htmx:afterSettle (v2.62) |
| `offcanvas_editar_cliente.html` sin `onsubmit="return false;"` | Submit por teclado bypasseaba JS handler | Fix alineado con create form (v2.62) |
| `notifyError()` en `clientes.list.js` | Inyectaba error en `#form-inventario-feedback` | Reemplazado por `UIManager.handleError()` |
| `deleteCliente(rowData.id)` sin `activo` | Backend retornaba 400 sin contexto del estado | Reemplazado por `deleteCliente(rowData)` con objeto completo |
| `FormData` en payload de contactos | DOM Shield roto por `<select name>` | Extracción manual campo por campo |
| Tabulator sin `destroy()` antes de reemplazar | `Event Target Lookup Error` | Guard `table.destroy()` antes de re-init |

---

## 11. Flujos Completos

### 11.1. Crear Cliente con Contactos

```
[Usuario] Click "Nuevo Cliente"
    -> [HTMX] GET /api/v1/clientes/render-offcanvas/crear/
    -> render_offcanvas_crear() -> HTML en #offcanvas-container-clientes
    -> [Bootstrap] htmx:afterSettle -> Offcanvas.show('offcanvas-cliente')

[Usuario] Completa form -> Click "Guardar"
    -> [JS] recolectarDatosFormulario()
        -> getText() / getBool() campo por campo (sin FormData)
        -> contactos: querySelectorAll('.contacto-item') -> payload explícito
        -> parseInt(rawId, 10) || null para IDs de contacto
    -> [JS] clientesAPI.create(data)  [POST /api/v1/clientes/]
    -> [Backend] ClienteViewSet.create()
        -> ClienteDetailSerializer.validate()
        -> registrar_cliente_completo(empresa_id, validated_data, contactos_raw)
            -> upsert por (empresa_id, tipo_doc, num_doc)
            -> delete existing contactos + create new
        -> HTTP 201
    -> [JS] Exito: dispatchEvent('clienteGuardado') -> table.replaceData()
    -> [JS] Error: formatApiError() -> #form-cliente-feedback
```

### 11.2. Eliminar Cliente (Two-Step)

```
[Usuario] Click "Eliminar" en fila Tabulator
    -> handleCellAction -> deleteCliente(rowData)  [rowData completo]

deleteCliente(rowData):
  rowData.activo == true?
    -> confirm("Inactivar + eliminar?")
    -> clientesAPI.update(id, {activo: false})  [PATCH]
        -> Error -> showError(detail)  STOP
  -> confirm("Eliminar definitivamente?")
  -> clientesAPI.delete(id)  [DELETE]

[Backend] ClienteViewSet.destroy()
    -> get_object() con DSV
    -> cliente_crud.delete_cliente(cliente)
        -> activo? -> ValidationError 'active_record'
        -> cliente.delete()
    -> HTTP 204

[JS] dispatchEvent('clienteEliminado') -> table.replaceData()
```

### 11.3. Ver Detalle Cliente (v2.62)

```
[Usuario] Click "Ver" (ojo) en fila Tabulator
    -> handleCellAction -> viewCliente(id)
    -> [HTMX] GET /api/v1/clientes/{id}/render-offcanvas/detalle/
        -> render_offcanvas_detalle(request, pk=id)
        -> get_object() [DSV — valida tenant]
        -> HTML en #offcanvas-container-clientes
    -> htmx:afterSettle -> showOffcanvas('offcanvas-container-clientes', 'offcanvas-cliente-detalle')
```

### 11.4. Ver Detalle Contacto (v2.62)

```
[Usuario] Click "Ver" (ojo) en fila tabla Contactos
    -> handleCellAction('contactos') -> viewContacto(id)
    -> [HTMX] GET /api/v1/clientes/contactos/{id}/render-offcanvas/detalle/
        -> HTML en #offcanvas-container-contactos
    -> htmx:afterSettle -> showOffcanvas('offcanvas-container-contactos', 'offcanvas-contacto-cliente')
```

### 11.5. Editar Cliente

```
[Usuario] Click "Editar" en fila Tabulator
    -> editCliente(id)
    -> [HTMX] GET /api/v1/clientes/{id}/render-offcanvas/editar/
        -> get_object() [DSV]
        -> get_contacto_list(empresa_id, cliente_id)
        -> HTML offcanvas_editar_cliente.html en #offcanvas-container-clientes

[Usuario] Modifica -> Click "Actualizar"
    -> recolectarDatosFormulario()
    -> clientesAPI.update(id, data)  [PATCH]
    -> [Backend] partial_update() -> registrar_cliente_completo() -> HTTP 200
    -> dispatchEvent('clienteGuardado') -> table.replaceData()
```

---

## 12. Checklist de Verificación (v2.62)

- [x] Zero Trust: `destroy` delega a service con validación interna de tenant.
- [x] Zero Trust: Payload de formulario construido campo por campo (no `FormData`).
- [x] Zero Trust: `parseInt(rawId, 10) || null` para IDs de contactos.
- [x] Atomico: `@transaction.atomic` en todos los métodos de escritura.
- [x] Zero Waste: Todas las queries usan `.only(*FIELDS)`.
- [x] Zero Waste: Prefetch `contactos_prefetched` filtrado por `is_principal=True`.
- [x] Service Layer: Cero lógica de negocio en ViewSet o Serializer.
- [x] Tabulator: `table.destroy()` antes de re-inicialización.
- [x] UIManager: `showError` usa `handleError()` (no `notifyError()` deprecado).
- [x] Error Boundary: `formatApiError()` previene `[object Object]` en errores anidados.
- [x] Delete Two-Step: UI deactivate-then-delete antes de DELETE final.
- [x] Router order: `contactos` registrado antes del prefijo vacío `''`.
- [x] REST consistency: Todos los endpoints `render-offcanvas/detalle` usan `detail=True` + URL kwarg.
- [x] Encargado: Columna visible en tabla clientes con nombre + email del contacto is_principal.
- [x] Columna Acciones contactos: Ver → Editar → Eliminar (orden no-destructivo → destructivo).
- [x] htmx:afterSettle: Abre offcanvas para clientes (`offcanvas-cliente`) y contactos (`offcanvas-contacto-cliente`).
- [x] Sub-tab Contactos: Carga lazy al primer clic vía `shown.bs.tab`.
- [x] `onsubmit="return false;"` en ambos forms (crear y editar cliente).

---

## 13. Referencias

- [api/viewsets.py](api/viewsets.py)
- [api/serializers.py](api/serializers.py)
- [api/urls.py](api/urls.py)
- [services/business_service.py](services/business_service.py)
- [services/crud_service.py](services/crud_service.py)
- [services/selectors.py](services/selectors.py)
- [models.py](models.py)
- [static/clientes/js/clientes.list.js](static/clientes/js/clientes.list.js)
- [static/clientes/js/clientes.editor.js](static/clientes/js/clientes.editor.js)
- [static/clientes/js/clientes.api.js](static/clientes/js/clientes.api.js)
- [templates/tenant/clientes/clientes_list.html](templates/tenant/clientes/clientes_list.html)
- [apps/tenant/api/utils.py](../api/utils.py)
