# Auditoría de Flujo Completo - Modelo ContactoCliente v2.61.4

**Patrón:** Feature-Sliced Design (FSD)  
**Época:** v2.61.4 (Modularización Frontend + Backend)  
**Última actualización:** Marzo 23, 2026  

---

## I. Arquitectura General

### Ecosistema Separado para ContactoCliente

El modelo `ContactoCliente` (ForeignKey → Cliente) tiene su propia estructura modular **completamente independiente** de Clientes:

```
apps/tenant/clientes/
  models.py (ContactoCliente)
  api/
    viewsets.py (ContactoClienteViewSet)
    serializers.py (ContactoClienteSerializer)
  services/
    services.py (ClienteBusinessService.crear_contacto, actualizar_contacto)

apps/tenant/core/templates/tenant/core/partials/contactos/  [FSD: Aislado]
  offcanvas_crear_contacto_cliente.html
  offcanvas_editar_contacto_cliente.html
  offcanvas_detalle_contacto_cliente.html
  list_contacto_cliente.html

apps/tenant/core/static/core/js/contactos/  [FSD: Aislado]
  contacto_cliente_api.js (Wrapper API)
  contacto_cliente_form.js (Manejo de formularios)
  contacto_cliente_utils.js (Funciones auxiliares)
  contacto_cliente_main.js (Orquestador)
```

---

## II. Flujo de Creación de Contacto

### 1. **UI → Disparador**

Usuario hace clic en botón "Nuevo Contacto":
- Ubicación: `list_contacto_cliente.html` → `#btn-crear-contacto`
- Acción JavaScript: `ContactoClienteModule.abrirCrear(clienteId)`

### 2. **Frontend → Solicitar Template (HTMX)**

```javascript
// contacto_cliente_main.js → abrirCrearContacto()
GET /api/v1/clientes/contactos/render-offcanvas/crear/
  ?cliente_id={id}  [Opcional]

Response: HTML template (offcanvas_crear_contacto_cliente.html)
```

### 3. **Inyectar Offcanvas en DOM**

```javascript
// Crear div temporal, inyectar HTML, mostrar offcanvas Bootstrap
const div = document.createElement('div');
div.innerHTML = response.data;
container.appendChild(div);
new bootstrap.Offcanvas(offcanvasEl).show();
```

### 4. **Usuario Completa Formulario**

Template: `offcanvas_crear_contacto_cliente.html`
- Campo: `nombre_completo` (required)
- Campo: `email` (required)
- Campo: `cargo` (opcional)
- Campo: `telefono` (opcional)
- Checkbox: `activo` (default = true)
- Checkbox: `is_principal`
- Hidden: `cliente` (id del cliente)

### 5. **Usuario Presiona "Guardar"**

Botón: `#btn-guardar-contacto-cliente` → evento `click`

```javascript
// contacto_cliente_form.js → guardarContacto()
1. Recolectar datos del formulario (#form-contacto-cliente)
2. Normalizar checkboxes (activo, is_principal)
3. Convertir cliente a entero
4. Construir payload JSON
```

### 6. **Frontend → API POST**

```javascript
const payload = {
  nombre_completo: "Juan Pérez",
  email: "juan@example.com",
  cargo: "Gerente",
  telefono: "300123456",
  cliente: 1,
  activo: true,
  is_principal: false
};

POST /api/v1/clientes/contactos/
Content-Type: application/json
Body: payload
```

### 7. **Backend Valida**

```
ViewSet: ContactoClienteViewSet.create()
  ↓
Serializer: ContactoClienteSerializer.validate()
  - Normaliza email: strip + lowercase
  - Valida unique_together: cliente + email
  ↓
Service: ClienteBusinessService.crear_contacto()
  - Normaliza contacto payload
  - Valida cliente pertenece a empresa
  - Creates ContactoCliente instance
  ↓
Response: 201 Created + datos del contacto creado
```

### 8. **Frontend Maneja Éxito**

```javascript
if (response.ok) {
  UIManager.success('Contacto creado exitosamente');
  
  // Cerrar offcanvas
  bootstrap.Offcanvas.getInstance(offcanvasEl).hide();
  
  // Disparar evento para recargar tabla
  document.dispatchEvent(new CustomEvent('contactoGuardado'));
}
```

### 9. **Tabla se Recarga Automáticamente**

```javascript
// Event listener en contacto_cliente_main.js
document.addEventListener('contactoGuardado', () => table.replaceData());
```

---

## III. Flujo de Edición de Contacto

### 1. **UI → Disparador**

Usuario hace clic en botón "Editar" en fila de tabla:
- Evento: `click` en `.btn-editar-contacto` (data-contacto-id={id})
- Acción: `ContactoClienteModule.abrirEditar(contactoId)`

### 2. **Frontend → Solicitar Template (HTMX)**

```javascript
GET /api/v1/clientes/contactos/{id}/render-offcanvas/editar/

Response: HTML template (offcanvas_editar_contacto_cliente.html)
```

### 3. **Inyectar + Mostrar Offcanvas**

Mismo procedimiento que creación.

### 4. **Usuario Modifica Campos**

Template: `offcanvas_editar_contacto_cliente.html`
- Los campos están pre-rellenados con valores actuales
- Cliente se muestra como read-only (no se puede cambiar)
- Hidden: `id` (id del contacto a actualizar)
- Hidden: `cliente` (id del cliente, read-only)

### 5. **Usuario Presiona "Actualizar"**

Mismo flujo de recolección y normalización.

### 6. **Frontend → API PATCH**

```javascript
const contactoId = document.querySelector('#contacto-id').value;
const payload = { /* datos modificados */ };

PATCH /api/v1/clientes/contactos/{contactoId}/
Content-Type: application/json
Body: payload
```

### 7. **Backend Valida y Actualiza**

```
ViewSet: ContactoClienteViewSet.partial_update()
  ↓
Serializer: ContactoClienteSerializer.validate()
  ↓
Service: ClienteBusinessService.actualizar_contacto()
  - Normaliza payload
  - Actualiza ContactoCliente instance
  ↓
Response: 200 OK + datos actualizados
```

### 8. **Tabla se Recarga**

Mismo evento `contactoActualizado`.

---

## IV. Flujo de Eliminación de Contacto

### 1. **UI → Disparador**

Usuario hace clic en botón "Eliminar":
- Evento: `click` en `.btn-eliminar-contacto` (data-contacto-id={id})
- Acción: `ContactoClienteUtils.eliminar(contactoId, nombreContacto)`

### 2. **Confirmación Modal**

```javascript
if (!confirm(`¿Eliminar contacto "${nombreContacto}"?`)) return;
```

### 3. **Frontend → API DELETE**

```javascript
DELETE /api/v1/clientes/contactos/{id}/
```

### 4. **Backend Elimina**

```
ViewSet: ContactoClienteViewSet.destroy()
  ↓
Service: ClienteBusinessService.eliminar_cliente() [Oops! Usando servicio de Cliente]
  - Verifica no está activo (si aplica)
  ↓
Response: 204 No Content
```

### 5. **Tabla se Recarga**

Evento `contactoEliminado`.

---

## V. Componentes Clave

### A. **Templates HTML** (Feature-Sliced)

| Archivo | Propósito | Modo |
|---------|-----------|------|
| `offcanvas_crear_contacto_cliente.html` | Offcanvas para crear contacto | Creación |
| `offcanvas_editar_contacto_cliente.html` | Offcanvas para editar contacto | Edición |
| `offcanvas_detalle_contacto_cliente.html` | Offcanvas para ver detalle | Lectura |
| `list_contacto_cliente.html` | Tabla con Tabulator | Listado |

**Principio:** Cada template es **independiente y reutilizable** sin referencias cruzadas.

### B. **Scripts JavaScript** (Feature-Sliced)

| Archivo | Responsabilidad |
|---------|-----------------|
| `contacto_cliente_api.js` | Wrapper de API (GET, POST, PATCH, DELETE, render-offcanvas) |
| `contacto_cliente_form.js` | Recolección de datos, validación UI, guardado |
| `contacto_cliente_utils.js` | Acciones auxiliares (marcar principal, inactivar, etc.) |
| `contacto_cliente_main.js` | Orquestador: Tabulator, event delegation, HTMX |

**Namespace:** `window.AppContactoCliente` (evita colisiones globales)

### C. **ViewSet** (API Backend)

```python
class ContactoClienteViewSet(ClienteServiceMixin, BaseTenantViewSet):
    def list() → pagina de contactos
    def create() → POST /api/v1/clientes/contactos/
    def partial_update() → PATCH /api/v1/clientes/contactos/{id}/
    def destroy() → DELETE (no implementado explícitamente)
    
    # Nuevos endpoints HTMX (v2.61.4)
    @action render_offcanvas_crear()     → GET .../render-offcanvas/crear/
    @action render_offcanvas_editar()    → GET .../{id}/render-offcanvas/editar/
    @action render_offcanvas_detalle()   → GET .../render-offcanvas/detalle/?id={id}
```

### D. **Serializer**

```python
class ContactoClienteSerializer(NormalizationMixin, serializers.ModelSerializer):
    def validate() → normaliza email, nombre, valida unique_together
```

### E. **Service Layer**

```python
class ClienteBusinessService:
    def crear_contacto(empresa_id, data) → ContactoCliente
    def actualizar_contacto(contacto, data) → ContactoCliente
```

---

## VI. Validación y Manejo de Errores

### Frontend

1. **Recolección:** `contacto_cliente_form.js` valida campos requeridos
2. **Normalización:** Convierte tipos (checkbox → bool, cliente → int)
3. **Submisión:** Envia payload JSON a API
4. **Respuesta 400:** Extrae errores por campo, renderiza en contenedor `#form-contacto-cliente-feedback`
5. **Respuesta 200/201:** Dispara evento de recargar tabla

### Backend

1. **Serializer:** Valida email único (per cliente), normaliza
2. **Service:** Valida pertenencia a empresa
3. **Database:** Constraint `uniq_contacto_cliente_email` previene duplicados físicos

---

## VII. Integración con Clientes

**Flujo anidado:** Durante creación/edición de Cliente, los contactos se pasan como array anidado:

```javascript
POST /api/v1/clientes/
{
  "nombre_comercial": "Acme Inc",
  "numero_documento": "900123456",
  "contactos": [
    {
      "nombre_completo": "Juan",
      "email": "juan@acme.com",
      "cargo": "Gerente"
    }
  ]
}
```

Service maneja sincronización: crea/actualiza/elimina contactos según payload.

---

## VIII. Checklist de Alineación FSD

- [x] Templates en `partials/contactos/` (separado de clientes)
- [x] JS en `js/contactos/` (separado de clientes)
- [x] Namespace único: `window.AppContactoCliente`
- [x] API wrapper: `contacto_cliente_api.js`
- [x] Form handler: `contacto_cliente_form.js`
- [x] Utils: `contacto_cliente_utils.js`
- [x] Main orchestrator: `contacto_cliente_main.js`
- [x] Endpoints HTMX: render-offcanvas/crear, editar, detalle
- [x] Tabulator integration para listado
- [x] Event-driven: evento custom para recargar tabla
- [x] Zero Trust: validación en serializer + service
- [x] DOM Shield: cliente_id en hidden input

---

## IX. Rutas Clave (URLs)

```
GET    /api/v1/clientes/contactos/                              → List (paginated)
POST   /api/v1/clientes/contactos/                              → Create
GET    /api/v1/clientes/contactos/{id}/                         → Retrieve
PATCH  /api/v1/clientes/contactos/{id}/                         → Partial Update
DELETE /api/v1/clientes/contactos/{id}/                         → Destroy

GET    /api/v1/clientes/contactos/render-offcanvas/crear/       → Render create form
GET    /api/v1/clientes/contactos/{id}/render-offcanvas/editar/ → Render edit form
GET    /api/v1/clientes/contactos/render-offcanvas/detalle/     → Render detail view
```

---

## X. Próximos Pasos

1. Incluir `contacto_cliente_*.js` scripts en página principal
2. Incluir `list_contacto_cliente.html` en dashboard o workspace
3. Crear contenedor div `#offcanvas-container-contacto` en layout raíz
4. Pruebas E2E: crear, editar, eliminar contactos
5. Documentación de usuario para UI ContactoCliente

---

**Estado:** Modularización FSD completada v2.61.4  
**Responsabilidad:** Equipo de Desarrollo SINTEL

