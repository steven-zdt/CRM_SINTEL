# Auditoria Completa del Modulo de Gastos - Proyecto SINTEL v2.61.4

**Fecha de auditoria:** 2026-03-22  
**Version del sistema validada:** v2.61.4  
**Workspace actual:** v2.95  
**Modulo:** `apps/tenant/gastos`  
**Estado del documento:** sincronizado con codigo real

---

## 1. Resumen Ejecutivo

El modulo `gastos` opera hoy como un flujo de `DocumentoSoporte` DIAN con clasificacion contable posterior, no como un CRUD simple de gastos ni como un formulario basado en tipo/subtipo.

La implementacion vigente combina:

- `DocumentoSoporte` como evidencia legal inmutable.
- `Gasto` como capa operativa mutable y clasificatoria.
- `ResolucionDIAN` como fuente autorizante del consecutivo.
- Hooks de materializacion contable hacia `contabilidad`.
- Workspace con HTMX + Bootstrap Offcanvas + Tabulator.
- Fachada Core versionada para consumo workspace.

Hallazgos de alineacion mas importantes:

- El flujo vivo del workspace ya usa `gasto_form.js`, `gastos_main.js`, `resolucion_dian_main.js` y `resolucion_dian_form.js`.
- El alta de gasto ya no depende del desglose manual de `ItemGasto`; el usuario captura subtotal directo y el backend genera un item generico automatico para preservar integridad referencial.
- El calculo financiero centralizado ya vive en `calcular_totales_gasto()` y trata los porcentajes como valores humanos que deben dividirse entre 100.
- `GastoViewSet.create()` ya no manipula `items`; delega el payload simplificado directamente a `GastoService.registrar_gasto_total()`.
- `ResolucionDIAN` ya valida unicidad de `numero_resolucion` por empresa desde Service Layer y retorna `422 Unprocessable Entity` alineado con `UIManager`.
- La grilla de resoluciones ya incluye acciones `Ver` y `Eliminar`, con bloqueo de borrado si hay documentos asociados.

---

## 2. Arquitectura Actual del Modulo

### 2.1. Backend real

```text
apps/tenant/gastos/
├── models.py
├── services/
│   ├── __init__.py
│   └── services.py
├── api/
│   ├── serializers.py
│   ├── urls.py
│   └── viewsets.py
├── admin.py
├── choices/
│   ├── categoria_contable.py
│   └── centros_costo.py
├── tests/
└── AUDITORIA_FLUJO_COMPLETO.md
```

Notas:

- La logica viva del dominio esta consolidada en `apps/tenant/gastos/services/services.py`.
- `apps/tenant/gastos/services/__init__.py` expone la fachada de servicios consumida por serializers y viewsets.
- El documento anterior seguia describiendo `services.py` como archivo raiz principal; hoy el runtime usa el paquete `services/`.

### 2.2. Fachada Core real

```text
apps/tenant/core/api/v1/gastos/
├── serializers.py
└── viewsets.py
```

Notas:

- No existe `urls.py` local dentro de `apps/tenant/core/api/v1/gastos/`.
- El registro de la fachada Core se hace en `apps/tenant/core/api/urls.py`.

### 2.3. Frontend real del workspace

Templates activos:

```text
apps/tenant/core/templates/tenant/core/partials/gastos/
├── assets_gastos.html
├── gastos_list.html
├── offcanvas_crear.html
├── offcanvas_detalle.html
├── offcanvas_resolucion.html
└── partial_summary.html
```

JavaScript activo:

```text
apps/tenant/core/static/core/js/gastos/
├── gastos.api.js
├── gastos_main.js
├── gasto_form.js
├── resolucion_dian_form.js
└── resolucion_dian_main.js
```

Hallazgos reales:

- Los archivos `gastos_crear.js`, `gastos_anular.js`, `gastos_resolucion.js`, `gastos_resoluciones_list.js`, `gastos.modals.js`, `resoluciones.api.js` y `resoluciones.page.js` ya no forman parte del bundle activo.
- `assets_gastos.html` carga exclusivamente los 5 archivos anteriores y ese es el bundle oficial del workspace.
- El contenedor HTMX operativo es `#offcanvas-container-gastos`.

---

## 3. Modelo de Dominio y Tipo de Documento

### 3.1. Tipo documental vigente

El tipo documental oficial del flujo vivo es:

- `DocumentoSoporte`

No existe en el flujo operativo real un campo `tipo_documento`, ni un esquema `tipo/subtipo` como eje del formulario o del modelo principal.

Separacion real:

- `DocumentoSoporte`: evidencia legal DIAN e informacion monetaria.
- `Gasto`: clasificacion operativa y contable del documento.

### 3.2. ResolucionDIAN

Ubicacion:

- `apps/tenant/gastos/models.py`

Campos principales:

- `numero_resolucion`
- `prefijo`
- `rango_desde`
- `rango_hasta`
- `fecha_resolucion`
- `fecha_inicio`
- `fecha_fin`
- `clave_tecnica`
- `vigente`

Reglas reales:

- Solo una resolucion puede quedar `vigente=True` por empresa.
- `save()` desactiva automaticamente otras resoluciones vigentes de la misma empresa.
- `clean()` valida rangos y fechas.
- `esta_dentro_de_fecha()` define uso operativo.
- Service Layer valida unicidad de `numero_resolucion` por `empresa` antes de persistir.

### 3.3. DocumentoSoporte

Ubicacion:

- `apps/tenant/gastos/models.py`

Campos principales:

- `resolucion_dian`
- `prefijo`
- `consecutivo`
- `fecha`
- `vendedor_nombre`
- `vendedor_nit`
- `vendedor_direccion`
- `vendedor_telefono`
- `numero_factura_proveedor`
- `subtotal`
- `retefuente_porcentaje`
- `retefuente`
- `reteica_porcentaje`
- `reteica`
- `total`
- `adjunto`
- `activo`
- `anulado`
- `fecha_anulacion`

Reglas reales:

- El consecutivo es inmutable y debe quedar dentro del rango de la resolucion.
- El consecutivo no se recicla aunque el documento se anule.
- `clean()` recalcula y valida formula monetaria.
- La evidencia documental y monetaria no se edita desde `update()` de gasto.

Constraints reales:

- unicidad por `(resolucion_dian, consecutivo)`
- unicidad por `(empresa, vendedor_nit, numero_factura_proveedor)` cuando `anulado=False`

### 3.4. Gasto

Ubicacion:

- `apps/tenant/gastos/models.py`

Campos operativos principales:

- `documento_soporte`
- `proveedor`
- `numero_factura_proveedor`
- `asiento_contable`
- `cuenta_contable_uuid` **(NEW v2.61.4 - MANDATORY)**: referencia UUID al Plan de Cuentas (CuentaContable). Campo `blank=False` para enforcement de soberanía contable.
- `centro_costo` **(NEW v2.61.4 - OPTIONAL)**: campo `null=True, blank=True` para compatibilidad legacy.
- `categoria_contable` **(NEW v2.61.4 - OPTIONAL)**: campo `null=True, blank=True` para compatibilidad legacy.
- `periodo`
- `descripcion`
- `observaciones`

Reglas reales:

- `Gasto` representa clasificacion operativa, no el documento legal.
- `is_editable` retorna `False` cuando ya existe `asiento_contable`.
- Los valores monetarios se delegan al `DocumentoSoporte`.
- **NEW v2.61.4**: La clasificación contable primaria ahora es obligatoriamente `cuenta_contable_uuid`. Los campos `centro_costo` y `categoria_contable` son opcionales y compatibles con workflows legacy, pero no son requeridos para crear un gasto válido.

### 3.5. ItemGasto

Ubicacion:

- `apps/tenant/gastos/models.py`

Estado real:

- El modelo existe y sigue vigente.
- El flujo principal del workspace ya no captura multiples items manualmente.
- `GastoService.registrar_gasto_total()` crea un unico item generico automaticamente para preservar integridad referencial.

Campos:

- `descripcion`
- `cantidad`
- `valor_unitario`
- `total_linea`

### 3.6. GastoAnexo

Estado real:

- Existe `GastoAnexo` como capa de anexos operativos.
- Convive con `DocumentoSoporte.adjunto` como evidencia legal principal.

---

## 4. Capa de Servicios Real

Ubicacion operativa:

- `apps/tenant/gastos/services/services.py`

Responsabilidades vigentes:

- obtener resolucion vigente
- calcular consecutivo atomico
- construir querysets optimizados
- desactivar y anular documentos
- calcular summary financiero
- crear, desactivar y validar resoluciones
- validar eliminacion de resoluciones en uso
- registrar gasto completo desde subtotal directo

Funciones clave:

- `obtener_resolucion_vigente(empresa)`
- `obtener_siguiente_numero_soporte(empresa)`
- `qs_list(empresa_id, search=None)`
- `qs_detail(empresa_id)`
- `desactivar_gasto_service(gasto_id)`
- `anular_gasto_service(gasto_id)`
- `get_gastos_summary(empresa_id=None)`
- `qs_resolucion_list(empresa_id)`
- `qs_resolucion_detail(empresa_id, resolucion_id)`
- `crear_resolucion(empresa, data)`
- `desactivar_resolucion(empresa, resolucion_id)`
- `calcular_totales_gasto(subtotal, retefuente_pct, reteica_pct)`
- `calcular_retenciones(subtotal, retefuente_porcentaje, reteica_porcentaje)` como wrapper de compatibilidad
- `puede_eliminar_resolucion(empresa, resolucion_id)`
- `GastoService.registrar_gasto_total(empresa, data, items_data=None)`

Reglas de negocio reales:

- `calcular_totales_gasto()` usa `Decimal` y divide porcentajes por 100 antes de operar.
- `registrar_gasto_total()` ya no exige `items_data` para el flujo principal.
- Si no llegan items, el servicio crea un `ItemGasto` generico con cantidad `1.00` y valor igual al subtotal.
- `crear_resolucion()` valida unicidad por `empresa + numero_resolucion` antes de desactivar otras resoluciones vigentes.
- `obtener_siguiente_numero_soporte()` usa `select_for_update()` e incluye anulados para preservar secuencia.
- `get_gastos_summary()` excluye documentos anulados e inactivos.

**NEW v2.61.4 - Normalización de Porcentajes:**
- `_normalizar_porcentaje_choice_retefuente(value)`: Convierte valores UI (human-readable: 4, 6, 10, 11, 0) al formato de choice DB (0.04, 0.06, 0.10, 0.11, 0.00).
- `_normalizar_porcentaje_choice_reteica(value)`: Convierte valores UI (0.966, 0.69, 1.104, 0) al formato choice DB (0.00966, 0.0069, 0.01104, 0.00).
- `process_gasto_payload()` aplica normalización y valida contra `ContabilidadBusinessService.obtener_cuentas_gasto_disponibles()`.
- `ejecutar_operacion_gasto()` usa patrón de orchestration: `return {**data_original, **payload_normalized}` para preservar todos los campos antes de serializer.

**NEW v2.61.4 - Soberanía Contable:**
- El servicio valida que `cuenta_contable_uuid` existe en el catálogo de CuentaContable del tenant.
- Si la cuenta no existe o no pertenece al tenant, la validación falla antes de persistencia.
- La validación es delegada a `ContabilidadBusinessService`, no a consultas directas de modelos.

---

## 5. Capa de API Real

### 5.1. Rutas del modulo gastos

`apps/tenant/gastos/api/urls.py` registra:

- raiz `''` con `GastoViewSet`

Por inclusion en `config/api_urls.py`, el modulo expone:

- `/api/v1/gastos/`

### 5.2. Rutas de resoluciones

`ResolucionDIANViewSet` se registra fuera del router local de `gastos` y expone:

- `/api/v1/resoluciones-dian/`

### 5.3. GastoViewSet

Ubicacion:

- `apps/tenant/gastos/api/viewsets.py`

Configuracion real:

- base: `BaseTenantViewSet`
- permisos: `IsTenantMember`, `IsTenantAdminOrReadOnly`
- autenticacion: `SessionAuthentication`
- parsers: JSON, Form y MultiPart
- `http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']`

Acciones reales:

- `GET /api/v1/gastos/`
- `POST /api/v1/gastos/`
- `GET /api/v1/gastos/{id}/`
- `PUT /api/v1/gastos/{id}/`
- `PATCH /api/v1/gastos/{id}/`
- `DELETE /api/v1/gastos/{id}/`
- `POST /api/v1/gastos/{id}/desactivar/`
- `POST /api/v1/gastos/{id}/anular/`
- `GET /api/v1/gastos/summary/`
- `GET /api/v1/gastos/resoluciones/`
- `GET /api/v1/gastos/resolucion-activa/`
- `GET /api/v1/gastos/gestor-offcanvas/`
- `GET /api/v1/gastos/render-offcanvas/crear/`
- `GET /api/v1/gastos/render-offcanvas/resolucion/`
- `GET /api/v1/gastos/render-offcanvas/detalle/?id=...`
- `POST /api/v1/gastos/configurar-resolucion/`

Flujo real de `create()`:

1. Obtiene `empresa` desde `tenant_empresa`.
2. Copia `request.data`.
3. Delega todo el registro a `GastoService.registrar_gasto_total(empresa, data)`.
4. Retorna `GastoDetailSerializer` con `201`.
5. Si la materializacion contable falla, el gasto no se revierte; queda warning y continua.

Reglas de mutabilidad reales:

- `update()` y `partial_update()` solo permiten editar campos operativos del `Gasto`.
- Los campos legales y monetarios del `DocumentoSoporte` son inmutables por API de edicion.
- `destroy()` no es el flujo operativo recomendado; el flujo normal es `desactivar -> anular`.

### 5.4. Endpoint legacy de configuracion de resolucion

`POST /api/v1/gastos/configurar-resolucion/` sigue activo por compatibilidad HTMX del workspace.

Comportamiento actual:

- valida con `ResolucionDIANCreateSerializer`
- delega persistencia a `crear_resolucion()`
- retorna `422` con `details` y `missing_fields` cuando hay error de validacion

### 5.5. ResolucionDIANViewSet

Configuracion real:

- base: `BaseTenantViewSet`
- `http_method_names = ['get', 'post', 'delete', 'head', 'options']`

Acciones reales:

- `GET /api/v1/resoluciones-dian/`
- `POST /api/v1/resoluciones-dian/`
- `GET /api/v1/resoluciones-dian/{id}/`
- `DELETE /api/v1/resoluciones-dian/{id}/`
- `POST /api/v1/resoluciones-dian/{id}/desactivar/`
- `GET /api/v1/resoluciones-dian/activa/`

Reglas reales:

- no permite `PUT/PATCH`
- `DELETE` solo procede si no hay documentos asociados
- `create()` ya retorna `422` con `details` y `missing_fields` en errores de validacion

---

## 6. Core API Facade Real

Registro real en `apps/tenant/core/api/urls.py`:

- `/api/v1/core/v1/gastos/operativos/`
- `/api/v1/core/v1/gastos/resoluciones-dian/`
- gateway directo `/api/v1/core/_apps/gastos/`

ViewSets facade:

- `GastoCoreViewSet(GastoViewSet)`
- `ResolucionDIANCoreViewSet(ResolucionDIANViewSet)`

Comportamiento real:

- heredan logica y acciones de los viewsets propietarios
- no duplican Service Layer
- cambian serializer para el consumo workspace cuando aplica

Serializers facade:

- `DocumentoSoporteWorkspaceDetailSerializer`
- `GastoWorkspaceListSerializer`
- `GastoWorkspaceDetailSerializer`

Valor agregado real:

- `DocumentoSoporteWorkspaceDetailSerializer` expone `adjunto_url` cuando el request esta disponible

---

## 7. Serializers Reales del Modulo

Ubicacion:

- `apps/tenant/gastos/api/serializers.py`

Serializers vigentes:

- `ResolucionDIANNestedSerializer`
- `ResolucionDIANListSerializer`
- `ResolucionDIANCreateSerializer`
- `ResolucionDIANDetailSerializer`
- `GastoListSerializer`
- `DocumentoSoporteDetailSerializer`
- `GastoDetailSerializer`
- `ItemGastoSerializer`
- `GastoWorkspaceSerializer`

Hallazgos importantes:

- `GastoListSerializer` usa campos aplanados `ds_*` para Tabulator.
- `GastoWorkspaceSerializer` todavia conserva `items` como campo opcional por compatibilidad, pero el flujo principal del workspace no lo usa.
- `GastoWorkspaceSerializer.create()` aun puede recibir `items_data`, aunque el endpoint principal `GastoViewSet.create()` ya no los envia.

**NEW v2.61.4 - Campos Opcionales y Precisión Decimal:**
- `retefuente_porcentaje`: `DecimalField(max_digits=8, decimal_places=5, required=False)` - Porcentaje de retención en la fuente, envío opcional.
- `reteica_porcentaje`: `DecimalField(max_digits=8, decimal_places=5, required=False)` - Porcentaje de ReteICA, envío opcional. **NOTA**: `decimal_places` aumentado de 3 a 5 para soportar valores como 0.00966 (0.966%).
- `centro_costo`: `CharField(required=False, allow_blank=True, allow_null=True)` - Campo legacy opcionalizado.
- `categoria_contable`: `CharField(required=False, allow_blank=True, allow_null=True)` - Campo legacy opcionalizado.
- **NEW**: `cuenta_contable_codigo` y `cuenta_contable_nombre` - Campos `write_only` para recibir metadata del Plan de Cuentas desde UI (formato `[CODIGO] - Nombre`).
- Normalización de porcentajes ocurre en `process_gasto_payload()` del service layer, no en serializer.

---

## 8. Frontend Real del Workspace

### 8.1. Integracion base

`assets_gastos.html` carga en este orden:

- `gastos.api.js`
- `gastos_main.js`
- `gasto_form.js`
- `resolucion_dian_main.js`
- `resolucion_dian_form.js`

### 8.2. gastos_list.html

Componentes activos:

- panel de resumen
- boton `Nuevo Gasto`
- boton `Configurar Resolucion`
- `#grid-gastos`
- `#grid-resoluciones`
- `#offcanvas-container-gastos`

### 8.3. offcanvas_crear.html

Campos reales del formulario de alta:

- `resolucion_dian` via DOM Shield (`select` visible + `hidden input`)
- `fecha`
- `vendedor_nit`
- `vendedor_nombre`
- `subtotal`
- `retefuente_porcentaje`
- `reteica_porcentaje`
- `periodo`
- `categoria_contable`
- `centro_costo`
- `descripcion`
- `adjunto`

Estado real del formulario:

- ya no tiene seccion manual de `ITEMS DEL DOCUMENTO`
- el subtotal es de entrada directa
- los valores calculados de retenciones y total neto se actualizan en vivo
- si no hay resolucion activa, se bloquea el campo subtotal y el boton de guardar

### 8.4. gasto_form.js

Responsabilidades reales:

- cargar offcanvas de creacion
- cargar resoluciones disponibles
- sincronizar DOM Shield de `resolucion_dian`
- calcular retenciones y total neto en tiempo real
- validar seleccion de resolucion antes de guardar
- enviar payload JSON a `/api/v1/gastos/`
- refrescar select de resoluciones tras evento global `resolucionDianActualizada`
- **NEW (v2.61.4):** inicializar formulario tanto en flujo directo como en flujo HTMX

**NEW v2.61.4 - Flag Reading para Anulación:**
- `anular(id)`: Lee flags de estado desde respuesta API anidada en `documento_soporte`.
  - Fallback lógico: `documento_soporte.activo` (si no existe `ds_activo` legacy).
  - Fallback lógico: `documento_soporte.anulado` (si no existe `ds_anulado` legacy).
  - Validación pre-anulación: verifica que `activo === false` antes de proceder (documento debe estar desactivado).
- Esta lógica anidada evita falsos positivos "No se puede anular un documento que está activo" cuando los flags legacy no están presentes en la respuesta.

**NEW v2.61.4 - getCuentaContableSeleccion():**
- Extrae codigo y nombre desde el texto visible del select de Plan de Cuentas.
- Usa regex `/^\[([^\]]+)\]\s*-\s*(.+)$/` para parsear formato `[CODIGO] - Nombre`.
- Retorna objeto con `codigo` y `nombre` para envío en payload API.

Fix de binding HTMX (v2.61.4):

El offcanvas puede llegar por dos rutas: AppGasto.crear() con GESTOR_OFFCANVAS_URL, o directamente via render-offcanvas/crear desde el boton en gastos_list.html. Ambas rutas disparan funciones que ahora convergen en inicializarOffcanvasActual(), la cual enlaza todos los handlers del formulario. Se agrego listener htmx:afterSwap para inicializar cuando HTMX inyecta, y se refuerzo shown.bs.offcanvas para garantizar inicializacion en ambas rutas.

### 8.5. resolucion_dian_form.js

Responsabilidades reales:

- mostrar offcanvas de configuracion de resolucion
- validacion preventiva local de unicidad de `numero_resolucion` contra la tabla actual
- procesar guardado exitoso de resolucion
- disparar `document.dispatchEvent(new CustomEvent('resolucionDianActualizada'))`
- exponer `ver(id)` y `eliminar(id)`

### 8.6. resolucion_dian_main.js

Responsabilidades reales:

- inicializar `#grid-resoluciones`
- consumir `/api/v1/resoluciones-dian/`
- mostrar numero, prefijo, rango, fechas, documentos, estado y acciones
- delegar acciones `ver` y `eliminar`

### 8.7. gastos_main.js

Responsabilidades reales:

- inicializar tabla principal de gastos
- renderizar summary financiero
- verificar estado de resolucion activa
- delegar `ver`, `desactivar` y `anular`
- exponer `AppGastos.refresh()` y `AppGastos.refreshResoluciones()`

Observacion real:

- existe algun residuo menor de compatibilidad en botones y handlers legacy, pero el flujo operativo principal ya corre sobre `AppGasto` y `AppResolucionDIAN`.

### 8.8. Accounting Hook - materializar_asiento_desde_gasto() (NEW v2.61.4)

Ubicacion:

- `apps/tenant/contabilidad/services/asientos_service.py`

Cambios realizados en v2.61.4:

- **Fix de lookup de Proveedor**: Cambio de parámetro de búsqueda `numero_documento=ds.vendedor_nit` a `nit=ds.vendedor_nit`. El modelo `Proveedor` usa el campo `nit` como referencia de identificación, no `numero_documento`.
  
- **Fix de asignación de tercero_nit**: Cambio de `proveedor.numero_documento` a `proveedor.nit` para garantizar integridad de datos en el registro de `MovimientoContable`.
  
- **Fix de FK empresa**: Inyección explícita `mov_data['empresa'] = empresa` antes de `MovimientoContable.objects.create(**mov_data)` en dos ubicaciones críticas (aproximadamente líneas 1121 y 1330). Django no hereda automáticamente el contexto de empresa desde el signal de `post_save`; requiere asignación explícita.

Impacto:

- **Eliminación de warnings en logs**: 
  - `Cannot resolve keyword 'numero_documento'` (ahora usa `nit` correctamente).
  - `{'empresa': ['Este campo no puede ser nulo.']}` (ahora inyecta empresa antes de create).
  
- **Garantía de trazabilidad contable**: Los terceros (proveedores) quedan correctamente identificados en los asientos contables.
  
- **Éxito en creación de asientos**: Post-gasto-creation sin errores de validación o warnings.

---

## 9. Flujos Completos Reales

### 9.1. Crear gasto desde workspace

```text
1. Usuario entra a la pestaña de gastos
2. Usuario hace clic en Nuevo Gasto
3. HTMX GET /api/v1/gastos/render-offcanvas/crear/
4. Backend renderiza offcanvas (sin JS)
5. HTMX inyecta en #offcanvas-container-gastos
6. gasto_form.js capta htmx:afterSwap → inicializarOffcanvasActual()
   - Enlaza handlers (cambio Tipo de Documento, subtotal, retenciones)
   - Carga resoluciones y valores por defecto
7. Bootstrap Offcanvas muestra el formulario
8. gasto_form.js captura shown.bs.offcanvas → refuerza inicializarOffcanvasActual()
9. Si no hay resolucion activa, se bloquea subtotal y guardado
10. Usuario diligencia subtotal directo, porcentajes, clasificacion y datos
11. JS calcula retefuente, reteica y total neto en tiempo real
12. POST /api/v1/gastos/
13. Backend:
    - obtiene empresa del tenant
    - toma resolucion seleccionada o vigente
    - reserva consecutivo atomico
    - calcula totales con Decimal
    - crea DocumentoSoporte
    - crea Gasto
    - crea ItemGasto generico automatico
    - intenta materializar asiento contable
14. Frontend refresca tabla principal y summary
```

### 9.2. Flujo de desactivar y anular

```text
1. Usuario hace clic en Desactivar
2. POST /api/v1/gastos/{id}/desactivar/
3. Service cambia DocumentoSoporte.activo = False
4. Usuario hace clic en Anular
5. POST /api/v1/gastos/{id}/anular/
6. Service valida que activo=False
7. Service cambia DocumentoSoporte.anulado = True y setea fecha_anulacion
8. Frontend refresca tabla y summary
```

### 9.3. Flujo de resolucion DIAN

```text
1. Usuario abre Configurar Resolucion
2. HTMX solicita /api/v1/gastos/render-offcanvas/resolucion/
3. El formulario aplica validacion preventiva local de unicidad de numero_resolucion
4. POST /api/v1/gastos/configurar-resolucion/
5. Backend valida con ResolucionDIANCreateSerializer
6. Service Layer valida unicidad por empresa + numero_resolucion
7. Si vigente=True, desactiva resoluciones vigentes anteriores
8. Persiste la nueva resolucion
9. Frontend dispara resolucionDianActualizada y refresca select/grid
```

### 9.4. Flujo de grid de resoluciones

```text
1. resolucion_dian_main.js consume /api/v1/resoluciones-dian/
2. Tabulator muestra vigencia, rangos, fechas y conteo de documentos
3. Accion Ver abre offcanvas de detalle dinamico
4. Accion Eliminar solo se habilita si conteo_documentos = 0
5. Tras eliminar o crear, se refresca el grid y el estado de resolucion activa
```

### 9.5. Flujo de summary

```text
1. Frontend llama /api/v1/gastos/summary/
2. Service filtra solo activos y no anulados
3. Suma subtotal, retefuente, reteica, total y cantidad
4. Frontend actualiza panel financiero
```

---

## 10. Reglas de Negocio Criticas Validadas

- El tipo documental oficial es `DocumentoSoporte`.
- El consecutivo no se recicla aunque el documento se anule.
- La resolucion debe pertenecer al tenant y estar dentro de fecha para uso operativo.
- La resolucion valida `numero_resolucion` unico por empresa.
- `summary` excluye anulados e inactivos.
- `list` incluye anulados para preservar trazabilidad documental.
- `DocumentoSoporte` es inmutable en los endpoints de edicion del gasto.
- `Gasto` admite reclasificacion controlada sobre campos operativos.
- La contabilidad se intenta materializar automaticamente tras la creacion.
- El borrado fisico no es el flujo normal; el flujo operativo es `desactivar -> anular`.
- El alta de gasto desde workspace ya no depende de multiples items manuales.

---

## 11. Seguridad, Inmutabilidad y Zero Waste

Inmutabilidad real:

- `DocumentoSoporte` concentra los campos legales y monetarios.
- `update/partial_update` rechazan campos de `DocumentoSoporte`.
- `destroy()` no es el camino funcional recomendado para la operacion diaria.

Zero Waste real:

- `qs_list()` usa `select_related()` y `only()`.
- `qs_detail()` baja explicitamente campos de gasto, documento y resolucion.
- El filtrado principal opera por `empresa` del tenant.

DOM Shield real:

- `resolucion_dian` se sincroniza con `hidden input` numerico.
- El `select` visible no es la fuente final del payload.

Zero Trust real:

- El frontend normaliza valores con `parseFloat(...) || 0` y `parseInt(...) || 0`.
- El backend recalcula totales con `Decimal` y no confia en calculos del cliente.

---

## 12. Endpoints Oficiales Alineados

### 12.1. Gastos app API

- `GET /api/v1/gastos/`
- `POST /api/v1/gastos/`
- `GET /api/v1/gastos/{id}/`
- `PUT /api/v1/gastos/{id}/`
- `PATCH /api/v1/gastos/{id}/`
- `DELETE /api/v1/gastos/{id}/`
- `POST /api/v1/gastos/{id}/desactivar/`
- `POST /api/v1/gastos/{id}/anular/`
- `GET /api/v1/gastos/summary/`
- `GET /api/v1/gastos/resoluciones/`
- `GET /api/v1/gastos/resolucion-activa/`
- `GET /api/v1/gastos/gestor-offcanvas/`
- `GET /api/v1/gastos/render-offcanvas/crear/`
- `GET /api/v1/gastos/render-offcanvas/resolucion/`
- `GET /api/v1/gastos/render-offcanvas/detalle/?id=123`
- `POST /api/v1/gastos/configurar-resolucion/`

### 12.2. Resoluciones API

- `GET /api/v1/resoluciones-dian/`
- `POST /api/v1/resoluciones-dian/`
- `GET /api/v1/resoluciones-dian/{id}/`
- `DELETE /api/v1/resoluciones-dian/{id}/`
- `POST /api/v1/resoluciones-dian/{id}/desactivar/`
- `GET /api/v1/resoluciones-dian/activa/`

### 12.3. Core API

- `GET /api/v1/core/v1/gastos/operativos/`
- `POST /api/v1/core/v1/gastos/operativos/`
- `GET /api/v1/core/v1/gastos/operativos/{id}/`
- `PUT /api/v1/core/v1/gastos/operativos/{id}/`
- `PATCH /api/v1/core/v1/gastos/operativos/{id}/`
- `POST /api/v1/core/v1/gastos/operativos/{id}/desactivar/`
- `POST /api/v1/core/v1/gastos/operativos/{id}/anular/`
- `GET /api/v1/core/v1/gastos/operativos/summary/`
- `GET /api/v1/core/v1/gastos/resoluciones-dian/`
- `POST /api/v1/core/v1/gastos/resoluciones-dian/`
- `GET /api/v1/core/v1/gastos/resoluciones-dian/activa/`

---

## 13. Residuales y Compatibilidades

Hallazgos residuales reales:

- `GastoWorkspaceSerializer` aun acepta `items` por compatibilidad de integracion, aunque el workspace no los envia.
- Existe al menos un template legado fuera de `partials/` que no es la ruta oficial del flujo actual.
- El endpoint `POST /api/v1/gastos/configurar-resolucion/` sigue activo por compatibilidad HTMX, aunque semanticamente `POST /api/v1/resoluciones-dian/` es el endpoint propietario.

Estos residuales no gobiernan el flujo principal actual, pero siguen existiendo como superficie de compatibilidad o deuda tecnica controlada.

## 13.1. Cambios Realizados en v2.61.4

**Refactorización Completa del Módulo Gastos: Priorización de Plan de Cuentas (Fecha: 2026-03-22)**

El módulo de gastos fue refactorizado integralmente en v2.61.4 para que el Plan de Cuentas (`CuentaContable`) sea el eje obligatorio de clasificación contable, optacionalizando campos legacy (`centro_costo`, `categoria_contable`).

### 13.1.1. Cambios en Modelos (`apps/tenant/gastos/models.py`)

**Gasto Model:**
- `cuenta_contable_uuid` (NEW): Campo `UUIDField` con `blank=False` para enforcement de Plan de Cuentas obligatorio.
  - Establece soberanía contable centralizada.
  - Todos los gastos creados desde v2.61.4 DEBEN tener un Plan de Cuentas válido.
  - Mapea directamente a `CuentaContable.uuid` en la aplicación `contabilidad`.

- `centro_costo`: Cambio de `blank=False` a `null=True, blank=True`.
  - Campo legacy opcionalizado.
  - Soporta workflows sin datos de centros de costo.

- `categoria_contable`: Cambio de `blank=False` a `null=True, blank=True`.
  - Campo legacy opcionalizado.
  - Soporta workflows sin datos de categorías contables.

**Impacto en migraciones:**
- Migración `0007_alter_gasto_cuenta_contable_uuid` creada para todos los tenants.
- Asignación default a gastos existentes sin `cuenta_contable_uuid` (si aplica).
- Índice DB en `cuenta_contable_uuid` para optimización de queries.

### 13.1.2. Cambios en Servicios (`apps/tenant/gastos/services/services.py`)

**Normalización de Porcentajes (NEW):**

Problema diagnosticado:
- UI envía porcentajes en formato human-readable (4, 0.966).
- DB almacena en formato choice (0.04, 0.00966).
- Serializer rechazaba valores no presentes en `choices`.

Funciones nuevas implementadas:

```python
def _normalizar_porcentaje_choice_retefuente(value):
    """Mapeo: 4 -> 0.04, 6 -> 0.06, 10 -> 0.10, 11 -> 0.11, 0 -> 0.00"""
    mapeo = {4: '0.04', 6: '0.06', 10: '0.10', 11: '0.11', 0: '0.00'}
    return mapeo.get(int(value), '0.00')

def _normalizar_porcentaje_choice_reteica(value):
    """Mapeo: 0.966 -> 0.00966, 0.69 -> 0.0069, 1.104 -> 0.01104, 0 -> 0.00"""
    mapeo = {0.966: '0.00966', 0.69: '0.0069', 1.104: '0.01104', 0: '0.00'}
    return mapeo.get(float(value), '0.00')
```

- Aplica en `process_gasto_payload()` ANTES de serialization.
- Convierte valores UI a formato choice automáticamente.
- Entrada opcional en API (si no se envía, se definen a 0).

**Orchestration Pattern - Payload Merge:**

Cambio en `ejecutar_operacion_gasto()`:

```python
# Antes: return {payload}  # Perdía data_original
# Después:
return {**data_original, **payload_normalized}  # Preserva todos los campos
```

- Garantiza que todos los campos enviados en la solicitud llegan al serializer.
- Normalización aplicada sin pérdida de datos.
- Pre-validación sin efecto secundario en servidor.

**Validación de Plan de Cuentas:**

- `process_gasto_payload()` consulta `ContabilidadBusinessService.obtener_cuentas_gasto_disponibles(empresa)`.
- Valida que `cuenta_contable_uuid` exista en el catálogo del tenant.
- Si no existe, retorna error 400 `Bad Request` con detalle de validación.
- Delega responsabilidad a Service Layer, no a queries directas.

### 13.1.3. Cambios en Serializers (`apps/tenant/gastos/api/serializers.py`)

**GastoWorkspaceSerializer:**

- `retefuente_porcentaje`: Aumentado `decimal_places` de 3 a 5.
  - Soporta valores como 0.04, 0.06, 0.10, 0.11.
  - Normalización automática en service layer.

- `reteica_porcentaje`: Aumentado `decimal_places` de 3 a 5 (CRÍTICO).
  - Soporta precisión de 0.00966 (0.966%).
  - Evita truncamiento a 0.009 con decimal_places=3.
  - Normalización automática en service layer.

- `retefuente_porcentaje`, `reteica_porcentaje`: `required=False`.
  - Entrada opcional en API.
  - Defaults a 0 en backend si no se envía.

- `centro_costo`, `categoria_contable`: `required=False`, `allow_blank=True`, `allow_null=True`.
  - Compatibilidad con workflows sin datos legacy.
  - No bloquean creación de gasto.

- (NEW) `cuenta_contable_codigo`, `cuenta_contable_nombre`: `write_only` fields.
  - Reciben metadata desde UI: `[CODIGO] - Nombre`.
  - Procesados en service layer.
  - No persistidos; solo para context.

**Impacto operativo:**
- Serializer ya no valida presencia de campos legacy.
- Validación delegada a service layer.
- Incrementa flexibilidad sin comprometer integridad.

### 13.1.4. Cambios en Frontend (`apps/tenant/core/static/core/js/gastos/gasto_form.js`)

**Función getCuentaContableSeleccion() (NEW):**

```javascript
function getCuentaContableSeleccion() {
    const opcion = document.getElementById('select-cuenta-contable').selectedOptions[0];
    const texto = opcion.textContent.trim();
    const regex = /^\[([^\]]+)\]\s*-\s*(.+)$/;
    const match = texto.match(regex);
    if (match) {
        return { codigo: match[1], nombre: match[2] };
    }
    return null;
}
```

- Parsea texto visible del select: `[CODIGO] - Nombre`.
- Extrae `codigo` y `nombre`.
- Envía en payload: `cuenta_contable_codigo`, `cuenta_contable_nombre`.
- Asociado a `cuenta_contable_uuid` del option value numérico.

**Validación de Campos Opcionales:**

- Removidas validaciones bloqueantes para `centro_costo`, `categoria_contable`.
- Log: `[gasto:form] Omitiendo validación de campos opcionales (CC/Cat Legacy).`
- Permite creación sin llenar campos legacy.
- Ui-trust: campos no-required visualmente desindicados.

**Flag Reading para Anulación (FIX):**

Problema diagnosticado:
- Frontend leía `ds_activo`, `ds_anulado` legacy fields.
- API response anidaba flags en `documento_soporte` (nested).
- Falsos positivos: "No se puede anular documento activo" incluso después de desactivar.

Solución implementada:

```javascript
function anular(id) {
    const documento_soporte = respuesta.documento_soporte || {};
    const esActivo = documento_soporte.activo !== false;  // Lee nested flag
    if (esActivo) {
        UIManager.notifyError(...);
        return;
    }
    // Proceder a anular...
}
```

- Fallback lógico: espera `documento_soporte.activo` nested.
- Si no existe, asume default `true` (seguro).
- Anulación solo si `activo === false`.
- Validación en backend aún configura este estado.

### 13.1.5. Cambios en Accounting (`apps/tenant/contabilidad/services/asientos_service.py`)

**materializar_asiento_desde_gasto() - Fixes:**

Problema 1: Lookup de Proveedor fallaba.
```python
# Antes:
proveedor = Proveedor.objects.get(numero_documento=ds.vendedor_nit)  # Campo no existe

# Después:
proveedor = Proveedor.objects.get(nit=ds.vendedor_nit)  # Campo correcto
```

Problema 2: MovimientoContable rechazaba FK empresa nula.
```python
# Antes:
MovimientoContable.objects.create(**mov_data)  # empresa=None en mov_data

# Después:
mov_data['empresa'] = empresa  # Inyección explícita
MovimientoContable.objects.create(**mov_data)
```

- Dos ubicaciones corregidas (líneas ~1121 y ~1330).
- Eliminación de warnings en logs.
- Garantía de trazabilidad: terceros correctamente identificados.
- Asientos contables creados exitosamente post-gasto.

### 13.1.6. Cambios en Template (`apps/tenant/core/templates/tenant/core/partials/gastos/documento_soporte/offcanvas_crear.html`)

**Categoría Contable - Visual Signal:**

- Removido asterisco de etiqueta (ya no requerido visualmente).
- Campo `select-categoria-contable` sin atributo `required`.
- Ui-trust: indica al usuario que es field opcional.

**Plan de Cuentas - Nuevo Required:**

- Campo `select-cuenta-contable` marcado como `required`.
- Asterisco presente en etiqueta.
- Bloquea envío si no está seleccionado.
- Enforce de soberanía contable en UI.

### 13.1.7. Fix de Inicialización HTMX en gasto_form.js

**Problema diagnosticado:**
- Botón "Nuevo Gasto" → HTMX GET → `render-offcanvas/crear/`
- Offcanvas inyectado dinámicamente, pero handlers JS no se enlazan.
- Change handler de Tipo Documento → no ejecuta.
- Cascada Proveedor → se queda en disabled state.

**Solución implementada:**

1. Nueva función `inicializarOffcanvasActual()` que centraliza toda inicialización.
2. Listener `htmx:afterSwap` en `#offcanvas-container-gastos` → dispara inicialización.
3. Refuerzo con `shown.bs.offcanvas` → failsafe en ambas rutas.
4. Exposición pública: `w.AppGasto.inicializarOffcanvasActual()`.

**Impacto operativo:**
- Dos rutas de apertura (AppGasto.crear + HTMX directo) convergen en punto único.
- Cascada Proveedor funciona en ambas rutas.
- Código mínimo, sin cambios API.
- Mantenibilidad mejorada.

---

## 14. Estado Final

La documentacion oficial del modulo `gastos` queda alineada al estado real del repositorio a fecha 2026-03-22.

Conclusion operativa:

- El modulo gira alrededor de `DocumentoSoporte` como tipo documental DIAN.
- `Gasto` es la capa operativa mutable y hoy ya conversa con contabilidad.
- El workspace oficial corre con HTMX + Offcanvas + Tabulator y estructura FSD modular.
- El alta de gasto fue simplificada a subtotal directo con calculo centralizado y item generico automatico.
- La gestion de resoluciones ya incluye unicidad, reactividad entre modulos y acciones operativas completas en la grilla.

---

**Fin del documento**  
**Ultima actualizacion:** 2026-03-22 - v2.61.4 Complete Refactoring  
**Version del sistema:** 2.61.4  
**Estado:** Sincronizado con models, services, api, core facade, accounting hooks y workspace actuales. Refactorización de Plan de Cuentas como eje obligatorio completada y validada.
