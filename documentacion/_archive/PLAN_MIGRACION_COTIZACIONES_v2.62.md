# Plan de Accion: Migracion Arquitectonica App Cotizaciones
**Version:** 1.0
**Fecha:** 2026-05-05
**Estado:** PENDIENTE DE APROBACION
**Alcance:** `apps/tenant/cotizaciones/`
**Autorizacion Requerida:** Usuario Principal (este documento es el RFC formal)

---

## Base de Conocimiento Consultada

- `AGENTS.md` (raiz del proyecto) — Reglas SINTEL v2.62.0 (inmutables)
- `.antigravity/rules/core.md` — Mirror de AGENTS.md para agentes IA
- `.antigravity/rules/behavior.md` — Flujo operativo y checklist
- `.antigravity/rules/permissions.md` — Comandos autorizados
- `.agents/skills/backend/service-layer.md` — Patron Service Layer
- `.agents/skills/backend/drf-viewset.md` — Patron ViewSet DRF
- `.agents/skills/backend/drf-serializers.md` — Patron Serializers
- `.agents/skills/frontend/crud-fsd.md` — Patron FSD Frontend
- `.agents/skills/frontend/vanilla-js.md` — Patron JS modular
- `.agents/skills/frontend/htmx.md` — Patron HTMX
- `.agents/skills/frontend/tabulator.md` — Patron Tabulator
- `apps/tenant/cotizaciones/AUDITORIA_FLUJO_COMPLETO.md` — Estado actual
- PDF adjunto: `COT-0000-Plantilla Maestra.pdf` — Plantilla de referencia visual

---

## Seccion 1: Analisis del PDF de Referencia

El PDF `COT-0000-Plantilla Maestra.pdf` define el esquema visual y los datos esperados
en la salida del sistema. Se identifican dos vistas del mismo documento:

### 1.1. Vista Publica (entregada al cliente)

**Pagina 1 — Carta de Presentacion:**
- Membrete: logo empresa, ciudad, fecha, numero cotizacion (formato `STS. NNNN-YY`)
- Destinatario: nombre cliente, contacto, sede/ciudad
- Asunto: descripcion del proyecto
- Cuerpo: texto de presentacion comercial
- Pie: datos empresa (direccion, telefono, web)

**Paginas 2-3 — Propuesta Economica:**

| Cabecera        | Campo modelo              |
|-----------------|--------------------------|
| Cotizacion No.  | `Cotizacion.codigo_unico`  |
| Cliente         | `Cliente.razon_social`     |
| Direccion       | `Cliente.sede` (opcional)  |
| Servicio        | `Cotizacion.tipo_cotizacion` |
| Fecha           | `Cotizacion.fecha_emision` |
| Dirigida a      | `Cliente.contacto`         |
| F/C             | `Cotizacion.fecha_vencimiento` |

Tabla de items agrupada por tipo:

| Seccion | tipo_item en modelo        |
|---------|---------------------------|
| 1.0 Dispositivos         | `PRODUCTO`    |
| 2.0 Infraestructura      | `MATERIAL`    |
| 3.0 Servicios/Instalacion| `SERVICIO`    |

Columnas por item (publicas):
`ITEM` | `DESCRIPCION` | `MARCA` | `REFERENCIA` | `CANT.` | `UND.` | `VALOR UNIT` | `VALOR TOTAL`

Totales:
- `SUBTOTAL $` por seccion
- `SUBTOTAL (antes de IVA)` — suma de subtotales
- `IVA 19%` — `Cotizacion.iva_porcentaje`
- `TOTAL VALOR $ mc` — `Cotizacion.total_con_impuestos`

### 1.2. Vista Interna (no entregada al cliente — analysis privado)

Columnas adicionales visibles solo en version interna:
- `NUEVO COSTO - VALOR TOTAL / USD` — `CotizacionItem.costo_unitario` en USD (requiere TRM)
- `UTILIDAD SOBRE VENTA $ m/C` — calculo derivado de `porcentaje_utilidad`
- `TRM` — tasa de cambio referencial (campo nuevo si se implementa)
- `Margen %` — `CotizacionItem.porcentaje_utilidad`
- `UTILI VENTA` — `precio_unitario_venta - costo_unitario` * cantidad

### 1.3. Reglas de Generacion PDF (SSoT de presentacion)

1. El agrupamiento de items se hace por `tipo_item` en orden: PRODUCTO, MATERIAL, SERVICIO
2. La numeracion de items es secuencial dentro de cada seccion (1.1, 1.2, ..., 2.1, 2.2, ...)
3. El PDF publico omite columnas de costo/margen/USD
4. El PDF interno incluye todas las columnas (uso gerencial)
5. El template HTML usa tablas para compatibilidad con `xhtml2pdf`

---

## Seccion 2: Inventario de Modelos y Gaps Actuales

### 2.1. Modelos en `models.py`

| Modelo               | Service Layer actual | CRUD API | UI/CBV | Frontend FSD |
|----------------------|---------------------|----------|--------|--------------|
| `Cotizacion`         | Parcial (monolitico)| Si       | Si     | Parcial      |
| `CotizacionItem`     | Parcial             | Si       | No     | No           |
| `Producto`           | No existe           | No       | No     | No           |
| `Servicio`           | No existe           | No       | No     | No           |
| `ConfiguracionCotizacion` | No existe    | Si (simple)| Si  | Parcial      |

### 2.2. Gaps Criticos Identificados

**Backend:**
- `business_service.py` es monolitico: mezcla logica de Cotizacion, Item, calculo de totales
- `crud_service.py` mezcla logica de Cotizacion y Item en un solo archivo
- `selectors.py` mezcla selectores de Cotizacion y CotizacionItem
- No existen servicios para `Producto` ni `Servicio`
- `pdf_service.py` referenciado en viewsets pero no existe en disco (archivo eliminado)
- `utils/pdf_generator.py` referenciado pero no existe en disco
- `services/services.py` (fachada legacy) importa `CotizacionServiceLegacy` — alias redundante
- `CotizacionItem.save()` tiene logica de negocio (calculo precios) en el modelo
- `CotizacionItemViewSet` no hereda `CotizacionItemServiceMixin`

**Frontend:**
- `cotizaciones.module.js`, `cotizaciones.list.js`, `cotizaciones.editor.js`, `cotizaciones.detalle.js`
  son archivos de nivel raiz que coexisten con `features/cotizacion_list.js` — duplicidad
- No existen archivos JS ni templates para `Producto`, `Servicio` (modelos sin UI)
- `cotizaciones.ui.js` mezcla logica de Cotizacion + Item + Configuracion

**Templates:**
- Ruta `templates/cotizaciones/` (sin prefijo `tenant/`) — parcialmente corregido en `ui_views.py`
  pero los templates fisicos aun no se han movido al directorio correcto `templates/tenant/cotizaciones/`

---

## Seccion 3: Estructura Objetivo (Arbol de Archivos)

```
apps/tenant/cotizaciones/
|-- __init__.py
|-- admin.py
|-- apps.py
|-- models.py                          [SIN CAMBIOS en estructura - solo limpiar save()]
|-- permissions.py
|-- ui_views.py                        [REFACTORIZAR: CBVs por modelo, consumir servicios]
|
|-- api/
|   |-- __init__.py
|   |-- urls.py                        [EXTENDER: agregar rutas Producto, Servicio]
|   |-- serializers.py                 [REFACTORIZAR: separar por modelo]
|   |-- viewsets.py                    [REFACTORIZAR: separar por modelo]
|   |-- pdf_viewsets.py                [REFACTORIZAR: consumir services/pdf_export_service.py]
|   |-- pagination.py
|
|-- services/
|   |-- __init__.py                    [ACTUALIZAR: exportar nuevas clases]
|   |-- selectors.py                   [REFACTORIZAR: dividir por modelo]
|   |-- crud_service.py                [REFACTORIZAR: dividir por modelo]
|   |-- business_service.py            [REFACTORIZAR: solo logica Cotizacion cabecera]
|   |-- api_mixins.py                  [EXTENDER: agregar mixins Producto, Servicio]
|   |-- services.py                    [ELIMINAR: fachada legacy innecesaria]
|   |-- producto_service.py            [NUEVO - AUTORIZADO]
|   |-- servicio_service.py            [NUEVO - AUTORIZADO]
|   |-- item_service.py                [NUEVO - AUTORIZADO]
|   |-- configuracion_service.py       [NUEVO - AUTORIZADO]
|   |-- pdf_export_service.py          [NUEVO - AUTORIZADO: reemplaza pdf_service.py eliminado]
|
|-- configuracion/
|   |-- __init__.py
|   |-- models.py
|   |-- serializers.py
|   |-- viewsets.py                    [REFACTORIZAR: consumir configuracion_service.py]
|   |-- services/                      [NUEVO - AUTORIZADO: sub-service layer para configuracion]
|       |-- __init__.py
|       |-- selectors.py
|       |-- crud_service.py
|       |-- business_service.py
|       |-- api_mixins.py
|
|-- templates/
|   |-- tenant/
|       |-- cotizaciones/              [MOVER desde templates/cotizaciones/]
|           |-- list.html
|           |-- list_producto.html     [NUEVO]
|           |-- list_servicio.html     [NUEVO]
|           |-- offcanvas_crear_cotizacion.html
|           |-- offcanvas_editar_cotizacion.html
|           |-- offcanvas_detalle_cotizacion.html
|           |-- offcanvas_crear_producto.html    [NUEVO]
|           |-- offcanvas_editar_producto.html   [NUEVO]
|           |-- offcanvas_detalle_producto.html  [NUEVO]
|           |-- offcanvas_crear_servicio.html    [NUEVO]
|           |-- offcanvas_editar_servicio.html   [NUEVO]
|           |-- offcanvas_detalle_servicio.html  [NUEVO]
|           |-- offcanvas_crear_item.html        [NUEVO]
|           |-- offcanvas_editar_item.html       [NUEVO]
|           |-- offcanvas_list_plantillas.html
|           |-- offcanvas_plantilla_crear.html
|           |-- offcanvas_plantilla_editar.html
|           |-- offcanvas_plantilla_detalle.html
|           |-- assets_cotizaciones.html
|           |-- pdf/
|               |-- formato_profesional.html     [REFACTORIZAR: vista publica]
|               |-- formato_interno.html         [NUEVO: vista con columnas internas]
|
|-- static/
    |-- cotizaciones/
        |-- js/
        |   |-- cotizaciones.main.js   [LIMPIAR: eliminar referencias a modulos legacy]
        |   |-- cotizaciones.api.js    [EXTENDER: endpoints Producto, Servicio]
        |   |-- cotizaciones.table.js  [MANTENER]
        |   |-- cotizaciones.ui.js     [REFACTORIZAR: solo Cotizacion cabecera]
        |   |-- cotizaciones.utils.js  [MANTENER]
        |   |-- features/
        |       |-- cotizacion_list.js     [CANÓNICO: mantener y limpiar]
        |       |-- cotizacion_editor.js   [NUEVO: consolidar logica editor]
        |       |-- producto_list.js       [NUEVO]
        |       |-- producto_editor.js     [NUEVO]
        |       |-- servicio_list.js       [NUEVO]
        |       |-- servicio_editor.js     [NUEVO]
        |       |-- item_editor.js         [NUEVO: formulario items en cotizacion]
        |-- css/
            |-- cotizaciones.css       [SIN CAMBIOS]
```

---

## Seccion 4: Plan de Accion Paso a Paso

### FASE 0 — Preparacion y Congelamiento (Prerequisito)

**Paso 0.1 — Backup y rama git**
- Crear rama: `feat/cotizaciones-arch-migration`
- Confirmar que los tests actuales pasan: `python manage.py test apps.tenant.cotizaciones`
- Registrar estado actual en `AUDITORIA_FLUJO_COMPLETO.md`

**Paso 0.2 — Identificar templates fisicos a mover**
- Verificar que `templates/cotizaciones/` contiene los 12 templates existentes
- Confirmar que `templates/tenant/cotizaciones/` NO existe aun (crear estructura vacia)

---

### FASE 1 — Limpieza de Modelo (`models.py`)

**Paso 1.1 — Extraer logica de `CotizacionItem.save()`**
- Eliminar el override de `save()` en `CotizacionItem` que calcula
  `precio_unitario_venta` y `subtotal_linea`
- Mover el calculo a `item_service.py` (ver Paso 4.3)
- Resultado: `CotizacionItem` es un modelo puro de datos sin logica de negocio
- Validar con: `python -m py_compile apps/tenant/cotizaciones/models.py`

**Paso 1.2 — Verificar herencia de `ConfiguracionCotizacion`**
- Confirmar que `ConfiguracionCotizacion` en `configuracion/models.py` no redeclara
  el campo `empresa` si `SintelTenantBaseModel` ya lo provee
- Eliminar la FK `empresa` redundante si existe en la subclase

---

### FASE 2 — Migracion de Templates (C-1 del plan de auditoria)

**Paso 2.1 — Crear estructura de directorio objetivo**
```
apps/tenant/cotizaciones/templates/tenant/cotizaciones/
apps/tenant/cotizaciones/templates/tenant/cotizaciones/pdf/
```

**Paso 2.2 — Mover templates existentes**
Mover los 12 archivos de `templates/cotizaciones/` a `templates/tenant/cotizaciones/`
Archivos a mover:
- `list.html`, `list_full.html`, `list_cotizaciones.html`
- `offcanvas_crear_cotizacion.html`, `offcanvas_editar_cotizacion.html`
- `offcanvas_detalle_cotizacion.html`
- `offcanvas_list_plantillas.html`, `offcanvas_plantilla_crear.html`
- `offcanvas_plantilla_editar.html`, `offcanvas_plantilla_detalle.html`
- `assets_cotizaciones.html`
- `pdf/formato_profesional.html`

**Paso 2.3 — Actualizar referencias `template_name` en ViewSets**
En `api/viewsets.py`, actualizar todas las cadenas de `template_name`:
```python
# ANTES
template_name='cotizaciones/offcanvas_crear_cotizacion.html'
# DESPUES
template_name='tenant/cotizaciones/offcanvas_crear_cotizacion.html'
```
Archivos afectados: `api/viewsets.py` (acciones `render_offcanvas_*`)

**Paso 2.4 — Eliminar directorio antiguo**
Eliminar `templates/cotizaciones/` una vez confirmado que todos los templates
cargan correctamente desde la nueva ruta.

---

### FASE 3 — Service Layer por Modelo (Backend Core)

#### Paso 3.1 — `services/producto_service.py` [NUEVO - AUTORIZADO]

Responsabilidades:
- `ProductoSelector` — queries optimizadas para listar y detallar productos
- `ProductoCRUDService` — crear, actualizar, eliminar con `@transaction.atomic`
- `ProductoBusinessService` — validar unicidad de codigo por empresa, DSV
- `ProductoServiceMixin` — inyeccion en ViewSet de Producto

Campos SSoT:
```python
PRODUCTO_LIST_FIELDS = ('id', 'empresa_id', 'codigo', 'nombre', 'marca',
                        'referencia', 'unidad', 'precio_venta', 'activo', 'created_at')
PRODUCTO_DETAIL_FIELDS = PRODUCTO_LIST_FIELDS
```

Metodos minimos:
```
ProductoSelector.get_list(empresa_id, search=None, activo=None)
ProductoSelector.get_detail(empresa_id, pk)
ProductoCRUDService.crear(empresa_id, data)
ProductoCRUDService.actualizar(instance, data)
ProductoCRUDService.eliminar(instance)
ProductoBusinessService.registrar(empresa_id, data, instance=None)
ProductoServiceMixin.get_qs_list()
ProductoServiceMixin.get_qs_detail()
ProductoServiceMixin.service_crear_producto(serializer)
```

#### Paso 3.2 — `services/servicio_service.py` [NUEVO - AUTORIZADO]

Identico al patron de Producto, adaptado para `Servicio`:
- Campos: `nombre`, `precio_venta`, `activo`
- Sin campo `codigo` (servicios no tienen codigo unico)
- `ServicioSelector`, `ServicioCRUDService`, `ServicioBusinessService`, `ServicioServiceMixin`

#### Paso 3.3 — `services/item_service.py` [NUEVO - AUTORIZADO]

Responsabilidades:
- `CotizacionItemSelector` — mover desde `selectors.py`
- `CotizacionItemCRUDService` — crear/actualizar/eliminar items con recalculo atomico
- `CotizacionItemBusinessService` — logica movida desde `CotizacionItem.save()`:
  ```python
  @staticmethod
  def calcular_precio_venta(costo_unitario, porcentaje_utilidad):
      factor = Decimal('1') + (porcentaje_utilidad / Decimal('100'))
      return (costo_unitario * factor).quantize(Decimal('0.01'), ROUND_HALF_UP)

  @staticmethod
  def calcular_subtotal(cantidad, precio_unitario_venta):
      return (cantidad * precio_unitario_venta).quantize(Decimal('0.01'), ROUND_HALF_UP)
  ```
- DSV: verificar que `cotizacion.empresa_id == empresa_id` antes de agregar item
- Despues de crear/actualizar/eliminar item, invocar
  `CotizacionBusinessService.recalcular_totales(cotizacion_id)`

#### Paso 3.4 — Refactorizar `services/business_service.py`

Mantener solo la logica de cabecera de `Cotizacion`:
- `CotizacionService.crear_preforma()` — ya existe, mantener
- `CotizacionService.calcular_totales()` — ya existe, mantener
- `CotizacionService._build_header_fields()` — mantener
- Eliminar cualquier logica de items que se haya movido a `item_service.py`

#### Paso 3.5 — Refactorizar `services/selectors.py`

Separar en secciones claras con comentarios de bloque:
```
# --- CotizacionSelector ---
# --- CotizacionItemSelector ---  (mover a item_service.py o mantener aqui como referencia)
```
Agregar al final:
```
# --- ProductoSelector --- (importar desde producto_service.py)
# --- ServicioSelector ---  (importar desde servicio_service.py)
```

#### Paso 3.6 — Refactorizar `services/crud_service.py`

El `CotizacionCRUDService` actual mezcla logica de cliente, configuracion y cotizacion.
Separar:
- Mantener `CotizacionCRUDService` solo para operaciones de `Cotizacion` y generacion
  de `codigo_unico` (numeracion automatica)
- Los helpers de FK (`get_configuracion_for_empresa`, `get_cliente_for_empresa`)
  se mueven a `business_service.py` como metodos de validacion DSV

#### Paso 3.7 — `services/configuracion_service.py` [NUEVO - AUTORIZADO]

Servicio dedicado para `ConfiguracionCotizacion`:
```
ConfiguracionSelector.get_list(empresa_id)
ConfiguracionSelector.get_detail(empresa_id, pk)
ConfiguracionCRUDService.crear(empresa_id, data)
ConfiguracionCRUDService.actualizar(instance, data)
ConfiguracionCRUDService.eliminar(instance)  # solo si no tiene cotizaciones activas
ConfiguracionBusinessService.registrar(empresa_id, data, instance=None)
ConfiguracionServiceMixin  -> para ConfiguracionCotizacionViewSet
```

Este paso resuelve el gap C-6 del plan de auditoria (sub-app sin Service Layer).

#### Paso 3.8 — Actualizar `services/__init__.py`

Exportar todas las clases nuevas y eliminar el alias `CotizacionServiceLegacy`.
Eliminar `services/services.py` (fachada legacy vacia).

#### Paso 3.9 — Corregir `CotizacionItemViewSet` (gap C-5)

Agregar `CotizacionItemServiceMixin` a la herencia:
```python
class CotizacionItemViewSet(CotizacionItemServiceMixin, BaseTenantViewSet):
```
Eliminar el codigo de resolucion de empresa duplicado.

#### Paso 3.10 — Corregir `CotizacionViewSet.create()` (gap C-4)

El metodo `create()` debe delegar a `service_crear_cotizacion()` del mixin,
no llamar `serializer.save()` directamente:
```python
def create(self, request, *args, **kwargs):
    serializer = self.get_serializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    instance = self.service_crear_cotizacion(serializer)
    output = self.get_serializer(instance)
    return Response(output.data, status=status.HTTP_201_CREATED)
```
Eliminar `perform_create()` vacio (gap A-2).

#### Paso 3.11 — Corregir `_resolve_empresa()` en `api/viewsets.py` (gap A-1)

Reemplazar el fallback silencioso `Empresa.objects.only('id').first()` con:
```python
from rest_framework.exceptions import PermissionDenied
raise PermissionDenied("No se pudo determinar la empresa activa.")
```
Utilizar `resolve_tenant_empresa()` si ya existe en `apps.tenant.api.utils`,
equivalente a lo implementado en `ui_views.py`.

---

### FASE 4 — Servicio de Generacion PDF (`services/pdf_export_service.py`)

**Paso 4.1 — Crear `services/pdf_export_service.py` [NUEVO - AUTORIZADO]**

Este servicio reemplaza los archivos `pdf_service.py` y `utils/pdf_generator.py`
que actualmente no existen en disco (archivos eliminados pero referenciados).

Responsabilidades:
- `CotizacionPDFExportService.generar_pdf_publico(cotizacion, empresa, request)`
  → renderiza `tenant/cotizaciones/pdf/formato_profesional.html`
  → retorna bytes del PDF via `xhtml2pdf`
  → omite columnas de costo/margen/USD
- `CotizacionPDFExportService.generar_pdf_interno(cotizacion, empresa, request)`
  → renderiza `tenant/cotizaciones/pdf/formato_interno.html`
  → incluye columnas de costo, margen, utilidad USD

Metodo de preparacion de contexto (extraido de la logica referenciada en viewsets):
```python
@staticmethod
def preparar_contexto(cotizacion, empresa, request):
    items_qs = CotizacionItemSelector.get_list(cotizacion.id, empresa.id)
    secciones = CotizacionPDFExportService._agrupar_por_tipo(items_qs)
    subtotales = CotizacionPDFExportService._calcular_subtotales(secciones)
    return {
        'cotizacion': cotizacion,
        'empresa': empresa,
        'secciones': secciones,
        'subtotales': subtotales,
        'iva_porcentaje': cotizacion.iva_porcentaje,
        'total_con_impuestos': cotizacion.total_con_impuestos,
    }

@staticmethod
def _agrupar_por_tipo(items_qs):
    # Agrupa items en {'PRODUCTO': [...], 'MATERIAL': [...], 'SERVICIO': [...]}
    # Asigna numero secuencial por seccion (1.1, 1.2, ..., 2.1, 2.2, ...)
    # Coincide con la estructura visual del PDF plantilla
    ...
```

**Paso 4.2 — Refactorizar `api/viewsets.py` accion `exportar_pdf`**

Reemplazar la logica inline por llamada directa al servicio:
```python
@action(detail=True, methods=['get'], url_path='exportar-pdf')
def exportar_pdf(self, request, uuid=None):
    cotizacion = self.get_object()
    empresa = self._resolve_empresa(request)
    pdf_bytes = CotizacionPDFExportService.generar_pdf_publico(cotizacion, empresa, request)
    ...
```

**Paso 4.3 — Refactorizar template PDF publico**

`templates/tenant/cotizaciones/pdf/formato_profesional.html` debe renderizar:
- Seccion 1: Carta de presentacion (membrete + destinatario + cuerpo introductorio)
- Seccion 2: Tabla propuesta economica agrupada por `tipo_item`
  - Columnas visibles: ITEM, DESCRIPCION, MARCA, REFERENCIA, CANT, UND, V.UNIT, V.TOTAL
  - Subtotal por seccion con fila de cierre azul
  - Fila SUBTOTAL antes de IVA
  - Fila IVA (porcentaje dinamico desde cotizacion)
  - Fila TOTAL VALOR $ mc (en negrita)

**Paso 4.4 — Crear template PDF interno [NUEVO]**

`templates/tenant/cotizaciones/pdf/formato_interno.html` incluye adicionalmente:
- Columna `Margen %` (`CotizacionItem.porcentaje_utilidad`)
- Columna `Utilidad Venta $ mc` (calculada)
- Indicadores globales: margen ponderado, total costos, total utilidad

---

### FASE 5 — API Endpoints Nuevos (Producto y Servicio)

**Paso 5.1 — Crear `api/serializers.py` secciones Producto y Servicio**

Agregar en el archivo existente:
```python
class ProductoListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = ('id', 'codigo', 'nombre', 'marca', 'referencia',
                  'unidad', 'precio_venta', 'activo')

class ProductoSerializer(ProductoListSerializer):
    pass  # mismo conjunto de campos (modelo simple)

class ServicioListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Servicio
        fields = ('id', 'nombre', 'precio_venta', 'activo')

class ServicioSerializer(ServicioListSerializer):
    pass
```

**Paso 5.2 — Crear ViewSets en `api/viewsets.py`**

```python
class ProductoViewSet(ProductoServiceMixin, BaseTenantViewSet):
    queryset = Producto.objects.none()
    serializer_class = ProductoSerializer
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    renderer_classes = [JSONRenderer]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        empresa_id = self.get_empresa_id()
        return ProductoSelector.get_list(empresa_id)

    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer],
            url_path='render-offcanvas/crear')
    def render_offcanvas_crear(self, request):
        return Response({}, template_name='tenant/cotizaciones/offcanvas_crear_producto.html')

    @action(detail=True, methods=['get'], renderer_classes=[TemplateHTMLRenderer],
            url_path='render-offcanvas/editar')
    def render_offcanvas_editar(self, request, **kwargs):
        instance = self.get_object()
        return Response({'producto': instance},
                        template_name='tenant/cotizaciones/offcanvas_editar_producto.html')

class ServicioViewSet(ServicioServiceMixin, BaseTenantViewSet):
    # Identico al patron de ProductoViewSet
    ...
```

**Paso 5.3 — Registrar rutas en `api/urls.py`**

```python
router.register(r'productos', ProductoViewSet, basename='cotizacion-producto')
router.register(r'servicios', ServicioViewSet, basename='cotizacion-servicio')
```

Endpoints resultantes:
- `GET /api/v1/cotizaciones/productos/` — listado con Tabulator
- `POST /api/v1/cotizaciones/productos/` — crear producto
- `GET /api/v1/cotizaciones/productos/{uuid}/` — detalle
- `PATCH /api/v1/cotizaciones/productos/{uuid}/` — actualizar
- `DELETE /api/v1/cotizaciones/productos/{uuid}/` — eliminar
- `GET /api/v1/cotizaciones/productos/render-offcanvas/crear/` — HTML HTMX
- `GET /api/v1/cotizaciones/productos/{uuid}/render-offcanvas/editar/` — HTML HTMX
- Mismo patron para `/servicios/`

---

### FASE 6 — CBVs (`ui_views.py`)

Las CBVs NO contienen logica de negocio. Son UI Shells que consumen servicios.

**Paso 6.1 — Agregar CBVs para Producto**

```python
class ProductoListOffcanvasView(CotizacionTemplateView):
    template_name = 'tenant/cotizaciones/list_producto.html'

class ProductoCrearOffcanvasView(CotizacionTemplateView):
    template_name = 'tenant/cotizaciones/offcanvas_crear_producto.html'

class ProductoEditarOffcanvasView(CotizacionTemplateView):
    template_name = 'tenant/cotizaciones/offcanvas_editar_producto.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = kwargs.get('pk')
        empresa = self._resolve_empresa()
        producto = ProductoSelector.get_detail(empresa.id, pk)
        if not producto:
            raise Http404("Producto no encontrado")
        context['producto'] = producto
        return context

class ProductoDetalleOffcanvasView(ProductoEditarOffcanvasView):
    template_name = 'tenant/cotizaciones/offcanvas_detalle_producto.html'
```

**Paso 6.2 — Agregar CBVs para Servicio**

Identico al patron de Producto, usando `ServicioSelector`.

**Paso 6.3 — Registrar rutas UI en `api/urls.py`**

```python
ui_urlpatterns += [
    path('partials/productos/', ProductoListOffcanvasView.as_view(), name='ui_list_producto'),
    path('partials/productos/crear/', ProductoCrearOffcanvasView.as_view(), name='ui_crear_producto'),
    path('partials/productos/editar/<int:pk>/', ProductoEditarOffcanvasView.as_view(), name='ui_editar_producto'),
    path('partials/productos/ver/<int:pk>/', ProductoDetalleOffcanvasView.as_view(), name='ui_ver_producto'),
    path('partials/servicios/', ServicioListOffcanvasView.as_view(), name='ui_list_servicio'),
    path('partials/servicios/crear/', ServicioCrearOffcanvasView.as_view(), name='ui_crear_servicio'),
    path('partials/servicios/editar/<int:pk>/', ServicioEditarOffcanvasView.as_view(), name='ui_editar_servicio'),
    path('partials/servicios/ver/<int:pk>/', ServicioDetalleOffcanvasView.as_view(), name='ui_ver_servicio'),
]
```

---

### FASE 7 — Frontend Feature-Sliced Design

**Paso 7.1 — Canonizar archivos JS existentes**

Determinar cuales son canonicos vs legacy:
- CANONICO: `features/cotizacion_list.js` → mantener y limpiar
- LEGACY a ELIMINAR: `cotizaciones.list.js`, `cotizaciones.editor.js`,
  `cotizaciones.detalle.js`, `cotizaciones.module.js`
  (confirmar que no son referenciados en templates antes de eliminar)

**Paso 7.2 — Crear `features/cotizacion_editor.js` [NUEVO]**

Consolida la logica de formularios de creacion y edicion de `Cotizacion`.
Patron obligatorio (segun `.agents/skills/frontend/crud-fsd.md`):
- Escucha `shown.bs.offcanvas` para inyectar logica al offcanvas dinamico
- Captura payload via `FormData` + DOM Shield (inputs ocultos para FKs)
- Envia JSON via `window.http(method, url, data)` con JWT Bearer header
- On success: dispara `CustomEvent('cotizacionGuardada')`
- On error: delega a `window.UIManager.handleError(response)`

**Paso 7.3 — Crear `features/producto_list.js` [NUEVO]**

```javascript
// Namespace: window.Sintel.Cotizaciones.Productos
(function(w, d) {
  'use strict';
  w.Sintel = w.Sintel || {};
  w.Sintel.Cotizaciones = w.Sintel.Cotizaciones || {};
  
  var state = { table: null };
  var DOM = {
    grid: '#tabla-productos',
    search: '#search-producto',
    btnCrear: '#btn-producto-crear',
    container: '#offcanvas-container-productos'
  };

  function init() {
    state.table = w.TabulatorFactory.create(
      DOM.grid,
      '/api/v1/cotizaciones/productos/',
      getColumnas(),
      { searchInputSelector: DOM.search }
    );
    bindEvents();
  }

  function getColumnas() {
    return [
      { title: 'Codigo', field: 'codigo', widthGrow: 1 },
      { title: 'Nombre', field: 'nombre', widthGrow: 2 },
      { title: 'Marca', field: 'marca', widthGrow: 1 },
      { title: 'Precio Venta', field: 'precio_venta',
        formatter: w.TabulatorFactory.formatters.currency },
      { title: 'Estado', field: 'activo',
        formatter: w.TabulatorFactory.formatters.badgeStatus },
      {
        title: 'Acciones',
        formatter: function() {
          return '<div class="btn-group btn-group-sm">' +
            '<button class="btn btn-outline-primary" data-action="edit">' +
            '<i class="bi bi-pencil"></i></button>' +
            '<button class="btn btn-outline-danger" data-action="delete">' +
            '<i class="bi bi-trash"></i></button></div>';
        },
        cellClick: handleCellAction
      }
    ];
  }

  function handleCellAction(e, cell) {
    var btn = e.target.closest('button');
    if (!btn) return;
    var action = btn.dataset.action;
    var row = cell.getRow().getData();
    if (action === 'edit') abrirEdicion(row.uuid);
    if (action === 'delete') eliminar(row.uuid, row.activo);
  }

  function abrirEdicion(uuid) {
    var url = '/api/v1/cotizaciones/productos/' + uuid + '/render-offcanvas/editar/';
    htmx.ajax('GET', url, { target: DOM.container, swap: 'innerHTML' });
  }

  async function eliminar(uuid, activo) {
    if (activo) {
      w.UIManager.notifyError({
        data: { detail: 'Inactivar el producto antes de eliminarlo.' }
      });
      return;
    }
    // confirmacion y DELETE via API
  }

  function bindEvents() {
    var btn = d.querySelector(DOM.btnCrear);
    if (btn) {
      btn.addEventListener('htmx:afterRequest', function() {
        state.table.replaceData();
      });
    }
    d.addEventListener('productoGuardado', function() { state.table.replaceData(); });
    d.addEventListener('productoEliminado', function() { state.table.replaceData(); });
  }

  w.Sintel.Cotizaciones.Productos = { init: init };

}(window, document));
```

**Paso 7.4 — Crear `features/producto_editor.js` [NUEVO]**

- Escucha `shown.bs.offcanvas` filtrado por ID `offcanvas-producto`
- Captura: `codigo`, `nombre`, `marca`, `referencia`, `unidad`, `precio_venta`, `activo`
- PATCH si existe `data-producto-uuid`, POST si no
- On success: `d.dispatchEvent(new CustomEvent('productoGuardado'))`

**Paso 7.5 — Crear `features/servicio_list.js` y `features/servicio_editor.js` [NUEVOS]**

Identico al patron de Producto. Campos: `nombre`, `precio_venta`, `activo`.

**Paso 7.6 — Crear `features/item_editor.js` [NUEVO]**

Logica de formulario para agregar/editar items dentro de una cotizacion:
- Calculo en tiempo real: `precio_venta = costo_unitario * (1 + utilidad/100)`
- Subtotal en tiempo real: `subtotal = cantidad * precio_venta`
- Selector de Producto/Servicio con autocompletado (HTMX o fetch al API)
- DOM Shield obligatorio para FKs (`producto_id`, `servicio_id`)
- On success: recalcular totales de la cotizacion (`CustomEvent('itemGuardado')`)

**Paso 7.7 — Actualizar `cotizaciones.api.js`**

Agregar endpoints para los nuevos modelos:
```javascript
var URLS = {
  cotizaciones:  '/api/v1/cotizaciones/',
  items:         '/api/v1/cotizaciones/items/',
  productos:     '/api/v1/cotizaciones/productos/',
  servicios:     '/api/v1/cotizaciones/servicios/',
  configuracion: '/api/v1/cotizaciones/configuracion/',
};
```

**Paso 7.8 — Actualizar `cotizaciones.main.js`**

Inicializar los nuevos sub-modulos cuando el tab de cotizaciones se active:
```javascript
if (w.Sintel.Cotizaciones.Productos) w.Sintel.Cotizaciones.Productos.init();
if (w.Sintel.Cotizaciones.Servicios) w.Sintel.Cotizaciones.Servicios.init();
```

---

### FASE 8 — Templates HTML por Modelo

**Paso 8.1 — Templates para Producto (4 archivos nuevos)**

Cada template sigue el patron FSD:
- `list_producto.html`: contiene boton `hx-get` + contenedor Tabulator + offcanvas vacio
- `offcanvas_crear_producto.html`: formulario campos Producto, accion POST via `producto_editor.js`
- `offcanvas_editar_producto.html`: formulario pre-llenado, accion PATCH
- `offcanvas_detalle_producto.html`: vista readonly, sin formulario

Todos heredan de la estructura Bootstrap Offcanvas estandar del proyecto.

**Paso 8.2 — Templates para Servicio (4 archivos nuevos)**

Mismo patron que Producto. Campos: `nombre`, `precio_venta`, `activo`.

**Paso 8.3 — Refactorizar template PDF publico**

`templates/tenant/cotizaciones/pdf/formato_profesional.html` — estructura objetivo:
```html
<!-- BLOQUE 1: Carta de presentacion -->
<div class="carta-presentacion">
  <div class="membrete"><!-- logo, fecha, numero cotizacion --></div>
  <div class="destinatario"><!-- cliente, sede, ciudad --></div>
  <h3 class="asunto">ASUNTO: {{ cotizacion.asunto }}</h3>
  <div class="cuerpo"><!-- texto introductorio de la empresa --></div>
</div>

<!-- SALTO DE PAGINA -->
<div style="page-break-before: always;"></div>

<!-- BLOQUE 2: Propuesta economica -->
<table class="tabla-propuesta">
  <thead><!-- ITEM | DESCRIPCION | MARCA | REFERENCIA | CANT | UND | V.UNIT | V.TOTAL --></thead>
  {% for seccion in secciones %}
  <tr class="seccion-header">
    <td colspan="8">{{ seccion.numero }}. {{ seccion.nombre }}</td>
  </tr>
  {% for item in seccion.items %}
  <tr>
    <td>{{ item.numero_secuencial }}</td>
    <td>{{ item.descripcion }}</td>
    <td>{{ item.marca }}</td>
    <td>{{ item.referencia }}</td>
    <td>{{ item.cantidad }}</td>
    <td>{{ item.unidad }}</td>
    <td>{{ item.precio_unitario_venta|floatformat:0 }}</td>
    <td>{{ item.subtotal_linea|floatformat:0 }}</td>
  </tr>
  {% endfor %}
  <tr class="subtotal-seccion">
    <td colspan="7">SUBTOTAL $</td>
    <td>{{ seccion.subtotal|floatformat:0 }}</td>
  </tr>
  {% endfor %}
  <tr><td colspan="7">SUBTOTAL (antes de IVA)</td><td>{{ subtotales.antes_iva }}</td></tr>
  <tr><td colspan="7">IVA {{ cotizacion.iva_porcentaje }}%</td><td>{{ subtotales.iva }}</td></tr>
  <tr class="total-final"><td colspan="7">TOTAL VALOR $ mc</td><td>{{ cotizacion.total_con_impuestos }}</td></tr>
</table>
```

---

### FASE 9 — Limpieza y Deuda Tecnica

**Paso 9.1 — Eliminar `services/services.py`**
Fachada vacia que solo re-exporta. Actualizar imports en codigo que la use.

**Paso 9.2 — Eliminar `facturas_prueba/`**
Archivos XML/PDF de prueba no deben residir en el directorio de la app.
Mover a `documentacion/_archive/` o agregar a `.gitignore`.

**Paso 9.3 — Limpiar archivos JS legacy**
Tras confirmar que no son referenciados en templates:
- Eliminar `cotizaciones.list.js` (reemplazado por `features/cotizacion_list.js`)
- Eliminar `cotizaciones.editor.js` (reemplazado por `features/cotizacion_editor.js`)
- Eliminar `cotizaciones.detalle.js`
- Eliminar `cotizaciones.module.js`

**Paso 9.4 — Actualizar `AUDITORIA_FLUJO_COMPLETO.md`**
Reflejar la nueva arquitectura, estructura de archivos y flujos CRUD por modelo.

---

## Seccion 5: Orden de Ejecucion y Dependencias

```
FASE 0 (prerequisito)
  |
  +--> FASE 1 (models.py)
  |       |
  |       +--> FASE 3 (services - backend) <-- depende de FASE 1
  |               |
  |               +--> FASE 4 (PDF service) <-- depende de FASE 3
  |               |
  |               +--> FASE 5 (API endpoints nuevos) <-- depende de FASE 3
  |
  +--> FASE 2 (mover templates) <-- independiente, puede ejecutarse primero
          |
          +--> FASE 6 (CBVs) <-- depende de FASE 2 y FASE 3
          |
          +--> FASE 8 (templates HTML nuevos) <-- depende de FASE 2
                  |
                  +--> FASE 7 (JS FSD) <-- depende de FASE 8 y FASE 5
                          |
                          +--> FASE 9 (limpieza) <-- depende de TODAS
```

---

## Seccion 6: Restricciones y Autorizaciones RFC

### Archivos `.py` NUEVOS — Autorizados por este RFC

| Archivo nuevo | Justificacion |
|---|---|
| `services/producto_service.py` | Modelo sin Service Layer — gap critico C-6 |
| `services/servicio_service.py` | Modelo sin Service Layer — gap critico C-6 |
| `services/item_service.py` | Extraer logica del modelo (`save()`) — gap C-2 |
| `services/configuracion_service.py` | Sub-app sin Service Layer — gap C-6 |
| `services/pdf_export_service.py` | Reemplaza archivos eliminados referenciados en viewsets |
| `configuracion/services/__init__.py` | Estructura Service Layer sub-app |
| `configuracion/services/selectors.py` | Idem |
| `configuracion/services/crud_service.py` | Idem |
| `configuracion/services/business_service.py` | Idem |
| `configuracion/services/api_mixins.py` | Idem |

### Archivos `.py` ELIMINADOS por este RFC

| Archivo a eliminar | Razon |
|---|---|
| `services/services.py` | Fachada legacy vacia — alias redundante |

### Archivos sin cambio de negocio

| Archivo | Estado |
|---|---|
| `models.py` | Solo limpiar `save()` de `CotizacionItem` |
| `configuracion/models.py` | Solo verificar FK `empresa` redundante |
| `api/pagination.py` | Sin cambios |
| `permissions.py` | Sin cambios |

---

## Seccion 7: Validaciones por Fase

Cada fase debe pasar las siguientes validaciones antes de continuar a la siguiente:

```
FASE 1: python -m py_compile apps/tenant/cotizaciones/models.py
FASE 2: Verificar que Django carga templates desde nueva ruta (test request a endpoint HTMX)
FASE 3: python -m py_compile apps/tenant/cotizaciones/services/*.py
FASE 4: Generar PDF desde endpoint y verificar estructura visual
FASE 5: GET /api/v1/cotizaciones/productos/ retorna 200 con datos paginados
FASE 6: Requests HTMX a partials/productos/ retornan HTML valido
FASE 7: Console sin errores JS al cargar workspace con tab cotizaciones
FASE 8: Templates renderizan sin errores de template tag
FASE 9: git diff --stat confirma eliminacion de archivos legacy
FINAL:  python manage.py test apps.tenant.cotizaciones
```

---

*Fin del Plan de Accion — Generado segun base de conocimiento SINTEL v2.62.0*
*RFC valido hasta: aprobacion del usuario o nueva version de AGENTS.md*
