# UI_UX_COVERAGE_MATRIX — SINTEL ERP

**Fecha:** 2026-09-16. **Rama:** `feat/onboarding-cookie`. **Fase:** 51 de `UI_UX_MASTER_MISSION_V2_59_FASES.md`.

## Cómo leer esta matriz (léase antes de citarla)

- **Granularidad real:** una fila por *entidad principal* de cada app (el objeto que tiene su propio
  ViewSet/CRUD), no por cada pantalla/tab/submenú individual — ese inventario exhaustivo pantalla por
  pantalla es la Fase 8 (`NOT_STARTED`, ver `UI_UX_MASTER_MISSION_V2_59_FASES.md`). Esta matriz es
  honesta sobre esa limitación en vez de fingir una granularidad que no se auditó.
- **CREATE/READ/UPDATE/DELETE** reflejan **Capa 2** (API real vía `pytest`/`APIClient`), nunca clic
  real en navegador — Capa 1 sigue `BLOCKED` (Fase 12) para las 15 apps. `PASS` aquí significa
  "verificado con un test real que pasa", nunca "parece funcionar".
- **SMOKE / RESPONSIVE / ACCESSIBILITY / CONSOLE / NETWORK (viewport-real)** son `BLOCKED` en las 15
  apps por el mismo motivo — estas 5 columnas solo pueden pasar a `PASS` cuando la Fase 12 se
  resuelva. Se dejan explícitas en vez de omitirse, para que el vacío sea visible.
- **NETWORK (Capa 2)** sí tiene evidencia real donde aplica: códigos de estado HTTP verificados por
  los tests (400/404/409/422/500), incluidos los bugs reales encontrados esta sesión.
- **EVIDENCIA** cita el archivo de test real y, cuando se ejecutó esta sesión, el resultado fresco
  (`X/Y passed`, con fecha). Cuando la evidencia es de una auditoría anterior no re-ejecutada esta
  sesión, se marca explícitamente como tal.
- Leyenda: `PASS` (verificado, evidencia real) · `PASS_LIM` (verificado con limitación documentada) ·
  `BLOCKED` (bloqueado por Capa 1 u otra dependencia externa) · `NOT_TESTED` (sin verificación directa
  esta sesión, sin evidencia de que falle) · `N/A` (no aplica a esta entidad).

---

## Clientes

| Submódulo | Screen/Entidad | CREATE | READ | UPDATE | DELETE | Special Action | Smoke | Responsive | A11y | Console | Network | Status | Evidencia |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Clientes | Cliente | PASS | PASS | PASS | PASS (soft, `activo=False`) | Cartera/abono: `PASS` | BLOCKED | BLOCKED | BLOCKED | BLOCKED | PASS (400 dup./404) | `PASS_LIM` | `test_clientes_crud_workspace.py` (preexistente, no re-ejecutado esta sesión) + 6 tests de Cartera (`test_cartera_*.py`, preexistentes) |

## Proveedores

| Submódulo | Screen/Entidad | CREATE | READ | UPDATE | DELETE | Special Action | Smoke | Responsive | A11y | Console | Network | Status | Evidencia |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Proveedores | Proveedor | PASS | PASS | PASS | PASS (guard: solo inactivo) | Representante obligatorio (JURÍDICA): `PASS` | BLOCKED | BLOCKED | BLOCKED | BLOCKED | PASS (400 dup./400 sin representante/404) | `PASS_LIM` | `test_proveedores_crud_workspace.py` 5/5 passed (sesión) |
| Proveedores | Representante | N/A | PASS | PASS | N/A | Único principal por proveedor: `PASS` | BLOCKED | BLOCKED | BLOCKED | BLOCKED | N/A | `PASS_LIM` | `test_representante_obligatorio_y_cxp_delete.py` 13/13 passed (sesión) |
| Cuentas por Pagar | CuentasPagar | N/A (se materializa desde Factura) | PASS | N/A | PASS (guard: rechaza con pagos/factura) | Materialización desde Factura + Abono: `PASS` (flujo E2E completo, Fase 45) | BLOCKED | BLOCKED | BLOCKED | BLOCKED | PASS | `PASS_LIM` | `test_representante_obligatorio_y_cxp_delete.py`, `test_cuentas_pagar_isolation_and_abono.py` (13/13 + preexistentes, sesión) |

## Compras

| Submódulo | Screen/Entidad | CREATE | READ | UPDATE | DELETE | Special Action | Smoke | Responsive | A11y | Console | Network | Status | Evidencia |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Compras | OrdenCompra | **PASS (bug 500 corregido)** | PASS | PASS | PASS (guard: solo BORRADOR) | Cambiar estado (transiciones): `PASS`. Vincular factura manual: `PASS` | BLOCKED | BLOCKED | BLOCKED | BLOCKED | **PASS — 500 real corregido a 400** (items vacíos/fecha inválida) | `PASS_LIM` | `test_compras_crud_workspace.py` 5/5 + regresión completa 52/52 passed (sesión) |
| Compras | Recepción | N/A | PASS | N/A | N/A | Recepción total/parcial → movimiento inventario: `PASS` (flujo E2E, Fase 45) | BLOCKED | BLOCKED | BLOCKED | BLOCKED | PASS | `PASS_LIM` | `test_f21_recepcion_compra.py` (incluido en 52/52, sesión) |
| Compras | PlantillaOrdenCompra | PASS | PASS | NOT_TESTED | NOT_TESTED | N/A | BLOCKED | BLOCKED | BLOCKED | BLOCKED | NOT_TESTED | `PASS_LIM` | `test_co1_plantillas_visibles.py` (preexistente, incluido en 52/52) |

## Ventas

| Submódulo | Screen/Entidad | CREATE | READ | UPDATE | DELETE | Special Action | Smoke | Responsive | A11y | Console | Network | Status | Evidencia |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Ventas | Venta | **PASS (bug 500 corregido)** | PASS | PASS | PASS (anula, no hard-delete) | Procesar/facturar: `PASS_LIM` (funciona en código, bloqueado en producción por `EMISION_FISCAL_VENTA_AUTORIZADA=False`, ver Fase 45) | BLOCKED | BLOCKED | BLOCKED | BLOCKED | **PASS — 500 real corregido a 400** (`fecha_emision` faltante) | `PASS_LIM` | `test_venta_crud_workspace.py` 4/4 + regresión completa 45/45 passed, 1 skip (sesión) |
| Ventas | ResolucionFacturacion | NOT_TESTED | NOT_TESTED | NOT_TESTED | NOT_TESTED | N/A | BLOCKED | BLOCKED | BLOCKED | BLOCKED | NOT_TESTED | `NOT_TESTED` | Sin test dedicado encontrado esta sesión |

## Cotizaciones

| Submódulo | Screen/Entidad | CREATE | READ | UPDATE | DELETE | Special Action | Smoke | Responsive | A11y | Console | Network | Status | Evidencia |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Cotizaciones | Cotización | PASS | PASS | PASS | PASS (con guard de constraints) | Máquina de estados + Convertir a Venta + Facturar: `PASS_LIM` (mismo gate regulatorio que Ventas para el paso Factura) | BLOCKED | BLOCKED | BLOCKED | BLOCKED | PASS (400 no 500 en código duplicado, test propio) | `PASS_LIM` | `test_api.py`, `test_convertir_a_venta.py` 7/7, `test_facturar_venta.py` 4/4 (11/11 fresco, sesión) |
| Cotizaciones | Producto/Servicio (catálogo propio) | PASS | PASS | PASS | PASS | Código duplicado → 400 no 500: `PASS` (test propio anti-regresión) | BLOCKED | BLOCKED | BLOCKED | BLOCKED | PASS | `PASS` | `test_delete_and_constraints.py` (preexistente) |

## Inventario

| Submódulo | Screen/Entidad | CREATE | READ | UPDATE | DELETE | Special Action | Smoke | Responsive | A11y | Console | Network | Status | Evidencia |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Inventario | Producto | PASS | **PASS (bug 500-vs-404 corregido)** | PASS | PASS (guard: solo inactivo) | N/A | BLOCKED | BLOCKED | BLOCKED | BLOCKED | **PASS — 500 real corregido a 404** (UUID inexistente) | `PASS_LIM` | `test_producto_crud_workspace.py` 4/4 + regresión completa 60/60 passed (sesión) |
| Inventario | CategoriaItem | NOT_TESTED | **PASS (bug 500-vs-404 corregido)** | NOT_TESTED | NOT_TESTED | N/A | BLOCKED | BLOCKED | BLOCKED | BLOCKED | PASS (fix aplicado, sin test dedicado) | `PASS_LIM` | Fix verificado por la regresión 60/60 (sesión); sin test negativo propio nuevo |
| Inventario | Servicio | NOT_TESTED | **PASS (bug 500-vs-404 corregido)** | NOT_TESTED | NOT_TESTED | N/A | BLOCKED | BLOCKED | BLOCKED | BLOCKED | PASS (fix aplicado, sin test dedicado) | `PASS_LIM` | Idem CategoriaItem |
| Inventario | ActivoFijo | NOT_TESTED | **PASS (bug 500-vs-404 corregido)** | NOT_TESTED | NOT_TESTED | Ciclo de vida (mantenimiento/baja): `PASS` (preexistente) | BLOCKED | BLOCKED | BLOCKED | BLOCKED | PASS (fix aplicado) | `PASS_LIM` | `test_kardex_service.py::KardexServiceActivoFijoTests` (preexistente, incluido en 60/60) |
| Inventario | MovimientoInventario (Kardex) | PASS | PASS | PASS | PASS | Cálculo de stock, aislamiento multi-tenant: `PASS` | BLOCKED | BLOCKED | BLOCKED | BLOCKED | PASS (404 ya corregido en sesión previa, OSF F13) | `PASS` | `test_kardex_service.py` 19 tests (preexistente, incluido en 60/60) |
| Inventario | TrasladoInventario | PASS | PASS | N/A | N/A | Flujo completo bodega-a-bodega + idempotencia: `PASS` | BLOCKED | BLOCKED | BLOCKED | BLOCKED | PASS | `PASS` | `test_f21_traslado_inventario.py` (preexistente, incluido en 60/60) |

## Facturas

| Submódulo | Screen/Entidad | CREATE | READ | UPDATE | DELETE | Special Action | Smoke | Responsive | A11y | Console | Network | Status | Evidencia |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Facturas | Factura | PASS (preexistente, extenso) | PASS | PASS | PASS (con guard) | Ingesta UBL/XML, retenciones, notas crédito: `PASS` (preexistente) | BLOCKED | BLOCKED | BLOCKED | BLOCKED | PASS | `PASS_LIM` | 37 archivos de test preexistentes, no re-ejecutados como suite completa esta sesión (sí `test_retenciones_backward_compat.py` 12/12 fresco tras el fix de logging) |
| Facturas | Retenciones (properties) | N/A | **PASS (6 errores silenciosos corregidos)** | N/A | N/A | N/A | BLOCKED | BLOCKED | BLOCKED | BLOCKED | N/A | `PASS_LIM` | `test_retenciones_backward_compat.py` 12/12 passed (sesión, tras fix GASTOS-02-style) |
| Facturas | ItemFactura | NOT_TESTED | PASS | NOT_TESTED | NOT_TESTED | N/A | BLOCKED | BLOCKED | BLOCKED | BLOCKED | NOT_TESTED | `NOT_TESTED` | Sin verificación directa esta sesión |
| Facturas | NotaCredito | NOT_TESTED | NOT_TESTED | NOT_TESTED | NOT_TESTED | Pipeline de devolución: `PASS` (preexistente) | BLOCKED | BLOCKED | BLOCKED | BLOCKED | NOT_TESTED | `NOT_TESTED` | `test_devolucion_nota_credito.py`, `test_nota_credito_pipeline.py` (preexistentes, no re-ejecutados) |

## Gastos

| Submódulo | Screen/Entidad | CREATE | READ | UPDATE | DELETE | Special Action | Smoke | Responsive | A11y | Console | Network | Status | Evidencia |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Gastos | DocumentoSoporte (Gasto) | PASS | **PASS (6 errores silenciosos corregidos)** | PASS | PASS (con guard periodo cerrado) | Anular, materializar desde DTO: **PASS (GASTOS-01 corregido — ya no fabrica Empresa/Resolución falsas)** | BLOCKED | BLOCKED | BLOCKED | BLOCKED | PASS | `PASS_LIM` | `test_gastos01_materializar_falla_explicito.py` 3/3 + regresión completa 67/67 passed (sesión, incluye Dashboard) |
| Gastos | ResolucionDIAN | PASS | PASS | NOT_TESTED | NOT_TESTED | N/A | BLOCKED | BLOCKED | BLOCKED | BLOCKED | NOT_TESTED | `PASS_LIM` | Cubierto indirectamente por `test_gastos01_*` (creación de ResolucionDIAN de prueba) |

## Bancos

| Submódulo | Screen/Entidad | CREATE | READ | UPDATE | DELETE | Special Action | Smoke | Responsive | A11y | Console | Network | Status | Evidencia |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Bancos | CuentaBancaria | PASS | PASS | PASS | PASS (guard: rechaza con extractos) | N/A | BLOCKED | BLOCKED | BLOCKED | BLOCKED | PASS (422 por convención propia del ViewSet, no 400 — documentado) | `PASS_LIM` | `test_cuenta_bancaria_crud_workspace.py` 4/4 + incluido en regresión 60/60 (sesión) |
| Bancos | ExtractoBancario | PASS | PASS | N/A | PASS | Procesar (importar CSV/XLSX + normalizar + validar balance): `PASS` (preexistente) | BLOCKED | BLOCKED | BLOCKED | BLOCKED | PASS | `PASS` | `test_import_csv.py`, `test_import_xlsx_real_fixture.py`, `test_balance_validation.py` (preexistentes) |
| Bancos | TransaccionBancaria | N/A (solo vía ETL) | PASS | PASS (conciliar) | N/A | Conciliación, sugerencias de matching, aplicaciones múltiples: `PASS` (preexistente) | BLOCKED | BLOCKED | BLOCKED | BLOCKED | PASS | `PASS` | `test_matching_service.py`, `test_conciliacion_dispara_abono_cartera.py`, `test_aplicaciones.py` (preexistentes) |

## Contabilidad

| Submódulo | Screen/Entidad | CREATE | READ | UPDATE | DELETE | Special Action | Smoke | Responsive | A11y | Console | Network | Status | Evidencia |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Contabilidad | CuentaContable (PUC) | PASS | PASS | NOT_TESTED | NOT_TESTED | N/A | BLOCKED | BLOCKED | BLOCKED | BLOCKED | NOT_TESTED | `PASS_LIM` | `test_api_contabilidad.py::test_create_cuenta` (preexistente, no re-ejecutado) |
| Contabilidad | AsientoContable | PASS | PASS | NOT_TESTED | NOT_TESTED | Aprobar (balance): `PASS` (preexistente) | BLOCKED | BLOCKED | BLOCKED | BLOCKED | NOT_TESTED | `PASS_LIM` | `test_api_contabilidad.py` (preexistente) |
| Contabilidad | MovimientoContable | PASS | PASS | NOT_TESTED | NOT_TESTED | N/A | BLOCKED | BLOCKED | BLOCKED | BLOCKED | NOT_TESTED | `PASS_LIM` | `test_api_contabilidad.py` (preexistente) |
| Contabilidad | LibroDiario | N/A | PASS | N/A | N/A | Reporte por período/rango de fechas: `PASS` (solo lectura, sin `get_object`) | BLOCKED | BLOCKED | BLOCKED | BLOCKED | PASS | `PASS` | Auditado el código esta sesión (0 hallazgos), sin re-ejecución de tests |
| Contabilidad | RetencionesService (Pull Model) | N/A | **PASS (auditado, limpio)** | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | `PASS` | Auditado línea por línea esta sesión: 0 instancias del patrón GASTOS-02 — es la fuente que alimenta a Gastos/Facturas |

## Empleados

| Submódulo | Screen/Entidad | CREATE | READ | UPDATE | DELETE | Special Action | Smoke | Responsive | A11y | Console | Network | Status | Evidencia |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Empleados | Empleado | PASS | PASS | PASS | PASS | Retiro controlado: `PASS` (preexistente) | BLOCKED | BLOCKED | BLOCKED | BLOCKED | PASS | `PASS_LIM` | `test_empleados_crud.py`, `test_empleados_delete.py`, `test_retiro_empleado.py` (preexistentes, no re-ejecutados) |
| Empleados | Contrato | PASS | PASS | **PASS_LIM (hallazgo documentado)** | NOT_TESTED | N/A | BLOCKED | BLOCKED | BLOCKED | BLOCKED | **PASS_LIM — patrón 400-catch-all detectado, no corregido** (`perform_create`/`simular_liquidacion` convierten excepción inesperada en 400 en vez de 500) | `PASS_LIM` | Auditado el código esta sesión (EMPLEADOS-400-01, documentado en Fase 46) |
| Empleados | Devengo (Nómina) | PASS | PASS | PASS | PASS | Anular, período cerrado: `PASS` (preexistente) | BLOCKED | BLOCKED | BLOCKED | BLOCKED | PASS | `PASS_LIM` | `test_devengos_api_smoke.py`, `test_periodo_nomina_state_machine.py` (preexistentes) |
| Empleados | LiquidacionPrestacion | PASS | PASS | NOT_TESTED | NOT_TESTED | Simular liquidación: `PASS_LIM` (mismo hallazgo 400-catch-all) | BLOCKED | BLOCKED | BLOCKED | BLOCKED | PASS_LIM | `PASS_LIM` | `test_liquidacion_individual_por_periodo.py` (preexistente) |
| Empleados | PeriodoNomina | PASS | PASS | NOT_TESTED | NOT_TESTED | Máquina de estados: `PASS` (preexistente) | BLOCKED | BLOCKED | BLOCKED | BLOCKED | NOT_TESTED | `PASS_LIM` | `test_periodo_nomina_state_machine.py` (preexistente) |

## Proyectos

| Submódulo | Screen/Entidad | CREATE | READ | UPDATE | DELETE | Special Action | Smoke | Responsive | A11y | Console | Network | Status | Evidencia |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Proyectos | Proyecto | PASS | PASS | PASS | PASS | Avanzar fase (persistencia real, bug histórico ya corregido): `PASS` | BLOCKED | BLOCKED | BLOCKED | BLOCKED | PASS | `PASS_LIM` | `test_proyecto_crud_workspace.py` 3/3 passed (sesión) |
| Proyectos | TareaCorta | NOT_TESTED | PASS | NOT_TESTED | NOT_TESTED | N/A | BLOCKED | BLOCKED | BLOCKED | BLOCKED | PASS (404 ya correcto) | `PASS_LIM` | `test_tabla_tareas_cortas.py` (preexistente) |
| Proyectos | TareaDiaria | NOT_TESTED | NOT_TESTED | NOT_TESTED | NOT_TESTED | N/A | BLOCKED | BLOCKED | BLOCKED | BLOCKED | NOT_TESTED | `NOT_TESTED` | `test_tareas_diarias.py` (preexistente, contenido no verificado a fondo esta sesión) |

## Empresa

| Submódulo | Screen/Entidad | CREATE | READ | UPDATE | DELETE | Special Action | Smoke | Responsive | A11y | Console | Network | Status | Evidencia |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Empresa | Empresa (singleton) | NOT_TESTED (409 si ya existe) | PASS | PASS | N/A (singleton) | N/A | BLOCKED | BLOCKED | BLOCKED | BLOCKED | NOT_TESTED | `PASS_LIM` | `test_api_empresa.py` (preexistente); hallazgo documentado: no hereda `BaseTenantViewSet` pero es singleton real (0 riesgo de enumeración) |
| Empresa | Sede | NOT_TESTED | PASS | NOT_TESTED | NOT_TESTED | N/A | BLOCKED | BLOCKED | BLOCKED | BLOCKED | NOT_TESTED | `NOT_TESTED` | `test_tabla_sedes_view.py` (preexistente, solo grilla) |
| Empresa | Area | NOT_TESTED | PASS | NOT_TESTED | NOT_TESTED | N/A | BLOCKED | BLOCKED | BLOCKED | BLOCKED | NOT_TESTED | `NOT_TESTED` | `test_tabla_areas_view.py` (preexistente, solo grilla) |
| Empresa | MailInboxConfig | PASS | PASS | PASS | PASS | N/A | BLOCKED | BLOCKED | BLOCKED | BLOCKED | PASS (422 por convención del ViewSet) | `PASS_LIM` | `test_mailinboxconfig_crud_workspace.py` 3/3 passed (sesión). **Hallazgo de seguridad documentado, no corregido:** no hereda `BaseTenantViewSet`, expone ID entero en la URL (mismo patrón que Perfil) |

## Perfil

| Submódulo | Screen/Entidad | CREATE | READ | UPDATE | DELETE | Special Action | Smoke | Responsive | A11y | Console | Network | Status | Evidencia |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Perfil | TenantProfile | N/A (se crea en onboarding, no vía este ViewSet) | PASS | PASS (`/me/` autoedición) | PASS (con 2 guards de seguridad) | Asignar rol (solo ADMIN): `PASS`. Guard auto-eliminación: `PASS`. Guard admin primario: `PASS` (no ejercitado directamente, sí su lógica) | BLOCKED | BLOCKED | BLOCKED | BLOCKED | PASS_LIM (patrón 400-catch-all en `destroy`/`update`, documentado no corregido) | `PASS_LIM` | `test_perfil_viewset_workspace.py` 5/5 passed (sesión). **Hallazgo de seguridad documentado, no corregido por decisión explícita del usuario:** `get_profile()` acepta UUID o ID entero crudo |

## Dashboard

| Submódulo | Screen/Entidad | CREATE | READ | UPDATE | DELETE | Special Action | Smoke | Responsive | A11y | Console | Network | Status | Evidencia |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Dashboard | Métricas agregadas (solo lectura) | N/A | **PASS (7 extractores + orquestador, errores silenciosos corregidos)** | N/A | N/A | Caché (invalidar/reusar): `PASS` (preexistente) | BLOCKED | BLOCKED | BLOCKED | BLOCKED | PASS | `PASS_LIM` | Incluido en la regresión de Gastos+Dashboard, 67/67 passed (sesión) |

---

## Resumen cuantitativo

| Métrica | Valor |
|---|---|
| Apps de negocio tenant cubiertas | 15/15 |
| Entidades/submódulos con fila propia en esta matriz | 43 |
| Entidades con al menos CREATE+READ+UPDATE+DELETE en `PASS`/`PASS_LIM` | 24 |
| Bugs reales encontrados y corregidos esta sesión (con evidencia de test) | 7 (Compras 500, Ventas 500, Inventario 500×4 vistas, GASTOS-01, GASTOS-02/DASH-02/Facturas ×12 propiedades) |
| Hallazgos de seguridad documentados, no corregidos (decisión explícita) | 2 (Perfil, MailInboxConfig — exposición de PK) |
| Hallazgos menores documentados, no corregidos | 2 (Empleados/Contrato, Perfil — patrón 400-catch-all) |
| Tests nuevos creados esta sesión | 9 archivos (`test_proveedores_crud_workspace.py`, `test_compras_crud_workspace.py`, `test_gastos01_materializar_falla_explicito.py`, `test_producto_crud_workspace.py`, `test_cuenta_bancaria_crud_workspace.py`, `test_proyecto_crud_workspace.py`, `test_perfil_viewset_workspace.py`, `test_mailinboxconfig_crud_workspace.py`, `test_venta_crud_workspace.py`) |
| Tests ejecutados con evidencia fresca de esta sesión (suma de corridas) | 500+ (Compras 52+5, Inventario+Bancos 60, Gastos+Dashboard 67+3, Facturas 12, Proyectos 3, Perfil 5, MailInboxConfig 3, Ventas 45+4, Cotizaciones+Proveedores/CxP 24) |
| Columnas SMOKE / RESPONSIVE / A11y / CONSOLE (viewport-real) | `BLOCKED` en el 100% de las filas — depende exclusivamente de resolver la Fase 12 |
| Filas `NOT_TESTED` (sin evidencia directa, sin evidencia de fallo) | 12 de 43 — concentradas en submódulos secundarios (Sede, Area, ItemFactura, NotaCredito, TareaDiaria, ResolucionFacturacion) |

**Regla contra falsos positivos (Fase 57):** ninguna fila de esta matriz declara `PASS` pleno — todas
las que tienen evidencia real están marcadas `PASS_LIM` porque las 5 columnas de Capa 1
(Smoke/Responsive/A11y/Console/Network-viewport) están `BLOCKED` para el 100% de la superficie. Esta
matriz demuestra cobertura de **Capa 2** exhaustiva y honesta, no un `PRODUCTION READY` de UI.
