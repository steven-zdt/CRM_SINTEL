# UI_UX_INVENTARIO_UI — SINTEL ERP

**Fecha:** 2026-09-17. **Rama:** `feat/onboarding-cookie`. **Fase:** 8 de `UI_UX_MASTER_MISSION_V2_59_FASES.md`.

Inventario real de la UI de las 15 apps de negocio tenant: APP → RUTA → SUBMÓDULO → TAB → LISTADO →
DETALLE → CREAR → EDITAR → ELIMINAR → ACCIONES ESPECIALES, distinguiendo explícitamente **MODELO
EXISTE** (hay clase en `models.py`) de **UI EXISTE** (hay ruta/template real para ese modelo).

**Metodología:** auditoría estática de solo lectura — `urls.py`, `api/urls.py`, `api/viewsets.py`,
`models.py` y los templates/JS de cada app. No requiere Capa 1 (navegador real, `BLOCKED` — Fase 12);
es exactamente el tipo de fase que sí puede ejecutarse sin ese desbloqueo. Cada fila es trazable a un
archivo real citado por la auditoría; ninguna fila fue inventada.

**Cómo leer "UI existe":** `Sí` = hay ruta/template/JS real que expone el modelo al usuario. `Parcial`
= existe pero incompleto (falta alguna operación CRUD, o es de solo lectura embebida sin CRUD propio).
`No` = el modelo y/o su API existen pero no hay ninguna forma de alcanzarlos desde la UI — esto es el
hallazgo más valioso de esta fase, no un detalle menor.

---

## Clientes

| Submódulo | Ruta | Tabs | Listado | Detalle | Crear | Editar | Eliminar | Acciones especiales | Modelo existe | UI existe |
|---|---|---|---|---|---|---|---|---|---|---|
| Cliente | `/clientes/` (`clientes:cliente-list`), API `/api/v1/clientes/` | Sí (Clientes/Contactos/Cartera) | Sí (django-tables2+HTMX) | Sí (offcanvas, tabs Info/Facturas) | Sí (offcanvas) | Sí (offcanvas) | Sí (hard delete, requiere `activo=False` antes) | — | Sí | Sí |
| ContactoCliente | API `/api/v1/clientes/contactos/` | — | Sí (gestor embebido en offcanvas del cliente) | Sí | Sí (con template duplicado, ver `UI_UX_PATRONES_VISUALES.md`) | Sí | Sí | Marcar Principal / Representante Legal | Sí | Sí |
| Cartera (CxC) | API `/api/v1/clientes/cartera/` | Tab "Cartera" | Sí (grid JS, no django-tables2) | No (offcanvas de detalle propio) | Sí | No hay edición general | Sí | Registrar Abono, Notas de seguimiento, filtro Vencidas, KPIs inline | Sí | Sí |
| CarteraNota | Sub-recurso `.../cartera/{uuid}/notas/` | — | Sí (embebida) | — | Sí (mini-form embebido) | No (inmutable por diseño) | No (append-only) | — | Sí | Sí (sub-widget) |

## Proveedores

| Submódulo | Ruta | Tabs | Listado | Detalle | Crear | Editar | Eliminar | Acciones especiales | Modelo existe | UI existe |
|---|---|---|---|---|---|---|---|---|---|---|
| Proveedor | `/proveedores/` | Sí (Directorio/CxP/Representantes) | Sí (django-tables2+HTMX) | No hay offcanvas de detalle dedicado (se reutiliza `offcanvas_form.html` en modo lectura, no confirmado al 100%) | Sí | Sí | Sí | — | Sí | Sí |
| CuentasPagar (CxP) | API `/api/v1/proveedores/cuentas-pagar/` | Tab "Cuentas por Pagar" | Sí (django-tables2+HTMX) | Sí (offcanvas modo "ver") | No (se materializa desde Factura, Pull Model) | No (solo abono) | Sí (guard: rechaza con pagos/factura) | Registrar Abono | Sí | Sí |
| Representante | API `/api/v1/proveedores/representantes/` | Tab "Representantes" + sub-tabla en detalle de Proveedor | **3 implementaciones distintas de tabla para la misma entidad** (ver Hallazgos) | No hay offcanvas de detalle dedicado | Sí | Sí | Sí (guard sobre principal) | Marcar Principal | Sí | Sí (con inconsistencia grave de implementación) |

## Compras

| Submódulo | Ruta | Tabs | Listado | Detalle | Crear | Editar | Eliminar | Acciones especiales | Modelo existe | UI existe |
|---|---|---|---|---|---|---|---|---|---|---|
| OrdenCompra | `/compras/` | Sí (Órdenes/Plantillas) | Sí (django-tables2+HTMX, KPI cards hand-rolled) | Sí (offcanvas) | Sí (offcanvas) | Sí (offcanvas) | Sí | Cambiar Estado, Vincular Factura manual, Siguiente Consecutivo | Sí | Sí |
| ItemOrdenCompra | Sub-recurso embebido | — | Embebido | Embebido | Embebido (JS dinámico) | Embebido | Embebido (quitar fila) | — | Sí | Sí (correcto por diseño) |
| PlantillaOrdenCompra | Tab "Plantillas" | Tab dentro de Compras | Sí (django-tables2+HTMX) | No hay offcanvas de detalle dedicado | Sí | Sí | Sí | — | Sí | Sí |
| RecepcionCompra / RecepcionCompraItem (F21) | API `/api/v1/compras/recepciones/` (crear, confirmar, anular) | — | **No existe ningún template** | No | No (API-only) | No | No | Confirmar/Anular solo vía API — el propio código documenta la omisión deliberada ("`RecepcionCompraViewSet.render_offcanvas_* deliberadamente no existe`") | Sí | **No** — hueco modelo-sin-UI confirmado |

## Ventas

| Submódulo | Ruta | Tabs | Listado | Detalle | Crear | Editar | Eliminar | Acciones especiales | Modelo existe | UI existe |
|---|---|---|---|---|---|---|---|---|---|---|
| Venta | `/api/v1/ventas/` | No (filtros por estado) | Sí (django-tables2+HTMX) | Sí (offcanvas) | Sí (offcanvas) | Sí (mismo offcanvas, modo edición) | **API existe (`destroy`) pero SIN botón en la UI** — nunca invocado desde el JS | Anular (con botón); Vincular factura (con botón); **Facturar DIAN es código muerto** — el botón fue removido por bloqueo regulatorio pero el JS (`venta_editor.js:313,367`) sigue presente sin trigger | Sí | Parcial (falta Eliminar; Facturar-DIAN deshabilitado a propósito) |
| ItemVenta | Sub-recurso embebido | — | — | Incluido en detalle | Incluido en form | Incluido en form | Sí (`.btn-eliminar-item`) | — | Sí | Sí (embebido, correcto) |
| ResolucionFacturacion (DIAN) | `/api/v1/ventas/resoluciones/` | No | Sí (grid Tabulator) | No | Sí | Sí | Sí | — | Sí | Sí (CRUD completo) |

## Cotizaciones

| Submódulo | Ruta | Tabs | Listado | Detalle | Crear | Editar | Eliminar | Acciones especiales | Modelo existe | UI existe |
|---|---|---|---|---|---|---|---|---|---|---|
| Cotizacion | `/api/v1/cotizaciones/` | No (filtros por estado) | Sí (grid Tabulator) | Sí (offcanvas) | Sí (editor completo) | Sí (mismo editor) | Sí (modal) | **9 de 11 acciones de backend inalcanzables desde la UI**: `recalcular`, `historial`, `volver-a-borrador`, `aprobar`, `rechazar`, `archivar`, `convertir-a-venta`, `facturar-venta`, `convertir-a-proyecto` — solo exportar/generar PDF están conectados | Sí | Sí, pero el flujo de estados es en la práctica inalcanzable |
| ConfiguracionCotizacion ("Plantilla") | `/api/v1/cotizaciones/configuracion/` | No | Sí (offcanvas) | Sí | Sí | Sí | Sí | — | Sí | Sí (CRUD completo) |
| Producto (catálogo propio) | `/api/v1/cotizaciones/productos/` | No | Vía picker embebido | No | Sí | Sí | **API existe pero SIN botón de eliminar en la UI** | — | Sí | Parcial (falta Eliminar) |
| Servicio (catálogo propio) | `/api/v1/cotizaciones/servicios/` | No | Vía picker embebido | No | Sí | Sí | **API existe pero SIN botón de eliminar en la UI** | — | Sí | Parcial (falta Eliminar) |
| CotizacionEstadoConfig | — | — | — | — | — | — | — | — | Sí | **No — ni ViewSet ni referencia en templates/JS** |
| CotizacionHistorialEstado | Solo vía `@action historial` | — | — | — | — | — | — | — | Sí | No (acción de API sin UI) |
| `offcanvas_crear/editar_cotizacion.html` | — | — | — | — | — | — | — | — | N/A | **OBSOLETO** — confirmado huérfano por comentario propio del código; el flujo real usa `editor_cotizacion.html` |

## Inventario

| Submódulo | Ruta | Tabs | Listado | Detalle | Crear | Editar | Eliminar | Acciones especiales | Modelo existe | UI existe |
|---|---|---|---|---|---|---|---|---|---|---|
| CategoriaItem | `/api/v1/inventario/categorias/` | Tab "Categorías" | Sí (django-tables2) | No | Sí | Sí | Sí | Resumen | Sí | Sí |
| Producto | `/api/v1/inventario/productos/` | Tab "Productos" | Sí (django-tables2 + KPIs) | No offcanvas propio (vía Kardex) | Sí | Sí | Sí | Ver Kardex, Stock, Ingesta masiva (sin UI confirmada) | Sí | Sí |
| Servicio | `/api/v1/inventario/servicios/` | Tab "Servicios" | Sí (django-tables2) | Vía Historial | Sí | Sí | Sí | Historial de servicio, Vincular a proyecto | Sí | Sí |
| ActivoFijo | `/api/v1/inventario/activos/` | Tab "Activos Fijos" | Sí (django-tables2 + KPIs) | No offcanvas propio | Sí | Sí | Sí | `list-all` (sin UI confirmada) | Sí | Sí |
| MovimientoInventario (Kardex) | `/api/v1/inventario/movimientos/` | Tab "Movimientos Recientes" | Sí (grid **Tabulator**, fuera de alcance Fase 5-BIS a propósito) | Timeline unificado | Sí | No confirmado | No confirmado | Timeline | Sí | Sí (patrón distinto al resto) |
| **TrasladoInventario** | `/api/v1/inventario/traslados/` (CRUD + aprobar/enviar/recibir/cancelar) | — | — | — | — | — | — | — | Sí | **NO EXISTE — cero templates, cero tab, cero JS.** No hay pestaña "Traslados" en `list_inventario.html` |

## Facturas

| Submódulo | Ruta | Tabs | Listado | Detalle | Crear | Editar | Eliminar | Acciones especiales | Modelo existe | UI existe |
|---|---|---|---|---|---|---|---|---|---|---|
| Factura (venta/compra) | `/facturas/`, API `/api/v1/facturas/` | Sí (Ventas/Compras) | Sí (django-tables2+HTMX) | Sí (2 templates distintos para lo mismo, ver Hallazgos) | Sí (drag&drop XML masivo) | Sí (5 tabs: General/Emisor-Receptor/Comercial/Ítems/DIAN) | Sí | Importar XML UBL masivo, sincronizar buzón, historial de ingestas, crear-from-dto, ver XML/ApplicationResponse | Sí | Sí |
| ItemFactura | Sub-recurso, API `items-factura/` | — | Embebido | Embebido | Vía XML (no manual) | No editable manualmente | No expuesto | — | Sí | Parcial (solo lectura embebida) |
| NotaCredito / ItemNotaCredito | API `notas-credito/` | — | No | No | No (vía XML CreditNote) | No | No | Badge "NC" es el único indicio visual | Sí | **No — hueco modelo-sin-UI** |
| MailIngestionRun / DocumentProcessing | Client-rendered, sin template propio | No | Sí | Sí | Al disparar "Sincronizar Buzón" | No | No | Ingesta asíncrona por correo | Sí | Sí (client-rendered, sin `.html` propio) |
| MailInboxState | Ninguna | — | — | — | — | — | — | Estado interno de buzón | Sí | **No — backend-only** |
| FacturaAnexos | Ninguna ruta directa | — | — | — | — | — | — | Se actualiza automáticamente en upload-ubl | Sí | **No UI directa** |
| TransmisionFactura | Ninguna | — | — | — | — | — | — | Trazabilidad DIAN | Sí | **No template propio** |
| FacturaImpuesto | Ninguna | — | Sí (embebido, "Desglose de Impuestos") | Sí (embebido) | No | No | No | — | Sí | Sí (embebido, sin CRUD) |

## Gastos

| Submódulo | Ruta | Tabs | Listado | Detalle | Crear | Editar | Eliminar | Acciones especiales | Modelo existe | UI existe |
|---|---|---|---|---|---|---|---|---|---|---|
| DocumentoSoporte (Gasto) | `/gastos/`, API `/api/v1/gastos/` | Sí (Gastos/Resoluciones DIAN) | Sí (django-tables2+HTMX) | Sí (extiende `_base_offcanvas.html`) | Sí | Sí | Sí | Anular, materializar desde DTO (ya no fabrica datos falsos — ver `UI_UX_FINDINGS.md` GASTOS-01) | Sí | Sí |
| ResolucionDIAN | API `/api/v1/gastos/resoluciones/` | Sub-tab | Sí (django-tables2) | No | Sí (crear/editar combinados) | Sí (mismo template) | No hay botón eliminar, solo **Desactivar** | Desactivar resolución vigente | Sí | Sí |

## Bancos

| Submódulo | Ruta | Tabs | Listado | Detalle | Crear | Editar | Eliminar | Acciones especiales | Modelo existe | UI existe |
|---|---|---|---|---|---|---|---|---|---|---|
| CuentaBancaria | API `cuentas/` | Sí (Cuentas/Extractos) | Sí (django-tables2) | **No existe** offcanvas de detalle | Sí | Sí | Sí | — | Sí | Sí (falta detalle) |
| ExtractoBancario | API `extractos/` | Sub-tab | Sí (django-tables2) | Sí (panel split transacciones+conciliación) | Sí (importar XLS/XLSX, no formulario manual) | **No existe** (extracto inmutable tras importar, por diseño) | Sí | Procesar (importar), Conciliar | Sí | Sí (falta editar, por diseño) |
| TransaccionBancaria | Sub-recurso, API `transacciones/` | No | Embebida en detalle de extracto | Embebida | Vía "Procesar" del extracto | No | No expuesto | Filtros Ingreso/Egreso/Conciliado | Sí | Sí (embebida) |
| MovimientoBancarioAplicacion | Sub-recurso, API `aplicaciones/` | No | Embebida (panel "Aplicaciones") | Embebida | Sí (embebido) | No | Implícito vía "Quitar" | Conciliación multi-concepto, botón "Sugerir" (matching automático) | Sí | Sí (embebida) |

## Contabilidad

| Submódulo | Ruta | Tabs | Listado | Detalle | Crear | Editar | Eliminar | Acciones especiales | Modelo existe | UI existe |
|---|---|---|---|---|---|---|---|---|---|---|
| CuentaContable (PUC) | `/contabilidad/cuentas/` | No | Sí | Sí (offcanvas) | Sí | Sí | Sí | Sincronizar desde catálogo NIIF, filtro cuentas-proveedor | Sí | Sí |
| AsientoContable | `/contabilidad/asientos/` | No | Sí | Sí (offcanvas) | Sí | Sí | Sí | Aprobar (BORRADOR→APROBADO), reportes (balance de prueba, estado de resultados) | Sí | Sí |
| MovimientoContable | Solo API, sin ruta UI propia | No | No (embebido en Asiento) | No | No (se crea dentro del form de Asiento) | No | Sí (override) | — | Sí | Parcial (gestionado inline) |
| PeriodoContable | `/contabilidad/periodos/` | No | Sí | Sí (offcanvas) | Sí | Sí | Sí | Cerrar (ABIERTO→CERRADO) | Sí | Sí |
| TipoComprobante | Solo API, sin ruta UI | No | No | No | No | No | Sí (estándar DRF) | Selector embebido en form de Asiento | Sí | **No CRUD propio** |
| CatalogoMaestroNIIF | Solo API, sin templates | No | No | No | No | No | No | `buscar-por-tipo`; se puebla vía management command | Sí | **No — solo FK de referencia** |
| DocumentosPendientes | Templates propios, sin modelo dedicado | No | Sí | No | No | No | No | render-offcanvas (contabilizar), contabilizar-manual, asistente-IA | No (vista agregadora) | Sí |
| LibroDiario | API solo lectura | No | Sí | No | No | No | No | Reporte de solo lectura | No (es un reporte) | Sí (solo listado) |
| Retencion | UI "solo lectura" explícita | No | Sí | No | No | No | No | Consulta por tercero/documento (integración Pull Model) | Sí | Sí (por diseño, sin CRUD) |
| ConfiguracionRetenciones | Solo API, sin templates | — | No | No | No | No | No | — | Sí | **No** |
| PlantillaContable + LineaPlantilla | `/contabilidad/plantillas/` | No | Sí | Sí (offcanvas) | Sí | Sí | Sí | Agregar/eliminar línea (inline) | Sí | Sí |
| ImpuestoDocumento | Sin ViewSet ni ruta | — | — | — | — | — | — | — | Sí (solo interno) | **No** |
| Reportes (Balance de Prueba, Estado de Resultados) | `/contabilidad/reportes/` | N/A | N/A | N/A | N/A | N/A | N/A | Generación de reportes financieros | No (derivado) | Sí |

## Empleados

| Submódulo | Ruta | Tabs | Listado | Detalle | Crear | Editar | Eliminar | Acciones especiales | Modelo existe | UI existe |
|---|---|---|---|---|---|---|---|---|---|---|
| Empleado | `/empleados/` | No | Sí | Sí (+ historial de nóminas) | Sí | Sí | Sí (hard delete solo si `RETIRADO`) | Retiro controlado (vía `PATCH estado=RETIRADO`, cancela contratos activos) | Sí | Sí |
| Contrato | API `contratos/` | No | Sí | Sí (offcanvas) | Sí | Sí | Sí (estándar) | Cancelar, Simular liquidación | Sí | Sí |
| Devengo (Nómina) | Master-Detail | Sí | Sí | Sí (solo lectura) | Sí | No (inmutable, 405 en update) | Sí (override) | Anular, preview-cálculo, PDF desprendible | Sí | Sí — **bug de código confirmado: `render_offcanvas_crear` definido 2 veces en `DevengoViewSet` con el mismo `url_path`, la segunda sobreescribe la primera silenciosamente** |
| LiquidacionPrestacion | Master-Detail | Sí | Sí | Sí (offcanvas) | Sí | No (inmutable tras crear) | Sin override visible | Simular, PDF | Sí | Sí |
| PeriodoNomina | API `periodos-nomina/` | No | Sí | Sí (render-offcanvas GET) | Sí | No (avanza solo por acciones) | No (se anula, no se borra) | Máquina de estados completa: preliquidar/enviar-revisión/rechazar/aprobar/marcar-pagado/cerrar/anular/bloquear/desbloquear | Sí | Sí |
| ResolucionDIAN (Empleados) | API `resoluciones-dian/` | No | Sí | No | Sí | No (sin template) | Sí (estándar) | — | Sí | Sí (solo crear/listar) |
| TransmisionNominaDIAN | Sin ViewSet ni ruta | — | — | — | — | — | — | — | Sí (interno) | **No** |

## Proyectos

| Submódulo | Ruta | Tabs | Listado | Detalle | Crear | Editar | Eliminar | Acciones especiales | Modelo existe | UI existe |
|---|---|---|---|---|---|---|---|---|---|---|
| Proyecto | `/proyectos/` | No | Sí (django-tables2) | No hay offcanvas de solo-detalle (reutiliza `offcanvas_form.html`) | Sí | Sí | Sí | Avanzar fase (BORRADOR→INICIO→PLANEACION→EJECUCION→CIERRE), Vincular proyecto | Sí | Sí (falta detalle de solo lectura dedicado — rompe patrón FSD del resto de la app) |
| ItemPresupuestoProyecto | Sub-recurso embebido | No | Embebido | No | Embebido | Embebido | Embebido | — | Sí | Sí (embebido, correcto) |
| TareaDiariaProyecto | API `tareas-diarias/` completa (incl. `cambiar-estado`) | — | No | No | No | No | No | API completa pero sin consumidor JS/template real | Sí | **No — API sin UI** |
| TareaCorta | API `tareas-cortas/` | No | Sí | No (panel único) | Sí (panel) | Sí (mismo panel) | Sí (estándar) | Cambiar estado, menú de tareas | Sí | Sí |
| AsignacionPersonal | Sin ViewSet ni ruta | — | — | — | — | — | — | — | Sí (solo modelo) | **No** |
| PedidoProyecto | Sin ViewSet ni ruta | — | — | — | — | — | — | — | Sí (solo modelo) | **No** |
| ItemPedido | Sin ViewSet ni ruta (depende de PedidoProyecto) | — | — | — | — | — | — | — | Sí (solo modelo) | **No** |

## Empresa

| Submódulo | Ruta | Tabs | Listado | Detalle | Crear | Editar | Eliminar | Acciones especiales | Modelo existe | UI existe |
|---|---|---|---|---|---|---|---|---|---|---|
| Empresa (singleton) | `/api/v1/empresas/` + tab "Datos de Empresa" | Sí (Datos/Sedes/Áreas) | Sí | No (solo editar) | No (bloqueado salvo flag interno; UI usa `PATCH /api/v1/core/empresa/`) | Sí (offcanvas) | **API existe (`DELETE`, solo STAFF/ADMIN) pero SIN botón en la UI** | — | Sí | Sí |
| Sede | `/api/v1/empresas/sedes/` | Tab "Sedes" | Sí | No | Sí (offcanvas) | Sí | Sí | — | Sí | Sí |
| Area | `/api/v1/empresas/areas/` | Tab "Áreas" | Sí | No | Sí (offcanvas, con selector de Sede) | Sí | Sí | — | Sí | Sí |
| MailInboxConfig | `/api/v1/empresas/mail-inbox-config/` | Sección propia (no tab independiente) | Sí | No | Sí (offcanvas) | Sí | Sí | Probar Conexión (con y sin guardar) | Sí | Sí |

## Perfil

| Submódulo | Ruta | Tabs | Listado | Detalle | Crear | Editar | Eliminar | Acciones especiales | Modelo existe | UI existe |
|---|---|---|---|---|---|---|---|---|---|---|
| TenantProfile / Perfil | `/api/v1/perfil/perfiles/` | No | Sí (django-tables2) | Sí (offcanvas) | Sí (offcanvas, condicionado a `can_create_profiles`) | Sí (offcanvas) | Sí (con guards: no auto-eliminación, no admin primario) | Asignar Rol (botón dedicado en tabla + select embebido en edición — 2 caminos de UI para la misma acción); `/me/` autoedición | Sí | Sí |
| Departamento | `/api/v1/perfil/departamentos/` (CRUD completo en API) | — | **No hay listado/tabla propia** | No | No hay offcanvas propio | No hay offcanvas propio | No hay botón en UI | — | Sí (modelo + API completos) | **No — solo usado como `<select>` embebido en offcanvas de Perfil** |
| Sedes/Áreas asignadas (M2M) | Selects multi dentro del offcanvas de Perfil | — | N/A (subcampo) | — | — | Se edita junto con "Editar Perfil" | — | Filtrado dinámico Área según Sede | Sí (M2M) | Sí (embebido) |

## Dashboard (solo lectura)

| Submódulo | Ruta | Tabs | Listado | Detalle | Crear | Editar | Eliminar | Acciones especiales | Modelo existe | UI existe |
|---|---|---|---|---|---|---|---|---|---|---|
| Métricas consolidadas | `GET /api/v1/dashboard/` (+ alias `/metricas/`) | No | Sí (widgets) | N/A | N/A | N/A | N/A | Botón "Actualizar" (solo re-fetch client-side, no invalida caché backend) | `SnapshotMetricaDiaria` (histórico Celery Beat) | Sí |
| Widgets (Facturas/Clientes/Empleados/Inventario/Proveedores/Gastos/Proyectos) | Extractores por dominio | — | Sí (cards) | No | N/A | N/A | N/A | — | No (leen de otras apps vía extractor) | Sí |
| KPIs por Sede | `GET /api/v1/dashboard/kpis-por-sede/` | — | Sí (tabla) | No | N/A | N/A | N/A | Filtro por rango de fechas | Igual (agregados) | Sí |
| Invalidar caché (admin) | `POST /api/v1/dashboard/invalidar-cache/` | — | N/A | N/A | N/A | N/A | N/A | **Endpoint + wrapper JS existen, pero no está enlazado a ningún botón/UI** | N/A | **No — API/JS sin UI que la dispare** |
| Endpoints legacy (`/data/`, `/summary/`, `/kpis/`, `/quick-actions/`) | `dashboard/api/views.py` | — | — | — | — | — | — | Marcados DEPRECADOS en código, sin consumidor activo aparente en `dashboard_main.js` | N/A | Presumiblemente sin consumidor activo |

---

## Hallazgos notables (consolidado de las 15 apps)

### A. Modelos con API completa pero cero UI ("huérfanos")

- **Proyectos:** `AsignacionPersonal`, `PedidoProyecto`, `ItemPedido` — sin ViewSet, sin ruta, sin
  template. Ni siquiera aparecen en `api/urls.py`. El gap más grande de todo el inventario.
- **Proyectos:** `TareaDiariaProyecto` — API completa (incluida `cambiar-estado`) pero sin ningún
  consumidor JS/template; la URL solo aparece listada en `proyectos.api.js`, nunca invocada.
- **Inventario:** `TrasladoInventario` — CRUD completo + flujo `aprobar/enviar/recibir/cancelar`, cero
  templates, cero tab, cero JS. Solo aparece en tests de integración contable de otra app.
- **Compras:** `RecepcionCompra`/`RecepcionCompraItem` (F21) — API completa (crear/confirmar/anular),
  cero templates. El propio código documenta la omisión deliberada.
- **Facturas:** `NotaCredito`/`ItemNotaCredito` — modelo + API CRUD completos, solo aparecen como un
  badge "NC" en la tabla de facturas. Hueco funcional, no solo visual.
- **Perfil:** `Departamento` — modelo + API CRUD completos, sin listado/tabla ni offcanvas propio;
  solo se usa como `<select>` de opciones embebido en el formulario de Perfil.
- **Contabilidad:** `TipoComprobante`, `CatalogoMaestroNIIF`, `ConfiguracionRetenciones`,
  `ImpuestoDocumento` — modelo (y a veces API) sin ningún template propio; se usan solo como
  selectores embebidos o registros generados internamente. Es un patrón esperable para catálogos de
  soporte, pero se documenta para que quede explícito.
- **Empleados:** `TransmisionNominaDIAN` — sin ViewSet ni ruta registrada, uso puramente interno.
- **Dashboard:** `invalidar-cache` (POST, admin) tiene endpoint + wrapper JS, pero ningún botón lo
  invoca; los endpoints legacy `/data/`, `/summary/`, `/kpis/`, `/quick-actions/` están marcados
  DEPRECADOS en el propio código sin consumidor activo visible.
- **Empresa:** `DELETE` de Empresa (singleton) existe en el ViewSet y en `empresa.api.js`, pero no hay
  botón en la UI — solo alcanzable vía API directa.

### B. Acciones de backend inalcanzables desde la UI (máquinas de estado "muertas" en superficie)

- **Cotizaciones — el hallazgo más grave de esta categoría:** de 11 acciones definidas en
  `CotizacionViewSet`, **9 no tienen ningún botón, `hx-post` ni llamada JS**: `recalcular`, `historial`,
  `volver-a-borrador`, `aprobar`, `rechazar`, `archivar`, `convertir-a-venta`, `facturar-venta`,
  `convertir-a-proyecto`. Solo exportar/generar PDF están conectados. La máquina de estados completa
  de Cotización es, en la práctica, un endpoint muerto desde el punto de vista de un usuario real.
- **Ventas:** `destroy()` (Eliminar Venta) existe en la API y en el wrapper JS (`API.eliminar`,
  `ventas.api.js:67`) pero nunca se invoca desde ningún feature JS — no hay botón Eliminar en la UI.
- **Ventas:** "Facturar DIAN" es código muerto — el botón se removió de los offcanvas de creación y
  detalle por el bloqueo regulatorio (ver `EMISION-FISCAL-01` en `UI_UX_FINDINGS.md`), pero
  `API.procesarFacturar` y la rama `if (action === 'facturar-dian')` siguen presentes en
  `venta_editor.js` sin ningún trigger que los alcance.
- **Cotizaciones:** `Producto`/`Servicio` (catálogo propio de Cotizaciones) tienen Crear/Editar pero
  **sin botón de Eliminar** en la UI, pese a que la API lo soporta.
- **Cotizaciones:** `offcanvas_crear_cotizacion.html`/`offcanvas_editar_cotizacion.html` son templates
  completos pero huérfanos — confirmado por comentario propio del código (`cotizaciones.ui.js:192-196`),
  ningún view los renderiza; el flujo real usa `editor_cotizacion.html`.

### C. Bugs de código descubiertos incidentalmente durante el inventario

- **Empleados:** `DevengoViewSet.render_offcanvas_crear` está definido **dos veces** con el mismo
  `url_path='render-offcanvas/crear'` (`api/viewsets.py` líneas 1545 y 1613) — la segunda definición
  sobreescribe silenciosamente a la primera en Python. Código muerto real, no solo redundante; merece
  revisión de cuál de las dos implementaciones es la que realmente se ejecuta.

### D. Inconsistencia de patrón "Detalle" dentro de la misma app

- **Proyectos:** a diferencia del resto de sus propios submódulos, `Proyecto` reutiliza el mismo
  `offcanvas_form.html` para crear y editar, y no tiene una vista de solo lectura dedicada
  (`offcanvas_detalle_proyecto.html`) — rompe el patrón FSD que la propia app aplica en otros lugares.
- **Proveedores:** `Representante` tiene **3 implementaciones de tabla distintas** para la misma
  entidad (grid Tabulator legado en el directorio, `<table>` HTML manual en el detalle de Proveedor,
  ninguna en django-tables2) — ver detalle de la inconsistencia visual en `UI_UX_PATRONES_VISUALES.md`.

**Resumen:** de las ~85 filas de submódulo/entidad relevadas en las 15 apps, se confirmaron **11
modelos/acciones sin ninguna UI alcanzable** (categoría A+B con `UI existe = No`), **4 con UI parcial**
(falta alguna operación CRUD), **2 templates huérfanos confirmados** y **1 bug de código** (método
duplicado). El resto (~65 filas) tiene UI real y completa para su alcance.

---

**FIN — Fase 8 de `UI_UX_MASTER_MISSION_V2_59_FASES.md`.**
