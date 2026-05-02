# Auditoria de Flujo Completo - Modulo Proveedores v2.61.4

Ultima actualizacion: 2026-03-30
Estado: AUDITORIA SINCRONIZADA CON IMPLEMENTACION MODULAR v3.5 (selectors/crud/business)

---
## 1. Vision General

La app apps/tenant/proveedores implementa el directorio de proveedores bajo patron API-First y aislamiento tenant estricto. El flujo vigente se compone de:

- Backend DRF: ProveedorViewSet como fachada CRUD principal.
- Service Layer (v3.5 Modular):
  - selectors.py: QuerySets optimizados (Zero Waste).
  - crud_service.py: Persistencia pura y atomica.
  - business_service.py: Orquestador y logica de negocio (SSoT).
- Serializers: separacion por listado (List) y detalle (Detail).
- Frontend: window.Sintel.Proveedores (Main, Form, API).
- Templates FSD Nucleus: list.html, assets_proveedores.html, proveedor_offcanvas.html, etc. bajo templates/proveedores/.

---
## 2. Estructura Real de la App

### 2.1 Modelos

#### Proveedor

- Hereda de SintelTenantBaseModel.
- Campos principales:
  - uuid
  - tipo_persona
  - tipo_documento
  - numero_documento (SSoT Identificacion)
  - digito_verificacion
  - razon_social
  - nombre_comercial
  - regimen_tributario
  - actividad_economica_ciiu
  - plazo_pago_dias
  - banco
  - tipo_cuenta
  - numero_cuenta
  - activo
  - codigo_contable (Mapeo NIIF Clase 2)
  - observaciones
- Unicidad de negocio: empresa + tipo_documento + numero_documento.

### 2.2 Servicios (v3.5)

Ubicacion: apps/tenant/proveedores/services/

#### ProveedorSelector (selectors.py)
- qs_list(empresa_id, search=None): Filtrado por empresa y busqueda optimizada.
- qs_detail(empresa_id, pk): Detalle con campos explicitos.

#### ProveedorCRUDService (crud_service.py)
- create, update, delete atomicos.
- Manejo de IntegrityError para unicidad de documento.

#### ProveedorBusinessService (business_service.py)
- SSoT de logica financiera: calcular_neto_gasto, calcular_componentes_retencion.
- Orquestacion CRUD: crear_proveedor, actualizar_proveedor, eliminar_proveedor (con regla de bloqueo si activo).
- registrar_proveedor_con_contactos: Compatibilidad para futuros flujos maestro-detalle.

### 2.3 Serializers

#### ProveedorListSerializer
- Optimo para Tabulator.
- Campos calculados: nit (formateado con DV), contacto_principal, estado.

#### ProveedorDetailSerializer
- Lectura/Escritura completa.
- NormalizationMixin para sanitizacion Zero Trust.
- Validacion estricta de codigo_contable (NIIF Pasivos).

### 2.4 ViewSet y URLs

#### ProveedorViewSet
- Base: BaseTenantViewSet + ProveedorServiceMixin.
- Acciones HTMX: render-offcanvas/crear, render-offcanvas/editar, render-offcanvas/detalle.
- get_offcanvas_response: Inyecta contexto NIIF y choices.

---
## 3. Frontend Real Actual (v2.61.4)

### 3.1 Templates activos (templates/proveedores/)

- list.html (Estructura de grilla)
- assets_proveedores.html (Carga modular de scripts)
- proveedor_offcanvas.html (Formulario unico modular)

### 3.2 JS activo (static/proveedores/js/)

- Namespace Global: window.Sintel.Proveedores
- Proveedores.API: Consumo de endpoints DRF.
- Proveedores.Main: Orquestacion de Tabulator y eventos de lista.
- Proveedores.Form: Gestion de Offcanvas, validaciones y persistencia HTMX/REST.

---
## 4. Flujo End-to-End

1. **Carga**: Workspace carga `list.html` + `assets_proveedores.html`.
2. **Inicializacion**: `Sintel.Proveedores.Main.init()` lanza Tabulator contra `/api/v1/proveedores/`.
3. **CRUD**: Los botones delegan a `Sintel.Proveedores.Form`.
4. **HTMX**: Se usa `render-offcanvas/` para UI reactiva.
5. **Feedback**: Exito dispara `refresh()` de la grilla.

---
## 5. Checklist de Verificacion

### Backend
- [x] models.py con SintelTenantBaseModel
- [x] selectors/crud/business service modulares
- [x] ViewSet con ServiceMixin
- [x] Validacion NIIF estricta
- [x] Unicidad DB (empresa + documento)

### Frontend
- [x] templates en nucleo de la app (v3.5)
- [x] JS en nucleo de la app (v3.5)
- [x] Namespace window.Sintel.Proveedores
- [x] Tabulator con replaceData() silencioso

---
## 11. Validacion Ejecutada

- pytest apps/tenant/proveedores/tests/
- [x] 10 tests passed (verificado 2026-03-30)
