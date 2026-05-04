# Auditoria de Flujo Completo - Modulo Proveedores v2.62.4 (Estabilizado)

Ultima actualizacion: 2026-05-04
Estado: AUDITORIA SINCRONIZADA Y ESTABILIZADA CON FSD v2.62 (Resiliencia DOM + UIManager)

---
## 1. Vision General

La app apps/tenant/proveedores implementa el directorio de proveedores bajo patron API-First y aislamiento tenant estricto. El flujo vigente se compone de:

- Backend DRF: ProveedorViewSet como fachada CRUD principal.
- Capa de Seguridad (Centralizada):
  - Uso obligatorio de resolve_tenant_empresa en apps/tenant/api/utils.py.
  - Renderizado seguro mediante render_template_safe para respuestas HTMX/JSON.
- Service Layer (v3.5 Modular):
  - selectors.py: QuerySets optimizados (Zero Waste).
  - crud_service.py: Persistencia pura y atomica.
  - business_service.py: Orquestador y logica de negocio (SSoT).
- Serializers: separacion por listado (List) y detalle (Detail).
- Frontend Sync (dom-ids-sync.md) & Resiliencia:
  - Delegacion de eventos global para evitar perdida de listeners tras swaps de HTMX.
  - Auto-curacion (Self-healing) del DOM para el contenedor de Offcanvas.
  - IDs estandarizados (mezcla controlada: containerOffcanvasProveedor, grid-proveedores, btn-nuevo-proveedor).
  - Namespace Global: window.Sintel.Proveedores (Main, Form, API).
- Templates FSD Nucleus: proveedores_list.html, assets_proveedores.html, offcanvas_crear_proveedor.html, offcanvas_editar_proveedor.html.

---
## 2. Estructura Real de la App

### 2.1 Modelos

#### Proveedor

- Hereda de SintelTenantBaseModel.
- Campos principales:
  - uuid (Lookup Field)
  - tipo_persona, tipo_documento, numero_documento (SSoT Identificacion)
  - razon_social, nombre_comercial
  - regimen_tributario, actividad_economica_ciiu
  - plazo_pago_dias, banco, tipo_cuenta, numero_cuenta
  - activo
  - observaciones
- Unicidad de negocio: empresa + tipo_documento + numero_documento.

### 2.2 Servicios (v3.5)

Ubicacion: apps/tenant/proveedores/services/

#### ProveedorSelector (selectors.py)
- qs_list(empresa_id, search=None): Filtrado por empresa y busqueda optimizada (corregido bug de alias 'nit').
- qs_detail(empresa_id, pk): Detalle con campos explicitos.

#### ProveedorCRUDService (crud_service.py)
- create, update, delete atomicos con @transaction.atomic.

#### ProveedorBusinessService (business_service.py)
- Orquestacion CRUD: crear_proveedor, actualizar_proveedor, eliminar_proveedor.
- Doble Verificacion Semantica (DSV) integrada.

### 2.4 ViewSet y URLs

#### ProveedorViewSet
- Base: BaseTenantViewSet + ProveedorServiceMixin.
- Acciones HTMX (Refactorizadas v2.62):
  - render-offcanvas/crear/
  - render-offcanvas/editar/
  - render-offcanvas/detalle/
- Inyeccion de contexto centralizada en get_offcanvas_response.

---
## 3. Frontend Real Actual (v2.62.3)

### 3.1 Templates activos (templates/proveedores/)

- proveedores_list.html (Estructura de grilla, IDs: searchProveedor, gridProveedores)
- assets_proveedores.html (Carga modular de scripts)
- offcanvas_crear_proveedor.html (Template de creación dedicado)
- offcanvas_editar_proveedor.html (Template de edición dedicado)

### 3.2 JS activo (static/proveedores/js/)

- Namespace Global: window.Sintel.Proveedores
- Proveedores.API: Consumo de endpoints DRF.
- Proveedores.Main: Orquestacion de Tabulator (TabulatorFactory) y eventos de lista.
- Proveedores.Form: Gestion de Offcanvas, validaciones y persistencia Zero Trust.

---
## 4. Flujo End-to-End (Sincronizado)

1. **Carga**: Workspace carga `proveedores_list.html`.
2. **Inicializacion**: `Sintel.Proveedores.Main.init()` se lanza via evento `tab-activated` e inicializa Tabulator.
3. **Resiliencia UI**: Eventos delegados al `document` capturan clicks en `btn-nuevo-proveedor`.
4. **Auto-Healing**: Si `#containerOffcanvasProveedor` no existe, `proveedores_form.js` lo inyecta dinamicamente en el DOM.
5. **HTMX**: Se usa `render-offcanvas/` para traer el formulario al contenedor.
6. **Persistencia & Feedback**: El formulario se procesa con DSV. El exito dispara `UIManager.showSuccess` y un `refresh()` silencioso de Tabulator.

---
## 5. Checklist de Verificacion (v2.62)

### Backend
- [x] models.py con SintelTenantBaseModel
- [x] selectors/crud/business service modulares
- [x] ViewSet con resolve_tenant_empresa (Centralizado)
- [x] Renderizado con render_template_safe (Core Helper)
- [x] Unicidad DB (empresa + documento)

### Frontend
- [x] Templates alineados con dom-ids-sync.md y delegacion global.
- [x] Auto-healing para inyeccion dinamica de contenedores.
- [x] Namespace window.Sintel.Proveedores
- [x] Tabulator con replaceData() silencioso
- [x] Offcanvas gestionado por UIManager (Backdrop Cleaning)
- [x] Feedback unificado via UIManager.showSuccess()

---
## 11. Validacion Ejecutada

- python -m py_compile apps/tenant/proveedores/api/viewsets.py
- [x] Compilación exitosa (v2.62.3)
- [x] IDs Sincronizados entre HTML y JS.
