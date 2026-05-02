# AUDITORIA DE FLUJO COMPLETO - Módulo Clientes SINTEL v3.5

**Última Actualización:** 2026-03-29
**Estado:** REFACTORIZACIÓN v3.5 COMPLETADA — Modularización de servicios, DSV en ViewSets y Aislamiento FSD de Assets.

---

## 1. Resumen Ejecutivo

El módulo de Clientes gestiona la información legal, comercial y de contacto de los clientes bajo una arquitectura **Feature-Sliced Design (FSD)** multi-tenant. Cada cliente puede tener múltiples contactos (`ContactoCliente`) que se persisten de forma atómica en la misma transacción del maestro.

**Principios aplicados:**
- **Modular Service Layer (v3.5):** Descomposición en `selectors.py` (lectura), `crud_service.py` (escritura) y `business_service.py` (lógica y orquestación).
- **Double Semantic Verification (DSV):** Validación forzada en `get_object()` para garantizar aislamiento estricto por tenant.
- **Aislamiento FSD (Assets):** Templates y Scripts JS residen localmente en la app `clientes`, eliminando dependencias del monolito `core`.
- **Dual-Auth Bridge:** Soporte para SessionAuth y JWT (vía `TabulatorFactory`).

---

## 2. Estructura de Directorios (FSD)

```
apps/tenant/clientes/
    AUDITORIA_FLUJO_CLIENTES.md         <- Este archivo (SSoT)
    models.py                           <- Herencia SintelTenantBaseModel
    api/
        viewsets.py                     <- DSV en get_object()
        serializers.py                  <- NormalizationMixin aplicado
    services/                           <- Modularización v3.5
        selectors.py                    <- Zero Waste Queries (.only)
        crud_service.py                 <- Atomic Mutations
        business_service.py             <- Business Flow Orchestration
    templates/                          <- App-local Templates (FSD)
        clientes/
        contactos/
    static/clientes/js/                 <- App-local JS (FSD)
        clientes.editor.js              <- DOM Shield implementado
        contactos/                      <- Submódulos de contactos
```

---

## 3. Modelos (Anémicos)

### 3.1. `Cliente`

Hereda de `SintelTenantBaseModel`, que inyecta automáticamente el FK `empresa` y garantiza el aislamiento por esquema sin declararlo explícitamente en el modelo.

**Campos principales:**

| Campo | Tipo | Notas |
|---|---|---|
| `tipo_persona` | CharField | `NATURAL` / `JURIDICA` |
| `tipo_documento` | CharField | NIT, CC, etc. |
| `numero_documento` | CharField | Validado sin puntos ni guiones |
| `razon_social` | CharField | Nombre legal |
| `nombre_comercial` | CharField | Opcional |
| `regimen_tributario` | CharField | `RESPONSABLE_IVA`, `NO_RESPONSABLE`, etc. |
| `email` | EmailField | Opcional |
| `telefono` | CharField | Normalizado |
| `direccion` | TextField | Opcional |
| `ciudad` | CharField | Opcional |
| `activo` | BooleanField | Default `True`; debe estar `False` para poder eliminar |
| `observaciones` | TextField | Opcional |

**Constraint de unicidad:**
```
uniq_doc_cliente_empresa  ON (empresa_id, tipo_documento, numero_documento)
```

### 3.2. `ContactoCliente`

Hereda de `SintelTenantBaseModel`. FK a `Cliente` con `CASCADE` y `related_name='contactos'`.

**Campos principales:**

| Campo | Tipo | Notas |
|---|---|---|
| `cliente` | FK(Cliente) | CASCADE, related_name='contactos' |
| `nombre_completo` | CharField | Requerido |
| `cargo` | CharField | Opcional |
| `email` | EmailField | Requerido para unicidad |
| `telefono` | CharField | Opcional |
| `activo` | BooleanField | Default `True` |
| `is_principal` | BooleanField | Primer contacto principal |

**Constraint de unicidad:**
```
uniq_contacto_cliente_email  ON (cliente_id, email)
```

**Ordering:** `[-is_principal, nombre_completo]`

---

## 4. Service Layer — `ClienteBusinessService`

**Archivo:** `apps/tenant/clientes/services/services.py`

SSoT absoluta para toda lógica de negocio. Inyectado en `ClienteViewSet` vía `ClienteServiceMixin` (herencia).

### 4.1. Constantes de campo

```python
LIST_FIELDS   = ("id", "empresa_id", "tipo_persona", "tipo_documento",
                 "numero_documento", "razon_social", "nombre_comercial",
                 "regimen_tributario", "email", "telefono", "ciudad", "activo")

DETAIL_FIELDS = LIST_FIELDS + ("direccion", "observaciones")

CONTACT_FIELDS = ("id", "empresa_id", "cliente_id", "nombre_completo",
                  "cargo", "email", "telefono", "activo", "is_principal")
```

Toda consulta usa `.only(*FIELDS)` — Zero Waste obligatorio.

### 4.2. Métodos de consulta

| Método | Firma | Descripción |
|---|---|---|
| `qs_list` | `(empresa_id, search=None)` | Lista con filtro Q sobre razón social, documento, email, nombre comercial |
| `qs_detail` | `(empresa_id, pk)` | Retorna instancia o `None` (no lanza excepción) |
| `get_contactos_queryset` | `(empresa_id, cliente_id=None)` | ContactoCliente con `select_related("cliente")` |
| `get_cliente_tenant` | `(empresa_id, cliente_id)` | Utilidad para validar pertenencia |

### 4.3. Operaciones de escritura

Todos los métodos de escritura están decorados con `@transaction.atomic`.

#### `crear_cliente(empresa, data, contactos_data=None)`

Flujo:
1. `_validate_empresa(empresa)` — lanza `ValidationError` si `empresa` es inválida.
2. `_normalize_cliente_payload(data)` — elimina `contactos`, `empresa`, `empresa_id` del dict.
3. Busca cliente existente por `(empresa_id, tipo_documento, numero_documento)`.
4. Si no existe: `Cliente.objects.create(empresa=empresa, **payload)` — captura `IntegrityError`.
5. Si existe: delega a `actualizar_cliente_con_contactos` y retorna `(cliente, False)` (idempotencia).
6. Si se pasaron `contactos_data`: segunda llamada a `actualizar_cliente_con_contactos` con `replace_existing=True`.
7. Retorna `(cliente, creado: bool)`.

#### `actualizar_cliente(cliente, data, contactos_data=None)`

Wrapper delgado sobre `actualizar_cliente_con_contactos(replace_existing=contactos_data is not None)`.

#### `actualizar_cliente_con_contactos(cliente, data, contactos_data, replace_existing=True)`

Flujo de reemplazo total (estrategia por defecto):
1. Valida que `cliente.empresa_id` exista.
2. Actualiza campos del modelo via `setattr` + `cliente.save()`.
3. Si `replace_existing=True`:
   - `existing_qs.delete()` — elimina TODOS los contactos previos.
   - Recrea cada uno con `ContactoCliente.objects.create(...)`.
4. Si `replace_existing=False`: merge por ID (upsert individual).
5. Un `contactos_data = []` (array vacío) activa el reemplazo total y borra todos los contactos.
6. Retorna el cliente refrescado con los campos de `DETAIL_FIELDS`.

#### `eliminar_cliente(pk, empresa)`

Firma refactorizada — el servicio posee la validación de tenant completa:
1. Carga cliente con `filter(pk=pk, empresa_id=empresa.id).only("id", "empresa_id", "activo", ...)`.
2. Si no encontrado: `ValidationError({"detail": "Cliente no encontrado en este tenant."})`.
3. Si `cliente.activo == True`: `ValidationError({"error": "active_record", "message": "..."})`.
4. `cliente.delete()`.

Regla de negocio: **cliente activo no se puede eliminar**. El flujo UI requiere PATCH `{activo: false}` previo.

### 4.4. Métodos de normalización internos

| Método | Comportamiento |
|---|---|
| `_normalize_cliente_payload(data)` | Elimina `contactos`, `empresa`, `empresa_id` del dict de payload |
| `_normalize_contactos_payload(contactos_data)` | Filtra contactos sin `nombre_completo` o `email`; normaliza cada campo con `str(...).strip()` |
| `_raise_integrity_error(exc)` | Mapea constraint DB (`uniq_doc_cliente_empresa`, `uniq_contacto_cliente_email`) a `ValidationError` con mensaje amigable |
| `_validate_empresa(empresa)` | Lanza `ValidationError` si `empresa` o `empresa.id` son falsy |
| `_validate_contacto_cliente(empresa_id, cliente)` | Verifica que el cliente no sea None y pertenezca al mismo tenant |

### 4.5. `ClienteServiceMixin`

```python
class ClienteServiceMixin:
    @property
    def service(self):
        return ClienteBusinessService()
```

El ViewSet hereda de este mixin para acceder a `self.service.*` sin importar la clase directamente.

---

## 5. API — ViewSets y URLs

### 5.1. Router (orden crítico)

**Archivo:** `apps/tenant/clientes/api/urls.py`

```python
router.register(r'contactos', ContactoClienteViewSet, basename='contactocliente')
router.register(r'', ClienteViewSet, basename='cliente')
```

El prefijo `contactos` debe registrarse **antes** que el prefijo vacío `''`. Si se invierte, DRF interpreta `"contactos"` como un PK numérico al hacer `GET /api/v1/clientes/contactos/`.

### 5.2. `ClienteViewSet`

Hereda de `ClienteServiceMixin, BaseTenantViewSet`.

**Endpoints REST estándar:**

| Método | URL | Acción | Descripción |
|---|---|---|---|
| GET | `/api/v1/clientes/` | `list` | Lista paginada para Tabulator (`StandardResultsSetPagination`, página 10) |
| POST | `/api/v1/clientes/` | `create` | Crear cliente (idempotente por documento) |
| GET | `/api/v1/clientes/{id}/` | `retrieve` | Detalle con contactos prefetched |
| PUT | `/api/v1/clientes/{id}/` | `update` | Actualización completa |
| PATCH | `/api/v1/clientes/{id}/` | `partial_update` | Actualización parcial (usado para deactivar antes de eliminar) |
| DELETE | `/api/v1/clientes/{id}/` | `destroy` | Eliminación física (solo si `activo=False`) |

**Endpoints HTMX (acciones extra):**

| Método | URL | Acción | Descripción |
|---|---|---|---|
| GET | `/api/v1/clientes/render-offcanvas/crear/` | `render_offcanvas_crear` | HTML del offcanvas de creación |
| GET | `/api/v1/clientes/{id}/render-offcanvas/editar/` | `render_offcanvas_editar` | HTML del offcanvas de edición |
| GET | `/api/v1/clientes/render-offcanvas/detalle/?id={id}` | `render_offcanvas_detalle` | HTML del offcanvas de detalle (read-only) |
| GET | `/api/v1/clientes/offcanvas/` | `offcanvas` | Endpoint legacy unificado (crear o editar por `?id=`) |

### 5.3. Resolución de empresa — `get_empresa()`

Cadena de fallback de 4 niveles implementada en `resolve_tenant_empresa(request, view_instance)`:

```
1. view_instance.tenant_empresa  (propiedad en mixins/custom views)
2. request.tenant.empresa        (middleware multi-tenant)
3. request.tenant_empresa        (compatibilidad)
4. Empresa.objects.first()       (singleton del esquema actual)
   -> ProgrammingError  -> None  (esquema sin migraciones tenant)
```

Cualquier endpoint que requiera empresa devuelve `HTTP 400` si el resultado es `None`.

### 5.4. `destroy` — flujo seguro

```python
def destroy(self, request, *args, **kwargs):
    empresa = self.get_empresa()
    if not empresa:
        return Response({'detail': '...'}, status=400)
    pk = self.kwargs.get(self.lookup_field)
    try:
        self.service.eliminar_cliente(pk, empresa)
        return Response(status=204)
    except serializers.ValidationError as exc:
        return Response(exc.detail, status=400)
```

No llama a `get_object()`. La validación de tenant ocurre dentro del servicio.

### 5.5. `render_offcanvas_editar` — flujo seguro

```python
def render_offcanvas_editar(self, request, pk=None):
    empresa = self.get_empresa()
    try:
        pk_int = int(pk)
    except (TypeError, ValueError):
        return Response({'error': 'invalid_pk', ...}, status=400)
    cliente = self.service.qs_detail(empresa_id=empresa.id, pk=pk_int)
    if cliente is None:
        return Response({'error': 'cliente_not_found', ...}, status=404)
    contactos = self.service.get_contactos_queryset(empresa_id=empresa.id, cliente_id=cliente.id)
    context = {'cliente': cliente, 'contactos': contactos, 'is_draft': False, 'modo': 'editar'}
    return render_template_safe(context, 'tenant/core/partials/clientes/offcanvas_editar_cliente.html', request=request)
```

No usa `get_object()` (que lanza `Http404` no capturable con `except Cliente.DoesNotExist`). La conversión a `int` previene inyección de valor no numérico en la query.

### 5.6. `get_queryset`

Utiliza `Prefetch` con `to_attr='contactos_prefetched'` para que `to_representation` en el serializer use la lista en memoria sin queries adicionales:

```python
models.Prefetch('contactos', queryset=contactos_qs, to_attr='contactos_prefetched')
```

### 5.7. `ContactoClienteViewSet`

Hereda de `ClienteServiceMixin, BaseTenantViewSet`. `lookup_field = 'id'`. Endpoints estándar de CRUD para contactos individuales (fuera del flujo Maestro-Detalle).

---

## 6. Serializers

**Archivo:** `apps/tenant/clientes/api/serializers.py`

### 6.1. `ClienteListSerializer`

Solo lectura. Campos computados con sufijo `_display` para Tabulator (ej. `tipo_persona_display`, `regimen_tributario_display`). Usado exclusivamente en `list`.

### 6.2. `ContactoClienteSerializer(NormalizationMixin, ModelSerializer)`

- `id = IntegerField(required=False, allow_null=True)` — declarado explícitamente para que DRF incluya el ID en `validated_data` (por defecto los PKs son read-only en serializers anidados).
- `validate()` omite la validación `unique_together` de `(cliente, email)` cuando `self.instance is None` — necesario para el contexto de creación anidada donde el cliente aún no está asignado.

### 6.3. `ClienteDetailSerializer(NormalizationMixin, ModelSerializer)`

- `contactos = ContactoClienteSerializer(many=True, required=False)` — permite payload Maestro-Detalle en un solo request.
- `validate()`:
  - Normaliza `numero_documento` (strip, uppercase).
  - Valida unicidad de `(empresa_id, tipo_documento, numero_documento)` excluyendo la instancia actual.
- `to_representation()`:
  - Usa `instance.contactos_prefetched` si el atributo existe (evita N+1 en list con Prefetch).
  - Recae en `instance.contactos.all()` si no hay prefetch.

### 6.4. `NormalizationMixin`

Importado desde `apps/tenant/api/utils.py`. Provee:
- `normalize_data(data)` — strip en strings.
- `normalize_phone(value)` — limpieza de números de teléfono.
- `normalize_document_number(value)` — limpieza de caracteres no alfanuméricos.

---

## 7. Frontend — Módulos JS

### 7.1. Namespace y módulos

Todos los módulos del cliente usan el namespace `window.AppCliente` (o subnombres como `window.ClienteUtils`). Ningún módulo declara variables globales fuera del namespace.

### 7.2. `clientes.list.js` — Orquestador Tabulator

**Namespace:** `window.AppCliente`
**Logger:** `log.info/warn/error('[Clientes.List] ...')`

**Estado del módulo:**

```javascript
const state = {
    clientesLoaded: false, clientesLoading: false,
    contactosLoaded: false, contactosLoading: false,
    clientesTable: null, contactosTable: null,
    clientesCount: 0, contactosCount: 0
};
```

**Tabulator — ciclo de vida (corrección aplicada):**

El error `Event Target Lookup Error` ocurría cuando `loadClientesTable()` se ejecutaba sobre un contenedor que ya tenía una instancia anterior sin destruir. Solución en el bloque de reset:

```javascript
// En el path donde el grid está vacío y se va a reemplazar:
if (state.clientesTable) {
    state.clientesTable.destroy();
    state.clientesTable = null;
}
```

Mismo patrón aplicado a `loadContactosTable`.

**Flujo de eliminación de cliente (two-step):**

`handleCellAction` pasa el objeto `rowData` completo a `deleteCliente(rowData)`:

```
deleteCliente(rowData)
  |
  +-- rowData.activo == true?
  |     -> Confirmar desactivación primero
  |     -> clientesAPI.update(id, {activo: false})  [PATCH]
  |         -> Error? -> showError(real API message)  STOP
  |     -> Confirmar eliminación
  |     -> clientesAPI.delete(id)  [DELETE]
  |
  +-- rowData.activo == false?
        -> Confirmar eliminación directa
        -> clientesAPI.delete(id)  [DELETE]

Exito -> dispatchEvent('clienteEliminado') -> table.replaceData()
```

**`showError(msg)`:**

```javascript
function showError(msg) {
    UIManager.handleError(
        { status: 500, data: { detail: msg } },
        'Clientes'
    );
}
```

`UIManager.notifyError()` está **DEPRECADO** — hardcodea `#form-inventario-feedback` como contenedor de destino, lo cual es incorrecto en el contexto del módulo de clientes.

### 7.3. `clientes.editor.js` — Formulario Maestro-Detalle

**Estrategia de payload (Zero Trust):**

No se usa `FormData`. Cada campo se extrae manualmente:

```javascript
const getText = (selector) => (form.querySelector(selector)?.value || '').trim();
const getBool = (selector) => form.querySelector(selector)?.checked ?? false;
```

DOM Shield aplicado a contactos: el ID del contacto se lee desde `data-contacto-id` en el elemento `.contacto-item`, nunca de un input con `name`. Se convierte con `parseInt(rawId, 10) || null` — `null` para contactos nuevos, entero para existentes.

**`formatApiError(val)`:**

Función recursiva que previene el bug `[object Object]` cuando DRF retorna errores anidados en contactos:

```javascript
// DRF puede retornar: {contactos: [{email: ["Este email ya existe"]}]}
// formatApiError convierte esto a string legible
function formatApiError(val) {
    if (Array.isArray(val)) {
        return val.map(item => {
            if (item && typeof item === 'object') {
                return Object.entries(item)
                    .map(pair => pair[0] + ': ' + formatApiError(pair[1]))
                    .join('; ');
            }
            return String(item);
        }).join(' | ');
    }
    // ... string y fallback
}
```

**Error boundary:**

Todos los errores de `guardarCliente()` se inyectan en `#form-cliente-feedback` dentro del offcanvas. No se usa `UIManager.notifyError()`.

**Contacto por defecto:**

Al inicializar el formulario de creación, `initFormulario()` verifica si `#contenedor-contactos` tiene `.contacto-item` hijos. Si no tiene ninguno, agrega una fila de contacto vacía por defecto.

### 7.4. `clientes.api.js` — Capa de datos

Wrapper de `fetch` expuesto como `window.clientesAPI` (o integrado en `AppCliente`). Métodos: `list`, `get`, `create`, `update`, `delete`. Todas las respuestas de error incluyen el cuerpo JSON para que el módulo que llama pueda extraer `response.data.detail` o `response.data.error`.

---

## 8. Templates HTMX

**Ruta base:** `apps/tenant/core/templates/tenant/core/partials/clientes/`

| Template | Disparado por | Contenedor destino |
|---|---|---|
| `offcanvas_crear_cliente.html` | `GET render-offcanvas/crear/` | `#offcanvas-container-cliente` |
| `offcanvas_editar_cliente.html` | `GET {id}/render-offcanvas/editar/` | `#offcanvas-container-cliente` |
| `offcanvas_detalle_cliente.html` | `GET render-offcanvas/detalle/?id=` | `#offcanvas-container-cliente` |
| `list_clientes.html` | Carga de workspace | Integrado en el layout principal |

Cada template tiene su propio contenedor de feedback: `#form-cliente-feedback`.

---

## 9. Patrones Críticos y Antipatrones Conocidos

### 9.1. Patterns obligatorios

| Patron | Ubicacion | Estado |
|---|---|---|
| `table.destroy()` antes de re-inicializar Tabulator | `clientes.list.js:loadClientesTable/loadContactosTable` | APLICADO |
| `UIManager.handleError()` para notificaciones globales | `clientes.list.js:showError` | APLICADO |
| `formatApiError()` recursivo para errores anidados | `clientes.editor.js` | APLICADO |
| `parseInt(rawId, 10) || null` para IDs de contacto | `clientes.editor.js:recolectarDatosFormulario` | APLICADO |
| `service.qs_detail()` en lugar de `get_object()` en HTMX | `viewsets.py:render_offcanvas_editar` | APLICADO |
| `eliminar_cliente(pk, empresa)` con validacion tenant en servicio | `services.py` + `viewsets.py:destroy` | APLICADO |
| `@transaction.atomic` en todos los métodos de escritura del servicio | `services.py` | APLICADO |

### 9.2. Antipatrones resueltos

| Antipatrón | Consecuencia | Resolución |
|---|---|---|
| `notifyError()` en `clientes.list.js` | Inyectaba error en `#form-inventario-feedback` (contenedor de otro módulo) | Reemplazado por `UIManager.handleError()` |
| `except Cliente.DoesNotExist` tras `get_object()` | Dead code — `get_object()` lanza `Http404`, no `DoesNotExist` → 500 silencioso | Reemplazado por `service.qs_detail()` que retorna `None` |
| `deleteCliente(rowData.id)` | Sin acceso a `activo` → backend retorna 400 "cant delete active" → capturado como error genérico | Reemplazado por `deleteCliente(rowData)` pasando objeto completo |
| `FormData` en payload de contactos | DOM Shield roto — `<select>` visibles con `name` sobrescriben `<input type="hidden">` | Eliminado; extraccion manual campo por campo |
| Tabulator sin `destroy()` antes de reemplazar | `Event Target Lookup Error` en la segunda inicialización | Añadido guard `state.clientesTable.destroy()` |

---

## 10. Flujos Completos

### 10.1. Crear Cliente con Contactos

```
[Usuario] Click "Nuevo Cliente"
    |
    v
[HTMX] GET /api/v1/clientes/render-offcanvas/crear/
    -> render_offcanvas_crear()
    -> render_template_safe(context, 'offcanvas_crear_cliente.html')
    -> HTML inyectado en #offcanvas-container-cliente
    |
    v
[JS] initFormulario()
    -> Si 0 contactos en #contenedor-contactos: agregar fila por defecto
    |
    v
[Usuario] Completa formulario -> Click "Guardar"
    |
    v
[JS] recolectarDatosFormulario()
    -> getText() / getBool() campo por campo
    -> Contactos: querySelectorAll('.contacto-item') -> payload explícito
    -> parseInt(rawId, 10) || null para IDs
    -> data.contactos = contactos (siempre presente)
    |
    v
[JS] clientesAPI.create(data)  [POST /api/v1/clientes/]
    |
    v
[Backend] ClienteViewSet.create()
    -> get_empresa()
    -> ClienteDetailSerializer.validate()  [NormalizationMixin]
    -> service.crear_cliente(empresa, validated_data, contactos_data)
        -> _validate_empresa()
        -> filter por (empresa_id, tipo_doc, num_doc) -> upsert
        -> Cliente.objects.create()  [IntegrityError -> ValidationError]
        -> actualizar_cliente_con_contactos(..., replace_existing=True)
            -> existing_qs.delete()
            -> ContactoCliente.objects.create() * N
    -> return (cliente, creado)
    -> Serializar respuesta con ClienteDetailSerializer
    -> HTTP 201 (creado) o HTTP 200 (upsert)
    |
    v
[JS] Éxito -> dispatchEvent('clienteCreado') -> table.replaceData()
[JS] Error -> formatApiError(response.data) -> inyectar en #form-cliente-feedback
```

### 10.2. Eliminar Cliente Activo (Two-Step)

```
[Usuario] Click "Eliminar" en fila activa de Tabulator
    |
    v
[JS] handleCellAction(e, cell, 'clientes')
    -> rowData = cell.getRow().getData()   [objeto completo]
    -> action == 'delete'
    -> deleteCliente(rowData)              [NO solo rowData.id]
    |
    v
[JS] deleteCliente(rowData)
    -> rowData.activo == true?
        -> confirm("Desactivar antes de eliminar?")
        -> clientesAPI.update(rowData.id, {activo: false})  [PATCH]
            -> Error? -> showError(response.data.detail)  STOP
        -> confirm("Eliminar definitivamente?")
    -> clientesAPI.delete(rowData.id)  [DELETE]
    |
    v
[Backend] ClienteViewSet.destroy()
    -> get_empresa()  -> None? -> HTTP 400
    -> pk = self.kwargs['pk']
    -> service.eliminar_cliente(pk, empresa)
        -> filter(pk=pk, empresa_id=empresa.id) -> .first()
        -> None? -> ValidationError detail
        -> activo? -> ValidationError error:'active_record'
        -> cliente.delete()
    -> HTTP 204
    |
    v
[JS] Éxito -> dispatchEvent('clienteEliminado') -> table.replaceData()
```

### 10.3. Editar Cliente

```
[Usuario] Click "Editar" en fila Tabulator
    |
    v
[JS] handleCellAction -> editCliente(rowData.id)
    |
    v
[HTMX] GET /api/v1/clientes/{id}/render-offcanvas/editar/
    -> render_offcanvas_editar(request, pk=id)
    -> int(pk) -> ValueError -> HTTP 400
    -> service.qs_detail(empresa.id, pk_int) -> None -> HTTP 404
    -> service.get_contactos_queryset(empresa.id, cliente.id)
    -> render_template_safe(context, 'offcanvas_editar_cliente.html')
    -> HTML inyectado en #offcanvas-container-cliente
    |
    v
[JS] initFormulario()
    -> Autollenar campos con datos del cliente desde HTML
    -> Renderizar filas de contactos existentes
    |
    v
[Usuario] Modifica datos -> Click "Guardar"
    |
    v
[JS] recolectarDatosFormulario() -> clientesAPI.update(id, data)  [PATCH]
    |
    v
[Backend] ClienteViewSet.partial_update()
    -> ClienteDetailSerializer(cliente, data, partial=True)
    -> validated_data.pop('contactos', None)
    -> service.actualizar_cliente(cliente, validated_data, contactos_data)
        -> actualizar_cliente_con_contactos(replace_existing=True)
    -> Respuesta con ClienteDetailSerializer
    -> HTTP 200
    |
    v
[JS] Éxito -> dispatchEvent('clienteActualizado') -> table.replaceData()
```

---

## 11. Utilidades Compartidas

| Utilidad | Archivo | Descripción |
|---|---|---|
| `render_template_safe()` | `apps/tenant/api/utils.py` | Wrapper de `TemplateHTMLRenderer` — captura `TemplateDoesNotExist` y `OSError` → devuelve JSON 500 en vez de traceback |
| `BaseTenantViewSet` | `apps/tenant/api/base.py` | ViewSet base con middleware multi-tenant integrado |
| `NormalizationMixin` | `apps/tenant/api/utils.py` | Normalización Zero Trust de datos de entrada en serializers |
| `UIManager.handleError()` | `apps/tenant/core/static/core/js/lib/ui-manager.js` | Boundary de errores activo. `notifyError()` DEPRECADO |
| `TabulatorFactory` | `apps/tenant/core/static/core/js/common/tabulator.factory.js` | Factory global para todas las instancias Tabulator |
| `SintelTenantBaseModel` | `apps/tenant/shared/models.py` (aprox.) | Base model que inyecta FK `empresa` para aislamiento multi-tenant |

---

## 12. Checklist de Verificación (v2.61.5)

- [x] Zero Trust: `destroy` no llama a `get_object()`; tenant validado en servicio.
- [x] Zero Trust: `render_offcanvas_editar` valida `pk` con `int()` y usa `qs_detail()`.
- [x] Zero Trust: Payload de formulario se construye campo por campo (no `FormData`).
- [x] Zero Trust: `parseInt(rawId, 10) || null` para IDs de contactos.
- [x] Atomico: `@transaction.atomic` en `crear_cliente`, `actualizar_cliente_con_contactos`, `eliminar_cliente`.
- [x] Zero Waste: Todas las queries usan `.only(*FIELDS)`.
- [x] Service Layer: Cero lógica de negocio en ViewSet o Serializer.
- [x] Tabulator: `table.destroy()` antes de re-inicialización en `loadClientesTable/loadContactosTable`.
- [x] UIManager: `showError` usa `handleError()` (no `notifyError()` deprecado).
- [x] Error Boundary: `formatApiError()` previene `[object Object]` en errores anidados.
- [x] Delete Two-Step: UI deactivate-then-delete antes de DELETE final.
- [x] Router order: `contactos` router registrado antes del prefijo vacío.
- [x] `manage.py check` -> 0 issues.

---

## 13. Referencias

- [apps/tenant/clientes/api/viewsets.py](../api/viewsets.py)
- [apps/tenant/clientes/api/serializers.py](../api/serializers.py)
- [apps/tenant/clientes/api/urls.py](../api/urls.py)
- [apps/tenant/clientes/services/services.py](../services/services.py)
- [apps/tenant/clientes/models.py](../models.py)
- [apps/tenant/core/static/core/js/clientes/clientes.list.js](../../core/static/core/js/clientes/clientes.list.js)
- [apps/tenant/core/static/core/js/clientes/clientes.editor.js](../../core/static/core/js/clientes/clientes.editor.js)
- [apps/tenant/api/utils.py](../../api/utils.py)
- [apps/tenant/core/static/core/js/lib/ui-manager.js](../../core/static/core/js/lib/ui-manager.js)
