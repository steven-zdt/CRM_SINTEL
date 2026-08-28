# Matriz de Brechas Empresariales — SINTEL ERP

**Fecha:** 2026-08-27. Consolidación de evidencia real (código citado archivo:línea)
de: 2 auditorías de arquitectura previas (2026-08-21), 9 matrices normativas
por app (2026-08-21), 4 documentos de baseline F15/F18/F20/F22 (2026-08-09,
con drift verificado), 3 misiones de modernización dedicadas en esta sesión
(cotizaciones/proveedores/inventario, 2026-08-27), y 3 agentes de
investigación fresca de esta misma auditoría (controles internos, UX/
reporting, integridad de datos — 2026-08-27).

Columnas: Proceso | App | Hallazgo | Severidad | Categoría | Impacto |
Corrección sugerida | Dependencia | Evidencia

---

## CRITICAL

| Proceso | App | Hallazgo | Categoría | Impacto | Corrección | Dependencia | Evidencia |
|---|---|---|---|---|---|---|---|
| Facturación | `facturas` | `Factura.destroy()` hace **DELETE físico** de Factura+NC+Anexos+Items, sin bloqueo, incluso si es una factura electrónica con CUFE ya aceptado por la DIAN. No reversa `MovimientoInventario` ni `AsientoContable` ya generados — quedan huérfanos referenciando un `documento_origen_id` inexistente | ACCOUNTING, LEGAL, DATA | Pérdida de integridad contable/inventario; para una factura DIAN aceptada, es además un problema de cumplimiento (no se "borra" un documento electrónico, se corrige con NC/ND) | Bloquear `destroy()` si la factura tiene `cufe` no nulo o vínculos contables activos; ofrecer solo anulación/reversa, mismo patrón que `Venta.anular_venta()`/`Gasto.anular_documento()`/`Contabilizador.reversar_asiento()` | Ninguna — corrección interna, sin dependencia externa | `apps/tenant/facturas/api/viewsets.py:532-596`, `services/crud_service.py:68-89` |
| Cierre contable | `contabilidad`↔`facturas`/`gastos` | `PeriodoContable` documenta explícitamente en su propio docstring que "bloquea edición/anulación de Facturas y Gastos en periodos cerrados" — **la función real (`verificar_periodo_cerrado`) nunca se invoca desde `facturas` ni `gastos`**, solo desde `contabilidad` para `AsientoContable` | ACCOUNTING | Una Factura o Gasto puede editarse/anularse libremente con fecha dentro de un período ya cerrado, descuadrando los reportes contables ya emitidos de ese período | Invocar `verificar_periodo_cerrado()` desde los puntos de edición/anulación de `Factura`/`DocumentoSoporte`, o corregir el docstring si la decisión real es no bloquearlos (documentar cuál) | Ninguna | `apps/tenant/contabilidad/models.py:572-574` (docstring) vs. grep negativo en `apps/tenant/facturas/`, `apps/tenant/gastos/` |
| Facturación electrónica DIAN | `facturas` | Transmisión real del documento firmado al webservice DIAN nunca ocurre — confirmado de nuevo con grep exhaustivo. Existe un adaptador SOAP real (`DIANAdapter`, `apps/tenant/core/dian/adapters.py`, usa `zeep`) pero está desconectado por defecto (`NullTransportAdapter`) y el propio módulo se autodeclara "NO VERIFICADO CONTRA EL AMBIENTE REAL DE LA DIAN" (WS-Security no implementado, WSDL no configurado) | LEGAL, TAX | Ninguna factura emitida por SINTEL tiene validez legal como factura electrónica ante la DIAN hoy, independientemente de que CUFE/XML/firma sean técnicamente correctos | Requiere credenciales/certificado/WSDL DIAN reales de un tenant en producción para siquiera empezar a cerrarse — **no se puede completar sin esas credenciales** | **EXTERNAL_DEPENDENCY** (credenciales DIAN) | `apps/tenant/facturas/services/electronic_invoice_service.py:71-136`, `apps/tenant/core/dian/adapters.py:1-45,167-189` |

## HIGH

| Proceso | App | Hallazgo | Categoría | Impacto | Corrección | Dependencia | Evidencia |
|---|---|---|---|---|---|---|---|
| Nómina electrónica DIAN | `empleados` | DSPNE (`TransmisionNominaDIAN.estado_dian`) permanece `PENDIENTE` indefinidamente — mismo patrón que facturas, sin transmisión XML real (DEUDA-11, abierta desde 2026-06-17) | LEGAL, TAX | Nómina electrónica sin validez legal ante DIAN para tenants obligados | Igual que arriba — requiere credenciales DIAN reales | **EXTERNAL_DEPENDENCY** | `apps/tenant/empleados/services/business_service.py:464-471`, `.agent/AUDITORIA_FLUJO_EMPLEADOS.md:550` |
| Compras | `compras` | `OrdenCompra.cambiar_estado()` no valida la máquina de estados (permite saltos arbitrarios ej. `RECIBIDA→BORRADOR`); anular una orden ya `APROBADA` no reversa la CxP ya generada (reconocido en comentario propio del código como fuera de alcance) | ARCHITECTURE, ACCOUNTING | Estados inconsistentes de OrdenCompra; una CxP puede quedar activa tras anular su orden origen | Agregar validación de transición válida (`TRANSICIONES_VALIDAS`, mismo patrón ya usado en `Factura`); implementar reversa de CxP al anular una orden aprobada | Ninguna | `apps/tenant/compras/services/crud_service.py:245-261`, `business_service.py:360-380` |
| Contabilidad/Tributario | `contabilidad` | `Retencion` no tiene NINGUNA protección contra duplicados — ni `UniqueConstraint` de BD ni `.exists()` de aplicación en `RetencionesService.crear_retenciones_desde_dict()` | TAX, DATA | Una doble ejecución (retry, doble-click, reprocesamiento de backfill) duplica silenciosamente los montos de retención, afectando reportes DIAN de retenciones | Agregar `UniqueConstraint` sobre `(documento_origen_app, documento_origen_modelo, documento_origen_id, tipo)` (mismo patrón ya usado en `AsientoContable`/`MovimientoInventario`) | Ninguna | `apps/tenant/contabilidad/services/retenciones_service.py:208-297`, `models.py:1088-1093` (solo índice, no constraint) |
| Contabilidad | `contabilidad` | `TipoComprobante.obtener_siguiente_numero()` es el único generador de numeración de todo el sistema sin `select_for_update()` — bajo concurrencia real puede generar `IntegrityError` no controlado o saltar un consecutivo | DATA, ARCHITECTURE | Riesgo de fallo real bajo uso concurrente (2 usuarios contabilizando simultáneamente) | Aplicar `select_for_update()` sobre `TipoComprobante`, mismo patrón ya usado consistentemente en `cotizaciones`/`compras`/`ventas`/`empleados` | Ninguna | `apps/tenant/contabilidad/models.py:225-230` |
| Controles internos | `compras`/`gastos`/`bancos` | Sin segregación de rol real en ninguno de los 3 flujos — un mismo ADMIN puede crear, aprobar, recibir/pagar y (en bancos) conciliar sin ningún punto de control forzado. Bancos ni siquiera registra quién concilió | BUSINESS, SECURITY | Riesgo de control interno real (fraude/error no detectable) en 3 de 5 flujos transaccionales auditados | Requiere decisión de producto: ¿el negocio necesita segregación forzada, o es aceptable para el tamaño de MIPYME objetivo? Si se decide que sí, replicar el patrón ya probado de `PeriodoNominaViewSet._ROLES_POR_ACCION` | Decisión de producto — no es un bug, es una ausencia de feature | `apps/tenant/compras/api/viewsets.py:73-78`, `apps/tenant/gastos/models.py:4-9`, `apps/tenant/bancos/api/viewsets.py:275` |

## MEDIUM

| Proceso | App | Hallazgo | Categoría | Corrección sugerida | Evidencia |
|---|---|---|---|---|---|
| Gastos | `gastos` | `destroy()` del ViewSet se salta la protección "debe estar anulado antes de borrar" cuando `settings.DEBUG=True` — mismo patrón de bypass que ya se corrigió en Kardex/Inventario en esta misma sesión | SECURITY | Aplicar el mismo fix (quitar el bypass condicional a `DEBUG`) | `apps/tenant/gastos/api/viewsets.py:124-134` |
| Bancos | `bancos` | `TransaccionBancaria`/`ExtractoBancario` sin `UniqueConstraint` de BD contra duplicados — solo `.exists()` de aplicación, TOCTOU real bajo doble-submit | DATA | Agregar constraint de BD equivalente | `apps/tenant/bancos/models.py` (solo `Index`, sin `UniqueConstraint`) |
| Facturación | `facturas` | `Factura.consecutivo=0` para TODAS las facturas importadas por XML externo (`dto.get("consecutivo", 0)`) — el campo queda inutilizable como identificador fuera del flujo interno | DATA | Documentar explícitamente en el modelo que `consecutivo` no aplica a `Origen.EXTERNO`, o usar `None` en vez de `0` | `apps/tenant/facturas/services/business_service.py:656` |
| Tesorería | `bancos` | Sin validación de que la fecha de una conciliación/pago sea posterior o igual a la fecha del documento que paga | DATA, ACCOUNTING | Agregar validación en `ConciliarSerializer.validate()` | `apps/tenant/bancos/api/serializers.py:246-252` |
| UX empresarial | `dashboard` | Faltan extractores de Compras y Bancos — órdenes pendientes de recepción y conciliación bancaria no aparecen en el Dashboard consolidado | UX, ARCHITECTURE | Agregar `compras_ext.py`/`bancos_ext.py` siguiendo el patrón Pull ya usado por los 7 extractores existentes | `apps/tenant/dashboard/services/extractores/` (ausencia confirmada) |
| UX empresarial | `dashboard` | Widget "Gastos → Vencidos" muestra en realidad `gastos_anulados` (documentos anulados), no gastos vencidos — bug real de negocio, no solo naming | UX, DATA | Corregir la métrica para calcular vencimiento real (fecha de vencimiento vs. hoy), o renombrar el widget si "anulados" es lo que realmente se quiere mostrar | `apps/tenant/dashboard/services/extractores/gastos_ext.py:26-34` |
| Reporting | `dashboard`/`inventario` | "Valor de inventario" tiene 2 fórmulas divergentes: Dashboard filtra `activo=True`, la vista propia de Inventario no filtra — mismo concepto, cifras distintas en pantallas distintas | DATA, ARCHITECTURE | Unificar en una sola función SSoT consumida por ambas pantallas | `apps/tenant/dashboard/services/extractores/inventario_ext.py:44-47` vs `apps/tenant/inventario/views.py:83-85` |
| Reporting | `clientes` | "Cartera pendiente" de clientes (CxC) tiene 2 selectores independientes (`get_cartera_kpis_facturas_venta` sobre `Factura` directo, `get_cartera_kpis` sobre modelo `Cartera` con vocabulario de estado distinto) — riesgo de desincronización si `Cartera.saldo` y `Factura.total` alguna vez divergen | DATA, ARCHITECTURE | Determinar cuál es el SSoT real y hacer que el otro lo consuma, no lo recalcule | `apps/tenant/clientes/services/selectors.py:336-364,367-383` |
| UX empresarial | `core`/reporting frontend | Reporting Hub backend sirve 5 datasets reales, pero el frontend solo tiene pantalla propia para 1 (`ventas.resumen`) — los otros 4 muestran "Próximamente" | UX | Completar las 4 pantallas faltantes, o retirar del catálogo los datasets sin UI si no hay plan de completarlos pronto | `apps/tenant/core/static/core/js/.../reportes_landing.js:19-21` (documentado en el propio comentario del archivo) |
| Control de cierre | `contabilidad` | `cerrar_periodo()` no verifica pendientes=0 ni descuadres antes de cerrar — es un único clic con un `prompt()` de observaciones opcionales, sin checklist previo | ACCOUNTING, BUSINESS | Agregar un gate previo (documentos sin contabilizar=0, asientos descuadrados=0) antes de permitir el cierre | `apps/tenant/contabilidad/services/business_service.py:349-361` |
| UX por rol | `contabilidad`/`bancos`/`empleados` | VISOR ve exactamente el mismo HTML/botones que ADMIN — el bloqueo de mutaciones es 100% backend, sin ocultamiento visual (un VISOR ve botones que fallarán al hacer clic) | UX | Ocultar/deshabilitar controles según `TenantProfile.rol` en el frontend, consumiendo el mismo `User Access Context` ya existente — no construir una regla paralela | Grep exhaustivo sin resultados reales fuera de la propia app `perfil` |
| Ciclo comercial | `cotizaciones`→`ventas` | Aceptar una Cotización no crea ni vincula automáticamente una Venta — discontinuidad real en el flujo Cliente→Cotización→Venta que el prompt maestro describe como secuencial | BUSINESS | Requiere decisión de producto: ¿es intencional (Cotización es solo documento comercial previo) o falta el paso? | `F15_INTEGRATION_BASELINE.md` — sin arista `cotizaciones→ventas` detectada |

## LOW

| Proceso | App | Hallazgo | Categoría |
|---|---|---|---|
| Compras | `compras` | `OrdenCompra.ESTADO_CHOICES` incluye `'ANULADA'` pero ningún método de servicio transiciona a ese estado — código inalcanzable, no corrupción | ARCHITECTURE |
| Facturación | `facturas` | `Factura` no tiene ningún campo persistido hacia `Venta` (`venta_uuid`) pese a que un comentario del propio código sugiere que debería tenerlo — el vínculo real es solo por igualdad de string (`numero_factura`==`numero`) | ARCHITECTURE, DATA |
| Tributario | `proveedores` | `ProveedorBusinessService.obtener_configuracion_retenciones()`/`calcular_componentes_retencion()` son código muerto confirmado (tarifas hardcodeadas, nunca ejecutadas — el mecanismo real vive en `contabilidad`) | ARCHITECTURE |

---

## DEFERRED (requiere revisión profesional, no una corrección de código)

- Contenido de los seeds PUC/NIIF/períodos/reglas contables no verificado contra la versión normativa vigente — `PROFESSIONAL_REVIEW_REQUIRED`.
- Tarifas de IVA sin validar contra 0%/5%/19% en `compras`/`ventas` (entrada libre del usuario).
- Jornada Ley 2101/2021 no parametrizada por fecha histórica; límite 2h/día de horas extra no confirmado como validado.
- Clasificación de régimen tributario del cliente (`regimen_tributario`) capturada pero sin lógica downstream que la use.
- Calendario tributario/vencimientos: no existe ningún mecanismo (correctamente, no se hardcodeó nada tampoco).
- Dirección inversa de retenciones (cliente actuando como agente retenedor sobre lo que nos paga) — no confirmado si existe o no, requiere verificación dirigida futura.
